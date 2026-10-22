"""
BlueROV2-style end hardware for a 4" Sch40 PVC hull (Brian's ROV) — PLA+ test parts.

Same architecture as the Blue Robotics 4" WTE:
  * an O-ring FLANGE that stays in the tube (2 radial O-rings into the pipe bore),
  * a removable END CAP / DOME that bolts to the flange face (face-seal O-ring),
  * BR numbers kept where they matter: Ø114.3 flange OD, 6 x M3 on a Ø108.0 circle
    (so a genuine BR 4" aluminium end cap would also bolt on), 10 mm end cap,
    4 x M3 inner sled mounting holes on Ø94.0 (BR flange "inner mounting hole circle").
  * Differences forced by PVC: piston sized to the Sch40 bore (BR's is Ø103.91 for its
    own machined tube), and 3 radial screws through the pipe wall replace BR's locking
    cord (PVC has no cord groove).

Parts
  br_flange_rear        flange, rear (sled mounts here)
  br_endcap_rear        10 mm end cap, 14 holes for cable glands + vent
  br_flange_front_dome  flange, front, wider ring to clamp an Amazon 100 mm CCTV dome
  dome_retaining_ring   clamps the dome flange onto its face O-ring

Frame: z=0 = outer face of the flange, +z into the hull.
"""
import math
import cadquery as cq

# ---- pipe / piston -------------------------------------------------------------------
PIPE_ID, PIPE_OD = 102.26, 114.30           # 4" Sch40 nominal
RAD_CLEAR  = 0.20
PISTON_D   = PIPE_ID - 2 * RAD_CLEAR
SKIRT_WALL = 8.0
INNER_D    = PISTON_D - 2 * SKIRT_WALL      # flange through-opening (~Ø85.9)

# radial O-rings: 2 x AS568-240 (94.84 mm ID x 3.53 CS)
OR_CS, SQUEEZE, GROOVE_W = 3.53, 0.20, 4.8
GROOVE_BOT = PIPE_ID - 2 * OR_CS * (1 - SQUEEZE)
GROOVE_D   = (PISTON_D - GROOVE_BOT) / 2

# ---- flange ring ------------------------------------------------------------------------
RING_T     = 10.0                           # outer ring (stops on the pipe end)
CAP_PCD    = 108.0                          # BR 4" end cap screw circle
CAP_SCREWS = 6
CAP_ANG0   = 30.0
TAP_D      = 2.5                            # M3 tap drill — tap or self-thread in PLA+
TAP_DEPTH  = 9.0
RETAIN_Z   = RING_T + 5.0                   # radial screw, 5 mm past the pipe end
M3_INS_D, M3_INS_H = 4.0, 7.0
G1 = RETAIN_Z + 6.0
G2 = G1 + GROOVE_W + GROOVE_D + 3.2
SKIRT_END  = G2 + GROOVE_W + GROOVE_D + 3.0 + M3_INS_H   # sled inserts clear the grooves

# face-seal O-ring under the end cap: AS568-239 (91.67 ID), groove ID = O-ring ID
FACE_OR_ID = 91.67
FACE_GW, FACE_GD = 3.8, 2.65

# sled mounting (BR inner mounting hole circle)
SLED_PCD   = 94.0
SLED_ANG   = (45, 135, 225, 315)            # confirm against your Printables sled

# ---- rear end cap ------------------------------------------------------------------------
CAP_T      = 10.0
CAP_HOLE   = 3.4                            # M3 clearance
# (name, thread, hole Ø, radius, angle) — tapped holes, gland screws straight in
M12, M16 = 10.5, 14.5                        # tap drills for M12x1.5 / M16x1.5
VENT     = 10.2                              # Blue Robotics vent plug (M10, nut inside)
REAR_HOLES = (
    [("LIGHT 1", "M12x1.5", M12, 15, 45), ("LIGHT 2", "M12x1.5", M12, 15, 135),
     ("BATTERY", "M16x1.5", M16, 15, 225), ("VENT", "M10 (BR vent)", VENT, 15, 315)]
    + [(n, "M12x1.5", M12, 36, 90 + 36 * k) for k, n in enumerate(
        ["TETHER", "MOTOR 1", "MOTOR 2", "SPARE 1", "SPARE 2",
         "SPARE 3", "SPARE 4", "SPARE 5", "MOTOR 3", "MOTOR 4"])]
)
BODY_D = {"M12x1.5": 17.0, "M16x1.5": 22.0, "M10 (BR vent)": 17.0}   # gland/nut envelope

# ---- front dome (UQISOVI 4" acrylic CCTV dome, Amazon B0DR2HP4YQ) -----------------------
DOME_OD, DOME_FL_D, DOME_FL_T = 99.8, 115.0, 2.0   # MEASURE the flange thickness
FRONT_RING_OD = 130.0
FRONT_PCD     = 122.0
DOME_OR_ID    = 101.19                      # AS568-242 face seal under the dome flange
RR_T          = 6.0
# -------------------------------------------------------------------------------------------


def cyl(r, z0, z1, x=0.0, y=0.0):
    return cq.Workplane("XY", origin=(0, 0, z0)).center(x, y).circle(r).extrude(z1 - z0)


def ring(ri, ro, z0, z1):
    return cyl(ro, z0, z1).cut(cyl(ri, z0 - 1, z1 + 1))


def polar(r, deg):
    a = math.radians(deg)
    return r * math.cos(a), r * math.sin(a)


def radial_hole(d, r_in, r_out, z, deg):
    return (cq.Workplane("YZ", origin=(r_in, 0, 0)).center(0, z).circle(d / 2)
            .extrude(r_out - r_in).rotate((0, 0, 0), (0, 0, 1), deg))


def groove_cutter(g):
    """radial groove; 45 deg flank on +z side = self-supporting when printed face-down"""
    rb, ro = GROOVE_BOT / 2, PISTON_D / 2 + 1
    d = ro - rb
    pts = [(rb, g), (rb, g + GROOVE_W), (ro, g + GROOVE_W + d), (ro, g)]
    return cq.Workplane("XZ").polyline(pts).close().revolve(360, (0, 0, 0), (0, 1, 0))


def flange(ring_od, pcd, face_or_id, sled=False):
    f = cyl(ring_od / 2, 0, RING_T).union(cyl(PISTON_D / 2, 0, SKIRT_END))
    f = f.cut(cyl(INNER_D / 2, -1, SKIRT_END + 1))
    for g in (G1, G2):
        f = f.cut(groove_cutter(g))
    f = f.cut(ring(face_or_id / 2, face_or_id / 2 + FACE_GW, -1, FACE_GD))   # face seal
    for k in range(CAP_SCREWS):                                              # M3 tapped
        x, y = polar(pcd / 2, CAP_ANG0 + 360 * k / CAP_SCREWS)
        f = f.cut(cyl(TAP_D / 2, -1, TAP_DEPTH, x, y))
    for a in (0, 120, 240):                                                  # retaining
        f = f.cut(radial_hole(M3_INS_D, PISTON_D / 2 - M3_INS_H, PISTON_D / 2 + 1, RETAIN_Z, a))
    if sled:
        for a in SLED_ANG:
            x, y = polar(SLED_PCD / 2, a)
            f = f.cut(cyl(M3_INS_D / 2, SKIRT_END - M3_INS_H, SKIRT_END + 1, x, y))
    return f


def br_flange_rear():
    return flange(PIPE_OD, CAP_PCD, FACE_OR_ID, sled=True)


def br_flange_front_dome():
    return flange(FRONT_RING_OD, FRONT_PCD, DOME_OR_ID, sled=True)   # tray can mount either end


def br_endcap_rear():
    c = cyl(PIPE_OD / 2, 0, CAP_T)
    for k in range(CAP_SCREWS):
        x, y = polar(CAP_PCD / 2, CAP_ANG0 + 360 * k / CAP_SCREWS)
        c = c.cut(cyl(CAP_HOLE / 2, -1, CAP_T + 1, x, y))
    for _, _, d, r, a in REAR_HOLES:
        x, y = polar(r, a)
        c = c.cut(cyl(d / 2, -1, CAP_T + 1, x, y))
    return c


def dome_retaining_ring():
    """z=0 = face that sits on the flange. Pocket holds the dome flange."""
    rr = ring((DOME_OD + 1.2) / 2, FRONT_RING_OD / 2, 0, RR_T)
    rr = rr.cut(cyl((DOME_FL_D + 0.6) / 2, -1, DOME_FL_T - 0.1))   # 0.1 mm clamp on acrylic
    for k in range(CAP_SCREWS):
        x, y = polar(FRONT_PCD / 2, CAP_ANG0 + 360 * k / CAP_SCREWS)
        rr = rr.cut(cyl(CAP_HOLE / 2, -1, RR_T + 1, x, y))
    return rr


def check_layout():
    msgs, pts = [], []
    for n, t, d, r, a in REAR_HOLES:
        x, y = polar(r, a)
        pts.append((n, t, d, x, y, r))
        if r + d / 2 > INNER_D / 2 - 0.5:
            msgs.append(f"!! {n}: thread reaches r={r + d/2:.1f}, flange opening r={INNER_D/2:.1f}")
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            a, b = pts[i], pts[j]
            dist = math.hypot(a[3] - b[3], a[4] - b[4])
            need = (BODY_D[a[1]] + BODY_D[b[1]]) / 2 + 1.0
            if dist < need:
                msgs.append(f"!! {a[0]} / {b[0]} bodies overlap ({dist:.1f} < {need:.1f})")
    for n, t, d, x, y, r in pts:
        if r + BODY_D[t] / 2 > CAP_PCD / 2 - 3.5:
            msgs.append(f"!! {n} gland body hits a cap screw head")
    return msgs or ["hole layout OK: threads clear the flange bore, gland bodies and screw heads clear"]


if __name__ == "__main__":
    parts = {"br_flange_rear": br_flange_rear(), "br_endcap_rear": br_endcap_rear(),
             "br_flange_front_dome": br_flange_front_dome(),
             "dome_retaining_ring": dome_retaining_ring()}
    for n, p in parts.items():
        cq.exporters.export(p, f"{n}.stl", tolerance=0.02, angularTolerance=0.1)
        cq.exporters.export(p, f"{n}.step")
        print("wrote", n)
    print(f"piston Ø{PISTON_D:.2f}, opening Ø{INNER_D:.2f}, flange length {SKIRT_END:.1f} mm "
          f"(inserts {SKIRT_END - RING_T:.1f} mm into the pipe)")
    print("\n".join(check_layout()))
