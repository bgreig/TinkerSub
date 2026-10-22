"""
MOCKUP ONLY (v4: electronics hull + 3" battery pod, 6 thrusters, 2 lights): cable runs and electronics boxes for
the render. Not interference-checked, not for printing. Built in world coordinates from the placed assembly.

Rear hull cap: MOTORS M16 (6-lead pot multicore), LIGHTS M12 (2-lead pot), BATTERY M16 (from the pod), TETHER M12, vent.
"""
import numpy as np
from manifold3d import Manifold
import lights as LT, frame_clamp as FC

def _seg(p0, p1, r, n=16):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    v = p1 - p0; L = np.linalg.norm(v)
    if L < 1e-6: return Manifold()
    z = v / L; a = np.array([0, 0, 1.0]) if abs(z[2]) < 0.9 else np.array([1.0, 0, 0])
    x = np.cross(a, z); x /= np.linalg.norm(x); y = np.cross(z, x)
    return Manifold.cylinder(L, r, r, n).transform(np.column_stack([x, y, z, p0]))

def cable(pts, r):
    pts = [np.asarray(p, float) for p in pts]
    m = Manifold()
    for a, b in zip(pts[:-1], pts[1:]): m = m + _seg(a, b, r)
    for p in pts[1:-1]: m = m + Manifold.sphere(r, 16).translate(tuple(p))
    return m

def box(c, size):
    (cx, cy, cz), (sx, sy, sz) = c, size
    return Manifold.cube((sx, sy, sz)).translate((cx - sx/2, cy - sy/2, cz - sz/2))

def P(r, deg, z):
    a = np.radians(deg); return np.array([r*np.cos(a), r*np.sin(a), z])

def arc(r, a0, a1, z, n=8):
    return [P(r, a0 + (a1 - a0)*i/n, z) for i in range(n + 1)]

def build(A):
    out = {}
    zc = A.REAR_FACE - 10.0
    hole = {n: (FC.GLAND_R*np.cos(np.radians(a)), FC.GLAND_R*np.sin(np.radians(a))) for n, (m, a, t) in FC.GLANDS.items()}
    size = {n: m for n, (m, a, t) in FC.GLANDS.items()}
    glands = Manifold.cylinder(8, 7, 7, 6).translate((0, 0, zc - 8))
    for n, (x, y) in hole.items():
        rb = 11.0 if size[n] == 16 else 8.5
        glands = glands + Manifold.cylinder(8, rb, rb, 6).translate((x, y, zc - 8)) \
                        + Manifold.cylinder(8, rb - 2, rb - 2, 24).translate((x, y, zc - 16))
    out["w_glands"] = (glands, 0x15181b, "Cable glands + vent (mockup)", "wiring")
    gtip = {n: np.array([x, y, zc - 16]) for n, (x, y) in hole.items()}

    def _pt(name, p):
        M, n = A.JBOX[name]; return (M @ np.array([*p, 1.0]))[:3]
    def pot_entry(name, i):
        n = A.JBOX[name][1]
        return _pt(name, (-FC.JX_L/2, (i - (n - 1)/2)*FC.JB_PITCH, FC.JX_ENTRY_Z))
    def pot_exit(name): return _pt(name, (FC.JX_L/2, 0, FC.JX_ENTRY_Z))

    # --- thruster leads: tail gland -> up the hull side -> along the top -> MOTORS pot
    mot = Manifold(); k = 0
    tails = [(M, s) for key, M, g, _ in A.inst if key == "tail" for s in [np.sign(M[0, 3]) or 1]]
    order = sorted(range(len(tails)), key=lambda i: (-tails[i][1], -(tails[i][0] @ [0, 0, -23.0, 1])[2]))
    slots = {}
    rs = [i for i in order if tails[i][1] > 0]; ls = [i for i in order if tails[i][1] < 0]
    for j, i in enumerate(rs): slots[i] = j                       # right side -> right half of the pot
    for j, i in enumerate(ls): slots[i] = 5 - j
    for i, (M, sx) in enumerate(tails):
        tip = (M @ np.array([0, 0, -23.0, 1]))[:3]; d = -M[:3, 2]
        j = slots[i]; e = pot_entry("MOTORS", j)
        ang = np.degrees(np.arccos(np.clip(e[0]/74.0, -1, 1)))
        p1 = tip + d*12
        side = np.array([sx*72.0, -20.0, p1[2]])
        pts = [tip, p1, side, np.array([sx*74.0, 12.0, p1[2]])]
        a0 = np.degrees(np.arctan2(12.0, sx*74.0))
        pts += arc(74.0, a0, ang, p1[2], 8)[1:]
        pts += [P(74.0, ang, e[2] + 28), np.array([e[0], e[1] - 8, e[2] + 22]), e + [0, 0, 10], e]
        mot = mot + cable(pts, 2.6)
    out["w_motor"] = (mot, 0x2a2d31, "Thruster leads (mockup)", "wiring")

    # --- light leads: out the side of each head, back along the rail, over to the LIGHTS pot
    lc = Manifold()
    for j, H in enumerate(sorted(A.LIGHT_H, key=lambda H: H[0, 3])):
        ex = (H @ np.array([*LT.CABLE_EXIT, 1.0]))[:3]
        u = H[:3, 1]
        rail = np.array([H[0, 3], H[1, 3], 0.0])
        run = rail + u*16.0
        e = pot_entry("LIGHTS", j)
        pts = [ex - u*4, ex + u*2, np.array([run[0], run[1], ex[2] - 30]), np.array([run[0], run[1], e[2] + 40]),
               np.array([e[0]*1.2, e[1] + 10, e[2] + 25]), e + [0, 0, 10], e]
        lc = lc + cable(pts, 2.2)
    out["w_light"] = (lc, 0x1b1d20, "Light leads (mockup)", "wiring")

    # --- multicores: pot -> over the flange -> rear cap gland
    mc = Manifold()
    for name, rr in (("MOTORS", 4.5), ("LIGHTS", 3.0)):
        g = gtip[name]; e = pot_exit(name)
        mc = mc + cable([e, e + [0, 0, -14], np.array([g[0]*1.4, 75.0, zc - 26]), np.array([g[0], g[1], zc - 34]), g], rr)
    out["w_multicore"] = (mc, 0x202327, "Multicore cables to the hull (mockup)", "wiring")

    # --- battery: pod rear-cap gland -> hull rear cap BATTERY gland
    pz = A.POD_Z0 - 1.5 - 14.0 - 8.0                                  # pod cap outer face
    bg = np.array([0.0, A.POD_Y + 12.0, pz])
    bat = Manifold.cylinder(10, 8.5, 8.5, 6).translate((bg[0], bg[1], pz - 10))
    gb = gtip["BATTERY"]
    bat = bat + cable([bg - [0, 0, 10], bg - [0, 0, 26], np.array([gb[0]*0.6, -80.0, pz - 40]),
                       np.array([gb[0], -60.0, zc - 40]), np.array([gb[0], gb[1], zc - 30]), gb], 4.0)
    out["w_battery"] = (bat, 0x9c1f24, "Battery cable (mockup)", "wiring")

    t0 = gtip["TETHER"]
    out["w_tether"] = (cable([t0, t0 - [0, 0, 50], np.array([30, 40, zc - 150]), np.array([30, 120, zc - 360])], 3.5),
                       0xe6b800, "Tether, Cat6 (mockup)", "wiring")

    # --- electronics on the tray (mockup)
    E = box((5, 9.5, 102), (30, 5, 65)) + box((-30, 8.5, 95), (21, 4, 51)) + box((-34, 12, 28), (22, 12, 40))
    D = box((0, 16, -48), (45, 18, 45)) + box((0, 16, 2), (45, 18, 45)) + box((0, -14, 15), (45, 14, 45))
    Bx = box((34, 13, -48), (23, 14, 46)) + box((34, 11, 10), (22, 10, 40)) + box((0, -12, -40), (60, 15, 22))
    W = Manifold()
    zi = A.REAR_FACE + 2
    for n, tgt, r in [("MOTORS", (0, 20, -70), 3.5), ("LIGHTS", (32, 12, -12), 2.6), ("TETHER", (-34, 12, 6), 2.5), ("BATTERY", (0, -10, -52), 3.5)]:
        x, y = hole[n]
        W = W + cable([np.array([x, y, zi]), np.array([x*0.6, y*0.6, A.SLED_DISC[0] - 30]),
                       np.array([x*0.4 + tgt[0]*0.3, (y*0.4 + 25) if tgt[1] > 0 else -30, A.SLED_DISC[0] - 2.5]),
                       np.array(tgt, float)], r)
    W = W + cable([np.array([0, 14, -2]), np.array([20, 18, 40]), np.array([10, 13, 72])], 2.0)
    W = W + cable([np.array([30, 12, 30]), np.array([10, 14, 70])], 1.5)
    cam_z = A.SLED_DISC[1] + 5
    W = W + box((0, 3.5, (cam_z + 134) / 2), (16, 0.6, cam_z - 134))
    # BMS + pack leads in the pod
    pk = box((0, A.POD_Y, A.PACK_END + 6), (56, 10, 8)) + cable([np.array([0, A.POD_Y + 30, A.PACK_END + 2]),
            np.array([0, A.POD_Y + 30, A.POD_Z0 + 2]), np.array([0, A.POD_Y + 12, A.POD_Z0 - 6])], 3.0)
    out["e_logic"] = (E, 0x1d6b3a, "Pi Zero 2W, Pico, USB-Ethernet (mockup)", "electronics")
    out["e_drivers"] = (D, 0xb3262d, "Motor drivers x3, dual channel (mockup)", "electronics")
    out["e_power"] = (Bx, 0x2b55a8, "Buck converter, MOSFET board, fuse block (mockup)", "electronics")
    out["e_harness"] = (W, 0x3a3d42, "Internal wiring + camera ribbon (mockup)", "electronics")
    out["e_bms"] = (pk, 0x2b55a8, "3S BMS + pack leads (mockup)", "electronics")
    return out
