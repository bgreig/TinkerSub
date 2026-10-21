"""One-piece side plate STLs (HDPE version: no seam/splice holes), 12.7 mm thick, outside face up.
   out_final/rov_side_plate_port.stl, _stbd.stl, and rov_side_plates_24x24_nest.stl (both, laid out as on the sheet)."""
import numpy as np, trimesh
from manifold3d import Manifold, CrossSection
import rov_v5 as V
def plate(side):
    s = -1 if side == "port" else 1                       # seen from outside, as in the DXF / templates
    cs = V._solid
    for z, y, r, k in V.HOLES:
        if k not in ("lap", "splice"): cs = cs - V.circ(z, y, r)
    cs = cs.scale((-s, 1)) if s == 1 else cs               # drawing coords: u = -z (port = front on the left)
    return Manifold.extrude(cs, V.T_PL)
def save(m, name):
    g = m.to_mesh(); t = trimesh.Trimesh(g.vert_properties[:, :3], g.tri_verts)
    t.apply_translation(-t.bounds[0]); t.export(f"out_final/{name}.stl")
    print(name, t.is_watertight, np.round(t.extents, 1)); return t
p, s = plate("port"), plate("stbd")
save(p, "rov_side_plate_port"); save(s, "rov_side_plate_stbd")
bp, bs = np.array(p.bounding_box()), np.array(s.bounding_box())
S, gap = 609.6, 4.8
h = bp[4] - bp[1]
p2 = p.translate(((S - (bp[3] - bp[0]))/2 - bp[0], (S - 2*h - gap)/2 - bp[1], 0))
s2 = s.translate(((S - (bs[3] - bs[0]))/2 - bs[0], (S - 2*h - gap)/2 + h + gap - bs[1], 0))
t = save(p2 + s2, "rov_side_plates_24x24_nest")
print("nest footprint in mm:", np.round(t.extents[:2], 1), "sheet 609.6 x 609.6")
