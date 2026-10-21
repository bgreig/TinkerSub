"""
ROV hull ring for 4" Sch40 PVC (114.3 mm OD). Two identical halves (print 2 per ring)
clamp the hull with 4x M4 bolts through the top and bottom ears.
Each half has a side pad with 4x M3 heat-set inserts on a 20 x 20 mm square,
so a thruster (pylon_clamp) bolts on with its thrust either along the hull
(horizontal) or vertical, just by turning the pylon 90 deg on the pad.

World frame: hull axis = Z, up = +Y, ring centered on z = 0, this half on +X.
Run: python3 ring.py
"""
import numpy as np, trimesh, os
from manifold3d import Manifold, CrossSection
import thruster as T, bracket as B, pylon as PY

HULL_R   = 114.3/2
BORE_R   = HULL_R + 0.25
GAP      = 1.0            # split gap between halves (clamps ~0.25 mm on radius)
RING_T   = 6.0
WIDTH    = 34.0           # along the hull
EAR_H    = 14.0           # ear height above the ring OD
EAR_T    = 7.0            # ear thickness (each half)
BOLT_DZ  = 9.0            # two M4 bolts per ear, +-9 mm along the hull
PAD_FACE = HULL_R + RING_T + 5.0     # pad face distance from hull axis (68.15)
PAD_HALF = 17.0
INSERT_D, INSERT_L = 4.0, 6.0        # M3 heat-set
SEG = 240

R_OUT = BORE_R + RING_T

def zcyl(r, z0, z1, seg=SEG):
    return Manifold.cylinder(z1 - z0, r, r, seg).translate((0, 0, z0))

def xcyl(r, x0, x1, y, z, seg=40):
    return Manifold.cylinder(x1 - x0, r, r, seg).rotate((0, 90, 0)).translate((x0, y, z))

def half_ring():
    z0, z1 = -WIDTH/2, WIDTH/2
    ring = zcyl(R_OUT, z0, z1) - zcyl(BORE_R, z0 - 1, z1 + 1)
    ring = ring ^ Manifold.cube((R_OUT + 1, 2*R_OUT + 40, WIDTH + 2)).translate((GAP/2, -R_OUT - 20, z0 - 1))
    # ears at top and bottom
    ear_r = R_OUT + EAR_H
    for sgn in (1, -1):
        ear = Manifold.cube((EAR_T, ear_r - (BORE_R + 2), WIDTH)).translate((GAP/2, 0, z0))
        ear = ear.translate((0, BORE_R + 2, 0)) if sgn > 0 else ear.translate((0, -ear_r, 0))
        ring = ring + ear
        yb = sgn*(R_OUT + EAR_H/2 - 1)
        for dz in (-BOLT_DZ, BOLT_DZ):
            ring = ring - xcyl(2.25, -1, EAR_T + 5, yb, dz)                    # M4 clearance
            ring = ring - Manifold.cylinder(3.5, 4.3, 4.3, 6).rotate((0, 90, 0)).translate((GAP/2 + EAR_T - 3.0, yb, dz))  # M4 nut pocket
    # side pad (flat face at x = PAD_FACE), tapered 45 deg into the ring so it prints clean
    pts = [(BORE_R - 1, -PAD_HALF - 8), (PAD_FACE - 8, -PAD_HALF), (PAD_FACE, -PAD_HALF),
           (PAD_FACE, PAD_HALF), (PAD_FACE - 8, PAD_HALF), (BORE_R - 1, PAD_HALF + 8)]
    pad = Manifold.extrude(CrossSection([pts]), WIDTH).translate((0, 0, z0))
    pad = pad - zcyl(BORE_R, z0 - 1, z1 + 1)
    ring = ring + pad
    for y, z in [(dy, dz) for dy in (-B.HOLE_X, B.HOLE_X) for dz in (-B.HOLE_X, B.HOLE_X)]:
        ring = ring - xcyl(INSERT_D/2, PAD_FACE - INSERT_L, PAD_FACE + 1, y, z)
    return ring

def place_thruster(mode, side=1):
    """housing + tail + prop + pylon, bolted to the pad on the +X (side=1) or -X (side=-1) half"""
    parts = {"housing": T.housing(foot=False), "tail": T.tail_cone(comp=True), "prop": T.prop(1), "pylon": PY.pylon()}
    out = {}
    for k, m in parts.items():
        m = m.translate((0, 0, -B.BZC))                       # pylon hole-pattern center -> origin
        # pylon frame: mounting face at y = -RF, outward normal -y. Map -y -> -X(world), so y -> X
        if mode == "horizontal":      # thruster axis along the hull (world Z)
            m = m.rotate((0, 0, -90))                         # (x, y, z) -> (y, -x, z): face (y=-RF) toward hull
            m = m.translate((PAD_FACE + B.RF, 0, 0))
        else:                         # vertical: thruster axis -> world Y
            m = m.rotate((0, 0, -90)).rotate((-90, 0, 0))     # then thruster axis z -> world Y
            m = m.translate((PAD_FACE + B.RF, 0, 0))
        if side < 0: m = m.mirror((1, 0, 0))
        out[k] = m
    return out

if __name__ == "__main__":
    os.makedirs("out", exist_ok=True)
    H = half_ring()
    full = H + H.mirror((1, 0, 0))
    hull = zcyl(HULL_R, -250, 250) - zcyl(HULL_R - 6.0, -251, 251)
    print("ring/hull overlap mm3:", round((full ^ hull).volume(), 2), "(should be 0; the 1 mm gap closes when bolted)")
    for mode in ("horizontal", "vertical"):
        th = place_thruster(mode)
        allth = th["housing"] + th["tail"] + th["prop"]
        print(f"{mode:10s} thruster/hull {round((allth ^ hull).volume(),2)}  thruster/ring {round((allth ^ full).volume(),2)}"
              f"  pylon/ring {round((th['pylon'] ^ full).volume(),2)}  pylon/hull {round((th['pylon'] ^ hull).volume(),2)}")
        bb = allth.bounding_box()
        print(f"           thruster spans x {bb[0]:.1f}..{bb[3]:.1f}  y {bb[1]:.1f}..{bb[4]:.1f}  z {bb[2]:.1f}..{bb[5]:.1f}"
              f"  (duct clears hull by {bb[0] - HULL_R:.1f} mm)")
    # hole alignment: pylon bolt holes must line up with the pad inserts in both modes
    for mode in ("horizontal", "vertical"):
        py = place_thruster(mode)["pylon"]
        bolts = Manifold()
        for y, z in [(dy, dz) for dy in (-B.HOLE_X, B.HOLE_X) for dz in (-B.HOLE_X, B.HOLE_X)]:
            bolts = bolts + xcyl(1.4, PAD_FACE - INSERT_L + 0.5, PAD_FACE + B.RF - PY.BLOCK_R - 0.5, y, z)
        print(f"{mode:10s} M3 bolt path through pylon+pad blocked by material: {round((bolts ^ (py + H)).volume(), 2)} mm3 (0 = aligned)")
    g = H.to_mesh(); tm = trimesh.Trimesh(g.vert_properties[:, :3], g.tri_verts)
    tm.apply_translation((0, 0, -tm.bounds[0][2]))
    tm.export("out/hull_ring_half.stl")
    print(f"hull_ring_half watertight={tm.is_watertight} bodies={len(tm.split(only_watertight=False))} size={np.round(tm.extents,1)}")
    print(f"ROV width with 2 thrusters: {2*(PAD_FACE + B.RF + T.RO):.0f} mm")
