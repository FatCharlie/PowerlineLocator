#!/usr/bin/env python3
"""Calibrate the four coils against a wire on the ground.

Depth comes from the ratio of the bottom and top coil readings, so the coils'
gains must match to about 1 %. No two hand-wound coils do, and the interface's
four preamps differ too. This measures each channel's gain (and sign) relative
to the bottom horizontal coil, once per frequency, and saves cal.json.

Two ways to make the calibration field (for_dummies.md, Parts 5 and 6, and
SCHEMATICS.md section 8 have pictures):

  loop (default, Stage 1: no transmitter needed)
    * Lay a 9 m x 5 m (29.5 x 16.4 ft) rectangle of wire flat on bare ground,
      away from fences, vehicles and buried lines. Corners square.
    * Its two ends go, through a 47 ohm resistor, to a TRS cable plugged into
      the interface's MAIN L output. MIX knob fully to PLAYBACK, MAIN knob
      at about 3 o'clock.
    * Stand at the middle of one long side, facing along it, with the rest of
      the loop to your LEFT. Board face toward you.
    * Put marks 20 in and 31.5 in (0.5 m and 0.8 m) either side of that side.
    The script plays the tone itself.

  transmitter (Stage 2)
    * 20 m (65 ft) or more of wire dead straight on the ground. Far end to a
      ground stake; near end to transmitter RED; BLACK to a second stake 2 to
      3 m off to the side. Same marks, either side of the middle.

    python3 calibrate.py                     # loop: 90 Hz, 8 kHz and 33 kHz
    python3 calibrate.py --only 90           # just power mode
    python3 calibrate.py --source transmitter
    python3 calibrate.py --sim               # rehearse with simulated coils

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
from locator.geometry import fit_gains, line_model, loop_model
from locator.lockin import Tracker, coherent_average
from locator.pipeline import lock_frequency, save_cal

TX_NAMES = {"8192": "8 kHz (green LED)", "32768": "33 kHz (yellow LED)",
            "90": "90 Hz CAL (red LED)"}
FREQ_NAMES = {"8192": "8 kHz", "32768": "33 kHz", "90": "90 Hz (for 60 Hz power mode)"}
ORDER = ["90", "8192", "32768"]      # power mode first: Stage 1 needs only that


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


def model_for(source):
    if source == "loop":
        return loop_model(config.CAL_POSITIONS)
    return line_model(config.CAL_POSITIONS)


def open_sim(source, freq):
    from locator.sim import SimSource
    pos = {"x": 0.0}
    if source == "loop":
        field = lambda t: loop_model([pos["x"]])[0]          # noqa: E731
        src = SimSource(freq=freq, field_fn=field, gains=(1.0, -0.93, 1.06, 0.97),
                        noise=2e-6, amplitude=0.002, hum=0.002)
    else:
        src = SimSource(freq=freq, lines=[(0.0, -config.CAL_WIRE_Y, 1.0)],
                        staff_x=lambda t: -pos["x"], gains=(1.0, -0.93, 1.06, 0.97),
                        noise=2e-6, amplitude=0.002, freq_error=1.3 if freq > 100 else 0.0)
    return src, pos


def calibrate_one(key, args):
    freq = config.CAL_FREQS[key]
    tone = None
    pos = None
    if args.sim:
        src, pos = open_sim(args.source, freq)
    else:
        from locator.audio import AlsaSource, ToneOut
        if args.source == "transmitter":
            input("\nSet the transmitter to %s, HIGH level, and press Enter..." % TX_NAMES[key])
        src = AlsaSource()
        if args.source == "loop":
            tone = ToneOut(freq)
    try:
        if args.source == "loop":
            found = freq             # same clock in and out: exact
        else:
            span = 0.0 if freq < 100 else 60.0
            found, _ = lock_frequency(src, freq, span, seconds=1.0)
        print("  at %.2f Hz" % found)
        tracker = Tracker(src.rate, found, config.CHANNELS, config.TAU, src.block,
                          config.NOISE_OFFSET_HZ, config.NOISE_OFFSET_ALT_HZ)
        rows, weak = [], False
        for x in config.CAL_POSITIONS:
            if args.sim:
                pos["x"] = x
            else:
                input("  Stand the staff upright, tip on the ground, with %s. Enter..." % say_position(x))
            measure(src, tracker, config.CAL_SETTLE_S)
            s, snr = measure(src, tracker, config.CAL_AVERAGE_S)
            if tracker.peak >= config.CLIP_LEVEL:
                print("    inputs are clipping: turn the interface's MAIN knob down and run again")
                return False
            flag = ""
            if snr < config.CAL_MIN_SNR_DB:
                weak = True
                flag = ("   <- weak: MAIN knob up? MIX at PLAYBACK? loop connected?" if args.source == "loop"
                        else "   <- weak: check the transmitter and stakes")
            print("    %-34s signal %5.1f dB%s" % (say_position(x), snr, flag))
            rows.append(s)
    finally:
        if tone:
            tone.stop()
        src.close()

    gains, err = fit_gains(config.CAL_POSITIONS, np.array(rows), model=model_for(args.source))
    print("\n  %-10s %10s %10s" % ("coil", "gain", "fit error"))
    bad = False
    for c, g, e in zip(config.COILS, gains, err):
        warn = ""
        if e > config.CAL_MAX_FIT_ERR:
            warn, bad = "  <- high", True
        print("  %-10s %10.4f %9.1f %%%s" % (c["name"], g, 100 * e, warn))
    if bad:
        print("\n  A high fit error means that coil's readings didn't match the field the wire\n"
              "  should make. Usual causes: a position mark off by more than an inch, the\n"
              "  staff tilted, metal nearby, the loop not square or not the size in\n"
              "  locator/config.py, or a coil loose on the board.")
    if weak and key == "32768" and args.source == "loop":
        print("\n  33 kHz is near the top of what the interface's output can make. If it stays\n"
              "  weak, calibrate 33 kHz with the transmitter later (Stage 2).")
    entry = {"gains": [float(g) for g in gains], "fit_err": [float(e) for e in err],
             "freq_found": found, "source": args.source,
             "date": datetime.datetime.now().isoformat(timespec="seconds")}
    if args.dry_run:
        print("  (dry run: not saved)")
    else:
        save_cal(key, entry)
        print("  saved to %s as '%s'" % (config.CAL_FILE, key))
    return not bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", choices=list(config.CAL_FREQS), action="append")
    ap.add_argument("--source", choices=["loop", "transmitter"], default=config.CAL_SOURCE)
    ap.add_argument("--sim", action="store_true", help="simulated coils and wire")
    ap.add_argument("--dry-run", action="store_true", help="don't write cal.json")
    args = ap.parse_args()
    if args.sim and not args.dry_run:
        args.dry_run = True
    if args.source == "loop" and not args.sim:
        print("Loop calibration. Check: MIX knob fully to PLAYBACK, MAIN knob at about 3 o'clock,\n"
              "the loop's TRS cable in MAIN L, and the rest of the loop on your LEFT.")
    ok = True
    for key in [k for k in ORDER if k in (args.only or ORDER)]:
        print("\n=== %s ===" % FREQ_NAMES[key])
        ok &= calibrate_one(key, args)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
