"""Software lock-in amplifier for four coil channels.

For each 50 ms block of samples x_c(t) the lock-in computes the phasor

    P_c = (2/N) * sum_t x_c(t) * exp(-i 2 pi f t)

which is the amplitude and phase of channel c at frequency f. Everything else
(other frequencies, 60 Hz hum in active mode, random noise) averages towards
zero. A second lock-in at f + NOISE_OFFSET_HZ, where there's no signal,
measures the noise floor in the same bandwidth.

The four phasors share one time base (one ADC clock), so their relative
phases are real physics: the vertical coil is either in phase with the
horizontal one (line on one side) or 180 degrees out (line on the other).
`Tracker` projects each block onto the strongest channel's phase to get
signed real amplitudes, then smooths those.
"""
import math

import numpy as np


def phasors(x, n0, fs, freq):
    """Phasor per channel. x: (N, C) floats; n0: index of x[0] in the stream."""
    n = x.shape[0]
    # phase in cycles, kept small so float64 stays exact for days
    start = math.fmod(n0 * freq / fs, 1.0)
    cyc = start + np.arange(n) * (freq / fs)
    ref = np.exp(-2j * np.pi * cyc)
    return 2.0 * (x * ref[:, None]).mean(axis=0)


def find_frequency(x, fs, nominal, span):
    """Strongest frequency within nominal +/- span, from a long capture x (N, C).

    Returns (freq, peak_to_median). Parabolic interpolation on the log power
    spectrum gets well under one bin. With span 0 it just returns nominal.
    """
    if span <= 0:
        return nominal, float("nan")
    n = x.shape[0]
    win = np.hanning(n)[:, None]
    spec = (np.abs(np.fft.rfft(x * win, axis=0)) ** 2).sum(axis=1)
    freqs = np.fft.rfftfreq(n, 1.0 / fs)
    lo, hi = np.searchsorted(freqs, [nominal - span, nominal + span])
    lo, hi = max(lo, 1), min(hi, len(freqs) - 2)
    if hi <= lo:
        return nominal, float("nan")
    k = lo + int(np.argmax(spec[lo:hi + 1]))
    a, b, c = np.log(spec[k - 1:k + 2] + 1e-300)
    denom = a - 2 * b + c
    delta = 0.5 * (a - c) / denom if denom != 0 else 0.0
    delta = max(-0.5, min(0.5, delta))
    contrast = spec[k] / (np.median(spec[lo:hi + 1]) + 1e-300)
    return float(freqs[k] + delta * fs / n), float(contrast)


def noise_frequency(freq, offset=40.0, alt=60.0):
    """A quiet frequency near freq: offset above it, or alt if that lands
    within 15 Hz of a 60 Hz mains harmonic."""
    f = freq + offset
    if abs(f - 60.0 * round(f / 60.0)) < 15.0:
        f = freq + alt
    return f


class Tracker:
    """Signed, smoothed amplitudes and noise for every channel."""

    def __init__(self, fs, freq, channels=4, tau=0.4, block=4800, noise_offset=40.0,
                 noise_alt=60.0):
        self.fs, self.freq = fs, freq
        self.noise_freq = noise_frequency(freq, noise_offset, noise_alt)
        self.alpha = 1.0 - math.exp(-(block / fs) / tau)
        self.n = 0
        self.s = None                       # smoothed signed amplitudes
        self.noise2 = np.zeros(channels)    # smoothed |noise phasor|^2
        self.peak = 0.0                     # largest |sample| in the last block
        self.last_p = None                  # raw phasors of the last block

    def feed(self, x):
        p = phasors(x, self.n, self.fs, self.freq)
        q = phasors(x, self.n, self.fs, self.noise_freq)
        self.n += x.shape[0]
        self.peak = float(np.max(np.abs(x))) if x.size else 0.0
        self.last_p = p
        ref = int(np.argmax(np.abs(p)))
        mag = abs(p[ref])
        s = (p * np.conj(p[ref])).real / mag if mag > 0 else np.zeros(len(p))
        if self.s is None:
            self.s = s
            self.noise2 = np.abs(q) ** 2
            return
        # keep one global sign from block to block, or smoothing would cancel
        if float(np.dot(s, self.s)) < 0:
            s = -s
        a = self.alpha
        self.s = self.s + a * (s - self.s)
        self.noise2 = self.noise2 + a * (np.abs(q) ** 2 - self.noise2)

    def sigma(self):
        """1-sigma noise of each smoothed signed amplitude."""
        a = self.alpha
        # E|q|^2 splits evenly between the real and imaginary parts; the
        # exponential smoother then cuts the variance by a / (2 - a).
        return np.sqrt(self.noise2 / 2.0 * a / (2.0 - a)) + 1e-15

    def snr_db(self, ch=0):
        if self.s is None:
            return float("-inf")
        return 20.0 * math.log10(abs(self.s[ch]) / self.sigma()[ch] + 1e-30)


def coherent_average(P):
    """Signed amplitudes from many blocks of phasors P (B, C), for calibration.

    Averaging complex phasors over seconds rejects anything more than a
    fraction of a hertz away (60 Hz hum next to a 90 Hz tone, for example)
    far better than smoothing block-by-block amplitudes. The catch is that the
    transmitter's frequency is only known to about 0.1 Hz, which would smear
    the phase over a few seconds; so first fit a straight line to the
    strongest channel's phase and take that drift out of every channel.
    Returns (signed (C,), snr_db of the strongest channel).
    """
    P = np.asarray(P)
    ref = int(np.argmax(np.abs(P).mean(axis=0)))
    phase = np.unwrap(np.angle(P[:, ref]))
    b = np.arange(len(phase))
    slope, icept = np.polyfit(b, phase, 1) if len(b) > 1 else (0.0, phase[0])
    D = P * np.exp(-1j * (slope * b + icept))[:, None]
    mean = D.mean(axis=0)
    signed = mean.real
    spread = np.std(D[:, ref].real) / math.sqrt(len(b)) + 1e-30
    return signed, 20.0 * math.log10(abs(signed[ref]) / spread)
