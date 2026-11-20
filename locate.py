#!/usr/bin/env python3
"""The locator itself: listens to the four coils and shows depth and direction.

    python3 locate.py                    # real hardware (the boot service runs this)
    python3 locate.py --sim              # no hardware: a line 5 ft down, staff sweeping
    python3 locate.py --sim --sim-depth 1.2 --sim-second 0.8
    python3 locate.py --mode 33k --no-screen

MODE button: 8 kHz -> 33 kHz -> 60 Hz power -> 8 kHz ...
SOUND button: buzzer on/off.
"""
import argparse
import signal
import sys
import time

from locator import config
from locator.controls import Controls, pitch_for
from locator.pipeline import Locator, load_cal, lock_frequency


def build_source(args, mode):
    if not args.sim:
        from locator.audio import AlsaSource
        return AlsaSource()
    from locator.sim import SimSource, walking
    lines = [(0.0, args.sim_depth, 1.0)]
    if args.sim_second:
        # a shallow line off to the side carrying current back the other way
        lines.append((args.sim_second, 0.5, -0.5))
    power = mode["key"] == "power"
    # a Pico transmitter lands a few Hz off nominal; the grid is right on 60
    return SimSource(freq=mode["freq"], lines=lines, staff_x=walking(),
                     freq_error=0.0 if power else 2.6, realtime=True,
                     hum=0.0 if power else 0.01)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=[m["key"] for m in config.MODES], default="8k")
    ap.add_argument("--sim", action="store_true", help="simulated coils, no hardware")
    ap.add_argument("--sim-depth", type=float, default=1.5, help="simulated depth, m")
    ap.add_argument("--sim-second", type=float, default=0.0,
                    help="add a shallow return line this far to the side, m (shows DISTORTED)")
    ap.add_argument("--no-screen", action="store_true", help="print to the terminal instead")
    ap.add_argument("--quiet", action="store_true", help="start with the buzzer off")
    ap.add_argument("--seconds", type=float, default=0, help="stop after this long (0 = run forever)")
    args = ap.parse_args()

    modes = config.MODES
    mi = [m["key"] for m in modes].index(args.mode)
    cal = load_cal()
    if args.sim:
        sim_gains = [1.0, -0.93, 1.06, 0.97]
        cal = {m["cal_key"]: {"gains": sim_gains} for m in modes}

    screen = sharp = None
    if not args.no_screen and not args.sim:
        try:
            from locator.display import Screen, SharpDisplay
            screen, sharp = Screen(), SharpDisplay()
        except Exception as e:
            print("screen unavailable (%s); using the terminal" % e, file=sys.stderr)
    from locator.display import TerminalDisplay
    term = TerminalDisplay()
    controls = Controls(enabled=not args.sim)
    sound = not args.quiet

    stop = {"now": False}
    signal.signal(signal.SIGTERM, lambda *a: stop.update(now=True))

    def start_mode(i):
        m = modes[i]
        src = build_source(args, m)
        if screen:
            from locator.pipeline import Estimate
            sharp.show(screen.render(Estimate(status="starting"), m["label"], sound,
                                     "finding the frequency"))
        freq, _ = lock_frequency(src, m["freq"], m["search"])
        gains = (cal.get(m["cal_key"]) or {}).get("gains")
        return src, Locator(freq, gains, src.rate, src.block)

    src, loc = start_mode(mi)
    every = max(1, int(round(src.rate / src.block / config.UPDATE_HZ)))
    chirp_every = max(1, int(round(src.rate / src.block / 5)))
    n = 0
    t_end = time.monotonic() + args.seconds if args.seconds else None
    est = None
    try:
        while not stop["now"]:
            loc.feed(src.read())
            n += 1
            if controls.take_sound():
                sound = not sound
            if controls.take_mode():
                src.close()
                mi = (mi + 1) % len(modes)
                src, loc = start_mode(mi)
                n = 0
                continue
            if n % every == 0:
                est = loc.estimate()
                label = modes[mi]["label"]
                if sharp:
                    sharp.show(screen.render(est, label, sound))
                else:
                    term.show_estimate(est, label, sound)
            # chirp: one block on, the rest off; double chirp when on the line
            if sound and est is not None and est.snr_db is not None:
                ph = n % chirp_every
                on_line = est.status == "ok" and est.x is not None and abs(est.x) < 0.05
                beep = ph == 0 or (on_line and ph == 2)
                controls.tone(pitch_for(est.snr_db) if beep else 0)
            else:
                controls.tone(0)
            if t_end and time.monotonic() > t_end:
                break
    except KeyboardInterrupt:
        pass
    finally:
        controls.close()
        src.close()
        print()


if __name__ == "__main__":
    main()
