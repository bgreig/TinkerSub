"""
Render scenes for the final build guide. Colours: top cowl yellow, every other printed part black,
bought parts (PVC pipe, dome, motors, metal, electronics) in their own colours.
Usage: python3 scene_final.py <render_dir>
Writes: f_asm.json (complete ROV), f_v4parts.json (sled / hull / pack detail), f_thr.json, f_light.json,
        f_parts.json (every printed part in print orientation), mix_final.json, crop/f_layout.png
"""
import sys, os, json, base64, re
import numpy as np, trimesh
RD = sys.argv[1]
import parts_final as PF, rov_v5 as V, rov_assembly as A

BLACK, YELLOW = 0x26292d, 0xf2c200
NATURAL = re.compile(r"^(pt_pan_servo|pt_tilt_servo|pt_camera|hull|pod|dome|rod|picam|cell|lt_disc|lt_window|lt_led|lt_cob|motor|coupler|stud|jam|nyloc|oring|gland|rail|rseg|hseg|pseg|cap3|pvc34|cap34|hdpe_.*|e_.*|w_.*|sp13_.*)$")
def colour(k): return YELLOW if k.startswith("cowl") else (None if NATURAL.match(k) else BLACK)
def clean(lbl): return re.sub(r"\s*\((NEW|new|ROV Project)[^)]*\)", "", lbl).replace("BR-style ", "")

def recolour(src, dst, drop=()):
    d = json.load(open(src))
    for k in list(d["meshes"]):
        if k in drop: del d["meshes"][k]; continue
        m = d["meshes"][k]; c = colour(k)
        if c is not None: m["color"] = c
        m["label"] = clean(m.get("label", k))
    d["instances"] = [i for i in d["instances"] if i["k"] in d["meshes"]]
    json.dump(d, open(os.path.join(RD, dst), "w"))
    return d

recolour("rov_viewer/assembly_v6.json", "f_asm.json")
recolour(os.path.join(RD, "v4.json"), "f_v4parts.json")
recolour(os.path.join(RD, "scene_thruster.json"), "f_thr.json")
recolour(os.path.join(RD, "scene_light.json"), "f_light.json", drop=("rail",))

def enc(t, color, label):
    v, f = np.asarray(t.vertices, np.float32), np.asarray(t.faces, np.uint32)
    return {"v": base64.b64encode(v.tobytes()).decode(), "i": base64.b64encode(f.tobytes()).decode(), "color": color, "label": label}
Rx = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]], float)
meshes, inst = {}, []
for sec, stem, src, *_ in PF.PRINTED:
    t = trimesh.load(f"{src}/{stem}.stl"); t.apply_translation(-t.bounds.mean(0) * [1, 1, 0] - [0, 0, t.bounds[0, 2]])
    meshes[stem] = enc(t, YELLOW if PF.is_yellow(stem) else BLACK, stem)
    inst.append({"k": stem, "m": Rx.T.flatten().tolist(), "g": "part", "ex": [0, 0, 0]})
json.dump({"meshes": meshes, "instances": inst}, open(os.path.join(RD, "f_parts.json"), "w"))

# ---------------- thruster positions, mixing and layout (from the final frame)
names = {("H", True, 1): "T1 front port", ("H", True, -1): "T2 front starboard", ("H", False, 1): "T3 rear port",
         ("H", False, -1): "T4 rear starboard", ("V", None, 1): "T5 vertical port", ("V", None, -1): "T6 vertical starboard"}
rows = []
for i, (kind, M2, side, face, corners) in enumerate(V.THR):
    p = (M2 @ np.array([0, 0, 52.0, 1]))[:3]; a = A.THR[i][1][:3, 2]; a = a / np.linalg.norm(a)
    front = None if kind == "V" else p[2] > 0
    rows.append([names[(kind, front, side)], p, a, a[2], -a[0], a[1], p[2]*a[0] - p[0]*a[2], kind])
rows.sort(key=lambda r: r[0])
ymax = max(abs(r[6]) for r in rows)
mix = [{"name": r[0], "x": round(float(r[1][0])), "y": round(float(r[1][1])), "z": round(float(r[1][2])),
        "surge": round(float(r[3]), 2), "sway": round(float(r[4]), 2), "heave": round(float(r[5]), 2), "yaw": round(float(r[6]/ymax), 2)} for r in rows]
json.dump(mix, open(os.path.join(RD, "mix_final.json"), "w"), indent=1)

import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon, FancyArrow
fig, ax = plt.subplots(figsize=(6.4, 7.6))
X = lambda x: -x
ax.add_patch(Rectangle((-57.15, A.P0), 114.3, A.HULL_L, fc="#eef1f4", ec="#7d8790", lw=1.2))
ax.add_patch(Polygon([[X(-50*np.cos(t)), A.FRONT_FACE + 2 + 50*np.sin(t)] for t in np.linspace(0, np.pi, 40)], fc="#dcecf7", ec="#7d8790"))
ax.add_patch(Rectangle((-44.45, A.POD_Z0), 88.9, A.POD_L, fc="none", ec="#7d8790", ls="--", lw=1))
for s in (1, -1): ax.add_patch(Rectangle((X(s*V.XP) - (V.T_PL if s < 0 else 0), V.PZ0), V.T_PL, V.PZ1 - V.PZ0, fc="#26292d", ec="#26292d"))
for zc in V.ST_Z: ax.add_patch(Rectangle((-V.XP, zc - 12), 2*V.XP, 24, fc="#26292d33", ec="#26292d", lw=0.8))
for r in rows:
    p, a = r[1], r[2]; px, pz = X(p[0]), p[2]
    if r[7] == "V":
        ax.add_patch(Circle((px, pz), 43, fc="#26292d22", ec="#26292d", lw=1.2)); ax.add_patch(Circle((px, pz), 6, fc="#26292d", ec="#26292d"))
    else:
        d = np.array([X(a[0]), a[2]]); n = np.array([-d[1], d[0]]); c = np.array([px, pz]); L, W = 104, 86
        ax.add_patch(Polygon([c + d*L/2 + n*W/2, c + d*L/2 - n*W/2, c - d*L/2 - n*W/2, c - d*L/2 + n*W/2], fc="#26292d22", ec="#26292d", lw=1.2))
        ax.add_patch(FancyArrow(px, pz, d[0]*70, d[1]*70, width=5, head_width=16, head_length=16, color="#c0392b", ec="#26292d", lw=0.6))
    ax.text(px + (14 if px > 0 else -14), pz - 30, r[0].split()[0], fontsize=10, fontweight="bold", ha="center")
ax.annotate("FRONT (dome)", (0, A.FRONT_FACE + 70), ha="center", fontsize=9, color="#5b6670")
ax.text(150, -265, "starboard →", ha="right", fontsize=8, color="#5b6670")
ax.set_xlim(-200, 200); ax.set_ylim(-280, 300); ax.set_aspect("equal"); ax.axis("off")
ax.set_title("Thruster layout, top view (red arrows = + thrust; side plates and stations in black)", fontsize=9)
plt.tight_layout(); plt.savefig(os.path.join(RD, "crop", "f_layout.png"), dpi=170)
print("scenes ok;", json.dumps(mix))
