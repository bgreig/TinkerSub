"""
All printed ROV parts in one Bambu Studio project (.3mf), laid out on plates for a Bambu Lab A1 (256 x 256 mm).

Format follows Bambu Studio's own project files (production-extension sub-models, Metadata/model_settings.config
with <plate> entries, Metadata/project_settings.config). The project settings start from Bambu's own A1 project
template (resources/calib/.../auto_pa_line_single.3mf) cut down to one filament, then every key that exists in the
current system profiles (Bambu Lab A1 0.4 nozzle / 0.20mm Standard @BBL A1 / Bambu PETG Basic @BBL A1) is set to
that profile's value, so the presets load as the stock system presets.

usage: python3 make_3mf.py <template_project_settings.config> <flat_machine.json> <flat_process.json> <flat_filament.json> <out.3mf>
"""
import re
import sys, os, json, uuid, zipfile, io, datetime, copy
import numpy as np, trimesh
sys.path.insert(0, ".")
TEMPLATE, FM, FP, FF, OUT = sys.argv[1:6]
# FM == "-": TEMPLATE is already a finished Bambu project_settings.config (e.g. taken from an earlier project) and is used as-is.
# PLATE_PLAN env var: JSON file [[group name, [part numbers]], ...]. Each group gets its own plates, named after the group
# and the part numbers on that plate; groups never share a plate. Without it, plates follow the old section packing.
_argv = sys.argv; sys.argv = ["x", "/tmp/claude-0/-home-claude/b7c29eea-26f3-52c6-87fd-02a53346edd5/scratchpad/rovtest", "pkg"]
import importlib, os as _os
PRINTED = getattr(importlib.import_module(_os.environ.get("PRINTED_MOD", "build_guide")), _os.environ.get("PRINTED_ATTR", "PRINTED"))
sys.argv = _argv
BED, MARGIN, GAP = 256.0, 6.0, 8.0
def _base(stem): return stem.split("_", 1)[1] if stem[:3].isdigit() and stem[3:4] == "_" else stem
def PAD(stem):                                       # extra clearance round parts whose supports / brims spread past the part
    st = OBJ_SETTINGS.get(_base(stem), {}) if 'OBJ_SETTINGS' in globals() else {}
    if st.get("enable_support") == "1" or "cowl" in stem: return 20.0
    if st.get("brim_type", "") == "outer_only": return 2 * float(st.get("brim_width", "5"))   # brim on both sides
    return 0.0
STRIDE = BED * 1.2                                    # Bambu: plate stride = width * (1 + 1/5)
APP = "BambuStudio-02.00.02.01"
SECTION = {"Tools": "Thrusters"}
# per-object overrides (stored the way Bambu Studio stores object settings): 4 walls + 25 % gyroid for everything,
# brims on the tall thruster parts, tree supports under the prop blades
BASE_SETTINGS = {"wall_loops": "4", "sparse_infill_density": "25%", "sparse_infill_pattern": "gyroid"}
OBJ_SETTINGS = {
    "housing_no_foot": {**BASE_SETTINGS, "wall_loops": "5", "brim_type": "outer_only", "brim_width": "5"},
    "tail_cone_comp": {**BASE_SETTINGS, "wall_loops": "5", "brim_type": "outer_only", "brim_width": "5"},
    "prop_hub_RH": {**BASE_SETTINGS, "enable_support": "1", "support_type": "tree(auto)"},
    "prop_hub_LH": {**BASE_SETTINGS, "enable_support": "1", "support_type": "tree(auto)"},
    "rov_light_rear_body": {**BASE_SETTINGS, "wall_loops": "5"},
    "rov_light_front_ring": {**BASE_SETTINGS, "wall_loops": "5"},
    "rov_pod_endcap_3in": {**BASE_SETTINGS, "wall_loops": "5"},
    "rov_pod_flange_3in": {**BASE_SETTINGS, "wall_loops": "5"},
    "rov_endcap_rear_5hole": {**BASE_SETTINGS, "wall_loops": "5"},
    "coupler_gauge": {"wall_loops": "2", "sparse_infill_density": "15%"},
    "rov5_splice_strip_lower": {**BASE_SETTINGS, "sparse_infill_density": "100%"},
    "rov5_splice_strip_upper": {**BASE_SETTINGS, "sparse_infill_density": "100%"},
    "rov5_bracket_corner_a": {**BASE_SETTINGS, "wall_loops": "5", "sparse_infill_density": "40%"},
    "rov5_bracket_corner_b": {**BASE_SETTINGS, "wall_loops": "5", "sparse_infill_density": "40%"},
    "rov5_cowl_mid_port": {**BASE_SETTINGS, "enable_support": "1", "support_type": "tree(auto)"},
    "rov5_cowl_mid_stbd": {**BASE_SETTINGS, "enable_support": "1", "support_type": "tree(auto)"},
}                       # the coupler gauge rides along with the thruster parts
for _k in [k for k in OBJ_SETTINGS if k.startswith("rov5_")]: OBJ_SETTINGS["rov_" + _k[5:]] = OBJ_SETTINGS[_k]   # final names
for _k in ("rov_pod_endcap_3in_rear", "rov_pod_endcap_3in_front"): OBJ_SETTINGS[_k] = OBJ_SETTINGS["rov_pod_endcap_3in"]
# (2026-10-20) parts that hold water out under pressure print SOLID: at 25 % infill with 3-5 skin layers, water can seep
# through the skin into the infill and on past the O-rings. Hull flanges + rear cap, pod flanges + caps, light front ring.
SOLID = {**BASE_SETTINGS, "wall_loops": "5", "sparse_infill_density": "100%"}
for _k in ("br_flange_rear", "br_flange_front_dome", "rov_endcap_rear_5hole", "rov_pod_flange_3in",
           "rov_pod_endcap_3in", "rov_pod_endcap_3in_rear", "rov_pod_endcap_3in_front", "rov_light_front_ring"):
    OBJ_SETTINGS[_k] = SOLID
OBJ_SETTINGS.update({"rov_junction_box": {**BASE_SETTINGS, "wall_loops": "5"},
                     "pantilt_base": {**BASE_SETTINGS, "wall_loops": "5", "sparse_infill_density": "40%"},
                     "pantilt_yoke": {**BASE_SETTINGS, "wall_loops": "5", "sparse_infill_density": "40%"},
                     "pantilt_cradle": {**BASE_SETTINGS, "sparse_infill_density": "100%", "enable_support": "1", "support_type": "tree(auto)"},   # (2026-10-20) port cheek overhangs 9 mm at 28 mm
                     "pantilt_lever": {**BASE_SETTINGS, "sparse_infill_density": "100%"},
                     "sled_deck": {**BASE_SETTINGS, "sparse_infill_density": "40%"},
                     "rov_cell_plate_8_v2": {**BASE_SETTINGS, "wall_loops": "5"}})

# ------------------------------------------------------------------ project settings
def project_settings():
    if FM == "-": return json.load(open(TEMPLATE))
    t = json.load(open(TEMPLATE))
    nf = len(t["filament_colour"])
    out = {}
    for k, v in t.items():                            # cut every per-filament array down to one filament
        if isinstance(v, list):
            if len(v) == nf: v = v[:1]
            elif len(v) == nf * nf: v = v[:1]
            elif len(v) == nf * 2: v = v[:2]
            elif len(v) == nf + 2: v = v[:3]
        out[k] = v
    meta = {"name", "inherits", "from", "type", "setting_id", "instantiation", "version", "description",
            "compatible_printers", "compatible_printers_condition", "compatible_prints", "compatible_prints_condition",
            "filament_id", "is_custom_defined", "renamed_from", "base_id"}
    changed, skipped = 0, []
    for path in (FM, FP, FF):
        prof = json.load(open(path))
        for k, v in prof.items():
            if k in meta or k not in out: continue
            cur = out[k]
            if isinstance(cur, list) and isinstance(v, list):
                if len(v) == len(cur): out[k] = v
                elif len(v) > len(cur): out[k] = v[:len(cur)]
                else: skipped.append(k); continue
            elif isinstance(cur, list) != isinstance(v, list):
                skipped.append(k); continue
            else:
                out[k] = v
            changed += 1
    ff = json.load(open(FF))
    out["filament_settings_id"] = [ff["name"]]
    out["filament_colour"] = ["#5B6670"]
    if "filament_ids" in out: out["filament_ids"] = [ff.get("filament_id", out["filament_ids"][0])]
    out["different_settings_to_system"] = ["", "", ""]
    if "inherits_group" in out: out["inherits_group"] = ["", "", ""]
    out["printer_settings_id"] = json.load(open(FM))["name"]
    out["print_settings_id"] = json.load(open(FP))["name"]
    out["name"], out["from"], out["version"] = "project_settings", "project", APP.split("-")[1]
    print(f"project settings: {len(out)} keys, {changed} set from system profiles, skipped {skipped}")
    return out

# ------------------------------------------------------------------ packing (MaxRects, best short side fit, 90 deg rotation)
class Bin:
    def __init__(s, w, h): s.free = [(0.0, 0.0, w, h)]; s.used = []
    def insert(s, w, h):
        best = None
        for (fx, fy, fw, fh) in s.free:
            for (rw, rh, rot) in ((w, h, False), (h, w, True)):
                if rw <= fw + 1e-6 and rh <= fh + 1e-6:
                    score = (min(fw - rw, fh - rh), max(fw - rw, fh - rh))
                    if best is None or score < best[0]: best = (score, fx, fy, rw, rh, rot)
        if best is None: return None
        _, x, y, rw, rh, rot = best
        s._split(x, y, rw, rh); s.used.append((x, y, rw, rh)); return x, y, rot
    def _split(s, x, y, w, h):
        nf = []
        for (fx, fy, fw, fh) in s.free:
            if x >= fx + fw or x + w <= fx or y >= fy + fh or y + h <= fy: nf.append((fx, fy, fw, fh)); continue
            if x > fx: nf.append((fx, fy, x - fx, fh))
            if x + w < fx + fw: nf.append((x + w, fy, fx + fw - x - w, fh))
            if y > fy: nf.append((fx, fy, fw, y - fy))
            if y + h < fy + fh: nf.append((fx, y + h, fw, fy + fh - y - h))
        s.free = [a for i, a in enumerate(nf) if not any(i != j and a[0] >= b[0] - 1e-6 and a[1] >= b[1] - 1e-6 and
                  a[0] + a[2] <= b[0] + b[2] + 1e-6 and a[1] + a[3] <= b[1] + b[3] + 1e-6 and (a != b or j < i)
                  for j, b in enumerate(nf))]

def load_mesh(src, stem):
    t = trimesh.load(f"{src}/{stem}.stl")
    c = t.bounds.mean(0); t.apply_translation([-c[0], -c[1], -t.bounds[0, 2]])
    return t

# ------------------------------------------------------------------ build
def main():
    meshes, items = {}, []
    for sec, stem, src, qty, mat, note, use in PRINTED:
        meshes[stem] = load_mesh(src, stem)
        for q in range(qty): items.append((sec, stem, q + 1, qty))
    # one group of plates per section, sections in build-guide order
    order = []
    for sec, *_ in PRINTED:
        sec = SECTION.get(sec, sec)
        if sec not in order: order.append(sec)
    plates = []                                       # (name, [(stem, label, x, y, rot)])
    usable = BED - 2 * MARGIN
    def pack(its):
        bins = []
        for _, stem, n, qty in its:
            ex = meshes[stem].extents
            w, h = ex[0] + GAP + PAD(stem), ex[1] + GAP + PAD(stem)
            if max(ex[0], ex[1]) > usable:            # oversize part (skid bracket body): its own plate, centred
                nb = Bin(0, 0); nb.full = True
                bins.append((nb, [(stem, n, qty, (usable - ex[0]) / 2 - GAP / 2 + GAP / 2, (usable - ex[1]) / 2, False)]))
                continue
            for b in bins:
                if getattr(b[0], "full", False): continue
                r = b[0].insert(w, h)
                if r: b[1].append((stem, n, qty, *r)); break
            else:
                nb = Bin(usable + GAP, usable + GAP); r = nb.insert(w, h)
                assert r, f"{stem} does not fit the bed"
                bins.append((nb, [(stem, n, qty, *r)]))
        return bins
    keys = [lambda e: -e[0] * e[1], lambda e: -max(e[0], e[1]), lambda e: -min(e[0], e[1]), lambda e: -(e[0] + e[1])]
    PLAN = json.load(open(os.environ["PLATE_PLAN"])) if os.environ.get("PLATE_PLAN") else None
    if PLAN:
        pn_of = lambda stem: stem[:3]
        listed = [p[:3] for _, pns in PLAN for p in pns]
        missing = sorted({pn_of(st) for _, st, *_ in items} - set(listed))
        assert not missing, f"parts not in the plate plan: {missing}"
        taken = set()                                 # "105*3" in a group = the next 3 copies of part 105 not yet placed
        for gname, pns in PLAN:
            its = []
            for p in pns:
                pn, k = (p.split("*")[0], int(p.split("*")[1])) if "*" in p else (p, 999)
                for it in items:
                    if pn_of(it[1]) == pn and (it[1], it[2]) not in taken and k > 0:
                        its.append(it); taken.add((it[1], it[2])); k -= 1
            pns = [p[:3] for p in pns]
            if not its: continue
            best = None
            for kf in keys:
                trial = pack(sorted(its, key=lambda it: (pns.index(pn_of(it[1])), kf(meshes[it[1]].extents[:2]))))
                trial2 = pack(sorted(its, key=lambda it: kf(meshes[it[1]].extents[:2])))
                for t in (trial, trial2):
                    if best is None or len(t) < len(best): best = t
            for i, (bn, placed) in enumerate(best):
                cnt = {}
                for st, *_ in placed: cnt[pn_of(st)] = cnt.get(pn_of(st), 0) + 1
                tag = ", ".join(f"{p}" + (f" x{c}" if c > 1 else "") for p, c in sorted(cnt.items()))
                plates.append((f"{gname} ({i + 1} of {len(best)}) - {tag}" if len(best) > 1 else f"{gname} - {tag}", placed, bn))
        assert len(taken) == len(items), "plate plan leaves parts unplaced"
        order = []                                    # skip the section packing below
    for sec in order:
        its = [it for it in items if SECTION.get(it[0], it[0]) == sec]
        best = None
        for kf in keys:
            trial = pack(sorted(its, key=lambda it: kf(meshes[it[1]].extents[:2])))
            if best is None or len(trial) < len(best): best = trial
        bins = best
        for i, (bn, placed) in enumerate(bins):
            plates.append((f"{sec} {i + 1}" if len(bins) > 1 else sec, placed, bn))
    # gather nearly empty plates (< 25 % used) into shared "Mixed" plates
    def fill(pl): return sum(meshes[st].extents[0] * meshes[st].extents[1] for st, *_ in pl[1]) / (usable * usable)
    def yel(pl): return any('cowl' in st for st, *_ in pl[1])     # yellow (cowl) parts never share a plate with black ones
    sparse = [pl for pl in plates if fill(pl) < 0.35 and not yel(pl) and not any(max(meshes[st].extents[:2]) > usable for st, *_ in pl[1])]
    if len(sparse) > 1 and not PLAN:
        plates = [pl for pl in plates if pl not in sparse]
        its = [(None, st, k, q) for _, placed, _b in sparse for st, k, q, *_ in placed]
        best = None
        for kf in keys:
            trial = pack(sorted(its, key=lambda it: kf(meshes[it[1]].extents[:2])))
            if best is None or len(trial) < len(best): best = trial
        for i, (bn, placed) in enumerate(best):
            plates.append((f"Mixed {i + 1}" if len(best) > 1 else "Mixed", placed, bn))
    # absorb plates with 1-2 small parts into free space on other plates
    for pl in sorted(plates, key=lambda pl: len(pl[1])):
        if PLAN or len(pl[1]) > 2 or len(plates) < 2: continue
        moves = []
        for it in pl[1]:
            st = it[0]; ex = meshes[st].extents
            for other in plates:
                if other is pl or getattr(other[2], "full", False) or yel(other) != ("cowl" in st): continue
                r = other[2].insert(ex[0] + GAP + PAD(st), ex[1] + GAP + PAD(st))
                if r: moves.append((other, (st, it[1], it[2], *r))); break
            else: break
        if len(moves) == len(pl[1]):
            for other, it in moves: other[1].append(it)
            plates.remove(pl)
    import re as _re                                  # renumber plate names per section after merging
    base = [pl[0] if PLAN else _re.sub(r" \d+$", "", pl[0]) for pl in plates]
    cnt = {b: base.count(b) for b in base}; seen = {}
    for i, pl in enumerate(plates):
        b = base[i]; seen[b] = seen.get(b, 0) + 1
        plates[i] = (f"{b} {seen[b]}" if cnt[b] > 1 else b, pl[1], pl[2])
    n = len(plates)
    v = np.sqrt(n); cols = int(round(v)) + (1 if v > round(v) else 0)

    model_files, root_objs, build_items, cfg_objs, cfg_plates = {}, [], [], [], []
    sub_id = {stem: i + 1 for i, stem in enumerate(meshes)}
    for stem, m in meshes.items():                    # one sub-model per unique part
        i = sub_id[stem]
        vtx = "\n".join(f'     <vertex x="{a:.4f}" y="{b:.4f}" z="{c:.4f}"/>' for a, b, c in m.vertices)
        tri = "\n".join(f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in m.faces)
        model_files[f"3D/Objects/object_{i}.model"] = (
            '<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
            'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
            'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">\n'
            ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n <resources>\n'
            f'  <object id="{i}" p:UUID="{uuid.uuid4()}" type="model">\n   <mesh>\n    <vertices>\n{vtx}\n    </vertices>\n'
            f'    <triangles>\n{tri}\n    </triangles>\n   </mesh>\n  </object>\n </resources>\n <build/>\n</model>\n')
    next_id, ident = len(meshes) + 1, 100
    placed_check = []
    for pi, (pname, placed, _) in enumerate(plates):
        row, col = pi // cols, pi % cols
        ox, oy = col * STRIDE, -row * STRIDE
        inst = []
        fp = []                                       # footprints incl. brim / support clearance, to centre the group
        for stem, k, qty, x, y, rot in placed:
            ex = meshes[stem].extents; w, h = (ex[1], ex[0]) if rot else (ex[0], ex[1])
            fp.append((x, y, x + w + PAD(stem), y + h + PAD(stem)))
        usable = BED - 2 * MARGIN
        dx = (usable - (max(f[2] for f in fp) - min(f[0] for f in fp))) / 2 - min(f[0] for f in fp)
        dy = (usable - (max(f[3] for f in fp) - min(f[1] for f in fp))) / 2 - min(f[1] for f in fp)
        for stem, k, qty, x, y, rot in placed:
            m = meshes[stem]; ex = m.extents
            w, h = (ex[1], ex[0]) if rot else (ex[0], ex[1])
            cx = ox + MARGIN + dx + x + (w + PAD(stem)) / 2; cy = oy + MARGIN + dy + y + (h + PAD(stem)) / 2
            R = "0 1 0 -1 0 0 0 0 1" if rot else "1 0 0 0 1 0 0 0 1"
            oid = next_id; next_id += 1; ident += 1
            label = f"{stem}" + (f" ({k} of {qty})" if qty > 1 else "")
            root_objs.append(f'  <object id="{oid}" p:UUID="{uuid.uuid4()}" type="model">\n   <components>\n'
                             f'    <component p:path="/3D/Objects/object_{sub_id[stem]}.model" objectid="{sub_id[stem]}" '
                             f'p:UUID="{uuid.uuid4()}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>\n   </components>\n  </object>')
            build_items.append(f'  <item objectid="{oid}" p:UUID="{uuid.uuid4()}" transform="{R} {cx:.4f} {cy:.4f} 0" printable="1"/>')
            extra = "".join(f'    <metadata key="{k}" value="{v}"/>\n' for k, v in OBJ_SETTINGS.get(_base(stem), {**BASE_SETTINGS, "sparse_infill_density": "40%"} if stem.startswith("rov5_plate") else BASE_SETTINGS).items())
            cfg_objs.append(f'  <object id="{oid}">\n    <metadata key="name" value="{label}"/>\n    <metadata key="extruder" value="1"/>\n' + extra +
                            f'    <metadata face_count="{len(m.faces)}"/>\n    <part id="{sub_id[stem]}" subtype="normal_part">\n'
                            f'      <metadata key="name" value="{stem}"/>\n'
                            f'      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>\n'
                            f'      <metadata key="source_file" value="{stem}.stl"/>\n'
                            f'      <metadata key="source_object_id" value="0"/>\n      <metadata key="source_volume_id" value="0"/>\n'
                            f'      <mesh_stat face_count="{len(m.faces)}" edges_fixed="0" degenerate_facets="0" facets_removed="0" '
                            f'facets_reversed="0" backwards_edges="0"/>\n    </part>\n  </object>')
            inst.append(f'    <model_instance>\n      <metadata key="object_id" value="{oid}"/>\n'
                        f'      <metadata key="instance_id" value="0"/>\n      <metadata key="identify_id" value="{ident}"/>\n    </model_instance>')
            # bounds check in plate coordinates
            placed_check.append((pi, stem, cx - ox - w/2, cx - ox + w/2, cy - oy - h/2, cy - oy + h/2))
        pname = re.sub(r'[<>:/\\|?*"]', "-", pname)        # Bambu Studio rejects these characters in names
        cfg_plates.append(f'  <plate>\n    <metadata key="plater_id" value="{pi + 1}"/>\n    <metadata key="plater_name" value="{pname}"/>\n'
                          f'    <metadata key="locked" value="false"/>\n' + "\n".join(inst) + "\n  </plate>")
    for pi, stem, x0, x1, y0, y1 in placed_check:
        assert x0 >= 3 and y0 >= 3 and x1 <= BED - 3 and y1 <= BED - 3, (pi, stem, x0, x1, y0, y1)
    # overlap check per plate
    for pi in range(n):
        r = [c for c in placed_check if c[0] == pi]
        for a in range(len(r)):
            for b in range(a + 1, len(r)):
                A, B = r[a], r[b]
                assert A[2] >= B[3] or B[2] >= A[3] or A[4] >= B[5] or B[4] >= A[5], ("overlap", A, B)

    today = datetime.date.today().isoformat()
    root = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
            'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
            'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">\n'
            f' <metadata name="Application">{APP}</metadata>\n <metadata name="BambuStudio:3mfVersion">1</metadata>\n'
            f' <metadata name="CreationDate">{today}</metadata>\n <metadata name="ModificationDate">{today}</metadata>\n'
            ' <metadata name="Title">TinkerSub KB-1 printed parts</metadata>\n <metadata name="Designer">Brian</metadata>\n'
            ' <resources>\n' + "\n".join(root_objs) + '\n </resources>\n'
            f' <build p:UUID="{uuid.uuid4()}">\n' + "\n".join(build_items) + '\n </build>\n</model>\n')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n' +
            "\n".join(f' <Relationship Target="/{p}" Id="rel-{i + 1}" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
                      for i, p in enumerate(model_files)) + '\n</Relationships>\n')
    cfg = '<?xml version="1.0" encoding="UTF-8"?>\n<config>\n' + "\n".join(cfg_objs) + "\n" + "\n".join(cfg_plates) + "\n</config>\n"
    ctypes = ('<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
              ' <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
              ' <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n'
              ' <Default Extension="png" ContentType="image/png"/>\n'
              ' <Default Extension="gcode" ContentType="text/x.gcode"/>\n</Types>\n')
    toprels = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
               ' <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n</Relationships>\n')
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctypes)
        z.writestr("_rels/.rels", toprels)
        z.writestr("3D/3dmodel.model", root)
        z.writestr("3D/_rels/3dmodel.model.rels", rels)
        for p, s in model_files.items(): z.writestr(p, s)
        z.writestr("Metadata/model_settings.config", cfg)
        z.writestr("Metadata/project_settings.config", json.dumps(project_settings(), indent=4))
    print(f"{OUT}: {len(build_items)} parts on {n} plates ({cols} columns)")
    for pi, (pname, placed, _) in enumerate(plates):
        print(f"  plate {pi + 1:2d}  {pname:20s} " + ", ".join(f"{s}" for s, *_ in placed))
    json.dump([(p, [s for s, *_ in pl]) for p, pl, _ in plates], open(OUT + ".plates.json", "w"))

if __name__ == "__main__":
    main()
