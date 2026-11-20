"""Fake coil signals, so the whole pipeline runs with no hardware.

The simulator places one or more lines under the staff, works out the field
each coil sees with the same model the solver uses, applies made-up coil
gains (signs included, as if two coils were wound backwards), then adds 60 Hz
hum and white noise. The staff can walk back and forth across the line.
"""
import math
import time

import numpy as np

from . import config
from .geometry import coil_samples, response


class SimSource:
    """Drop-in for AlsaSource.

    lines: list of (x, depth, strength); x and depth in metres from the tip.
    staff_x: function of time (s) giving the staff's sideways position.
    """

    def __init__(self, freq=8192.0, lines=((0.0, 1.5, 1.0),), staff_x=None,
                 gains=(1.0, -0.93, 1.06, 0.97), noise=2e-5, hum=0.0,
                 amplitude=0.02, rate=None, block=None, seed=1, freq_error=0.0,
                 realtime=False, field_fn=None):
        self.rate = rate or config.SAMPLE_RATE
        self.block = block or config.BLOCK
        self.channels = config.CHANNELS
        self.freq = freq + freq_error
        self.lines = list(lines)
        self.staff_x = staff_x or (lambda t: 0.0)
        self.gains = np.asarray(gains, float)
        self.noise, self.hum, self.amplitude = noise, hum, amplitude
        self.rng = np.random.default_rng(seed)
        self.n = 0
        self.pts, self.axes = coil_samples()
        self.phase0 = 0.7
        self.hum_phase = self.rng.uniform(0, 2 * math.pi, self.channels)
        self.realtime = realtime
        self.field_fn = field_fn        # if set: t -> field per coil, overrides lines
        self._t_start = None

    def field(self, t):
        """Field along each coil axis (arbitrary units) at time t."""
        if self.field_fn is not None:
            return np.asarray(self.field_fn(t), float)
        sx = self.staff_x(t)
        total = np.zeros(self.channels)
        for (x, depth, strength) in self.lines:
            total += strength * response(x - sx, -depth, self.pts, self.axes)
        return total

    def read(self):
        n = self.block
        if self.realtime:
            if self._t_start is None:
                self._t_start = time.monotonic()
            ahead = self._t_start + self.n / self.rate - time.monotonic()
            if ahead > 0:
                time.sleep(ahead)
        t0 = self.n / self.rate
        t = t0 + np.arange(n) / self.rate
        amp = self.amplitude * self.gains * self.field(t0 + 0.5 * n / self.rate)
        carrier = np.cos(2 * np.pi * self.freq * t + self.phase0)
        x = carrier[:, None] * amp[None, :]
        if self.hum:
            x += self.hum * np.cos(2 * np.pi * 60.0 * t[:, None] + self.hum_phase[None, :])
        x += self.rng.normal(0.0, self.noise, x.shape)
        self.n += n
        return x

    def close(self):
        pass


def walking(span=1.2, period=16.0):
    """Staff position: sweeps from -span to +span and back."""
    return lambda t: span * math.sin(2 * math.pi * t / period)
