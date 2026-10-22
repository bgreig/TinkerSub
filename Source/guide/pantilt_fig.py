"""Pan-tilt fit diagram: side and top views against the hull bore, dome flange bore and dome."""
import sys, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, Wedge
import pantilt_fit as P
out = sys.argv[1]
def proj(m, view):
    if view == "side": mm = m.rotate((0, -90, 0)); f = lambda p: np.c_[-p[:, 0], p[:, 1]]        # (z, y)
    else: mm = m.rotate((90, 0, 0)); f = lambda p: np.c_[-p[:, 1], p[:, 0]]                       # (z, x)
    return [f(np.array(q)) for q in mm.project().to_polygons()]
def draw(ax, m, **kw):
    for q in proj(m, ax.view): ax.add_patch(Polygon(q, closed=True, **kw))
fig, axs = plt.subplots(1, 2, figsize=(12, 5.6))
for ax, view in zip(axs, ("side", "top")):
    ax.view = view
    # envelope: pipe (z<164.2), flange bore, dome
    z = [150, P.Z_FL0, P.Z_FL0, P.Z_FL1, P.Z_FL1, P.ZD]
    r = [P.R_PIPE, P.R_PIPE, P.R_FL, P.R_FL, P.R_DOME, P.R_DOME]
    for s in (1, -1): ax.plot(z, [s*v for v in r], color="#7d8790", lw=1.4)
    ax.add_patch(Wedge((P.ZD, 0), P.R_DOME, -90, 90, fill=False, ec="#7d8790", lw=1.4))
    ax.fill_between([P.Z_FL0, P.Z_FL1], P.R_FL, P.R_PIPE, color="#c9ced3"); ax.fill_between([P.Z_FL0, P.Z_FL1], -P.R_PIPE, -P.R_FL, color="#c9ced3")
    ax.text((P.Z_FL0 + P.Z_FL1)/2, -P.R_PIPE - 5, "dome flange 203: bore 85.8", ha="center", fontsize=7, color="#5b6670")
    draw(ax, P.base() + P.pan_servo(), fc="#26292d33", ec="#26292d", lw=0.6)
    if view == "side":
        for ph, a in ((-45, 0.25), (45, 0.25), (0, 0.9)):
            draw(ax, P.R_tilt(P.cradle() + P.camera(), ph), fc=(0.12, 0.48, 0.23, a*0.4), ec="#1f7a3a", lw=0.6)
        draw(ax, P.yoke() + P.tilt_servo(0) + P.pan_horn(), fc="#26292d55", ec="#26292d", lw=0.6)
        ax.set_title("Side view: tilt -45 / 0 / +45 deg (camera green)", fontsize=9)
        ax.set_ylabel("y, up (mm)")
    else:
        for th in range(-90, 91, 30):
            mv = P.R_pan(P.yoke() + P.tilt_servo(0) + P.pan_horn() + P.cradle() + P.camera() + P.lever(), th)
            draw(ax, mv, fc=(0.15, 0.16, 0.18, 0.06 if th else 0.35), ec="#26292d" if th == 0 else "#26292d55", lw=0.5)
        ax.set_title("Top view: pan -90 to +90 deg in 30 deg steps", fontsize=9)
        ax.set_ylabel("x, port (mm)")
    ax.plot([P.ZC], [P.LENS_Y if view == "side" else 0], "+", color="#c0392b", ms=12, mew=2)
    ax.set_xlim(145, 270); ax.set_ylim(-58, 58); ax.set_aspect("equal"); ax.grid(alpha=0.25); ax.set_xlabel("z, forward from hull centre (mm)")
plt.suptitle("Camera pan-tilt (216-219) inside the dome: everything stays 1 mm or more inside the bore, flange and dome", fontsize=10)
plt.tight_layout(); plt.savefig(out, dpi=160)
