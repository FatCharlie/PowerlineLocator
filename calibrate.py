#!/usr/bin/env python3
"""Calibrate the four coils against a straight wire on the ground.

Depth comes from the ratio of the bottom and top coil readings, so the coils'
gains must match to about 1 %. No two hand-wound coils do, and the interface's
four preamps differ too. This measures each channel's gain (and sign) relative
to the bottom horizontal coil, once per frequency, and saves cal.json.

Setup (for_dummies.md, Part 9, has pictures):
  * Lay at least 20 m (65 ft) of wire dead straight on bare ground, away from
    fences, vehicles and buried lines.
  * Far end of the wire: clip to a ground stake. Near end: transmitter RED.
    Transmitter BLACK: a second stake 2 to 3 m off to the side of the near end.
  * Stand at the middle of the wire, facing along it, board face toward you.
  * Put marks on the ground 20 in and 31.5 in (0.5 m and 0.8 m) either side.

    python3 calibrate.py               # all three: 8 kHz, 33 kHz, 90 Hz
    python3 calibrate.py --only 8192
    python3 calibrate.py --sim         # rehearse with simulated coils

Stop the boot service first, or it will be holding the interface:
    sudo systemctl stop powerline-locator
If the Pi is locked read-only (lockdown.sh on), unlock it first or the result
vanishes at the next reboot.
"""
import argparse
import datetime
import sys

import numpy as np

from locator import config
from locator.geometry import fit_gains
from locator.lockin import Tracker, coherent_average
from locator.pipeline import lock_frequency, save_cal

TX_NAMES = {"8192": "8 kHz (green LED)", "32768": "33 kHz (yellow LED)",
            "90": "90 Hz CAL (red LED)"}


def say_position(x):
    side = "RIGHT" if x > 0 else "LEFT"
    inches = abs(x) / 0.0254
    return "the wire %.1f in (%.2f m) to your %s" % (inches, abs(x), side)


def measure(src, tracker, seconds):
    """Coherent average over `seconds`: signed amplitudes with bottom H > 0."""
    blocks = max(2, int(round(seconds * src.rate / src.block)))
    P = []
    for _ in range(blocks):
        tracker.feed(src.read())
        P.append(tracker.last_p)
    s, snr = coherent_average(P)
    if s[0] < 0:            # sign convention: bottom H positive
        s = -s
    return s, snr


def calibrate_one(key, args):
    freq = config.CAL_FREQS[key]
    if args.sim:
        from locator.sim import SimSource
        pos = {"x": 0.0}
        src = SimSource(freq=freq, lines=[(0.0, -config.CAL_WIRE_Y, 1.0)],
                        staff_x=lambda t: -pos["x"], gains=(1.0, -0.93, 1.06, 0.97),
                        noise=2e-6, amplitude=0.002, freq_error=1.3 if freq > 100 else 0.0)
    else:
        from locator.audio import AlsaSource
        input("\nSet the transmitter to %s, HIGH level, and press Enter..." % TX_NAMES[key])
        src = AlsaSource()
    span = 0.0 if freq < 100 else 60.0
    found, contrast = lock_frequency(src, freq, span, seconds=1.0)
    print("  locked to %.2f Hz" % found)
    tracker = Tracker(src.rate, found, config.CHANNELS, config.TAU, src.block,
                      config.NOISE_OFFSET_HZ, config.NOISE_OFFSET_ALT_HZ)
    rows = []
    for x in config.CAL_POSITIONS:
        if args.sim:
            pos["x"] = x
        else:
            input("  Stand the staff upright, tip on the ground, with %s. Enter..." % say_position(x))
        measure(src, tracker, config.CAL_SETTLE_S)
        s, snr = measure(src, tracker, config.CAL_AVERAGE_S)
        flag = "" if snr >= config.CAL_MIN_SNR_DB else "   <- weak: check the transmitter and stakes"
        print("    %-34s signal %5.1f dB%s" % (say_position(x), snr, flag))
        rows.append(s)
    src.close()

    gains, err = fit_gains(config.CAL_POSITIONS, np.array(rows))
    print("\n  %-10s %10s %10s" % ("coil", "gain", "fit error"))
    bad = False
    for c, g, e in zip(config.COILS, gains, err):
        warn = ""
        if e > config.CAL_MAX_FIT_ERR:
            warn, bad = "  <- high", True
        print("  %-10s %10.4f %9.1f %%%s" % (c["name"], g, 100 * e, warn))
    if bad:
        print("\n  A high fit error means that coil's readings didn't follow the shape of a\n"
              "  single straight wire. Usual causes: a position mark off by more than an\n"
              "  inch, metal nearby, the wire not straight, or a coil loose on the board.")
    entry = {"gains": [float(g) for g in gains], "fit_err": [float(e) for e in err],
             "freq_found": found, "date": datetime.datetime.now().isoformat(timespec="seconds")}
    if args.dry_run:
        print("  (dry run: not saved)")
    else:
        save_cal(key, entry)
        print("  saved to %s as '%s'" % (config.CAL_FILE, key))
    return not bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", choices=list(config.CAL_FREQS), action="append")
    ap.add_argument("--sim", action="store_true", help="simulated coils and wire")
    ap.add_argument("--dry-run", action="store_true", help="don't write cal.json")
    args = ap.parse_args()
    if args.sim and not args.dry_run:
        args.dry_run = True
    ok = True
    for key in args.only or list(config.CAL_FREQS):
        print("\n=== %s ===" % TX_NAMES[key])
        ok &= calibrate_one(key, args)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
