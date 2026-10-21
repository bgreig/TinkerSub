"""
Realistic 3D scene of the electronics sled for the guide's Electronics section: every board, the 12 V bus, fuses, the
LED drivers and the wiring harnesses, placed on the real sled parts (212-215, 207) inside the hull.

Coordinates: sled frame, mm. x = starboard, y = up, z = aft. z 0 = front bulkhead (207) inner face, deck 214 top face
at y +1.5, rear bulkhead 215 rear face at z 241.5. Hull frame -> sled frame: x -> -x, z -> 145 - z.
Board positions come from the deck's own mounting slots and holes (214), the bulkhead pockets (215) and the
electronics page's sled layout.

Writes  <out>/elec_scene.json  (meshes for render_real.html: v, i, color, rough, metal, opacity)
usage:  python3 elec_scene.py <assembly_v6.json> <out_dir>
"""
import sys, json, base64, numpy as np, trimesh
from trimesh.creation import box as _box, cylinder as _cyl

ASM, OUT = sys.argv[1], sys.argv[2]
MESH = {}                                            # key -> [trimesh list, props]
def add(key, m, color, rough=0.55, metal=0.0, opacity=1.0, clear=0.0, smooth=False):
    key = f"{key}|{color}|{rough}|{metal}|{opacity}"            # one mesh per key and material; the renderer filters on the part before "|"
    if key not in MESH: MESH[key] = [[], dict(color=color, rough=rough, metal=metal, opacity=opacity, clear=clear, smooth=smooth)]
    MESH[key][0].append(m)

def B(x0, x1, y0, y1, z0, z1):
    m = _box(extents=[x1 - x0, y1 - y0, z1 - z0]); m.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2]); return m
def CY(r, h, axis="y", c=(0, 0, 0), sections=32):
    m = _cyl(radius=r, height=h, sections=sections)               # along z
    if axis == "y": m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    if axis == "x": m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    m.apply_translation(c); return m

def tube(pts, r, fillet=6.0, sides=14, profile=None):
    """Sweep a circle (or a w x h rectangle given as profile=(w, h)) along a polyline with rounded corners."""
    P = [np.array(p, float) for p in pts]
    path = [P[0]]
    for i in range(1, len(P) - 1):
        a, b, c = P[i - 1], P[i], P[i + 1]
        u, v = b - a, c - b; lu, lv = np.linalg.norm(u), np.linalg.norm(v)
        if lu < 1e-6 or lv < 1e-6: continue
        f = min(fillet, lu / 2.01, lv / 2.01)
        p0, p1 = b - u / lu * f, b + v / lv * f
        for t in np.linspace(0, 1, 9): path.append((1 - t) ** 2 * p0 + 2 * (1 - t) * t * b + t ** 2 * p1)
    path.append(P[-1])
    Q = [path[0]]
    for p in path[1:]:
        if np.linalg.norm(p - Q[-1]) > 0.05: Q.append(p)
    Q = np.array(Q)
    T = np.gradient(Q, axis=0); T /= np.linalg.norm(T, axis=1)[:, None]
    ref = np.array([0, 1, 0.0]) if abs(T[0][1]) < 0.9 else np.array([1, 0, 0.0])
    N = np.cross(T[0], ref); N /= np.linalg.norm(N)
    frames = []
    for i, t in enumerate(T):                               # parallel transport
        if i:
            N = N - np.dot(N, t) * t; N /= np.linalg.norm(N)
        frames.append((N, np.cross(t, N)))
    if profile is None:
        ang = np.linspace(0, 2 * np.pi, sides, endpoint=False); ring = [(r * np.cos(a), r * np.sin(a)) for a in ang]
    else:
        w, h = profile; ring = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    k = len(ring); V = []
    for q, (n, bn) in zip(Q, frames):
        for (a, b) in ring: V.append(q + a * n + b * bn)
    F = []
    for i in range(len(Q) - 1):
        for j in range(k):
            a, b, c, d = i * k + j, i * k + (j + 1) % k, (i + 1) * k + (j + 1) % k, (i + 1) * k + j
            F += [[a, b, c], [a, c, d]]
    V = np.array(V); n0 = len(V)
    V = np.vstack([V, Q[0], Q[-1]])
    for j in range(k):
        F += [[n0, (j + 1) % k, j], [n0 + 1, (len(Q) - 1) * k + j, (len(Q) - 1) * k + (j + 1) % k]]
    return trimesh.Trimesh(V, np.array(F), process=False)

def offset_path(pts, off, keep_ends=1):
    """Shift the middle waypoints of a route sideways by off = (a, b) in the plane across the route (bundles)."""
    P = np.array(pts, float); out = P.copy()
    for i in range(keep_ends, len(P) - keep_ends):
        t = P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]; t /= np.linalg.norm(t)
        ref = np.array([0, 1, 0.0]) if abs(t[1]) < 0.8 else np.array([1, 0, 0.0])
        n1 = np.cross(t, ref); n1 /= np.linalg.norm(n1); n2 = np.cross(t, n1)
        out[i] = P[i] + off[0] * n1 + off[1] * n2
    return out

# ------------------------------------------------------------------ colours / materials
PCB_RED, PCB_PI, PCB_GRN = "#9c1f1a", "#1d6b3b", "#24703c"
BLK, CHIP, SILV, GOLD, BRASS = "#141517", "#18191b", "#c9ccd0", "#d4aa45", "#b8913c"
W_RED, W_BLK, W_YEL, W_ORG, W_BRN, W_WHT, W_BLU, W_GRN, W_PUR, W_GRY = ("#c81e1e", "#1b1c1f", "#e3b20e", "#ee7a16", "#6b3e1f",
                                                                         "#e8e8e4", "#2161c9", "#2d9a3e", "#7a3fb8", "#8b9096")

# ------------------------------------------------------------------ mechanical context from the assembly (hull frame -> sled frame)
S = np.array([[-1, 0, 0, 0], [0, 1, 0, 0], [0, 0, -1, 145.0], [0, 0, 0, 1]], float)
def b64d(s, T): return np.frombuffer(base64.b64decode(s), T)
A = json.load(open(ASM))
MECH = {"hull": ("hull", "#d9dde0", 0.35, 0, 0.18), "fl_rear": ("fl_rear", "#232629", 0.6, 0, 1), "cap_rear": ("cap_rear", "#232629", 0.6, 0, 1),
        "fl_front": ("fl_front", "#232629", 0.6, 0, 1), "dome_ring": ("dome_ring", "#232629", 0.6, 0, 1), "dome": ("dome", "#dfeef7", 0.05, 0, 0.25),
        "bh_front": ("bh_207", "#2a2c2f", 0.55, 0, 1), "rod": ("rods", "#a9aeb3", 0.3, 0.9, 1),
        "sl_rail_p": ("rail_212", "#26282b", 0.62, 0, 1), "sl_rail_s": ("rail_213", "#26282b", 0.62, 0, 1),
        "sl_deck": ("deck_214", "#2b2d30", 0.62, 0, 1), "sl_bh": ("bh_215", "#26282b", 0.62, 0, 1),
        "pt_base": ("pt", "#26282b", 0.6, 0, 1), "pt_yoke": ("pt", "#26282b", 0.6, 0, 1), "pt_cradle": ("pt", "#26282b", 0.6, 0, 1),
        "pt_lever": ("pt", "#26282b", 0.6, 0, 1), "pt_pan_servo": ("pt_servo", "#2a4f9e", 0.45, 0, 1),
        "pt_tilt_servo": ("pt_servo", "#2a4f9e", 0.45, 0, 1), "pt_camera": ("pt_cam", "#1f6e3a", 0.5, 0, 1)}
for inst in A["instances"]:
    k = inst["k"]
    if k not in MECH: continue
    m = A["meshes"][k]
    t = trimesh.Trimesh(b64d(m["v"], np.float32).reshape(-1, 3).astype(float), b64d(m["i"], np.uint32).reshape(-1, 3), process=False)
    M = np.array(inst["m"]).reshape(4, 4).T
    t.apply_transform(S @ M)
    key, col, rough, metal, op = MECH[k]
    add(key, t, col, rough, metal, op)

# ------------------------------------------------------------------ board placement
DECK = 1.5; STAND = 8.0; PT = 1.6
def place(parts, face, x, z, key):
    """parts: [(mesh in board frame: PCB bottom at y 0, parts on +y), colour, rough, metal]; face 'top' or 'bot'."""
    for m, col, rough, metal in parts:
        m = m.copy()
        if face == "bot": m.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
        m.apply_translation([x, DECK + STAND if face == "top" else -DECK - STAND, z])
        add(key, m, col, rough, metal, clear=0.25 if col in (PCB_RED, PCB_PI, PCB_GRN) else 0)
def bpt(face, x, z, lx, ly, lz):
    """Board-frame point -> sled frame."""
    if face == "top": return np.array([x + lx, DECK + STAND + ly, z + lz])
    return np.array([x + lx, -DECK - STAND - ly, z - lz])

def standoffs(face, x, z, dx, dz, h=STAND, r=2.75, col=BRASS, screw=True):
    for sx in (-dx, dx):
        for sz in (-dz, dz):
            y0, y1 = (DECK, DECK + h) if face == "top" else (-DECK - h, -DECK)
            add("standoffs", CY(r, y1 - y0, "y", (x + sx, (y0 + y1) / 2, z + sz), sections=6), col, 0.35, 0.85)
            if screw:
                yy = DECK + h + PT + 0.9 if face == "top" else -DECK - h - PT - 0.9
                add("screws", CY(2.7, 1.8, "y", (x + sx, yy, z + sz), sections=20), SILV, 0.3, 0.9)

# ---- IBT_2 (BTS7960 dual half-bridge), heatsink removed. Board frame: x -25 (port, power terminals) .. +25 (stbd, 8-pin header)
def ibt2():
    P = [(B(-25, 25, 0, PT, -25, 25), PCB_RED, 0.45, 0)]
    P.append((B(-25, -14.5, PT, PT + 10.5, -12.5, 12.5), "#2a5db0", 0.5, 0))              # 4-way screw terminal B+ B- M+ M-
    for i, zz in enumerate((-9.4, -3.1, 3.1, 9.4)):
        P.append((CY(1.9, 1.0, "y", (-19.5, PT + 10.6, zz)), SILV, 0.3, 0.9))
        P.append((B(-25.05, -23.5, PT + 2.5, PT + 6.5, zz - 1.8, zz + 1.8), "#0d0e10", 0.8, 0))
    P.append((B(20.5, 23.0, PT, PT + 2.5, -10.2, 10.2), BLK, 0.6, 0))                    # 8-pin header
    for i in range(8):
        P.append((B(21.43, 22.07, PT + 2.5, PT + 8.5, -8.89 + i * 2.54 - 0.32, -8.89 + i * 2.54 + 0.32), GOLD, 0.25, 1.0))
    for zz in (-10.5, 10.5):                                                                # 2 x BTS7960 (TO-263-7)
        P.append((B(-6, 4, PT, PT + 4.4, zz - 5, zz + 5), CHIP, 0.35, 0))
        P.append((B(4, 6.5, PT, PT + 0.6, zz - 4, zz + 4), SILV, 0.3, 0.9))
        for j in range(7): P.append((B(-9, -6, PT, PT + 0.5, zz - 3.9 + j * 1.27 - 0.3, zz - 3.9 + j * 1.27 + 0.3), SILV, 0.3, 0.9))
    P.append((B(9.5, 17, PT, PT + 2.3, -6.6, 6.6), CHIP, 0.4, 0))                          # 74HC244
    for j in range(10):
        for s in (8.6, 17.4):
            P.append((B(s - 0.5, s + 0.5, PT, PT + 0.6, -5.7 + j * 1.27 - 0.2, -5.7 + j * 1.27 + 0.2), SILV, 0.3, 0.9))
    P.append((CY(4, 10.5, "y", (-9.5, PT + 5.25, 0)), "#1e2a63", 0.35, 0))                  # input cap
    P.append((CY(3.6, 0.3, "y", (-9.5, PT + 10.6, 0)), SILV, 0.3, 0.9))
    rng = np.random.default_rng(7)
    for _ in range(14):
        cx, cz = rng.uniform(5, 19), rng.uniform(-22, 22)
        if abs(cz) < 7.5 and 8 < cx < 18: continue
        P.append((B(cx, cx + 1.6, PT, PT + 0.6, cz, cz + 0.8), rng.choice(["#3a3226", "#b9a27c", "#5a5d61"]), 0.5, 0))
    P.append((B(13, 15, PT, PT + 0.8, 18, 19.6), "#e33b2c", 0.3, 0))                        # power LED
    return P
IBT = ibt2()
BX, BZ = 3.2, (101.0, 153.0, 205.0)                  # pair centres (deck slots); T1-T3 on top, T4-T6 under T1-T3
for i, zc in enumerate(BZ):
    place(IBT, "top", BX, zc, f"ibt_T{i + 1}"); standoffs("top", BX, zc, 21, 21)
    place(IBT, "bot", BX, zc, f"ibt_T{i + 4}"); standoffs("bot", BX, zc, 21, 21)

# ---- Pi Zero 2W, top face, header to starboard, CSI to the front, SD card aft (pins 1-10 at the aft end)
def pizero():
    P = [(B(-15, 15, 0, PT, -32.5, 32.5), PCB_PI, 0.45, 0)]
    P.append((B(-6.5, 8, PT, PT + 1.3, -9, 5.5), "#b9bcc0", 0.25, 0.8))                   # RP3A0 lid
    P.append((B(9.0, 14.0, PT, PT + 2.5, -25.4, 25.4), BLK, 0.6, 0))                       # 2 x 20 header
    for i in range(20):
        for xx in (10.23, 12.77):
            P.append((B(xx - 0.32, xx + 0.32, PT + 2.5, PT + 8.5, 24.13 - i * 2.54 - 0.32, 24.13 - i * 2.54 + 0.32), GOLD, 0.25, 1))
    for zz, w in ((32.5 - 12.4, 11.2), (32.5 - 41.4, 7.5), (32.5 - 54.0, 7.5)):          # mini HDMI, USB OTG, PWR
        P.append((B(-15.6, -10.5, PT, PT + 3.0, zz - w / 2, zz + w / 2), SILV, 0.25, 0.9))
    P.append((B(-8.5, 8.5, PT, PT + 1.4, -32.6, -28.6), "#2a2a2a", 0.5, 0))                # CSI connector
    P.append((B(-8.5, 8.5, PT + 1.4, PT + 2.0, -32.6, -31.0), "#d8cfb8", 0.6, 0))
    P.append((B(-6, 6, PT, PT + 1.4, 22, 33), SILV, 0.3, 0.9))                             # micro SD
    P.append((B(-13, -7, PT, PT + 1.0, 8, 16), "#c7c9cc", 0.3, 0.7))                       # wifi can
    P.append((B(3, 4.2, PT, PT + 0.5, 28, 29.5), "#3ad06a", 0.3, 0))
    return P
PI = (15.5, 36.0)
place(pizero(), "top", PI[0], PI[1], "pizero"); standoffs("top", PI[0], PI[1], 11.5, 29, h=STAND, r=2.4, col=BRASS)

# ---- Waveshare ETH/USB HUB HAT on the Pi (2026-10-16, replaces the separate USB-Ethernet adapter). Same 65 x 30 footprint,
# 11 mm above the Pi on the 40-pin header + 4 standoffs; RJ45 and 3 USB-A on the Pi's port-facing edge (toward the hull
# centreline); stacking pins above the HAT carry the UART / 5 V wires; a small micro-USB link board joins the Pi's USB OTG
# port to the HAT's hub input. Board frame as the Pi: x -15 port edge .. +15 header edge, z -32.5 front .. +32.5 aft.
HAT_Y = PT + 11.0                                   # HAT PCB bottom above the Pi PCB bottom
PCB_HAT = "#1f4f9e"
def hat():
    P = [(B(-15, 15, HAT_Y, HAT_Y + PT, -32.5, 32.5), PCB_HAT, 0.45, 0)]
    P.append((B(9.0, 14.0, PT + 2.5, HAT_Y, -25.4, 25.4), BLK, 0.6, 0))                    # female header under the HAT
    for i in range(20):
        for xx in (10.23, 12.77):
            P.append((B(xx - 0.32, xx + 0.32, HAT_Y + PT, HAT_Y + PT + 10.0, 24.13 - i * 2.54 - 0.32, 24.13 - i * 2.54 + 0.32), GOLD, 0.25, 1))
    P.append((B(-16.5, 4.5, HAT_Y - 1.6, HAT_Y + PT + 11.5, 3.5, 19.5), SILV, 0.3, 0.85))      # RJ45 (mid-mount), opening faces port
    P.append((B(-16.55, -14, HAT_Y + 1.5, HAT_Y + PT + 9.5, 6.0, 17.0), "#0a0a0a", 0.8, 0))
    for z0, z1 in ((20.0, 32.5), (-14.5, -0.5), (-32.5, -19.5)):                              # 3 x USB-A
        P.append((B(-16.0, -2.0, HAT_Y + PT, HAT_Y + PT + 7.0, z0, z1), SILV, 0.3, 0.85))
        P.append((B(-16.05, -10, HAT_Y + PT + 1.2, HAT_Y + PT + 5.8, z0 + 1.0, z1 - 1.0), "#1f3f8f", 0.5, 0))
    P.append((B(-6, 2, HAT_Y + PT, HAT_Y + PT + 1.2, -2, 5), CHIP, 0.4, 0))                  # RTL8152B
    P.append((B(-19.0, -17.4, -6.5, HAT_Y, 32.5 - 41.4 - 6.0, 32.5 - 41.4 + 6.0), PCB_HAT, 0.45, 0))   # micro-USB link board
    P.append((B(-17.4, -10.5, 0.4, PT + 3.0, 32.5 - 41.4 - 3.8, 32.5 - 41.4 + 3.8), SILV, 0.3, 0.9))
    return P
place(hat(), "top", PI[0], PI[1], "pihat")
for sx in (-11.5, 11.5):
    for sz in (-29.0, 29.0):
        add("standoffs", CY(2.4, HAT_Y - PT, "y", (PI[0] + sx, DECK + STAND + PT + (HAT_Y - PT) / 2, PI[1] + sz), sections=6), BRASS, 0.35, 0.85)
        add("screws", CY(2.5, 1.6, "y", (PI[0] + sx, DECK + STAND + HAT_Y + PT + 0.8, PI[1] + sz), sections=20), SILV, 0.3, 0.9)

# ---- Pico, underneath, USB to the front; pins 1-20 starboard row (pin 1 front), 21-40 port row (pin 40 front)
def pico():
    P = [(B(-10.5, 10.5, 0, PT, -25.5, 25.5), PCB_GRN, 0.45, 0)]
    P.append((B(-3.5, 3.5, PT, PT + 0.9, -3.5, 3.5), CHIP, 0.35, 0))                        # RP2040
    P.append((B(-2.6, 2.6, PT, PT + 1.0, 8, 14), CHIP, 0.35, 0))                           # flash
    P.append((B(-4, 4, PT, PT + 3.0, 21.5, 26.5), SILV, 0.25, 0.9))                        # micro USB (local +z -> front after flip)
    P.append((B(3.5, 7.5, PT, PT + 1.6, 16.5, 20.5), "#f2f2ee", 0.4, 0))                    # BOOTSEL
    P.append((B(-7, -4.5, PT, PT + 0.8, 10, 13.2), SILV, 0.3, 0.9))                        # crystal
    for s in (-8.89, 8.89):
        P.append((B(s - 1.27, s + 1.27, PT, PT + 2.5, -25.4, 25.4), BLK, 0.6, 0))
        for i in range(20):
            zz = 24.13 - i * 2.54
            P.append((B(s - 0.32, s + 0.32, PT + 2.5, PT + 8.5, zz - 0.32, zz + 0.32), GOLD, 0.25, 1))
    return P
# (2026-10-16) the Pico sits on a 57 x 63 mm screw-terminal breakout under the front of the deck (the builder's board),
# centred between the rails on 10 mm standoffs; terminal strips along both long edges face the rails, the Pico plugs into
# the breakout's female headers from below, USB to the front. Pin n's terminal entry: pico_pin(n). The separate buck is
# replaced by a CPT 12 V -> 5 V 3 A potted converter on the top face, port side, beside the Pi + HAT.
BRK = dict(z0=4.0, z1=67.0, w=57.0, h=10.0)
BY0 = -DECK - BRK["h"]                                    # breakout board top face (toward the deck)
def brk_z(n):
    k = (n - 1) if n <= 20 else (40 - n)
    return BRK["z0"] + 3.0 + k * 3.0
def pico_pin(n):
    """Entry of the breakout's screw terminal for Pico pin n (1-20 starboard, pin 1 at the front; 21-40 port)."""
    return np.array([29.2 if n <= 20 else -29.2, BY0 - PT - 4.9, brk_z(n)])
add("pico_brk", B(-BRK["w"] / 2, BRK["w"] / 2, BY0 - PT, BY0, BRK["z0"], BRK["z1"]), "#1f7a3c", 0.45, 0, clear=0.25)
for sx in (-1, 1):
    add("pico_term", B(sx * 21.0, sx * 28.5, BY0 - PT - 9.5, BY0 - PT, BRK["z0"] + 1.5, BRK["z1"] - 1.5) if sx > 0 else
        B(sx * 28.5, sx * 21.0, BY0 - PT - 9.5, BY0 - PT, BRK["z0"] + 1.5, BRK["z1"] - 1.5), "#2fa24f", 0.55, 0)
    for k in range(20):
        z = BRK["z0"] + 3.0 + k * 3.0
        add("pico_term_sc", CY(1.1, 0.4, "y", (sx * 24.0, BY0 - PT - 9.6, z), sections=12), SILV, 0.3, 0.9)
        add("pico_term_hole", B(sx * 28.55 - 0.3, sx * 28.55 + 0.3, BY0 - PT - 6.0, BY0 - PT - 3.8, z - 0.9, z + 0.9), "#0b0b0c", 0.8)
    add("pico_hdr", B(sx * 8.89 - 1.27, sx * 8.89 + 1.27, BY0 - PT - 8.5, BY0 - PT, 35.5 - 25.4, 35.5 + 25.4), BLK, 0.6, 0)
    for sz in (BRK["z0"] + 3.0, BRK["z1"] - 3.0):
        add("standoffs", CY(2.75, BRK["h"], "y", (sx * 25.0, -DECK - BRK["h"] / 2, sz), sections=6), BRASS, 0.35, 0.85)
PY0 = BY0 - PT - 8.5 - 2.5                                # Pico PCB (its headers in the breakout's sockets), components down
add("pico", B(-10.5, 10.5, PY0 - PT, PY0, 35.5 - 25.5, 35.5 + 25.5), PCB_GRN, 0.45, 0, clear=0.25)
add("pico", B(-3.5, 3.5, PY0 - PT - 0.9, PY0 - PT, 32, 39), CHIP, 0.35, 0)
add("pico", B(-4, 4, PY0 - PT - 3.0, PY0 - PT, 35.5 - 26.5, 35.5 - 21.5), SILV, 0.25, 0.9)         # micro USB, front
add("pico", B(3.5, 7.5, PY0 - PT - 1.6, PY0 - PT, 35.5 - 20.5, 35.5 - 16.5), "#f2f2ee", 0.4, 0)   # BOOTSEL
for sx in (-8.89, 8.89): add("pico", B(sx - 1.27, sx + 1.27, PY0, PY0 + 2.5, 10.1, 60.9), BLK, 0.6, 0)

# ---- two mini MP1584EN 5 V 1.8 A buck boards (~22 x 17 mm, heat-shrunk, foam tape) on the top face, port side beside
# the Pi: U9A (front) feeds the Pi / HAT / camera / Pico, U9B (behind it) only the servos. IN at the front end, OUT aft.
MB = {"U9A": (8.0, 30.0), "U9B": (31.0, 53.0)}; MBX = (-27.0, -10.0)
for k, (z0, z1) in MB.items():
    add("mini_buck", B(MBX[0], MBX[1], DECK, DECK + 1.0, z0, z1), "#d8d8d2", 0.8, 0)                     # foam tape
    add("mini_buck", B(MBX[0], MBX[1], DECK + 1.0, DECK + 2.6, z0, z1), "#1d6fb8", 0.45, 0, clear=0.25)
    add("mini_buck", B(-23.0, -16.0, DECK + 2.6, DECK + 5.6, (z0 + z1) / 2 - 3.5, (z0 + z1) / 2 + 3.5), "#2b2d30", 0.5, 0.2)  # inductor
    add("mini_buck", B(-14.5, -11.5, DECK + 2.6, DECK + 3.6, z0 + 3, z0 + 7), CHIP, 0.4, 0)
    add("mini_buck_hs", B(MBX[0] - 0.4, MBX[1] + 0.4, DECK + 0.9, DECK + 6.2, z0 + 0.5, z1 - 0.5), "#2b6fb8", 0.3, 0, opacity=0.35)  # clear heat-shrink
S5 = np.array([12.0, 5.0, 71.5])                                   # 5 V splice above the deck slot behind the Pi
add("splice", CY(1.6, 7.0, "x", S5 + [2.5, 0, 0], sections=12), "#2a2a2c", 0.5)

# ---- rear bulkhead 215, rear face (z 241.5): Wago 221-415 x2 port side (entries face port), LDD-700HW x2 starboard
ZR = 241.5
def wago(y0, key):
    add(key, B(-20.7, -2.0, y0, y0 + 30.1, ZR, ZR + 8.3), "#c7ced3", 0.15, 0.0, opacity=0.78, clear=0.8)
    for i in range(5):
        yy = y0 + 3.0 + i * 6.0
        add("wago_lever", B(-20.4, -6, yy - 2.2, yy + 2.2, ZR + 8.3, ZR + 9.6), "#f07c1b", 0.4)
        add("wago_slot", B(-20.75, -20.6, yy - 1.4, yy + 1.4, ZR + 2.5, ZR + 5.5), "#3a3f44", 0.6)
    return [np.array([-20.7, y0 + 3.0 + i * 6.0, ZR + 4.0]) for i in range(5)]       # wire entry points, top to bottom
WP = wago(2.5, "wago_12v"); WG = wago(-32.6, "wago_gnd")
WP.sort(key=lambda p: -p[1]); WG.sort(key=lambda p: -p[1])
def ldd(y0, key):
    add(key, B(2.5, 22.5, y0, y0 + 31.8, ZR, ZR + 12.2), "#151618", 0.45)
    add(key, B(5, 20, y0 + 6, y0 + 25, ZR + 12.2, ZR + 12.3), "#e4e4e0", 0.7)            # label
    return {n: np.array([4.5 + i * 3.6, y0 + (31.8 if y0 > 0 else 0), ZR + 6]) for i, n in enumerate(("+Vin", "-Vin", "DIM", "+Vo", "-Vo"))}
L1 = ldd(3.0, "ldd1"); L2 = ldd(-32.8, "ldd2")
for k, y0 in (("ziptie", 1.0), ("ziptie", -34.3)):
    add(k, B(-22, 24, y0 + 14, y0 + 17.5, ZR + 12.4, ZR + 13.5), "#0b0b0c", 0.5)

# ---- hull rear cap glands (inside nuts) at r 26: MOTORS upper port, LIGHTS upper stbd, BATTERY lower stbd, TETHER lower port
ZC = 358.2
GL = {"MOTORS": (-18.4, 18.4, 11.0), "LIGHTS": (18.4, 18.4, 8.5), "BATTERY": (18.4, -18.4, 11.0), "TETHER": (-18.4, -18.4, 8.5)}
for n, (gx, gy, r) in GL.items():
    add("glands", CY(r, 6, "z", (gx, gy, ZC - 3), sections=6), "#2c2f33", 0.5)
    add("glands", CY(r * 0.62, 7, "z", (gx, gy, ZC - 9.5)), "#2c2f33", 0.5)
add("glands", CY(5.5, 5, "z", (0, 0, ZC - 2.5), sections=6), "#c9a24a", 0.35, 0.9)           # vent bolt thread end (brass barb side)

# ------------------------------------------------------------------ wiring
def wire(key, pts, r, col, fillet=5.0, rough=0.5):
    add(key, tube(pts, r, fillet), col, rough, 0, smooth=True)
R14, R16, R20, RDU = 1.45, 1.2, 0.95, 0.65

# terminal entry points (board frame: screw clamps at x -25, z -9.4 B+, -3.1 B-, +3.1 M+, +9.4 M-)
TERM = {"B+": -9.4, "B-": -3.1, "M+": 3.1, "M-": 9.4}
def term(face, zc, n): return bpt(face, BX, zc, -25.0, PT + 4.5, TERM[n])
PORT_X = -42.0                    # port harness trough, outside rail 212
STBD_X = 42.0

# 1) +12 V / GND feeds: Wago -> port window of 215 -> trough -> rail window -> top board B+/B-; 16 AWG jumpers through the port slot to the board below
for i, zc in enumerate(BZ):
    for n, wp, col, dy in (("B+", WP[i + 1], W_RED, 1.5), ("B-", WG[i + 1], W_BLK, -1.5)):
        t = term("top", zc, n)
        wire(f"feed_{n}", [wp, wp + [-6, 0, 0], [-34, wp[1] * 0.5, ZR - 2], [PORT_X, 17 + dy, ZR - 14], [PORT_X, 17 + dy, zc + 26 + dy * 2],
                           [PORT_X + 5, 17 + dy, zc + 14 + TERM[n]], [t[0] - 6, t[1], t[2]], t], R14, col, 6)
        tb = term("bot", zc, n)
        sx = -26.5
        wire(f"jump_{n}", [t + [-0.5, 0.4, 0], [t[0] - 3, t[1] + 1, t[2]], [sx, 8, t[2] + (2.5 if n == "B+" else 3.5)], [sx, -8, tb[2] + (2.5 if n == "B+" else 3.5)],
                           [tb[0] - 3, tb[1] - 1, tb[2]], tb + [-0.5, -0.4, 0]], R16, col, 3)

# 2) battery: BATTERY gland (lower stbd) -> 12 AWG twin -> F1 (red) -> +12 V Wago top slot; black -> GND Wago top slot
bat = np.array(GL["BATTERY"][:2] + (ZC - 13,))
wire("bat_jacket", [bat, bat + [0, 0, -12]], 4.6, "#1b1c1f", rough=0.55)
c0 = bat + [0, 0, -12]
red = [c0 + [1.6, 0, 0], c0 + [1.6, 0, -6], [10, -30, 318], [-12, -36, 300]]
wire("bat_red", red + [[-30, -26, 290]], 1.8, W_RED)
add("f1", B(-38, -24, -28, -18, 279, 292), "#1d1e21", 0.5); add("f1", B(-35, -27, -18.2, -17.9, 281, 290), "#efc21b", 0.4)  # F1 holder + 30 A
wire("bat_red2", [[-31, -20, 280], [-33, -10, 268], [-30, 5, 262], [WP[0][0] - 8, WP[0][1], WP[0][2] + 6], WP[0]], 1.8, W_RED)
wire("bat_blk", [c0 + [-1.6, 0, 0], c0 + [-1.6, 0, -8], [6, -36, 312], [-14, -38, 290], [-28, -30, 268], [WG[0][0] - 8, WG[0][1], WG[0][2] + 6], WG[0]], 1.8, W_BLK)
# 3) aux: +12 V Wago -> F2 (3 A) -> LDD1, LDD2 +Vin and the buck; GND Wago -> LDD -Vin and buck GND
f2 = np.array([-8, -5, 262])
wire("aux_red", [WP[4], WP[4] + [-6, 0, 0], [-24, 0, 258], f2 + [-6, 0, 0]], R20, W_RED)
add("f2", B(f2[0] - 6, f2[0] + 6, f2[1] - 3, f2[1] + 3, f2[2] - 4, f2[2] + 4), "#1d1e21", 0.5)
add("f2", B(f2[0] - 3, f2[0] + 3, f2[1] + 2.9, f2[1] + 3.2, f2[2] - 2, f2[2] + 2), "#9c2bd6", 0.4)
wire("aux_red", [f2 + [6, 0, 0], [6, 0, 262], [L1["+Vin"][0], L1["+Vin"][1] + 4, ZR + 16], L1["+Vin"] + [0, 2, 0]], R20, W_RED)
wire("aux_red", [f2 + [6, 0, 0], [6, -1, 262], [L2["+Vin"][0], L2["+Vin"][1] - 4, ZR + 16], L2["+Vin"] + [0, -2, 0]], R20, W_RED)
wire("aux_blk", [WG[4], WG[4] + [-6, 0, 0], [-24, -6, 256], [2, -3, 256], [L1["-Vin"][0], L1["-Vin"][1] + 5, ZR + 18], L1["-Vin"] + [0, 2, 0]], R20, W_BLK)
wire("aux_blk", [[2, -3, 256], [L2["-Vin"][0], L2["-Vin"][1] - 5, ZR + 18], L2["-Vin"] + [0, -2, 0]], R20, W_BLK)
# converter feed: from F2 forward along the port trough, up through the top window to both mini bucks' IN ends; C1 in the trough
cinA = np.array([-21.0, DECK + 2.6, MB["U9A"][0]]); cinB = np.array([-21.0, DECK + 2.6, MB["U9B"][0]])
wire("aux_red", [f2 + [-6, 0, 0], [-30, -12, 250], [-34, -24, ZR - 14], [PORT_X + 2, -24, 120], [PORT_X + 1, 12, 80], [PORT_X + 1, 14, 30],
                 [-33, 12, 25], [-28.5, 8, 18], [-24, 6, 5], cinA + [0, 1, -3], cinA], R20, W_RED)
wire("aux_red", [[-28.5, 8, 18], [-28.5, 7.5, 30.5], cinB + [0, 1, -0.5], cinB], R20, W_RED)
wire("aux_blk", [WG[4] + [-6, 0, 0], [-31, -14, 252], [-35, -26, ZR - 14], [PORT_X + 3, -26, 120], [PORT_X + 3, 10, 80], [PORT_X + 3, 12, 30],
                 [-33, 10, 24], [-29.0, 6, 18], [-17, 6, 4], cinA + [5, 1, -3], cinA + [5, 0, 0]], R20, W_BLK)
wire("aux_blk", [[-29.0, 6, 18], [-29.0, 6, 29.5], [-16, 5, 30.5], cinB + [5, 0, 0]], R20, W_BLK)
add("c1", CY(5.0, 20, "z", (-44.5, 6, 40)), "#18233f", 0.4, 0, clear=0.3)
add("c1", B(-45.1, -43.9, 10.9, 11.05, 31, 49), "#c9ccd0", 0.5, 0)
wire("c1_w", [[-44.5, 8, 30], [-44, 11, 27], [PORT_X + 1, 14, 27]], 0.5, W_GRY, 2)

# 4) motors: 12-core from the MOTORS gland, broken out into 6 pairs, through 215's port window to M+/M- of each board
mo = np.array(GL["MOTORS"][:2] + (ZC - 13,))
wire("motor_cable", [mo, mo + [0, 0, -22], [-26, 22, 300], [-30, 24, 276]], 4.6, "#6d7277", rough=0.5)
add("motor_cable", CY(4.8, 6, "z", (-30, 24, 273)), "#111214", 0.6)                         # heat-shrink at the breakout
PAIRS = [("#d23c32", "#2b2b2b"), ("#e07a1c", "#5a3a20"), ("#e3c21b", "#2a62c4"), ("#3a9a45", "#8a8f94"), ("#f0f0ea", "#7b46b5"), ("#ef7fa8", "#40c0c0")]
for i, zc in enumerate(BZ):
    for face, j in (("top", i), ("bot", i + 3)):
        cp, cn = PAIRS[j]
        up = face == "top"
        for n, col, d in (("M+", cp, -0.8), ("M-", cn, 0.8)):
            t = term(face, zc, n)
            yy = (22 if up else -20) + d
            wire("motor_cores", [[-30 + d, 24, 270], [-36, (20 if up else -2) + d, ZR - 6], [PORT_X - 3, yy, ZR - 16], [PORT_X - 3, yy, zc + 30],
                                 [PORT_X + 4, yy * 0.8, zc + 16 + TERM[n]], [t[0] - 6, t[1], t[2]], t], 0.75, col, 6)

# 5) logic: Dupont bundles from each IBT_2 header (stbd edge) along the starboard trough to the Pico's starboard row
HDR = ["RPWM", "LPWM", "R_EN", "L_EN", "R_IS", "L_IS", "VCC", "GND"]
DCOL = {"RPWM": W_YEL, "LPWM": W_ORG, "R_EN": W_GRN, "L_EN": W_GRN, "VCC": W_RED, "GND": W_BLK}
PICO_PINS = {1: (2, 3), 2: (4, 5), 3: (6, 7), 4: (9, 10), 5: (11, 12), 6: (14, 15)}      # Pico pin numbers for RPWM, LPWM per thruster
def hdr_pin(face, zc, k):
    return bpt(face, BX, zc, 21.75, PT + 8.5, -8.89 + k * 2.54)
for i, zc in enumerate(BZ):
    for face, T in (("top", i + 1), ("bot", i + 4)):
        up = face == "top"
        for k, n in enumerate(HDR):
            if n in ("R_IS", "L_IS"): continue
            p = hdr_pin(face, zc, k)
            hz = p[2]
            add("dupont", B(p[0] - 1.27, p[0] + 1.27, p[1] - 0.2, p[1] + 14 if up else p[1] + 0.2, hz - 1.27, hz + 1.27) if up else
                B(p[0] - 1.27, p[0] + 1.27, p[1] - 14, p[1] + 0.2, hz - 1.27, hz + 1.27), BLK, 0.5)
            tip = p + [0, 14 if up else -14, 0]
            o = (k - 3.5) * 1.3
            if n == "RPWM": end = pico_pin(PICO_PINS[T][0])
            elif n == "LPWM": end = pico_pin(PICO_PINS[T][1])
            elif n in ("R_EN", "L_EN"): end = pico_pin(20)
            elif n == "VCC": end = pico_pin(36)
            else: end = pico_pin(3 if T in (1, 2) else 8 if T in (3, 4) else 13)
            yy = (20 if up else -18) + o * 0.4
            route = [tip, tip + [0, 3 if up else -3, 0], [33, yy + (4 if up else -4), hz + o * 0.3], [STBD_X, yy, hz - 6], [STBD_X, yy, 90 - T * 1.6]]
            if end[0] > 0: route += [[STBD_X - 2, -18 + o * 0.3, end[2] + 10], [36.5, end[1], end[2]], end]
            else: route += [[STBD_X - 4, -32, 80], [18, -36, 70], [-20, -36, end[2] + 12], [-36.5, end[1], end[2]], end]
            wire("dupont_w", route, RDU, DCOL[n], 4)
# 6) Pi <-> Pico UART + GND + 5 V: from the Pi header's aft pins down through the deck slot (z 71-73) to the Pico
def pi_pin(n):                       # Pi header pin n (odd = inner row x 10.23, even = outer row x 12.77); pin 1 at the aft end
    row = 12.77 if n % 2 == 0 else 10.23
    zz = 24.13 - ((n - 1) // 2) * 2.54
    return bpt("top", PI[0], PI[1], row, HAT_Y + PT + 3.0, zz)          # on the HAT's stacking pins, 3 mm above the HAT
for n, col, pn, o in ((2, W_RED, None, -1.5), (6, W_BLK, 3, -0.5), (8, W_WHT, 2, 0.5), (10, W_BLU, 1, 1.5)):
    p = pi_pin(n)
    add("solder_sleeve", CY(1.1, 5.0, "y", (p[0], p[1] + 1.5, p[2]), sections=10), "#2a2a2c", 0.5)       # soldered + heat-shrink
    tip = p + [0, 3.5, 0]
    if pn:
        e = pico_pin(pn)
        wire("dupont_w", [tip, tip + [-3, 1.5, 0], [22 + o, 30, 66], [20 + o, 22, 72], [18 + o, 2, 72], [18 + o, -6, 72], [33, -7 + o * 0.3, 68],
                          [38, -14, 40], [37.5, e[1], e[2] + 6], [36.5, e[1], e[2]], e], RDU, col, 4)
    else:                                                                                       # 5 V from the CPT output splice
        wire("dupont_w", [tip, tip + [-3, 1.5, 0], [22 + o, 30, 66], [20 + o, 22, 72], S5 + [5, 0, 0]], 0.75, W_RED, 4)
# U9A output (aft end): +5 V to the splice; GND out through the port top window and down the trough to Pico GND (38)
cout = np.array([-20.0, DECK + 2.6, MB["U9A"][1]])
wire("cpt_out", [cout, cout + [0, 3, 0.5], [-12, 8, 34], [-6, 9, 56], [0, 6, 70], S5], 0.75, W_RED, 4)
g38 = pico_pin(38)
wire("cpt_out", [cout + [5, 0, 0], cout + [5, 2.5, 0.5], [-26, 9, 34], [-33, 9, 40], [-38.5, -6, 40], [-38.5, -16, g38[2] + 8], [-36.5, g38[1], g38[2]], g38], 0.75, W_BLK, 4)
# U9B output (aft end): servo + and - (the servo leads end here, C2 across them)
SV5 = np.array([-20.0, DECK + 2.6, MB["U9B"][1]])
# splice -> down through the slot -> under the deck -> port lower window -> D1 -> VSYS (39)
vs = pico_pin(39)
wire("d1_w", [S5 + [5, 0, 0], [16, -6, 72], [-10, -7, 70], [-33, -8, 66], [-38.5, -12, 50], [-38.5, -14, 34], [-38, -17, vs[2] + 7], [-36.5, vs[1], vs[2]], vs], 0.7, W_RED, 3)
add("d1", CY(1.3, 4.8, "z", (-38.5, -13.5, 42)), "#121214", 0.4); add("d1", CY(1.35, 0.8, "z", (-38.5, -13.5, 40.2)), "#c9ccd0", 0.4)

# 7) DIM (GP14, pin 19) -> both LDD DIM inputs, starboard trough aft through 215's starboard window
d0 = pico_pin(19)
wire("dim_w", [d0, d0 + [7, 0, 0], [STBD_X + 2, -24, d0[2] + 10], [STBD_X + 2, -28, 70], [STBD_X + 2, -28, ZR - 18], [34, -6, ZR - 4],
               [L1["DIM"][0], L1["DIM"][1] + 6, ZR + 15], L1["DIM"] + [0, 2, 0]], RDU, W_PUR, 4)
wire("dim_w", [[34, -6, ZR - 4], [L2["DIM"][0], L2["DIM"][1] - 6, ZR + 15], L2["DIM"] + [0, -2, 0]], RDU, W_PUR, 4)

# 8) LIGHTS 4-core from the LIGHTS gland to the two LDD outputs (two separate pairs)
li = np.array(GL["LIGHTS"][:2] + (ZC - 13,))
wire("lights_cable", [li, li + [0, 0, -40], [16, 14, 290]], 2.9, "#1b1c1f")
for L, cp, cn, s in ((L1, W_WHT, W_BLU, 1), (L2, W_BRN, W_GRY, -1)):
    for n, col, o in (("+Vo", cp, -1), ("-Vo", cn, 1)):
        e = L[n]
        wire("lights_cores", [[16 + o * 0.9, 14 + s * 0.8, 290], [e[0] + 2, 6 + s * 8, 272], [e[0], e[1] + s * 8, ZR + 18], e + [0, s * 2, 0]], 0.7, col, 4)

# 9) tether: Cat6 from the TETHER gland, through 215's starboard window, over the boards to the USB-Ethernet RJ45 (aft face)
te = np.array(GL["TETHER"][:2] + (ZC - 13,))
jack = bpt("top", PI[0], PI[1], -16.5, HAT_Y + 5.4, 11.5)                       # RJ45 opening centre
add("cat6", B(jack[0] - 16, jack[0], jack[1] - 6.8, jack[1] + 6.8, jack[2] - 7.0, jack[2] + 7.0), "#e8eef2", 0.3, opacity=0.95)   # 90-degree plug
cp = np.array([-4.0, 36.0, 118.0])                                              # inline RJ45 coupler, over T1-T2
add("rj_coupler", B(cp[0] - 9, cp[0] + 9, cp[1] - 7.5, cp[1] + 7.5, cp[2] - 19, cp[2] + 19), "#d9dde1", 0.35)
wire("cat6", [te, te + [0, 0, -20], [10, -30, 300], [34, -14, 262], [STBD_X - 4, -8, ZR - 10], [STBD_X - 6, 4, 200], [24, 34, 170], [8, 38, 150],
               cp + [0, 0, 19]], 2.9, "#2f6fd1", 10)
wire("cat6", [cp + [0, 0, -19], [-6, 36, 90], [-10, 32, 68], [jack[0] - 9, jack[1], jack[2] + 7.0]], 2.4, "#2f6fd1", 8)

# 10) servos + camera: ribbon from the Pi's CSI forward through 207's top window; servo leads down through the slot to Pico 21/22
csi = bpt("top", PI[0], PI[1], 0, PT + 1.4, -32.6)
add("ribbon", tube([csi, csi + [0, 1, -4], [15.5, 22, -6], [12, 28, -20], [6, 26, -40], [2, 18, -58]], 0.1, 6, profile=(12, 0.3)), "#e9e4d6", 0.6)
for n, col in ((21, W_ORG), (22, W_YEL)):
    e = pico_pin(n)
    o = 0 if n == 21 else 2.2
    for c2, oo in ((col, 0), (W_RED, 0.8), (W_BRN, 1.6)):
        if c2 != col and n == 22: continue
        wire("servo_w", [[-6 + o + oo, 20, -40], [-4 + o + oo, 24, -8], [-2 + o + oo, 26, 40], [6 + o + oo, 6, 72], [6 + o + oo, -6, 72],
                         [-12, -8 - oo, 70], [-33, -9 - oo, 68], [-37.5, e[1], e[2] + 4], [-36.5, e[1], e[2]], e] if c2 == col else
                        [[-6 + o + oo, 20, -40], [-4 + o + oo, 24, -8], [-2 + o + oo, 26, 40], [-6 + oo, 12, 60], [-14 + oo, 7, 58], SV5 + [oo * 2.5, 1.0, 0.5], SV5 + [oo * 2.5, 0, 0]], 0.5, c2, 4)
add("c2", CY(3.2, 7, "y", (-6.0, DECK + 3.5, 60.0)), "#1c2a5a", 0.4)                              # 470 uF at the servo 5 V tap

# harness ties on the rails
for zz in (40, 140, 188):
    for xx, yy in ((PORT_X - 2, 20), (PORT_X, -24), (STBD_X, 18), (STBD_X, -22)):
        add("harness_tie", tube([(xx - 4, yy - 5, zz), (xx + 4, yy - 5, zz), (xx + 4, yy + 5, zz), (xx - 4, yy + 5, zz), (xx - 4, yy - 5, zz)], 0.5, 1.5, profile=(2.5, 1.0)), "#0b0b0c", 0.5)

# ------------------------------------------------------------------ write
out = {"meshes": {}}
for k, (ms, pr) in MESH.items():
    m = trimesh.util.concatenate(ms)
    out["meshes"][k] = {"v": base64.b64encode(np.asarray(m.vertices, np.float32).tobytes()).decode(),
                        "i": base64.b64encode(np.asarray(m.faces, np.uint32).tobytes()).decode(), **pr}
json.dump(out, open(f"{OUT}/elec_scene.json", "w"))
print("meshes", len(out["meshes"]), "triangles", sum(len(trimesh.util.concatenate(v[0]).faces) for v in MESH.values()))
