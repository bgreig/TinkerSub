"""
Single-part render scenes for the guide's part pictures: each printed part from out_lbl/ in print orientation,
centred on the bed, rotated z-up -> y-up for three.js. Cowl parts yellow, everything else black.
Writes <render_dir>/<scene>.json for every scene in SCENES (the names render/views/parts.json asks for).
usage: python3 part_scenes.py <out_lbl dir> <render_dir>
"""
import sys, os, glob, json, base64
import numpy as np, trimesh

BLACK, YELLOW = 0x26292d, 0xf2c200
Rx = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]], int)
SCENES = {"parts.json": ["803", "804"], "parts_cowl.json": ["805", "806"],
          **{f"parts{pn}.json": [pn] for pn in ("202", "216", "217", "302", "401", "501", "503", "606")}}
FLIP = {"503"}          # shown face up (the socket map side), not as printed

def enc(t, color, label):
    v, f = np.asarray(t.vertices, np.float32), np.asarray(t.faces, np.uint32)
    return {"v": base64.b64encode(v.tobytes()).decode(), "i": base64.b64encode(f.tobytes()).decode(), "color": color, "label": label}

def scene(lbl, pns):
    meshes, inst = {}, []
    for pn in pns:
        path = glob.glob(os.path.join(lbl, f"{pn}_*.stl"))[0]; stem = os.path.basename(path)[:-4]
        t = trimesh.load(path)
        if pn in FLIP: t.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
        t.apply_translation(-t.bounds.mean(0) * [1, 1, 0] - [0, 0, t.bounds[0, 2]])
        meshes[pn] = enc(t, YELLOW if pn.startswith("8") else BLACK, stem)
        inst.append({"k": pn, "g": "part", "m": Rx.T.flatten().tolist(), "ex": [0, 0, 0]})
    return {"meshes": meshes, "instances": inst}

if __name__ == "__main__":
    lbl, rd = sys.argv[1], sys.argv[2]
    for name, pns in SCENES.items():
        json.dump(scene(lbl, pns), open(os.path.join(rd, name), "w"))
    print("part scenes:", ", ".join(SCENES))
