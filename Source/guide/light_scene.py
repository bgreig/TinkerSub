"""
Render scenes for the lights (guide sections 12 and 17):
  f_light.json       one light head, exploded along the beam, cable straight out of the back (rear body 401)
  f_lightmount.json  front cowl sections (805 / 806) with both heads in their nose sleeves, the M3 set screws, and the
                     two light leads running back to sockets L1 / L2 on the junction box (501), plugs mated
usage: python3 light_scene.py <assembly_json> <render_dir>
"""
import sys, os, json, base64
import numpy as np, trimesh
import lights as LT

ASM, RD = sys.argv[1], sys.argv[2]
BLACK, ALU, GLASS, CABLE, STEEL, LED = 0x26292d, 0xc9ccd0, 0xdfeef7, 0x1b1c1f, 0x9aa0a6, 0xf2efe2

def enc_tm(t, color, label):
    return {"v": base64.b64encode(np.asarray(t.vertices, np.float32).tobytes()).decode(),
            "i": base64.b64encode(np.asarray(t.faces, np.uint32).tobytes()).decode(), "color": color, "label": label}
def man2tm(m):
    g = m.to_mesh(); return trimesh.Trimesh(g.vert_properties[:, :3], g.tri_verts, process=False)
def M16(M): return np.asarray(M, float).T.flatten().round(5).tolist()

def cable(pts, r=2.8):
    """round cable along a polyline: cylinders between points + spheres at the joints"""
    P = [np.array(p, float) for p in pts]; parts = []
    for a, b in zip(P[:-1], P[1:]):
        parts.append(trimesh.creation.cylinder(radius=r, segment=[a, b], sections=16))
    for p in P[1:-1]: parts.append(trimesh.creation.icosphere(subdivisions=1, radius=r).apply_translation(p))
    return trimesh.util.concatenate(parts)

def smooth(pts, n=6):
    """corner-rounded polyline (quadratic fillets) so the cable reads as a cable"""
    P = [np.array(p, float) for p in pts]; out = [P[0]]
    for i in range(1, len(P) - 1):
        a, b, c = P[i - 1], P[i], P[i + 1]
        u, v = b - a, c - b; f = min(12.0, np.linalg.norm(u) / 2.1, np.linalg.norm(v) / 2.1)
        p0, p1 = b - u / np.linalg.norm(u) * f, b + v / np.linalg.norm(v) * f
        for t in np.linspace(0, 1, n): out.append((1 - t) ** 2 * p0 + 2 * (1 - t) * t * b + t ** 2 * p1)
    out.append(P[-1]); return out

HEAD = {"lt_rear": (LT.rear_body, BLACK), "lt_disc": (LT.disc, ALU), "lt_led": (LT.led, LED), "lt_spacer": (LT.spacer, BLACK),
        "lt_window": (LT.window, GLASS), "lt_front": (LT.front_ring, BLACK)}
HEADM = {k: man2tm(f()) for k, (f, c) in HEAD.items()}

# ---------------- 1) exploded head + cable out of the back (head frame: +z = beam)
meshes, inst = {}, []
EX = {"lt_rear": 0, "lt_disc": 22, "lt_led": 34, "lt_spacer": 46, "lt_window": 58, "lt_front": 76}
for k, (f, c) in HEAD.items():
    meshes[k] = enc_tm(HEADM[k], c, k); inst.append({"k": k, "m": M16(np.eye(4)), "g": "light", "ex": [0, 0, EX[k]]})
meshes["lt_cable"] = enc_tm(cable(smooth([(0, 0, LT.Z_CAV + 3), (0, 0, -30), (0, -8, -52), (0, -30, -62)]), 2.8), CABLE, "cable")
inst.append({"k": "lt_cable", "m": M16(np.eye(4)), "g": "light", "ex": [0, 0, 0]})
json.dump({"meshes": meshes, "instances": inst}, open(os.path.join(RD, "f_light.json"), "w"))

# ---------------- 2) mounting: cowl nose sections, heads in the sleeves, set screws, leads to the junction box
A = json.load(open(ASM))
KEEP = ("cowl_front_port", "cowl_front_stbd", "cowl_mid_port", "cowl_mid_stbd", "jbox", "jlid", "sp13_plugs", "jdeck", "hull",
        "st_top_port", "st_top_stbd", "fl_front", "dome_ring", "dome")
meshes, inst = {}, []
for i in A["instances"]:
    if i["k"] in KEEP or i["k"].startswith("lt_"):
        if i["k"] not in meshes: meshes[i["k"]] = A["meshes"][i["k"]]
        inst.append(i)
# set screws: M3 x 8 down through the cowl roof and the sleeve wall onto the head (hole at z = CZ1 - 30)
CZ1 = 236.0
TILT, PIV_Y, PIV_D = 15.0, 92.0, 22.0                        # rov_v5.LIGHT_TILT / LIGHT_PIV: sleeves aimed 15 deg nose-down
_t = np.radians(TILT)
def aim(p):
    """a point given for an untilted sleeve -> where it sits with the sleeve pitched TILT deg down about its mid-length"""
    x, y, z = p; dy, dz = y - PIV_Y, z - (CZ1 - PIV_D)
    return (x, PIV_Y + dy*np.cos(_t) - dz*np.sin(_t), CZ1 - PIV_D + dy*np.sin(_t) + dz*np.cos(_t))
AX = np.array([0, -np.sin(_t), np.cos(_t)])                  # beam direction
ss = trimesh.creation.cylinder(radius=1.5, height=8.0, sections=16)
meshes["lt_setscrew"] = enc_tm(ss, STEEL, "M3 x 8 set screw")
cab = []
for sx in (1, -1):                                           # +x = port (L1), -x = starboard (L2)
    inst.append({"k": "lt_setscrew", "m": M16(np.array([[1, 0, 0, sx*100], [0, 0, 1, 116.0 + 4.0], [0, -1, 0, CZ1 - 30], [0, 0, 0, 1]])), "g": "lights", "ex": [0, 0, 0]})
    route = [aim((sx*100, 92, 185 + LT.CABLE_EXIT[2] + 2)), (sx*100, 96, 168), (sx*82, 93, 140), (sx*34, 95, 92), (sx*12, 93.5, 62), (sx*12, 93.5, 48)]
    cab.append(cable(smooth(route), 2.8))
meshes["lt_leads"] = enc_tm(trimesh.util.concatenate(cab), CABLE, "light leads")
inst.append({"k": "lt_leads", "m": M16(np.eye(4)), "g": "lights", "ex": [0, 0, 0]})
json.dump({"meshes": meshes, "instances": inst}, open(os.path.join(RD, "f_lightmount.json"), "w"))
print("light scenes ok")

# ---------------- 3) close-up: port nose sleeve only (head pulled forward out of it), set screw, cable
meshes3, inst3 = {}, []
for i in inst:
    M = np.array(i["m"]).reshape(4, 4).T
    if i["k"] == "cowl_front_port" or (i["k"].startswith("lt_") and i["k"] not in ("lt_leads",) and M[0, 3] > 0):
        meshes3[i["k"]] = meshes[i["k"]]
        inst3.append({**i, "ex": list(AX*70) if i["k"].startswith("lt_") and i["k"] != "lt_setscrew" else ([0, 18, 0] if i["k"] == "lt_setscrew" else [0, 0, 0])})
r3 = [aim((100, 92, 185 + LT.CABLE_EXIT[2] + 2)), (100, 96, 150), (96, 96, 120)]
meshes3["lt_leads"] = enc_tm(cable(smooth(r3), 2.8), CABLE, "light lead")
inst3.append({"k": "lt_leads", "m": M16(np.eye(4)), "g": "lights", "ex": list(AX*70)})
json.dump({"meshes": meshes3, "instances": inst3}, open(os.path.join(RD, "f_lightsleeve.json"), "w"))
print("sleeve scene ok")
