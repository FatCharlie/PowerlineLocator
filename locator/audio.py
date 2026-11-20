"""Four-channel capture from the USB audio interface, through ALSA.

The interface's mic preamps do the job of a custom low-noise amplifier: each
coil goes straight into an XLR input. We open the card through ALSA's "plug"
layer, which converts the card's native 24-bit samples to 32-bit integers for
us, and read 50 ms blocks as numpy arrays of floats in [-1, 1).
"""
import os

import numpy as np

from . import config


class AudioError(RuntimeError):
    pass


def find_card():
    """ALSA card id of the interface, e.g. 'U192k'. Raises AudioError."""
    try:
        import alsaaudio
    except ImportError as e:
        raise AudioError("python3-alsaaudio is not installed (sudo ./RPI_SETUP.sh)") from e
    cards = alsaaudio.cards()
    for hint in config.AUDIO_CARD_HINTS:
        for c in cards:
            if hint.lower() in c.lower():
                return c
    raise AudioError("no UMC404HD found; ALSA sees: " + (", ".join(cards) or "no cards")
                     + ". Is its USB cable in and its power light on?")


def device_name():
    return config.AUDIO_DEVICE or "plughw:CARD=%s,DEV=0" % find_card()


def card_streams():
    """Text of /proc/asound/<card>/stream0: the formats and rates it offers."""
    try:
        card = find_card()
    except AudioError:
        return ""
    path = "/proc/asound/%s/stream0" % card
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return ""


class AlsaSource:
    """Blocks of shape (BLOCK, 4), float64, from the interface."""

    def __init__(self, rate=None, block=None, channels=None):
        import alsaaudio
        self.rate = rate or config.SAMPLE_RATE
        self.block = block or config.BLOCK
        self.channels = channels or config.CHANNELS
        name = device_name()
        kw = dict(type=alsaaudio.PCM_CAPTURE, mode=alsaaudio.PCM_NORMAL,
                  device=name, channels=self.channels, rate=self.rate,
                  format=alsaaudio.PCM_FORMAT_S32_LE, periodsize=self.block)
        try:
            try:
                # periods= (a deeper buffer) arrived in pyalsaaudio 0.10
                self.pcm = alsaaudio.PCM(periods=16, **kw)
            except TypeError:
                self.pcm = alsaaudio.PCM(**kw)
        except alsaaudio.ALSAAudioError as e:
            msg = str(e)
            if "busy" in msg.lower():
                msg += (" (the locator service probably has it: "
                        "sudo systemctl stop powerline-locator)")
            raise AudioError("can't open %s: %s" % (name, msg)) from e
        got = getattr(self.pcm, "info", lambda: {})()
        rate = got.get("rate", self.rate) if isinstance(got, dict) else self.rate
        if rate != self.rate:
            raise AudioError("card runs at %s Hz, not %s" % (rate, self.rate))
        self._buf = np.zeros((0, self.channels))

    def read(self):
        while self._buf.shape[0] < self.block:
            n, data = self.pcm.read()
            if n < 0:          # overrun: we fell behind; drop and carry on
                continue
            if n == 0:
                continue
            a = np.frombuffer(data, dtype="<i4").reshape(-1, self.channels)
            self._buf = np.vstack([self._buf, a.astype(np.float64) / 2147483648.0])
        out, self._buf = self._buf[:self.block], self._buf[self.block:]
        return out

    def close(self):
        try:
            self.pcm.close()
        except Exception:
            pass


def open_source(sim=None):
    """The real interface, or a simulator if sim is a SimSource."""
    if sim is not None:
        return sim
    if os.environ.get("POWERLINE_SIM"):
        from .sim import SimSource
        return SimSource()
    return AlsaSource()
