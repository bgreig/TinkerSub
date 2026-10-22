"""
Split clamp bracket for the thruster body, carrying the mounting block.
Use it with housing_no_foot (or with_foot) to mount the thruster by its body.

  bracket_bottom : lower half + mounting block (4x M3 heat-set inserts, same
                   20 mm hole spacing across as before) + 4x M4 heat-set inserts
  bracket_top    : upper half, 4x M4x16 SHCS clamp it shut
  slide_adapter_bracket : the dovetail slide adapter, re-drilled for the bracket
                          (the hull pad is unchanged)

The halves are cut with a 0.8 mm gap, so tightening squeezes the 43.5 mm body
by about 0.5 mm. The bracket can be rotated around the body to any angle.
Run: python3 bracket.py
"""
import numpy as np, trimesh, os
from manifold3d import Manifold, CrossSection
import thruster as T
import mount as M

T.housing()
RF = -T.FOOT_FACE_Y            # mounting face distance from the axis (same as the nozzle foot)
BORE_R = T.TUBE_R + 0.15
GAP = 0.8
LEN = 32.0
EAR_X, EAR_T = 33.0, 8.0
BOLT_X, BOLT_DZ = 27.5, 8.0
TOP_R = T.TUBE_R + 5.0
FOOT_HW = 15.0
HOLE_X, HOLE_DZ = 10.0, 10.0      # square 20 x 20 pattern: the pylon can be bolted on at 0 or 90 deg

# position: bracket sits behind the stator struts, plate thumbscrews clear of it
PLATE_Z0 = 18.0 - 26.0                       # adapter rear end
BZ0 = PLATE_Z0 + 26.0                        # = 18
BZ1 = BZ0 + LEN                              # = 50 (struts start at z = 53)
BZC = (BZ0 + BZ1)/2
ADAPTER_Z1 = PLATE_Z0 + M.PLATE_L
HOLES = [(x, BZC + dz) for dz in (-HOLE_DZ, HOLE_DZ) for x in (-HOLE_X, HOLE_X)]

def poly_extrude(pts, z0, z1):
    a = sum(x0*y1 - x1*y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    return Manifold.extrude(CrossSection([pts if a > 0 else pts[::-1]]), z1 - z0).translate((0, 0, z0))

def ycyl(r, y0, y1, x, z, seg=40):
    return Manifold.cylinder(abs(y1 - y0), r, r, seg).rotate((-90, 0, 0)).translate((x, min(y0, y1), z))

def bore():
    return Manifold.cylinder(LEN + 2, BORE_R, BORE_R, 180).translate((0, 0, BZ0 - 1))

def bracket_bottom():
    yt = -GAP/2
    ytaper = -10.0
    yfoot = ytaper - (EAR_X - FOOT_HW)          # 45 deg taper: prints without supports
    pts = [(-EAR_X, yt), (EAR_X, yt), (EAR_X, ytaper), (FOOT_HW, yfoot),
           (FOOT_HW, -RF), (-FOOT_HW, -RF), (-FOOT_HW, yfoot), (-EAR_X, ytaper)]
    b = poly_extrude(pts, BZ0, BZ1) - bore()
    for x in (-BOLT_X, BOLT_X):                  # M4 heat-set inserts from the split face
        for dz in (-BOLT_DZ, BOLT_DZ):
            b = b - ycyl(2.8, yt - 8.0, yt + 0.01, x, BZC + dz)
    for x, z in HOLES:                           # M3 heat-set inserts in the mounting face
        b = b - ycyl(2.0, -RF - 0.01, -RF + 8.0, x, z)
    return b

def bracket_top():
    yb = GAP/2
    ring = Manifold.cylinder(LEN, TOP_R, TOP_R, 180).translate((0, 0, BZ0))
    ring = ring ^ Manifold.cube((2*TOP_R + 2, TOP_R + 2, LEN + 2)).translate((-TOP_R - 1, yb, BZ0 - 1))
    ears = Manifold.cube((2*EAR_X, EAR_T, LEN)).translate((-EAR_X, yb, BZ0))
    t = (ring + ears) - bore()
    for x in (-BOLT_X, BOLT_X):                  # M4 clearance
        for dz in (-BOLT_DZ, BOLT_DZ):
            t = t - ycyl(2.25, yb - 1, yb + EAR_T + 1, x, BZC + dz)
    return t

def slide_adapter_bracket():
    return M.slide_adapter(z1=ADAPTER_Z1, holes=HOLES)

def export(m, name):
    g = m.to_mesh(); tm = trimesh.Trimesh(g.vert_properties[:, :3], g.tri_verts)
    tm.apply_translation((-tm.bounds[0][0] - tm.extents[0]/2, -tm.bounds[0][1] - tm.extents[1]/2, -tm.bounds[0][2]))
    tm.export(f"out/{name}.stl")
    print(f"{name:22s} watertight={tm.is_watertight} bodies={len(tm.split(only_watertight=False))} size={np.round(tm.extents,1)}")

if __name__ == "__main__":
    os.makedirs("out", exist_ok=True)
    Bb, Bt, A = bracket_bottom(), bracket_top(), slide_adapter_bracket()
    P = M.pad_receiver(z1=ADAPTER_Z1)
    H, C = T.housing(foot=False), T.tail_cone()
    print("interference (mm3): bottom/housing", round((Bb ^ H).volume(), 2),
          " top/housing", round((Bt ^ H).volume(), 2),
          " bottom/top", round((Bb ^ Bt).volume(), 2),
          " bracket/cone", round(((Bb + Bt) ^ C).volume(), 2),
          " adapter/bracket", round((A ^ Bb).volume(), 2),
          " adapter/housing", round((A ^ H).volume(), 2),
          " pad/adapter", round((P ^ A).volume(), 2),
          " pad/housing", round((P ^ H).volume(), 2))
    print("thumbscrew z:", [round(PLATE_Z0 + d, 1) for d in M.THUMB_DZ], " bracket z:", BZ0, "-", BZ1)
    # print orientations: bottom = mounting face down; top = split face down; adapter = plate down
    export(Bb.rotate((90, 0, 0)), "bracket_bottom")
    export(Bt.rotate((-90, 0, 0)), "bracket_top")
    export(A.rotate((-90, 0, 0)), "slide_adapter_bracket")
