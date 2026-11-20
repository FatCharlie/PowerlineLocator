"""From raw blocks to an answer: signal strength, depth, left/right, warnings."""
import json
import math
import os
import time

import numpy as np

from . import config
from .geometry import is_distorted, solve
from .lockin import Tracker, find_frequency


# ------------------------------------------------------------ calibration --
def load_cal(path=None):
    path = path or config.CAL_FILE
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_cal(entry_key, entry, path=None):
    path = path or config.CAL_FILE
    cal = load_cal(path)
    cal[entry_key] = entry
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cal, f, indent=2)
    os.replace(tmp, path)
    return cal


# -------------------------------------------------------------- frequency --
def capture(source, seconds):
    blocks = max(1, int(round(seconds * source.rate / source.block)))
    return np.vstack([source.read() for _ in range(blocks)])


def lock_frequency(source, nominal, span, seconds=1.0):
    """Find the transmitter's exact frequency (it can be a few Hz off)."""
    if span <= 0:
        return nominal, float("nan")
    x = capture(source, seconds)
    return find_frequency(x, source.rate, nominal, span)


# ------------------------------------------------------------------ result --
class Estimate:
    __slots__ = ("snr_db", "signal", "depth", "x", "distorted", "rel_resid",
                 "overload", "calibrated", "freq", "status")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))

    def as_dict(self):
        return {k: getattr(self, k) for k in self.__slots__}


class Locator:
    """Feeds blocks to a lock-in and turns its output into an Estimate."""

    def __init__(self, freq, gains=None, rate=None, block=None):
        self.rate = rate or config.SAMPLE_RATE
        self.block = block or config.BLOCK
        self.freq = freq
        self.tracker = Tracker(self.rate, freq, config.CHANNELS, config.TAU,
                               self.block, config.NOISE_OFFSET_HZ, config.NOISE_OFFSET_ALT_HZ)
        self.gains = None if gains is None else np.asarray(gains, float)
        self.overload_until = 0.0

    def feed(self, x):
        self.tracker.feed(x)
        if self.tracker.peak >= config.CLIP_LEVEL:
            self.overload_until = time.monotonic() + 1.0

    def estimate(self):
        t = self.tracker
        overload = time.monotonic() < self.overload_until
        if t.s is None:
            return Estimate(status="starting", overload=overload, freq=self.freq,
                            calibrated=self.gains is not None)
        snr = t.snr_db(0)
        signal = float(abs(t.s[0]))
        e = Estimate(snr_db=snr, signal=signal, overload=overload, freq=self.freq,
                     calibrated=self.gains is not None, distorted=False)
        if overload:
            e.status = "overload"
            return e
        if snr < config.MIN_SNR_DB:
            e.status = "weak"
            return e
        if self.gains is None:
            e.status = "uncalibrated"
            return e
        u = t.s / self.gains
        sig = t.sigma() / np.abs(self.gains)
        fit = solve(u, sig)
        e.rel_resid = fit["rel_resid"]
        e.distorted = is_distorted(fit)
        e.status = "distorted" if e.distorted else "ok"
        # a best fit pinned against the far edges of the search area isn't an
        # answer (the near edge, depth 0, is: a wire lying on the ground)
        d1 = config.SEARCH_DEPTH[1]
        x0, x1 = config.SEARCH_X
        if fit["depth"] > d1 - 0.02 or not (x0 + 0.02 < fit["x"] < x1 - 0.02):
            return e
        e.depth = fit["depth"] - config.TIP_HEIGHT
        e.x = fit["x"]
        return e


# ------------------------------------------------------------------ units --
def fmt_depth(m, units=None):
    units = units or config.UNITS
    if m is None or not math.isfinite(m):
        return "--"
    if units == "metric":
        return "%.2f m" % m
    inches = int(round(m / 0.0254))
    return "%d' %d\"" % (inches // 12, inches % 12)


def fmt_offset(m, units=None):
    """'ON LINE', '< 7 in' (line is to your left) or '9 in >'."""
    units = units or config.UNITS
    if m is None or not math.isfinite(m):
        return ""
    if abs(m) < 0.05:
        return "ON LINE"
    if units == "metric":
        mag = "%d cm" % round(abs(m) * 100)
    else:
        inches = abs(m) / 0.0254
        mag = ("%d in" % round(inches)) if inches < 36 else fmt_depth(abs(m), units)
    return ("< " + mag) if m < 0 else (mag + " >")
