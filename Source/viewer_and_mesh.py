"""Refresh the 3D viewer's parts table and the positioned mesh assembly (CAD/STEP/TinkerSub_KB-1_assembly_mesh.3mf)."""
import html, json, collections, numpy as np, trimesh
import parts_final as PF
p = "rov_viewer_v6/index.html"; s = open(p).read()
rows = []
for proj, lst in (("TinkerSub_KB-1_Frame.3mf", PF.PRINTED_A), ("TinkerSub_KB-1_Core.3mf", PF.PRINTED_B)):
    rows.append(f'      <tr class="grp"><td colspan="5">{proj} ({sum(x[3] for x in lst)} parts)</td></tr>')
    sec = None
    for sc, stem, src, q, mat, note, use in lst:
        if sc != sec: rows.append(f'      <tr class="grp"><td colspan="5">{html.escape(sc)}</td></tr>'); sec = sc
        y = PF.is_yellow(stem)
        rows.append(f'      <tr><td><span class="pill {"p-y" if y else "p-k"}">{PF.pn(stem)}</span></td><td>{html.escape(use)}</td><td class="m">{stem}.stl</td><td class="q">{q}</td><td>{html.escape(note)}</td></tr>')
a = s.index("<tbody>"); b = s.index("</tbody>")
s = s[:a] + "<tbody>\n" + "\n".join(rows) + "\n    " + s[b:]
s = s.replace("parts in total", "parts in total", 1)
import re
s = re.sub(r"<span>\d+ parts in total</span>", f"<span>{sum(x[3] for x in PF.PRINTED)} parts in total</span>", s)
open(p, "w").write(s)

import rov_v6 as V6
from make_step import KEYMAP
d = json.load(open("rov_viewer_v6/assembly.json"))
Zup = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)
sc = trimesh.Scene(); cnt = collections.Counter(); base = {}
for k, M, g, ex in V6.inst:
    m, col, label = V6.parts[k]
    if k not in base:
        gm = m.to_mesh(); base[k] = trimesh.Trimesh(gm.vert_properties[:, :3], gm.tri_verts)
    t = base[k].copy(); t.apply_transform(Zup @ M)
    c = d["meshes"][k]["color"]; t.visual.face_colors = [(c >> 16) & 255, (c >> 8) & 255, c & 255, 255]
    v = KEYMAP.get(k, k); nm = (PF.PN.get(v, PF.PN_CUT.get(v, "")) + "_" + v).lstrip("_"); cnt[nm] += 1
    sc.add_geometry(t, geom_name=f"{g}/{nm}_{cnt[nm]}", node_name=f"{nm}_{cnt[nm]}")
sc.export("out_final/step/TinkerSub_KB-1_assembly_mesh.3mf"); print("mesh asm", len(sc.geometry))
