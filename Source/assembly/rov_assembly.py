"""
Full ROV assembly, v4: 16" electronics hull, 3" battery pod underneath, three 3-part frame clamps,
6 thrusters (4 vectored horizontals at the corners + 2 verticals at the centre of gravity),
compact bullet lights on the two upper float rails.
Places every part with a 4x4 matrix, runs interference checks, writes rov_viewer/assembly.json.
"""
import sys, json, base64, itertools
import numpy as np, trimesh
from manifold3d import Manifold, Mesh
import frame_clamp as FC, lights as LT, pvc as PV, thruster as T, ring as RG, pylon as PY, bracket as B, rov_parts as RP

T.THREAD_N, T.THREAD_DIV = 48, 24

def Tm(x, y, z): m = np.eye(4); m[:3, 3] = (x, y, z); return m
def Rx(d):
    a = np.radians(d); c, s = np.cos(a), np.sin(a); m = np.eye(4); m[1:3, 1:3] = [[c, -s], [s, c]]; return m
def Ry(d):
    a = np.radians(d); c, s = np.cos(a), np.sin(a); m = np.eye(4); m[0, 0], m[0, 2], m[2, 0], m[2, 2] = c, s, -s, c; return m
def Rz(d):
    a = np.radians(d); c, s = np.cos(a), np.sin(a); m = np.eye(4); m[:2, :2] = [[c, -s], [s, c]]; return m
def Sx(): m = np.eye(4); m[0, 0] = -1; return m

# ---------------- layout ----------------
HULL_L = 406.4                          # 16" hull, electronics only
P0, P1 = -HULL_L/2, HULL_L/2
RING_T, SKIRT = 10.0, 49.0
REAR_FACE, FRONT_FACE = P0 - RING_T, P1 + RING_T
SLED_DISC = (-89.0, 145.0)              # tray bulkhead discs, inner faces (234 apart, as built)
MID_Z = -8.0                            # mid clamp + vertical thrusters, on the centre of gravity
CORNER_Z = 95.0                         # front / rear clamps carry the vectored horizontals
FRAME = {"rear": -CORNER_Z, "mid": MID_Z, "front": CORNER_Z}
POD_Y = FC.POD4_Y
POD_L = 300.0                           # 3" Sch40 battery pod pipe
POD_Z0 = -CORNER_Z - FC.W/2 - 1.0 - 25.0   # rear flange socket stops just behind the rear clamp
POD_Z1 = POD_Z0 + POD_L
BR_Z0 = -200.0                          # junction bridge across the upper rails, z -200 .. -130 (behind the rear clamp)
TRAY_ZS = (MID_Z + (CORNER_Z - MID_Z)/2, MID_Z - (CORNER_Z + MID_Z)/2)  # two lead trays, between the clamps
TRAY_L = 50.0
RAIL_Z0, RAIL_Z1 = -250.0, 232.0
SKID_Z0, SKID_Z1 = -235.0, 235.0

import os
_E = lambda k, d: float(os.environ.get(k, d))
FC.CORNER_FACE, FC.CORNER_Y = _E("CF", FC.CORNER_FACE), _E("CY", FC.CORNER_Y)
FC.VERT_FACE, FC.VERT_Y = _E("VF", FC.VERT_FACE), _E("VY", FC.VERT_Y)
FC.CORNER_YAW = _E("CYAW", FC.CORNER_YAW)
PROPS_OUT = os.environ.get("POUT", "1") == "1"

def pipe(od, idd, length): return Manifold.cylinder(length, od/2, od/2, 128) - Manifold.cylinder(length + 2, idd/2, idd/2, 128).translate((0, 0, -1))
def stl(path):
    t = trimesh.load(path)
    return Manifold(Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
UP = "rov_project/"
# UQISOVI 4" acrylic CCTV dome (Amazon B0DR2HP4YQ): 99.8 OD / 96 ID hemisphere, 5.1 mm straight skirt, 2 mm flange 115 OD,
# 57 mm overall. Local z = 0 is the flange underside (sits on 203's face, over the O-ring). The flange is modelled 1.9 mm
# thick, as clamped in 204's 1.9 mm recess, so the sphere centre lands at z 0 + 1.9 + 5.2 = 7.1 (hull z 220.3).
_DZ = 7.1
_hemi = Manifold.sphere(99.8/2, 128) ^ Manifold.cube((200, 200, 100)).translate((-100, -100, 0))
_hemi = _hemi - (Manifold.sphere(96.0/2, 128) ^ Manifold.cube((200, 200, 100)).translate((-100, -100, 0)))
dome = _hemi.translate((0, 0, _DZ))
dome = dome + (Manifold.cylinder(_DZ - 1.9, 99.8/2, 99.8/2, 128) - Manifold.cylinder(_DZ, 96.0/2, 96.0/2, 128).translate((0, 0, -1))).translate((0, 0, 1.9))
dome = dome + (Manifold.cylinder(1.9, 115.0/2, 115.0/2, 128) - Manifold.cylinder(4, 96.0/2, 96.0/2, 128).translate((0, 0, -1)))
cell = Manifold.cylinder(RP.CELL_L, RP.CELL_D/2, RP.CELL_D/2, 32)

def lead_tray_short():
    FC.TRAY_L = TRAY_L
    t = FC.lead_tray(FC.SKID4)
    FC.TRAY_L = 100.0
    return t

parts = {  # key: (manifold in its own frame, color, label)
    "hull": (pipe(114.3, 102.26, HULL_L), 0xe9ecef, "4\" Sch40 PVC hull (16\")"),
    "fl_rear": (stl(UP + "br_flange_rear.stl"), 0x7d8790, "Rear flange (ROV Project)"),
    "cap_rear": (FC.endcap_rear_5hole(), 0x4f5962, "Rear end cap, 4 glands + vent"),
    "fl_front": (stl(UP + "br_flange_front_dome.stl"), 0x7d8790, "Front dome flange (ROV Project)"),
    "dome_ring": (stl(UP + "dome_retaining_ring.stl"), 0x4f5962, "Dome retaining ring (ROV Project)"),
    "dome": (dome, 0xbfe0f5, "Acrylic dome, UQISOVI 4 in (100 mm, 115 mm flange)"),
    "tray": (stl(UP + "ETRAY4-ROV-TRAY-R2.stl"), 0x3f8f6b, "Electronics tray ETRAY4 R2 (ROV Project)"),
    "bh_rear": (RP.sled_bulkhead(False), 0x23272b, "Sled rear bulkhead"),
    "bh_front": (RP.sled_bulkhead(True), 0x23272b, "Sled front bulkhead + camera mount holes"),
    "rod": (Manifold.cylinder(1.0, 1.5, 1.5, 16), 0xb0b6bb, "M3 threaded rod"),
    "cam_mount": (RP.camera_mount(), 0x8bd0ae, "Camera stalk on front bulkhead"),
    "picam": (RP.picam3(), 0x1f7a3a, "Pi Camera Module 3"),
    # battery pod
    "pod": (pipe(PV.P3_OD, RP.BAT_ID, POD_L), 0xe9ecef, "3\" Sch40 PVC battery pod"),
    "pod_fl": (RP.battery_flange(), 0x7d8790, "Battery pod rear flange, 3\" BR-style (new)"),
    "pod_cap": (RP.battery_endcap(), 0x4f5962, "Battery pod rear cap, M12 gland + vent (new)"),
    "cap3": (PV.cap3(), 0xf4f4f4, "3\" Sch40 PVC slip cap (pod front)"),
    "cell_plate": (RP.battery_cell_plate(), 0x2f6fd6, "Cell holder plate, 8 x 18650 (new)"),
    "cell": (cell, 0x6fa86a, "18650 cell"),
    # thrusters + frame
    "housing": (T.housing(foot=False), 0x3d4349, "Thruster housing"),
    "tail": (T.tail_cone(comp=True), 0x2c3136, "Tail cone (compensator)"),
    "hub": (T.prop_hub(1), 0xd9a514, "Prop hub"),
    "nose": (T.nose_cone(), 0xe8c24a, "Nose cone"),
    "pylon": (PY.pylon(), 0x5b8fb0, "Pylon clamp"),
    "pvc34": (pipe(RP.PIPE_34, 20.9, 1.0), 0xf2f2f2, "3/4\" Sch40 PVC pipe"),
    "cap34": (PV.cap34(), 0xf8f8f8, "3/4\" PVC slip cap"),
    "fc_top": (FC.top_cap(), 0xe0a040, "Frame clamp top cap, upper rail bosses"),
    "fc_mid": (FC.body4(0.0), 0x6b8fb5, "Frame clamp body, mid (square pads, vertical thrusters)"),
    "fc_corner": (FC.body4(FC.CORNER_YAW), 0x6b8fb5, "Frame clamp body, corner (45 deg pads, front + rear)"),
    "fc_pod": (FC.pod_bottom4(), 0xe0a040, "Frame clamp pod cap, skid legs"),
    "lead_tray": (lead_tray_short(), 0x4a4f55, "Lead ballast tray, 50 mm"),
    "jbox6": (FC.junction_box(6), 0x2b3036, "Junction box, 6 motor leads (potted)"),
    "jbox2": (FC.junction_box(2), 0x2b3036, "Junction box, 2 light leads (potted)"),
    "jbridge": (FC.junction_bridge(), 0xe0a040, "Junction bridge, clamps across the upper rails"),
}
parts.update({k: (f(), c, l) for k, f, c, l in [
    ("lt_rear", LT.rear_body, 0x2b3036, "Light rear body (printed)"),
    ("lt_disc", LT.disc, 0xaab2ba, "Light heat-sink disc, 42 x 5 aluminium"),
    ("lt_spacer", LT.spacer, 0x2b3036, "Light window spacer (printed)"),
    ("lt_window", LT.window, 0xdff2ff, "Light window, 28 x 3 polycarbonate"),
    ("lt_front", LT.front_ring, 0x2b3036, "Light front ring (printed)"),
    ("lt_led", LT.led, 0xffd84a, "LED, 20 mm star 5 W")]})

inst = []   # (key, M, group, explode)
def add(key, M, group, ex=(0, 0, 0)): inst.append((key, M, group, ex))

# ---- main hull
add("hull", Tm(0, 0, P0), "hull")
add("fl_rear", Tm(0, 0, REAR_FACE), "hull", (0, 0, -50))
add("cap_rear", Tm(0, 0, REAR_FACE - 10), "hull", (0, 0, -110))
add("fl_front", Tm(0, 0, FRONT_FACE) @ Rx(180), "hull", (0, 0, 50))
add("dome_ring", Tm(0, 0, FRONT_FACE), "hull", (0, 0, 110))
add("dome", Tm(0, 0, FRONT_FACE), "hull", (0, 0, 110))
z_rs, z_fs = -170.0, 170.0      # (2026-10-23) 340 mm rods, centred, as in the guide: the tips sit ~6 mm in the flanges' 4 mm holes
EXS = (0, 0, -200)
add("bh_rear", Tm(0, 0, SLED_DISC[0] - RP.BH_T), "sled", EXS)
add("bh_front", Tm(0, 0, SLED_DISC[1] + RP.BH_T) @ Rx(180), "sled", EXS)
for a in (45, 135, 225, 315):
    x, y = 47*np.cos(np.radians(a)), 47*np.sin(np.radians(a))
    add("rod", Tm(x, y, z_rs) @ np.diag([1, 1, z_fs - z_rs, 1]), "sled", EXS)
tz = (SLED_DISC[0] + SLED_DISC[1])/2 - 221.76/2
add("tray", np.array([[0, 1, 0, -50], [0, 0, 1, -2.5], [1, 0, 0, tz], [0, 0, 0, 1]], float), "sled", EXS)
cam_face = SLED_DISC[1] + 5
RP.CAM_STALK = FRONT_FACE + 2.0 - 11.5 - 2 - cam_face
parts["cam_mount"] = (RP.camera_mount(), parts["cam_mount"][1], parts["cam_mount"][2])
add("cam_mount", Tm(0, 0, cam_face), "sled", EXS)
add("picam", Tm(0, 0, cam_face + RP.CAM_STALK + 2), "sled", EXS)

# ---- battery pod: 3" pipe, BR-style flange + 2-hole cap at the rear, PVC slip cap at the front
EXB = (0, -60, 0)
add("pod", Tm(0, POD_Y, POD_Z0), "battery", EXB)
add("pod_fl", Tm(0, POD_Y, POD_Z0 - 1.5) @ Ry(180), "battery", (0, -60, -40))
add("pod_cap", Tm(0, POD_Y, POD_Z0 - 1.5) @ Ry(180), "battery", (0, -60, -90))
add("cap3", Tm(0, POD_Y, POD_Z1 - PV.CAP3_SOCK), "battery", (0, -60, 60))
# 3S8P pack: three parallel groups of 8 cells, a holder plate at each end of each group, slides in from the rear
GROUP_L = RP.CELL_L + 2*(7.0 - 5.5)
z = POD_Z0 + 6.0
CELL_Z = []
for g in range(3):
    add("cell_plate", Tm(0, POD_Y, z), "battery", (0, -60, -150))
    for (cx, cy) in RP.CELL_POS:
        add("cell", Tm(cx, POD_Y + cy, z + 1.5), "battery", (0, -60, -150))
    add("cell_plate", Tm(0, POD_Y, z + 1.5 + RP.CELL_L + 1.5) @ Ry(180), "battery", (0, -60, -150))
    CELL_Z.append(z); z += GROUP_L + 3.0
PACK_END = z

# ---- thrusters
def thr_matrix(mode, side, rz):
    M = Tm(0, 0, -B.BZC)
    M = Rz(-90) @ M
    if mode == "v": M = Rx(-90) @ M
    if mode == "hr": M = Rx(180) @ M
    M = Tm(RG.PAD_FACE + B.RF, 0, 0) @ M
    if side < 0: M = Sx() @ M
    return Tm(0, 0, rz) @ M

def corner_matrix(front, side):
    """vectored horizontal: pad face turned 45 deg (front: normal forward-outboard, rear: aft-outboard).
    Props face outboard, tail cones (and leads) point in toward the hull."""
    yaw = FC.CORNER_YAW if front else -FC.CORNER_YAW
    zc = CORNER_Z if front else -CORNER_Z
    mode = ("hr" if front else "h") if PROPS_OUT else ("h" if front else "hr")
    M = Tm(FC.CORNER_FACE, FC.CORNER_Y, zc) @ Ry(yaw) @ Tm(-RG.PAD_FACE, 0, 0) @ thr_matrix(mode, 1, 0)
    return Sx() @ M if side < 0 else M

THR = []
for front in (True, False):
    for side in (1, -1):
        THR.append(("H", corner_matrix(front, side), side))
for side in (1, -1):
    THR.append(("V", Tm(side*(FC.VERT_FACE - RG.PAD_FACE), FC.VERT_Y, 0) @ thr_matrix("v", side, MID_Z), side))
for kind, M, side in THR:
    out = np.array([side*70.0, 0, 0])
    for k in ("housing", "tail", "hub", "nose"): add(k, M, "thrusters", tuple(out))
    add("pylon", M, "frame", tuple(out*0.5))

# ---- frame clamps (rear clamp = the corner body turned 180 deg about y)
for name, zc in FRAME.items():
    P = Tm(0, 0, zc) @ (Ry(180) if name == "rear" else np.eye(4)) @ Tm(0, 0, -FC.W/2)
    add("fc_top", P, "frame", (0, 45, 0))
    add("fc_mid" if name == "mid" else "fc_corner", P, "frame", (0, -20, 0))
    add("fc_pod", P, "frame", (0, -90, 0))

def pipe_seg(p0, p1, group, ex):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    add("pvc34", PV.align_z(p1 - p0, p0) @ np.diag([1, 1, np.linalg.norm(p1 - p0), 1]), group, ex)

def straight_rail(x, y, z0, z1, group, ex, light=False):
    add("cap34", Tm(x, y, z0) @ Rx(180) @ Tm(0, 0, -PV.F34_SOCK), group, ex)
    if light:
        H = Tm(x, y, z1 - LT.SOCK) @ Rz(-np.sign(x)*40.0)       # cable exit turned up and outboard
        for k in LT.POD_PARTS: add(k, H, "lights", (0, 0, 60))
        LIGHT_H.append(H)
    else:
        add("cap34", Tm(x, y, z1) @ Tm(0, 0, -PV.F34_SOCK), group, ex)
    pipe_seg((x, y, z0), (x, y, z1), group, ex)

LIGHT_H = []
for s in (1, -1):
    straight_rail(s*FC.UPPER[0], FC.UPPER[1], RAIL_Z0, RAIL_Z1, "pipes", (s*40, 50, 0), light=True)
    straight_rail(s*FC.SKID4[0], FC.SKID4[1], SKID_Z0, SKID_Z1, "pipes", (0, -110, 0))
for tzc in TRAY_ZS:
    add("lead_tray", Tm(0, 0, tzc - TRAY_L/2), "frame", (0, -140, 0))

add("jbridge", Tm(0, 0, BR_Z0), "frame", (0, 60, 0))
JBOX = {}
for name, x in FC.JBOX_X.items():
    M = np.eye(4); M[:3, 0], M[:3, 1], M[:3, 2] = (0, 0, -1), (-1, 0, 0), (0, 1, 0)
    M[:3, 3] = (x, FC.BR_Y + FC.BR_T, BR_Z0 + FC.BR_D/2)
    JBOX[name] = (M, FC.JBOX_N[name])
    add("jbox6" if FC.JBOX_N[name] == 6 else "jbox2", M, "frame", (0, 90, 0))

import wiring as WR                                # mockup cables + electronics (not interference-checked)
for _k, (_m, _c, _l, _g) in WR.build(sys.modules[__name__]).items():
    parts[_k] = (_m, _c, _l); add(_k, np.eye(4), _g)
MOCKUP = ("wiring", "electronics")

def world(key, M):
    return parts[key][0].transform(M[:3, :])

if __name__ == "__main__":
    W = [(k, g, world(k, M)) for k, M, g, _ in inst if g not in MOCKUP]
    if os.environ.get("QUICK"):
        TK = ("housing", "tail", "hub", "nose", "pylon")
        bad = []
        for (k1, g1, m1), (k2, g2, m2) in itertools.combinations(W, 2):
            if not (k1 in TK or k2 in TK): continue
            b1, b2 = np.array(m1.bounding_box()), np.array(m2.bounding_box())
            if np.any(b1[3:] < b2[:3]) or np.any(b2[3:] < b1[:3]): continue
            v = (m1 ^ m2).volume()
            if v > 0.5: bad.append((k1, k2, round(v, 1)))
        allb = np.array([m.bounding_box() for _, g, m in W])
        print("width", round(allb[:, 3].max()*2), "bad", bad[:6], len(bad)); sys.exit()
    bad = []
    for (k1, g1, m1), (k2, g2, m2) in itertools.combinations(W, 2):
        b1, b2 = np.array(m1.bounding_box()), np.array(m2.bounding_box())
        if np.any(b1[3:] < b2[:3]) or np.any(b2[3:] < b1[:3]): continue
        v = (m1 ^ m2).volume()
        if v > 0.5: bad.append((k1, k2, round(v, 1)))
    print("interferences:", bad if bad else "none")
    allb = np.array([m.bounding_box() for _, g, m in W])
    print("envelope (x, y, z) mm:", np.round(allb[:, 3:].max(0) - allb[:, :3].min(0), 0), "pack end z", round(PACK_END, 1), "pod inner end", POD_Z1)
    meshes = {}
    for k, (m, col, label) in parts.items():
        g = m.to_mesh()
        v = np.asarray(g.vert_properties[:, :3], np.float32); f = np.asarray(g.tri_verts, np.uint32)
        meshes[k] = {"v": base64.b64encode(v.tobytes()).decode(), "i": base64.b64encode(f.tobytes()).decode(),
                     "color": col, "label": label}
    data = {"meshes": meshes,
            "instances": [{"k": k, "m": M.T.flatten().round(5).tolist(), "g": g, "ex": list(ex)} for k, M, g, ex in inst]}
    import os; os.makedirs("rov_viewer", exist_ok=True)
    json.dump(data, open("rov_viewer/assembly.json", "w"))
    print("instances:", len(inst), " json MB:", round(os.path.getsize("rov_viewer/assembly.json")/1e6, 2))
