"""
Kayak quick-release mount for the bilge thruster.
  pad_receiver : glue to hull (3M 5200 / 4200). Dovetail channel, closed at the FRONT.
  slide_adapter: bolts to the thruster foot (4x M3x12), dovetail tongue slides into pad.
  fit_coupon   : nose O-ring fit test, holes 14.4 -> 15.2 mm in 0.2 steps (notch = smallest).
Thrust is carried by the front stop; 2x M4 thumbscrews lock it (reverse + retention).
Run: python3 mount.py   (uses geometry from thruster.py)
"""
import numpy as np, trimesh, os
from manifold3d import Manifold, CrossSection, JoinType
import thruster as T

T.housing()                       # populates FOOT_FACE_Y / FOOT_HOLES
RF = -T.FOOT_FACE_Y               # foot face at y = -RF
Z1 = T.DUCT_Z1
CLR = 0.3
PLATE_T, TONGUE_D = 5.0, 7.0
T_ROOT, T_TIP = 10.0, 13.0        # dovetail half-widths
PLATE_HW = T.FOOT_W/2
PLATE_L = 62.0
PLATE_Z0 = Z1 - PLATE_L
THUMB_DZ = (7.0, 19.0)            # thumbscrews, measured from the plate's rear end
THUMB_Z = tuple(PLATE_Z0 + d for d in THUMB_DZ)
FLOOR_T = 7.5
WALL = 11.0
STOP_T = 6.0

def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube((x1-x0, y1-y0, z1-z0)).translate((x0, y0, z0))

def ycyl(r, y0, y1, x, z, seg=40):   # cylinder along y from y0 to y1
    h = abs(y1 - y0)
    return Manifold.cylinder(h, r, r, seg).rotate((-90, 0, 0)).translate((x, min(y0, y1), z))

def dovetail(hw_root, hw_tip, y_root, y_tip, z0, z1):
    pts = [(-hw_root, y_root), (hw_root, y_root), (hw_tip, y_tip), (-hw_tip, y_tip)]
    a = sum(x0*y1 - x1*y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if a < 0: pts = pts[::-1]
    return Manifold.extrude(CrossSection([pts]), z1 - z0).translate((0, 0, z0))

def rrect(w, l, r, t, y_bot, zc):
    cs = CrossSection.square((w - 2*r, l - 2*r), center=True).offset(r, JoinType.Round, circular_segments=48)
    # extrude in z, then lay flat: XY plane -> XZ plane, thickness along -y
    m = Manifold.extrude(cs, t).rotate((90, 0, 0))     # occupies y in [-t, 0]
    return m.translate((0, y_bot + t, zc))

def slide_adapter(z1=None, holes=None):
    """z1 = front (stop) end of the plate; holes = [(x, z)] M3 bolt positions"""
    z1 = Z1 if z1 is None else z1
    holes = T.FOOT_HOLES if holes is None else holes
    z0 = z1 - PLATE_L
    y_plate = -RF
    a = box(-PLATE_HW, PLATE_HW, y_plate - PLATE_T, y_plate, z0, z1)
    a = a + dovetail(T_ROOT - CLR, T_TIP - CLR, y_plate - PLATE_T + 0.01, y_plate - PLATE_T - TONGUE_D, z0, z1)
    yt = y_plate - PLATE_T - TONGUE_D
    for x, z in holes:                       # M3 SHCS, heads recessed from tongue face
        a = a - ycyl(1.7, yt - 1, y_plate + 1, x, z)
        a = a - ycyl(3.0, yt - 1, y_plate - PLATE_T + 0.2, x, z)
    for dz in THUMB_DZ:                             # M4 thumbscrew clearance
        a = a - ycyl(2.25, yt - 1, y_plate + 1, 0, z0 + dz)
    return a

def pad_receiver(z1=None):
    """same part for every configuration; z1 only positions it for fit checks"""
    if z1 is not None:
        return pad_receiver().translate((0, 0, z1 - Z1))
    y_floor = -RF - PLATE_T - TONGUE_D - CLR
    y_open = -RF - PLATE_T - CLR
    y_bot = y_floor - FLOOR_T
    hw_out = T_TIP + WALL
    zb0, zb1 = PLATE_Z0 - 2, Z1 + CLR + STOP_T
    blk = box(-hw_out, hw_out, y_bot, y_open, zb0, zb1)
    chan = dovetail(T_TIP, T_ROOT, y_floor, y_open + 0.01, zb0 - 1, Z1 + CLR)
    blk = blk - chan
    for z in THUMB_Z:                               # M4 heat-set inserts in floor
        blk = blk - ycyl(2.8, y_floor - 6.0, y_floor + 0.01, 0, z)
    # feathered glue pad (stepped taper)
    zc = (zb0 + zb1)/2
    pad = Manifold()
    for w, l, t in ((110, 130, 1.2), (96, 116, 2.0), (82, 100, 2.8)):
        pad = pad + rrect(w, l, 12, t, y_bot - 2.8, zc)
    return blk + pad

def fit_coupon():
    holes = np.arange(14.4, 15.21, 0.2)
    pitch = 19.0
    L = pitch*len(holes) + 4
    c = Manifold.cube((L, 20, 8)).translate((0, -10, 0))
    for i, d in enumerate(holes):
        c = c - Manifold.cylinder(9, d/2, d/2, 96).translate((pitch*i + pitch/2 + 2, 0, 1.5))
    c = c - Manifold.cube((3, 3, 10)).translate((-1.5, -1.5, -1))     # notch at smallest end
    return c

def export(m, name):
    g = m.to_mesh(); tm = trimesh.Trimesh(g.vert_properties[:, :3], g.tri_verts)
    tm.apply_translation(-tm.bounds[0] * np.array([0, 0, 1]))
    tm.export(f"out/{name}.stl")
    print(f"{name:14s} watertight={tm.is_watertight} bodies={len(tm.split(only_watertight=False))} size={np.round(tm.extents,1)}")
    return tm

if __name__ == "__main__":
    os.makedirs("out", exist_ok=True)
    A, P = slide_adapter(), pad_receiver()
    # print orientations: adapter plate-face down (tongue up); pad bottom down
    export(A.rotate((-90, 0, 0)), "slide_adapter")
    export(P.rotate((90, 0, 0)), "pad_receiver")
    export(fit_coupon(), "nose_fit_coupon")
    # interference check against housing
    H = T.housing()
    print("adapter∩housing vol:", round((A ^ H).volume(), 2), " pad∩adapter vol:", round((P ^ A).volume(), 2), " pad∩housing:", round((P ^ H).volume(), 2))
