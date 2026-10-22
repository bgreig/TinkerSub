"""
Debossed text labels on printed parts (same colour as the part: the letters are cut 0.6 mm into a flat face).
Finds the flat upward-facing faces of a part in its print orientation and fits each label into solid material,
as close as possible to a requested anchor point, shrinking the text if it has to.
"""
import numpy as np, trimesh
from manifold3d import Manifold, Mesh, CrossSection, FillRule
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties

FONT = FontProperties(family="DejaVu Sans", weight="bold")
DEPTH = 0.6

def text_cs(s, h):
    """text as a CrossSection, cap height ~h mm, centred on (0,0)"""
    tp = TextPath((0, 0), s, size=h / 0.73, prop=FONT)
    polys = [p for p in tp.to_polygons(closed_only=True) if len(p) >= 3]
    cs = CrossSection([np.asarray(p[:-1] if np.allclose(p[0], p[-1]) else p, float) for p in polys], FillRule.EvenOdd)
    b = cs.bounds()
    return cs.translate((-(b[0] + b[2]) / 2, -(b[1] + b[3]) / 2))

def to_manifold(t):
    return Manifold(Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))

def to_trimesh(m):
    g = m.to_mesh(); return trimesh.Trimesh(g.vert_properties[:, :3], g.tri_verts)

def levels(t, min_area=150.0):
    """z heights of flat upward faces with their total area, largest first"""
    n = t.face_normals; up = n[:, 2] > 0.999
    if not up.any(): return []
    z = np.round(t.triangles_center[up, 2], 2); a = t.area_faces[up]
    out = {}
    for zz, aa in zip(z, a): out[zz] = out.get(zz, 0) + aa
    return sorted([(zz, aa) for zz, aa in out.items() if aa >= min_area], key=lambda x: -x[1])

def free_region(m, z, top):
    """area at height z that is a flat face with material DEPTH+0.8 below it and nothing above it"""
    if top:
        reg = m.slice(z - 0.05) ^ m.slice(z - DEPTH - 0.8)
        zmax = m.bounding_box()[5]
        for zz in np.arange(z + 0.3, zmax, 1.0): reg = reg - m.slice(zz)
    else:
        reg = m.slice(0.05) ^ m.slice(DEPTH + 0.8)
    return reg

RES = 0.25
def _raster(cs, x0, y0, W, H):
    from PIL import Image, ImageDraw, ImageChops
    img = Image.new("1", (W, H), 0)
    for P in cs.to_polygons():
        layer = Image.new("1", (W, H), 0)
        pts = [((x - x0) / RES, (y - y0) / RES) for x, y in P]
        if len(pts) >= 3: ImageDraw.Draw(layer).polygon(pts, fill=1)
        img = ImageChops.logical_xor(img, layer)
    return np.array(img, bool)

def place(region, s, anchor=None, hmax=6.0, hmin=2.4, margin=1.2, rotations=(0, 30, -30, 45, -45, 60, -60, 90)):
    """best (cross-section, h, x, y, rot) fitting s inside region, nearest the anchor (raster search, exact check)"""
    from scipy.signal import fftconvolve
    reg = region.offset(-margin, circular_segments=12)
    if reg.is_empty(): return None
    b = reg.bounds(); x0, y0 = b[0] - 2, b[1] - 2
    W, H = int((b[2] - b[0] + 4) / RES) + 1, int((b[3] - b[1] + 4) / RES) + 1
    R = _raster(reg, x0, y0, W, H); outside = (~R).astype(np.float32)
    if anchor is None: anchor = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
    h = hmax
    while h >= hmin - 1e-6:
        best = None
        for rot in rotations:
            T = text_cs(s, h).rotate(rot); tb = T.bounds()
            if tb[2] - tb[0] > b[2] - b[0] or tb[3] - tb[1] > b[3] - b[1]: continue
            tw, th = int((tb[2] - tb[0]) / RES) + 3, int((tb[3] - tb[1]) / RES) + 3
            K = _raster(T, tb[0] - RES, tb[1] - RES, tw, th).astype(np.float32)
            if not K.any(): continue
            hits = fftconvolve(outside, K[::-1, ::-1], mode="valid")
            ok = np.argwhere(hits < 0.5)
            if not len(ok): continue
            cx = x0 + ok[:, 1] * RES - (tb[0] - RES); cy = y0 + ok[:, 0] * RES - (tb[1] - RES)
            d = np.hypot(cx - anchor[0], cy - anchor[1]); order = np.argsort(d)
            for k in order[:50]:
                Tt = T.translate((cx[k], cy[k]))
                if (Tt - reg).area() < 1e-2:
                    if best is None or d[k] < best[0]: best = (d[k], Tt, h, cx[k], cy[k], rot)
                    break
            if best is not None and rot == rotations[0]: break
        if best is not None: return best[1:]
        h *= 0.88
    return None

def engrave(t, labels, used=None):
    """labels: list of dicts {text, anchor=(x,y)|None, hmax, level='top'|'bottom'|z}. Returns (mesh, report)."""
    m = to_manifold(t)
    if m.status().name != "NoError" if hasattr(m.status(), "name") else False: return t, ["not a closed solid: skipped"]
    lv = levels(t)
    rep, cut = [], None
    taken = CrossSection()
    for L in labels:
        cands = []
        if L.get("level", "top") == "bottom": cands = [(0.0, False)]
        elif isinstance(L.get("level"), (int, float)): cands = [(float(L["level"]), True)]
        else: cands = [(z, True) for z, a in lv] + [(0.0, False)]
        done = False
        for z, top in cands:
            reg = free_region(m, z, top) - taken.offset(2.0, circular_segments=8)
            r = place(reg, L["text"], L.get("anchor"), L.get("hmax", 6.0), L.get("hmin", 2.4), L.get("margin", 1.2), **({"rotations": L["rotations"]} if L.get("rotations") else {}))
            if r is None: continue
            T, h, x, y, rot = r
            if not top: T = T.mirror((1, 0))                    # bottom face: reads correctly from below
            if not top: T = T.translate((2 * x, 0))
            z0, z1 = (z - DEPTH, z + 1.0) if top else (-1.0, DEPTH)
            sol = Manifold.extrude(T, z1 - z0).translate((0, 0, z0))
            cut = sol if cut is None else cut + sol
            taken = taken + T
            rep.append(f"'{L['text']}' {h:.1f} mm on {'z=%.1f' % z if top else 'bed face'}"); done = True; break
        if not done: rep.append(f"'{L['text']}' did not fit")
    if cut is None: return t, rep
    return to_trimesh(m - cut), rep

SIDE_ROT = {"+x": (0, -90, 0), "-x": (0, 90, 0), "+y": (90, 0, 0), "-y": (-90, 0, 0)}
def _R(r):
    return trimesh.transformations.euler_matrix(*np.radians(r), axes="sxyz")
def engrave_all(t, labels, margin=None):
    """like engrave(), but labels may carry side='+x'|'-x'|'+y'|'-y' to go on a vertical wall"""
    rep = []
    groups = {}
    for L in labels: groups.setdefault(L.get("side"), []).append(L)
    for side, ls in groups.items():
        if side is None:
            t, r = engrave(t, ls)
        else:
            M = _R(SIDE_ROT[side]); t = t.copy(); t.apply_transform(M)
            up = M[:3, :3] @ np.array([0, 0, 1.0])                  # where the part's up ends up in the rotated frame
            base = np.degrees(np.arctan2(up[1], up[0])) - 90         # text rotation that keeps letters upright
            ls = [dict(L, rotations=(base,)) for L in ls]
            t, r = engrave(t, ls); t.apply_transform(np.linalg.inv(M))
            r = [x + f" ({side} wall)" for x in r]
        rep += r
    return t, rep
