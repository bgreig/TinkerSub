"""
Sled side rails 212 / 213: open the front end of the lower wire window (2026-10-16).

The Pico now sits on a 57 x 63 mm screw-terminal breakout under the front of the deck. Its terminals face the rails with
only 1.5 mm to spare, so every wire has to come in through a rail window. The lower windows started at sled z 20, which
left the first ~15 mm of terminals (USB end: Pico pins 1-5 and 36-40) facing solid rail. This cuts the lower window of
both rails forward to z 3.5 (rounded corners, r 3), between y -25.5 and -5.5 like the existing windows.

Sources: the supplied rail STLs (sled frame, New_parts/21x_*.stl) and their print-orientation
copies (prep/sled_rail_*.stl, which also carry the engraved labels). Print frame: port rail z_sled = 117 - x,
starboard rail z_sled = 117 + x; y is the same in both frames; x/z thickness 0..5.2.
Writes  src_parts/21x_*.stl (sled frame, read by rov_v6.py) and prep/sled_rail_*.stl (print frame, labelled).
usage:  python3 rail_notch.py <New_parts dir> <prep dir in> <out root>
"""
import sys, os, numpy as np, trimesh
from manifold3d import Manifold, Mesh, CrossSection

NP, PREP, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
Z0, Z1, Y0, Y1, R = 3.5, 24.0, -25.5, -5.5, 3.0          # notch in the sled frame (z along the rail, y up)

def mf(t): return Manifold(Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
def tm(m): g = m.to_mesh(); return trimesh.Trimesh(g.vert_properties[:, :3], g.tri_verts)
def prism(u0, u1, v0, v1, w0, w1):
    """rounded rectangle in (u, v), extruded along w; returned with u -> axis 0, v -> axis 1, w -> axis 2"""
    cs = CrossSection.square((u1 - u0 - 2 * R, v1 - v0 - 2 * R)).translate((u0 + R, v0 + R)).offset(R, circular_segments=24)
    return Manifold.extrude(cs, w1 - w0).translate((0, 0, w0))

os.makedirs(f"{OUT}/src_parts", exist_ok=True); os.makedirs(f"{OUT}/prep", exist_ok=True)
for pn, name, side in (("212", "sled_rail_port", -1), ("213", "sled_rail_stbd", 1)):
    # sled frame: rail occupies x 30..35.2 (stbd) or -35.2..-30 (port); cut (z, y) profile through x
    s = trimesh.load(f"{NP}/{pn}_{name}.stl"); m = mf(s)
    cut = prism(Z0, Z1, Y0, Y1, -40, 40)                           # (z, y, x) -> reorder to (x, y, z)
    cut = cut.transform([[0, 0, 1, 0], [0, 1, 0, 0], [1, 0, 0, 0]])
    a = tm(m - cut); a.export(f"{OUT}/src_parts/{pn}_{name}.stl")
    # print frame: x = 117 - z (port) or z - 117 (stbd), y = y, thickness along z 0..5.2
    p = trimesh.load(f"{PREP}/{name}.stl"); mp = mf(p)
    x0, x1 = sorted(((117 - Z0, 117 - Z1) if side < 0 else (Z0 - 117, Z1 - 117)))
    b = tm(mp - prism(x0, x1, Y0, Y1, -5, 10)); b.export(f"{OUT}/prep/{name}.stl")
    print(f"{pn} {name}: removed {s.volume - a.volume:.0f} / {p.volume - b.volume:.0f} mm3, watertight {a.is_watertight}/{b.is_watertight}, "
          f"bodies {len(a.split())}/{len(b.split())}")
