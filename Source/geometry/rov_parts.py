"""
ROV hull parts around a 4" Sch40 PVC hull (114.3 OD, 102.3 ID).
World frame: hull axis = Z (+Z = front/dome), up = +Y, hull centered on z = 0.

  hull_flange        glue onto each hull end; plug-in caps seal on 2 radial O-rings in its bore
  rear_endcap        bolts to the rear flange; 11 tapped M12x1.5 gland holes + sled mount
  front_dome_ring    bolts to the front flange; clamps an acrylic dome flange (verify dome size)
  dome_clamp_ring    outer clamp ring for the dome flange
  electronics_sled   tray + 2 cradle discs, hangs off the rear endcap
  battery_flange / battery_endcap   same idea for the 3" Sch40 battery tube (88.9 OD, 77.9 ID)
  battery_cell_plate holds 8 x 18650 per parallel group (3S8P = 6 plates)
  battery_hanger_top / _mid / _bot   clamp the battery tube under the hull
  skid_ring_top (2x 3/4" slip sockets for floats) / skid_ring_bot (legs to 3/4" PVC skids)
Run: python3 rov_parts.py
"""
import numpy as np, trimesh, os
from manifold3d import Manifold, CrossSection

SEG = 200
HULL_OD, HULL_ID, HULL_L = 114.3, 102.3, 450.0
BAT_OD, BAT_ID, BAT_L = 88.9, 77.9, 300.0
PIPE_34 = 26.67                          # 3/4" PVC OD
GAP = 1.0                                # clamp split gap

def cyl(r, h, z0=0.0, seg=SEG): return Manifold.cylinder(h, r, r, seg).translate((0, 0, z0))
def box(x0, x1, y0, y1, z0, z1): return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))
def ycyl(r, y0, y1, x, z, seg=40): return Manifold.cylinder(y1 - y0, r, r, seg).rotate((-90, 0, 0)).translate((x, y0, z))
def xcyl(r, x0, x1, y, z, seg=40): return Manifold.cylinder(x1 - x0, r, r, seg).rotate((0, 90, 0)).translate((x0, y, z))
def poly(pts, z0, z1):
    a = sum(x0*y1 - x1*y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    return Manifold.extrude(CrossSection([pts if a > 0 else pts[::-1]]), z1 - z0).translate((0, 0, z0))
def hexnut_pocket(af, h, x, y, z, axis="y"):
    rc = af/np.sqrt(3); m = Manifold.cylinder(h, rc, rc, 6)
    m = m.rotate((-90, 0, 0)) if axis == "y" else m.rotate((0, 90, 0))
    return m.translate((x, y, z))

# ---------------- flange + endcaps (shared by hull and battery tube) ----------------
def flange(od, idd, sock_d=30.0, seal_l=16.0, fl_od=None, fl_t=10.0, n_bolts=6, bolt_r=None):
    """z = 0 is the pipe end. Socket (glued) for z < 0, seal bore + bolt flange for z > 0."""
    ro = od/2 + 0.2 + 4.0
    fl_od = fl_od or od + 36; bolt_r = bolt_r or (od/2 + fl_od/2)/2 + 1
    f = cyl(ro, sock_d + seal_l, -sock_d) + cyl(fl_od/2, fl_t, seal_l - fl_t)
    f = f - cyl(od/2 + 0.2, sock_d + 0.01, -sock_d - 0.01)         # glue socket
    f = f - cyl(idd/2, seal_l + 2, -1)                              # seal bore = pipe ID
    f = f + (cyl(od/2 + 0.2, 1.5, -1.5) - cyl(idd/2, 3, -2))        # pipe stop ledge
    for k in range(n_bolts):
        a = 2*np.pi*(k + 0.5)/n_bolts
        x, y = bolt_r*np.cos(a), bolt_r*np.sin(a)
        f = f - cyl(3.2, 8.0, seal_l - 8.0 + 0.01, 32).translate((x, y, 0))   # M5 heat-set insert
    # 45 deg underside on the bolt flange so it prints socket-down without supports
    cham = Manifold.cylinder(fl_od/2 - ro, ro, fl_od/2, SEG).translate((0, 0, seal_l - fl_t - (fl_od/2 - ro)))
    f = f + (cham - cyl(od/2 + 0.2, 100, -60))
    return f, bolt_r, fl_od

def endcap(od, idd, seal_l=16.0, fl_od=None, plate_t=10.0, n_bolts=6, bolt_r=None, oring_cs=3.0):
    """plate sits on the flange face (z = seal_l); plug goes into the seal bore (toward -z)."""
    fl_od = fl_od or od + 36; bolt_r = bolt_r or (od/2 + fl_od/2)/2 + 1
    plug_r = idd/2 - 0.15
    c = cyl(fl_od/2, plate_t, seal_l) + cyl(plug_r, seal_l - 1.0, 1.0)
    for zg in (4.0, 10.0):                                             # 2 radial O-ring grooves
        c = c - (cyl(plug_r + 1, oring_cs*1.15, zg) - cyl(plug_r - oring_cs*0.78, oring_cs*1.15 + 2, zg - 1))
    for k in range(n_bolts):
        a = 2*np.pi*(k + 0.5)/n_bolts
        c = c - cyl(2.75, plate_t + 2, seal_l - 1, 32).translate((bolt_r*np.cos(a), bolt_r*np.sin(a), 0))
    return c

HF, HULL_BOLT_R, HULL_FL_OD = flange(HULL_OD, HULL_ID)
SEAL_L = 16.0

GLANDS = [("Motor 1", -33, 24), ("Motor 2", -11, 24), ("Motor 3", 11, 24), ("Motor 4", 33, 24),
          ("Light 1", -36, 2), ("Tether", -12, 2), ("Battery", 12, 2), ("Light 2", 36, 2),
          ("Vent valve", 0, 40), ("Spare", -24, -18), ("Spare", 24, -18)]

def rear_endcap():
    c = endcap(HULL_OD, HULL_ID)
    for name, x, y in GLANDS:
        r = 4.25 if name == "Vent valve" else 5.25          # M10 vent (tap 8.5) / M12x1.5 gland (tap 10.5)
        c = c - cyl(r, 40, -5, 48).translate((x, y, 0))
    # electronics sled mount: 2x M3 heat-set inserts on the plug face, low down
    for x in (-20, 20):
        c = c - cyl(2.0, 7, 0.99, 24).translate((x, -38, 0))
    return c

DOME_FLANGE_OD, DOME_FLANGE_T, DOME_R, DOME_AP = 130.0, 6.0, 50.0, 96.0   # VERIFY against your dome
def front_dome_ring():
    c = endcap(HULL_OD, HULL_ID)
    c = c - cyl(DOME_AP/2, 60, -5)                                   # viewing aperture
    c = c - (cyl(DOME_AP/2 + 6.5, 1.6, SEAL_L + 10 - 1.6) - cyl(DOME_AP/2 + 3.5, 3, SEAL_L + 10 - 2.5))  # face O-ring groove
    for k in range(6):                                               # clamp-ring screws, M4 inserts
        a = 2*np.pi*k/6; r = (DOME_AP/2 + DOME_FLANGE_OD/2)/2 + 2
        c = c - cyl(2.8, 8, SEAL_L + 10 - 8 + 0.01, 24).translate((r*np.cos(a), r*np.sin(a), 0))
    return c

def dome_clamp_ring():
    t = 5.0
    r = cyl(HULL_FL_OD/2 - 6, t, 0) - cyl(DOME_R + 1.0, t + 2, -1) - cyl(DOME_FLANGE_OD/2 + 0.4, DOME_FLANGE_T - 1.0, -0.01)
    for k in range(6):
        a = 2*np.pi*k/6; rr = (DOME_AP/2 + DOME_FLANGE_OD/2)/2 + 2
        r = r - cyl(2.25, t + 2, -1, 24).translate((rr*np.cos(a), rr*np.sin(a), 0))
    return r

# ---------------- electronics sled ----------------
SLED_L, SLED_W, SLED_Y = 250.0, 84.0, -24.0
def electronics_sled():
    """local frame: z = 0 at the rear endcap plug face, sled runs toward +z"""
    t = 3.0
    tray = box(-SLED_W/2, SLED_W/2, SLED_Y - t, SLED_Y, 0, SLED_L)
    rails = box(-SLED_W/2, -SLED_W/2 + 3, SLED_Y, SLED_Y + 8, 0, SLED_L) + box(SLED_W/2 - 3, SLED_W/2, SLED_Y, SLED_Y + 8, 0, SLED_L)
    s = tray + rails
    # mounting grid: M2.5 holes every 10 mm (Pi Zero, Pico, drivers, buck on standoffs)
    for x in np.arange(-35, 36, 10):
        for z in np.arange(15, SLED_L - 10, 10):
            s = s - ycyl(1.3, SLED_Y - t - 1, SLED_Y + 1, x, z, 16)
    # cradle discs that ride the hull ID (open at the top for wiring)
    for z0 in (60.0, SLED_L - 8.0):
        d = cyl(HULL_ID/2 - 0.8, 6, z0) - cyl(HULL_ID/2 - 7, 8, z0 - 1)
        d = d ^ box(-60, 60, -60, SLED_Y + 6, z0 - 1, z0 + 7)
        d = d + box(-SLED_W/2, SLED_W/2, -HULL_ID/2 + 4, SLED_Y, z0, z0 + 6)
        s = s + (d - cyl(0.01, 1, 0))
        s = s - box(-25, 25, -HULL_ID/2 + 8, SLED_Y - t - 2, z0 - 1, z0 + 7)   # wiring cut-out
    # endcap bracket: plate up against the plug face with 2x M3 holes
    s = s + box(-26, 26, -42, SLED_Y, 0, 4) + box(-26, 26, SLED_Y - t - 1, SLED_Y, 0, 14)
    for x in (-20, 20):
        s = s - Manifold.cylinder(6, 1.7, 1.7, 24).translate((x, -38, -1))
    return s ^ cyl(HULL_ID/2 - 0.6, SLED_L + 2, -1)          # stays inside the hull bore

# ---------------- battery tube, sled ----------------
BF, BAT_BOLT_R, BAT_FL_OD = flange(BAT_OD, BAT_ID, sock_d=25.0, seal_l=14.0, fl_od=BAT_OD + 24, n_bolts=6)
def battery_flange(): return BF
def battery_endcap():
    c = endcap(BAT_OD, BAT_ID, seal_l=14.0, fl_od=BAT_OD + 24, plate_t=8.0, oring_cs=2.5)
    c = c - cyl(7.25, 40, -5, 48).translate((0, 12, 0))          # M16 gland: battery leads (14 AWG)
    c = c - cyl(4.5, 40, -5, 48).translate((0, -14, 0))          # VENT: M10 x 1.0 tap drill (barb / bolt + bonded washer)
    return c

CELL_D, CELL_L = 18.4, 65.0
RING_R = (CELL_D + 0.6)/(2*np.sin(np.pi/7))
CELL_POS = [(0.0, 0.0)] + [(RING_R*np.cos(2*np.pi*k/7 + np.pi/2), RING_R*np.sin(2*np.pi*k/7 + np.pi/2)) for k in range(7)]
ROD_POS = [((RING_R + 0.0)*0.55*np.cos(2*np.pi*k/3 + np.pi/7 + np.pi/2), (RING_R)*0.55*np.sin(2*np.pi*k/3 + np.pi/7 + np.pi/2)) for k in range(3)]
def battery_cell_plate():
    """one end of a parallel group: 8 x 18650 pockets, 14 mm windows for nickel strip, 3x M4 rods"""
    t = 7.0
    p = cyl(BAT_ID/2 - 0.6, t, 0)
    for x, y in CELL_POS:
        p = p - cyl((CELL_D + 0.5)/2, t - 1.5 + 0.01, 1.5, 48).translate((x, y, 0))
        p = p - cyl(7.0, 3, -1, 32).translate((x, y, 0))
    outer_ring_r = RING_R + CELL_D/2
    for k in range(3):                                   # rods between the outer cells, outside the ring
        a = 2*np.pi*k/3 + np.pi/7 + np.pi/2
        rr = outer_ring_r + 3.5
        p = p - cyl(2.2, t + 2, -1, 24).translate((rr*np.cos(a), rr*np.sin(a), 0))
    p = p - box(-4, 4, -BAT_ID/2, -BAT_ID/2 + 4, -1, t + 1)    # wire channel along the bottom
    # nickel-strip grooves in the outer face, through the 1.5 mm floor so the strip lies flat on the cell ends:
    # a ring of straight runs cell-to-cell round the 7 outer cells, plus one run from the centre cell through the
    # top cell to the plate edge (the series link / tab exit). Mirror-symmetric, so the exits of facing plates line up.
    W = STRIP_W
    def run(a, b): return Manifold.batch_hull([cyl(W/2, 1.5 + 1.01, -1, 24).translate((a[0], a[1], 0)),
                                               cyl(W/2, 1.5 + 1.01, -1, 24).translate((b[0], b[1], 0))])
    ring = CELL_POS[1:]
    for i in range(7): p = p - run(ring[i], ring[(i + 1) % 7])
    p = p - run((0.0, 0.0), (0.0, BAT_ID/2 + 2))
    return p
STRIP_W = 8.6            # groove width for 8 mm nickel strip

# ---------------- clamp rings (side ears, split at y = 0) ----------------
def clamp_half(r_in, t, width, top, ear=10.0, ear_t=8.0, nut=True):
    r_out = r_in + t
    ring = cyl(r_out, width, 0) - cyl(r_in, width + 2, -1)
    y0, y1 = (GAP/2, r_out + 1) if top else (-r_out - 1, -GAP/2)
    ring = ring ^ box(-r_out - 1, r_out + 1, y0, y1, -1, width + 1)
    ey0, ey1 = (GAP/2, GAP/2 + ear_t) if top else (-GAP/2 - ear_t, -GAP/2)
    for s in (-1, 1):
        e = box(min(s*(r_in + 2), s*(r_out + ear)), max(s*(r_in + 2), s*(r_out + ear)), ey0, ey1, 0, width)
        ring = ring + (e - cyl(r_in, width + 2, -1))
        bx = s*(r_out + ear/2)
        for dz in (width/2 - 8, width/2 + 8) if width >= 28 else (width/2,):
            ring = ring - ycyl(2.25, ey0 - 1, ey1 + 1, bx, dz)
            if nut and not top:
                ring = ring - hexnut_pocket(7.2, 3.5, bx, ey0 - 0.01, dz)
    return ring, r_out

HANG_W = 30.0
BAT_Y = -128.0                                   # battery tube axis: clears the thruster-ring bottom ears
def battery_hanger_top():
    return clamp_half(HULL_OD/2 + 0.25, 6.0, HANG_W, top=True)[0]
def battery_hanger_mid():
    """hull bottom half + web + battery top half, one part"""
    h, ro = clamp_half(HULL_OD/2 + 0.25, 6.0, HANG_W, top=False)
    b, rob = clamp_half(BAT_OD/2 + 0.25, 5.0, HANG_W, top=True)
    b = b.translate((0, BAT_Y, 0))
    web = poly([(-28, -HULL_OD/2 + 6), (28, -HULL_OD/2 + 6), (22, BAT_Y + BAT_OD/2 + 3), (-22, BAT_Y + BAT_OD/2 + 3)], 0, HANG_W)
    web = web - cyl(HULL_OD/2 + 0.25, HANG_W + 2, -1) - cyl(BAT_OD/2 + 0.25, HANG_W + 2, -1).translate((0, BAT_Y, 0))
    return h + b + web
def battery_hanger_bot():
    return clamp_half(BAT_OD/2 + 0.25, 5.0, HANG_W, top=False)[0].translate((0, BAT_Y, 0))

SKID_W = 30.0
SKID_X, SKID_Y = 80.0, -140.0
FLOAT_X, FLOAT_Y = 42.0, 76.0
SOCK_R = PIPE_34/2 + 0.25
def socket_ring(x, y, w):
    return cyl(SOCK_R + 4.5, w, 0, 64).translate((x, y, 0)) - cyl(SOCK_R, w + 2, -1, 64).translate((x, y, 0))
def skid_ring_top():
    """hull top half + two 3/4" PVC slip sockets for float pipes"""
    h, ro = clamp_half(HULL_OD/2 + 0.25, 6.0, SKID_W, top=True)
    for s in (-1, 1):
        x, y = s*FLOAT_X, FLOAT_Y
        post = poly([(x - 8, 40), (x + 8, 40), (x + 8, y), (x - 8, y)], 0, SKID_W) - cyl(SOCK_R, SKID_W + 2, -1, 64).translate((x, y, 0))
        h = h + (post - cyl(HULL_OD/2 + 0.25, SKID_W + 2, -1)) + socket_ring(x, y, SKID_W)
        h = h - xcyl(2.0, x - 30, x + 30, y, SKID_W/2)              # M4 pin through socket + pipe
    return h
def skid_ring_bot():
    """hull bottom half + two legs to 3/4" PVC skid sockets, clear of the battery tube"""
    h, ro = clamp_half(HULL_OD/2 + 0.25, 6.0, SKID_W, top=False)
    for s in (-1, 1):
        x0, y0 = s*44.0, -40.0
        x1, y1 = s*SKID_X, SKID_Y
        n = np.array([y1 - y0, -(x1 - x0)]); n = n/np.linalg.norm(n)*5.0
        leg = poly([(x0 + n[0], y0 + n[1]), (x1 + n[0], y1 + n[1]), (x1 - n[0], y1 - n[1]), (x0 - n[0], y0 - n[1])], 0, SKID_W)
        leg = leg - cyl(SOCK_R, SKID_W + 2, -1, 64).translate((x1, y1, 0)) - cyl(HULL_OD/2 + 0.25, SKID_W + 2, -1)
        h = h + leg + socket_ring(x1, y1, SKID_W)
        h = h - xcyl(2.0, x1 - 30, x1 + 30, y1, SKID_W/2)     # M4 pin through the skid pipe
    return h

# ---------------- sled mounts for the BR-style flanges (ROV Project caps) ----------------
FL_SLED_PCD, FL_SLED_ANG = 94.0, (45, 135, 225, 315)
PIPE_ID_SCH40 = 102.26
MOUNT_OD, MOUNT_ID, MOUNT_T = 99.0, 70.0, 6.0
def _mount_ring():
    m = cyl(MOUNT_OD/2, MOUNT_T, 0) - cyl(MOUNT_ID/2, MOUNT_T + 2, -1)
    for a in FL_SLED_ANG:                       # M3 to the flange inserts, heads on the sled side
        x, y = FL_SLED_PCD/2*np.cos(np.radians(a)), FL_SLED_PCD/2*np.sin(np.radians(a))
        m = m - cyl(1.7, MOUNT_T + 2, -1, 24).translate((x, y, 0)) - cyl(3.0, 3.01, MOUNT_T - 3, 24).translate((x, y, 0))
    return m
SLED_RODS = [(0, 39, 90), (0, 39, -90), (0, 45, 0), (0, 45, 180)]
def battery_sled_mount():
    """pod rear flange -> battery sled: the sled's 4 tie rods end in nuts pocketed on the flange side"""
    m = _mount_ring() + (cyl(MOUNT_OD/2, MOUNT_T, 0) - cyl(MOUNT_ID/2 - 0.01, MOUNT_T + 2, -1))
    for _, r, a in SLED_RODS:
        x, y = r*np.cos(np.radians(a)), r*np.sin(np.radians(a))
        m = m - cyl(2.3, MOUNT_T + 2, -1, 24).translate((x, y, 0))
        m = m - Manifold.cylinder(3.5, 7.2/np.sqrt(3), 7.2/np.sqrt(3), 6).translate((x, y, -0.01))
    for a in FL_SLED_ANG:
        x, y = FL_SLED_PCD/2*np.cos(np.radians(a)), FL_SLED_PCD/2*np.sin(np.radians(a))
        m = m - cyl(1.7, MOUNT_T + 2, -1, 24).translate((x, y, 0)) - cyl(3.0, 3.01, MOUNT_T - 3, 24).translate((x, y, 0))
    return m
def pod_endcap_2hole():
    """Battery pod rear cap: same 10 mm BR-style cap as the hull (6x M3 on 108), but only two holes:
    M16x1.5 battery power gland and the M10 BR vent, both on r 15."""
    c = cyl(114.3/2, 10.0, 0, 128)
    for k in range(6):
        a = np.radians(30 + 60*k)
        c = c - cyl(1.7, 12, -1, 24).translate((54*np.cos(a), 54*np.sin(a), 0))
    c = c - cyl(14.5/2, 12, -1, 48).translate((-15, 0, 0))   # M16x1.5 tap drill
    c = c - cyl(10.2/2, 12, -1, 48).translate((15, 0, 0))    # BR vent
    return c
TRAY_TAB_W, TRAY_T = 80.0, 5.0
# ---------------- electronics sled bulkheads (front + rear) ----------------
BH_R, BH_T = 50.4, 5.0                  # fits the 4" Sch40 bore (r 51.13) with 0.7 mm clearance
BH_ROD_R, BH_ROD_ANG = 47.0, (45, 135, 225, 315)   # same circle as the flange sled inserts, so the rods line up
TRAY_GAP = 6.12                         # disc face to tray prong tip (discs 234 apart, tray 221.76 long)
PRONG_W, PRONG_L, PRONG_X = 25.0, 5.0, 27.5        # ETRAY4 end prongs: 2 per end, 25 wide, 5 long, centres +-27.5
def sled_bulkhead(front=True):
    """z = 0 outer face, +z toward the tray. Boss on the inner face takes the tray's two end prongs;
    the tray shoulder sits on the boss top, and the 4 rods clamp the stack together."""
    d = cyl(BH_R, BH_T, 0, 160)
    boss_h = TRAY_GAP + PRONG_L
    d = d + box(-44, 44, -6.5, 6.5, BH_T - 0.01, BH_T + boss_h - BH_T)          # boss top at TRAY_GAP + PRONG_L
    for sx in (-1, 1):                                                          # prong pockets (0.3 mm clearance)
        d = d - box(sx*PRONG_X - PRONG_W/2 - 0.3, sx*PRONG_X + PRONG_W/2 + 0.3, -TRAY_T/2 - 0.25, TRAY_T/2 + 0.25,
                    TRAY_GAP - 0.2, boss_h + 1)
    for a in BH_ROD_ANG:                                                        # rod holes
        x, y = BH_ROD_R*np.cos(np.radians(a)), BH_ROD_R*np.sin(np.radians(a))
        d = d - cyl(1.7, BH_T + 2, -1, 24).translate((x, y, 0))
    d = d - box(-8.5, 8.5, -1.2, 1.2, -1, boss_h + 1)                            # camera ribbon slot through the centre
    for sy in (-1, 1):                                                          # wiring windows above and below the tray
        win = (box(-22, 22, 20, 38, -1, BH_T + 1) + cyl(9, BH_T + 2, -1, 48).translate((-22, 29, 0))
               + cyl(9, BH_T + 2, -1, 48).translate((22, 29, 0)))
        d = d - (win if sy > 0 else win.mirror((0, 1, 0)))
    if front:                                                                   # camera stalk: 4x M3 on a 26 mm square
        for x in (-13, 13):
            for y in (-13, 13):
                d = d - cyl(1.7, BH_T + 2, -1, 24).translate((x, y, 0))
    return d

CAM_STALK = 51.7                        # set by the assembly so the lens lands at the dome centre
def camera_mount(stalk=None):
    """Pi Camera Module 3 stalk that bolts to the tray's front bulkhead disc (4x M3 on a 26 mm square).
    z = 0 on the disc face, +z points at the dome. Square tube carries the ribbon."""
    L = CAM_STALK if stalk is None else stalk
    base = box(-18, 18, -18, 18, 0, 3) - box(-8, 8, -1, 1, -1, 4)
    for x in (-13, 13):
        for y in (-13, 13): base = base - cyl(1.7, 5, -1, 24).translate((x, y, 0))
    tube = box(-11, 11, -11, 11, 0, L) - box(-9, 9, -9, 9, -1, L + 1)
    camp = box(-15, 15, -15, 15, L, L + 2) - box(-8, 8, -1, 1, L - 1, L + 3)   # ribbon slot
    for x in (-10.5, 10.5):                                             # Pi Cam 3 holes 21 x 12.5
        for y in (-6.25, 6.25):
            camp = camp - cyl(1.1, 4, L - 1, 24).translate((x, y + 2.0, 0))
    return base + tube + camp
def picam3():
    """Pi Camera Module 3 placeholder (purchased): 25 x 24 board, lens block. z=0 on the mount plate."""
    b = box(-12.5, 12.5, -10, 14, 0, 1.0)
    return b + box(-4.25, 4.25, -2.25, 6.25, 1, 6) + cyl(3.5, 5.5, 6, 48).translate((0, 2.0, 0))
def tray_mount():
    """rear flange -> ETRAY4 tray: a bridge bar with a slot for the tray's end tab, 2x M3 clamp screws"""
    m = _mount_ring()
    bar = box(-MOUNT_ID/2 - 1, MOUNT_ID/2 + 1, -8, 8, 0, 12)
    bar = bar ^ cyl(MOUNT_OD/2, 13, -1)
    m = m + bar
    m = m - box(-TRAY_TAB_W/2 - 0.3, TRAY_TAB_W/2 + 0.3, -TRAY_T/2 - 0.2, TRAY_T/2 + 0.2, 6.0, 13)      # tab slot
    for x in (-25, 25):
        m = m - ycyl(1.25, 0, 9, x, 9.0, 24)                                                       # M3 clamp (self-tap)
    return m

# ---------------- thruster saddle: hull + battery pod, pads at the waist ----------------
POD_Y = -122.0                          # pod axis below hull axis (from the ROV Project skid bracket)
SAD_W, SAD_PAD_FACE, SAD_PAD_Y = 34.0, 68.15, POD_Y/2
def saddle_hull_cap():
    return clamp_half(HULL_OD/2 + 0.25, 6.0, SAD_W, top=True)[0]
def saddle_body():
    h = clamp_half(HULL_OD/2 + 0.25, 6.0, SAD_W, top=False)[0]
    p = clamp_half(HULL_OD/2 + 0.25, 6.0, SAD_W, top=True)[0].translate((0, POD_Y, 0))
    waist = box(-SAD_PAD_FACE, SAD_PAD_FACE, SAD_PAD_Y - 17, SAD_PAD_Y + 17, 0, SAD_W)
    waist = waist - cyl(HULL_OD/2 + 0.25, SAD_W + 2, -1) - cyl(HULL_OD/2 + 0.25, SAD_W + 2, -1).translate((0, POD_Y, 0))
    b = h + p + waist
    for sx in (-1, 1):                      # 4x M3 heat-set inserts per pad, 20 mm square (same as the hull ring)
        for dy in (-10, 10):
            for dz in (-10, 10):
                b = b - xcyl(2.0, SAD_PAD_FACE - 6 if sx > 0 else -SAD_PAD_FACE - 1, SAD_PAD_FACE + 1 if sx > 0 else -SAD_PAD_FACE + 6,
                             SAD_PAD_Y + dy, SAD_W/2 + dz, 24)
    return b
def saddle_pod_cap():
    return clamp_half(HULL_OD/2 + 0.25, 6.0, SAD_W, top=False)[0].translate((0, POD_Y, 0))

LOW_RAIL_R, LOW_RAIL_ANG = 170.0, 56.0   # lower float rail, on the float ring's lower coupler line
def skid_body_rail(path="rov_project/skid_bracket_body_x2.stl"):
    """Your skid bracket body + a 3/4" slip boss on each leg so the lower float rails pass through it.
    No cross pin: the rails are sealed floats, and the tees at the float rings already hold them."""
    import trimesh as _tm; from manifold3d import Mesh
    t = _tm.load(path)
    b = Manifold(Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
    for sx in (-1, 1):
        a = np.radians(LOW_RAIL_ANG)               # same 0.4 mm offset as the float-ring coupler bore
        x = sx*LOW_RAIL_R*np.cos(a) - sx*0.4*np.sin(a); y = -LOW_RAIL_R*np.sin(a) - 0.4*np.cos(a)
        b = b + cyl(PIPE_34/2 + 4.5, 24, 0, 64).translate((x, y, 0))
        b = b - cyl(SOCK_R, 26, -1, 64).translate((x, y, 0))
    return b

def export(m, name, flip_x=0, flip_y=0):
    if flip_x: m = m.rotate((flip_x, 0, 0))
    if flip_y: m = m.rotate((0, flip_y, 0))
    g = m.to_mesh(); tm = trimesh.Trimesh(g.vert_properties[:, :3], g.tri_verts)
    tm.apply_translation(-tm.bounds[0] * np.array([0, 0, 1]))
    tm.export(f"out/rov_{name}.stl")
    print(f"{name:22s} watertight={tm.is_watertight} bodies={len(tm.split(only_watertight=False))} size={np.round(tm.extents,1)}")
    return tm

PARTS = {
    "battery_sled_mount": (battery_sled_mount, 0, 0),
    "tray_mount":         (tray_mount, 0, 0),
    "saddle_hull_cap":    (saddle_hull_cap, 0, 0),
    "saddle_body":        (saddle_body, 0, 0),
    "saddle_pod_cap":     (saddle_pod_cap, 0, 0),
    "pod_endcap_2hole":   (pod_endcap_2hole, 0, 0),
    "camera_mount":       (camera_mount, 0, 0),
    "sled_bulkhead_front": (lambda: sled_bulkhead(True), 0, 0),
    "sled_bulkhead_rear":  (lambda: sled_bulkhead(False), 0, 0),
    "skid_bracket_body_rail": (skid_body_rail, 0, 0),
}

if __name__ == "__main__":
    os.makedirs("out", exist_ok=True)
    for name, (fn, fx, fy) in PARTS.items():
        export(fn(), name, fx, fy)
