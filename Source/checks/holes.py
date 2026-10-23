"""
Round-hole finder for meshes (used by fastener_check.py).

A hole wall is made of faces whose normals are perpendicular to the hole axis and point into the hole. For each such face
and each trial radius r, centroid + r * normal lands on the hole axis; faces of one hole with the right r all land on the
same point. Clusters with enough faces all round the axis are holes. Axes tried: x, y, z and the six 45-degree diagonals
(every hole in this design is cut along one of those in its part's own frame).
"""
import itertools
import numpy as np

def axes():
    """x, y, z and every direction in the three principal planes at 15-degree steps (bolt circles at 60 / 120 degrees,
    45-degree brackets, radial screws)"""
    a = []
    for i, j in itertools.combinations(range(3), 2):
        for deg in range(0, 180, 15):
            v = np.zeros(3); v[i] = np.cos(np.radians(deg)); v[j] = np.sin(np.radians(deg))
            if not any(abs(abs(np.dot(v, x)) - 1) < 1e-9 for x in a): a.append(v)
    return a

VERSION = 2                                              # bump when the finder changes: invalidates the cache
RADII = np.round(np.arange(0.9, 3.55, 0.05), 3)          # 1.8 to 7 mm diameter: fastener holes

def find_holes(vertices, faces, min_cover=0.66, cell=0.25):
    """[{axis, point (on axis), r, t0, t1}] in the mesh's own frame. t = position along the axis."""
    V = np.asarray(vertices, float); F = np.asarray(faces)
    tri = V[F]; cen = tri.mean(1)
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    area = np.linalg.norm(nrm, axis=1); ok = area > 1e-9
    nrm[ok] /= area[ok, None]
    out = []
    for a in axes():
        sel = ok & (np.abs(nrm @ a) < 0.02)
        if sel.sum() < 6: continue
        c, n = cen[sel], nrm[sel]
        n = n - np.outer(n @ a, a); n /= np.linalg.norm(n, axis=1)[:, None]
        u = np.cross(a, [1, 0, 0] if abs(a[0]) < 0.9 else [0, 1, 0]); u /= np.linalg.norm(u); w = np.cross(a, u)
        # a fastener-hole facet is narrow across the axis (2 pi r / segments < 1.6 mm): drop flat walls first
        tri_s = tri[sel]; perp = tri_s - np.einsum("fvk,k->fv", tri_s, a)[..., None] * a
        narrow = np.ptp(perp @ u, axis=1) ** 2 + np.ptp(perp @ w, axis=1) ** 2 < 1.6 ** 2
        c, n = c[narrow], n[narrow]
        if len(c) < 6: continue
        cu, cw, nu, nw = c @ u, c @ w, n @ u, n @ w
        ang = np.arctan2(-nw, -nu)                         # direction from the axis to the wall
        tt = c @ a
        # axis point for every face at every trial radius, quantised; one sort finds every cluster
        PU = cu[:, None] + RADII[None, :] * nu[:, None]; PW = cw[:, None] + RADII[None, :] * nw[:, None]
        key = np.stack([np.broadcast_to(np.arange(len(RADII)), PU.shape).ravel(),
                        np.round(PU / cell).astype(np.int64).ravel(), np.round(PW / cell).astype(np.int64).ravel()], 1)
        uniq, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True)
        inv = inv.ravel(); fidx = np.repeat(np.arange(len(c)), len(RADII))
        order = np.argsort(inv, kind="stable"); starts = np.concatenate([[0], np.cumsum(cnt)])
        seen = []
        for gi in np.nonzero(cnt >= 6)[0]:
            m = fidx[order[starts[gi]:starts[gi + 1]]]; r = RADII[uniq[gi, 0]]
            # angular coverage: fraction of 12 sectors that hold a face of this cluster (holes are cut with 16-80 segments)
            cover = len(np.unique(np.floor((ang[m] + np.pi) / (2 * np.pi) * 12).astype(int) % 12)) / 12.0
            if cover < min_cover: continue
            P = np.array([PU[m, uniq[gi, 0]].mean(), PW[m, uniq[gi, 0]].mean()])
            d = np.hypot(cu[m] - P[0], cw[m] - P[1])         # face centroids sit at r*cos(pi/N) from the axis
            if any(abs(s_[0] - r) < 0.12 and np.hypot(*(s_[1] - P)) < 0.3 for s_ in seen): continue
            seen.append((r, P))
            out.append({"axis": a.copy(), "point": P[0] * u + P[1] * w, "r": round(float(np.median(d)), 2),
                        "t0": float(tt[m].min()), "t1": float(tt[m].max()), "faces": int(len(m)), "cover": cover})
    # same physical hole found at neighbouring trial radii / both axis signs: keep the best per (axis line, r)
    best = []
    for h in sorted(out, key=lambda h: -h["faces"]):
        dup = False
        for b in best:
            if abs(abs(np.dot(b["axis"], h["axis"])) - 1) > 1e-6 or abs(b["r"] - h["r"]) > 0.15: continue
            off = h["point"] - b["point"]; off -= np.dot(off, b["axis"]) * b["axis"]
            if np.linalg.norm(off) < 0.4 and h["t0"] < b["t1"] + 0.5 and b["t0"] < h["t1"] + 0.5:
                b["t0"], b["t1"] = min(b["t0"], h["t0"]), max(b["t1"], h["t1"]); dup = True; break
        if not dup: best.append(dict(h))
    return best
