"""
Streamlined pylon clamp for the thruster body (use with housing_no_foot).

One piece: a thin faired band around the body, a foil-section strut, and a
mounting block that sits outside the prop jet. The band is split through the
strut; 2x M4 pinch bolts in the block (outside the jet) close it on the body.
Thrust goes straight into the motor body, not through the nozzle.

Mounting face: 4x M3 through holes on a 20 x 20 mm square (bolt it on at 0 or 90 deg),
hex pockets on the top of the block for the bolt heads (or M3 nuts).
Prints standing on its trailing edge (rear end down), no supports.
Run: python3 pylon.py
"""
import numpy as np, trimesh, os
from manifold3d import Manifold, CrossSection
import thruster as T
import bracket as B

RB      = T.TUBE_R + 0.1      # band bore radius
BAND_T  = 2.5                 # band thickness
EDGE_T  = 0.8                 # band thickness at its faired edges
RAMP    = 5.0                 # fairing length at each band edge
SLOT    = 1.6                 # split width (closing it squeezes the body ~0.15 mm radius)
STRUT_T = 8.0                 # strut max thickness (NACA 4-digit, 25 %)
BLOCK_R = 38.0                # block starts here: jet edge is the duct ID, r = 37.75
BLOCK_HW = 15.0
RF      = B.RF                # mounting face radius (50.25, same as before)
Z0, Z1  = B.BZ0, B.BZ1        # 18..50, trailing edge at Z0 (jet flows toward -z)
ZC      = (Z0 + Z1)/2
PINCH_DZ, PINCH_Y = 3.0, -(BLOCK_R + 4.5)
SEG = 180

def ring():
    pts = [(RB, Z0), (RB + EDGE_T, Z0), (RB + BAND_T, Z0 + RAMP), (RB + BAND_T, Z1 - RAMP),
           (RB + EDGE_T, Z1), (RB, Z1)]
    a = sum(x0*y1 - x1*y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    return Manifold.revolve(CrossSection([pts if a > 0 else pts[::-1]]), SEG)

def foil_strut(y_top, y_bot):
    """NACA 00xx section in the x-z plane, leading edge at Z1, swept along -y"""
    c = Z1 - Z0; t = STRUT_T/c
    u = np.linspace(0, 1, 60)
    yt = 5*t*c*(0.2969*np.sqrt(u) - 0.1260*u - 0.3516*u**2 + 0.2843*u**3 - 0.1036*u**4)
    yt = np.maximum(yt, SLOT/2 + 0.8)          # each split half keeps >= 0.8 mm to the bed
    zs = Z1 - u*c
    pts = [(x, z) for x, z in zip(yt, zs)] + [(-x, z) for x, z in zip(yt[::-1], zs[::-1])]
    a = sum(x0*y1 - x1*y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    cs = CrossSection([pts if a > 0 else pts[::-1]])
    L = y_top - y_bot
    m = Manifold.extrude(cs, L).rotate((90, 0, 0))      # local (x, z) -> world (x, z); extrude -> -y
    return m.translate((0, y_top, 0))

def xcyl(r, x0, x1, y, z, seg=40):
    return Manifold.cylinder(x1 - x0, r, r, seg).rotate((0, 90, 0)).translate((x0, y, z))

def ycyl(r, y0, y1, x, z, seg=40):
    return Manifold.cylinder(abs(y1 - y0), r, r, seg).rotate((-90, 0, 0)).translate((x, min(y0, y1), z))

def pylon():
    band = ring()
    strut = foil_strut(-(RB + 1.0), -(BLOCK_R + 0.5))
    block = Manifold.cube((2*BLOCK_HW, RF - BLOCK_R, Z1 - Z0)).translate((-BLOCK_HW, -RF, Z0))
    p = band + strut + block
    p = p - Manifold.cylinder(Z1 - Z0 + 2, RB, RB, SEG).translate((0, 0, Z0 - 1))
    # split through band, strut and block
    p = p - Manifold.cube((SLOT, RF - (RB - 2) + 1, Z1 - Z0 + 2)).translate((-SLOT/2, -RF - 0.5, Z0 - 1))
    # pinch bolts: M4 clearance through, M4 heat-set insert from the -x face
    for dz in (-PINCH_DZ, PINCH_DZ):
        p = p - xcyl(2.25, -BLOCK_HW - 1, BLOCK_HW + 1, PINCH_Y, ZC + dz)
        p = p - xcyl(2.8, -BLOCK_HW - 0.01, -BLOCK_HW + 6.0, PINCH_Y, ZC + dz)
    # mounting: 4x M3 through holes on a 20 x 20 square, hex pockets on top of the block
    # (bolt heads for the hull ring, or captive M3 nuts for the kayak slide adapter)
    for x, z in B.HOLES:
        p = p - ycyl(1.7, -RF - 0.01, -BLOCK_R + 0.01, x, z)
        p = p - Manifold.cylinder(HEX_D, 6.0/np.sqrt(3), 6.0/np.sqrt(3), 6).rotate((-90, 0, 0)).rotate((0, 0, 0)) \
                .translate((x, -BLOCK_R - HEX_D + 0.01, z))
    return p

HEX_D = 3.0       # hex pocket depth (6.0 mm across flats, fits M3 nut or SHCS head)

def blockage():
    r_in, r_out = T.TUBE_R, T.RI + 0.5
    jet = Manifold.cylinder(1, r_out, r_out, SEG) - Manifold.cylinder(3, r_in, r_in, SEG).translate((0, 0, -1))
    sec = Manifold.extrude(pylon().slice(ZC), 1.0)
    return (sec ^ jet).volume(), jet.volume()

if __name__ == "__main__":
    os.makedirs("out", exist_ok=True)
    P = pylon()
    H, C, A = T.housing(foot=False), T.tail_cone(), B.slide_adapter_bracket()
    print("interference mm3: pylon/housing", round((P ^ H).volume(), 2), " pylon/cone", round((P ^ C).volume(), 2),
          " pylon/adapter", round((P ^ A).volume(), 2))
    b, j = blockage()
    print(f"jet blockage: {b:.0f} of {j:.0f} mm2 = {100*b/j:.0f}%  (bracket was 52%)")
    g = P.to_mesh(); tm = trimesh.Trimesh(g.vert_properties[:, :3], g.tri_verts)
    tm.apply_translation((0, 0, -tm.bounds[0][2]))
    tm.export("out/pylon_clamp.stl")
    print(f"pylon_clamp watertight={tm.is_watertight} bodies={len(tm.split(only_watertight=False))} size={np.round(tm.extents,1)}")
