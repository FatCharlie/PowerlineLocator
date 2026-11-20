#!/usr/bin/env python3
"""Hardware check: tests each part of the receiver and says what's ready.

    python3 check_hw.py                  # everything that needs no help
    python3 check_hw.py --interactive    # also buttons, buzzer and screen (you watch)
    python3 check_hw.py --only audio     # one section: pi, packages, audio, display, controls, cal
    python3 check_hw.py --live           # live level of each coil at 60 Hz (Ctrl-C to stop)
    python3 check_hw.py --live --freq 8192

--live is the coil test: hold each coil near a lamp cord with the lamp ON and
its bar should jump. Stop the boot service first:
    sudo systemctl stop powerline-locator
Exits non-zero if anything failed.
"""
import argparse
import importlib
import math
import os
import sys
import time

from locator import config

RESULTS = []


def report(section, item, ok, detail, fix=""):
    RESULTS.append((section, item, ok, detail, fix))
    mark = {True: "PASS", False: "FAIL", None: "INFO"}[ok]
    print("  [%s] %-22s %s" % (mark, item, detail))
    if fix and ok is False:
        print("         fix: %s" % fix)


def check_pi():
    print("\nPi")
    try:
        model = open("/proc/device-tree/model").read().strip("\x00\n")
        report("pi", "board", True, model)
    except OSError:
        report("pi", "board", False, "not a Raspberry Pi?", "run this on the Pi")
    spi = "/dev/spidev%d.%d" % (config.SPI_BUS, config.SPI_DEV)
    report("pi", "SPI", os.path.exists(spi), spi,
           "sudo raspi-config nonint do_spi 0 && sudo reboot")
    groups = os.popen("id -Gn").read().split()
    for g in ("spi", "gpio", "audio"):
        report("pi", "group " + g, g in groups, "you are%s in it" % ("" if g in groups else " not"),
               "sudo usermod -aG %s $USER, then log out and in" % g)


def check_packages():
    print("\nPackages")
    for mod, pkg in (("numpy", "python3-numpy"), ("alsaaudio", "python3-alsaaudio"),
                     ("spidev", "python3-spidev"), ("gpiozero", "python3-gpiozero"),
                     ("PIL", "python3-pil")):
        try:
            importlib.import_module(mod)
            report("packages", mod, True, "installed")
        except ImportError:
            report("packages", mod, False, "missing", "sudo apt install " + pkg)


def check_audio():
    print("\nAudio interface (UMC404HD)")
    try:
        from locator.audio import AlsaSource, card_streams, find_card
        card = find_card()
        report("audio", "found", True, "ALSA card '%s'" % card)
    except Exception as e:
        report("audio", "found", False, str(e), "plug in its USB cable; check its power light")
        return
    streams = card_streams()
    if streams:
        cap = streams.split("Capture:")[-1] if "Capture:" in streams else ""
        has_rate = str(config.SAMPLE_RATE) in cap
        has_ch = "Channels: %d" % config.CHANNELS in cap
        report("audio", "96 kHz capture", has_rate, "offered" if has_rate else "not offered",
               "this interface can't do 96 kHz; 33 kHz mode needs it")
        report("audio", "4-channel capture", has_ch, "offered" if has_ch else "not offered",
               "check it's a UMC404HD, not a 2-input model")
    try:
        import numpy as np
        src = AlsaSource()
        x = np.vstack([src.read() for _ in range(20)])     # 1 s
        src.close()
    except Exception as e:
        report("audio", "capture", False, str(e))
        return
    report("audio", "capture", True, "1 s of %d x %d samples" % x.shape)
    from locator.lockin import phasors
    for c in config.COILS:
        col = x[:, c["ch"]]
        rms = float(np.sqrt(np.mean(col ** 2)))
        hum = abs(phasors(col[:, None], 0, config.SAMPLE_RATE, 60.0)[0])
        peak = float(np.max(np.abs(col)))
        dead = rms < 1e-7
        clip = peak >= config.CLIP_LEVEL
        detail = "input %d: rms %.1e, 60 Hz %.1e%s" % (c["ch"] + 1, rms, hum, "  CLIPPING" if clip else "")
        report("audio", c["name"], not (dead or clip), detail,
               "dead: check the XLR plug, gain knob and coil leads" if dead
               else "clipping: is +48V phantom ON? (switch on the back: OFF)")


def check_display(interactive):
    print("\nDisplay")
    try:
        from PIL import ImageDraw
        from locator.display import Screen, SharpDisplay
        d = SharpDisplay()
        img = Screen().render(_fake_estimate(), "SCREEN TEST", True)
        ImageDraw.Draw(img).rectangle([0, 0, config.DISPLAY_W - 1, config.DISPLAY_H - 1], outline=0, width=3)
        d.show(img)
        report("display", "sent a frame", True, "a test screen with 4' 7\" and a border")
    except Exception as e:
        report("display", "sent a frame", False, str(e), "check SPI is on and the wiring (for_dummies.md, Step 6)")
        return
    if interactive:
        ans = input("  Does the screen show '4' 7\"' the right way round, black on grey? [y/n/m=mirrored] ")
        report("display", "looks right", ans.lower().startswith("y"), ans,
               "mirrored: set DISPLAY_MIRROR = True in locator/config.py; blank: wire DISP to 3V3")
    else:
        report("display", "looks right", None, "can't tell from here; use --interactive")


def _fake_estimate():
    from locator.pipeline import Estimate
    return Estimate(status="ok", snr_db=42.0, depth=4 * 0.3048 + 7 * 0.0254, x=-0.18, distorted=False)


def check_controls(interactive):
    print("\nButtons and buzzer")
    from locator.controls import Controls
    c = Controls()
    if not c.ok:
        report("controls", "GPIO", False, getattr(c, "error", "unavailable"), "sudo apt install python3-gpiozero python3-lgpio")
        return
    report("controls", "GPIO", True, "buttons on GPIO%d/%d, buzzer on GPIO%d"
           % (config.BTN_MODE_GPIO, config.BTN_SOUND_GPIO, config.BUZZER_GPIO))
    if not interactive:
        report("controls", "press test", None, "use --interactive")
        return
    for f in (500, 1000, 2000):
        c.tone(f)
        time.sleep(0.25)
    c.tone(0)
    ans = input("  Did you hear three rising beeps? [y/n] ")
    report("controls", "buzzer", ans.lower().startswith("y"), ans, "check the piezo's + leg goes to the 100 ohm resistor")
    for name, take in (("MODE", c.take_mode), ("SOUND", c.take_sound)):
        take()
        print("  Press %s within 10 s..." % name, flush=True)
        t = time.time()
        got = False
        while time.time() - t < 10:
            if take():
                got = True
                break
            time.sleep(0.05)
        report("controls", name + " button", got, "pressed" if got else "nothing", "check its two wires: GPIO pin and GND")
    c.close()


def check_cal():
    print("\nCalibration")
    from locator.pipeline import load_cal
    cal = load_cal()
    for key, name, stage in (("90", "power (90 Hz cal)", 1), ("8192", "8 kHz", 2), ("32768", "33 kHz", 2)):
        e = cal.get(key)
        if e:
            worst = max(e.get("fit_err", [0])) * 100
            report("cal", name, worst <= config.CAL_MAX_FIT_ERR * 100,
                   "%s, worst fit error %.1f %%" % (e.get("date", "?"), worst), "re-run calibrate.py --only " + key)
        elif stage == 1:
            report("cal", name, False, "not calibrated", "python3 calibrate.py --only " + key)
        else:
            report("cal", name, None, "not calibrated (only needed with the transmitter, Stage 2)")


def live(freq):
    import numpy as np
    from locator.audio import AlsaSource
    from locator.lockin import phasors
    src = AlsaSource()
    n0 = 0
    print("Live level at %.0f Hz on each input (Ctrl-C to stop)\n" % freq)
    try:
        while True:
            x = np.vstack([src.read() for _ in range(4)])
            p = np.abs(phasors(x, n0, src.rate, freq))
            n0 += x.shape[0]
            bars = []
            for c in config.COILS:
                db = 20 * math.log10(p[c["ch"]] + 1e-12) + 120
                bars.append("%d %-8s %-24s" % (c["ch"] + 1, c["name"], "#" * int(max(0, min(24, db / 4)))))
            print("\r" + " | ".join(bars), end="", flush=True)
    except KeyboardInterrupt:
        print()
    finally:
        src.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", action="append",
                    choices=["pi", "packages", "audio", "display", "controls", "cal"])
    ap.add_argument("--interactive", action="store_true")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--freq", type=float, default=60.0)
    args = ap.parse_args()
    if args.live:
        live(args.freq)
        return
    want = args.only or ["pi", "packages", "audio", "display", "controls", "cal"]
    if "pi" in want:
        check_pi()
    if "packages" in want:
        check_packages()
    if "audio" in want:
        check_audio()
    if "display" in want:
        check_display(args.interactive)
    if "controls" in want:
        check_controls(args.interactive)
    if "cal" in want:
        check_cal()
    failed = [r for r in RESULTS if r[2] is False]
    print("\n%d checks, %d failed" % (len(RESULTS), len(failed)))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
