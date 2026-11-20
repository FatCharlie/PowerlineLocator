"""Sharp Memory LCD (Adafruit 4694, 2.7" 400x240) and the screen layout.

Why this screen: it's reflective, like e-paper, so it gets *easier* to read
in full New Mexico sun, while a backlit LCD washes out. It also refreshes fast
enough for a live meter and draws almost no power.

Protocol, as the display wants it (first bit on the wire first):
    command byte : M0 = 1 (write line), M1 = VCOM, M2 = 0
    for each line: address (1..240, least significant bit first),
                   50 data bytes (first bit = leftmost pixel, 1 = white),
                   8 dummy bits
    8 more dummy bits at the end
The Pi's SPI only sends most-significant-bit first, so the command is 0x80
(plus 0x40 for VCOM) and the line address is bit-reversed. Pillow's 1-bit
images already put the leftmost pixel in the top bit, so data goes as-is.
VCOM must flip at least once a second or the panel slowly fades; every frame
flips it. CS is active HIGH on this panel, so it's driven from a plain GPIO.
"""
import os

from . import config

FONT_DIRS = ("/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/dejavu",
             "/usr/share/fonts/TTF")


def reverse_bits(b):
    b = ((b & 0xF0) >> 4) | ((b & 0x0F) << 4)
    b = ((b & 0xCC) >> 2) | ((b & 0x33) << 2)
    return ((b & 0xAA) >> 1) | ((b & 0x55) << 1)


def build_frame(data, width, height, vcom):
    """Bytes to send for a full-screen update. data: height * width/8 bytes."""
    line_len = width // 8
    out = bytearray([0x80 | (0x40 if vcom else 0)])
    for line in range(height):
        out.append(reverse_bits(line + 1))
        out += data[line * line_len:(line + 1) * line_len]
        out.append(0)
    out.append(0)
    return bytes(out)


def _font(size, bold=True):
    try:
        from PIL import ImageFont
    except ImportError:
        return None
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for d in FONT_DIRS:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


class SharpDisplay:
    def __init__(self):
        import spidev
        from gpiozero import DigitalOutputDevice
        self.spi = spidev.SpiDev()
        self.spi.open(config.SPI_BUS, config.SPI_DEV)
        self.spi.max_speed_hz = config.SPI_HZ
        self.spi.mode = 0
        self.cs = DigitalOutputDevice(config.DISPLAY_CS_GPIO, active_high=True,
                                      initial_value=False)
        self.vcom = False

    def show(self, img):
        from PIL import ImageOps
        if config.DISPLAY_MIRROR:
            img = ImageOps.mirror(img)
        if config.DISPLAY_INVERT:
            img = ImageOps.invert(img.convert("L")).convert("1")
        self.vcom = not self.vcom
        frame = build_frame(img.tobytes(), config.DISPLAY_W, config.DISPLAY_H, self.vcom)
        self.cs.on()
        try:
            for i in range(0, len(frame), 4096):
                self.spi.writebytes2(frame[i:i + 4096])
        finally:
            self.cs.off()

    def close(self):
        try:
            self.spi.close()
            self.cs.close()
        except Exception:
            pass


class Screen:
    """Lays out one Estimate on a 400 x 240 1-bit image."""

    def __init__(self):
        from PIL import Image, ImageDraw  # noqa: F401  (fail early if missing)
        self.f_small = _font(22)
        self.f_mid = _font(34)
        self.f_big = _font(76)

    def render(self, est, mode_label, sound_on, extra=""):
        from PIL import Image, ImageDraw
        from .pipeline import fmt_depth, fmt_offset
        W, H = config.DISPLAY_W, config.DISPLAY_H
        img = Image.new("1", (W, H), 1)
        d = ImageDraw.Draw(img)

        # top bar: mode on the left, sound on the right, inverted
        d.rectangle([0, 0, W, 30], fill=0)
        d.text((8, 3), mode_label, font=self.f_small, fill=1)
        snd = "SOUND ON" if sound_on else "SOUND OFF"
        tw = d.textlength(snd, font=self.f_small)
        d.text((W - tw - 8, 3), snd, font=self.f_small, fill=1)

        # signal bar: 0 to 60 dB above the noise
        snr = est.snr_db if (est.snr_db is not None and est.snr_db > -1e9) else 0.0
        frac = max(0.0, min(1.0, snr / 60.0))
        d.rectangle([8, 40, W - 8, 62], outline=0, width=2)
        d.rectangle([10, 42, 10 + int((W - 20) * frac), 60], fill=0)
        d.text((8, 64), "signal %d dB" % round(snr), font=self.f_small, fill=0)

        status = est.status or ""
        if status in ("ok", "distorted"):
            depth = fmt_depth(est.depth)
            if status == "distorted" and est.depth is not None:
                depth = "(" + depth + ")"
            tw = d.textlength(depth, font=self.f_big)
            d.text(((W - tw) / 2, 86), depth, font=self.f_big, fill=0)
            off = fmt_offset(est.x)
            tw = d.textlength(off, font=self.f_mid)
            d.text(((W - tw) / 2, 166), off, font=self.f_mid, fill=0)
        else:
            msg = {"weak": "WEAK SIGNAL", "overload": "OVERLOAD",
                   "uncalibrated": "NOT CALIBRATED", "starting": "STARTING"}.get(status, status.upper())
            tw = d.textlength(msg, font=self.f_mid)
            d.text(((W - tw) / 2, 110), msg, font=self.f_mid, fill=0)
            hint = {"weak": "move closer / check transmitter",
                    "overload": "move away from wiring",
                    "uncalibrated": "run calibrate.py"}.get(status, extra)
            if hint:
                tw = d.textlength(hint, font=self.f_small)
                d.text(((W - tw) / 2, 160), hint, font=self.f_small, fill=0)

        if status == "distorted":
            d.rectangle([0, H - 30, W, H], fill=0)
            msg = "DISTORTED - depth unreliable"
            tw = d.textlength(msg, font=self.f_small)
            d.text(((W - tw) / 2, H - 27), msg, font=self.f_small, fill=1)
        return img


class TerminalDisplay:
    """Fallback when there's no screen: one line, rewritten in place."""

    def show_estimate(self, est, mode_label, sound_on):
        from .pipeline import fmt_depth, fmt_offset
        snr = est.snr_db if (est.snr_db is not None and est.snr_db > -1e9) else 0.0
        bar = "#" * int(max(0, min(30, snr / 2)))
        parts = ["%-12s" % mode_label, "%-30s" % bar, "%5.1f dB" % snr]
        if est.status in ("ok", "distorted"):
            parts += ["depth %-8s" % fmt_depth(est.depth), "%-10s" % fmt_offset(est.x)]
            if est.distorted:
                parts.append("DISTORTED")
        else:
            parts.append((est.status or "").upper())
        print("\r" + "  ".join(parts) + " " * 10, end="", flush=True)
