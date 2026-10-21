"""Top-down preview of every plate in a Bambu project 3MF made by make_3mf.py."""
import zipfile, re, sys, numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon
from scipy.spatial import ConvexHull
src, out = sys.argv[1], sys.argv[2]
z = zipfile.ZipFile(src)
cfg = z.read('Metadata/model_settings.config').decode(); root = z.read('3D/3dmodel.model').decode()
names = dict(re.findall(r'<object id="(\d+)">\s*<metadata key="name" value="([^"]+)"', cfg))
comp = dict(re.findall(r'<object id="(\d+)"[^>]*>\s*<components>\s*<component p:path="([^"]+)"', root))
tf = {o: np.array(t.split(), float) for o, t in re.findall(r'<item objectid="(\d+)"[^>]*transform="([^"]+)"', root)}
plates = re.findall(r'<plate>(.*?)</plate>', cfg, re.S)
hulls = {}
def hull(path):
    if path not in hulls:
        v = np.array(re.findall(r'x="([-\d.]+)" y="([-\d.]+)"', z.read(path.lstrip('/')).decode()), float)
        hulls[path] = v[ConvexHull(v).vertices]
    return hulls[path]
n = len(plates); v = np.sqrt(n); cols = int(round(v)) + (1 if v > round(v) else 0); rows = (n + cols - 1) // cols; S = 307.2
fig, axs = plt.subplots(rows, cols, figsize=(4 * cols, 4.4 * rows))
axs = np.atleast_2d(axs)
for pi, p in enumerate(plates):
    ax = axs[pi // cols][pi % cols]; ox, oy = (pi % cols) * S, -(pi // cols) * S
    pname = re.search(r'plater_name" value="([^"]*)"', p).group(1)
    ax.add_patch(Rectangle((0, 0), 256, 256, fc='#f3f5f7', ec='#9aa4ad'))
    for oid in re.findall(r'object_id" value="(\d+)"', p):
        t = tf[oid]; R = t[:9].reshape(3, 3); T = t[9:]
        hv = hull(comp[oid]); P = (np.c_[hv, np.zeros(len(hv))] @ R)[:, :2] + T[:2] - [ox, oy]
        yl = 'cowl' in names[oid]
        ax.add_patch(Polygon(P, fc='#f2c200' if yl else '#26292d', ec='#1d2329', alpha=0.9, lw=0.6))
        c = P.mean(0)
        nm = names[oid]; q = re.search(r'\((\d+) of (\d+)\)', nm)
        lbl = nm[:3] + (f"\n{q.group(1)}/{q.group(2)}" if q else "")    # part number, as engraved on the part
        if np.ptp(P[:, 0]) < 15 and np.ptp(P[:, 1]) < 15: continue      # too small to label (title lists them)
        ax.text(c[0], c[1], lbl, fontsize=6.5, ha='center', va='center', fontweight='bold', color='#1d2329' if yl else 'white')
    ax.set_xlim(-5, 261); ax.set_ylim(-5, 261); ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
    import textwrap
    ax.set_title("\n".join(textwrap.wrap(f"Plate {pi + 1}: {pname}", 40)), fontsize=9)
for k in range(n, rows * cols): axs[k // cols][k % cols].axis('off')
plt.tight_layout(); plt.savefig(out, dpi=110)
