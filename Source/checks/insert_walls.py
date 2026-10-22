"""Wall thickness around heat-set insert holes in every printed part (sections along x, y and z).
An insert needs about 1.5-2 mm of plastic round it, or the boss splits when it is pressed in or the screw is torqued."""
import sys, numpy as np, trimesh
from shapely.geometry import Polygon, Point
import parts_final as PF
RANGES = {"M2.5": (3.1, 3.7), "M3": (3.8, 4.4), "M4": (5.3, 6.0), "M5": (6.2, 7.3)}
def kind(d):
    for k, (a, b) in RANGES.items():
        if a <= d <= b: return k
def scan(path, step=1.0):
    m = trimesh.load(path); out = {}
    for ax in range(3):
        n = np.zeros(3); n[ax] = 1
        lo, hi = m.bounds[0, ax], m.bounds[1, ax]
        for c in np.arange(lo + 0.5, hi, step):
            o = np.zeros(3); o[ax] = c
            s = m.section(plane_origin=o, plane_normal=n)
            if s is None: continue
            P, T = s.to_2D()
            for pg in P.polygons_full:
                for h in pg.interiors:
                    hp = Polygon(h); cc = np.array(h.coords); ctr = np.array(hp.centroid.coords[0])
                    r = np.linalg.norm(cc - ctr, axis=1); d = 2 * r.mean()
                    if r.std() > 0.15 or not kind(d): continue        # round holes only
                    others = [pg.exterior] + [g for g in pg.interiors if Polygon(g).centroid.distance(hp.centroid) > 0.05]
                    wall = min(hp.exterior.distance(g) for g in others)
                    X = (T @ np.array([*ctr, 0, 1]))[:3]
                    key = (kind(d), ax, tuple(np.round(X[[i for i in range(3) if i != ax]] / 2) * 2))
                    if key not in out or wall < out[key][0]: out[key] = (wall, d, np.round(X, 1))
    return out
if __name__ == "__main__":
    src = sys.argv[1]
    for sec, stem, *_ in PF.PRINTED:
        res = scan(f"{src}/{stem}.stl")
        bad = sorted([(round(w, 2), k[0], round(d, 2), list(X)) for k, (w, d, X) in res.items() if w < 1.6])
        n = len({(k[0], k[2]) for k in res})
        print(f"{stem:34s} insert-size holes {n:3d}  thin (<1.6 mm): {bad[:6]}", flush=True)
