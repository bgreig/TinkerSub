#!/usr/bin/env python3
"""
TinkerSub KB-1: one entry point for everything generated from this folder.

    python3 Source/build.py all              every step below except step (STEP export is slow); then check
    python3 Source/build.py all --step       the same, plus the STEP files
    python3 Source/build.py parts            one step (or several: parts plates 3mf)
    python3 Source/build.py check            compare the build with the repository
    python3 Source/build.py install          copy what changed into the repository

Steps, in order (each uses what the steps before it wrote, in the build folder):
    parts     printed parts: generate, assemble (with the interference check), name, number and label -> out_lbl/,
              then the fastener check (below)
    fasteners every screw hole in the assembled ROV followed through every part: the screw in assembly/fasteners.py must
              go in, reach its thread without bottoming out, and have room for its head and nut; every joint and hole
              must be accounted for, and the shopping list and guide text must name the same screws. Stops the build.
    plates    HDPE side plates: DXFs, cutting templates, plate STLs -> out_final/
    3mf       Bambu Studio projects (Frame, Core, Reprint) and their plate maps -> outdir/
    step      STEP files for Fusion 360 and other CAD apps -> out_final/step/  (slow: run it on its own or with --step)
    figures   drawn figures: thruster layout, pan-tilt fit, side-plate figures, schematics, wiring diagram, wire list
    scenes    3D scenes for the renders (assembly, lights, electronics, insert map, single parts) -> render/
    renders   every view in render/views/*.json, in headless Chromium -> render/final/crop/
    guide     the assembly guide PDF and the whole generated package -> outdir/TinkerSub_KB-1_Build_Package/
              Pictures not regenerated in this run are carried over from the repository's Images/ (so `guide` alone
              rebuilds the guide after a text change, as long as parts, plates and 3mf have run).
    check     compare the generated package with the repository, file by file (see below)
    install   copy changed and new generated files into the repository; never deletes anything

The build folder is Source/build/ (git-ignored); --build DIR picks another. Inputs (Source/inputs/) are copied into it first.
Needs Python 3.11+ and `pip install -r Source/requirements.txt`; renders and schematics need `playwright install chromium`.
"""
import os, sys, glob, json, shutil, subprocess, time, argparse, zipfile, re

SRC = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SRC)
CODE = [os.path.join(SRC, d) for d in ("geometry", "assembly", "outputs", "checks", "guide")]
FP = "TinkerSub_KB-1"
STEPS = ["parts", "fasteners", "plates", "3mf", "step", "figures", "scenes", "renders", "guide", "check"]

def log(*a): print(*a, flush=True)

class Build:
    def __init__(self, bdir):
        self.b = os.path.abspath(bdir)
        os.makedirs(self.b, exist_ok=True)
        self.env = {**os.environ, "PYTHONPATH": os.pathsep.join(CODE + [os.environ.get("PYTHONPATH", "")]).rstrip(os.pathsep),
                    "PYTHONDONTWRITEBYTECODE": "1", "MPLBACKEND": "Agg"}
        self.fresh = set()                       # build-relative picture paths regenerated in this run

    def p(self, *a): return os.path.join(self.b, *a)

    def run(self, script, *args, cwd=None, env=None):
        """run a script from one of the code folders (or python -c ...) with the build folder as working directory"""
        if script == "-c": cmd = [sys.executable, "-c", *args]
        else:
            path = next((os.path.join(d, script) for d in CODE + [os.path.join(SRC, "render")] if os.path.exists(os.path.join(d, script))), None)
            if not path: sys.exit(f"build.py: no script {script}")
            cmd = [sys.executable, path, *args]
        t0 = time.time()
        r = subprocess.run(cmd, cwd=cwd or self.b, env={**self.env, **(env or {})}, capture_output=True, text=True)
        logf = self.p("logs", re.sub(r"\W", "_", script if script != "-c" else args[0][:30]) + ".log")
        os.makedirs(os.path.dirname(logf), exist_ok=True)
        open(logf, "a").write(f"$ {' '.join(cmd)}\n{r.stdout}{r.stderr}\n")
        if r.returncode:
            sys.stderr.write(r.stdout[-3000:] + r.stderr[-3000:])
            sys.exit(f"build.py: {script} failed (log: {logf})")
        log(f"    {script if script != '-c' else 'python -c'} {' '.join(a for a in args if script != '-c')}  ({time.time() - t0:.0f} s)")
        return r.stdout

    def inputs(self):
        for d in ("New_parts", "src_parts", "prep", "rov_project", "step_supplied"):
            shutil.copytree(os.path.join(SRC, "inputs", d), self.p(d), dirs_exist_ok=True)
        for d in ("out", "out_v5", "out_final", "out_lbl", "outdir", "rov_viewer", "render/final/crop", "render/crop"):
            os.makedirs(self.p(d), exist_ok=True)
        for f in glob.glob(os.path.join(SRC, "render", "*.*")):          # the render pages and their drivers
            shutil.copy(f, self.p("render"))

    # ------------------------------------------------------------------ steps
    def parts(self):
        for s in ("thruster.py", "pylon.py", "export_v4.py", "jbox.py", "export_v5.py", "export_v6.py"): self.run(s)
        self.run("-c", "import pantilt_fit as P; P.export('prep')")
        out = self.run("rov_v6.py")
        hit = [l for l in out.splitlines() if "interferences" in l]
        log("    " + (hit[0] if hit else "interference check: no result line"))
        if hit and not hit[0].rstrip().endswith("none"): log("    !! parts overlap in the assembly: see logs/rov_v6_py.log")
        self.run("parts_final.py")
        out = self.run("label_parts.py")
        if "issues: 0" not in out: log("    !! label_parts reported issues: see logs/label_parts_py.log")
        self.fasteners()

    def fasteners(self):
        """every screw joint in the assembled model against assembly/fasteners.py: stops the build on any error"""
        cmd = [sys.executable, os.path.join(SRC, "checks", "fastener_check.py"), "fastener_report.json"]
        t0 = time.time()
        r = subprocess.run(cmd, cwd=self.b, env=self.env, capture_output=True, text=True)
        open(self.p("logs", "fastener_check.log"), "w").write(r.stdout + r.stderr)
        tail = [l for l in r.stdout.splitlines() if l.startswith(("ERROR", "warning", "fastener check"))]
        for l in tail[:40]: log("    " + l)
        if len(tail) > 40: log(f"    ... {len(tail) - 40} more in logs/fastener_check.log")
        if r.returncode:
            sys.exit("build.py: the fastener check failed (logs/fastener_check.log, fastener_report.json). Fix the model or "
                     "assembly/fasteners.py: every screw must fit before anything is built from it.")
        log(f"    (fastener check {time.time() - t0:.0f} s)")

    def plates(self):
        self.run("plate_templates_final.py"); self.run("plate_stl_final.py")

    def threemf(self):
        o = os.path.join(SRC, "outputs")
        for name, plan, mod, attr in (("Core", "plates_core.json", "parts_final", "PRINTED_B"), ("Frame", "plates_frame.json", "parts_final", "PRINTED_A"),
                                      ("Reprint_2026-10-20", "plates_reprint.json", "reprint_parts", "PRINTED_R")):
            self.run("make_3mf.py", os.path.join(o, "ps.json"), "-", "-", "-", f"outdir/ROV_{name}.3mf",
                     env={"PLATE_PLAN": os.path.join(o, plan), "PRINTED_MOD": mod, "PRINTED_ATTR": attr})
        for n in ("Core", "Frame"):
            self.run("plate_preview.py", f"outdir/ROV_{n}.3mf", f"outdir/ROV_{n}_plates.png"); self.fresh.add(f"outdir/ROV_{n}_plates.png")

    def step(self):
        self.run("make_step.py", "parts"); self.run("make_step.py", "asm", "rov_viewer/assembly_v6.json"); self.run("viewer_and_mesh.py")

    def figures(self):
        crop = "render/final/crop"
        self.run("scene_final.py", "render")                       # also writes the assembly scene + thruster mixing table
        shutil.copy(self.p("render/crop/f_layout.png"), self.p(crop, "f_layout.png"))
        shutil.copy(self.p("render/mix_final.json"), self.p("render/final/mix_final.json"))
        self.run("pantilt_fig.py", f"{crop}/f_pantilt_fit.png")
        self.run("plate_figs.py", crop, "render")
        os.makedirs(self.p("render/elec"), exist_ok=True)
        self.run("elec_drawings.py", "render/elec")
        for n in ("elec_sch1", "elec_sch2", "elec_wiring"): shutil.copy(self.p("render/elec", n + ".png"), self.p(crop, f"f_{n}.png"))
        shutil.copy(self.p("render/elec/elec_wires.json"), self.p("render/elec_wires.json"))
        self.fresh |= {f"{crop}/{f}.png" for f in ("f_layout", "f_pantilt_fit", "f_nest", "f_tile", "f_elec_sch1", "f_elec_sch2", "f_elec_wiring")}
        os.makedirs(self.p("out"), exist_ok=True)
        self.run("comp_fig.py", "out/compensator_section.png"); self.fresh.add("out/compensator_section.png")

    def scenes(self):
        if not os.path.exists(self.p("render/asm.json")): self.run("scene_final.py", "render")
        self.run("light_scene.py", "render/asm.json", "render")
        self.run("elec_scene.py", "rov_viewer/assembly_v6.json", "render")
        self.run("insert_map.py", "out_lbl", "render", "render/inserts.json")
        self.run("part_scenes.py", "out_lbl", "render")
        if not os.path.exists(self.p("render/parts901.json")): self.run("plate_figs.py", "render/final/crop", "render")

    def renders(self):
        out = self.p("render/out"); os.makedirs(out, exist_ok=True)
        for vf in sorted(glob.glob(os.path.join(SRC, "render", "views", "*.json"))):
            drv = "shoot_real.py" if os.path.basename(vf) == "electronics.json" else "shoot.py"
            self.run(drv, vf, out, cwd=self.p("render"))
            for name in json.load(open(vf)):
                crop = name if name.startswith(("f_", "pf_")) else "f_" + name
                shutil.copy(os.path.join(out, name + ".png"), self.p("render/final/crop", crop + ".png"))
                self.fresh.add(f"render/final/crop/{crop}.png")

    def guide(self):
        sys.path[:0] = CODE
        import package_images as PI
        stems = json.loads(self.run("-c", "import json, parts_final as P; print(json.dumps([p[1] for p in P.PRINTED]))").strip().splitlines()[-1])
        n = 0
        for bpath, pkpath in PI.image_map(stems):           # pictures this run did not make: from the repository
            if bpath in self.fresh and os.path.exists(self.p(bpath)): continue
            src = os.path.join(ROOT, pkpath)
            if not os.path.exists(src): sys.exit(f"build.py guide: {bpath} was not regenerated and {pkpath} is not in the repository")
            os.makedirs(os.path.dirname(self.p(bpath)), exist_ok=True); shutil.copy(src, self.p(bpath)); n += 1
        log(f"    {n} pictures carried over from the repository, {len(self.fresh)} regenerated")
        for n_ in ("Frame", "Core"):                        # projects and plate maps, if 3mf did not run
            if not os.path.exists(self.p(f"outdir/ROV_{n_}.3mf")): shutil.copy(os.path.join(ROOT, f"{FP}_{n_}.3mf"), self.p(f"outdir/ROV_{n_}.3mf"))
        for f in glob.glob(os.path.join(ROOT, f"{FP}_Reprint_*.3mf")):
            b = self.p("outdir", os.path.basename(f).replace(FP + "_", "ROV_"))
            if not os.path.exists(b): shutil.copy(f, b)
        if not os.path.exists(self.p("render/final/mix_final.json")):
            self.run("scene_final.py", "render"); shutil.copy(self.p("render/mix_final.json"), self.p("render/final/mix_final.json"))
        if not os.path.exists(self.p("render/elec_wires.json")):    # wire list back from the repository's CSV
            import csv
            rows = list(csv.reader(open(os.path.join(ROOT, "Wire_list.csv"))))[1:]
            json.dump([[int(r[0]), r[1], r[2], r[3]] for r in rows], open(self.p("render/elec_wires.json"), "w"))
        if not os.path.exists(self.p("render/inserts.json")): self.run("insert_map.py", "out_lbl", "render", "render/inserts.json")
        import trimesh                                      # part volumes (labelled parts, as printed) for the filament estimates
        vols = {}
        for st in stems:
            t = trimesh.load(self.p("out_lbl", st + ".stl")); vols[st] = [t.volume / 1000, list(map(float, t.extents))]
        json.dump(vols, open(self.p("render/vols.json"), "w"))
        ev = json.load(open(os.path.join(SRC, "render", "views", "electronics.json")))       # callout keys under the electronics pictures
        json.dump({k: [l[2] for l in v.get("labels", []) if l[1] != "C"] for k, v in ev.items()}, open(self.p("render/elec_legends.json"), "w"), indent=1)
        if os.path.exists(self.p("outdir", f"{FP}_Build_Package")): shutil.rmtree(self.p("outdir", f"{FP}_Build_Package"))
        self.run("build_guide_final.py", "render/final", "outdir")

    # ------------------------------------------------------------------ check / install
    def pkg(self): return self.p("outdir", f"{FP}_Build_Package")

    def check(self, quiet=False):
        if not os.path.isdir(self.pkg()): sys.exit("build.py check: no package yet (run the guide step)")
        res = {"same": [], "equivalent": [], "changed": [], "new": []}
        for dp, _, fs in os.walk(self.pkg()):
            for f in fs:
                rel = os.path.relpath(os.path.join(dp, f), self.pkg()); repo = os.path.join(ROOT, rel)
                if not os.path.exists(repo): res["new"].append((rel, "")); continue
                kind, why = compare(os.path.join(dp, f), repo)
                res[kind].append((rel, why))
        log(f"    same {len(res['same'])}, equivalent {len(res['equivalent'])}, changed {len(res['changed'])}, new {len(res['new'])}")
        for k in ("equivalent", "changed", "new"):
            for rel, why in sorted(res[k]): log(f"    {k:10s} {rel}" + (f"  ({why})" if why else ""))
        json.dump(res, open(self.p("check.json"), "w"), indent=1)
        return res

    def install(self):
        res = self.check()
        for rel, _ in res["changed"] + res["new"]:
            dst = os.path.join(ROOT, rel); os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy(os.path.join(self.pkg(), rel), dst); log(f"    installed {rel}")
        log(f"    {len(res['changed']) + len(res['new'])} files written to {ROOT}; equivalent files left as they are")

# ------------------------------------------------------------------ comparisons
def _stl(p):
    import numpy as np
    d = open(p, "rb").read(); n = int.from_bytes(d[80:84], "little")
    return np.frombuffer(d[84:84 + n * 50], dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))

def _step_colours(s):
    """{solid entity: rgb} from the styling section of a STEP file (whitespace already removed)"""
    tail = s[s.find(b"STYLED_ITEM") - 20:]
    ent = dict(re.findall(rb"#(\d+)=(.*?);(?=#|ENDSEC)", tail))
    def rgb(e, depth=0):
        t = ent.get(e, b""); m = re.search(rb"COLOUR_RGB\('',([^)]*)\)", t)
        if m: return tuple(round(float(v), 4) for v in m.group(1).split(b","))
        for r in (re.findall(rb"#(\d+)", t) if depth < 8 else []):
            c = rgb(r, depth + 1)
            if c: return c
    return {m.group(2): rgb(m.group(1)) for t in ent.values() for m in [re.match(rb"STYLED_ITEM\('color',\(#(\d+)\),#(\d+)\)", t)] if m}

def compare(a, b):
    """('same' | 'equivalent' | 'changed', reason). Equivalent = only file metadata, IDs, dates or float rounding differ."""
    if open(a, "rb").read() == open(b, "rb").read(): return "same", ""
    ext = os.path.splitext(a)[1].lower()
    try:
        if ext == ".stl":
            import numpy as np
            x, y = _stl(a), _stl(b)
            if len(x) == len(y):
                dv = float(np.abs(x["v"] - y["v"]).max())
                if dv <= 1e-4: return "equivalent", f"float rounding, max {dv * 1000:.3f} um"
            return "changed", "geometry"
        if ext == ".png":
            import numpy as np
            from PIL import Image
            x, y = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
            if x.size != y.size: return "changed", f"size {y.size} -> {x.size}"
            dd = np.abs(np.asarray(x, int) - np.asarray(y, int)).sum(2)
            return ("equivalent", "same pixels") if not dd.any() else ("changed", f"{int((dd > 0).sum())} pixels")
        if ext == ".3mf":
            U = re.compile(rb"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"); D = re.compile(rb"20\d\d-\d\d-\d\d")
            N = re.compile(rb"-?\d+\.\d+")
            za, zb = zipfile.ZipFile(a), zipfile.ZipFile(b)
            if sorted(za.namelist()) != sorted(zb.namelist()): return "changed", "contents"
            fl = False
            for n in za.namelist():
                x, y = D.sub(b"D", U.sub(b"U", za.read(n))), D.sub(b"D", U.sub(b"U", zb.read(n)))
                if x == y: continue
                if N.sub(b"#", x) != N.sub(b"#", y): return "changed", n
                if max(abs(float(p) - float(q)) for p, q in zip(N.findall(x), N.findall(y))) > 1e-3: return "changed", n
                fl = True
            return "equivalent", "float rounding" if fl else "IDs / dates"
        if ext == ".step":
            def norm(p):
                s = open(p, "rb").read()
                return re.sub(rb"Open CASCADE STEP translator \d+\.\d+ \d+", b"OCC", re.sub(rb"FILE_NAME\([^;]*;", b"FILE_NAME;", s))
            x, y = norm(a), norm(b)
            if x == y: return "equivalent", "header"
            x, y = re.sub(rb"\s+", b"", x), re.sub(rb"\s+", b"", y)      # line breaks move with number lengths
            N = re.compile(rb"-?\d+\.\d*(?:E[-+]?\d+)?")
            if N.sub(b"#", x) == N.sub(b"#", y) and max(abs(float(p) - float(q)) for p, q in zip(N.findall(x), N.findall(y))) <= 1e-3:
                return "equivalent", "float rounding"
            def sty(t): k = t.find(b"MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION"); return k if k > 0 else t.find(b"STYLED_ITEM")
            i, j = sty(x), sty(y)                                       # same solids, colour table written in another order?
            if i > 0 and x[:x.rfind(b"#", 0, i)] == y[:y.rfind(b"#", 0, j)] and _step_colours(x) == _step_colours(y):
                return "equivalent", "colour table order"
            return "changed", "geometry"
        if ext == ".dxf":
            import ezdxf
            def ents(p):
                out = []
                for e in ezdxf.readfile(p).modelspace():
                    d = e.dxfattribs(); d.pop("handle", None); d.pop("owner", None)
                    pts = [tuple(round(c, 6) for c in q) for q in e.get_points()] if e.dxftype() == "LWPOLYLINE" else None
                    out.append((e.dxftype(), repr(sorted((k, str(v)) for k, v in d.items())), repr(pts)))
                return out
            return ("equivalent", "header") if ents(a) == ents(b) else ("changed", "entities")
        if ext == ".pdf":
            import pymupdf
            A, B = pymupdf.open(a), pymupdf.open(b)
            if len(A) != len(B): return "changed", f"{len(B)} -> {len(A)} pages"
            pages = [i + 1 for i, (p, q) in enumerate(zip(A, B))
                     if p.get_text() != q.get_text() or p.get_pixmap(dpi=50).samples != q.get_pixmap(dpi=50).samples]
            return ("equivalent", "metadata") if not pages else ("changed", "pages " + ", ".join(map(str, pages[:20])) + (" ..." if len(pages) > 20 else ""))
    except Exception as e:
        return "changed", f"could not compare: {e}"
    return "changed", ""

# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("steps", nargs="+", help="all, a step name, check or install")
    ap.add_argument("--build", default=os.path.join(SRC, "build"), help="build folder (default Source/build)")
    ap.add_argument("--step", action="store_true", help="with all: include the STEP export")
    a = ap.parse_args()
    steps = [s for s in STEPS if (s != "step" or a.step) and s != "fasteners"] if "all" in a.steps else a.steps   # parts runs fasteners
    for s in steps:
        if s not in STEPS + ["install"]: sys.exit(f"build.py: unknown step {s} (choose from all, {', '.join(STEPS)}, install)")
    B = Build(a.build); B.inputs()
    fresh_file = B.p("fresh.json")                 # remembered across runs in the same build folder
    if os.path.exists(fresh_file) and "all" not in a.steps: B.fresh = set(json.load(open(fresh_file)))
    t0 = time.time()
    for s in steps:
        log(f"== {s}")
        (B.threemf if s == "3mf" else getattr(B, s))()
        json.dump(sorted(B.fresh), open(fresh_file, "w"))
    log(f"done in {time.time() - t0:.0f} s; build folder {B.b}")

if __name__ == "__main__":
    main()
