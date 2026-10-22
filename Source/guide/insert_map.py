"""
Heat-set insert map: finds every insert hole in each printed part (out_lbl STLs, print orientation) and writes
render scenes with an arrow pointing into each hole, coloured by size (M3 orange, M4 blue, M5 magenta).
Hole sizes in this design: M3 insert 4.0 mm, M4 5.6 mm, M5 6.4 mm (clearance holes are 3.4 / 4.5 / 5.5, so no overlap).
usage: python3 insert_map.py <out_lbl> <render_dir> <inserts.json>
"""
import sys, json, base64, itertools
import numpy as np, trimesh
from shapely.geometry import Polygon
import parts_final as PF

SIZES = {"M3": (4.0, 0.12), "M4": (5.6, 0.12), "M5": (6.4, 0.12)}
COL = {"M3": 0xf28c28, "M4": 0x2f7de1, "M5": 0xd63384}
# expected count per part (from the source code: rov_v5 arm()/st_top()/st_bot()/junction_deck()/brackets/cowl feet,
# pylon.py pinch ears, rov_parts pod flange, jbox lid bosses, hull flange radial holes)
EXPECT = {"106": {"M4": 2}, "201": {"M3": 3}, "203": {"M3": 3}, "301": {"M5": 6}, "501": {"M3": 4},
          "601": {"M5": 2, "M3": 1}, "602": {"M5": 2, "M3": 1}, "604": {"M5": 2, "M4": 1}, "605": {"M5": 2, "M4": 1},
          "606": {"M3": 4}, "607": {"M3": 4, "M5": 2}, "608": {"M3": 4, "M5": 2},
          "801": {"M3": 1}, "802": {"M3": 1}, "803": {"M3": 2}, "804": {"M3": 2}, "805": {"M3": 1}, "806": {"M3": 1}}

def normals():
    n = [np.eye(3)[i] for i in range(3)]
    for i, j in itertools.combinations(range(3), 2):
        for s in (1, -1):
            v = np.zeros(3); v[i] = 1; v[j] = s; n.append(v / np.linalg.norm(v))
    return n

def find(m, step=0.5):
    hits = []
    for n in normals():
        d = m.vertices @ n
        for c in np.arange(d.min() + 0.3, d.max() - 0.3, step):
            s = m.section(plane_origin=n * c, plane_normal=n)
            if s is None: continue
            P, T = s.to_2D()
            for pg in P.polygons_full:
                for h in pg.interiors:
                    cc = np.array(h.coords); ctr = np.array(Polygon(h).centroid.coords[0])
                    r = np.linalg.norm(cc - ctr, axis=1)
                    if r.std() > 0.08: continue
                    for k, (dia, tol) in SIZES.items():
                        if abs(2 * r.mean() - dia) <= tol:
                            hits.append((k, tuple(n), (T @ np.array([*ctr, 0, 1]))[:3], c))
    # cluster: same size + axis, centres on one line within 0.6 mm
    holes = []
    for k, n, X, c in hits:
        n = np.array(n)
        for h in holes:
            if h["k"] == k and abs(abs(np.dot(h["n"], n)) - 1) < 1e-6:
                off = X - h["p"]; perp = off - np.dot(off, h["n"]) * h["n"]
                if np.linalg.norm(perp) < 0.6: h["t"].append(np.dot(X, h["n"])); break
        else: holes.append({"k": k, "n": n, "p": X, "t": [np.dot(X, n)]})
    holes = [h for h in holes if len(h["t"]) >= 3]          # a real hole spans several sections
    out = []
    for h in holes:
        n, p = h["n"], h["p"]; base = p - np.dot(p, n) * n
        t0, t1 = min(h["t"]), max(h["t"])
        # open end = the end where the material stops just beyond the last ring
        # open end vs bottom: just past each end, sample a ring at 0.85 x the insert radius. At the bottom (or where the
        # hole steps down to a bolt clearance) that ring is in plastic; at the open end it is in air.
        u = np.cross(n, [1, 0, 0] if abs(n[0]) < 0.9 else [0, 1, 0]); u /= np.linalg.norm(u); w = np.cross(n, u)
        rr = 0.85 * SIZES[h["k"]][0] / 2
        ring = [rr * (np.cos(a) * u + np.sin(a) * w) for a in np.linspace(0, 2*np.pi, 12, endpoint=False)]
        fa = np.mean(m.contains([base + n * (t0 - 1.0) + q for q in ring]))
        fb = np.mean(m.contains([base + n * (t1 + 1.0) + q for q in ring]))
        if fa < fb: mouth, inward = base + n * t0, n          # open at the t0 end
        else: mouth, inward = base + n * t1, -n
        out.append({"size": h["k"], "mouth": mouth.round(2).tolist(), "inward": inward.round(4).tolist(), "depth": round(t1 - t0 + 0.5, 1)})
    # drop duplicates found along two normals (diagonal sections of an axial hole are ellipses, so rare)
    return out

def arrow(mouth, inward, length=22.0, r=1.4):
    """arrow pointing into the hole; tip 1 mm outside the mouth"""
    mouth, inward = np.array(mouth), np.array(inward)
    tip = mouth - inward * 1.0
    shaft = trimesh.creation.cylinder(radius=r, segment=[tip - inward * length, tip - inward * 7.0], sections=16)
    cone = trimesh.creation.cone(radius=r * 2.6, height=7.0, sections=24)
    # cone axis +z, base at z=0 -> point it along inward, tip at `tip`
    R = trimesh.geometry.align_vectors([0, 0, 1], inward)
    cone.apply_transform(R); cone.apply_translation(tip - inward * 7.0)
    return trimesh.util.concatenate([shaft, cone])

def enc(t, color, label):
    return {"v": base64.b64encode(np.asarray(t.vertices, np.float32).tobytes()).decode(),
            "i": base64.b64encode(np.asarray(t.faces, np.uint32).tobytes()).decode(), "color": color, "label": label}

if __name__ == "__main__":
    src, rd, js = sys.argv[1:4]
    res = {}
    Rx = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]], float)    # print z-up -> render y-up
    for sec, stem, *_ in PF.PRINTED:
        pn = stem[:3]
        if pn not in EXPECT: continue
        m = trimesh.load(f"{src}/{stem}.stl")
        holes = find(m)
        if pn in ("201", "203"):        # hull flanges: 3 radial M3 at 0/120/240 deg, 15 mm up (the 4 sled holes stay plain)
            h0 = next(h for h in holes if abs(h["inward"][2]) < 1e-3 and abs(abs(h["inward"][0]) - 1) < 1e-3)
            r, z = float(np.hypot(*h0["mouth"][:2])), h0["mouth"][2]
            holes = [{"size": "M3", "mouth": [round(r*np.cos(a), 2), round(r*np.sin(a), 2), z], "inward": [round(-np.cos(a), 4), round(-np.sin(a), 4), 0.0],
                      "depth": h0["depth"]} for a in np.radians([0.0, 120.0, 240.0])]
        cnt = {}
        for h in holes: cnt[h["size"]] = cnt.get(h["size"], 0) + 1
        ok = cnt == EXPECT[pn]
        res[pn] = {"stem": stem, "holes": holes, "count": cnt, "expected": EXPECT[pn], "ok": ok}
        print(f"{stem:30s} found {cnt}  expected {EXPECT[pn]}  {'OK' if ok else 'CHECK'}", flush=True)
        c = m.bounds.mean(0) * [1, 1, 0] + [0, 0, m.bounds[0, 2]]
        meshes = {pn: enc(m.copy().apply_translation(-c), 0x5c636b, pn)}
        inst = [{"k": pn, "m": Rx.T.flatten().tolist(), "g": "part", "ex": [0, 0, 0]}]
        for i, h in enumerate(holes):
            sc = max(1.0, float(max(m.extents)) / 60.0)          # bigger arrows on big parts
            a = arrow(np.array(h["mouth"]) - c, h["inward"], length=22.0 * sc, r=1.4 * min(sc, 1.8))
            k = f"arr_{h['size']}_{i}"; meshes[k] = enc(a, COL[h["size"]], k)
            inst.append({"k": k, "m": Rx.T.flatten().tolist(), "g": "arrow", "ex": [0, 0, 0]})
        json.dump({"meshes": meshes, "instances": inst}, open(f"{rd}/ins_{pn}.json", "w"))
    json.dump(res, open(js, "w"), indent=1)
