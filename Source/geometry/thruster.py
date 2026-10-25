"""
Pod-in-duct bilge-motor thruster (oil-filled).
Parts: housing (pod + duct + stators + mount foot, one print), tail_cone, prop (spinner).
Edit the MOTOR block to your calipers, then:  python3 thruster.py
All dimensions mm. Housing frame: z=0 at rear flange face, +z toward prop.
"""
import numpy as np, os, trimesh
from manifold3d import Manifold, CrossSection, Mesh

# ---------------- MOTOR (measure these!) ----------------
MOTOR_D    = 35.7    # can diameter (measured)
MOTOR_L    = 57.3    # can + white end bell (measured)
NOSE_D     = 15.0    # black O-ring OD at nose (measured)
NOSE_BORE_ADJ = 0.5  # widen nose bore by this much (diameter); 0 = original 14.7 mm bore
NOSE_L     = 4.5     # nose length past can face (estimate)
SHAFT_D    = 3.17    # shaft diameter
SHAFT_OUT  = 22.8    # 80.1 overall - 57.3 body (measured)

# ---------------- POD ----------------
FIT, WALL         = 0.4, 3.5
FRONT_T           = 11.0   # solid front (nose pocket + seal pocket)
REAR_SPACE        = 7.0    # wiring room behind end bell (spigot adds 8 more)
SPIGOT_H          = 8.0    # tail-cone spigot depth into bore (carries the O-ring)
THREAD_L, THREAD_P, THREAD_D, THREAD_CLR = 10.0, 2.5, 1.0, 0.3   # 45-deg flank thread
CAP_WALL          = 2.5
ORING_CS, ORING_ID     = 2.0, 32.0    # radial O-ring on the tail-cone spigot
GROOVE_DEPTH, GROOVE_W = 1.55, 2.7
INSERT_D, INSERT_DEPTH = 4.0, 8.0     # M3 heat-set (mount foot)
SEAL_OD, SEAL_DEPTH    = 10.2, 2.5    # front-face recess: the brass coupler sinks 1 mm into it
GLAND_HOLE        = 10.5              # tap drill for an M12x1.5 cable gland (tap after printing)
TIP_WALL          = 5.0               # tip thickness = thread engagement for the gland

# ---------------- PROP / DUCT ----------------
PROP_R, PROP_PITCH, PROP_BLADES = 36.0, 45.0, 4
PROP_AX       = 9.0
TIP_GAP       = 0.75
DUCT_L        = 34.0
DUCT_WALL     = 6.5
DUCT_FLARE    = 4.0
STRUT_N, STRUT_T = 4, 3.0
FOOT_W, FOOT_H   = 30.0, 7.0
SEG = 180
FOOT_HOLE_X = 10.0

# ---------------- derived ----------------
BORE_R = MOTOR_D/2 + FIT
TUBE_R = BORE_R + WALL
R_CAP  = TUBE_R + THREAD_CLR + CAP_WALL
L_INT  = SPIGOT_H + REAR_SPACE + MOTOR_L
FRONT_Z = L_INT + FRONT_T
POCKET = NOSE_L + 0.3
SPIN_R = TUBE_R - 0.2
PROP_Z0 = FRONT_Z + 0.6                 # spinner back face
BLADE_ZC = PROP_Z0 + 2 + PROP_AX/2
RI = PROP_R + TIP_GAP
DUCT_Z1 = BLADE_ZC + 0.4*DUCT_L         # inlet (prop side)
DUCT_Z0 = DUCT_Z1 - DUCT_L              # outlet
RO = RI + DUCT_WALL
SHAFT_EXPOSED = (L_INT + SHAFT_OUT) - FRONT_Z
assert SHAFT_EXPOSED > 4, f"only {SHAFT_EXPOSED:.1f} mm shaft exposed"

def rev(pts, seg=SEG):
    a = sum(x0*y1 - x1*y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    return Manifold.revolve(CrossSection([pts if a > 0 else pts[::-1]]), seg)

def cyl(r, h, z0=0.0, seg=SEG):
    return Manifold.cylinder(h, r, r, seg).translate((0, 0, z0))

def polar(n, r, a0=0.0):
    return [(r*np.cos(a0 + 2*np.pi*i/n), r*np.sin(a0 + 2*np.pi*i/n)) for i in range(n)]

THREAD_N, THREAD_DIV = 144, 72     # points per turn, slices per turn (lower = lighter mesh)
def thread_rod(r_major, length, z0=0.0, clr=0.0):
    n = THREAD_N
    """single-start 45-deg trapezoid thread made by twisting a cam-shaped section"""
    pts = []
    for i in range(n):
        u = i/n; th = 2*np.pi*u
        if u < 0.1: f = 0.0
        elif u < 0.5: f = (u - 0.1)/0.4
        elif u < 0.6: f = 1.0
        else: f = 1.0 - (u - 0.6)/0.4
        r = r_major - THREAD_D + f*THREAD_D + clr
        pts.append((r*np.cos(th), r*np.sin(th)))
    turns = length/THREAD_P
    m = Manifold.extrude(CrossSection([pts]), length, n_divisions=int(turns*THREAD_DIV), twist_degrees=360*turns)
    return m.translate((0, 0, z0))

def radial_plate(rz_pts, thick, angle_deg):
    """polygon in (r,z) extruded +-thick/2 tangentially, rotated to angle"""
    cs = CrossSection([rz_pts])
    m = Manifold.extrude(cs, thick).translate((0, 0, -thick/2)).rotate((90, 0, 0))
    return m.rotate((0, 0, angle_deg))

# ===================== HOUSING (prints rear end down, no supports) =====================
def housing(foot=True):
    with_foot = foot
    prof = [(BORE_R, THREAD_L), (TUBE_R, THREAD_L),
            (TUBE_R, FRONT_Z), (0.01, FRONT_Z), (0.01, L_INT), (BORE_R, L_INT)]
    h = rev(prof)
    h = h + (thread_rod(TUBE_R, THREAD_L + 0.01) - cyl(BORE_R, THREAD_L + 2, -1))   # male thread

    # duct (inlet at top in print, 45 deg chamfer at outlet bottom)
    inner = [(RI + 0.5, DUCT_Z0), (RI, DUCT_Z0 + 0.3*DUCT_L), (RI, DUCT_Z1 - 0.3*DUCT_L)]
    n = 12
    for i in range(1, n + 1):
        t = i/n
        inner.append((RI + DUCT_FLARE*t**2, DUCT_Z1 - 0.3*DUCT_L*(1 - t)))
    ch = RO - (RI + 1.3)
    outer = [(RO, DUCT_Z1), (RO, DUCT_Z0 + ch), (RI + 1.3, DUCT_Z0)]
    duct = rev(inner + outer)

    # stator struts: 45 deg underside so they print unsupported
    zt = DUCT_Z0 + 0.3*DUCT_L
    zb = DUCT_Z0 - (RI + 1.0 - (TUBE_R - 1))
    strut = [(TUBE_R - 1, zb), (RI + 1.0, DUCT_Z0), (RI + 1.0, zt), (TUBE_R - 1, zt)]
    struts = Manifold()
    for k in range(STRUT_N):
        struts = struts + radial_plate(strut, STRUT_T, 360*k/STRUT_N + 45)

    # mount foot (on -Y), 45 deg underside
    rf = RO + FOOT_H
    foot_pts = [(RO - 2, DUCT_Z0 + ch - 2), (rf, DUCT_Z0 + ch - 2 + (rf - RO + 2)), (rf, DUCT_Z1), (RO - 2, DUCT_Z1)]
    foot = Manifold.extrude(CrossSection([foot_pts]), FOOT_W).translate((0, 0, -FOOT_W/2)).rotate((90, 0, 0)).rotate((0, 0, -90))
    foot = foot - cyl(RI + 0.2, 200, -10)
    fz0 = DUCT_Z0 + ch - 2 + (rf - RO + 2)
    for z in (fz0 + 4, DUCT_Z1 - 4):
        for x in (-FOOT_HOLE_X, FOOT_HOLE_X):
            foot = foot - Manifold.cylinder(INSERT_DEPTH, INSERT_D/2, INSERT_D/2, 40).rotate((90, 0, 0)).translate((x, -rf - 0.01 + INSERT_DEPTH, z))

    global FOOT_FACE_Y, FOOT_HOLES
    FOOT_FACE_Y = -rf
    FOOT_HOLES = [(x, z) for z in (fz0 + 4, DUCT_Z1 - 4) for x in (-FOOT_HOLE_X, FOOT_HOLE_X)]
    h = h + duct + (struts - cyl(BORE_R, L_INT)) + (foot if with_foot else Manifold())

    # internal features
    h = h - cyl(NOSE_D/2 - 0.15 + NOSE_BORE_ADJ/2, POCKET, L_INT - 0.01)   # nose O-ring bore
    h = h - cyl(SHAFT_D/2 + 0.6, 40, L_INT)
    h = h - cyl(SEAL_OD/2, SEAL_DEPTH + 0.01, FRONT_Z - SEAL_DEPTH)
    return h

# ===================== TAIL CONE (screws on; prints tip down) =====================
CONE_L, CONE_TIP, CONE_SH = 20.0, 9.5, 3.0
SPIG_IN = BORE_R - GROOVE_DEPTH - 2.0
def tail_cone(comp=False):
    """cap frame: z=0 butts the housing rear face, threads/spigot toward +z, cone toward -z
    comp=True adds the internal compensator nipple (bladder inside, 2 mm vent to the water)"""
    W = 2.6
    zt = -CONE_SH - CONE_L
    outer = rev([(0.01, zt), (CONE_TIP, zt), (R_CAP, -CONE_SH), (R_CAP, THREAD_L), (0.01, THREAD_L)])
    c = outer - thread_rod(TUBE_R, THREAD_L + 0.02, -0.01, clr=THREAD_CLR)        # female thread
    rc_top = R_CAP - 4.5
    z45 = -CONE_SH - 1.0 + (rc_top - SPIG_IN)                                  # 45-deg roof, no supports
    c = c - rev([(0.01, zt + TIP_WALL), (CONE_TIP - 1.6, zt + TIP_WALL), (rc_top, -CONE_SH - 1.0),
                 (SPIG_IN, z45), (0.01, z45)])                                   # hollow
    spig = cyl(BORE_R - 0.15, SPIGOT_H + 0.5, -0.5) - cyl(SPIG_IN - 0.3, SPIGOT_H + 2, -1)
    gz = SPIGOT_H/2 - GROOVE_W/2
    spig = spig - (cyl(BORE_R, GROOVE_W, gz) - cyl(BORE_R - GROOVE_DEPTH, GROOVE_W + 2, gz - 1))
    c = c + spig
    c = c - cyl(GLAND_HOLE/2, 10, zt - 1)
    # two flush M4 ports (fill +X, bleed -X): bosses stay inside the cone surface
    zc = -CONE_SH - CONE_L*0.45
    rc = R_CAP + (CONE_TIP - R_CAP)*0.45
    for sgn in (1, -1):
        boss = Manifold.cylinder(9, 5.0, 5.0, 40).rotate((0, 90, 0)).translate((rc - 8 if sgn > 0 else -rc - 1, 0, zc))
        c = c + ((boss ^ outer) - cyl(SPIG_IN - 2, 100, -60))
        c = c - Manifold.cylinder(30, 1.65, 1.65, 30).rotate((0, 90, 0)).translate((rc - 12 if sgn > 0 else -rc - 18, 0, zc))
    if comp:
        # (2026-10-25) v2: the v1 nipple (y 13.5, tip at z -1) sat under the spigot lip, 10 mm down: no room to stretch
        # the finger cot over it or to tie it. Now it stands clear of the lip with its tip 2.5 mm under the rim, so the cot
        # slides straight down over it, and a 5 x 1.5 mm O-ring rolled over the barb into the groove holds the cot (no tie).
        yt, zb, ztop = COMP_Y, -18.0, COMP_TIP
        zg = ztop - COMP_BARB                                                    # groove top = barb bottom
        stem = Manifold.cylinder(zg - COMP_GROOVE - zb, 3.0, 3.0, 40).translate((0, yt, zb))
        groove = Manifold.cylinder(COMP_GROOVE, COMP_GROOVE_R, COMP_GROOVE_R, 40).translate((0, yt, zg - COMP_GROOVE))
        barb = Manifold.cylinder(COMP_BARB, 3.6, 2.6, 40).translate((0, yt, zg))   # wide at the bottom: holds the ring
        c = c + ((stem + groove + barb) ^ outer)
        zv = -17.5                                                               # vent: down the nipple, then 45 deg out
        c = c - Manifold.cylinder(ztop - zv + 1, 1.1, 1.1, 24).translate((0, yt, zv))
        c = c - Manifold.cylinder(12, 1.1, 1.1, 24).rotate((-135, 0, 0)).translate((0, yt, zv))   # toward +y, -z
    return c

COMP_Y = 8.5        # nipple axis: barb clears the spigot lip (r 14.4) by 2.3 mm and the gland hole (r 5.25)
COMP_TIP = 6.0      # nipple tip, 2.5 mm under the spigot rim (z 8.5): the cot goes on from straight above
COMP_BARB, COMP_GROOVE, COMP_GROOVE_R = 2.0, 2.0, 2.5   # barb 7.2 -> 5.2 mm; groove 5.0 mm dia for a 5 x 1.5 O-ring

# ===================== PROP with spinner =====================
COUPLER_D, COUPLER_L = 9.0, 20.0   # brass 3 mm -> 5 mm shaft coupler
COUPLER_CLR = 0.6                  # hub bore = 9.6 mm
COUPLER_SINK = 1.0                 # coupler bottom sits this far below the housing face (set with coupler_gauge)
NUT_AF, JAM_T, NYLOC_T = 8.0, 4.0, 5.0   # M5 hex nut (jam, drives the hub) and M5 nyloc (holds it on)
HEX_CLR = 0.3
WEB_T = 4.0                        # hub floor between the two nuts
NOSE_LEN = 36.0                    # spinner taper length (hub + nose cone)
SPIG_RI, SPIG_RO, SPIG_H = 6.8, 12.0, 6.0   # hub spigot the nose cone slides over (ID fits an 8 mm nut driver)
NOSE_SCREW_DZ = 3.0                # radial M3x6 button screws, 3 places
Z_CPL0 = FRONT_Z - COUPLER_SINK
Z_CPL1 = Z_CPL0 + COUPLER_L
Z_WEB0 = Z_CPL1 + JAM_T
Z_SPLIT = Z_WEB0 + WEB_T           # hub top / nose cone base
def blade(theta0, hand):
    rs = np.linspace(SPIN_R - 1.5, PROP_R, 36); ns = 24; rings = []
    for r in rs:
        phi = np.arctan(PROP_PITCH/(2*np.pi*r))
        chord = PROP_AX/np.sin(phi)
        rm = SPIN_R + 0.55*(PROP_R - SPIN_R)
        if r > rm:
            chord *= max(0.35, np.sqrt(max(0, 1 - ((r - rm)/(PROP_R - rm))**2)))
        thick = np.interp(r, [SPIN_R, PROP_R], [2.6, 1.2])
        ss = -np.cos(np.linspace(0, np.pi, ns))*chord/2
        half = [max(0.2, thick/2*np.sqrt(max(0, 1 - (2*s/chord)**2))) for s in ss]
        loop = list(zip(ss, half)) + [(s, -d) for s, d in zip(ss[::-1], half[::-1])]
        ring = []
        for s, d in loop:
            z = BLADE_ZC + s*np.sin(phi) + d*np.cos(phi)
            a = theta0 + hand*(s*np.cos(phi) - d*np.sin(phi))/r
            ring.append((r*np.cos(a), r*np.sin(a), z))
        rings.append(ring)
    V = np.array([p for rg in rings for p in rg]); m = len(rings[0]); F = []
    for i in range(len(rings) - 1):
        for j in range(m):
            a, b = i*m + j, i*m + (j + 1) % m
            F += [(a, b, b + m), (a, b + m, a + m)]
    for idx, flip in ((0, True), (len(rings) - 1, False)):
        ci = len(V); V = np.vstack([V, V[idx*m:(idx + 1)*m].mean(0)])
        for j in range(m):
            a, b = idx*m + j, idx*m + (j + 1) % m
            F.append((ci, b, a) if flip else (ci, a, b))
    tm = trimesh.Trimesh(V, np.array(F)); trimesh.repair.fix_normals(tm)
    return Manifold(Mesh(vert_properties=np.asarray(tm.vertices, np.float32), tri_verts=np.asarray(tm.faces, np.uint32)))

def spinner_r(z):
    u = z - PROP_Z0
    if u <= 13.0: return SPIN_R
    t = min(1.0, (u - 13.0)/NOSE_LEN)
    return max(0.6, SPIN_R*(1 - t**1.7))

def spinner_profile(z0, z1, n=40):
    zs = np.linspace(z0, z1, n)
    if z0 < PROP_Z0 + 13.0 < z1: zs = np.sort(np.append(zs, PROP_Z0 + 13.0))
    return [(spinner_r(z), z) for z in zs]

def hex_prism(af, h, z0):
    rc = af/np.sqrt(3)
    return Manifold.cylinder(h, rc, rc, 6).rotate((0, 0, 30)).translate((0, 0, z0))

def prop_hub(hand=1):
    pts = [(0.01, PROP_Z0)] + spinner_profile(PROP_Z0, Z_SPLIT) + [(0.01, Z_SPLIT)]
    p = rev(pts, 120)
    p = p + (cyl(SPIG_RO, SPIG_H, Z_SPLIT - 0.01, 96) - cyl(SPIG_RI, SPIG_H + 2, Z_SPLIT - 1, 96))
    for k in range(PROP_BLADES):
        p = p + blade(2*np.pi*k/PROP_BLADES, hand)
    p = p - cyl(COUPLER_D/2 + COUPLER_CLR/2, Z_CPL1 - PROP_Z0 + 1.01, PROP_Z0 - 1, 64)   # coupler bore
    p = p - hex_prism(NUT_AF + HEX_CLR, Z_WEB0 - Z_CPL1 + 0.21, Z_CPL1 - 0.2)          # jam-nut hex drive
    p = p - cyl(2.75, WEB_T + 1, Z_WEB0 - 0.5, 40)                                      # stud through the floor
    for k in range(3):                                                                  # M3 pilot holes for the nose screws
        a = 360*k/3 + 60
        p = p - Manifold.cylinder(SPIG_RO - SPIG_RI + 1, 1.25, 1.25, 24).rotate((0, 90, 0)) \
                .translate((SPIG_RI - 0.5, 0, Z_SPLIT + NOSE_SCREW_DZ)).rotate((0, 0, a))
    return p

def nose_cone():
    tip = PROP_Z0 + 13.0 + NOSE_LEN
    p = rev([(0.01, Z_SPLIT)] + spinner_profile(Z_SPLIT, tip, 60) + [(0.01, tip)], 120)
    s_r = SPIG_RO + 0.2
    roof = Z_SPLIT + SPIG_H + 0.2
    cav = rev([(0.01, Z_SPLIT - 1), (s_r, Z_SPLIT - 1), (s_r, roof), (5.8, roof + (s_r - 5.8)),
               (0.01, roof + (s_r - 5.8) + 5.8)], 96)                                  # 45-deg roofs: no supports
    p = p - cav
    for k in range(3):
        a = 360*k/3 + 60
        z = Z_SPLIT + NOSE_SCREW_DZ
        hole = Manifold.cylinder(15, 1.7, 1.7, 24).rotate((0, 90, 0)).translate((s_r - 1, 0, z))
        cbore = Manifold.cylinder(15, 3.1, 3.1, 32).rotate((0, 90, 0)).translate((s_r + 1.5, 0, z))
        p = p - (hole + cbore).rotate((0, 0, a))
    return p

def prop(hand=1):
    """assembled hub + nose cone (for fit checks and the viewer)"""
    return prop_hub(hand) + nose_cone()

def coupler_gauge():
    """stands on the housing face; push the coupler up until it touches the ceiling, tighten, remove"""
    H = COUPLER_L - COUPLER_SINK            # ceiling height above the housing face
    g = cyl(9.5, H + 2.0, 0, 64) - cyl(COUPLER_D/2 + 0.4, H, -0.01, 64) - cyl(2.0, 5, H - 1, 24)
    for a in (0, 90):                       # windows to reach the shaft-end set screws
        g = g - Manifold.cube((12, 7, 10)).translate((0, -3.5, -0.01)).rotate((0, 0, a))
    return g

def save(m, name):
    g = m.to_mesh(); tm = trimesh.Trimesh(g.vert_properties[:, :3], g.tri_verts)
    tm.export(f"out/{name}.stl")
    print(f"{name:12s} watertight={tm.is_watertight} vol={tm.volume/1000:5.1f}cm3 size={np.round(tm.extents,1)}")
    return tm

if __name__ == "__main__":
    os.makedirs("out", exist_ok=True)
    for f in os.listdir("out"):
        if f.endswith(".stl"): os.remove("out/" + f)
    H, C = housing(), tail_cone()
    save(H, "housing_with_foot")
    save(housing(foot=False), "housing_no_foot")
    save(C.translate((0, 0, CONE_SH + CONE_L)), "tail_cone")
    save(tail_cone(comp=True).translate((0, 0, CONE_SH + CONE_L)), "tail_cone_comp")
    save(prop_hub(1).translate((0, 0, -PROP_Z0)), "prop_hub_RH")
    save(prop_hub(-1).translate((0, 0, -PROP_Z0)), "prop_hub_LH")
    save(nose_cone().translate((0, 0, -Z_SPLIT)), "nose_cone")
    save(coupler_gauge(), "coupler_gauge")
    print(f"shaft exposed {SHAFT_EXPOSED:.1f}  duct ID {2*RI:.1f} OD {2*RO:.1f}  body OD {2*TUBE_R:.1f}  cap OD {2*R_CAP:.1f}  O-ring {ORING_ID:.0f}x{ORING_CS}")
