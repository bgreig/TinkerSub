"""
FRAME CLAMP: one 3-part clamp that replaces the float rings, skid brackets, thruster saddle and hull ring.

  top cap     hull top half + two slip bosses for the upper float rails
  body        hull bottom half + pod top half + waist block with a thruster pad each side (4x M3 inserts, 20 mm square,
              same pattern as the pylon clamp, so a thruster bolts on horizontal or vertical)
  bottom cap  pod bottom half + two legs to the skid bosses + two slip bosses for the middle float rails

The same three parts are used at all three stations. Every rail and skid is a straight 3/4" pipe that slides through
the bosses (no tees, no stubs), sealed with caps or light sockets at the ends.

Frame: x across, y up, z along the hull. Hull axis at (0, 0), pod axis at (0, POD_Y). Clamp occupies z 0..W.
Also here: the 5-hole rear end cap and the potted cable junction (fewer hull penetrations).
"""
import numpy as np
from manifold3d import Manifold
import rov_parts as RP
from rov_parts import cyl, box, xcyl, ycyl, clamp_half, HULL_OD, PIPE_34, thread_cutter

W = 34.0                                   # clamp width along the hull
R_IN = HULL_OD/2 + 0.25
POD_Y = RP.POD_Y                           # -122
PAD_FACE, PAD_Y = RP.SAD_PAD_FACE, RP.SAD_PAD_Y   # 68.15, -61: thruster pads at the waist, near the centre of gravity
UPPER = (75.0, 112.0)                      # upper float rails (x, y), mirrored
MIDDLE = (102.0, -148.0)                   # middle float rails
SKID = (85.0, -205.0)                      # skids
BOSS_R = PIPE_34/2 + 4.5
BORE_R = PIPE_34/2 + 0.25                  # slip fit on 3/4" Sch40
STRUT = 11.0                               # strut thickness across

def strut(p0, p1, w=STRUT):
    """flat bar from p0 to p1 (xy), full clamp width in z."""
    a = cyl(w/2, W, 0, 32).translate((p0[0], p0[1], 0)); b = cyl(w/2, W, 0, 32).translate((p1[0], p1[1], 0))
    return Manifold.batch_hull([a, b])

def boss(c):
    return cyl(BOSS_R, W, 0, 64).translate((c[0], c[1], 0))

def bore(c):
    return cyl(BORE_R, W + 2, -1, 64).translate((c[0], c[1], 0))

def polar(r, deg, cy=0.0):
    a = np.radians(deg); return (r*np.cos(a), cy + r*np.sin(a))

def top_cap():
    c = clamp_half(R_IN, 6.0, W, top=True)[0]
    for s in (-1, 1):
        u = (s*UPPER[0], UPPER[1])
        ang = np.degrees(np.arctan2(u[1], u[0]))
        c = c + boss(u) + strut(polar(R_IN + 3, ang), u) + strut(polar(R_IN + 3, ang + s*-22), u, 9.0)
    c = c - cyl(R_IN, W + 2, -1, 200)
    for s in (-1, 1): c = c - bore((s*UPPER[0], UPPER[1]))
    return c

def body():
    return RP.saddle_body()

def bottom_cap():
    c = clamp_half(R_IN, 6.0, W, top=False)[0].translate((0, POD_Y, 0))
    for s in (-1, 1):
        sk, md = (s*SKID[0], SKID[1]), (s*MIDDLE[0], MIDDLE[1])
        ear = (s*(R_IN + 6 + 7), POD_Y - 6)                       # outer end of the bottom ear
        a_sk = np.degrees(np.arctan2(sk[1] - POD_Y, sk[0]))
        c = c + boss(sk) + boss(md)
        c = c + strut(polar(R_IN + 3, a_sk, POD_Y), sk)           # leg: pod -> skid
        c = c + strut(polar(R_IN + 3, a_sk + s*38, POD_Y), sk, 9.0)   # second leg leaning in (triangulated)
        c = c + strut(ear, md, 10.0)                              # ear -> middle rail boss
        c = c + strut(md, sk, 9.0)                                # middle rail boss -> skid boss
    c = c - cyl(R_IN, W + 2, -1, 200).translate((0, POD_Y, 0))
    for s in (-1, 1):
        c = c - bore((s*SKID[0], SKID[1])) - bore((s*MIDDLE[0], MIDDLE[1]))
        # M3 grub screw into each skid boss only (the skids flood; the float rails are never drilled)
        c = c - ycyl(1.25, SKID[1] - BOSS_R - 1, SKID[1] - BORE_R + 0.5, s*SKID[0], W/2, 20)
    return c

# ---------------- v3: single hull (battery + electronics in one tube), no middle rails ----------------
PAD_Y1 = -35.0                             # thruster pads on the hull's lower flanks (pylon clears the clamp ears)
SKID1 = (85.0, -130.0)                     # skids
LOWL = (64.0, -98.0)                       # lower light stubs (front clamp only uses them; bosses on all, kit stays one part)
def hull_bottom():
    """Hull bottom half + thruster pad each side + braced skid legs + lower-light boss."""
    c = clamp_half(R_IN, 6.0, W, top=False)[0]
    for s in (-1, 1):
        pad = box(min(s*40, s*PAD_FACE), max(s*40, s*PAD_FACE), PAD_Y1 - 17, PAD_Y1 + 17, 0, W)
        sk, ll = (s*SKID1[0], SKID1[1]), (s*LOWL[0], LOWL[1])
        a_sk = np.degrees(np.arctan2(sk[1], sk[0]))
        c = c + pad + boss(sk) + boss(ll)
        c = c + strut(polar(R_IN + 3, a_sk), sk)                     # main leg
        c = c + strut(polar(R_IN + 3, a_sk + s*28), ll, 10.0)        # outer brace via the light boss
        c = c + strut(ll, sk, 9.0)
        c = c + strut((s*(PAD_FACE - 6), PAD_Y1 - 17), ll, 9.0)      # pad -> light boss
    c = c - cyl(R_IN, W + 2, -1, 200)
    for s in (-1, 1):
        c = c - bore((s*SKID1[0], SKID1[1])) - bore((s*LOWL[0], LOWL[1]))
        c = c - ycyl(1.25, SKID1[1] - BOSS_R - 1, SKID1[1] - BORE_R + 0.5, s*SKID1[0], W/2, 20)   # skid grub screw
        for dy in (-10, 10):                                         # 4x M3 heat-set inserts per pad, 20 mm square
            for dz in (-10, 10):
                x0, x1 = (PAD_FACE - 6, PAD_FACE + 1) if s > 0 else (-PAD_FACE - 1, -PAD_FACE + 6)
                c = c - xcyl(2.0, x0, x1, PAD_Y1 + dy, W/2 + dz, 24)
    return c

TRAY_L, TRAY_H = 100.0, 16.0
def lead_tray(skid=None):
    """Ballast tray between the skids, frame coordinates (skids at SKID1), z = 0..TRAY_L. Its ends hook over the skids
    from above (open underneath, so it drops on) and are zip-tied. Holds lead shot bags or bars, as low as possible."""
    xs, ys = skid or SKID1
    fy = ys - 8.0                                                 # floor bottom
    xi = xs - 14.0                                                # inner edge of the skid hooks
    t = box(-xi, xi, fy, fy + 3, 0, TRAY_L)
    t = t + (box(-xi, xi, fy, ys + 8, 0, TRAY_L) - box(-xi + 2.5, xi - 2.5, fy + 3, ys + 9, 2.5, TRAY_L - 2.5))
    for s in (-1, 1):
        lo, hi = (xs - 17, xs + 12) if s > 0 else (-xs - 12, -xs + 17)
        end = box(lo, hi, fy, ys + PIPE_34/2 + 4, 0, TRAY_L) - cyl(BORE_R, TRAY_L + 2, -1, 64).translate((s*xs, ys, 0))
        cut_lo, cut_hi = (xs - BORE_R, xs + 13) if s > 0 else (-xs - 13, -xs + BORE_R)
        end = end - box(cut_lo, cut_hi, fy - 1, ys, -1, TRAY_L + 1)          # open below the skid centre
        t = t + end
        for z in (20, TRAY_L - 20):
            t = t - box(min(s*xs - 3, s*xs + 3), max(s*xs - 3, s*xs + 3), ys + 9, ys + 20, z - 3, z + 3)   # zip-tie slot over the skid
    return t

# ---------------- fewer penetrations ----------------
CAP_T, CAP_PCD = 10.0, 108.0
GLANDS = {"MOTORS": (16, 45, 14.5), "LIGHTS": (12, 135, 10.5), "BATTERY": (16, 225, 14.5), "TETHER": (12, 315, 10.5)}   # BATTERY: power lead from the pod
# (2026-10-30) every gland hole and the vent are printed threads now (M16 x 1.5, M12 x 1.5, M10 x 1.0): no taps needed
GLAND_R = 26.0
def endcap_rear_5hole():
    """Hull rear cap, same bolt circle as your BR-style cap: 4 glands on r 26 + M10 x 1.0 vent in the centre."""
    c = cyl(HULL_OD/2, CAP_T, 0, 200)
    for k in range(6):
        x, y = polar(CAP_PCD/2, 30 + 60*k)
        c = c - cyl(1.7, CAP_T + 2, -1, 24).translate((x, y, 0))
    for name, (m, a, tap) in GLANDS.items():
        x, y = polar(GLAND_R, a)
        c = c - thread_cutter(m, 1.5, 0.0, CAP_T).translate((x, y, 0))
    return c - thread_cutter(10, 1.0, 0.0, CAP_T)                 # VENT: M10 x 1.0 (bolt + bonded washer)

JB_L, JB_W, JB_H = 56.0, 36.0, 26.0
JB_PITCH = 7.5
def junction_pot(n_in=4):
    JB_W = max(36.0, n_in*JB_PITCH + 9.0)
    """Potted cable junction that sits on top of the hull: n_in thin leads in one end, one multicore out the other.
    Fill with potting epoxy / urethane. Two zip-tie or hose-clamp slots through the curved base."""
    outer = box(-JB_L/2, JB_L/2, -JB_W/2, JB_W/2, 0, JB_H)
    saddle = cyl(HULL_OD/2 + 0.3, JB_L + 2, -1, 200).rotate((0, 90, 0)).translate((-JB_L/2 - 1, 0, -HULL_OD/2 + 6))
    p = outer - saddle
    p = p - (box(-JB_L/2 + 2.5, JB_L/2 - 2.5, -JB_W/2 + 2.5, JB_W/2 - 2.5, 8.5, JB_H + 1))     # potting well
    for i in range(n_in):                                                                  # lead entries, one end
        y = (i - (n_in - 1)/2) * 7.5
        p = p - xcyl(3.4, -JB_L/2 - 1, -JB_L/2 + 3, y, 16.5, 24)
    p = p - xcyl(5.2, JB_L/2 - 3, JB_L/2 + 1, 0, 16.5, 32)                                  # multicore out
    for x in (-JB_L/2 + 12, JB_L/2 - 12):                                                  # strap slots
        p = p - box(x - 3, x + 3, -JB_W/2 - 1, JB_W/2 + 1, 3.0, 6.0)
    return p

# ---------------- v4: electronics hull + 3" battery pod underneath, vectored thrusters ----------------
POD4_R = RP.BAT_OD/2 + 0.25                # 3" Sch40 pod
POD4_Y = -116.0                            # pod axis (its BR flange clears the hull by 2 mm)
PAD4_Y = -58.0                             # thruster pads at the waist between hull and pod
SKID4 = (85.0, -182.0)
CORNER_YAW = -45.0                         # right pad normal turned 45 deg toward +z; the rear clamp is the same part turned 180

CORNER_FACE, CORNER_Y = 60.0, PAD4_Y        # corner pad face centre (x, y): as far in as the pylon clears the clamp ring
VERT_FACE, VERT_Y = 55.0, -85.0              # mid pad face centre: verticals tucked down beside the pod
def _pad(yaw, face, py, depth=30.0):
    blk = box(-depth, 0, -17, 17, -17, 17)
    holes = Manifold()
    for dv in (-10, 10):
        for dw in (-10, 10):
            holes = holes + xcyl(2.0, -6.0, 1.0, dv, dw, 24)        # M3 heat-set, 20 mm square (pylon pattern)
    T = lambda m: m.rotate((0, yaw, 0)).translate((face, py, W/2))
    return T(blk), T(holes)

def body4(yaw=0.0):
    """Hull bottom half + pod top half + waist with a thruster pad each side.
    yaw = 0: mid clamp (pads square, verticals). yaw = CORNER_YAW: front/rear clamp (pads at 45 deg, vectored horizontals)."""
    b = clamp_half(R_IN, 6.0, W, top=False)[0] + clamp_half(POD4_R, 6.0, W, top=True)[0].translate((0, POD4_Y, 0))
    face, py = (VERT_FACE, VERT_Y) if yaw == 0 else (CORNER_FACE, CORNER_Y)
    b = b + box(-48, 48, PAD4_Y - 17, PAD4_Y + 17, 0, W)
    blk, holes = _pad(yaw, face, py)
    root = box(min(40, face - 30), min(50, face - 18), py - 17, py + 17, 0, W)
    arm = Manifold.batch_hull([blk, root]) ^ box(0, 200, -200, 200, 0, W)
    b = b + arm + arm.mirror((1, 0, 0))
    b = b - holes - holes.mirror((1, 0, 0))
    b = b - cyl(R_IN, W + 2, -1, 200) - cyl(POD4_R, W + 2, -1, 200).translate((0, POD4_Y, 0))
    return b

def pod_bottom4():
    """Pod bottom half + braced legs to the two skid bosses (skids slide through, M3 grub screw each)."""
    c = clamp_half(POD4_R, 6.0, W, top=False)[0].translate((0, POD4_Y, 0))
    ro = POD4_R + 6.0
    for s in (-1, 1):
        sk = (s*SKID4[0], SKID4[1])
        a_sk = np.degrees(np.arctan2(sk[1] - POD4_Y, sk[0]))
        ear = (s*(ro + 6), POD4_Y - 5)
        c = c + boss(sk) + strut(polar(ro - 3, a_sk, POD4_Y), sk) + strut(ear, sk, 9.0)
        c = c + strut(polar(ro - 3, -90 + s*25, POD4_Y), sk, 8.0)
    c = c - cyl(POD4_R, W + 2, -1, 200).translate((0, POD4_Y, 0))
    for s in (-1, 1):
        c = c - bore((s*SKID4[0], SKID4[1]))
        c = c - ycyl(1.25, SKID4[1] - BOSS_R - 1, SKID4[1] - BORE_R + 0.5, s*SKID4[0], W/2, 20)
    return c

if __name__ == "__main__":
    import trimesh, os
    os.makedirs("out", exist_ok=True)
    parts = {"frame_clamp_top_cap": top_cap(), "frame_clamp_bottom": hull_bottom(), "lead_tray": lead_tray(),
             "endcap_rear_5hole": endcap_rear_5hole(), "junction_pot_4in": junction_pot(4), "junction_pot_lights": junction_pot(4)}
    print("clamp overlap top/bottom (mm3):", round((parts["frame_clamp_top_cap"] ^ parts["frame_clamp_bottom"]).volume(), 1))
    for n, m in parts.items():
        if n == "junction_pot_lights": continue
        g = m.to_mesh(); t = trimesh.Trimesh(g.vert_properties[:, :3], g.tri_verts)
        t.apply_translation(-t.bounds[0] * np.array([0, 0, 1]))
        t.export(f"out/rov_{n}.stl")
        print(f"{n:24s} watertight={t.is_watertight} bodies={len(t.split(only_watertight=False))} size={np.round(t.extents,1)} vol={t.volume/1000:.1f}cm3")

# ---------------- v4: frame-mounted cable junctions ----------------
JX_L, JX_H, JX_FLOOR, JX_TAB = 56.0, 26.0, 4.0, 9.0
def jx_width(n_in): return max(36.0, n_in*JB_PITCH + 9.0)
JX_ENTRY_Z = (JX_FLOOR + JX_H) / 2 + 2.0
JX_SCREWS = (-16.0, 16.0)
def junction_box(n_in=6):
    """Potted cable junction, flat base. Local frame: x along the box (leads in at -x, multicore out at +x),
    z up from the base. Two M3 screws through the floor into the junction bridge; the potting covers their heads."""
    W = jx_width(n_in)
    p = box(-JX_L/2, JX_L/2, -W/2, W/2, 0, JX_H)
    p = p - box(-JX_L/2 + 2.5, JX_L/2 - 2.5, -W/2 + 2.5, W/2 - 2.5, JX_FLOOR, JX_H + 1)   # potting well
    for i in range(n_in):
        y = (i - (n_in - 1)/2) * JB_PITCH
        p = p - xcyl(3.4, -JX_L/2 - 1, -JX_L/2 + 3, y, JX_ENTRY_Z, 24)
    p = p - xcyl(5.2, JX_L/2 - 3, JX_L/2 + 1, 0, JX_ENTRY_Z, 32)
    for x in JX_SCREWS:                                                       # 2x M3 down through the floor into the bridge
        p = p - cyl(1.7, 6, -1, 24).translate((x, 0, 0)) - cyl(3.0, 4, 1.5, 24).translate((x, 0, 0))   # heads end up potted
    return p

BR_D, BR_Y, BR_T = 70.0, 95.0, 5.0             # junction bridge: depth along the rails, plate underside, plate thickness
BR_RING_L, BR_RING_R = 26.0, BORE_R + 5.0
JBOX_X = {"MOTORS": 22.0, "LIGHTS": -32.0}     # box centrelines across the bridge
JBOX_N = {"MOTORS": 6, "LIGHTS": 2}
def junction_bridge():
    """Plate across the two upper float rails behind the rear clamp, carrying both junction boxes.
    Clamps each rail with a split ring + M3 pinch screw (no hole in the sealed rail). Frame coords, z = 0..BR_D."""
    zc = BR_D / 2
    b = box(-UPPER[0] + 12, UPPER[0] - 12, BR_Y, BR_Y + BR_T, 0, BR_D)
    for s in (-1, 1):
        c = (s*UPPER[0], UPPER[1])
        ring = cyl(BR_RING_R, BR_RING_L, zc - BR_RING_L/2, 64).translate((c[0], c[1], 0))
        ears = box(c[0] - 7, c[0] + 7, c[1] + BORE_R - 1, c[1] + BORE_R + 10, zc - BR_RING_L/2, zc + BR_RING_L/2)
        web = box(min(s*(UPPER[0] - 14), s*(UPPER[0] - 4)), max(s*(UPPER[0] - 14), s*(UPPER[0] - 4)), BR_Y, c[1], 0, BR_D)
        b = b + ring + ears + (web - cyl(BR_RING_R - 0.01, BR_D + 2, -1, 64).translate((c[0], c[1], 0)))
        b = b - cyl(BORE_R, BR_D + 2, -1, 64).translate((c[0], c[1], 0))
        b = b - box(c[0] - 0.8, c[0] + 0.8, c[1], c[1] + BORE_R + 11, -1, BR_D + 1)          # split
        b = b - xcyl(1.7, c[0] - 8, c[0] + 8, c[1] + BORE_R + 5, zc, 24)                     # M3 pinch screw
        b = b - Manifold.cylinder(3.0, 6.4/np.sqrt(3), 6.4/np.sqrt(3), 6).rotate((0, 90, 0)).translate((c[0] + 4.01, c[1] + BORE_R + 5, zc))  # nut pocket
    for name, x in JBOX_X.items():                 # M3 heat-set inserts (5 deep) for each box's two tabs
        for dz in JX_SCREWS:
            b = b - ycyl(2.0, BR_Y + BR_T - 5.0, BR_Y + BR_T + 1, x, zc + dz, 24)
    for zz in (10, BR_D - 10):                     # zip-tie slots for the leads and multicores
        for x in (-55, 55):
            b = b - box(x - 2, x + 2, BR_Y - 1, BR_Y + BR_T + 1, zz - 4, zz + 4)
    return b
