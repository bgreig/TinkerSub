"""
Guide figure: section through a thruster's axis, drawn from the real part geometry (thruster.py), showing the oil fill and
the compensator (nipple, finger-cot bladder, O-ring, vent), with labels. Replaces the hand-drawn compensator_section.png,
which had drifted from the part. The motor, cable gland, lead and bladder are drawn schematically.
usage: python3 comp_fig.py out/compensator_section.png
"""
import sys
import numpy as np, trimesh, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly, Circle
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import polygonize, unary_union
import thruster as T

PART, MOTOR, OIL, WATER, BLADDER, DARK = "#5a5f66", "#c3c7cc", "#f0ad3c", "#bfe0f7", "#1f5fb4", "#25282c"

def mesh(m):
    g = m.to_mesh(); return trimesh.Trimesh(g.vert_properties[:, :3], g.tri_verts)

def section(t):
    """the part's section on the plane x = 0 as shapely polygons in (z, y)"""
    s = t.section([1, 0, 0], [0, 0, 0])
    lines = [LineString([(p[2], p[1]) for p in e]) for e in s.discrete]
    out = []
    for poly in polygonize(unary_union(lines)):
        q = poly.representative_point()
        if t.contains([[0.0, q.y, q.x]])[0]: out.append(poly)
    return unary_union(out)

def draw(ax, geom, fc, ec=None, lw=0.6, z=2, alpha=1.0):
    for g in getattr(geom, "geoms", [geom]):
        if g.is_empty: continue
        ax.add_patch(MPoly(np.array(g.exterior.coords), closed=True, fc=fc, ec=ec or fc, lw=lw, zorder=z, alpha=alpha))
        for h in g.interiors: ax.add_patch(MPoly(np.array(h.coords), closed=True, fc="white", ec=ec or fc, lw=lw, zorder=z))

def main(out):
    housing, cone, prop = (mesh(m) for m in (T.housing(foot=False), T.tail_cone(comp=True), T.prop(1)))
    H, C, P = section(housing), section(cone), section(prop)
    zt = -T.CONE_SH - T.CONE_L
    # oil: the housing bore + the cone's cavity and spigot (parts and the motor are drawn over it)
    rc_top = T.R_CAP - 4.5; z45 = -T.CONE_SH - 1.0 + (rc_top - T.SPIG_IN)
    half = [(zt + T.TIP_WALL, 0), (zt + T.TIP_WALL, T.CONE_TIP - 1.6), (-T.CONE_SH - 1.0, rc_top), (z45, T.SPIG_IN), (T.L_INT, T.SPIG_IN)]
    cav = Polygon(half + [(z, -y) for z, y in reversed(half)])
    oil = unary_union([cav, box(0, -T.BORE_R, T.L_INT, T.BORE_R)])
    z0m = T.SPIGOT_H + T.REAR_SPACE
    motor = unary_union([box(z0m, -T.MOTOR_D/2, T.L_INT, T.MOTOR_D/2), box(T.L_INT - 0.1, -T.NOSE_D/2, T.L_INT + T.NOSE_L, T.NOSE_D/2),
                         box(T.L_INT, -T.SHAFT_D/2, T.L_INT + T.SHAFT_OUT, T.SHAFT_D/2)])
    # compensator, schematic parts: bladder over the nipple, O-ring in the groove, water in the vent
    y0, tip = T.COMP_Y, T.COMP_TIP; zg = tip - T.COMP_BARB
    sleeve = box(zg - T.COMP_GROOVE - 1.5, y0 - 3.9, tip + 0.5, y0 + 3.9)
    balloon = Point(tip + 4.5, y0 - 1.5).buffer(5.0).union(box(tip, y0 - 4.6, tip + 4.5, y0 + 3.9))
    bladder = sleeve.union(balloon).difference(C).buffer(0)
    inside = Point(tip + 4.5, y0 - 1.5).buffer(3.6).union(LineString([(zg - 1.5, y0), (tip + 4.5, y0 - 1.5)]).buffer(1.1))
    vent = LineString([(tip, y0), (-17.5, y0), (-17.5 - 6, y0 + 6)]).buffer(1.1)
    gland = unary_union([box(zt - 8, -8.5, zt, 8.5), box(zt - 15, -7, zt - 8, 7), box(zt + 0.01, -5.9, zt + T.TIP_WALL, 5.9)])
    cable = box(zt - 52, -3.0, zt - 15, 3.0)
    lead = LineString([(zt, -1.5), (-6, -2.5), (z0m, -6)]).buffer(1.2)

    fig, ax = plt.subplots(figsize=(13.5, 7.2)); fig.subplots_adjust(0.01, 0.06, 0.99, 0.99)
    draw(ax, oil, OIL, z=1)
    draw(ax, motor, MOTOR, ec="#8d939a", z=3)
    draw(ax, lead, DARK, z=3)
    draw(ax, H, PART, z=4); draw(ax, C, PART, z=4); draw(ax, P, "#9aa1a9", ec="#7d848c", z=4)
    draw(ax, vent, WATER, z=5)
    draw(ax, bladder, WATER, ec=BLADDER, lw=1.6, z=6); draw(ax, inside, WATER, z=6)
    for s in (1, -1):
        ax.add_patch(Circle((zg - T.COMP_GROOVE/2, y0 + s*(T.COMP_GROOVE_R + 0.85)), 0.75, fc="black", zorder=7))
        ax.add_patch(Circle((T.SPIGOT_H/2, s*(T.BORE_R - T.GROOVE_DEPTH/2)), 0.95, fc="black", zorder=7))
    draw(ax, gland, DARK, z=5); draw(ax, cable, DARK, z=5)

    def lab(text, xy, at, ha="left"):
        ax.annotate(text, xy=xy, xytext=at, fontsize=12.5, ha=ha, va="center", zorder=9, color="#25282c",
                    arrowprops=dict(arrowstyle="-", lw=0.8, color="#25282c", shrinkA=2, shrinkB=0))
        ax.add_patch(Circle(xy, 0.55, fc="#25282c", zorder=9))
    lab("Compensator bladder (finger cot):\nwater inside, oil outside", (tip + 5.5, y0 - 1.5), (-62, 44))
    lab("O-ring (5 x 1.5) in the nipple's groove\nholds the cot: no tie", (zg - 1, y0 + 3.4), (-62, 33))
    lab("2.2 mm vent: water moves in and out\nas the oil expands and shrinks", (-21, y0 + 3.6), (-75, 21))
    lab("Cable gland", (zt - 10, -5), (-75, -20))
    lab("Spigot O-ring", (T.SPIGOT_H/2, -(T.BORE_R - T.GROOVE_DEPTH/2)), (-40, -36))
    lab("Mineral oil: fills the housing, the tail\nand the inside of the motor", (6, -12), (5, -44))
    lab("Motor", (45, 6), (45, 40), ha="center")
    lab("Prop", (T.PROP_Z0 + 12, 14), (118, 40), ha="center")
    ax.text(30, -54, "Section through the thruster axis, from the part geometry (motor, gland and bladder drawn schematically). "
            "Fill and bleed ports are on the sides, not in this cut.", ha="center", fontsize=10.5, color="#6b7077")
    ax.set_xlim(-80, 140); ax.set_ylim(-58, 52); ax.set_aspect("equal"); ax.axis("off")
    fig.savefig(out, dpi=100, facecolor="white"); print("compensator figure:", out)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "out/compensator_section.png")
