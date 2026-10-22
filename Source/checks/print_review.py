"""
Printability review of every printed part as it sits on the bed (out_lbl/<PN>_<stem>.stl = print orientation).
Slices each part every DZ mm and checks, the way a slicer sees it:
  - bed fit (A1: 256 x 256 x 256), watertight, one body
  - LOOSE COLUMNS: separate regions that stand on the bed (or grow up) on their own and only join the rest of the
    part much higher up (the cowl v1 fault); reported with height before joining and minimum width
  - FLOATING ISLANDS: regions that start in mid-air with nothing under them (need supports)
  - OVERHANGS: area per layer that sticks out more than 50 deg from vertical past the layer below
  - THIN WALLS: area per layer narrower than 0.8 mm (two 0.4 mm lines); slicers drop or weaken these
  - STABILITY: first-layer contact area vs height
usage: python3 print_review.py <out_lbl dir> <report.json>
"""
import sys, json, math, glob, os
import numpy as np, trimesh
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
import parts_final as PF

SRC, OUT = (sys.argv[1:3] + [None, None])[:2]
DZ = 0.4
OVH = math.tan(math.radians(50)) * DZ          # allowed outward step per layer before it counts as overhang

def polys_at(m, z):
    s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if s is None: return []
    P, _ = s.to_2D(to_2D=np.eye(4))
    return [p.buffer(0) for p in P.polygons_full if p.area > 0.05]

def review(path, note):
    m = trimesh.load(path)
    ext = m.extents; z0, z1 = m.bounds[:, 2]
    res = {"size": [round(float(e), 1) for e in ext], "watertight": bool(m.is_watertight),
           "bodies": len(m.split(only_watertight=False)), "fits_bed": bool(max(ext[:2]) <= 250 and ext[2] <= 250)}
    zs = np.arange(z0 + DZ/2, z1, DZ)
    prev, prev_u, groups = [], None, []           # groups: per-region id via union-find
    parent = {}
    def find(a):
        while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
        return a
    def union(a, b): parent[find(a)] = find(b)
    gid = 0; info = {}                              # gid -> dict(start z, on_bed, min_width, max area)
    ovh_area, ovh_z, float_isl, thin_area, thin_z = 0.0, [], [], 0.0, []
    layer_groups = []
    first_area = None
    for li, z in enumerate(zs):
        cur = polys_at(m, z)
        if li == 0: first_area = sum(p.area for p in cur)
        ids = []
        for p in cur:
            gid += 1; parent[gid] = gid
            w = 2 * p.area / max(p.length, 1e-6)
            info[gid] = {"z0": z, "bed": li == 0, "minw": w, "area": p.area}
            hit = False
            for q, qid in prev:
                if p.intersects(q.buffer(OVH)): union(gid, qid); hit = True
            if not hit and li > 0:
                float_isl.append((round(float(z - z0), 1), round(p.area, 1), [round(c, 1) for c in p.centroid.coords[0]]))
            ids.append((p, gid))
        # overhang + thin walls
        if cur:
            u = unary_union(cur)
            if prev_u is not None and li > 0:
                a = u.difference(prev_u.buffer(OVH)).area
                if a > 2.0: ovh_area += a * DZ; ovh_z.append(round(float(z - z0), 1))
            th = u.difference(u.buffer(-0.4).buffer(0.4)).area
            if th > 1.0: thin_area += th * DZ; thin_z.append(round(float(z - z0), 1))
            prev_u = u
        layer_groups.append([g for _, g in ids])
        prev = ids
    # loose columns: at each layer, how many distinct final groups are present that started on the bed or grew from
    # a floating start; a column = a group of regions that stays separate from the largest region for many layers
    # (re-run union-find per layer prefix: track, per layer, the root of each region considering only layers <= now)
    parent2 = {}
    def f2(a):
        while parent2[a] != a: parent2[a] = parent2[parent2[a]]; a = parent2[a]
        return a
    sep = {}                                        # root -> (start z, layers separate, min width)
    prev_ids = []
    cols = []
    poly_cache = {}
    for li, z in enumerate(zs):
        ids = layer_groups[li]
        for g in ids: parent2[g] = g
        # recompute links with the previous layer
        cur = [(p, g) for p, g in zip(polys_at(m, z), ids)] if False else None
        prev_ids = ids
    # cheaper column detection: within each layer, count regions; for a region that is NOT the largest in its layer,
    # follow it down/up: report spans where a small region exists continuously and is unconnected in-layer
    small_runs = {}
    for li, ids in enumerate(layer_groups):
        if len(ids) < 2: continue
        big = max(ids, key=lambda g: info[g]["area"])
        for g in ids:
            if g == big: continue
            r = find(g)
            if r == find(big): pass
            key = r
            d = small_runs.setdefault(key, {"z0": zs[li] - z0, "z1": zs[li] - z0, "minw": info[g]["minw"], "maxa": info[g]["area"], "same_final": find(g) == find(big)})
            d["z1"] = zs[li] - z0; d["minw"] = min(d["minw"], info[g]["minw"]); d["maxa"] = max(d["maxa"], info[g]["area"])
    res["first_layer_mm2"] = round(float(first_area or 0), 1)
    res["height_over_base"] = round(float(ext[2] / max(math.sqrt(first_area or 1e-6), 1e-6)), 2)
    res["floating_islands"] = float_isl[:12]; res["n_floating"] = len(float_isl)
    res["overhang_mm3"] = round(ovh_area, 1); res["overhang_z"] = [min(ovh_z), max(ovh_z)] if ovh_z else []
    res["thin_mm3"] = round(thin_area, 1); res["thin_z"] = [min(thin_z), max(thin_z)] if thin_z else []
    res["separate_runs"] = sorted([{"from_z": round(float(v["z0"]), 1), "to_z": round(float(v["z1"]), 1), "height": round(float(v["z1"] - v["z0"]), 1),
                                    "min_width": round(float(v["minw"]), 2), "max_area": round(float(v["maxa"]), 1)} for v in small_runs.values()
                                   if v["z1"] - v["z0"] >= 4.0], key=lambda d: -d["height"])[:8]
    res["note"] = note
    return res

if __name__ == "__main__":
    out = {}
    for sec, stem, src, qty, mat, note, use in PF.PRINTED:
        p = f"{SRC}/{stem}.stl"
        if not os.path.exists(p): out[stem] = {"missing": True}; continue
        try: out[stem] = review(p, note)
        except Exception as e: out[stem] = {"error": repr(e)}
        r = out[stem]
        print(f"{stem:38s} size={r.get('size')} bodies={r.get('bodies')} float={r.get('n_floating')} ovh={r.get('overhang_mm3')} "
              f"thin={r.get('thin_mm3')} runs={[(d['height'], d['min_width']) for d in r.get('separate_runs', [])][:3]} base={r.get('first_layer_mm2')}", flush=True)
    json.dump(out, open(OUT, "w"), indent=1)

def loose(path, dz=0.4, min_h=6.0):
    """incremental connectivity: a region is LOOSE at layer i if, using only layers <= i, it is not connected to the
    largest region of that layer. Returns loose components with z range, thinnest width, biggest area and where."""
    m = trimesh.load(path); z0, z1 = m.bounds[:, 2]
    parent = {}
    def find(a):
        while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
        return a
    prev, gid, comps = [], 0, {}
    for li, z in enumerate(np.arange(z0 + dz/2, z1, dz)):
        cur = []
        for p in polys_at(m, z):
            gid += 1; parent[gid] = gid
            for q, qid in prev:
                if p.intersects(q.buffer(OVH)): parent[find(gid)] = find(qid)
            cur.append((p, gid))
        if len(cur) > 1:
            # main = component with the largest total area in this layer
            tot = {}
            for p, g in cur: tot[find(g)] = tot.get(find(g), 0) + p.area
            main = max(tot, key=tot.get)
            for p, g in cur:
                r = find(g)
                if r == main: continue
                w = 2 * p.area / max(p.length, 1e-6)
                c = comps.setdefault(r, {"from": z - z0, "to": z - z0, "minw": w, "maxw": w, "area": p.area, "xy": p.centroid.coords[0], "bed": li == 0})
                c["to"] = z - z0; c["minw"] = min(c["minw"], w); c["maxw"] = max(c["maxw"], w); c["area"] = max(c["area"], p.area)
        prev = cur
    # merge records whose roots later unified (report by final root)
    fin = {}
    for r, c in comps.items():
        k = find(r); d = fin.setdefault(k, dict(c)); d["from"] = min(d["from"], c["from"]); d["to"] = max(d["to"], c["to"])
        d["minw"] = min(d["minw"], c["minw"]); d["maxw"] = max(d["maxw"], c["maxw"]); d["area"] = max(d["area"], c["area"]); d["bed"] = d["bed"] or c["bed"]
    out = [{"z": [round(float(d["from"]), 1), round(float(d["to"]), 1)], "height": round(float(d["to"] - d["from"]), 1),
            "width": [round(float(d["minw"]), 2), round(float(d["maxw"]), 2)], "area": round(float(d["area"]), 1),
            "xy": [round(float(v), 1) for v in d["xy"]], "from_bed": d["bed"]} for d in fin.values() if d["to"] - d["from"] >= min_h]
    return sorted(out, key=lambda d: -d["height"])
