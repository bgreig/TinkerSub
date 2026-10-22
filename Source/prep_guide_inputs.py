"""
Rebuild the inputs build_guide_final.py needs (render crops, vols.json, mix_final.json, out_lbl STLs, out_final CAD,
3MF + plate maps) from a previous ROV_Build_Package, so the guide and package can be regenerated after a text-only
change without re-running the geometry and render pipeline.

Usage (from the workspace folder):
  python3 prep_guide_inputs.py <old ROV_Build_Package dir> <old ROV_Assembly_Guide.pdf>
  python3 build_guide_final.py render/final outdir
  rm -rf outdir/ROV_Build_Package/CAD/STEP; cp <old package>/README.txt outdir/ROV_Build_Package/
Then diff the new package against the old one: only the text you changed should differ.
Needs: pymupdf, trimesh, reportlab, pillow, pypdf (the guide appends the side-plate templates as Appendix A).
"""
import sys, os, glob, shutil, json, csv
import pymupdf as fitz, trimesh

P, OLD_PDF = sys.argv[1], sys.argv[2]
CROP = "render/final/crop"
for d in ("out_lbl", "out_final/step", "out", CROP, "outdir"): os.makedirs(d, exist_ok=True)
for f in glob.glob(os.path.join(P, "STL", "*", "*.stl")): shutil.copy(f, "out_lbl")
for f in glob.glob(os.path.join(P, "CAD", "*.*")): shutil.copy(f, "out_final")
for f in ("prop_hex_section", "compensator_section", "compensator_cutaway"): shutil.copy(os.path.join(P, "Images/Diagrams", f + ".png"), "out")
for sub in ("Renders", "Assembly_steps"):
    for f in glob.glob(os.path.join(P, "Images", sub, "*.png")): shutil.copy(f, os.path.join(CROP, "f_" + os.path.basename(f)))
for f in glob.glob(os.path.join(P, "Images/Parts/*.png")): shutil.copy(f, os.path.join(CROP, "pf_" + os.path.basename(f)))
# Electronics (section 9): images back to their render names, the wire list and the callout keys (from render_threejs/views_elec.json)
ENAMES = {"sled_top_face": "e_layout_top", "sled_bottom_face": "e_layout_bot", "stacked_pair": "e_stack", "rear_bay": "e_rear",
          "harness_port": "e_wire_port", "harness_starboard": "e_wire_stbd", "sled_in_hull": "e_hull",
          "schematic_1_power_and_drivers": "elec_sch1", "schematic_2_control_and_lights": "elec_sch2", "wiring_diagram": "elec_wiring"}
for n, k in ENAMES.items():
    shutil.copy(os.path.join(P, "Images/Electronics", n + ".png"), os.path.join(CROP, f"f_{k}.png"))
json.dump([[int(r[0]), r[1], r[2], r[3]] for r in list(csv.reader(open(os.path.join(P, "Wire_list.csv"))))[1:]], open("render/elec_wires.json", "w"))
_v = json.load(open("render_threejs/views_elec.json"))
json.dump({k: [l[2] for l in v.get("labels", []) if l[1] != "C"] for k, v in _v.items()}, open("render/elec_legends.json", "w"), indent=1)
shutil.copy(os.path.join(P, "Images/Diagrams/thruster_layout.png"), os.path.join(CROP, "f_layout.png"))
shutil.copy(os.path.join(P, "Images/Diagrams/side_plates_on_24x24_sheet.png"), os.path.join(CROP, "f_nest.png"))
for n in ("Frame", "Core"):
    shutil.copy(os.path.join(P, f"ROV_{n}.3mf"), "outdir")
    shutil.copy(os.path.join(P, "Images/Diagrams", f"ROV_{n}_plates.png"), "outdir")

# Label close-ups (L_*.png) are not in the package: take them from the old guide, in the order the guide places them.
doc = fitz.open(OLD_PDF)
def page_images(marker):
    for p in doc:
        if marker in p.get_text():
            return [b["xref"] for b in sorted(p.get_image_info(xrefs=True), key=lambda b: (round(b["bbox"][1] / 20), b["bbox"][0]))]
    raise SystemExit("marker not found: " + marker)
def save(xref, name):
    pix = fitz.Pixmap(doc, xref)
    if pix.n - pix.alpha > 3: pix = fitz.Pixmap(fitz.csRGB, pix)
    pix.save(os.path.join(CROP, name))
save(page_images("214 sled deck, top face")[0], "L_deck214.png")
for x, n in zip(page_images("Left: 202 hull rear cap"), ("L_rearcap", "L_deck", "L_jbox", "L_bh215", "L_station")): save(x, n + ".png")

# vols.json: extents from the STLs, volume back-solved from the old BOM so filament estimates stay identical.
vols = {}
for r in csv.DictReader(open(os.path.join(P, "BOM_printed_parts.csv"))):
    stem, qty, g = os.path.basename(r["File"])[:-4], int(r["Qty"]), float(r["Est. filament (g)"])
    ext = [float(x) for x in trimesh.load(os.path.join("out_lbl", stem + ".stl")).extents]
    fill = 0.95 if "cowl" in stem else (0.9 if min(ext) <= 8 else 0.55)
    vols[stem] = [g / (1.27 * fill * qty), ext]
json.dump(vols, open("render/vols.json", "w"))

# Thruster mixing table (guide section 14).
MIX = [("T1 front port", 108, 118, -0.71, -0.71, -0.0, 1.0), ("T2 front starboard", -108, 118, -0.71, 0.71, -0.0, -1.0),
       ("T3 rear port", 108, -118, 0.71, -0.71, 0.0, -1.0), ("T4 rear starboard", -108, -118, 0.71, 0.71, 0.0, 1.0),
       ("T5 vertical port", 105, -8, 0.0, -0.0, 1.0, -0.0), ("T6 vertical starboard", -105, -8, 0.0, -0.0, 1.0, 0.0)]
json.dump([dict(name=n, x=x, z=z, surge=a, sway=b, heave=c, yaw=d) for n, x, z, a, b, c, d in MIX], open("render/final/mix_final.json", "w"))
print("inputs ready")
