"""
v6 = v5 with two changes:
  1. Battery pod front: printed 3" flange + blank bolt-on end cap (no holes) instead of the PVC slip cap.
     Both pod ends are now the same flange; the pack can come out either end.
  2. Side plates: one piece each, cut from a single 24 x 24 in sheet of 1/2" black HDPE (no printed plate pieces,
     no splice strips, no seam bolts).
Builds on rov_v5 (same stations, brackets, cowl, belly pan, thrusters). Writes rov_viewer/assembly_v6.json.
"""
import sys, json, base64, itertools
import numpy as np
from manifold3d import Manifold
import rov_v5 as V, rov_parts as RP, rov_assembly as A

Tm, Ry = V.Tm, V.Ry

def pod_endcap_blank():
    """3" pod front cap: same plug, O-rings and 6x M5 bolt circle as the rear cap, 10 mm plate, no holes."""
    return RP.endcap(RP.BAT_OD, RP.BAT_ID, seal_l=14.0, fl_od=RP.BAT_OD + 24, plate_t=10.0, oring_cs=2.5)

def plate_onepiece(sgn):
    cs = V._solid
    for z, y, r, k in V.HOLES:
        if k not in ("lap", "splice"): cs = cs - V.circ(z, y, r)
    p = V.side_extrude(cs, V.XP, V.XP + V.T_PL)
    return p if sgn > 0 else p.mirror((1, 0, 0))

parts = {k: v for k, v in V.parts.items() if not k.startswith(("plate_", "splice_")) and k != "cap3"}
STATUS = {k: v for k, v in V.STATUS.items() if k in parts}
HDPE = 0x2a2e33
parts["hdpe_port"] = (plate_onepiece(1), HDPE, "Side plate, port: 1/2\" black HDPE, cut from the 24 x 24 in sheet")
parts["hdpe_stbd"] = (plate_onepiece(-1), HDPE, "Side plate, starboard: 1/2\" black HDPE, cut from the 24 x 24 in sheet")
STATUS["hdpe_port"] = STATUS["hdpe_stbd"] = "bought"
parts["pod_fl_front"] = (RP.battery_flange(), V.NEW, "Battery pod front flange, 3\" (NEW, same part as the rear)")
parts["pod_cap_front"] = (pod_endcap_blank(), V.NEW, "Battery pod front end cap, blank (NEW)")
STATUS["pod_fl_front"] = STATUS["pod_cap_front"] = "new"

inst = []
for k, M, g, ex in V.inst:
    if k.startswith(("plate_", "splice_")) or k == "cap3": continue
    inst.append((k, M, g, ex))
inst.append(("hdpe_port", np.eye(4), "frame", (110, 0, 0)))
inst.append(("hdpe_stbd", np.eye(4), "frame", (-110, 0, 0)))
FRONT = A.POD_Z1 + 1.5                                   # pipe end sits on the flange's stop ledge
inst.append(("pod_fl_front", Tm(0, A.POD_Y, FRONT), "battery", (0, -60, 40)))
inst.append(("pod_cap_front", Tm(0, A.POD_Y, FRONT), "battery", (0, -60, 90)))

# ---- electronics-chat sled (212-215), redesigned camera pan-tilt (216-219), cell plate v2 (305)
import trimesh as _tm
from manifold3d import Mesh as _Mesh
def _mf(path):
    t = _tm.load(path)
    return Manifold(_Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
import os
_NP = "/mnt/user-data/uploads/ROV/New_parts/"
SLED_M = np.array([[-1, 0, 0, 0], [0, 1, 0, 0], [0, 0, -1, 145.0], [0, 0, 0, 1]], float)   # sled frame (X stbd, Z aft) -> hull
for k in ("tray", "bh_rear", "cam_mount", "picam"): parts.pop(k, None); STATUS.pop(k, None)
inst = [i for i in inst if i[0] not in ("tray", "bh_rear", "cam_mount", "picam")]
for k, f, lbl in (("sl_rail_p", "212_sled_rail_port", "212 Sled side rail, port"), ("sl_rail_s", "213_sled_rail_stbd", "213 Sled side rail, starboard"),
                  ("sl_deck", "214_sled_deck", "214 Sled deck"), ("sl_bh", "215_sled_bulkhead_rear_v2", "215 Sled rear bulkhead")):
    _src = ("src_parts/" if os.path.exists("src_parts/" + f + ".stl") else _NP) + f + ".stl"   # rails: notched by rail_notch.py (2026-10-16)
    parts[k] = (_mf(_src).transform(SLED_M[:3, :]), 0x232629, lbl); STATUS[k] = "new"
    inst.append((k, np.eye(4), "sled", (0, 0, -200)))
import pantilt_fit as _PT
for k, m, col, lbl in (("pt_base", _PT.base(), 0x232629, "216 Pan-tilt base"), ("pt_yoke", _PT.yoke(), 0x232629, "217 Pan-tilt yoke"),
                       ("pt_cradle", _PT.cradle(), 0x232629, "218 Camera cradle"), ("pt_lever", _PT.lever(), 0x232629, "219 Tilt lever"),
                       ("pt_pan_servo", _PT.pan_servo() + _PT.pan_horn(), 0x2b55a8, "Pan servo SG90 / MG90S"),
                       ("pt_tilt_servo", _PT.tilt_servo(0), 0x2b55a8, "Tilt servo SG90 / MG90S"),
                       ("pt_camera", _PT.camera(), 0x1f7a3a, "Arducam for Pi Zero")):
    parts[k] = (m, col, lbl); STATUS[k] = "new"
    inst.append((k, np.eye(4), "sled", (0, 0, 90) if k != "pt_base" else (0, 0, 60)))
parts["cell_plate"] = (_mf(_NP + "305_rov_cell_plate_8_v2.stl"), parts["cell_plate"][1], "305 Cell holder plate v2")
# repack: plates v2 (2 mm floor, 6 mm pockets, cells on a 24.5 mm ring), groups 69 mm long, 3 mm spacers between
_cp = [(0.0, 0.0)] + [(24.5*np.cos(np.radians(90 + k*360/7)), 24.5*np.sin(np.radians(90 + k*360/7))) for k in range(7)]
inst = [i for i in inst if i[0] not in ("cell", "cell_plate")]
_z = A.POD_Z0 + 6.0
for _g in range(3):
    inst.append(("cell_plate", Tm(0, A.POD_Y, _z), "battery", (0, -60, -150)))
    for (cx, cy) in _cp: inst.append(("cell", Tm(cx, A.POD_Y + cy, _z + 2.0), "battery", (0, -60, -150)))
    inst.append(("cell_plate", Tm(0, A.POD_Y, _z + 69.0) @ Ry(180), "battery", (0, -60, -150)))
    _z += 69.0 + 3.0
# the real front bulkhead (207, your m03r7-001): inner face at z 145
_fb = _tm.load("rov_project/camera_mount/m03r7-001-00a.stl"); _fb.apply_translation(-_fb.bounds.mean(0) * [1, 1, 0] + [0, 0, 145.0 - _fb.bounds[0][2]])
_fbm = Manifold(_Mesh(vert_properties=np.asarray(_fb.vertices, np.float32), tri_verts=np.asarray(_fb.faces, np.uint32))).rotate((0, 0, 45))
for _a in (45, 135, 225, 315):                       # rotated 45 deg; the two missing rod holes drilled 3.2 mm
    _fbm = _fbm - Manifold.cylinder(20, 1.6, 1.6, 24).translate((47*np.cos(np.radians(_a)), 47*np.sin(np.radians(_a)), 140))
parts["bh_front"] = (_fbm, 0x232629, "207 Sled front bulkhead (m03r7-001)")
inst = [i for i in inst if i[0] != "bh_front"] + [("bh_front", np.eye(4), "sled", (0, 0, -200))]

def world(k, M): return parts[k][0].transform(M[:3, :])

if __name__ == "__main__":
    W = [(k, world(k, M)) for k, M, g, _ in inst]
    bad = []
    for (k1, m1), (k2, m2) in itertools.combinations(W, 2):
        b1, b2 = np.array(m1.bounding_box()), np.array(m2.bounding_box())
        if np.any(b1[3:] < b2[:3]) or np.any(b2[3:] < b1[:3]): continue
        v = (m1 ^ m2).volume()
        if v > 0.5: bad.append((k1, k2, round(v, 1)))
    print("v6 interferences:", bad if bad else "none")
    allb = np.array([m.bounding_box() for _, m in W])
    print("v6 envelope (x, y, z):", np.round(allb[:, 3:].max(0) - allb[:, :3].min(0), 0),
          " pod front cap face z =", round(FRONT + 14 + 10, 1))
    meshes = {}
    for k, (m, col, label) in parts.items():
        g = m.to_mesh()
        meshes[k] = {"v": base64.b64encode(np.asarray(g.vert_properties[:, :3], np.float32).tobytes()).decode(),
                     "i": base64.b64encode(np.asarray(g.tri_verts, np.uint32).tobytes()).decode(), "color": col, "label": label}
    json.dump({"meshes": meshes, "instances": [{"k": k, "m": M.T.flatten().round(5).tolist(), "g": g, "ex": list(ex)} for k, M, g, ex in inst]},
              open("rov_viewer/assembly_v6.json", "w"))
    print("instances", len(inst))
