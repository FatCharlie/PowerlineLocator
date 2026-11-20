#!/usr/bin/env python3
"""Checks the software with no hardware attached. Plain script, no test framework.

    python3 selftest.py          # all checks
    python3 selftest.py -v       # print every result, not just failures

Covers: the lock-in, the frequency finder, the depth solver across depths and
offsets, the distortion warning, the calibration fit, the whole pipeline on
simulated coils, the screen's bit order, unit formatting, and the
transmitter's timing maths (its MicroPython file imported with fakes).
"""
import importlib.util
import math
import os
import sys
import time

import numpy as np

from locator import config
from locator.geometry import coil_samples, fit_gains, is_distorted, response, solve
from locator.lockin import Tracker, find_frequency, phasors
from locator.pipeline import Locator, fmt_depth, fmt_offset, lock_frequency
from locator.sim import SimSource

VERBOSE = "-v" in sys.argv
PASSED, FAILED = [], []


def check(name, ok, detail=""):
    (PASSED if ok else FAILED).append(name)
    if VERBOSE or not ok:
        print("  %s  %-52s %s" % ("ok  " if ok else "FAIL", name, detail))


def section(title):
    print("\n" + title)


# ------------------------------------------------------------------ lock-in --
def test_lockin():
    section("Lock-in")
    # 8000 Hz makes a whole number of cycles per 50 ms block, so the 2f image
    # term cancels exactly and the comparisons below can be tight
    fs, f, n = 96000, 8000.0, 4800
    t = np.arange(n) / fs
    amps = np.array([0.3, -0.1, 0.2, 0.05])
    x = np.cos(2 * np.pi * f * t + 0.4)[:, None] * amps[None, :]
    x += 0.05 * np.cos(2 * np.pi * 60 * t)[:, None]          # hum
    p = phasors(x, 0, fs, f)
    check("amplitudes recovered", np.allclose(np.abs(p), np.abs(amps), rtol=2e-3),
          str(np.round(np.abs(p), 4)))
    rel = (p * np.conj(p[0])).real / abs(p[0])
    check("signs recovered", np.allclose(rel, amps, rtol=2e-3), str(np.round(rel, 4)))
    # continuity across blocks: same answer for the second block
    x1 = np.cos(2 * np.pi * f * t + 0.4)[:, None] * amps[None, :]
    x2 = np.cos(2 * np.pi * f * (t + n / fs) + 0.4)[:, None] * amps[None, :]
    check("phase continuous across blocks",
          np.allclose(phasors(x1, 0, fs, f), phasors(x2, n, fs, f), atol=1e-9))

    tr = Tracker(fs, f, 4, 0.4, n)
    rng = np.random.default_rng(0)
    for k in range(60):
        tt = (k * n + np.arange(n)) / fs
        xx = np.cos(2 * np.pi * f * tt + 0.4)[:, None] * amps[None, :] + rng.normal(0, 0.01, (n, 4))
        tr.feed(xx)
    s = tr.s * np.sign(tr.s[0])
    check("tracker signed amplitudes", np.allclose(s, amps, atol=3e-3), str(np.round(s, 4)))
    # noise: per-block real projection sd = 0.01 * sqrt(2/N); smoothed further
    sd_block = 0.01 * math.sqrt(2.0 / n)
    a = tr.alpha
    want = sd_block * math.sqrt(a / (2 - a))
    got = float(np.median(tr.sigma()))
    check("tracker noise estimate", 0.6 * want < got < 1.6 * want, "%.2e vs %.2e" % (got, want))


def test_frequency():
    section("Frequency finder")
    fs = 96000
    for f_true in (8194.6, 32765.4):
        n = fs
        t = np.arange(n) / fs
        x = np.cos(2 * np.pi * f_true * t)[:, None] * np.ones((1, 4)) * 0.01
        x += np.random.default_rng(1).normal(0, 0.01, x.shape)
        f, contrast = find_frequency(x, fs, round(f_true / 4096) * 4096.0, 60.0)
        check("finds %.1f Hz" % f_true, abs(f - f_true) < 0.15, "got %.3f, contrast %.0f" % (f, contrast))


# ------------------------------------------------------------------ solver --
def test_solver():
    section("Depth solver")
    pts, axes = coil_samples()
    worst = 0.0
    for depth in (0.4, 0.9, 1.5, 1.83, 2.5):
        for x in (-0.8, -0.2, 0.0, 0.3, 1.0):
            u = response(x, -depth, pts, axes) * 3.7
            fit = solve(u, np.full(4, 1e-9))
            err = max(abs(fit["depth"] - depth), abs(fit["x"] - x))
            worst = max(worst, err)
    check("exact data: depth and offset within 2 mm", worst < 0.002, "worst %.4f m" % worst)

    rng = np.random.default_rng(3)
    errs = []
    for depth in (0.9, 1.5, 1.83):
        u0 = response(0.15, -depth, pts, axes)
        sig = 0.003 * np.abs(u0[0]) * np.ones(4)       # 50 dB SNR on the bottom coil
        for _ in range(10):
            fit = solve(u0 + rng.normal(0, sig), sig)
            errs.append(abs(fit["depth"] - depth) / depth)
    check("50 dB SNR: depth within 10 % (worst of 30)", max(errs) < 0.10, "worst %.1f %%" % (100 * max(errs)))

    fit = solve(response(0.2, -1.2, pts, axes), np.full(4, 1e-6))
    check("clean single line not flagged", not is_distorted(fit), "rel %.3f" % fit["rel_resid"])
    u = response(0.0, -1.2, pts, axes) - 0.5 * response(0.8, -0.5, pts, axes)
    fit = solve(u, np.full(4, 1e-6) * np.abs(u).max())
    check("shallow line 0.8 m away, current returning: flagged", is_distorted(fit),
          "rel %.3f" % fit["rel_resid"])
    # Known limit, documented in the README: two parallel lines close together
    # (here 0.5 m apart, 1.2 m down) look like ONE line between them.
    u = response(0.0, -1.2, pts, axes) + 0.6 * response(0.5, -1.2, pts, axes)
    fit = solve(u, np.full(4, 1e-6) * np.abs(u).max())
    check("close parallel pair reads as one line between (known limit)",
          0.0 < fit["x"] < 0.5 and not is_distorted(fit), "x %.2f rel %.3f" % (fit["x"], fit["rel_resid"]))
    check("left/right sign: line to the right is +x",
          solve(response(0.4, -1.0, pts, axes), np.full(4, 1e-9))["x"] > 0)


def test_calibration():
    section("Calibration fit")
    pts, axes = coil_samples()
    true = np.array([1.0, -0.91, 1.07, 0.96])
    P = np.array(config.CAL_POSITIONS)
    f = response(P, np.full_like(P, config.CAL_WIRE_Y), pts, axes)
    m = 0.02 * f * true
    m = m * np.sign(m[:, :1])                 # calibrate.py's sign convention
    g, err = fit_gains(P, m)
    check("recovers gains and signs", np.allclose(g, true, rtol=1e-6), str(np.round(g, 4)))
    check("fit error ~0 on clean data", max(err) < 1e-6)
    from locator.geometry import line_model, loop_model, segment_field
    long_seg = loop_model(P, segments=[((0, config.CAL_WIRE_Y, -1e5), (0, config.CAL_WIRE_Y, 1e5))])
    check("finite-wire Biot-Savart -> infinite wire when long",
          np.allclose(long_seg, 2 * line_model(P), rtol=1e-8))
    # a 1 m segment seen from its middle at 0.5 m: (1/d) * 2 * 0.5/sqrt(0.25+0.25)
    b = np.linalg.norm(segment_field(np.array([0.5, 0.0, 0.0]), (0, 0, -0.5), (0, 0, 0.5)))
    check("finite segment field value", abs(b - 2 * 0.5 / math.sqrt(0.5) / 0.5) < 1e-12, "%.6f" % b)
    fl = loop_model(P)
    ml = 0.02 * fl * true
    ml = ml * np.sign(ml[:, :1])
    gl, errl = fit_gains(P, ml, model=fl)
    check("loop model: recovers gains", np.allclose(gl, true, rtol=1e-6), str(np.round(gl, 4)))
    _, err_wrong = fit_gains(P, ml)               # pretend it was a straight wire
    check("loop data fit as a straight wire is flagged", max(err_wrong) > config.CAL_MAX_FIT_ERR,
          "%.1f %%" % (100 * max(err_wrong)))
    m2 = m.copy()
    m2[1, 3] *= 1.15
    _, err2 = fit_gains(P, m2)
    check("flags a bad reading", err2[3] > config.CAL_MAX_FIT_ERR, "%.1f %%" % (100 * err2[3]))


# ---------------------------------------------------------------- pipeline --
def run_pipeline(depth, staff_x, mode_freq, seconds=3.0, second=None, hum=0.01,
                 noise=2e-5, freq_error=2.6, amplitude=0.02):
    gains = (1.0, -0.93, 1.06, 0.97)
    lines = [(0.0, depth, 1.0)]
    if second:
        lines.append(second)
    src = SimSource(freq=mode_freq, lines=lines, staff_x=lambda t: staff_x, gains=gains,
                    hum=hum, noise=noise, freq_error=freq_error, amplitude=amplitude)
    span = 60.0 if mode_freq > 100 else 0.0
    freq, _ = lock_frequency(src, mode_freq, span)
    loc = Locator(freq, gains, src.rate, src.block)
    for _ in range(int(seconds * src.rate / src.block)):
        loc.feed(src.read())
    return loc.estimate(), freq


def test_pipeline():
    section("Whole pipeline on simulated coils")
    for depth, sx, f in ((1.5, -0.3, 8192.0), (1.83, 0.0, 32768.0), (0.9, 0.5, 8192.0)):
        est, fl = run_pipeline(depth, sx, f)
        ok = (est.status == "ok" and abs(est.depth - depth) < 0.05 * depth
              and abs(est.x - (0.0 - sx)) < 0.05)
        check("%.2f m deep, staff at %+.1f m, %d Hz" % (depth, sx, f), ok,
              "status %s depth %s x %s lock %.2f Hz" % (est.status, est.depth and round(est.depth, 3),
                                                       est.x and round(est.x, 3), fl))
    est, _ = run_pipeline(1.0, 0.0, 60.0, hum=0.0, freq_error=0.0)
    check("power mode (60 Hz)", est.status == "ok" and abs(est.depth - 1.0) < 0.05,
          "depth %s" % (est.depth and round(est.depth, 3)))
    est, _ = run_pipeline(1.2, 0.0, 8192.0, second=(0.8, 0.5, -0.5))
    check("second line -> DISTORTED", est.status == "distorted", est.status)
    est, _ = run_pipeline(1.5, 0.0, 8192.0, noise=0.02, amplitude=2e-4)
    check("buried in noise -> WEAK", est.status == "weak", "%s, %.1f dB" % (est.status, est.snr_db))
    est, _ = run_pipeline(1.5, 0.0, 8192.0, noise=0.5)
    check("samples near full scale -> OVERLOAD", est.status == "overload", est.status)
    # calibrating power mode: 90 Hz tone with 60 Hz hum as strong as the tone
    import calibrate
    pos = {"x": 0.0}
    true = np.array([1.0, -0.93, 1.06, 0.97])
    src = SimSource(freq=90.0, lines=[(0.0, -config.CAL_WIRE_Y, 1.0)], staff_x=lambda t: -pos["x"],
                    gains=true, noise=2e-5, amplitude=0.01, hum=0.01)
    tr = Tracker(src.rate, 90.0, 4, config.TAU, src.block, config.NOISE_OFFSET_HZ,
                 config.NOISE_OFFSET_ALT_HZ)
    rows = []
    for x in config.CAL_POSITIONS:
        pos["x"] = x
        calibrate.measure(src, tr, config.CAL_SETTLE_S)
        rows.append(calibrate.measure(src, tr, config.CAL_AVERAGE_S)[0])
    g, err = fit_gains(config.CAL_POSITIONS, np.array(rows))
    check("90 Hz calibration under equal 60 Hz hum: gains within 0.5 %",
          np.allclose(g, true, rtol=5e-3), str(np.round(g, 4)))

    # Stage 1: the loop, driven from the interface, hum 5x the tone at the coils
    from locator.geometry import loop_model
    for f0 in (90.0, 8192.0):
        pos = {"x": 0.0}
        src = SimSource(freq=f0, field_fn=lambda t: loop_model([pos["x"]])[0], gains=true,
                        noise=2e-5, amplitude=0.002, hum=0.01)
        tr = Tracker(src.rate, f0, 4, config.TAU, src.block, config.NOISE_OFFSET_HZ,
                     config.NOISE_OFFSET_ALT_HZ)
        rows = []
        for x in config.CAL_POSITIONS:
            pos["x"] = x
            calibrate.measure(src, tr, config.CAL_SETTLE_S)
            rows.append(calibrate.measure(src, tr, config.CAL_AVERAGE_S)[0])
        g, err = fit_gains(config.CAL_POSITIONS, np.array(rows), model=loop_model(config.CAL_POSITIONS))
        check("loop calibration at %g Hz under strong hum: gains within 0.5 %%" % f0,
              np.allclose(g, true, rtol=5e-3) and max(err) < config.CAL_MAX_FIT_ERR,
              "%s, worst fit %.2f %%" % (np.round(g, 4), 100 * max(err)))
    loc = Locator(8192.0, None)
    src = SimSource()
    for _ in range(20):
        loc.feed(src.read())
    check("no calibration -> NOT CALIBRATED", loc.estimate().status == "uncalibrated")

    t = time.perf_counter()
    for _ in range(10):
        solve(np.array([1.0, 0.1, 0.7, 0.05]), np.full(4, 1e-3))
    ms = (time.perf_counter() - t) * 100
    check("solver fast enough for 4 updates/s", ms < 120, "%.0f ms per solve here" % ms)


# -------------------------------------------------------------- power mode --
def power_sweep(lines, xs, settle=20):
    gains = (1.0, -0.93, 1.06, 0.97)
    pos = {"x": 0.0}
    src = SimSource(freq=60.0, lines=lines, staff_x=lambda t: pos["x"], gains=gains, noise=2e-6)
    loc = Locator(60.0, gains, src.rate, src.block, power=True)
    out = []
    for x in xs:
        pos["x"] = x
        for _ in range(settle):
            loc.feed(src.read())
        out.append(loc.estimate())
    return out


def test_power():
    section("Power mode (no transmitter)")
    s = 0.012                      # hot and neutral 12 mm apart
    D = 1.5
    sources = {
        "single wire": [(0.0, D, 1.0)],
        "pair side by side": [(-s / 2, D, 1.0), (s / 2, D, -1.0)],
        "pair stacked": [(0.0, D - s / 2, 1.0), (0.0, D + s / 2, -1.0)],
        "pair + 5 % net current": [(-s / 2, D, 1.0), (s / 2, D, -0.95)],
    }
    for name, lines in sources.items():
        # walk out to 1.2 m and back to the line: the peak is where we started
        xs = [0.0, 0.0, 0.4, 0.8, 1.2, 0.8, 0.4, 0.15, 0.0]
        est = power_sweep(lines, xs)
        at_line, off = est[-1], est[4]
        brackets = at_line.depth is not None and at_line.depth - 0.05 <= D <= at_line.depth_hi + 0.05
        check("%s: AT PEAK over it, not 1.2 m off" % name,
              at_line.at_peak and not off.at_peak and off.peak_db < -1.0,
              "over %.2f dB, 1.2 m off %.2f dB" % (at_line.peak_db, off.peak_db))
        check("%s: depth range brackets %.1f m" % (name, D), brackets,
              "%.2f to %.2f m" % (at_line.depth or -1, at_line.depth_hi or -1))
    single = power_sweep(sources["single wire"], [0.0, 0.0])[-1]
    check("single wire: shallow end of the range is the true depth",
          abs(single.depth - D) < 0.05, "%.3f m" % single.depth)
    pair = power_sweep(sources["pair stacked"], [0.0, 0.0])[-1]
    check("pair: deep end of the range is the true depth",
          abs(pair.depth_hi - D) < 0.08, "%.3f m" % pair.depth_hi)


# ------------------------------------------------------------------ display --
def test_display():
    section("Screen")
    from locator.display import build_frame, reverse_bits
    check("bit reversal", reverse_bits(0x01) == 0x80 and reverse_bits(0b00000110) == 0b01100000
          and all(reverse_bits(reverse_bits(b)) == b for b in range(256)))
    data = bytes(range(50)) * 240
    fr = build_frame(data, 400, 240, True)
    check("frame length", len(fr) == 1 + 240 * 52 + 1, str(len(fr)))
    check("command byte with VCOM", fr[0] == 0xC0 and build_frame(data, 400, 240, False)[0] == 0x80)
    check("line 1 address LSB-first", fr[1] == 0x80 and fr[1 + 52] == 0x40)
    try:
        from locator.display import Screen
        from locator.pipeline import Estimate
        sc = Screen()
        img = sc.render(Estimate(status="distorted", snr_db=35.0, depth=1.40, x=0.2, distorted=True),
                        "8 kHz", True)
        check("renders 400 x 240 1-bit", img.size == (400, 240) and img.mode == "1")
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "screen-example.png")
        if "--save-screens" in sys.argv:
            img.convert("L").resize((800, 480)).save(out)
            sc.render(Estimate(status="ok", snr_db=48.0, depth=1.40, x=-0.18), "8 kHz", True) \
              .convert("L").resize((800, 480)).save(out.replace("example", "ok"))
            sc.render(Estimate(status="ok", snr_db=41.0, depth=1.31, depth_hi=2.9, power=True,
                               peak_db=-0.1, at_peak=True), "60 Hz POWER", True) \
              .convert("L").resize((800, 480)).save(out.replace("example", "power"))
    except ImportError:
        check("renders (Pillow not installed: skipped)", True)


def test_units():
    section("Units")
    check("4' 7\"", fmt_depth(4 * 0.3048 + 7 * 0.0254) == "4' 7\"", fmt_depth(1.397))
    check("metric", fmt_depth(1.234, "metric") == "1.23 m")
    check("left arrow", fmt_offset(-0.18) == "< 7 in", fmt_offset(-0.18))
    check("right arrow", fmt_offset(0.3) == "12 in >", fmt_offset(0.3))
    check("on line", fmt_offset(0.02) == "ON LINE")
    check("none", fmt_depth(None) == "--" and fmt_offset(None) == "")


# -------------------------------------------------------------- transmitter --
def test_transmitter():
    section("Transmitter timing (transmitter/main.py)")
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transmitter", "main.py")
    spec = importlib.util.spec_from_file_location("tx_main", path)
    tx = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tx)              # no rp2/machine here: imports cleanly
    check("imports without a Pico", not tx.ON_PICO)
    for f in tx.FREQS:
        for alpha in tx.LEVELS:
            drive, zero, got = tx.phase_counts(f, alpha)
            half = (drive + 3) + (zero + 3)
            ok = drive >= 0 and zero >= 0 and abs(got - f) < 0.01 and \
                abs(tx.SM_FREQ / (2 * half) - got) < 1e-9
            check("%5d Hz alpha %.2f" % (f, alpha), ok, "drive %d zero %d -> %.4f Hz" % (drive, zero, got))
    # fundamental of the three-level wave matches (4/pi) sin(pi alpha / 2)
    for alpha in tx.LEVELS:
        drive, zero, _ = tx.phase_counts(8192, alpha)
        half = drive + zero + 6
        on = drive + 3
        w = np.concatenate([np.ones(on), np.zeros(half - on), -np.ones(on), np.zeros(half - on)])
        a1 = 2 * abs(np.fft.rfft(w)[1]) / len(w)
        eff = on / half
        check("fundamental at level %.2f" % alpha,
              abs(a1 - 4 / math.pi * math.sin(math.pi * eff / 2)) < 0.01, "%.3f" % a1)


def main():
    t = time.time()
    test_lockin()
    test_frequency()
    test_solver()
    test_calibration()
    test_pipeline()
    test_power()
    test_display()
    test_units()
    test_transmitter()
    print("\n%d passed, %d failed (%.1f s)" % (len(PASSED), len(FAILED), time.time() - t))
    if FAILED:
        print("failed: " + ", ".join(FAILED))
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
