"""
Exports every NEW v5 printed part to out_v5/ in print orientation (mm) and updates the volume table.
Run: python3 export_v5.py <vols.json>
"""
import os, sys, json
import numpy as np, trimesh
import rov_v5 as V

OUT = "out_v5"
def save(name, m, rot=None, flip=False):
    if rot is not None: m = m.rotate(rot)
    if flip: m = m.rotate((180, 0, 0))
    g = m.to_mesh(); t = trimesh.Trimesh(g.vert_properties[:, :3], g.tri_verts)
    t.apply_translation([-(t.bounds[0][0] + t.bounds[1][0])/2, -(t.bounds[0][1] + t.bounds[1][1])/2, -t.bounds[0][2]])
    t.export(f"{OUT}/{name}.stl")
    ok = t.is_watertight and len(t.split(only_watertight=False)) == 1 and max(t.extents[:2]) <= 244
    print(f"{name:34s} {'ok ' if ok else 'CHECK'} size={np.round(t.extents, 1)}")
    return name

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    P = V.parts
    for k in [k for k in P if k.startswith("plate_")]:                 # side plate pieces: flat, thickness up
        sgn = 1 if k.endswith("port") else -1
        save("rov5_" + k, P[k][0], rot=(0, 90 if sgn > 0 else -90, 0))
    lower = next(m for k, (m, c, l) in P.items() if k.startswith("splice_lower_port"))
    upper = next(m for k, (m, c, l) in P.items() if k.startswith("splice_upper_port"))
    save("rov5_splice_strip_lower", lower, rot=(0, 90, 0))
    save("rov5_splice_strip_upper", upper, rot=(0, 90, 0))
    for k in V.STATION: save("rov5_station_" + k[3:], V.STATION[k])          # flat, z up (all 2D extrusions)
    save("rov5_junction_deck", P["jdeck"][0], rot=(-90, 0, 0))
    a = next(b for key, b in V.BRK if key == "brk_corner_a"); b = next(b for key, b in V.BRK if key == "brk_corner_b")
    sa = 1 if np.mean(np.array(a.bounding_box())[[0, 3]]) > 0 else -1
    save("rov5_bracket_corner_a", a, rot=(0, 90 if sa > 0 else -90, 0))     # plate face down
    save("rov5_bracket_corner_b", b, rot=(0, -90 if sa > 0 else 90, 0))
    for k, m in V.COWL.items():
        save("rov5_" + k, m, flip=k.startswith("cowl_front"))             # standing on a seam / the rear end; nose down for the front
    save("rov5_belly_pan", P["belly"][0], rot=(90, 0, 0))
    if len(sys.argv) > 1:
        vols = json.load(open(sys.argv[1]))
        for f in os.listdir(OUT):
            if f.endswith(".stl"):
                t = trimesh.load(f"{OUT}/{f}"); vols[f[:-4]] = [t.volume/1000, list(map(float, t.extents))]
        json.dump(vols, open(sys.argv[1], "w"))
