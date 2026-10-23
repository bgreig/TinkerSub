"""
v5 LOOK CONCEPT: side plates + top cowl + belly pan around the v4 hull, pod and thrusters.
  side plates   1/2" HDPE (or printed sections), full length, bottom edge is the skid, jet windows at the corners
  top cowl      flooded printed fairing in ROV yellow over the hull: hides the junction boxes and cables,
                lights flush in the nose, foam core inside sized for trim, holes over the vertical thrusters
  stations      two printed ring frames (z +-60) clamp hull + pod and bolt to both plates
  belly pan     flooded box under the pod between the plates, lead inside
Thrusters are turned 180 deg about their own axis so the pylons face out and bolt to the plates.
Writes rov_viewer/assembly_v5.json and runs the clash check.
"""
import sys, json, base64, itertools, os
import numpy as np
from manifold3d import Manifold, CrossSection
import rov_assembly as A, frame_clamp as FC, lights as LT, rov_parts as RP, pylon as PY

Tm, Rz, Ry, Rx = A.Tm, A.Rz, A.Ry, A.Rx
def cyl(r, z0, z1, n=96): return Manifold.cylinder(z1 - z0, r, r, n).translate((0, 0, z0))
def box(x0, x1, y0, y1, z0, z1): return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))
def rrect(u0, u1, v0, v1, r):
    return CrossSection.square((u1 - u0 - 2*r, v1 - v0 - 2*r)).translate((u0 + r, v0 + r)).offset(r, circular_segments=48)
def side_extrude(cs, x0, x1):
    """cross-section drawn in (u = -z, v = y), extruded along x from x0 to x1"""
    return Manifold.extrude(cs, x1 - x0).rotate((0, 90, 0)).translate((x0, 0, 0))
def front_extrude(cs, z0, z1):
    """cross-section drawn in (x, y), extruded along z"""
    return Manifold.extrude(cs, z1 - z0).translate((0, 0, z0))

# ---------------- thrusters: same positions, pylons turned to face out
THR = []
for kind, M, side in A.THR:
    M2 = M @ Rz(180)
    face = (M2 @ np.array([0, -PY.RF, 34.0, 1]))[:3]
    corners = [(M2 @ np.array([dx, -PY.RF, 34.0 + dz, 1]))[:3] for dx in (-17, 17) for dz in (-17, 17)]
    THR.append((kind, M2, side, face, corners))
XP = max(max(abs(c[0]) for c in t[4]) for t in THR if t[0] == "V") + 1.0     # plate inner face
T_PL = 12.7
print("plate inner face x =", round(XP, 1))

# ---------------- side plate (one solid plate per side, then cut into 6 printable pieces)
PZ0, PZ1, PY0, PY1 = -238.0, 240.0, -202.0, 98.0   # 300 mm tall: two plates fit a 24 x 24 in sheet
SEAM_Z = (-95.0, 95.0)                                      # butt seams, joined by splice strips on the inner face
SEAM_Y, LAP = 15.0, 10.0                                    # half-lap seam between upper and lower rows
def poly_zy(pts):                                           # polygon from (z, y) points, in plate (u = -z, v = y) coords
    p = [[-z, y] for z, y in pts]
    a = sum(x0*y1 - x1*y0 for (x0, y0), (x1, y1) in zip(p, p[1:] + p[:1]))
    return CrossSection([p if a > 0 else p[::-1]])
def rounded(cs, r): return cs.offset(-r, circular_segments=32).offset(r, circular_segments=32)
def circ(z, y, r): return CrossSection.circle(r, 32).translate((-z, y))
JET = []
for kind, M2, side, face, corners in THR:
    if kind != "H" or side < 0: continue
    p = (M2 @ np.array([0, 0, 52.0, 1]))[:3]; a = M2[:3, 2]
    hit = p + a*((XP - p[0]) / a[0]); JET.append((hit[2], hit[1]))
def plate_outline():
    return rounded(poly_zy([(-212, PY0), (212, PY0), (240, -176), (240, 30), (200, PY1), (-200, PY1), (-238, 62), (-238, -176)]), 16)
def plate_windows():
    w = []
    for z, y in JET:                                        # jet windows (corner thrusters), kept clear of the vertical pylon pads
        w.append(CrossSection.circle(1.0, 64).scale((54.0, 52.0)).translate((-(np.sign(z)*82.0), y)))
    w.append(rounded(poly_zy([(-45, -183), (45, -183), (45, -140), (-45, -140)]), 12))
    for sz in (1, -1):
        w.append(rounded(poly_zy([(sz*124, -185), (sz*200, -185), (sz*222, -163), (sz*222, -118), (sz*124, -118)]), 10))
        w.append(rounded(poly_zy([(sz*120, 34), (sz*182, 34), (sz*182, 64), (sz*158, 82), (sz*120, 82)]), 10))
    return w
_out = plate_outline(); _win = plate_windows()
_solid = _out
for h in _win: _solid = _solid - h
def solid_at(z, y, r=6.0):
    d = circ(z, y, r); return abs((d ^ _solid).area() - d.area()) < 0.5
# bolt holes (z, y, radius)
HOLES = []
ARM_Y = (10.0, -142.0)
for zc in (-60.0, 60.0):                                    # station arms: 2x M5 per arm into heat-set inserts in the arm ends
    for yc in ARM_Y:
        for dz in (-6.0, 6.0): HOLES.append((zc + dz, yc, 2.75, "arm"))
BRK_HOLES = []
for kind, M2, side, face, corners in THR:                   # corner brackets: 2x M5 through the plate into the bracket
    if kind == "H" and side > 0:
        zc = float(np.mean([c[2] for c in corners])); yc = float(face[1])
        for dz in (-14.0, 14.0): HOLES.append((zc + dz, yc, 2.75, "brk")); BRK_HOLES.append((zc + dz, yc))
    if kind == "V" and side > 0:                            # vertical pylons: 4x M3 straight through the plate
        for hx, hz in ((-10, 24), (10, 24), (-10, 44), (10, 44)):
            q = (M2 @ np.array([hx, -PY.RF, hz, 1]))[:3]; HOLES.append((q[2], q[1], 1.7, "pylon"))
for z in np.arange(-225.0, 230.0, 30.0):                    # half-lap seam bolts, M4
    if solid_at(z, SEAM_Y, 7) and all(abs(z - sz) > 12 for sz in SEAM_Z): HOLES.append((z, SEAM_Y, 2.2, "lap"))
STRIPS = []                                                 # splice strips on the inner face: (z0, z1, y0, y1)
for sz in SEAM_Z:
    STRIPS += [(sz - 20, sz + 20, -200, -125), (sz - 20, sz + 20, -4, 28)]
for z0, z1, y0, y1 in STRIPS:
    for zz in (z0 + 9, z1 - 9):
        for yy in ((y0 + 12, y1 - 12) if y1 - y0 > 40 else ((y0 + y1)/2,)): HOLES.append((zz, yy, 2.2, "splice"))
COWL_SCREWS = [(-200.0, 36.0), (-40.0, 36.0), (40.0, 36.0), (215.0, 36.0)]   # (2026-10-20) rear was -215: 3 mm behind the cowl (CZ0 -212), so it held nothing
for z, y in COWL_SCREWS: HOLES.append((z, y, 1.7, "cowl"))
def plate_cs():
    cs = _solid
    for z, y, r, _ in HOLES: cs = cs - circ(z, y, r)
    return cs
plate_r = side_extrude(plate_cs(), XP, XP + T_PL)
plate_l = plate_r.mirror((1, 0, 0))

def plate_pieces(plate, sgn):
    """6 pieces: rows split at SEAM_Y with a half lap (upper row keeps the outer half in the lap band), columns butt at SEAM_Z."""
    xi, xo = sorted((sgn*XP, sgn*(XP + T_PL)))
    xmid = sgn*(XP + T_PL/2)
    outer_half = box(*sorted((xmid, sgn*(XP + T_PL + 1))), -400, 400, -400, 400)
    inner_half = box(*sorted((sgn*(XP - 1), xmid)), -400, 400, -400, 400)
    up = box(-400, 400, SEAM_Y + LAP, 400, -400, 400) + (box(-400, 400, SEAM_Y - LAP, SEAM_Y + LAP, -400, 400) ^ outer_half)
    lo = box(-400, 400, -400, SEAM_Y - LAP, -400, 400) + (box(-400, 400, SEAM_Y - LAP, SEAM_Y + LAP, -400, 400) ^ inner_half)
    cols = {"rear": (-400, SEAM_Z[0]), "mid": (SEAM_Z[0], SEAM_Z[1]), "front": (SEAM_Z[1], 400)}
    out = {}
    for cn, (z0, z1) in cols.items():
        c = box(-400, 400, -400, 400, z0 + (0.3 if z0 > -400 else 0), z1 - (0.3 if z1 < 400 else 0))
        out[f"upper_{cn}"] = plate ^ up ^ c
        out[f"lower_{cn}"] = plate ^ lo ^ c
    return out
def strips(sgn):
    out = []
    for z0, z1, y0, y1 in STRIPS:
        st = box(*sorted((sgn*(XP - 6), sgn*XP)), y0, y1, z0, z1)
        for zz in (z0 + 9, z1 - 9):
            for yy in ((y0 + 12, y1 - 12) if y1 - y0 > 40 else ((y0 + y1)/2,)):
                st = st - Manifold.cylinder(10, 2.2, 2.2, 24).rotate((0, 90, 0)).translate((sgn*XP - 8, yy, zz))
        out.append(("lower" if y0 < -100 else "upper", st))
    return out

# ---------------- thruster brackets: hull of the pylon face and a matching patch on the plate (one part per thruster)
BRK = []                                                    # (key, manifold in world coords)
for i, (kind, M2, side, face, corners) in enumerate(THR):
    if kind == "V": continue                                # verticals bolt straight to the plate (1 mm shim)
    sgn = np.sign(face[0])
    pts = [Manifold.cube((0.5, 0.5, 0.5)).translate(tuple(c - 0.25)) for c in corners]
    px = XP - 0.5 if sgn > 0 else -XP
    pts += [Manifold.cube((0.5, 0.5, 0.5)).translate((px, c[1] - 0.25, c[2] - 0.25)) for c in corners]
    for c in corners:                                       # widen the plate patch along z so the wedge is a solid gusset
        for dz in (-22, 22):
            pts.append(Manifold.cube((0.5, 0.5, 0.5)).translate((px, c[1] - 0.25, c[2] + dz - 0.25)))
    b = Manifold.batch_hull(pts)
    b = b - box(-300, 300, -PY.RF, 600, -300, 300).transform(M2[:3, :])      # keep only the side beyond the pylon face
    for hx, hz in ((-10, 24), (10, 24), (-10, 44), (10, 44)):                 # 4x M3 heat-set inserts for the pylon
        b = b - Manifold.cylinder(7, 2.0, 2.0, 24).translate((hx, 0, hz)).rotate((90, 0, 0)).translate((0, -PY.RF, 0)).transform(M2[:3, :]) \
            if False else b - Manifold.cylinder(14.0, 2.0, 2.0, 24).translate((0, 0, -7.0)).rotate((90, 0, 0)).translate((hx, -PY.RF, hz)).transform(M2[:3, :])
    zc = float(np.mean([c[2] for c in corners])); yc = float(face[1])
    for dz in (-14.0, 14.0):                                                  # 2x M5 heat-set inserts from the plate side
        b = b - Manifold.cylinder(10.0, 3.2, 3.2, 24).rotate((0, 90, 0)).translate((sgn*XP - 10.0 if sgn > 0 else sgn*XP, yc, zc + dz))
    front = face[2] > 0
    key = "brk_corner_a" if (front and sgn > 0) or (not front and sgn < 0) else "brk_corner_b"
    BRK.append((key, b))

# ---------------- station frames (z = +-60): clamp halves like the v4 clamps, plus arms to the plates
#   top    = hull top half + upper arms + junction-box deck (split port / starboard, bolted rib on the centreline)
#   middle = hull bottom half + web + pod top half
#   bottom = pod bottom half + lower arms (split port / starboard)
ST_W = 24.0
R_H, R_P = A.FC.R_IN, FC.POD4_R
DECK_Y, DECK_T = 72.0, 5.0
ST_Z = (-60.0, 60.0)                     # station centres (world z); also set below
JB_ZC = -88.0                            # junction box centre (world z): front thruster plugs clear the cowl's vertical-thruster ducts
DECK_Z = (JB_ZC - ST_Z[0] + ST_W/2 - 58.0, JB_ZC - ST_Z[0] + ST_W/2 + 58.0)   # station-local z under the 116 mm box
def arm(sgn, y0, y1, x_in, yc):
    a = box(*sorted((sgn*x_in, sgn*XP)), y0, y1, 0, ST_W)
    for dz in (-6.0, 6.0):                                                    # 2x M5 heat-set inserts in the arm end
        # (2026-10-23) at yc = the side plate's hole height (ARM_Y). The top arm used to put them at its mid-height
        # (9.25), 0.75 mm below the plate holes (10.0): more than an M5's play in a 5.5 mm hole.
        a = a - Manifold.cylinder(10.0, 3.2, 3.2, 24).rotate((0, 90, 0)).translate((sgn*XP - 10.0 if sgn > 0 else sgn*XP, yc, ST_W/2 + dz))
    return a
def st_top():
    s = RP.clamp_half(R_H, 6.0, ST_W, top=True)[0]
    for sgn in (-1, 1):
        s = s + arm(sgn, 0.5, 18, 40, ARM_Y[0])
        s = s + box(*sorted((sgn*36, sgn*44)), 40, DECK_Y, 0, ST_W)            # deck ribs
        s = s - RP.ycyl(2.25, -1, 19, sgn*(R_H + 6 + 5), ST_W/2)               # clamp bolt runs up through the arm
    s = s + box(-6, 6, R_H + 2, DECK_Y, 0, ST_W)                              # centre rib
    s = s - cyl(R_H, -1, ST_W + 1, 200)
    # (2026-10-23) M3 through the centre rib (joins the halves). Was M4 at DECK_Y - 6: the clamp ring's outside is 3.2 mm
    # below that axis, too close for an M4 head or nut (3.5). An M3 head / nyloc fits here and in the old 4.5 mm hole.
    s = s - RP.xcyl(1.7, -8, 8, DECK_Y - 5, ST_W/2)
    for sgn in (-1, 1): s = s - RP.ycyl(2.0, DECK_Y - 8, DECK_Y + 1, sgn*40, ST_W/2)   # M3 inserts: junction deck screws
    return s
def junction_deck():
    """separate flat plate screwed onto the rear station's ribs; the junction box (501) screws to it"""
    d = box(-52, 52, DECK_Y, DECK_Y + DECK_T, *DECK_Z)
    for sgn in (-1, 1): d = d - RP.ycyl(1.7, DECK_Y - 1, DECK_Y + DECK_T + 1, sgn*40, ST_W/2)
    for x in (-20.0, 20.0):                                                   # junction box screws: M3 inserts
        for dz in (-36.0, 36.0): d = d - RP.ycyl(2.0, DECK_Y - 1, DECK_Y + DECK_T + 1, x, ST_W/2 + (JB_ZC - ST_Z[0]) + dz)
    return d
def st_mid():
    s = RP.clamp_half(R_H, 6.0, ST_W, top=False)[0] + RP.clamp_half(R_P, 6.0, ST_W, top=True)[0].translate((0, A.POD_Y, 0))
    s = s + box(-14, 14, A.POD_Y + R_P, -R_H + 2, 0, ST_W)
    return s - cyl(R_H, -1, ST_W + 1, 200) - cyl(R_P, -1, ST_W + 1, 200).translate((0, A.POD_Y, 0))
def st_bot():
    s = RP.clamp_half(R_P, 6.0, ST_W, top=False)[0].translate((0, A.POD_Y, 0))
    for sgn in (-1, 1): s = s + arm(sgn, -150, -134, 30, ARM_Y[1])
    s = s - cyl(R_P, -1, ST_W + 1, 200).translate((0, A.POD_Y, 0))
    for sgn in (-1, 1):                                                       # belly pan hanger screws: M4 inserts under the arm
        s = s - RP.ycyl(2.8, -151, -141, sgn*58, ST_W/2)
    return s
_top, _bot = st_top(), st_bot()
STATION = {"st_top_port": _top ^ box(0.3, 400, -400, 400, -400, 400), "st_top_stbd": _top ^ box(-400, -0.3, -400, 400, -400, 400),
           "st_mid": st_mid(),
           "st_bot_port": _bot ^ box(0.3, 400, -400, 400, -400, 400), "st_bot_stbd": _bot ^ box(-400, -0.3, -400, 400, -400, 400)}
ST_Z = (-60.0, 60.0)

# ---------------- top cowl: open-bottomed printed hood (3 mm shell), foam blocks inside, 6 pieces
CW = XP - 0.5
CZ0, CZ1 = -212.0, 236.0
CSPLIT = (-62.0, 87.0)
LIGHT_TILT = 15.0                                                        # light sleeves aimed this many degrees nose-down
LIGHT_PIV = (92.0, 22.0)                                                 # pivot: sleeve centre height y, distance behind the nose
def light_aim(m, sx):
    """sleeve / bore built along +z on the z axis: move it to (sx*100, 92) and pitch it LIGHT_TILT deg nose-down about its mid-length"""
    y0, d = LIGHT_PIV; pz = CZ1 - d
    return m.translate((0, 0, -pz)).rotate((LIGHT_TILT, 0, 0)).translate((sx*100, y0, pz))

SEAM_HOLES = ((-110, 120), (-60, 120), (60, 120), (110, 120), (-CW + 6.0, 70), (CW - 6.0, 70))
def roof_y(z):
    """outer roof height on the centreline at z (the side profile in cowl())"""
    if z < CZ0 + 36: return 80 + 46 * (z - CZ0) / 36
    if z > CZ1 - 40: return 126 - 16 * (z - (CZ1 - 40)) / 40
    return 126.0
def centre_bolt_y(z):
    """middle of the 9 mm flange under the roof (3 mm shell + 3 mm head room above the bolt)"""
    if z < CZ0 + 36: c = np.cos(np.arctan(46 / 36))
    elif z > CZ1 - 40: c = np.cos(np.arctan(16 / 40))
    else: c = 1.0
    return roof_y(z) - 6.0 / c

def cowl():
    prof = poly_zy([(CZ0, 30), (CZ1, 30), (CZ1, 110), (CZ1 - 40, 126), (CZ0 + 36, 126), (CZ0, 80)])
    # (2026-10-20) only the TOP corners are rounded. With all four rounded (r 34), the side walls stopped at y ~50 and the
    # 9 mm side feet (y 30-46) were a separate sliver, joined to the wall only through the seam flange at one end: printed
    # standing up it was a free 150 mm tall strip with a 4 mm slot beside it, and the prints failed. Walls now run straight down to y 30.
    outer = front_extrude((rrect(-CW, CW, 30, 126, 34.0) + CrossSection.square((2*CW, 34.0)).translate((-CW, 30.0)))
                          - CrossSection.circle(68.0, 128), CZ0, CZ1) ^ side_extrude(prof, -CW - 1, CW + 1)
    def inner(t):
        i = front_extrude(rrect(-CW + t, CW - t, -60, 126 - t, 34.0 - t), CZ0 + t, CZ1 - t) ^ side_extrude(prof.offset(-t, circular_segments=16), -CW, CW)
        return i + front_extrude(rrect(-CW + t, CW - t, -60, 60, 2.0), CZ0 + t, CZ1 - t)
    shell = outer - inner(3.0)
    thick = outer - inner(9.0)
    band = Manifold()                                                      # 9 mm flanges along every seam and the side feet
    for z in CSPLIT: band = band + box(-400, 400, -400, 400, z - 7, z + 7)
    band = band + box(-7, 7, -400, 400, -400, 400)
    band = band + box(-400, -CW + 9, 30, 46, -400, 400) + box(CW - 9, 400, 30, 46, -400, 400)
    body = shell + (thick ^ band)
    # (2026-10-20) 45-degree ramp on the hidden side of every seam flange: the 9 mm flange used to step in 6 mm in a single
    # layer, an unsupported ledge round the whole section at the top of the rear and front prints. 0.5 mm steps over 6 mm.
    for z in CSPLIT:
        for k in range(1, 13):
            for s0 in (-1, 1):
                za, zb = sorted((z + s0*(7 + 0.5*(k - 1)), z + s0*(7 + 0.5*k)))
                body = body + ((outer - inner(9.0 - 0.5*k)) ^ box(-400, 400, -400, 400, za, zb))
    for kind, M2, side, face, corners in THR:
        if kind == "V":
            p = M2[:3, 3]
            body = body - cyl(47, 0, 200).rotate((-90, 0, 0)).translate((p[0], 40, A.MID_Z))
            body = body + ((cyl(50, 0, 200) - cyl(47, -1, 201)).rotate((-90, 0, 0)).translate((p[0], 40, A.MID_Z)) ^ outer.hull())
    for sx in (-1, 1):                                                     # light sleeves in the nose + M3 grub screw
        # (2026-10-21) sleeves aimed LIGHT_TILT deg nose-down about their mid-length, so the ~80 deg underwater beam
        # covers the camera's full tilt range (0 to -45 deg) instead of ending at its bottom edge
        sl = cyl(24.5, CZ1 - 44, CZ1 + 12) - cyl(21.5, CZ1 - 45, CZ1 + 13)
        body = body + (light_aim(sl, sx) ^ outer.hull()) - light_aim(cyl(21.5, CZ1 - 45, CZ1 + 20), sx)
        body = body - RP.ycyl(1.25, 92, 125, sx*100, CZ1 - 30)
    # (2026-10-15) no carry handle: the old hand opening + 6 x 12 mm bar in the middle sections were too weak to lift
    # the ROV (split on the centreline, ~45 MPa in PETG at 15 kg static). The roof is now a closed 3 mm shell.
    # A future lifting point should load the HDPE side plates, not the cowl.
    # seam bolts: M3 x 20 + nyloc through the two 7 mm flanges (2026-10-23 fixes, found by checks/fastener_check.py):
    # - the holes were 20 mm long but the 45-degree ramps (2026-10-20) carry the flanges out to +/-13 mm: a 1 mm skin
    #   closed every hole end. Holes now run through the ramps, with a 6.8 mm spot face on each side down to the 7 mm
    #   flange face, so the head and nut seat flat.
    # - the side pair (x = CW - 4.5) sat 2 mm from the side wall, too close for a head; now CW - 6.
    # - the outer roof pair (x 120, y 118) broke out of the bottom of the flange (y 117-123 there); now x 110, y 120.
    for z in CSPLIT:
        for x, y in SEAM_HOLES:
            body = body - Manifold.cylinder(32, 1.7, 1.7, 24).translate((x, y, z - 16))
            for s0 in (-1, 1):
                body = body - Manifold.cylinder(9.0, 3.4, 3.4, 32).translate((x, y, z + 7.0 if s0 > 0 else z - 16.0))
    # centre seam (x = 0): each hole in the middle of the 9 mm flange under the roof line (the nose and tail slope down:
    # at a fixed y 120 the front hole had 1.3 mm under the roof and the rear one ran out of the flange)
    for z in (-180.0, -120.0, -30.0, 30.0, 140.0, 200.0):
        body = body - RP.xcyl(1.7, -12, 12, centre_bolt_y(z), z)
    for z, y in COWL_SCREWS:                                               # side feet: M3 inserts for the screws through the plates
        for sx in (-1, 1): body = body - RP.xcyl(2.0, *sorted((sx*CW, sx*(CW - 8))), y, z)
    return body
_cowl = cowl()
COWL = {}
zs = [CZ0 - 1, CSPLIT[0], CSPLIT[1], CZ1 + 1]
for i, nm in enumerate(("rear", "mid", "front")):
    for sx, sn in ((1, "port"), (-1, "stbd")):
        x0, x1 = (0.3, 400) if sx > 0 else (-400, -0.3)
        COWL[f"cowl_{nm}_{sn}"] = _cowl ^ box(x0, x1, -400, 400, zs[i] + (0.3 if i else 0), zs[i + 1] - (0.3 if i < 2 else 0))

# ---------------- belly pan (open top, lead inside), hangs from the bottom station arms
def belly():
    top = A.POD_Y - 54.0
    b = front_extrude(rrect(-56, 56, PY0 + 6, top, 12.0), -112, 112)
    b = b - front_extrude(rrect(-53, 53, PY0 + 9, top + 5, 9.0), -109, 109)
    for zc in ST_Z:
        for sgn in (-1, 1):
            t = box(*sorted((sgn*50, sgn*66)), top - 22, -150, zc - 10, zc + 10)
            # (2026-10-23) M4 clearance straight through the post: the screw goes in from below, head under the post
            # (the pan's bottom corners are rounded r 12, so the head clears the wall). It used to stop 16 mm short of the
            # post bottom, so no screw could get in.
            b = b + t - RP.ycyl(2.25, top - 24, -149, sgn*58, zc)
    return b

# ---------------- status colours: yellow = new printed part, black = already printed (v4), grey = bought / cut
NEW, OLD, BUY = 0xf2c200, 0x232629, 0xd5d9dd
STATUS, parts = {}, {}
EXIST = {"fl_rear", "cap_rear", "fl_front", "dome_ring", "tray", "bh_rear", "bh_front", "cam_mount", "pod_fl", "pod_cap",
         "cell_plate", "housing", "tail", "hub", "nose", "pylon", "jbox6", "jbox2", "lt_rear", "lt_front", "lt_spacer"}
KEEP = EXIST | {"hull", "dome", "rod", "picam", "pod", "cap3", "cell"}
for k, (m, c, l) in A.parts.items():
    if k in KEEP:
        col = OLD if k in EXIST else (0xbfe0f5 if k == "dome" else 0x9aa3ab if k in ("cell", "rod", "picam") else BUY)
        parts[k] = (m, col, l); STATUS[k] = "existing" if k in EXIST else "bought"
for k in LT.POD_PARTS:
    parts[k] = (A.parts[k][0], OLD if k in EXIST else (A.parts[k][1] if k in ("lt_window", "lt_led") else 0x9aa3ab), A.parts[k][2])
    STATUS[k] = "existing" if k in EXIST else "bought"
PLATE = {}
for sgn, sn, pl in ((1, "port", plate_r), (-1, "stbd", plate_l)):
    for k, m in plate_pieces(pl, sgn).items(): PLATE[f"plate_{k}_{sn}"] = m
    for j, (kind, m) in enumerate(strips(sgn)): PLATE[f"splice_{kind}_{sn}_{j}"] = m
for k, m in PLATE.items():
    parts[k] = (m, NEW, ("Side plate " + k[6:].replace("_", " ") if k.startswith("plate") else "Splice strip " + k.split("_")[1]) + " (NEW)"); STATUS[k] = "new"
LBL = {"st_top_port": "Station frame, top, port half", "st_top_stbd": "Station frame, top, starboard half",
       "st_mid": "Station frame, middle", "st_bot_port": "Station frame, bottom, port half",
       "st_bot_stbd": "Station frame, bottom, starboard half", "belly": "Belly pan",
       "brk_corner_a": "Corner thruster bracket A", "brk_corner_b": "Corner thruster bracket B"}
for k, m in STATION.items(): parts[k] = (m, NEW, LBL[k] + " (NEW)"); STATUS[k] = "new"
parts["jdeck"] = (junction_deck(), NEW, "Junction deck (NEW)"); STATUS["jdeck"] = "new"
for k, m in COWL.items(): parts[k] = (m, NEW, "Top cowl " + k[5:].replace("_", " ") + " (NEW)"); STATUS[k] = "new"
parts["belly"] = (belly(), NEW, "Belly pan (NEW)"); STATUS["belly"] = "new"
for i, (key, b) in enumerate(BRK):
    parts[f"{key}_{i}"] = (b, NEW, LBL[key] + " (NEW)"); STATUS[f"{key}_{i}"] = "new"

inst = []
def add(k, M, g, ex=(0, 0, 0)): inst.append((k, M, g, ex))
thr_keys = ("housing", "tail", "hub", "nose", "pylon")
for k, M, g, ex in A.inst:
    if k in KEEP and k not in thr_keys and not k.startswith("jbox") and k not in LT.POD_PARTS: add(k, M, g, ex)
for kind, M2, side, face, corners in THR:
    for k in thr_keys: add(k, M2, "thrusters", (np.sign(face[0])*60, 0, 0))
for k in PLATE:
    sg = 1 if k.endswith("port") else -1
    e = (sg*110, 30 if "upper" in k else 0, -50 if "rear" in k else 50 if "front" in k else 0)
    add(k, np.eye(4), "frame", e if k.startswith("plate") else (sg*70, 0, 0))
for i, (key, b) in enumerate(BRK):
    bb = b.bounding_box(); add(f"{key}_{i}", np.eye(4), "frame", (np.sign(bb[0] + bb[3])*50, 0, 0))
for z in ST_Z:
    for k in STATION: add(k, Tm(0, 0, z - ST_W/2), "frame", (0, 40, 0) if "top" in k else (0, -60, 0) if "bot" in k else (0, 0, 0))
for k in COWL: add(k, np.eye(4), "cowl", (60 if "port" in k else -60, 140, {"rear": -60, "mid": 0, "front": 60}[k.split("_")[1]]))
add("belly", np.eye(4), "frame", (0, -80, 0))
add("jdeck", Tm(0, 0, ST_Z[0] - ST_W/2), "frame", (0, 70, 0))
for sx in (-1, 1):
    _y0, _d = LIGHT_PIV; _P = Tm(0, _y0, CZ1 - _d); _c, _s = np.cos(np.radians(LIGHT_TILT)), np.sin(np.radians(LIGHT_TILT))
    _Rx = np.array([[1, 0, 0, 0], [0, _c, -_s, 0], [0, _s, _c, 0], [0, 0, 0, 1]])
    H = Tm(sx*100, 0, 0) @ _P @ _Rx @ np.linalg.inv(_P) @ Tm(0, 92, CZ1 - LT.Z_FRONT + 2) @ Rz(sx*40)
    for k in LT.POD_PARTS: add(k, H, "lights", (0, 60, 40))
# junction box 501 + lid 503 on the rear station deck (jbox.py): thruster sockets on its port / starboard faces,
# light sockets on the front, 12-core + 4-core out the back. Mated SP13 plugs drawn as bought parts.
import jbox as JB
JB_M = np.eye(4); JB_M[:3, 0], JB_M[:3, 1], JB_M[:3, 2] = (-1, 0, 0), (0, 0, 1), (0, 1, 0)
JB_M[:3, 3] = (0, DECK_Y + DECK_T, JB_ZC)
parts["jbox"] = (JB.junction_box(), NEW, "501 Junction box, SP13 sockets (NEW)"); STATUS["jbox"] = "new"
parts["jlid"] = (JB.junction_lid().translate((0, 0, JB.H)), NEW, "503 Junction box lid (NEW)"); STATUS["jlid"] = "new"
parts["sp13_plugs"] = (JB.plugs(), 0x1c1d20, "SP13 IP68 plugs, mated (bought)"); STATUS["sp13_plugs"] = "bought"
add("jbox", JB_M, "frame", (0, 90, 0)); add("jlid", JB_M, "frame", (0, 150, 0)); add("sp13_plugs", JB_M, "frame", (0, 90, 0))
JBOX5 = {"MOTORS": JB_M, "LIGHTS": JB_M}

def world(k, M): return parts[k][0].transform(M[:3, :])
def bed_size(m):
    e = np.array(m.bounding_box()); e = e[3:] - e[:3]
    best = min(((e[i], e[j], e[k]) for i, j, k in ((0, 1, 2), (0, 2, 1), (1, 2, 0))), key=lambda t: max(t[0], t[1]))
    return tuple(round(float(v)) for v in best)
if __name__ == "__main__":
    W = [(k, world(k, M)) for k, M, g, _ in inst]
    bad = []
    for (k1, m1), (k2, m2) in itertools.combinations(W, 2):
        b1, b2 = np.array(m1.bounding_box()), np.array(m2.bounding_box())
        if np.any(b1[3:] < b2[:3]) or np.any(b2[3:] < b1[:3]): continue
        v = (m1 ^ m2).volume()
        if v > 0.5: bad.append((k1, k2, round(v, 1)))
    print("interferences:", bad if bad else "none")
    allb = np.array([m.bounding_box() for _, m in W])
    print("envelope (x, y, z):", np.round(allb[:, 3:].max(0) - allb[:, :3].min(0), 0))
    rep = {}
    for k, (m, c, l) in parts.items():
        if STATUS.get(k) == "new":
            if m.is_empty(): print("EMPTY", k); continue
            rep[k] = {"size": bed_size(m), "vol_cm3": round(m.volume()/1000, 1), "parts": len(m.decompose())}
    json.dump(rep, open("rov_viewer/v5_new_parts.json", "w"), indent=1)
    for k, r in rep.items(): print(f"{k:24s} {r}")
    print("holes:", {t: sum(1 for h in HOLES if h[3] == t) for t in set(h[3] for h in HOLES)})
    meshes = {}
    for k, (m, col, label) in parts.items():
        g = m.to_mesh()
        meshes[k] = {"v": base64.b64encode(np.asarray(g.vert_properties[:, :3], np.float32).tobytes()).decode(),
                     "i": base64.b64encode(np.asarray(g.tri_verts, np.uint32).tobytes()).decode(), "color": col, "label": label}
    json.dump({"meshes": meshes, "instances": [{"k": k, "m": M.T.flatten().round(5).tolist(), "g": g, "ex": list(ex)} for k, M, g, ex in inst]},
              open("rov_viewer/assembly_v5.json", "w"))
    print("instances", len(inst))
