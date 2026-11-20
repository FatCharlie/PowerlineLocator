"""Field of a long straight line, the depth solver, and the calibration fit.

A long straight conductor carrying current I makes a field that circles it:

    |B| = mu0 I / (2 pi r)

At a coil sitting dx to the side of the line and dy above it (r^2 = dx^2 +
dy^2) the two components in the board's plane are

    Bx = -k dy / r^2        By = k dx / r^2        with k = mu0 I / (2 pi)

Each coil only sees the component along its own axis. We measure four numbers
(two horizontal coils, two vertical) and solve for three unknowns: the line's
position (X, Y) and its strength k. The fourth number is spare, and how badly
it disagrees with the best fit is the distortion warning: a second line, a
fence, a bend or a tee all bend the field away from the one-line shape.
"""
import math

import numpy as np

from . import config


def coil_samples(coils=None, half=None, n=None):
    """Sample points along each coil's axis: pts (C, n, 2) and axes (C, 2)."""
    coils = coils or config.COILS
    half = config.ROD_EFFECTIVE_HALF if half is None else half
    n = config.ROD_SAMPLES if n is None else n
    offs = np.linspace(-half, half, n) if n > 1 else np.zeros(1)
    pts, axes = [], []
    for c in coils:
        a = np.array([1.0, 0.0]) if c["axis"] == "x" else np.array([0.0, 1.0])
        centre = np.array([c["x"], c["y"]])
        pts.append(centre[None, :] + offs[:, None] * a[None, :])
        axes.append(a)
    return np.array(pts), np.array(axes)


def response(X, Y, pts, axes):
    """Field along each coil's axis for a unit-strength line at (X, Y).

    X, Y: arrays of any (matching) shape S. Returns shape S + (C,).
    """
    X = np.asarray(X, dtype=float)[..., None, None]
    Y = np.asarray(Y, dtype=float)[..., None, None]
    dx = pts[..., 0] - X
    dy = pts[..., 1] - Y
    r2 = dx * dx + dy * dy
    bx = -dy / r2
    by = dx / r2
    comp = bx * axes[:, 0][:, None] + by * axes[:, 1][:, None]
    return comp.mean(axis=-1)


def _fit_grid(u, w, X, Y, pts, axes):
    f = response(X, Y, pts, axes)                       # (G, C)
    fw = f * w
    k = (fw * u).sum(-1) / ((fw * f).sum(-1) + 1e-300)  # best strength per point
    r = u - k[..., None] * f
    chi2 = (w * r * r).sum(-1)
    return chi2, k


def solve(u, sigma, coils=None):
    """Best single-line fit to calibrated amplitudes u (C,) with noise sigma (C,).

    Returns a dict: x (m, + = line to your right), depth (m below the tip),
    k, rel_resid (0 = perfect single-line field), chi2 (noise-normalised).
    """
    pts, axes = coil_samples(coils)
    u = np.asarray(u, float)
    # Weights are pure noise, so the depth leans on the channels that are
    # actually clean. The tiny floor only stops one near-silent channel from
    # getting an absurd weight.
    floor = config.MODEL_FLOOR * float(np.max(np.abs(u)))
    w = 1.0 / np.maximum(np.asarray(sigma, float) ** 2 + floor ** 2, 1e-30)

    x0, x1 = config.SEARCH_X
    d0, d1 = config.SEARCH_DEPTH
    tip_y = 0.0
    xs = np.arange(x0, x1 + 1e-9, 0.05)
    ys = tip_y - np.arange(d0, d1 + 1e-9, 0.05)
    GX, GY = np.meshgrid(xs, ys, indexing="ij")
    chi2, _ = _fit_grid(u, w, GX, GY, pts, axes)
    i, j = np.unravel_index(int(np.argmin(chi2)), chi2.shape)
    bx, by = xs[i], ys[j]

    for step in (0.005, 0.0005):
        span = 15 * step * 2
        fx = bx + np.arange(-span, span + 1e-12, step)
        fy = by + np.arange(-span, span + 1e-12, step)
        fy = fy[fy <= tip_y - d0]
        GX, GY = np.meshgrid(fx, fy, indexing="ij")
        chi2, kk = _fit_grid(u, w, GX, GY, pts, axes)
        i, j = np.unravel_index(int(np.argmin(chi2)), chi2.shape)
        bx, by = fx[i], fy[j]
        best_chi2, best_k = float(chi2[i, j]), float(kk[i, j])

    # rel_resid: how far the four readings are from ANY single-line field, as
    # a fraction of the whole signal. Noise alone keeps chi2 near 1.
    model = best_k * response(bx, by, pts, axes)
    total = float((u * u).sum())
    rel = float(np.sqrt(((u - model) ** 2).sum() / total)) if total > 0 else 1.0
    return {"x": float(bx), "depth": float(-by), "k": best_k,
            "rel_resid": rel, "chi2": best_chi2}


def is_distorted(fit):
    return fit["rel_resid"] > config.DISTORT_REL and fit["chi2"] > config.DISTORT_CHI2


def line_model(positions, wire_y=None, coils=None):
    """Calibration model for one long straight wire: (P, C) field per coil."""
    wire_y = config.CAL_WIRE_Y if wire_y is None else wire_y
    pts, axes = coil_samples(coils)
    P = np.asarray(positions, float)
    return response(P, np.full_like(P, wire_y), pts, axes)


def segment_field(P, A, B):
    """Field at points P (..., 3) of a straight segment from A to B carrying a
    unit current, in units of mu0 I / (4 pi). This is Biot-Savart for a
    finite wire:

        |B| = (1/d) (s1 / sqrt(s1^2 + d^2) - s2 / sqrt(s2^2 + d^2))

    d is the point's distance from the wire's line; s1 and s2 are where the
    wire's two ends sit along it. For an infinitely long wire the bracket is 2,
    giving the familiar 2/d, i.e. mu0 I / (2 pi d). The field circles the wire.
    """
    A = np.asarray(A, float)
    B = np.asarray(B, float)
    L = np.linalg.norm(B - A)
    u = (B - A) / L
    ap = np.asarray(P, float) - A
    t = ap @ u
    rho = ap - t[..., None] * u
    d = np.maximum(np.linalg.norm(rho, axis=-1), 1e-9)
    s1, s2 = t, t - L
    mag = (s1 / np.sqrt(s1 ** 2 + d ** 2) - s2 / np.sqrt(s2 ** 2 + d ** 2)) / d
    return mag[..., None] * np.cross(u, rho / d[..., None])


def loop_segments(length=None, width=None, side=None, wire_y=None):
    """The calibration loop: a rectangle lying on the ground.

    The near leg runs along z (straight away from you) through x = 0; the far
    leg is `width` away on `side` (-1 = your left). You stand at the middle.
    """
    L = config.CAL_LOOP_LENGTH if length is None else length
    W = config.CAL_LOOP_WIDTH if width is None else width
    sd = config.CAL_LOOP_SIDE if side is None else side
    y = config.CAL_WIRE_Y if wire_y is None else wire_y
    xf = sd * W
    c = [(0.0, y, -L / 2), (0.0, y, L / 2), (xf, y, L / 2), (xf, y, -L / 2)]
    return [(c[i], c[(i + 1) % 4]) for i in range(4)]


def loop_model(positions, segments=None, coils=None):
    """Calibration model for the loop: (P, C) field per coil.

    positions: where the NEAR leg is relative to the staff (+ = your right),
    exactly like the straight-wire case. The far leg and the two end legs are
    all included, so the loop can be small enough to lay out in a yard.
    """
    segments = segments or loop_segments()
    pts, axes = coil_samples(coils)                    # (C, n, 2), (C, 2)
    out = []
    for p in np.asarray(positions, float):
        xyz = np.concatenate([pts[..., :1] - p, pts[..., 1:2], np.zeros(pts.shape[:-1] + (1,))], -1)
        field = sum(segment_field(xyz, a, b) for a, b in segments)   # (C, n, 3)
        comp = (field[..., :2] * axes[:, None, :]).sum(-1)           # along each coil axis
        out.append(comp.mean(-1))
    return np.array(out)


def fit_gains(positions, measured, wire_y=None, coils=None, model=None):
    """Calibration: relative gain of each channel from a wire at known spots.

    positions: where the wire is for each spot (m, + = wire to your right).
    measured: (P, C) signed amplitudes, sign fixed so channel 0 is positive.
    model: (P, C) predicted field, or None for a single long straight wire.
    Returns (gains (C,) with gains[0] = 1, fit_err (C,) as a fraction).

    Model: measured[p, c] = a_c * f_c(position p), one unknown a_c per channel
    (gain times current). Least squares gives each a_c on its own, and dividing
    by a_0 leaves the gains relative to the bottom horizontal coil, signs
    included, so you never need to know which way a coil was wound.
    """
    f = line_model(positions, wire_y, coils) if model is None else np.asarray(model, float)
    m = np.asarray(measured, float)
    a = (f * m).sum(0) / (f * f).sum(0)
    resid = m - a[None, :] * f
    err = np.sqrt((resid ** 2).sum(0) / ((m ** 2).sum(0) + 1e-300))
    return a / a[0], err

def pair_strengths(u):
    """Total field (horizontal and vertical combined) at the bottom and top pairs.

    For one wire, OR for a pair of wires at any orientation, this is the same
    whichever way the field points, so it peaks right over the line either way.
    """
    u = np.asarray(u, float)
    by = {(c["y"], c["axis"]): u[c["ch"]] for c in config.COILS}
    ys = sorted({c["y"] for c in config.COILS})
    yb, yt = ys[0], ys[-1]
    return (float(np.hypot(by[(yb, "x")], by[(yb, "y")])),
            float(np.hypot(by[(yt, "x")], by[(yt, "y")])), yb, yt)


def power_depth_range(u):
    """Depth range (shallowest, deepest) below the tip from the two pairs.

    R = |B(bottom)| / |B(top)| over the line. A single wire falls as 1/r, so
        h = d / (R - 1)
    A pair of wires (hot and neutral) falls as 1/r^2, so R = ((h + d)/h)^2 and
        h = d / (sqrt(R) - 1)
    A live cable is some mix of the two, so its true depth lies between: the
    single-wire number is the shallowest it can be. h is measured from the
    bottom pair; subtract the bottom pair's height to get depth below the tip.
    Returns (None, None) if the reading makes no sense (R <= 1).
    """
    b, t, yb, yt = pair_strengths(u)
    d = yt - yb
    if t <= 0 or b / t <= 1.0005:
        return None, None
    R = b / t
    lo = d / (R - 1.0) - yb
    hi = d / (math.sqrt(R) - 1.0) - yb
    return max(0.0, lo), max(0.0, hi)
