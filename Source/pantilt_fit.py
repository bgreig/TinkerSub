"""
Camera pan-tilt that fits the real 4" dome: parts 216 base, 217 yoke, 218 cradle, 219 tilt lever.
Arducam for Pi Zero (Pi Camera v2 board, 25 x 23.9 mm), two SG90 / MG90S micro servos.

Hull coordinates (mm): x + = port, y + = up, z + = forward, 0 = hull centre (same as rov_assembly).
Fixed by the hull (measured from the assembly CAD):
  front bulkhead 207 inner face z 145, 4.8 thick; rods (94 mm circle, 45 deg) end at z 164.1 in the dome flange inserts
  dome flange 203 skirt: bore r 42.9 from z 164.2 to 213.2; dome retaining ring bore r 50.5
  dome: UQISOVI 4" acrylic CCTV dome (Amazon B0DR2HP4YQ): 99.8 OD / 96 ID hemisphere (1.9 mm wall), 5.1 mm straight
        skirt, 2 mm flange 115 OD; 57 mm overall. Flange sits on 203's face (z 213.2), so the sphere centre is at z 220.3.
        (Until 2026-10-15 the model used a flangeless 2.5 mm-wall dome centred at z 215.2.)
Layout:
  216 base sits on the four rods in front of the bulkhead (back face z 152.2, on a nut), carries the pan servo on a shelf
      under the dome centre, shaft vertical through the lens.
  217 yoke turns on the pan horn. The tilt servo stands on the yoke BEHIND the camera (shaft along x) and drives the
      cradle through a 1 mm wire pushrod and lever 219 (a parallelogram, so tilt is 1:1). A side-mounted tilt servo,
      as in the usual kits, puts its far end 45 mm from the lens: that hits a 47.4 mm dome.
  218 cradle carries the camera; pivots on two pins through the yoke arms, the +x pin is a D-axle that keys lever 219.
The lens sits on the pan and tilt axes, LENS_Y above the hull axis, at the dome centre in z.
"""
import numpy as np, trimesh, json, sys
from manifold3d import Manifold, CrossSection
from rov_parts import box, cyl, ycyl, xcyl

# ---------------- hull limits
import os
ZD = 220.3; R_DOME = 48.0                     # real dome: sphere centre z, inner radius (skirt bore is the same 48)
ZC = float(os.environ.get("PT_ZC", ZD))       # lens z = pan and tilt axes (on the dome centre)
R_FL = 42.9; Z_FL0, Z_FL1 = 164.2, 213.2; R_PIPE = 51.13
ROD = 94.0 / 2 / np.sqrt(2)
Z_BASE = 152.2                      # base back face: bulkhead outer face 149.8 + one M3 nut
# ---------------- layout
LENS_Y = 9.5                        # lens = pan and tilt axes, above the hull axis
YH = -10.5                          # pan horn outer face
# SG90 envelope
SV_W, SV_L, SV_H = 12.4, 23.0, 22.7
SV_TAB_L, SV_TAB_T, SV_BOT_TAB, SV_BOT_HORN, SV_SHAFT_END, SV_TAB_HOLE = 32.6, 2.5, 15.9, 30.5, 5.9, 27.8
PILOT = 1.7
# camera board (Pi Camera v2 footprint)
CB_W, CB_H, CB_LENS_TOP = 25.0, 23.9, 9.46
CB_HOLE_DX, CB_HOLES_TOP = 21.0, (2.0, 14.5)

# ---------------- pan servo (fixed): shaft along +y at (x 0, z ZC), body runs aft
PB_Y0 = YH - SV_BOT_HORN                         # body bottom
PB_Z0, PB_Z1 = ZC - (SV_L - SV_SHAFT_END), ZC + SV_SHAFT_END
PB_ZC = (PB_Z0 + PB_Z1) / 2
P_TAB = PB_Y0 + SV_BOT_TAB                       # underside of the tabs
def pan_servo():
    b = box(-SV_W/2, SV_W/2, PB_Y0, PB_Y0 + SV_H, PB_Z0, PB_Z1)
    b = b + box(-SV_W/2, SV_W/2, P_TAB, P_TAB + SV_TAB_T, PB_ZC - SV_TAB_L/2, PB_ZC + SV_TAB_L/2)
    return b + ycyl(2.5, PB_Y0 + SV_H, YH - 1.5, 0, ZC)
def pan_horn():
    return ycyl(3.8, YH - 1.5, YH, 0, ZC) + box(-16.5, 16.5, YH - 1.5, YH, ZC - 3, ZC + 3)   # double-arm horn, turns with the yoke

# ---------------- tilt servo (on the yoke): shaft along +x at (y TY_S, z TZ_S), body length along y
TY_S = 10.0                                      # (v2, 2026-10-16: was 6; body now sits ON the yoke base, nothing cut through it)
T_X0 = -10.0                                     # body bottom face (servo's back)
T_TAB = T_X0 + SV_BOT_TAB
T_Y0, T_Y1 = TY_S - (SV_L - SV_SHAFT_END), TY_S + SV_SHAFT_END
T_YC = (T_Y0 + T_Y1) / 2
TZ_S = ZC - 28.0                                 # shaft z (body centre across its width): 28 mm pushrod behind the lens
T_Z0, T_Z1 = TZ_S - SV_W/2, TZ_S + SV_W/2
HORN_X = T_X0 + SV_BOT_HORN                      # 20.5
ARM = 8.0                                       # horn arm and lever length (pushrod 10 mm below the axes)
def tilt_servo(angle=0.0):
    b = box(T_X0, T_X0 + SV_H, T_Y0, T_Y1, T_Z0, T_Z1)
    b = b + box(T_TAB, T_TAB + SV_TAB_T, T_YC - SV_TAB_L/2, T_YC + SV_TAB_L/2, T_Z0, T_Z1)
    b = b + xcyl(2.5, T_X0 + SV_H, HORN_X, TY_S, TZ_S)
    arm = (xcyl(3.8, HORN_X - 1.5, HORN_X, 0, 0) + box(HORN_X - 1.5, HORN_X, -ARM - 2.5, 0, -2.5, 2.5))
    return b + arm.rotate((angle, 0, 0)).translate((0, TY_S, TZ_S))

# ---------------- camera on the cradle (moves with tilt): board front 3 mm behind the lens tip plane
B_TOP = LENS_Y + CB_LENS_TOP; B_BOT = B_TOP - CB_H
B_FRONT = ZC - 3.0
def camera():
    c = box(-CB_W/2, CB_W/2, B_BOT, B_TOP, B_FRONT - 1.0, B_FRONT)
    c = c + box(-4.2, 4.2, LENS_Y - 4.2, LENS_Y + 4.2, B_FRONT, B_FRONT + 2.5) + cyl(3.6, 2.0, B_FRONT + 2.5).translate((0, LENS_Y, 0))
    return c + box(-10, 10, B_BOT + 1, B_TOP - 4, B_FRONT - 2.6, B_FRONT - 1.0)          # parts on the back
PL_Z1 = B_FRONT - 1.0 - 2.0                      # 2 mm standoffs
PL_Z0 = PL_Z1 - 2.0
CHEEK = ((13.0, 15.0), (-15.0, -13.0))
ARM_X = ((15.5, 18.5), (-18.5, -15.5))           # yoke arms
AXLE_R = 2.5
LEVER_X = (19.0, 21.0)

def cradle():
    c = box(-13.0, 13.0, B_BOT - 0.3, B_TOP + 0.3, PL_Z0, PL_Z1)
    for x0, x1 in CHEEK:
        ch = box(x0, x1, B_BOT - 0.3, B_TOP + 0.3, PL_Z0, PL_Z0 + 4.0)
        ch = ch + box(x0, x1, LENS_Y - 5, LENS_Y + 5, PL_Z0, ZC) + xcyl(5.0, x0, x1, LENS_Y, ZC)
        c = c + ch
    c = c - xcyl(PILOT/2, -16.0, -12.0, LENS_Y, ZC)                                  # -x: M2 pivot screw
    ax = xcyl(AXLE_R, 14.5, LEVER_X[1], LENS_Y, ZC) - box(14, 22, LENS_Y + 1.6, LENS_Y + 3, ZC - 3, ZC + 3)   # D-axle
    c = c + ax - xcyl(PILOT/2, 16.0, LEVER_X[1] + 1, LENS_Y, ZC)                       # M2 x 6 holds the lever
    for dx in (CB_HOLE_DX/2, -CB_HOLE_DX/2):
        for dt in CB_HOLES_TOP:
            c = c - cyl(1.1, 10, PL_Z0 - 5).translate((dx, B_TOP - dt, 0))
    c = c - box(-9, 9, B_BOT + 0.8, B_BOT + 4.8, PL_Z0 - 1, PL_Z1 + 1)               # ribbon slot
    return c

def lever():
    l = xcyl(4.5, *LEVER_X, LENS_Y, ZC) + box(LEVER_X[0], LEVER_X[1], LENS_Y - ARM - 2.5, LENS_Y, ZC - 3, ZC + 3)
    l = l + xcyl(3.0, *LEVER_X, LENS_Y - ARM, ZC)
    hole = xcyl(AXLE_R + 0.15, LEVER_X[0] - 1, LEVER_X[1] + 1, LENS_Y, ZC) - box(18, 23, LENS_Y + 1.6 + 0.0, LENS_Y + 4, ZC - 4, ZC + 4)
    return l - hole - xcyl(0.65, LEVER_X[0] - 1, LEVER_X[1] + 1, LENS_Y - ARM, ZC)

# ---------------- yoke (moves with pan)
Y_B0, Y_B1 = YH - 1.6, YH + 3.4                  # base: 1.6 mm horn pocket underneath, 3.4 above
def yoke():
    """v2 (2026-10-16). v1 held the tilt servo in a 3 mm frame whose two 3 mm posts stood on the base right where the
    servo body and its lower tab were cut through it, so the frame snapped off at its root. v2: the servo sits ON a solid
    base and is boxed in by a cup (back wall, both side walls, roof), all rooted on the base over their full length;
    pushrod loads now go into the cup walls, and the M2 tab screw only stops the servo sliding out (+x)."""
    base = box(-18.5, 18.5, Y_B0, Y_B1, ZC - 8, ZC + 7.5)
    base = base + box(CUP_X0, CUP_X1 - 0.3, Y_B0, Y_B1, CUP_Z0, ZC - 7)                # tail under the cup, ends at the tab face
    y = base
    cup = box(CUP_X0, CUP_X1, Y_B1 - 0.5, T_Y1 + CUP_T, CUP_Z0, CUP_Z1)                 # back + side walls + roof
    cup = cup + box(CUP_X1 - FACE_T, CUP_X1, Y_B1 - 0.5, T_YC + SV_TAB_HOLE/2 + 2.2, CUP_Z0, CUP_Z1)   # tab face up to the screw
    cup = cup - box(T_X0 - 0.3, CUP_X1 + 1, T_Y0 - 0.3, T_Y1 + 0.3, T_Z0 - 0.25, T_Z1 + 0.25)     # servo pocket, open to +x
    cup = cup - xcyl(PILOT/2, CUP_X1 - 7, CUP_X1 + 1, T_YC + SV_TAB_HOLE/2, TZ_S)       # M2 x 8 through the upper tab
    # 45-degree fillets along the cup's root on both outer side walls and the back wall
    for z0, z1, sz in ((CUP_Z0 - 4.0, CUP_Z0, -1), (CUP_Z1, CUP_Z1 + 4.0, 1)):
        g = Manifold.extrude(CrossSection([[(0, 0), (4.0, 0), (0, 4.0)]]), CUP_X1 - CUP_X0 - 0.3)   # (z-ish, y) triangle, along x
        g = g.transform([[0, 0, 1, CUP_X0], [0, 1, 0, Y_B1], [-sz, 0, 0, (CUP_Z0 if sz < 0 else CUP_Z1)]])
        cup = cup + (g ^ box(CUP_X0, CUP_X1, Y_B1 - 1, Y_B1 + 5, z0, z1))
    g = Manifold.extrude(CrossSection([[(0, 0), (4.0, 0), (0, 4.0)]]), CUP_Z1 - CUP_Z0)
    cup = cup + (g.transform([[-1, 0, 0, CUP_X0], [0, 1, 0, Y_B1], [0, 0, 1, CUP_Z0]]) ^ box(CUP_X0 - 4, CUP_X0, Y_B1 - 1, Y_B1 + 5, CUP_Z0, CUP_Z1))
    # 2.5 mm chamfers on the roof's back and far edges: that corner passes closest to the dome-flange bore when panned
    top = T_Y1 + CUP_T
    w = Manifold.extrude(CrossSection([[(0, 0), (3.5, 0), (0, 3.5)]]), 80).translate((0, 0, -40))
    cup = cup - w.transform([[1, 0, 0, CUP_X0], [0, -1, 0, top], [0, 0, 1, 190]])           # along z at the back-top edge
    cup = cup - w.transform([[0, 0, 1, 0], [0, -1, 0, top], [1, 0, 0, CUP_Z0]])              # along x at the far-top edge
    y = y + cup
    # servo lead: leaves the bottom end of the servo near its back; slot through the base, open to the front so it slides in
    y = y - box(T_X0 - 0.5, CUP_X1 + 1, Y_B0 - 1, Y_B1 + 0.1, TZ_S - 2.6, TZ_S + 2.6)
    # arms with the tilt pivots
    for x0, x1 in ARM_X:
        a = box(x0, x1, Y_B0, LENS_Y + 6.0, ZC - 6.5, ZC + 6.5) + xcyl(6.5, x0, x1, LENS_Y, ZC)
        # v2: 3 mm 45-degree fillet along the outside of each arm's root
        sx = 1 if x0 > 0 else -1; xo = x1 if sx > 0 else x0
        g = Manifold.extrude(CrossSection([[(0, 0), (3.0, 0), (0, 3.0)]]), 13.0).translate((0, 0, ZC - 6.5))
        a = a + g.transform([[sx, 0, 0, xo], [0, 1, 0, Y_B1], [0, 0, 1, 0]])
        y = y + a
    y = y - xcyl(1.2, -19.5, -14.5, LENS_Y, ZC)                                       # M2 clearance (-x)
    y = y - xcyl(AXLE_R + 0.25, 14.5, 19.5, LENS_Y, ZC)                               # axle bearing (+x)
    # relief under the camera's tilt sweep
    y = y - box(-15.2, 15.2, Y_B1 - 1.6, Y_B1 + 1, ZC - 19, ZC + 7.6)
    # pan horn pocket + screw access + horn screw pilots
    y = y - (box(-17.2, 17.2, Y_B0 - 1, Y_B0 + 1.6, ZC - 3.3, ZC + 3.3) + ycyl(4.3, Y_B0 - 1, Y_B0 + 1.6, 0, ZC))
    y = y - ycyl(2.8, Y_B0 - 1, Y_B1 + 1, 0, ZC)
    for dx in (-13.0, -9.0, 9.0, 13.0): y = y - ycyl(0.75, Y_B0 - 1, Y_B1 + 1, dx, ZC)
    return y
CUP_T, FACE_T = 2.5, 3.5
CUP_X0, CUP_X1 = T_X0 - CUP_T, T_TAB                      # back wall .. tab face (tabs bear on it)
CUP_Z0, CUP_Z1 = T_Z0 - CUP_T, T_Z1 + 2.0

# ---------------- base (fixed)
SH_Y1 = P_TAB; SH_Y0 = SH_Y1 - 3.0
def base():
    p = cyl(R_PIPE - 1.3, 4.0, Z_BASE, 160)
    p = p - box(-15, 15, -6, 30, Z_BASE - 1, Z_BASE + 5)                              # ribbon + servo leads
    for sx in (1, -1):
        for sy in (1, -1):
            p = p - cyl(1.7, 6, Z_BASE - 1, 24).translate((sx*ROD, sy*ROD, 0))
    shelf = box(-10.5, 10.5, SH_Y0, SH_Y1, Z_BASE + 4, PB_ZC + SV_TAB_L/2 + 2.5)
    shelf = shelf - box(-SV_W/2 - 0.2, SV_W/2 + 0.2, SH_Y0 - 1, SH_Y1 + 1, PB_Z0 - 0.2, PB_Z1 + 0.2)
    for dz in (SV_TAB_HOLE/2, -SV_TAB_HOLE/2): shelf = shelf - ycyl(PILOT/2, SH_Y0 - 1, SH_Y1 + 1, 0, PB_ZC + dz)
    webs = box(7.0, 10.5, -38.0, SH_Y0, Z_BASE + 4, PB_Z0 - 1) + box(-10.5, -7.0, -38.0, SH_Y0, Z_BASE + 4, PB_Z0 - 1)
    # (2026-10-20, v2) ribs carried on beside the servo body to the end of the shelf: the 4 x 3 mm rails either side of the
    # servo window were the only thing holding the pan servo, layer lines across them (the failure mode of yoke v1)
    end = PB_ZC + SV_TAB_L/2 + 2.5
    webs = webs + box(6.9, 10.5, -38.0, SH_Y0, PB_Z0 - 2, end) + box(-10.5, -6.9, -38.0, SH_Y0, PB_Z0 - 2, end)
    return p + shelf + webs

# ---------------- checks
def allowed(margin=1.0):
    a = cyl(R_PIPE - margin, Z_FL0 - Z_BASE + 1, Z_BASE - 1, 160)
    a = a + cyl(R_FL - margin, Z_FL1 - Z_FL0, Z_FL0, 160) + cyl(R_DOME - margin, ZD - Z_FL1, Z_FL1, 160)   # dome flange ID + skirt
    s = Manifold.sphere(R_DOME - margin, 160).translate((0, 0, ZD)) ^ box(-60, 60, -60, 60, ZD, ZD + 60)
    return a + s
def R_pan(m, th): return m.translate((0, 0, -ZC)).rotate((0, th, 0)).translate((0, 0, ZC))
def R_tilt(m, ph): return m.translate((0, -LENS_Y, -ZC)).rotate((ph, 0, 0)).translate((0, LENS_Y, ZC))

def check(pans=range(-90, 91, 5), tilts=range(-50, 51, 5)):
    A = allowed(); fixed = base() + pan_servo()
    Y = yoke(); C = cradle() + camera() + lever()
    ok_pan, ok_tilt = [], []
    for ph in tilts:                                  # tilt vs yoke, tilt servo and its horn (horn follows tilt)
        mov = R_tilt(C, ph); ys = Y + tilt_servo(ph)
        bad = (mov ^ ys).volume()
        out = (mov - A).volume()
        ok_tilt.append((ph, round(bad, 1), round(out, 1)))
    for th in pans:
        worst = 0.0
        for ph in (-45, 0, 45):
            asm = R_pan(Y + pan_horn() + tilt_servo(ph) + R_tilt(C, ph), th)
            worst = max(worst, (asm - A).volume(), (asm ^ fixed).volume())
        ok_pan.append((th, round(worst, 1)))
    return ok_pan, ok_tilt

if __name__ == "__main__":
    pans, tilts = check()
    print("lens z", ZC, " dome centre z", ZD, " tilt servo shaft z", TZ_S)
    print("base 216 outside hull mm3:", round((base() - allowed()).volume(), 1), " (fixed parts) pan servo outside:", round((pan_servo() - allowed()).volume(), 1))
    print("tilt (deg, hit yoke mm3, outside hull mm3):", tilts)
    print("pan  (deg, worst mm3):", pans)

def export(out="out_final"):
    import os
    def save(name, m):
        g = m.to_mesh(); t = trimesh.Trimesh(g.vert_properties[:, :3], g.tri_verts)
        b = t.bounds; t.apply_translation([-(b[0][0] + b[1][0]) / 2, -(b[0][1] + b[1][1]) / 2, -b[0][2]])
        t.export(f"{out}/{name}.stl"); print(name, t.is_watertight, np.round(t.extents, 1))
    save("pantilt_base", base())                               # plate face down, shelf standing up
    save("pantilt_yoke", yoke().rotate((90, 0, 0)))            # base down (hull y -> print z)
    save("pantilt_cradle", cradle().rotate((0, -90, 0)))       # on its -x cheek: the +x axle prints vertical
    save("pantilt_lever", lever().rotate((0, -90, 0)))         # flat
