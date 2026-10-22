"""
Guide figures for the HDPE side plates, made from the current plate CAD (run after plate_templates_final.py and plate_stl_final.py):
  f_tile.png  - template tile A1 of the port plate, page 2 of out_final/rov_side_plate_templates.pdf at 80 dpi
  f_nest.png  - both plates on the 24 x 24 in sheet, drawn from out_final/rov_side_plates_24x24_nest.dxf
  f_plate.png - finished port plate, outside face: writes parts901.json into the render dir; render/views/plate.json renders it
                (build.py does this: renders 'plate', saved as f_plate.png)
Usage: python3 plate_figs.py <crop dir> [render dir]
(2026-10-22: replaces the older figures that still showed the rear cowl-foot hole at z -215.)
"""
import sys, os, json, base64
import numpy as np, trimesh, ezdxf, pymupdf
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

CROP = sys.argv[1]
RDIR = sys.argv[2] if len(sys.argv) > 2 else "render"                     # where the render scenes go
os.makedirs(CROP, exist_ok=True)

# template tile
pymupdf.open("out_final/rov_side_plate_templates.pdf")[1].get_pixmap(dpi=80, alpha=False).save(os.path.join(CROP, "f_tile.png"))

# sheet nest, dark CAD style
m = ezdxf.readfile("out_final/rov_side_plates_24x24_nest.dxf").modelspace()
S, pad, BG = 609.6, 20, "#212830"
fig = plt.figure(figsize=(5.28, 5.28), dpi=100); ax = fig.add_axes([0, 0, 1, 1])
fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
ax.set_xlim(-pad, S + pad); ax.set_ylim(-pad, S + pad); ax.set_aspect("equal"); ax.axis("off")
ax.add_patch(Rectangle((0, 0), S, S, fill=False, ec="#8a8f96", lw=0.6))          # the sheet
for e in m:
    if e.dxftype() == "LWPOLYLINE":
        p = np.array([q[:2] for q in e.get_points("xy")]); p = np.vstack([p, p[:1]]); ax.plot(p[:, 0], p[:, 1], color="white", lw=0.8)
    elif e.dxftype() == "CIRCLE":
        c = e.dxf.center; ax.add_patch(Circle((c.x, c.y), e.dxf.radius, fill=False, ec="white", lw=0.8))
fig.savefig(os.path.join(CROP, "f_nest.png"), facecolor=BG)

# render scene for the finished plate (port, outside face, front to the left), HDPE dark grey
t = trimesh.load("out_final/rov_side_plate_port.stl"); t.apply_translation(-t.bounds.mean(0))
v, f = np.asarray(t.vertices, np.float32), np.asarray(t.faces, np.uint32)
json.dump({"meshes": {"hdpe_901": {"v": base64.b64encode(v.tobytes()).decode(), "i": base64.b64encode(f.tobytes()).decode(),
                                   "color": 0x2c2f33, "label": "901"}},
           "instances": [{"k": "hdpe_901", "g": "part", "m": np.eye(4).flatten().tolist(), "ex": [0, 0, 0]}]},
          open(f"{RDIR}/parts901.json", "w"))
print("f_tile, f_nest written; parts901.json ready for render/views/plate.json")
