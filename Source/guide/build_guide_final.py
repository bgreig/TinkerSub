"""
Complete build package: BOM CSVs, start-to-finish assembly guide PDF, STL folders, CAD for the HDPE side plates.
Colours: top cowl = yellow PETG, every other printed part = black PETG.
Usage: python3 build_guide_final.py <render_dir> <out_dir>
"""
import sys, os, csv, json, shutil
import build_guide as G                                   # styles + helpers (argv: render dir, out dir)
from build_guide import (Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, NextPageTemplate, CondPageBreak,
                         BaseDocTemplate, PageTemplate, Frame, ParagraphStyle, colors, inch, letter, TA_CENTER,
                         H1, H2, H3, BODY, SMALL, CAP, CELL, CELLB, NOTE, W_TXT, img, fig, steps, table, on_cover, C, TODAY, VOLS)
from parts_final import PRINTED_A, PRINTED_B, PRINTED, is_yellow, base, pn
import parts_final as PF
from reportlab.platypus import Flowable
from package_images import image_map

RD, OUT = G.RD, G.OUT
BRAND, FP = "TinkerSub KB-1", "TinkerSub_KB-1"          # project name (open source) and file-name prefix
PKG = os.path.join(OUT, f"{FP}_Build_Package")
YEL, BLK = colors.HexColor("#f2c200"), colors.HexColor("#26292d")
SECTION_DIR = {"Thrusters": "1_Thrusters", "Thruster pylons": "1_Thrusters", "Hull + sled": "2_Hull_and_sled",
               "Battery pod": "3_Battery_pod", "Lights": "4_Lights", "Junction boxes": "5_Junction_boxes",
               "Stations + brackets": "6_Stations_and_brackets", "Belly pan": "7_Belly_pan", "Top cowl (YELLOW)": "8_Top_cowl_YELLOW"}
def grams(stem, qty):
    v, ext = VOLS[stem]
    fill = 0.9 if min(ext) <= 8 else 0.55
    if "cowl" in stem: fill = 0.95
    return round(v * 1.27 * fill * qty)
G_Y = sum(grams(p[1], p[3]) for p in PRINTED if is_yellow(p[1]))
G_B = sum(grams(p[1], p[3]) for p in PRINTED if not is_yellow(p[1]))
N_A, N_B = sum(p[3] for p in PRINTED_A), sum(p[3] for p in PRINTED_B)
MIX = json.load(open(os.path.join(RD, "mix_final.json")))

# ------------------------------------------------------------------ electronics (section 9): (ref, qty, part, notes, cost, source); cost None = already in HW
ELEC_SECTION = [
 ("U1-U6", "6", "IBT_2 (BTS7960) H-bridge driver", "One per thruster, heatsinks removed. Logic VCC from the Pico 3V3", "$40-60", "Amazon"),
 ("U9A, U9B", "2", "Mini MP1584EN 5 V 1.8 A buck boards (5-30 V in, fixed 5 V out)", "Top face, port side beside the Pi: U9A for the Pi, HAT, camera and Pico; U9B for the servos only", "already owned", "Amazon"),
 ("U9 mounting", "-", "Clear 20-25 mm heat-shrink + double-sided foam tape", "One sleeve over each mini buck, taped to the deck", "$3", "Any"),
 ("U10", "1", "Raspberry Pi Pico, headers fitted, on a 57 x 63 mm screw-terminal breakout board", "Underneath at the front, centred between the rails, USB to the front", "already owned", "Amazon"),
 ("U11", "1", "Raspberry Pi Zero 2W, header fitted", "Top face, header to starboard", "$15-18", "Pi reseller"),
 ("U12", "1", "Waveshare ETH/USB HUB HAT (RTL8152B: 1 x RJ45 + 3 x USB-A) with its micro-USB link board", "On the Pi Zero, 11 mm above it; tether to topside", "already owned", "Waveshare / Amazon"),
 ("Ethernet", "1 + 1", "Cat6 patch lead, 0.3 m, one end 90-degree (left or right angle), + RJ45 inline coupler", "HAT RJ45 to the tether: the plug has to turn aft within 25 mm", "$8-10", "Amazon"),
 ("U7-U8", "2", "Mean Well LDD-700HW LED driver", "Rear face of 215 (shopping list: Lights)", None, None),
 ("J1", "1", "Arducam for Pi Zero + 150-200 mm Zero ribbon", "On the pan-tilt cradle (shopping list: Camera)", None, None),
 ("SV1-SV2", "2", "MG90S micro servo", "Pan and tilt (shopping list: Camera)", None, None),
 ("F1", "1", "Inline ATO/ATC fuse holder, 12 AWG, + 30 A fuse", "Battery red, into the +12V Wago", "$7", "Auto parts store"),
 ("F2", "1", "Inline mini-blade holder + 3 A fuse", "Aux branch: LED drivers and both 5 V bucks", "$4", "Auto parts store"),
 ("C1", "1", "1000 uF 25 V low-ESR electrolytic", "Across the 5 V bucks' 12 V feed, in the port trough", "$1", "DigiKey / Mouser"),
 ("C2", "1", "470 uF 10 V electrolytic", "Across +5V / GND at the servo plugs", "$0.50", "DigiKey / Mouser"),
 ("D1", "1", "1N5817 Schottky diode", "U9A 5 V to Pico VSYS, band toward the Pico", "$0.25", "DigiKey / Mouser"),
 ("R1, R2", "2", "10 k resistor, 1/4 W", "ARM and DIM pull-downs", "$0.10", "Any"),
 ("R3, R4", "1 + 1", "33 k and 10 k resistors, 1/4 W", "Battery-voltage divider to GP26", "$0.20", "Any"),
 ("Bus", "2", "Wago 221-415 lever connectors", "+12V and GND, rear face of 215 (shopping list: Electronics sled)", None, None),
 ("Wire", "1 m + 1 m", "14 AWG silicone wire, red + black", "Bus to the three top boards", "$8", "Amazon"),
 ("Wire", "0.5 m + 0.5 m", "16 AWG silicone wire, red + black", "Jumpers to the bottom boards", "$6", "Amazon"),
 ("Wire", "1 m + 1 m", "20 AWG silicone wire, red + black", "Aux branch: F2 to LED drivers and both 5 V bucks", "$5", "Amazon"),
 ("Wire", "1 set", "Dupont female housings + 22 AWG hook-up wire, crimp splices", "Logic bundles (Dupont at the IBT_2 headers, bare ends into the Pico terminals), UART, DIM, 5 V", "$8", "Amazon"),
 ("Misc", "-", "Zip ties 2.5-3.6 mm, heat-shrink assortment", "Boards, harness ties, every splice", "$8", "Any"),
]
import purchases as PU                                     # "Everything to buy": fasteners counted from the fastener table
from insert_map import EXPECT as _INS                      # the insert chart's counts per part
BUY = PU.buy_list(round(G_B/1000 + 0.3, 1), round(G_Y/1000 + 0.2, 1))
_qty = {}
for _p in PRINTED: _qty[pn(_p[1])] = _qty.get(pn(_p[1]), 0) + _p[3]
_chart = {s_: sum(d.get(s_, 0)*_qty.get(k, 0) for k, d in _INS.items()) for s_ in ("M3", "M4", "M5")}
assert _chart == dict(PU.fastener_lines()[1]), f"insert totals: chart {_chart} vs fastener table {dict(PU.fastener_lines()[1])}"
CUTS = [("4\" Sch40 hull", 1, 406), ("3\" Sch40 battery pod", 1, 300)]

# ------------------------------------------------------------------ package
# The repository is the package. build_package() writes only the generated files (STL, images, CAD, 3MFs, BOMs, guide)
# into PKG, laid out as in the repository; Source/, Firmware/, docs and licences are the repository's own files.
# build.py check compares PKG with the repository; build.py install copies it over.
def build_package():
    if os.path.exists(PKG): shutil.rmtree(PKG)
    for d in sorted(set(SECTION_DIR.values())): os.makedirs(os.path.join(PKG, "STL", d), exist_ok=True)
    os.makedirs(os.path.join(PKG, "CAD"), exist_ok=True)
    for sec, stem, src, *_ in PRINTED:
        shutil.copy(os.path.join(src, stem + ".stl"), os.path.join(PKG, "STL", SECTION_DIR[sec], stem + ".stl"))
    for b, pk in image_map([p[1] for p in PRINTED]):                         # every guide picture (guide/package_images.py)
        os.makedirs(os.path.dirname(os.path.join(PKG, pk)), exist_ok=True); shutil.copy(b, os.path.join(PKG, pk))
    for f in ("rov_side_plate_port.dxf", "rov_side_plate_stbd.dxf", "rov_side_plates_24x24_nest.dxf", "rov_side_plate_templates.pdf", "rov_side_plate_templates_fullsize_24x18.pdf", "rov_side_plate_templates_letter_portrait.pdf", "rov_side_plates_both_24x36.pdf", "rov_side_plate_templates_factory_edges.pdf",
              "rov_side_plate_port.stl", "rov_side_plate_stbd.stl", "rov_side_plates_24x24_nest.stl"):
        shutil.copy(os.path.join("out_final", f), os.path.join(PKG, "CAD", f))
    if os.path.isdir("out_final/step"): shutil.copytree("out_final/step", os.path.join(PKG, "CAD", "STEP"))   # only when build.py step ran
    import glob
    for n in ("Frame", "Core"):
        shutil.copy(os.path.join(OUT, f"ROV_{n}.3mf"), os.path.join(PKG, f"{FP}_{n}.3mf"))
    for f in glob.glob(os.path.join(OUT, "ROV_Reprint_*.3mf")):                  # reprint projects for builders with earlier prints
        shutil.copy(f, os.path.join(PKG, os.path.basename(f).replace("ROV_", FP + "_")))
    with open(os.path.join(PKG, "BOM_printed_parts.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["Part #", "Bambu project", "Section", "File", "Qty", "Filament", "Print notes", "Used for", "Est. filament (g)"])
        for proj, lst in (("TinkerSub_KB-1_Frame.3mf", PRINTED_A), ("TinkerSub_KB-1_Core.3mf", PRINTED_B)):
            for sec, stem, src, qty, mat, note, use in lst:
                w.writerow([pn(stem), proj, sec, f"STL/{SECTION_DIR[sec]}/{stem}.stl", qty, mat, note, use, grams(stem, qty)])
    with open(os.path.join(PKG, "Parts_to_buy.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["Group", "Qty", "Item (exact size)", "Used for", "Approx. price (US)", "Source"])
        for row in BUY: w.writerow(row)
    with open(os.path.join(PKG, "Wire_list.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["Wire #", "From", "To", "Wire"])
        for row in json.load(open(os.path.join(os.path.dirname(RD.rstrip("/")), "elec_wires.json"))): w.writerow(row)
    with open(os.path.join(PKG, "Pin_connections.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["Board", "Pin", "Pin name", "Connects to", "Wire #"])
        for row in json.load(open(os.path.join(os.path.dirname(RD.rstrip("/")), "elec_pins.json"))): w.writerow(row)
    with open(os.path.join(PKG, "Pipe_cut_list.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["Piece", "Qty", "Length (mm)", "Length (in)"])
        for n, q, L in CUTS: w.writerow([n, q, L, round(L/25.4, 2)])

# ------------------------------------------------------------------ PDF helpers
def on_page(c, doc):
    c.saveState(); c.setStrokeColor(G.RULE); c.setLineWidth(0.6)
    c.line(0.75*inch, 0.6*inch, letter[0] - 0.75*inch, 0.6*inch)
    c.setFont("Helvetica", 7.5); c.setFillColor(G.MUTED)
    c.drawString(0.75*inch, 0.42*inch, f"{BRAND} Build Guide  |  4\" hull, 3\" battery pod, HDPE side plates, 6 vectored thrusters")
    c.drawRightString(letter[0] - 0.75*inch, 0.42*inch, f"Page {doc.page}"); c.restoreState()

def parts_table(lst):
    data = [[Paragraph(h, CELLB) for h in ("Part #", "File", "Qty", "Print notes", "Used for", "g")]]
    st = [("LINEBELOW", (0, 0), (-1, 0), 0.8, G.INK), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
          ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
    sec_prev = None
    for sec, stem, src, qty, mat, note, use in lst:
        if sec != sec_prev:
            data.append([Paragraph(f"<b>{sec}</b>", CELL), "", "", "", "", ""]); r = len(data) - 1
            st += [("SPAN", (0, r), (-1, r)), ("BACKGROUND", (0, r), (-1, r), G.SOFT)]; sec_prev = sec
        y = is_yellow(stem)
        data.append([Paragraph(f"<b>{pn(stem)}</b>", ParagraphStyle("s", parent=CELL, textColor=G.INK if y else colors.white, alignment=TA_CENTER, fontSize=9)),
                     Paragraph(stem + ".stl", CELL), Paragraph(str(qty), CELL), Paragraph(note, CELL), Paragraph(use, CELL),
                     Paragraph(str(grams(stem, qty)), CELL)])
        r = len(data) - 1; st.append(("BACKGROUND", (0, r), (0, r), YEL if y else BLK))
    t = Table(data, colWidths=[0.55*inch, 2.2*inch, 0.35*inch, 2.15*inch, 1.5*inch, 0.35*inch], repeatRows=1)
    t.setStyle(TableStyle(st)); return t

USE = {base(st): u for _, st, _s, q, _m, _n, u in PRINTED}
QTY = {base(st): q for _, st, _s, q, *_ in PRINTED}
BY_PN = {PF.PN[b]: b for b in USE}
def _use(stem): return USE[base(stem)].replace(" (your design)", "")
def parts_used(pns, extra=()):
    """'Parts for this section' strip: part number chips coloured like the part, name, quantity"""
    rows, st = [], [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3), ("BOX", (0, 0), (-1, -1), 0.5, G.RULE)]
    items = [(p, _use(BY_PN[p]), QTY[BY_PN[p]], is_yellow(BY_PN[p])) for p in pns] + [(p, n, q, False) for p, n, q in extra]
    half = (len(items) + 1) // 2; cols = [items[:half], items[half:]]
    for i in range(half):
        row = []
        for c in cols:
            if i < len(c):
                p, n, q, y = c[i]
                row += [Paragraph(f"<b>{p}</b>", ParagraphStyle("pc", parent=CELL, alignment=TA_CENTER, textColor=G.INK if y else colors.white)),
                        Paragraph(f"{n}", CELL), Paragraph(f"x{q}", CELL)]
                st.append(("BACKGROUND", (len(row) - 3, i), (len(row) - 3, i), YEL if y else BLK))
            else: row += ["", "", ""]
        rows.append(row)
    t = Table(rows, colWidths=[0.45*inch, 2.35*inch, 0.4*inch] * 2)
    t.setStyle(TableStyle(st))
    return KeepTogether([Paragraph("Parts for this section", ParagraphStyle("pu", parent=SMALL, textColor=G.MUTED)), t, Spacer(1, 6)])

def checklist(items):
    return table(["", "Before you go on"], [["[  ]", t] for t in items], [0.4*inch, W_TXT - 0.4*inch], zebra=False)

# ------------------------------------------------------------------ PDF
TEMPLATE_PDF = os.path.join("out_final", "rov_side_plate_templates.pdf")
APP = {"first": 0, "last": 0}            # guide page numbers of Appendix A's template pages (filled in by the first pass)
def app_pages(): return f"pages {APP['first']}-{APP['last']}" if APP["first"] else "the last pages"
def appb_pages(): return f"pages {APP['last'] + 1}-{APP['cfirst'] - 1}" if APP.get("cfirst") else "the last pages"
def appc_pages():
    if not APP.get("cfirst"): return "the last pages"
    return f"page {APP['cfirst']}" if APP["cfirst"] == APP["blast"] else f"pages {APP['cfirst']}-{APP['blast']}"
def build_pdf(path):
    doc = BaseDocTemplate(path, pagesize=letter, leftMargin=0.75*inch, rightMargin=0.75*inch, topMargin=0.7*inch,
                          bottomMargin=0.8*inch, title=f"{BRAND} Build Guide", author="Brian")
    fr = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
    doc.addPageTemplates([PageTemplate("cover", [fr], onPage=on_cover), PageTemplate("body", [fr], onPage=on_page)])
    S = []
    toc = [("1", "Overview and build order"), ("2", "What's in the package"), ("3", "Tools and ground rules"),
           ("4", "Shopping list"), ("5", "Print the parts"), ("6", "Cut the side plates from HDPE"), ("7", "Build the thrusters (x6)"),
           ("8", "Build the electronics sled"), ("9", "Electronics: parts, schematic, wiring and tests"), ("10", "Build and test the hull"), ("11", "Build the battery pod"), ("12", "Build the lights"),
           ("13", "Station frames: join hull and pod"), ("14", "Side plates and thrusters"), ("15", "Belly pan"),
           ("16", "Junction deck and wiring"), ("17", "Top cowl"), ("18", "Leak test, trim and first dive"), ("19", "Reference views and layout"),
           ("A", f"Appendix A: side plate cutting templates, 1:1 ({app_pages()})"),
           ("B", f"Appendix B: heat-set insert chart and picture-by-picture assembly ({appb_pages()})"),
           ("C", f"Appendix C: updating parts from an earlier build ({appc_pages()})")]
    # ---------------- cover
    S += [Paragraph(f"{BRAND}  <font color='#5b6670' size='20'>Build Guide</font>", ParagraphStyle("T", parent=H1, fontSize=32, leading=36)),
          Paragraph("A printable, open-source ROV you can build and change. Start-to-finish build: 4\" electronics hull, 3\" battery pod, HDPE side plates, yellow top cowl and six vectored 1200 GPH thrusters",
                    ParagraphStyle("st", parent=BODY, fontSize=12, leading=16, textColor=G.MUTED)),
          Spacer(1, 0.06*inch), img(C("f_front.png"), W_TXT, 2.35*inch), Spacer(1, 0.04*inch),
          Paragraph("Colours in every picture match the build: yellow = top cowl (yellow PETG); black = every other printed part (black PETG) "
                    "and the HDPE side plates; white / grey = PVC pipe and bought parts.", SMALL),
          Paragraph(TODAY, SMALL), Spacer(1, 0.1*inch),
          table(["#", "Section"], toc, [0.4*inch, W_TXT - 0.4*inch], zebra=False), NextPageTemplate("body"), PageBreak()]

    # ---------------- 1 overview
    S += [Paragraph("1  Overview and build order", H1),
          Paragraph(f"{BRAND} is an open-source, mostly 3D-printed ROV. It is two sealed tubes held together by two printed station frames: a 4\" PVC hull on top with the camera, "
                    "computer and drivers, and a 3\" PVC battery pod underneath. Two 1/2\" HDPE side plates bolt to the stations' arms "
                    "and carry the six oil-filled thrusters. A yellow printed cowl closes the top (lights and foam built in) "
                    "and a belly pan under the pod holds the lead ballast.", BODY),
          table(["Phase", "What you do", "Sections"], [
              ["1  Order", "Buy the hardware, the HDPE sheet, pipe and both filaments. Long-lead items first: motors, dome, LEDs, drivers.", "4"],
              ["2  Print", f"Two Bambu Studio projects, {N_A + N_B} parts. Black PETG for everything except the 6 cowl sections (yellow). "
                          "Start with the Core project: the thrusters take longest to finish.", "5"],
              ["3  Cut", "Both side plates from one 24 x 24\" HDPE sheet with the paper templates in Appendix A (or have a shop CNC them).", "6, A"],
              ["4  Sub-assemblies", "Thrusters, electronics sled and its wiring, hull, battery pod and lights. Each is finished and checked on its own.", "7-12"],
              ["5  Frame", "Stations on the hull and pod, side plates with the thrusters, belly pan, junction deck and wiring, cowl.", "13-17"],
              ["6  Test", "Vacuum and dunk tests, thruster checks, trim in a pool, then dives at 10, 30 and 60 ft.", "18"]],
              [1.2*inch, W_TXT - 2.0*inch, 0.8*inch]),
          Paragraph("Key numbers", H2),
          table(["Item", "Value"], [
              ["Size", "351 W x 328 H x 508 L mm (13.8 x 12.9 x 20.0 in)"],
              ["Weight (est.)", "about 12.5 kg in air before foam and lead; about 0.8 kg buoyant in fresh water before trimming."],
              ["Trim (est.)", "1.6 kg lead + 1.0 L foam: about 0.3 kg buoyant, centre of buoyancy 31 mm above the centre of gravity. "
                              "2.25 kg + 1.7 L: 41 mm (steadier). Fine-tune in a pool."],
              ["Thrusters", "4 horizontals at 45 deg in the corners (forward/back, sideways, turn) + 2 verticals at the centre of gravity"],
              ["Power", "3S8P 18650 pack (about 11-12.6 V) in the pod; Cat6 tether carries data only"],
              ["Depth", "Target 60 ft. The printed hull and pod caps carry 100-150 kg there: go deeper in steps (section 18.2), or machine those caps from aluminium."]],
              [1.2*inch, W_TXT - 1.2*inch]),
          Paragraph("Directions: port = left and starboard = right when you stand behind the ROV looking forward. The front is the dome end.", NOTE),
          PageBreak()]

    # ---------------- 2 package
    S += [Paragraph("2  What's in the package", H1),
          table(["File / folder", "Contents"], [
              ["TinkerSub_KB-1_Assembly_Guide.pdf", "This guide."],
              ["TinkerSub_KB-1_Frame.3mf", f"Bambu Studio project, {N_A} parts: station frames, junction deck, corner brackets, thruster pylons, belly pan (black) "
                                "and the top cowl (yellow, on its own plates)."],
              ["TinkerSub_KB-1_Core.3mf", f"Bambu Studio project, {N_B} parts, all black: thrusters, hull flanges and caps, sled, camera mount, battery pod, lights, junction box and lid."],
              ["TinkerSub_KB-1_Reprint_2026-10-20.3mf", "The parts changed on 2026-10-20, for builders who printed before then (Appendix C)."],
              ["BOM_printed_parts.csv", "Every printed part: project, file, quantity, filament colour, print notes, filament weight."],
              ["Parts_to_buy.csv", "The shopping list (section 4): every bought part with quantity, exact size, use, rough price and source."],
              ["Pipe_cut_list.csv", "4\" hull and 3\" pod lengths."],
              ["STL/", "Every printable part in print orientation (mm), in 8 folders in build order. The cowl folder is marked YELLOW."],
              ["CAD/", "Side plate templates (PDF) and DXFs: which file for which way of cutting is in section 6. "
                       "CAD/STEP: a STEP file for most printed parts and the whole ROV as a mesh (TinkerSub_KB-1_assembly_mesh.3mf). The full assembly STEP "
                       "(named, coloured components, for Fusion 360 or any CAD app) is too big for GitHub: it is the TinkerSub_KB-1_assembly_step.zip download on the KB-1 release."],
              ["Images/", "Renders, assembly pictures, part pictures, diagrams and the plate maps of both projects."],
              ["Source/", "The Python generators for every part, the 3MFs, templates, STEP files, renders and this guide, with their input files. One command rebuilds it all: python3 Source/build.py all (Source/README.md)."],
              ["Firmware/", "Pico firmware (source and ready-to-flash UF2), the Pi Zero bridge, the topside program and their tests."],
              ["docs/", "Battery_Pack_Build.md: cell matching, welding, BMS wiring, first charge and voltage limits for the 3S8P pack."],
              ["LICENSE, LICENSES/", "Hardware CERN-OHL-S-2.0, software MIT, documentation CC BY-SA 4.0. CHANGELOG.md lists every change to the files."]],
              [2.55*inch, W_TXT - 2.55*inch]),
          PageBreak()]

    # ---------------- 3 tools
    S += [Paragraph("3  Tools and ground rules", H1), Paragraph("Tools", H2),
          table(["Tool", "Used for"], [
              ["Bambu A1 (256 mm bed)", "Every part fits. The station halves and cowl sections are the largest."],
              ["Soldering iron with heat-set insert tip", "M3, M4 and M5 brass inserts (Appendix B has a chart of every one)"],
              ["Taps: M16 x 1.5, M12 x 1.5, M10 x 1.0 (fine pitch), M4 x 0.7, M3 x 0.5", "Cable glands, VENT ports, oil ports, light set screws"],
              ["Jigsaw + fine blades, drill + 3.5 / 4.5 / 5.5 / 10 mm bits, centre punch, clamps", "HDPE side plates"],
              ["Drill + 1/8\" (3.17 mm) bit or reamer", "Open the brass coupler's 3 mm end for the motor shaft"],
              ["Drill press or lathe + files", "Aluminium light discs (or have them cut)"],
              ["PVC saw or cutter, deburring tool", "4\" and 3\" pipe"],
              ["Hex keys 2-4 mm, 7 / 8 mm nut drivers", "General assembly. The 8 mm driver fits inside the prop hub."],
              ["Syringe (60 ml) with a short tube", "Oil fill"],
              ["Hand vacuum pump + gauge (generic brake-bleeder type) + 6 mm hose", "Hull and pod vacuum tests through the M10 barb"],
              ["Spot welder (or a shop that has one)", "Nickel strip on the 18650 pack. Never solder directly to cells."],
              ["Multimeter", "Wiring and pack checks"]],
              [2.6*inch, W_TXT - 2.6*inch]),
          Paragraph("Ground rules", H2),
          steps(["Measure your motor shaft before printing the props: the design assumes 3.17 mm (1/8\").",
                 "PVC cement only bonds PVC to PVC. Printed parts are bolted, or epoxied where they meet the pipe. Nothing sticks to HDPE: it is always bolted.",
                 "Grease every O-ring lightly with silicone grease. Never use petroleum grease on nitrile.",
                 "Keep the 12 V wiring and the 3.3 V / 5 V logic apart: the Pico's pins are 3.3 V only (section 9).",
                 "Label left/right parts as they come off the printer: most frame parts come as a port and a starboard version."]),
          PageBreak()]

    # ---------------- 4 shopping
    S += [Paragraph("4  Shopping list", H1),
          Paragraph("Every bought part for one ROV: total quantity, exact size, what it is for, and a rough US price to budget with (check current "
                    "prices before ordering). The screw, nut and insert counts come from the build's fastener table, which is checked against the "
                    "3D model, and the filament weights from the models. Tools are in section 3. The same list is Parts_to_buy.csv.", BODY),
          table(["Group", "Qty", "Item (exact size)", "Used for", "Price", "Source"],
                [(g if i == 0 or g != BUY[i - 1][0] else "", q, d, u, c, so) for i, (g, q, d, u, c, so) in enumerate(BUY)],
                [0.78*inch, 0.6*inch, 2.4*inch, 1.55*inch, 0.75*inch, W_TXT - 6.08*inch]),
          Spacer(1, 6), Paragraph("Pipe cut list", H3),
          table(["Piece", "Qty", "mm", "in"], [[n, q, L, f"{L/25.4:.2f}"] for n, q, L in CUTS], [3.4*inch, 0.6*inch, 0.8*inch, 0.8*inch]),
          PageBreak()]

    # ---------------- 5 print
    S += [Paragraph("5  Print the parts", H1),
          Paragraph(f"Everything is in two Bambu Studio projects, already laid out on plates: open the 3MF, slice, print plate by plate. "
                    "Each plate holds one group of parts and is named after them, with their part numbers (for example \"Camera pan-tilt: 216, 217, 218, 219\"); "
                    "both plate maps are at the end of this section. "
                    f"About {round(G_B/1000, 1)} kg of black PETG and {round(G_Y/1000, 1)} kg of yellow. Bambu Studio shows each plate's time after slicing.", BODY),
          Paragraph("Print settings", H3),
          table(["Setting", "Value"], [
              ["Material", "PETG for everything. Black for all parts except the top cowl, which is yellow."],
              ["Profile", "Bambu A1 0.4 nozzle, 0.20 mm Standard, Bambu PETG Basic. Per-part walls, infill, brims and supports are already set in the 3MF files."],
              ["Walls / infill", "4 walls, 25 % gyroid by default; 5 walls on thread, O-ring and bracket parts; 40 % on the corner brackets. "
                                 "SOLID (100 %) on the parts that hold water out, so it can't seep through the skin and past the O-rings: hull flanges 201 "
                                 "and 203, rear cap 202, pod flanges 301 and caps 302 / 303, light front rings 402."],
              ["Supports", "None, except tree supports under the prop blades, inside the two middle cowl sections and under the camera cradle's (218) port cheek. "
                           "Those parts, and all cowl sections, sit at least 18-28 mm from their neighbours so supports and brims can't collide."],
              ["After printing", "Seal the thruster housings, tail cones and light heads: a thin coat of epoxy on the outside closes any layer gaps."]],
              [1.3*inch, W_TXT - 1.3*inch]),
          Paragraph("Heat-set inserts: 18 of the printed parts take them (42 x M3, 16 x M4, 36 x M5 in all). Appendix B at the back opens with a chart "
                    "of every printed part showing which hole takes which insert, from which side; the others take none. Press them all as the parts come "
                    "off the printer, before you start building.", NOTE),
          steps(["TinkerSub_KB-1_Core.3mf first, plates 1-4: thruster housings and tail cones (1-2), then the props with their nose cones "
                 "(3 right-hand, 4 left-hand; tree supports under the blades are already on). The thrusters' oil fill and testing take the longest, "
                 "so you can build them while the rest prints.",
                 "Then TinkerSub_KB-1_Core.3mf plates 5-10: hull rear flange, cap and sled bulkheads (5); dome flange and camera pan-tilt (6); "
                 "dome ring, lights and junction box with lid (7); sled rails and deck (8); battery pod (9); battery pack plates and spacers (10).",
                 "TinkerSub_KB-1_Frame.3mf plates 1-6 in black: station tops (1), station middles (2), station bottoms (3), "
                 "thruster pylons and corner brackets (4), junction deck (5), belly pan (6).",
                 "Change to yellow PETG for TinkerSub_KB-1_Frame.3mf plates 7-9: the six top cowl sections, rear, middle and front. "
                 "Each plate's name says YELLOW and no plate mixes colours.",
                 "Check every part against the list below as it comes off. Pictures of every part are in the Appendix B chart."]),
          Paragraph(f"TinkerSub_KB-1_Frame.3mf  ({N_A} parts)", H2), parts_table(PRINTED_A),
          CondPageBreak(3*inch), Paragraph(f"TinkerSub_KB-1_Core.3mf  ({N_B} parts)", H2), parts_table(PRINTED_B),
          PageBreak(), Paragraph("Part numbers and labels", H2),
          Paragraph("Every printed part has its three-digit part number debossed (cut 0.6 mm in) on a flat face, in the part's own colour: "
                    "no second filament, no painting. The first digit is the subsystem: 1 thrusters, 2 hull and sled, 3 battery pod, 4 lights, "
                    "5 junction box, 6 stations and brackets, 7 belly pan, 8 top cowl (yellow), 9 the two HDPE side plates (marked from the template). "
                    "The STL and 3MF file names start with the same number, and the guide refers to parts by it.", BODY),
          Paragraph("Parts that something mounts on also carry where it goes:", BODY),
          table(["Part", "Label(s)", "Meaning"], [
              ["214 sled deck", "PI ZERO, USB-ETH, T1-T3, 12V (top); PICO, BUCK, C1, T4-T6 (underneath); FWD arrow. BUCK and C1 are no longer used there; the two mini 5 V bucks now sit in the USB-ETH space",
               "Where each board goes. Every power terminal faces port, every logic header starboard."],
              ["212 / 213 sled rails", "PORT, 12 V SIDE / STBD, LOGIC SIDE; FWD arrows", "Which rail goes where, and which side each harness runs."],
              ["215 sled rear bulkhead", "+12V, GND, LDD 1, LDD 2, 12V and LOGIC windows, TOP", "Wago bus and LED driver pockets on its rear face."],
              ["216 pan-tilt base", "TOP, PAN SERVO", "Which way up, and where the pan servo goes."],
              ["202 hull rear cap", "MOTORS, LIGHTS, BATTERY, TETHER, VENT (outside face)", "Which gland goes in which hole."],
              ["302 / 303 pod caps", "REAR, BATTERY, VENT / FRONT (outside faces)", "Pod ends and the rear cap's two holes."],
              ["305 battery holder plate", "Number on the grooved face", "Grooved face goes outward; tab notch at the top."],
              ["601-605 station parts", "PORT / STBD", "Which side each half goes."],
              ["606 junction deck", "JUNCTION BOX (top face)", "Where the junction box screws down."],
              ["501 junction box / 503 lid", "T1-T6, L1, L2 under each socket; same map on the lid", "Which plug goes in which socket."],
              ["607 / 608 corner brackets", "A FP/RS, B FS/RP", "Bracket A: front-port and rear-starboard; B: front-starboard and rear-port."],
              ["103 / 104 props", "RH / LH (back face)", "Prop hand."],
              ["801-806 cowl sections", "REAR / MID / FRONT + PORT / STBD (inside)", "Where each section goes."],
              ["901 / 902 HDPE plates", "Template marks each hole: 601-605 ARM, 607 A / 608 B, T5 / T6 PYLON, COWL FOOT", "Write them on the plate with a paint marker while the template is on."]],
              [1.45*inch, 2.75*inch, W_TXT - 4.2*inch]),
          Spacer(1, 6),
          fig(C("L_deck214.png"), "214 sled deck, top face: board positions engraved.", max_h=2.4*inch),
          Table([[img(C("L_rearcap.png"), W_TXT/2 - 6, 2.6*inch), img(C("L_deck.png"), W_TXT/2 - 6, 2.6*inch)]], colWidths=[W_TXT/2]*2),
          Paragraph("Left: 202 hull rear cap, outside face, one label per gland. Right: 606 junction deck, top face.", CAP),
          Table([[img(C("L_jbox.png"), W_TXT/3 - 6, 1.9*inch), img(C("L_bh215.png"), W_TXT/3 - 6, 1.9*inch), img(C("L_station.png"), W_TXT/3 - 6, 1.9*inch)]], colWidths=[W_TXT/3]*3),
          Paragraph("501 junction box, port face: T1, T5, T3; 215 sled rear bulkhead, rear face; 601 station top, PORT.", CAP),
          PageBreak(), Paragraph("TinkerSub_KB-1_Frame.3mf plate map (the three yellow plates are the cowl)", H2), img(os.path.join(OUT, "ROV_Frame_plates.png"), W_TXT, 8.2*inch),
          PageBreak(), Paragraph("TinkerSub_KB-1_Core.3mf plate map", H2), img(os.path.join(OUT, "ROV_Core_plates.png"), W_TXT, 8.2*inch),
          PageBreak()]

    # ---------------- 6 side plates
    S += [Paragraph("6  Cut the side plates from HDPE", H1), parts_used([], extra=[("901", "Side plate, port (1/2\" HDPE, cut)", 1), ("902", "Side plate, starboard (1/2\" HDPE, cut)", 1)]),
          Paragraph("Both plates come out of one 24 x 24 x 1/2\" sheet of black HDPE (marine board). Each plate is 478 x 300 mm (18.8 x 11.8 in) "
                    "and its bottom edge is the skid. The two plates are mirror images. Pick one way to get the 1:1 templates, every hole marked with its drill size:", BODY),
          table(["Template", "File (in CAD/)"], [
              ["Letter landscape tiles, taped together (Appendix A of this guide)", "rov_side_plate_templates.pdf"],
              ["Letter portrait tiles", "rov_side_plate_templates_letter_portrait.pdf"],
              ["Each plate whole on one 24 x 18 in sheet: print shop, no taping (easiest)", "rov_side_plate_templates_fullsize_24x18.pdf"],
              ["No template: a shop with a CNC router cuts them; then skip to section 7", "rov_side_plate_port.dxf, rov_side_plate_stbd.dxf (mm)"]],
              [W_TXT*0.58, W_TXT*0.42]),
          fig(C("f_nest.png"), "Both plates on the 24 x 24\" sheet, 4.8 mm apart. The sheet has only about 2 mm to spare at each edge.", max_h=2.8*inch),
          steps(["Measure the sheet: it needs at least 605 mm (23.8\") in one direction. Undersize sheets are common.",
                 "Print the templates at 100 % / Actual size: turn off 'fit to page', 'shrink oversized pages' and any borderless scaling. Measure the "
                 "100 mm bar on every page before trimming anything; if it isn't exactly 100 mm, fix the setting and reprint.",
                 "Trim and tape the 4 tiles of each plate together on the dashed lines, matching the red marks.",
                 "Spray-glue (3M Super 77) or glue-stick both templates onto the sheet as on the layout, 5 mm apart, outside faces up.",
                 "Centre-punch every crosshair. Drill on a scrap-wood backer at slow speed: 3.5 mm (M3: vertical pylons, cowl screws), "
                 "4.5 mm (M4 where marked), 5.5 mm (M5: station arms, corner brackets).",
                 "Drill the blue 10 mm starter hole in each window and cut the windows with a jigsaw, fine-tooth blade, slow speed, "
                 "just outside the line. Fast cutting melts HDPE and it welds shut behind the blade.",
                 "Cut the two outlines, then file and sand all edges and break the corners. Write 901 PORT / 902 STBD and the hole tags printed on the template (601-605 ARM, 607 A / 608 B, "
                 "T5 / T6 PYLON, COWL FOOT) on each plate's outside face with a paint marker, then peel off the templates."]),
          fig(C("f_tile.png"), "One template tile: outline, holes with drill sizes, starter holes, overlap and registration marks.", max_h=2.6*inch),
          fig(C("f_plate.png"), "Finished port plate, outside face.", max_h=2.1*inch),
          checklist(["Two plates, mirror images, all holes drilled, windows cut, edges smooth, outside faces marked."]),
          PageBreak()]

    # ---------------- 7 thrusters
    S += [Paragraph("7  Build the thrusters (x6)", H1), parts_used(["101", "102", "103", "104", "105", "106", "107"]),
          Paragraph("Each thruster is a printed housing with the Kort duct built in, an oil-filled motor bay, a threaded tail cone with a "
                    "built-in compensator, and a two-piece prop driven by a brass coupler. Build all six the same way; "
                    "only the prop hand changes (3 right-hand, 3 left-hand: one of each per pair).", BODY),
          fig(C("f_thr_ex.png"), "Exploded thruster, rear to front: motor lead gland, tail cone with its spigot O-ring, motor, housing "
              "(pylon clamp on it), brass coupler, M5 stud with jam nut, prop hub, M5 nyloc, nose cone.", max_h=1.9*inch),
          Paragraph("7.1  Prepare the parts", H3),
          steps(["Tap the tail cone (102) tip M12 x 1.5 and the two side ports M4. Thread the M12 gland in with a drop of sealant.",
                 "Ream the coupler's 3 mm end to 1/8\" (3.17 mm) so it slides onto the motor shaft with a light push fit."]),
          Paragraph("7.2  Motor, coupler and prop", H3),
          steps(["Lightly grease the motor's nose O-ring. Feed the motor lead out through the rear of the housing (101) and push the motor in from "
                 "the back until the nose seats in the front bore.",
                 "Slide the bare coupler onto the shaft, 3 mm end down (no stud in it yet: the stud would hit the gauge's ceiling and set it too low). "
                 "Stand the coupler gauge (107) flat on the housing's front face over it, push the coupler up until it touches the gauge's ceiling, "
                 "and tighten the coupler's shaft-end set screw through a gauge window. Lift the gauge off. The coupler now sits 1 mm below the housing "
                 "face, so it can never rub. No gauge? Set the coupler's top 19.0 mm above the housing face with a caliper's depth rod.",
                 "Thread the M5 x 20 set screw halfway into the coupler's 5 mm end and lock it with the coupler's own grub screw. "
                 "Spin the M5 jam nut down onto it, flat side toward the coupler, and tighten it against the coupler.",
                 "Drop the prop hub (103 RH or 104 LH, marked on its back face) over the stud so the jam nut sits in the hub's hex pocket. Spin on the M5 nyloc with the 8 mm nut "
                 "driver through the hub until it just seats; the hub must turn freely with no rub on the duct.",
                 "Slide the nose cone (105) over the hub and fit the 3 M3 x 8 button screws."], start=3),
          fig(os.path.join("out", "prop_hex_section.png"), "Section through the prop drive.", max_h=2.1*inch),
          Paragraph("7.3  Tail cone, oil fill and compensator", H3),
          steps(["Fit the compensator bladder: push a nitrile finger cot straight down over the nipple inside the tail cone (102) until it "
                 "covers the groove (the nipple's tip is just below the rim). Roll a 5 x 1.5 mm O-ring down over the barb with a fingertip "
                 "until it drops into the groove: it clamps the cot, no tie needed. Fold the rest of the cot down into the cone. Water enters "
                 "it through the 2.2 mm vent; oil stays outside it.",
                 "Pass the motor lead through the tail cone gland, grease the 32 x 2 O-ring on the spigot and thread the tail cone on hand tight.",
                 "Stand the thruster nose down. Fill through one M4 port with a syringe of mineral oil while air leaves the other; "
                 "rock it and spin the prop by hand to free bubbles. Top off, then seal both ports with M4 set screws and sealant.",
                 "Tighten the gland on the lead. Wait an hour and check for weeping at the thread and the ports."], start=8),
          fig(os.path.join("out", "compensator_section.png"), "Oil fill and compensator, section through the axis.", max_h=3.3*inch),
          Paragraph("7.4  Pylon clamp", H3),
          steps(["Slide the pylon clamp (106) over the housing body (101) and close it with the 2 M4 x 30 pinch bolts. Leave it loose: "
                 "its final position is set on the ROV (section 14)."], start=12),
          fig(C("f_thr_as.png"), "Finished thruster with its pylon clamp.", max_h=1.9*inch),
          Paragraph("Label each thruster T1-T6 now and note its prop hand: T1/T2, T3/T4 and T5/T6 are each one right-hand + one left-hand. "
                    "Reverse the left-hand units in software so both of a pair push the same way.", NOTE),
          checklist(["Six thrusters, oil full, no bubbles, no weeping after an hour, props spin freely, labelled T1-T6 with prop hand."]),
          PageBreak()]

    # ---------------- 8 sled
    S += [Paragraph("8  Build the electronics sled and camera pan-tilt", H1), parts_used(["207", "212", "213", "214", "215", "216", "217", "218", "219"]),
          Paragraph("The sled is a front bulkhead (207) and a new rear bulkhead (215) 234 mm apart on four M3 rods, with two side rails (212, 213) "
                    "and a deck (214) between them. The deck carries the six IBT_2 motor drivers, three on each face, plus the Pi Zero with its "
                    "Ethernet HAT and two small 5 V buck boards on top, and the Pico on its screw-terminal breakout underneath. The rear bulkhead carries the 12 V Wago bus and both LED drivers. 12 V runs down the port side, "
                    "logic down the starboard side. The camera pan-tilt (216-219) sits on the same rods in front of 207, inside the dome. "
                    "Section 9 covers the electronics: parts, layout, schematic, wiring and the bench test.", BODY),
          fig(C("f_sled.png"), "Sled with the pan-tilt on the front: rails, deck, rear bulkhead 215, front bulkhead 207 and the four rods.", max_h=2.3*inch),
          Paragraph("8.1  Sled", H3),
          steps(["Front bulkhead (207): its two rod holes sit on the horizontal axis, but the rods run at 45 deg. Turn it 45 deg and drill the two missing "
                 "3.2 mm holes on the 94 mm circle, so all four rods pass at 45 deg.",
                 "Strip the heatsinks off all six IBT_2 boards. The deck slots take any square hole pattern from 38 to 46 mm.",
                 "For each stacked pair, push four M3 x 8 male-female standoffs down through the deck (214) slots and thread an M3 x 8 female-female standoff "
                 "on each from below. Screw the top board on with M3 x 6 screws, terminals to port. Flip the deck and fit the bottom board the same way. "
                 "The deck is labelled T1-T3 on top, T4-T6 underneath.",
                 "Plug the camera ribbon into the Pi's CSI connector first: the HAT sits over it. Then fit the Pi Zero with its ETH/USB HUB HAT on top "
                 "where it is labelled PI ZERO, on M2.5 x 8 standoffs (not 5 mm: the HAT's micro-USB link board hangs 6.5 mm below the Pi), header to starboard, "
                 "so the HAT's RJ45 and USB ports face the hull centreline. The USB-ETH space beside it is now where the Ethernet plug turns aft. "
                 "Bench-test both mini buck boards first: about 1 A load each (a USB load tester or a 5 ohm 5 W resistor) and check 4.9-5.2 V. Then slide clear heat-shrink "
                 "over each and stick them to the top face beside the Pi, in the USB-ETH space, with foam tape: U9A in front, U9B behind it, IN ends to the front, "
                 "about 3 mm in from the port rail. The Ethernet plug passes over them.",
                 "Underneath, mount the Pico breakout on four M3 x 10 standoffs, centred between the rails with its front edge 4 mm behind the deck's front edge, "
                 "Pico USB to the front and pins 1-20 (GP0-GP15) on the starboard side. Its terminals face the rails: every wire reaches them through a rail window, "
                 "so wire them before the deck goes into the rails, or leave the wires long and feed them through.",
                 "Slide the deck into the grooves of both rails: 212 (PORT, 12 V SIDE) and 213 (STBD, LOGIC SIDE), FWD arrows to the front. "
                 "The rails' lower windows run right up to the front end, so the wires can reach the Pico breakout's front terminals.",
                 "Fit the two Wago 221-415 blocks and both LDD-700HW drivers into the pockets on the rear face of 215 (labelled +12V, GND, LDD 1, LDD 2; TOP up) "
                 "and zip-tie them.",
                 "Cut the four M3 rods to 340 mm, file the ends square and take the sharp edge off. Thread them: nut, 215, nut, then through the rail bosses, "
                 "then 207 and a nut each side. Set 234 mm between the bulkhead inner faces, with the rods centred: each rod sticks out 73.5 mm behind "
                 "215's rear face (and about 25 mm in front of 207, where the pan-tilt base goes in 8.2). Tighten the nuts on both bulkheads.",
                 "How the sled is held in the hull: the rod tips are locating pins. Each end of each rod drops about 6 mm into one of the four plain 4 mm holes "
                 "in the end of a flange skirt (201 at the rear, 203 at the front, on the 94 mm circle at 45 deg), so the sled is trapped between the two "
                 "flanges and can't turn. Leave those eight holes plain: no heat-set inserts."], start=1),
          Paragraph("8.2  Camera pan-tilt", H3),
          Paragraph("A 100 mm dome leaves little room: the pan servo hangs under the camera, and the tilt servo stands behind it in a closed pocket in the yoke "
                    "and drives the cradle through a short wire pushrod. Both axes pass through the lens, which sits at the dome centre (the dome's sphere centre is 7.1 mm in front of its flange face), 9.5 mm above the hull axis. "
                    "Checked in the model at every angle: pan to +/- 90 deg and tilt to +/- 50 deg stay at least 1 mm inside the hull bore, the "
                    "dome flange bore (85.8 mm) and the dome (99.8 mm OD, 96 mm ID: inner radius 48 mm).", BODY),
          Table([[img(C("f_pantilt.png"), W_TXT*0.52 - 6, 2.4*inch), img(C("f_pantilt_top.png"), W_TXT*0.48 - 6, 2.4*inch)]], colWidths=[W_TXT*0.52, W_TXT*0.48]),
          Paragraph("Left: pan-tilt in the dome (dome and flange see-through). Right: base 216 with the pan servo, yoke 217 with the tilt servo, cradle 218 with the camera.", CAP),
          steps(["Centre both servos (1500 us pulse) before fitting any horn. MG90S metal-gear servos are worth the extra dollar here.",
                 "Pan servo into base 216: body down through the shelf window, shaft up and at the front end, tabs on the shelf (labelled PAN SERVO). "
                 "Two M2 servo screws through the tabs.",
                 "Screw the double-arm horn into the pocket under yoke 217 with four M2 x 6 self-tappers. Tilt servo: feed its lead down through the slot "
                 "in the yoke base first, then slide the servo into the box-shaped pocket from the port side, bottom first and shaft to port, until both tabs "
                 "sit against the pocket face. One M2 servo screw through the upper tab; the lower tab hangs free beside the base. The pocket walls take the "
                 "pushrod load, the screw only stops the servo sliding out.",
                 "Fit the yoke on the pan servo's spline, square to the front, and fix it with the horn screw through the access hole.",
                 "Screw the Arducam to cradle 218 with four M2 x 6 on 2 mm standoffs, lens forward, ribbon down through the slot.",
                 "Hang the cradle in the yoke: its D-axle through the port arm, an M2 x 8 through the starboard arm into the cradle cheek. It must swing freely.",
                 "Push lever 219 onto the D-axle outside the port arm, pointing down, and hold it with an M2 x 6 and washer into the axle end.",
                 "Pushrod: 1 mm steel wire with a Z-bend at each end, 28 mm between bends, from the tilt horn's hole 8 mm below the shaft to the lever's hole "
                 "8 mm below the axle. With the servo centred, the camera should look straight ahead; adjust by re-bending.",
                 "Slide 216 onto the four rods in front of 207 with one M3 nut behind it and one in front (the rods need about 6 mm more thread). "
                 "Run the ribbon and both servo leads back through the window in 216 and the windows in 207 to the Pi and Pico.",
                 "Set the firmware limits to pan +/- 90 deg and tilt +/- 45 deg."], start=9),
          fig(C("f_pantilt_fit.png"), "Fit check against the hull: side view at three tilt angles, top view across the pan range. Grey bands: dome flange bore.", max_h=2.6*inch),
          checklist(["Sled square on its rods; pan and tilt move through their full range by hand without touching anything; everything powers up on the bench from a 12 V supply."]),
          PageBreak()]

    # ---------------- 9 electronics
    ELEG = json.load(open(os.path.join(os.path.dirname(RD.rstrip("/")), "elec_legends.json")))
    EWIRES = json.load(open(os.path.join(os.path.dirname(RD.rstrip("/")), "elec_wires.json")))
    EPINS = json.load(open(os.path.join(os.path.dirname(RD.rstrip("/")), "elec_pins.json")))
    def efig(name, caption, max_h=3.3*inch):
        """Render with numbered callouts; the callout texts are set below it as a two-column key."""
        leg = ELEG.get(name, [])
        items = [f"<b>{i + 1}</b>  {t}" for i, t in enumerate(leg)]
        half = (len(items) + 1) // 2
        rows = [[Paragraph(items[r], CELL), Paragraph(items[r + half], CELL) if r + half < len(items) else ""] for r in range(half)]
        key = Table(rows, colWidths=[W_TXT / 2] * 2) if rows else Spacer(1, 1)
        if rows: key.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                                          ("LEFTPADDING", (0, 0), (-1, -1), 2)]))
        return KeepTogether([img(C(f"f_{name}.png"), W_TXT, max_h), Paragraph(caption, CAP), key, Spacer(1, 6)])
    def landscape(name, max_h=8.9*inch):
        """Full-page drawing turned 90 degrees (read with the page turned clockwise)."""
        from PIL import Image as _PI
        src = C(f"f_{name}.png"); dst = C(f"f_{name}_rot.png")
        _PI.open(src).rotate(90, expand=True).save(dst)
        return img(dst, W_TXT, max_h)
    S += [Paragraph("9  Electronics", H1),
          Paragraph("Everything electrical inside the hull: the parts and their reference numbers, how the boards sit on the deck, the schematic, the "
                    "wiring diagram with every wire numbered, and the order to wire and test the sled on the bench. The cables from outside connect, "
                    "and the sled goes into the hull, in section 16.", BODY),
          Paragraph("Two rules hold everywhere: <b>no Pico pin ever touches 12 V</b> (the IBT_2 logic VCC comes from the Pico's 3V3 OUT), and "
                    "<b>12 V wiring runs down the port side, logic down the starboard side</b>. Check B+ / B- polarity with a meter before the battery "
                    "ever goes on: the IBT_2 has no reverse-polarity protection, and a swapped lead kills all six boards.", NOTE),
          Paragraph("9.1  Parts and reference numbers", H3),
          Paragraph("The reference numbers used on the schematic and in the wire list. Quantities and prices are in the shopping list (section 4); "
                    "the firmware (Pico UF2, Pi bridge, topside program) is in the Firmware folder.", BODY),
          table(["Ref", "Part", "Where"], [[r, p, n] for r, q, p, n, _, _ in ELEC_SECTION],
                [0.85*inch, 2.75*inch, W_TXT - 3.6*inch]),
          PageBreak(),
          Paragraph("9.2  How it fits on the deck", H3),
          Paragraph("The deck (214) carries boards on both faces. Each top board sits directly over its bottom partner on the same four standoffs, "
                    "so one 12 V feed serves a pair: T1 over T4, T2 over T5, T3 over T6. On both faces every screw terminal faces port and every "
                    "logic header faces starboard. The deck is engraved with each board's name.", BODY),
          efig("e_layout_top", "Top face, seen from above, front of the ROV to the left. T1-T3 are the front port, front starboard and rear port thrusters."),
          efig("e_layout_bot", "Bottom face, seen from below, front to the left. T4-T6 are the rear starboard, vertical port and vertical starboard thrusters."),
          efig("e_stack", "One stacked pair from the port side: the standoffs pass through the deck slots, and the 16 AWG jumpers carry 12 V to the lower board.", max_h=2.9*inch),
          Paragraph("9.3  Schematic", H3),
          Paragraph("Two sheets. Sheet 1 is the power path and the six motor drivers; sheet 2 is the 5 V supply, the Pico, the Pi, the camera, "
                    "the servos and the LED drivers. Nets with the same name are connected (net labels instead of long wires). The pages are turned "
                    "sideways: turn the guide clockwise to read them. Full-size copies are in Images/Electronics in the package.", BODY),
          PageBreak(), landscape("elec_sch1"), PageBreak(), landscape("elec_sch2"), PageBreak(),
          Paragraph("9.4  Wiring diagram and wire list", H3),
          Paragraph("The wiring diagram shows each harness from the rear cap through the rear bulkhead to the boards, with each top board drawn above "
                    "its bottom partner. The numbers on the runs match the wire list below.", BODY),
          table(["#", "From", "To", "Wire"], [[n, a, b, w] for n, a, b, w in EWIRES], [0.35*inch, 1.9*inch, 2.4*inch, W_TXT - 4.65*inch]),
          PageBreak(), landscape("elec_wiring"), PageBreak(),
          Paragraph("9.5  How the wires run", H3),
          Paragraph("12 V feeds and the motor cores run in the curved gap between the port rail (212) and the hull wall and enter through the rail windows; "
                    "the logic harness does the same on the starboard side (213). Tie each harness to the rail at the window bars. The cables from the "
                    "rear cap pass the rear bulkhead (215) through its port window (motors, battery feeds) and starboard window (tether, DIM).", BODY),
          efig("e_rear", "Rear bay, seen from aft and above with the rear cap see-through: the bus, both fuses and the LED drivers on 215, and the four glands.", max_h=3.6*inch),
          efig("e_wire_port", "Port side: the 12 V harness. Power feeds above, the bottom-board motor cores below, and the feed up to the two 5 V bucks.", max_h=2.3*inch),
          efig("e_wire_stbd", "Starboard side: the logic harness from every header to the Pico, the DIM line aft, and the tether over the boards.", max_h=2.3*inch),
          PageBreak(),
          Paragraph("9.6  Pico and Pi Zero pins", H3),
          Paragraph("Which pin goes where, board by board, then every connection on its own line. The Pico breakout's terminal numbers are the "
                    "Pico's pin numbers. On the sled the Pico's USB faces forward with pins 1-20 on the starboard side; the Pi's header runs fore and aft.", BODY),
          img(C("f_elec_pico.png"), W_TXT, 6.9*inch), Paragraph("Pico pin map, seen from above with the USB socket at the top.", CAP),
          PageBreak(),
          img(C("f_elec_pizero.png"), W_TXT, 6.9*inch), Paragraph("Pi Zero 2W header, seen from above with the SD card at the top.", CAP),
          PageBreak(),
          Paragraph("Pin connections, one line per connection. Wire # is the wire list number (9.4); a dash is a resistor soldered at the terminal.", BODY),
          table(["Board", "Pin", "Pin name", "Connects to", "Wire #"], [[b_, str(p_), n_, t_, w_] for b_, p_, n_, t_, w_ in EPINS],
                [0.75*inch, 0.45*inch, 1.25*inch, W_TXT - 3.0*inch, 0.55*inch]),
          Paragraph("Each thruster owns one PWM slice at 20 kHz (channel A = RPWM, B = LPWM). The lights dim from GP14 at 500 Hz; the servos run at 50 Hz on slice 0. "
                    "GP26 reads the battery through the 33 k / 10 k divider (12.6 V reads 2.93 V). GP20, GP21 and GP22 are kept free for a depth sensor, an IMU and a leak probe.", SMALL),
          PageBreak(), landscape("elec_arm_servo"), PageBreak(),
          Paragraph("9.7  Wire and test the sled", H3),
          steps(["Flash the Pico before wiring: hold BOOTSEL, plug it into your computer's USB and copy Firmware/build/pico_rov.ino.uf2 onto it. "
                 "Set up the Pi Zero with Firmware/pi_bridge/SETUP.md (static address 192.168.2.2 on the tether, video server, bridge service).",
                 "Bus (wires 1-2): fit the F1 holder on the battery lead's red core and push it into the top slot of the +12V Wago; the black core goes into the "
                 "top slot of the GND Wago. Leave the 30 A fuse out for now.",
                 "Pair feeds (3-8): 14 AWG red from +12V slots 2-4 and black from GND slots 2-4 to B+ and B- of T3, T2 and T1. Run them through 215's port "
                 "window, along the outside of the port rail and in through the upper rail windows. Tie them to the rail.",
                 "Jumpers (9-11): 16 AWG red and black from each top board's B+ / B- down through the deck's port slot to the same terminals on the board below. "
                 "Tighten every screw terminal and tug-test each wire.",
                 "Aux (13-15): 20 AWG red from the +12V Wago's bottom slot through F2 (3 A); splice it to LDD 1 +Vin, LDD 2 +Vin and the IN+ of both mini bucks. "
                 "20 AWG black from the GND Wago's bottom slot, spliced the same way to both -Vin and both bucks' IN-. The buck feed runs forward "
                 "in the port trough, up through the upper rail window, and splits to the two IN ends. Solder C1 across that feed in the trough, "
                 "stripe (-) to GND. Heat-shrink every splice.",
                 "5 V (21-22): U9A OUT+ to a splice just above the deck slot behind the Pi. From there: Pi pin 2 (soldered to the HAT's stacking pin), "
                 "and down through the slot and the port lower window through D1 (band toward the Pico) to the VSYS terminal (pin 39). "
                 "U9A OUT- to the Pico GND terminal (pin 38). U9B's output feeds only the servos (next steps). Never join the two 5 V outputs; the grounds are common.",
                 "Logic (19): one bundle per board along the starboard side, outside rail 213, Dupont housings on the IBT_2 end and bare ends into the Pico's terminals "
                 "through the lower rail window: RPWM and LPWM to the board's two pins in the 9.6 table, "
                 "R_EN + L_EN to ARM (pin 20), VCC to 3V3 OUT (pin 36), GND to the board's Pico GND in 9.6 (3, 8 or 13). Splice the six VCC wires, and the six "
                 "ARM pairs, so one wire goes into each terminal; VCC crosses under the breakout to the 3V3 OUT terminal on the port side. R_IS and L_IS stay empty.",
                 "Pull-downs and sense (ARM and R1: the ARM and servo drawing before 9.7): R1 10 k from ARM (pin 20) to GND (pin 18) and R2 10 k from DIM (pin 19) to the same GND terminal (pin 18), soldered at the Pico end. "
                 "Battery sense: R3 33 k from the +12V Wago (hull side of F1) to GP26 (pin 31), R4 10 k from GP26 to AGND (pin 33).",
                 "Pi to Pico (20): Pi pin 8 (TXD) to Pico pin 2 (GP1), Pi pin 10 (RXD) to Pico pin 1 (GP0), Pi pin 6 to Pico pin 3. With the HAT on, "
                 "solder these three (and the 5 V on pin 2) to the HAT's stacking pins 2-3 mm above the HAT and heat-shrink them; a Dupont housing there "
                 "would stand too tall for the hull. The wires drop through the slot just behind the Pi, out through the starboard lower rail window and forward to the GP0, GP1 and GND terminals. Check the HAT's micro-USB link board is pushed "
                 "fully into the Pi's USB OTG port (18).",
                 "DIM (24): Pico pin 19 to both LDD DIM inputs, along the starboard side and through 215's starboard window.",
                 "Camera and servos (23): the camera ribbon from the Pi's CSI connector forward through 207's top window. Pan servo signal to GP16 (pin 21), "
                 "tilt to GP17 (pin 22); servo + and - to U9B's OUT+ / OUT-, with C2 (470 uF) across them at the plugs (same drawing). Measure U9B's output (4.9-5.2 V) before plugging the servos in.",
                 "The motor cores (12), the two light pairs (16) and the tether (17) come in through the rear cap and are connected in section 16."], start=1),
          Paragraph("Bench test, before the sled goes in the hull", H3),
          steps(["Meter, no power: +12V to GND on the Wagos must not read a short. Each IBT_2 VCC must read continuity to Pico pin 36 and none to +12V.",
                 "Pico on USB only (no battery): the servos centre, the lights stay off, ARM (pin 20) reads 0 V.",
                 "First 12 V: use a bench supply limited to 1-2 A on the battery lead, or the pack with F1 fitted and the motors not connected. "
                 "Check +5V at both buck outputs (4.9-5.2 V), 3.3 V on every IBT_2 VCC pin, and that the Pi boots and answers on 192.168.2.2.",
                 "With the topside program connected: arm, then close the program and check ARM drops within half a second. The rest of the bench "
                 "procedure (Firmware/README.md) follows once the motors are on in section 16."], start=1),
          checklist(["Polarity checked with a meter; no Pico pin connected to anything above 3.3 V; every splice heat-shrunk; harnesses tied outside "
                     "the rails; the bench test passed."]),
          PageBreak()]

    # ---------------- 9 hull
    S += [Paragraph("10  Build and test the hull", H1), parts_used(["201", "202", "203", "204"]),
          fig(C("f_hull.png"), "Hull, exploded: dome and retaining ring, front flange, hull pipe (see-through), sled, rear flange and the 4-gland end cap.", max_h=2.2*inch),
          Paragraph("Both flanges (201 rear, 203 front) push into the pipe ends: two radial O-rings seal against the bore, and three M3 screws through "
                    "the pipe wall stop them backing out. The rear cap (202) and the dome ring (204) screw into the flange faces. "
                    "Close up and test the hull EMPTY first, so a leak costs you a paper towel, not the electronics; the sled goes in afterwards.", BODY),
          Paragraph("10.1  Pipe and flanges", H3),
          steps(["Cut the 4\" pipe square at 16\" (406 mm) and deburr inside and out. Chamfer the inside edges lightly so the O-rings don't nick.",
                 "Orientation: each flange goes in with one of its six face screw holes at the very top (12 o'clock). Its four 4 mm sled holes (inside, "
                 "at the end of the skirt) then sit at 45 deg to match the rods, at both ends. Draw a pencil line along the top of the pipe at each end as your 12 o'clock.",
                 "Mark the radial holes: on each flange, put a pencil tick on the outer edge of the collar straight in line with each of the three "
                 "radial holes in the skirt. Push the flange into its pipe end without O-rings, face hole on the top line, and copy the three ticks onto "
                 "the pipe, 5 mm in from the pipe end (that is the hole centre). Pull the flange out, drill 3.4 mm through the pipe wall at the marks and "
                 "deburr inside. Write F and R on the pipe so each flange goes back in its own end in the same position. "
                 "These screws sit outboard of both O-rings, on the wet side, so they never need sealing.",
                 "Check the three radial inserts in each flange sit flush with the skirt: brass standing proud scores the pipe. Tap the six "
                 "2.5 mm holes in each flange face M3 (or let the screws cut their own thread, slowly). Leave the four sled holes plain.",
                 "Grease two AS568-238 O-rings into each flange's radial grooves."]),
          Paragraph("10.2  Front: dome", H3),
          steps(["Press the dome flange (203) into the front of the pipe, face hole on the top line, until the pipe end meets its collar; turn it slightly until the "
                 "radial inserts show through the pipe holes and fit the 3 M3 x 10.",
                 "Seat an AS568-240 face O-ring in 203's face groove (it is a snug fit in the groove; that is intended). The dome is a 100 mm acrylic dome "
                 "with a 115 mm flange: if its flange has small holes over the O-ring, fill them flush with epoxy or acrylic cement first and let it cure, "
                 "and file any edge tab flush with the 115 mm rim.",
                 "Lay the dome flange side down on the O-ring, then fit the retaining ring (204) and tighten its 6 M3 x 12 evenly in a star pattern, "
                 "a little at a time, until the ring just bottoms. Don't overtighten: acrylic cracks."], start=6),
          Paragraph("10.3  Rear cap and glands", H3),
          table(["Hole", "Thread", "Position", "Use"], [["MOTORS", "M16 x 1.5", "upper port", "12-core from the junction box (motors)"],
                                           ["LIGHTS", "M12 x 1.5", "upper starboard", "4-core from the junction box (lights)"],
                                           ["BATTERY", "M16 x 1.5", "lower starboard", "12 AWG lead from the battery pod"],
                                           ["TETHER", "M12 x 1.5", "lower port", "Cat6 tether"],
                                           ["VENT", "M10 x 1.0", "centre", "Bolt + bonded washer; hose barb for the vacuum test"]],
                [1.0*inch, 0.9*inch, 1.2*inch, W_TXT - 3.1*inch]),
          steps(["Tap each hole in the rear end cap (202) to the thread in the table; the VENT is M10 x 1.0, fine pitch, not the usual 1.5. "
                 "Each hole is labelled on the cap's outside face. Tap straight and only once: PETG threads don't like being re-cut.",
                 "Thread each gland body in from the outside with its sealing washer on the outside face and a thin smear of silicone on the threads; "
                 "snug, not tight. Fit the vent bolt with a bonded washer on the outside face (rubber lip toward the cap) and snug it, no more.",
                 "Push the real cables through their glands now, nothing connected yet, from outside in: 12-core (MOTORS, about 400 mm inside: it has to reach "
                 "T1 at the front of the deck), 4-core (LIGHTS, 200 mm), the 12 AWG battery lead (BATTERY, 250 mm) and the Cat6 tether (TETHER, 350 mm). A cable is what seals a gland: an empty gland leaks. Short 150 mm stubs of the "
                 "same cables do for the test if the real ones aren't ready. Tighten the gland nuts."], start=9),
          Paragraph("10.4  Test the empty hull", H3),
          steps(["Rear flange (201): O-rings greased, press it into the rear of the pipe (face hole at 12 o'clock) and fit its 3 radial screws. "
                 "Lay a folded dry paper towel inside.",
                 "Seat the AS568-237 face O-ring on 201 and bolt the cap on with 6 M3 x 16, labels the right way up (MOTORS upper port), in a star pattern.",
                 "Vacuum test (section 18.1): -10 inHg must hold for 15 minutes.",
                 "Dunk: strap about 4 kg to the hull (it floats hard) and sink it in a pool or tub for 30 minutes, deeper is better. Dry it off, open the "
                 "cap and check the paper towel. Any damp spot shows you which end leaked."], start=12),
          Paragraph("10.5  Then open it again", H3),
          steps(["Unbolt the cap, take out 201's three radial screws and pull the flange out again. Keep the open end covered until the sled goes in "
                 "(section 16): it is wired and tested on the bench first, where the Pico's USB is still in reach."], start=16),
          PageBreak()]

    # ---------------- 10 pod
    S += [Paragraph("11  Build the battery pod", H1), parts_used(["301", "302", "303", "305", "306"]),
          Paragraph("The battery lives in its own 3\" tube under the hull, low and close to the middle, which keeps the ROV level and stable. "
                    "Both ends get the same printed flange; the front is closed by a blank printed cap and the rear by a cap with the battery gland "
                    "and vent. The 24 cells are packed as 3S8P: three groups of 8 in parallel, the groups in series.", BODY),
          fig(C("f_pod.png"), "Pod, exploded: blank front cap, front flange, 3\" pipe, rear flange, rear cap with gland + vent. Both flanges are the same part.", max_h=1.8*inch),
          fig(C("f_pack.png"), "3S8P pack: six holder plates (305), two per group, on four M4 rods with 3 mm spacers (306) between the groups.", max_h=1.8*inch),
          steps(["Cut the 3\" pipe to 300 mm (11-13/16\"), square. Deburr and chamfer the inside of both ends.",
                 "Epoxy a flange onto each end with marine epoxy, pushed on until the pipe hits the flange's stop ledge. "
                 "Line up the bolt holes of the two flanges. Let it cure fully.",
                 "Front: grease two 72 x 2.5 O-rings onto the blank cap's plug (303, marked FRONT) and bolt it on with 6 M5 x 16.",
                 "Build the pack by docs/Battery_Pack_Build.md (cell matching, welding, BMS wiring, first charge, voltage limits): test and match the cells, fish-paper ring on every + end, "
                 "six plates (305) grooved faces out, all 24 cells + toward the rear, 8 mm pure nickel in the grooves with the centre-to-edge run doubled, "
                 "series links folded across the 3 mm gaps, four M4 rods with a 3 mm spacer (306) on each rod in both gaps. Every plate goes on with its tab notch at the top. "
                 "The pack is about 213 mm long and reads about 11.1 V.",
                 "Tap the rear cap (302): M16 x 1.5 in the hole marked BATTERY (gland), M10 x 1.0 in VENT. Fit the gland body (sealing washer outside, "
                 "silicone on the threads) and the vent bolt with a bonded washer.",
                 "Test the EMPTY pod before the pack goes in: push a 150 mm stub of the 12 AWG lead through the gland and tighten it, put a dry paper towel "
                 "inside, grease the rear cap's two 72 x 2.5 O-rings and bolt it on. Vacuum test it (section 18.1), then strap on about 2 kg, sink it for "
                 "30 minutes and check the towel. Only then open it again.",
                 "Mount the BMS on group C's rear plate, balance leads along the notch in the bottom edge. Fit the 35 A inline fuse holder at pack + "
                 "(F1, 30 A, is the second fuse, in the hull). Pass the free end of the 12 AWG battery lead (its other end is already through the hull's "
                 "BATTERY gland, section 10.3) in through the pod gland from outside and solder it to the BMS output (P+ / P-). Check polarity with a meter now and mark the red core.",
                 "Put a block of foam against the front cap, slide the pack in from the rear, grease the rear cap's two 72 x 2.5 O-rings "
                 "and bolt it on with 6 M5 x 14 (the rear cap is 2 mm thinner than the front: an M5 x 16 bottoms out), then tighten the gland on the lead. The pack can also come out the front if you ever need it."]),
          Paragraph("Charging: open the rear cap, or fit an inline waterproof connector on the battery lead and charge through it. "
                    "Always charge with the BMS in circuit, and never charge a wet pack.", NOTE),
          checklist(["Pack reads 11-12.6 V at the lead, BMS balance leads correct, both caps on, vacuum holds (section 18.1)."]),
          PageBreak()]

    # ---------------- 11 lights
    S += [Paragraph("12  Build the lights", H1), parts_used(["401", "402", "403"]),
          Paragraph("Each light is a 42 mm head: an XHP50.2 LED on a 20 mm star, bonded to an aluminium disc whose rim is in the water and carries "
                    "the heat. The cable leaves straight out of the back so it can follow the head through its sleeve in the cowl nose (section 17).", BODY),
          fig(C("f_light_ex.png"), "Light head, exploded along the beam: rear body, aluminium disc, LED, spacer, window, front ring.", max_h=1.8*inch),
          steps(["Aluminium disc (42 x 5 mm, 6061): drill a 4 mm centre hole and 3 x 2.9 mm holes on a 37 mm circle. Deburr.",
                 "Look into the rear body (401): the 6.4 mm centre hole is for the cable, the two 3 mm holes either side are the potting fill and vent, "
                 "and the three 2.1 mm holes take the screws (no inserts).",
                 "Cut about 350 mm of 2-core 18 AWG cable (OD 5-6 mm) for each light. Solder it to the LED star (red to +), pass the wires back through "
                 "the disc's centre hole and bond the star to the disc's front face with thermal adhesive, covering the hole.",
                 "Thread the cable through the rear body's centre hole from the front, so it comes straight out of the back (the round socket). "
                 "Sit the disc on the front face, its holes over the three screw holes.",
                 "Seat the 30 x 1.5 O-ring in the front ring's (402) back-face groove and the 24 x 1.5 O-ring under its lip. Drop in the glass window, "
                 "then the spacer (403), and screw the ring and disc to the rear body with 3 M2.5 x 25: they pass 16.5 mm of ring and disc, then cut their own thread in the PETG, so drive them slowly, snug, and stop.",
                 "Pot the head: stand it nose-down, pull the cable taut and dab silicone round it where it enters the centre hole. Syringe potting compound "
                 "into one 3 mm hole until it comes out of the other. When that has set, fill the round socket at the back to the brim around the cable: "
                 "that is the cable's strain relief and second seal.",
                 "Test briefly in air at low PWM only: the disc needs water to shed the heat."]),
          fig(C("f_light_as.png"), "Finished light head from behind: the cable leaves straight out of the back, potted into the round socket.", max_h=1.9*inch),
          PageBreak()]

    # ---------------- 12 stations
    S += [Paragraph("13  Station frames: join hull and pod", H1), parts_used(["601", "602", "603", "604", "605"]),
          Paragraph("Two stations, 60 mm either side of the hull centre, clamp the hull and pod together. Each is 5 printed parts: a top in two halves "
                    "(port and starboard) with the upper arms, a middle piece between the hull and the pod, and a bottom in two halves with the lower arms. "
                    "The side plates bolt to the arm ends.", BODY),
          fig(C("f_station.png"), "Both stations exploded around the hull and pod; the junction deck spans both, the box sits over the rear station.", max_h=3.0*inch),
          steps(["Push M4 nuts into the hex pockets under the middle piece's hull ears and under the bottom halves' pod ears.",
                 "Mark 60 mm ahead of and behind the hull's centre on the hull and the same on the pod. Hull upside down on a towel: lay a middle piece (603) at each mark, "
                 "then the pod in the middle pieces' lower cradles, gland end toward the rear.",
                 "Fit the two bottom halves (604 PORT, 605 STBD) under the pod at each station and bolt the pod joints: M4 x 20 through each ear into the nut.",
                 "Turn it over. Fit the two top halves (601 PORT, 602 STBD) over the hull; bolt the halves to each other through the centre rib (M3 x 20 + nyloc, no washers: the hull clamp ring is right under it) and the hull joints "
                 "with M4 x 30 down through each upper arm and ear into the middle piece's nuts.",
                 "Snug evenly so the hull and pod stay parallel. The arm ends of both stations must line up straight along each side: check with a straight edge."]),
          checklist(["Hull and pod parallel, all four arm ends of each side in line, no bolts torqued so hard they crack the PETG."]),
          PageBreak()]

    # ---------------- 13 plates + thrusters
    mixrows = [[m["name"], f'{m["x"]}, {m["z"]}', f'{m["surge"]:+.2f}', f'{m["sway"]:+.2f}', f'{m["heave"]:+.2f}', f'{m["yaw"]:+.2f}'] for m in MIX]
    S += [Paragraph("14  Side plates and thrusters", H1), parts_used(["607", "608"], extra=[("901", "Side plate, port (HDPE)", 1), ("902", "Side plate, starboard (HDPE)", 1), ("T1-T6", "Finished thrusters (section 7)", 6)]),
          Paragraph("Four horizontal thrusters sit in the corners turned 45 deg in a diamond: together they drive forward/back, sideways and turn on the spot. "
                    "The two verticals sit on the plates at the estimated centre of gravity, so going up or down doesn't pitch the nose.", BODY),
          fig(C("f_thrusters.png"), "Corner thrusters on their 45 deg brackets, verticals straight on the plates (plates shown see-through).", max_h=2.9*inch),
          steps(["Bolt each corner pylon (106) to its bracket with 4 M3 x 16 (heads in the hex pockets) "
                 "(607 bracket A, marked A FP/RS = front-port and rear-starboard; 608 bracket B, marked B FS/RP = front-starboard and rear-port). Prop end faces out, tail cone toward the hull.",
                 "Bolt the four brackets to the plates (901 port, 902 starboard) at the holes you marked 607 A / 608 B: 2 M5 x 20 from outside each plate.",
                 "Vertical thrusters (T5 port, T6 starboard): pylon straight on the plate's inside face between the two big windows, 4 M3 x 30 through "
                 "the plate with a 1 mm shim washer on each and a nyloc outside. Prop up.",
                 "Offer each plate up to the station arms and bolt it with 8 M5 x 20 (2 per arm end). Do one side, then the other.",
                 "Slide each thruster in its pylon until the duct clears everything, then tighten the pinch bolts. Spin every prop by hand: nothing may touch. "
                 "The corner jets leave through the round windows in the plates."]),
          Paragraph("Mixing (topside software)", H3),
          Paragraph("Coefficients for a + command (thrust toward the nose cone). Surge + = forward, sway + = starboard, heave + = up, yaw + = nose to port. "
                    "Per thruster: command = surge x Fx + sway x Fy + yaw x Mz (+ heave for T5/T6), then scale so no output exceeds 1. "
                    "Flip the sign for any motor wired or propped the other way.", BODY),
          table(["Thruster", "x, z (mm)", "Surge", "Sway", "Heave", "Yaw"], mixrows, [1.6*inch, 1.0*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch]),
          fig(C("f_layout.png"), "Thruster layout, top view.", max_h=3.4*inch),
          PageBreak()]

    # ---------------- 14 belly
    S += [Paragraph("15  Belly pan", H1), parts_used(["701"]),
          fig(C("f_belly.png"), "Belly pan hanging from the four lower station arms under the pod.", max_h=2.6*inch),
          steps(["Lay lead shot in sealed bags (or bar) along the pan floor: start with 1.6 kg spread evenly front to back.",
                 "Hold the pan (701) up under the four lower arms and fit an M4 x 50 up through each of its four posts into the arm inserts.",
                 "The pan is open at the top and floods; the pod above keeps the lead in place."]),
          PageBreak()]

    # ---------------- 15 junction + wiring
    S += [Paragraph("16  Junction deck and wiring", H1), parts_used(["606", "501", "503"]),
          Paragraph("The thrusters and lights plug into one junction box (501) on the frame, so only two cables enter the hull: the 12-core for the motors "
                    "and the 4-core for the lights. Each thruster lead ends in an SP13 2-pin plug, each light lead in an SP13 3-pin plug, so a thruster or "
                    "light can be unplugged and swapped without opening anything. The lid (503) covers the wiring.", BODY),
          fig(C("f_deck.png"), "Junction box over the rear station: thruster sockets on both sides, light sockets at the front, cable exits at the back.", max_h=2.3*inch),
          table(["Face", "Sockets (front to back)", "Type"],
                [["Port", "T1 front, T5 vertical, T3 rear", "SP13 2-pin"], ["Starboard", "T2 front, T6 vertical, T4 rear", "SP13 2-pin"],
                 ["Front", "L1 port, L2 starboard", "SP13 3-pin (pins 1 +, 2 -)"], ["Back", "12-CORE (motors), 4-CORE (lights)", "cable exits, potted"]],
                [W_TXT*0.18, W_TXT*0.5, W_TXT*0.32]),
          steps(["Mount the sockets: push each SP13 panel socket through its hole from outside, flat at the bottom so it only goes in one way, "
                 "and tighten the rear nut inside. The name under each hole (T1-T6, L1, L2) is the one to use.",
                 "Pass the 12-core and 4-core in through the back exits. Solder the 12-core pairs to the motor socket cups, one pair per socket, and the 4-core to the light sockets "
                 "as two separate pairs, L1 +/- and L2 +/-. Never join the two LED - wires: each LDD-700HW output is its own current loop. "
                 "Sleeve every cup with heat-shrink and note which core colours go to which socket.",
                 "Screw the deck (606) to the ribs of both stations with 4 M3 x 10 (2 into each station top), then the box to the deck where it says JUNCTION BOX, "
                 "4 M3 x 8 down through the floor.",
                 "Test every socket for continuity to the hull end of its cable before potting. Then pour potting compound in thin layers, tapping out bubbles, until it covers the "
                 "socket cups and the floor screws but stays a few mm below the lid bosses. The potting is what keeps the box waterproof: the sockets are only splash-rated. Let it cure fully.",
                 "Screw the lid (503) on with 4 M3 x 8 countersunk screws. The socket map on the lid matches the labels on the sides.",
                 "Thruster leads: from each tail gland, up the inside of the plate and over to its socket. Zip-tie to the station arms and leave a drip loop at each thruster. "
                 "Cut to length, solder on the 2-pin plug (pin 1 to the motor's red), and slide the plug's gland nut and seal on first.",
                 "Light leads are plugged in when the lights go into the cowl (section 17, Mount the lights).",
                 "Put a smear of silicone dielectric grease on each plug's pins and O-ring, push it home and tighten the coupling ring hand-tight. Wipe off the excess.",
                 "Multicores: the 12-core and 4-core already pass through the MOTORS (M16) and LIGHTS (M12) glands (section 10.3). Run them forward from "
                 "the box exits along the rear station, zip-tied, to the hull's rear cap, which hangs behind the open hull on its cables.",
                 "Battery: the 12 AWG lead already runs from the pod's rear gland to the hull's BATTERY gland. Route it straight up between the two and "
                 "tie it to the rear station.",
                 "Tether: through the TETHER gland, with a strain relief tied to a station arm so the gland never takes the pull. Inside, crimp an RJ45 on it.",
                 "Thread all four cable ends through the rear flange's (201) bore, O-rings already on it. Set the sled on the bench right behind the open hull, "
                 "camera end toward the hull, and connect it: each motor pair from the 12-core to its IBT_2's M+ / M- (wire 12, one pair per board, following "
                 "the colour note you made at the box); each 4-core pair to its LDD's +Vo / -Vo (wire 16); the battery lead red through the F1 holder into the "
                 "+12V Wago and black into the GND Wago (wires 1-2), with the 30 A fuse still OUT; the tether into the inline coupler over T1-T2, and the 0.3 m "
                 "90-degree patch lead from the coupler to the HAT's RJ45, plug turned aft. Dress every cable through 215's port or starboard window and tie it."]),
          Paragraph("First power-up, with the sled still on the bench", H3),
          Paragraph("Do this before the sled goes in: the Pico's USB faces forward at the front of the deck and can't be reached once the sled is in the hull, "
                    "and every setting that needs a new firmware build is found here.", BODY),
          steps(["Stand the ROV so all six props are clear to spin in air. Topside laptop on the tether at 192.168.2.1, gain at 25 %.",
                 "Fit F1 (30 A). Telemetry should show the battery voltage and 'armed 0'.",
                 "Work through the bench procedure in Firmware/README.md: VBAT_CAL against a meter at the Wago, link loss stops the thrusters within 0.5 s, "
                 "thruster directions (THRUSTER_DIR, one per motor: the left-hand props come out reversed) with short bursts only (the shaft seals and oil "
                 "like water, not air), camera directions (PAN_DIR, TILT_DIR).",
                 "Each change is a line in Firmware/pico_rov/config.h: edit it, rebuild in the Arduino IDE (Raspberry Pi Pico / arduino-pico core), pull F1, "
                 "and copy the new UF2 to the Pico (hold BOOTSEL, plug in USB). Set directions in software only: never swap motor wires afterwards, or the "
                 "mixing table and the code disagree. Repeat until every direction is right.",
                 "I_FULL_A needs a thruster in water: put the ROV in a tub or pool with the sled still outside the hull on its cables (keep it dry and the "
                 "hull end up), or come back to it after the first pool session (that means pulling the sled out again).",
                 "Lights: both dim smoothly from off to full on the topside slider; run them only a few seconds in air."], start=1),
          Paragraph("Sled in and close up", H3),
          steps(["Pull F1. Slide the sled into the hull from the rear, camera first and Pi on top, rods at 45 deg, feeding the cables in behind it. Push it forward "
                 "until the front rod tips drop into 203's four sled holes: it moves another 6 mm, stops, and can no longer turn. Watch through the dome: "
                 "the camera must not touch anything at full pan and tilt.",
                 "Press 201 in behind it, guiding the four rear rod tips into its sled holes, and refit its 3 radial screws. The sled should have only "
                 "1-2 mm of end play. Tuck the slack cables into the rear bay so none crosses the 12 V / logic divide or presses on the camera ribbon.",
                 "Fit F1 (the ROV is now live: see below). Wipe and re-grease the AS568-237 O-ring, seat it on 201 and bolt the cap on (MOTORS upper port, "
                 "6 M3 x 16 in a star). Tighten every gland nut last, after the cables are dressed, so no cable is twisted in its gland."], start=7),
          Paragraph("Power on and off", H3),
          Paragraph("There is no main switch yet. The ROV is live whenever both fuses are in: the 35 A fuse at the pack (in the pod) and F1 (30 A, in the hull "
                    "at the BATTERY gland). Fit F1 last, just before the rear cap goes on, and pull it whenever the hull is open. Idle, the Pi, the Pico and "
                    "the drivers draw roughly 0.3 A, so a charged pack lasts a few days switched on, but the ROV is never truly off while sealed. "
                    "A waterproof 2-pin connector rated 30 A or more in the battery lead between the pod and the hull would give an outside on/off "
                    "and a charging point without opening anything: worth adding once the ROV is working.", NOTE),
          checklist(["Every thruster spins the right way from the topside software (props off the water only briefly), both lights dim with PWM."]),
          PageBreak()]

    # ---------------- 16 cowl
    S += [Paragraph("17  Top cowl", H1), parts_used(["801", "802", "803", "804", "805", "806"]),
          Paragraph("The cowl is the only yellow part: six sections (front, middle, rear, each in a port and starboard half). It floods, "
                    "and holds the buoyancy foam and the two light heads. It is a fairing, not a lifting point: see Lifting and carrying at the end of this section.", BODY),
          fig(C("f_cowl.png"), "Cowl sections pulled apart, with the light heads at the nose.", max_h=2.6*inch),
          steps(["Lay the six sections out by their labels: 801 REAR PORT, 802 REAR STBD, 803 MID PORT, 804 MID STBD, 805 FRONT PORT, 806 FRONT STBD. "
                 "Bolt the port and starboard halves of each section together through the centre flange (M3 x 20 + nyloc), then the three sections "
                 "to each other through the seam flanges. 18 bolts in all.",
                 "Foam: cut depth-rated closed-cell foam to fit inside the cowl roof, either side of the centre flange and clear of the vertical thruster sleeves. "
                 "Start with about 1.0 L. Glue it in with epoxy so it can't shift.",
                 "Fit the lights into the cowl first (below). Then lower the cowl between the plates, plugging L1 and L2 "
                 "into the junction box as it goes down, and fix it with 4 M3 x 20 through each plate."]),
          Paragraph("Mount the lights", H2),
          Paragraph("Each light head slides into the sleeve in its corner of the cowl nose: 805 FRONT PORT takes L1, 806 FRONT STBD takes L2. "
                    "The sleeve is a 43 mm bore, 44 mm deep and open at the back. The head is 42 mm, so it slides in by hand with its last 7 mm "
                    "standing out behind the sleeve, inside the cowl, and the cable carries on aft from there. "
                    "One M3 set screw, driven down through the cowl roof and the sleeve wall, holds it.", BODY),
          Paragraph("Both sleeves are aimed 15 deg nose-down. A bare XHP50.2 throws a beam about 80 deg wide underwater "
                    "(40 deg either side), so aimed straight ahead it ended right where the camera looks at full tilt (45 deg down). "
                    "Aimed down 15 deg it covers from about 25 deg above level to 55 deg below, the camera's whole tilt range, with the "
                    "brightest part slightly below level where you look most. For anything off to the side, turn the ROV rather than panning: "
                    "the lights turn with it.", NOTE),
          Table([[img(C("f_lightsleeve.png"), W_TXT/2 - 6, 2.4*inch), img(C("f_lightmount.png"), W_TXT/2 - 6, 2.4*inch)]], colWidths=[W_TXT/2]*2),
          Paragraph("Left: port head pulled forward out of its sleeve, cable first; the set screw goes in from the top of the cowl. "
                    "Right: cowl shown clear, both leads running back to L1 and L2 on the junction box.", CAP),
          steps(["Tap the set-screw hole M3 all the way through: it starts in the cowl roof about 30 mm behind the nose, where the roof and the top of the "
                 "sleeve are one piece about 6 mm thick. One pass of an M3 tap does it.",
                 "Feed the cable into the front of the sleeve and out of the back, inside the cowl, then push the head in after it until the bottom edge of its front face "
                 "sits about 4 mm proud of the nose (the head is tilted 15 deg, so the top edge sits about flush).",
                 "Drive an M3 x 8 set screw down through the roof hole until it bites on the head, then a quarter turn more. Don't crank it: it presses on "
                 "printed plastic. A dab of threadlocker keeps it there.",
                 "Run each lead aft inside the cowl, under the foam and inboard of the vertical-thruster ducts: port head to L1, starboard head to L2. "
                 "Hold it in place inside the cowl with a few adhesive zip-tie mounts. Leave about 60 mm of slack behind each head "
                 "so it can be pulled out of the front for service.",
                 "Sit the cowl in place on the ROV to measure, then cut each lead to reach its socket with a little slack. Slide on the SP13 3-pin plug's nut and seal, and solder: pin 1 to the LED + (red), pin 2 to LED - (black); "
                 "pin 3 is not used. Grease the plug and screw it onto its socket hand-tight.",
                 "To take a light out later: unscrew the cowl and lift it enough to unplug the light at the box, back the set screw off two turns and "
                 "pull the head out of the front of the sleeve."]),
          Paragraph("<b>Lifting and carrying:</b> never by the cowl, a thruster or the dome. Stand at one end and hook your fingers through the lower corner windows "
                    "of both side plates (the 98 x 67 mm windows next to the skids), lifting on the bottom strip of each plate: there is about 100 mm of "
                    "clear space behind those windows. The upper rear windows have the cowl right behind them; don't use them. The plates carry the "
                    "whole ROV this way exactly as they do when it sits on the ground. Sand the edges inside those four windows smooth first.", NOTE),
          fig(C("f_top.png"), "Finished ROV from above.", max_h=3.0*inch),
          PageBreak()]

    # ---------------- 17 test
    S += [Paragraph("18  Leak test, trim and first dive", H1),
          Paragraph("Test in stages, so a leak costs as little as possible. The vacuum test is safe with everything inside, so do it before every dive: "
                    "a vacuum can't hurt the electronics or the cells, it only proves the seals.", BODY),
          Paragraph("18.1  Vacuum test", H3),
          steps(["Swap the VENT bolt for the M10 x 1.0 brass barb (with a bonded washer), push the hand pump's 6 mm hose on and pump to about -10 inHg.",
                 "Watch the gauge for 15 minutes. It must not move. A slow drop is a leak: re-seat and re-grease the O-rings, check each gland is "
                 "tight on its cable, and repeat. To find it, re-seat one seal at a time and test again.",
                 "Let the air back in, swap the barb for the bolt and bonded washer, snug it, no more.",
                 "Never test by blowing air INTO the hull or pod: pressure from inside pushes the dome and caps off their seals and can crack them. "
                 "-10 inHg is about the same pressure difference as 3.4 m (11 ft) of water, in the same direction as diving, so it proves the "
                 "seals but not the depth."]),
          Paragraph("18.2  Order of tests", H3),
          steps(["Empty hull and empty pod: vacuum and a 30-minute dunk with a paper towel inside (sections 10.4 and 11). Done before anything valuable goes in.",
                 "Whole ROV, everything installed, F1 in: vacuum test the hull and the pod.",
                 "Thrusters in water: the ROV in a tub or pool at the edge, each thruster at low power for a minute, then all together. Check for oil "
                 "weeping at the tail cones and that each one pushes the way the mixing table says.",
                 "First wet run: pool, tethered, no deeper than 1-2 m, 10 minutes. Lift it out, dry it, pull F1 and open the hull and the pod: "
                 "look for any water at the O-rings and glands before going on.",
                 "Trim (below), then 10 ft, 30 ft and 60 ft dives on separate days, a vacuum test before each and a look inside after each.",
                 "Measure I_FULL_A in the pool now if you didn't on the bench (section 16)."], start=1),
          Paragraph("18.3  Trim", H3),
          steps(["In the pool it should float level and just barely positive (0.2-0.4 kg): a gentle push down and it comes back up slowly.",
                 "Too buoyant: add lead in the belly pan. Rolls or wobbles: add lead low AND foam high (both make it steadier). Nose up or down: move lead "
                 "along the pan."], start=1),
          Paragraph("Starting points from the 3D model are in section 1 (Key numbers).", NOTE),
          PageBreak()]

    # ---------------- 18 reference
    S += [Paragraph("19  Reference views and layout", H1),
          fig(C("f_side.png"), "Side view.", max_h=2.6*inch), fig(C("f_open.png"), "Cowl and port plate removed.", max_h=3.3*inch), PageBreak(),
          fig(C("f_exploded.png"), "Exploded.", max_h=3.4*inch), fig(C("f_under.png"), "From below.", max_h=2.6*inch),
          table(["Item", "z (mm)", "Notes"], [
              ["Side plates (HDPE)", "-238 to +240", "x +/-156.5 to 169.2 (12.7 thick), y -202 (skid edge) to +98 (300 mm tall)"],
              ["Rear station", "-72 to -48", "Junction deck on top, under the box"], ["Front station", "+48 to +72", "Front end of the junction deck"],
              ["Vertical thrusters", "-8", "T5 / T6 on the plates"], ["Corner thrusters", "about +/-118", "T1-T4 on 45 deg brackets"],
              ["Top cowl", "-212 to +236", "Splits at -62 and +87, and on the centreline"],
              ["Belly pan", "-112 to +112", "Under the pod"], ["Hull / dome", "-223 to +270", "Electronics only"],
              ["Battery pod", "-162 to +188", "Axis 116 mm below the hull; printed flange + cap at both ends"]],
              [1.6*inch, 1.2*inch, W_TXT - 2.8*inch])]

    # ---------------- Appendix A: side plate templates (the template PDF's own pages follow this divider, unscaled)
    S += [PageBreak(), Paragraph("Appendix A  Side plate cutting templates (1:1)", H1),
          Paragraph(f"The next 9 pages ({app_pages()}) are the full-size cutting templates for side plates 901 (port) and 902 (starboard): "
                    "an instruction page with the sheet layout, then four tiles per plate (A1, A2, B1, B2), every hole marked with its drill size and "
                    "part tag. Print only these pages, landscape on Letter, and cut the plates as section 6 describes.", BODY)]
    doc.build(S)
    from pypdf import PdfReader, PdfWriter                 # append the template pages untouched, so they stay 1:1
    w = PdfWriter(); w.append(PdfReader(path)); w.append(PdfReader(TEMPLATE_PDF))
    pb = path + ".appb.pdf"; build_appendix_b(pb, len(w.pages)); w.append(PdfReader(pb)); os.remove(pb)
    w.add_metadata({"/Title": f"{BRAND} Build Guide", "/Author": "Brian"})
    with open(path, "wb") as fh: w.write(fh)

# ------------------------------------------------------------------ Appendix B: insert chart + picture-by-picture assembly
APPB = {"n": 0}
INS = json.load(open(os.path.join(os.path.dirname(RD.rstrip("/")), "inserts.json")))
ICOL = {"M3": "#f28c28", "M4": "#2f7de1", "M5": "#d63384"}
# where each insert goes, in words (the render shows it with arrows)
IWHERE = {"106": "pinch ears, pressed in from the side the arrows show",
          "201": "radial holes in the skirt, from outside, flush. The 4 sled holes stay plain",
          "203": "radial holes in the skirt, from outside, flush. The 4 sled holes stay plain",
          "301": "flange face, around the bore",
          "501": "lid bosses in the 4 top corners",
          "601": "M5: arm end, from the outer face. M3: top of the deck rib",
          "602": "M5: arm end, from the outer face. M3: top of the deck rib",
          "604": "M5: arm end, from the outer face. M4: under the lower arm (belly pan hanger)",
          "605": "M5: arm end, from the outer face. M4: under the lower arm (belly pan hanger)",
          "606": "from the top, for the junction box floor screws",
          "607": "M3: the 45 deg face (pylon). M5: the plate face",
          "608": "M3: the 45 deg face (pylon). M5: the plate face",
          "801": "cowl foot, from the outside face", "802": "cowl foot, from the outside face",
          "803": "cowl feet, from the outside face", "804": "cowl feet, from the outside face",
          "805": "cowl foot, from the outside face", "806": "cowl foot, from the outside face"}

def _pf(stem):
    a = C(f"pf_{stem}.png")
    return a if os.path.exists(a) else C(f"pf_{pn(stem)}_{base(stem)}.png")

def _ins_text(p):
    if p not in INS: return "<font color='#8a939b'>No inserts</font>"
    c = INS[p]["count"]
    parts = [f"<font color='{ICOL[k]}'><b>{c[k]} x {k}</b></font>" for k in ("M3", "M4", "M5") if k in c]
    return " + ".join(parts) + f"<br/><font size='6.2'>{IWHERE[p]}</font>"

def insert_chart():
    out = [Paragraph("Appendix B  Heat-set insert chart and picture-by-picture assembly", H1),
           Paragraph("Every printed part, by part number. Arrows point into each hole that takes a heat-set insert, coloured by size; "
                     "parts in grey boxes take none. Press inserts with the iron at 230-245 C and a light push, keep the insert square, "
                     "and stop flush (proud brass stops parts sitting flat or scores the pipe). Count per part, not per set: x2 parts need it twice.", BODY)]
    key = Table([[Paragraph(f"<font color='{ICOL[k]}'><b>{k}</b></font>  {d}", CELL) for k, d in
                  (("M3", "insert hole 4.0 mm"), ("M4", "insert hole 5.6 mm"), ("M5", "insert hole 6.4 mm"))] +
                 [Paragraph("Totals for one ROV: <b>42 x M3, 16 x M4, 36 x M5</b>", CELL)]],
                colWidths=[1.25*inch, 1.25*inch, 1.25*inch, W_TXT - 3.75*inch])
    key.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, G.RULE), ("BACKGROUND", (0, 0), (-1, -1), G.SOFT), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    out += [key, Spacer(1, 6)]
    NC = 5; cw = W_TXT / NC
    cells, row, st = [], [], [("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                              ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                              ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                              ("INNERGRID", (0, 0), (-1, -1), 0.4, G.RULE), ("BOX", (0, 0), (-1, -1), 0.6, G.RULE)]
    for sec, stem, src, qty, *_ in sorted(PRINTED, key=lambda r: pn(r[1])):
        p = pn(stem); y = is_yellow(stem); has = p in INS
        im = img(C(f"f_ins_{p}.png") if has else _pf(stem), cw - 6, 1.08*inch)
        chip = Paragraph(f"<b>{p}</b>", ParagraphStyle("ic", parent=CELL, alignment=TA_CENTER, textColor=G.INK if y else colors.white, fontSize=8.5))
        chipt = Table([[chip]], colWidths=[0.42*inch]); chipt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), YEL if y else BLK),
                                                                                    ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
        cap = ParagraphStyle("icap", parent=CELL, alignment=TA_CENTER, fontSize=6.6, leading=8)
        row.append([chipt, im, Paragraph(f"{_use(stem)}  <b>x{qty}</b>", cap), Paragraph(_ins_text(p), cap)])
        if not has: st.append(("BACKGROUND", (len(row) - 1, len(cells)), (len(row) - 1, len(cells)), colors.HexColor("#eef0f2")))
        if len(row) == NC: cells.append(row); row = []
    if row: cells.append(row + [""] * (NC - len(row)))
    g = Table(cells, colWidths=[cw] * NC)                     # rows grow with their captions
    g.setStyle(TableStyle(st)); out.append(g)
    return out

def _chips(pns, hw):
    """IKEA 'you need' strip: printed parts as small pictures with part number and count, then the hardware as text boxes"""
    items = []
    for p, q in pns:
        k = p.split("/")[0]; qs = f"x{q}" if isinstance(q, int) else q
        if k in BY_PN:
            stem = BY_PN[k]
            items.append([img(_pf(stem), 0.62*inch, 0.5*inch),
                          Paragraph(f"<b>{p}</b> {qs}", ParagraphStyle("cp", parent=CELL, alignment=TA_CENTER, fontSize=7))])
        else:
            items.append([Paragraph(f"<b>{p}</b>", ParagraphStyle("cp2", parent=CELL, alignment=TA_CENTER, fontSize=8)),
                          Paragraph(qs, ParagraphStyle("cp", parent=CELL, alignment=TA_CENTER, fontSize=7))])
    n = 9; cw = W_TXT / n
    rows = [items[i:i + n] + [""] * (n - len(items[i:i + n])) for i in range(0, len(items), n)] or [[""] * n]
    pt = Table(rows, colWidths=[cw] * n)
    pt.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 1), ("RIGHTPADDING", (0, 0), (-1, -1), 1)]))
    hs = ParagraphStyle("hw", parent=CELL, fontSize=7.4, leading=9)
    hrow = [Paragraph(h, hs) for h in hw]; m = 4
    hrows = [hrow[i:i + m] + [""] * (m - len(hrow[i:i + m])) for i in range(0, len(hrow), m)]
    ht = Table(hrows, colWidths=[(W_TXT - 12) / m] * m)
    hst = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
    for r, rr in enumerate(hrows):
        for c, v in enumerate(rr):
            if v != "": hst += [("BOX", (c, r), (c, r), 0.6, G.INK)]
    ht.setStyle(TableStyle(hst))
    box = Table([[Paragraph("<b>YOU NEED</b>", ParagraphStyle("yn", parent=SMALL, textColor=G.MUTED))], [pt], [ht]], colWidths=[W_TXT])
    box.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, G.RULE), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 2),
                             ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return box

def ikea_step(no, title, sec, image, pns, hw, mult="", img_h=2.05*inch):
    big = ParagraphStyle("bn", parent=H1, fontSize=34, leading=38, textColor=colors.white, alignment=TA_CENTER)
    head = Table([[Paragraph(str(no), big), Paragraph(f"{title}", ParagraphStyle("bt", parent=H1, fontSize=18, leading=21)),
                   Paragraph(f"<b>{mult}</b>", ParagraphStyle("bm", parent=H1, fontSize=22, leading=26, alignment=2, textColor=G.ACCENT))],
                  [ "", Paragraph(f"Full instructions: section {sec}", SMALL), ""]],
                 colWidths=[0.8*inch, W_TXT - 1.6*inch, 0.8*inch])
    head.setStyle(TableStyle([("SPAN", (0, 0), (0, 1)), ("BACKGROUND", (0, 0), (0, 1), BLK), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                              ("SPAN", (2, 0), (2, 1)), ("LEFTPADDING", (1, 0), (1, -1), 10)]))
    return [KeepTogether([head, Spacer(1, 4), img(C(image), W_TXT, img_h), Spacer(1, 4), _chips(pns, hw)]), Spacer(1, 16)]

IKEA = [   # (title, guide section, picture, printed parts, hardware[, multiplier])
    ('Thrusters', '7', 'f_thr_ex.png', [('101', 1), ('102', 1), ('103/104', 1), ('105', 1), ('106', 1), ('107', 'gauge')], ['1200 GPH motor', 'Brass coupler + M5 x 20 set screw', 'M5 jam nut + M5 nyloc', '3 x M3 x 8 button (nose)', 'M12 x 1.5 gland', '32 x 2 O-ring', '2 x M4 set screw (oil ports)', '2 x M4 x 30 (pylon)', 'Nitrile finger cot + 5 x 1.5 O-ring', 'Mineral oil'], 'x6'),
    ('Electronics sled', '8.1 and 9', 'f_ik_sled.png', [('207', 1), ('212', 1), ('213', 1), ('214', 1), ('215', 1)], ['4 x M3 threaded rod, 340 mm', '16 x M3 nut', 'IBT_2 boards, Pi, Pico (section 9)', 'Wago 221-415 x2, LDD-700HW x2']),
    ('Camera pan-tilt', '8.2', 'f_ik_pantilt.png', [('216', 1), ('217', 1), ('218', 1), ('219', 1)], ['2 x MG90S servo', 'Arducam + 4 x M2 x 6, 2 mm standoffs', 'M2 screws (servo, axle)', '1 mm steel wire pushrod', '8 x M3 nut']),
    ('Hull: build it and test it empty', '10', 'f_ik_hull.png', [('201', 1), ('202', 1), ('203', 1), ('204', 1)], ['4" pipe, 406 mm', '4 x AS568-238 O-ring', 'AS568-240 + -237 O-rings', '6 x M3 x 10 (radial)', '6 x M3 x 16 (cap)', '6 x M3 x 12 (ring)', '100 mm acrylic dome', '2 x M16 + 2 x M12 gland, M10 vent bolt']),
    ('Battery pod', '11', 'f_ik_pod.png', [('301', 2), ('302', 1), ('303', 1), ('305', 6), ('306', 8)], ['3" pipe, 300 mm', '4 x 72 x 2.5 O-ring', '6 x M5 x 16 (front)', '6 x M5 x 14 (rear)', '4 x M4 rod, about 225 mm', '24 x 18650 cells (3S8P)', 'BMS + 35 A fuse', 'M16 gland, M10 vent bolt', 'Marine epoxy']),
    ('Light heads', '12', 'f_light_ex.png', [('401', 1), ('402', 1), ('403', 1)], ['Aluminium disc 42 x 5', 'XHP50.2 LED on 20 mm star', 'Glass window', '30 x 1.5 + 24 x 1.5 O-ring', '3 x M2.5 x 25', '2-core 18 AWG, 350 mm', 'Thermal adhesive, potting'], 'x2'),
    ('Station frames: join hull and pod', '13', 'f_ik_stations.png', [('601', 2), ('602', 2), ('603', 2), ('604', 2), ('605', 2)], ['M4 x 30 (hull joints)', 'M4 x 20 (pod joints)', 'M3 x 20 + nyloc (centre rib)', 'M4 nuts in the hex pockets']),
    ('Side plates and thrusters', '14', 'f_ik_plates.png', [('607', 2), ('608', 2), ('901', 1), ('902', 1), ('T1-T6', 6)], ['16 x M3 x 16 (pylons to brackets)', '8 x M5 x 20 (brackets)', '16 x M5 x 20 (plates to arms)', '8 x M3 x 30 + nyloc + 1 mm shim (verticals)']),
    ('Belly pan', '15', 'f_ik_belly.png', [('701', 1)], ['4 x M4 x 50', '1.6 kg lead shot in sealed bags']),
    ('Junction box', '16', 'f_ik_jbox.png', [('606', 1), ('501', 1), ('503', 1)], ['6 x SP13 2-pin socket', '2 x SP13 3-pin socket', '2 x M3 x 10 (deck)', '4 x M3 x 8 (box)', '4 x M3 x 8 countersunk (lid)', '12-core + 4-core cable', 'Potting compound']),
    ('Wire it, test it on the bench, slide the sled in', '16', 'f_ik_sledin.png', [('201', 1), ('202', 1)], ['F1 fuse, 30 A', 'AS568-237 O-ring (re-greased)', '6 x M3 x 16', 'Patch lead + RJ45 coupler']),
    ('Lights and top cowl', '17', 'f_ik_cowl.png', [('801', 1), ('802', 1), ('803', 1), ('804', 1), ('805', 1), ('806', 1)], ['18 x M3 x 20 + nyloc (cowl joints)', '8 x M3 x 20 (cowl to plates)', '2 x M3 x 8 set screw', 'About 1.0 L closed-cell foam', '2 x SP13 3-pin plug', 'Adhesive tie mounts']),
]

class Mark(Flowable):
    """zero-size flowable that records the page it lands on (MARKS[name], page number within its document)"""
    def __init__(self, name): super().__init__(); self.name = name
    def wrap(self, *a): return (0, 0)
    def draw(self): MARKS[self.name] = self.canv.getPageNumber()
MARKS = {}

# ------------------------------------------------------------------ Appendix C: parts and lists from earlier releases
# One row per change that affects something already printed, cut, bought or assembled. The build steps describe only the current parts.
RETRO = [
 ("Hull flanges 201, 203, rear cap 202, pod flanges 301, caps 302 / 303, light front rings 402", "Printed before 2026-10-20",
  "Printed at 25 % infill: water can seep through the skin into the infill and past the O-rings.",
  "Reprint them (TinkerSub_KB-1_Reprint_2026-10-20.3mf prints them solid), or give every outside surface that sees water two thin coats of epoxy, "
  "keeping it out of the O-ring grooves, the sealing faces and the threads."),
 ("Side plates 901 / 902", "Cut from templates printed before 2026-10-20",
  "The rearmost COWL FOOT hole is 15 mm too far back, behind the end of the cowl.",
  "Drill one new 3.5 mm hole in each plate 38 mm from the rear end and 62 mm below the top edge. Leave the old hole empty."),
 ("Top cowl 801-806", "Printed before 2026-10-23",
  "Before 2026-10-20 the side walls stopped above the foot (a loose strip with a slot beside it); before 2026-10-23 the section-seam holes were "
  "closed by the flange ramps and some seam bolts had no room for a head.", "Reprint all six sections from the current files."),
 ("Pan-tilt base 216", "Printed before 2026-10-20", "The pan servo shelf hung on two thin rails, the weakness that broke the first yoke.",
  "Reprint it (it is in the Reprint project)."),
 ("Pan-tilt yoke 217", "Printed before 2026-10-16", "The tilt servo sat in a thin frame that snaps off at its base.", "Reprint it (in the Reprint project)."),
 ("Sled rails 212 / 213", "Printed before 2026-10-16", "The lower windows stop short of the front, so the wires can't reach the Pico breakout's front terminals.",
  "Cut a 20 x 20 mm opening with a rotary tool from the front of the lower window to 3.5 mm from the rail's front end."),
 ("Hull flanges 201 / 203, sled holes", "Built from a guide before 2026-10-19", "Heat-set inserts fitted in the four sled holes at the end of each skirt.",
  "Drill each insert's thread out with a 3.2 mm bit so the rod tips slide in."),
 ("Thrusters: coupler and stud", "Assembled from a guide before 2026-10-23", "The M5 stud went in before the coupler gauge, so the stud hit the gauge's ceiling and the coupler sits too low.",
  "Loosen the coupler's grub screw, back the stud out, set the height with gauge 107 (section 7.2), then refit the stud."),
 ("Station tops 601 / 602", "Printed before 2026-10-23", "The arm-end inserts are 0.75 mm lower than the plate holes.",
  "Open the four upper holes in each plate to 7 mm (9/32\") and put a washer under each screw head. The centre rib takes the same M3 screw as the new part."),
 ("Light rear body 401", "Printed before 2026-10-23", "The three screw holes are 8 mm deep; the screws bottom out.", "Drill each to 12 mm with a 2.1 mm (5/64\") bit."),
 ("Belly pan 701", "Printed before 2026-10-23", "The hanger holes stop 16 mm short of the bottom of each post.",
  "Drill each through from the top with a 4.5 mm (11/64\") bit; the hole guides the drill."),
 ("Tail cones 102", "Printed before 2026-10-25", "The compensator nipple is tucked under the spigot lip, where a finger cot is very hard to fit.",
  "Reprint them, about 25 g each."),
 ("Junction deck 606", "Printed before 2026-10-26", "Shorter: it reaches only the rear station and flexes.", "Reprint it (Frame plate 5); it screws to both stations."),
 ("Screws", "Bought from a list before 2026-10-23", "Some lengths were wrong.",
  "Use the shopping list in section 4. Changed: plates to arms and brackets 20 mm (was 25), pylons to brackets 16 mm (was 12), vertical pylons 30 mm "
  "(was 25), dome ring 12 mm (was 16), pod rear cap 14 mm, nose cones 8 mm (was 6), belly pan 50 mm (was 30), centre rib now M3 + nyloc."),
 ("O-rings", "Bought from a list before 2026-10-25", "Wrong sizes for their grooves.",
  "Hull radial seals AS568-238 (was -240), rear cap face AS568-237 (was -239), pod caps 72 x 2.5 (was 74), light front ring 30 x 1.5 (was 31). "
  "The dome face AS568-240 and the others were right."),
]

def appendix_c():
    return [Paragraph("Appendix C  Updating parts from an earlier build", H1),
            Paragraph("The build steps describe only the current parts. If you printed, cut, bought or assembled anything from an earlier release, "
                      "find it here: what changed and how to bring it up to date. CHANGELOG.md has the full history.", BODY),
            table(["Part", "If yours is", "What was wrong", "What to do"], [list(row) for row in RETRO],
                  [1.35*inch, 1.05*inch, 2.0*inch, W_TXT - 4.4*inch])]

def build_appendix_b(path, before):
    """Appendix B as its own PDF, numbered on from the guide + template pages; build_pdf appends it last."""
    doc = BaseDocTemplate(path, pagesize=letter, leftMargin=0.75*inch, rightMargin=0.75*inch, topMargin=0.6*inch, bottomMargin=0.75*inch,
                          title=f"{BRAND} Build Guide, Appendix B")
    def op(c, d):
        c.saveState(); c.setStrokeColor(G.RULE); c.setLineWidth(0.6)
        c.line(0.75*inch, 0.6*inch, letter[0] - 0.75*inch, 0.6*inch)
        c.setFont("Helvetica", 7.5); c.setFillColor(G.MUTED)
        c.drawString(0.75*inch, 0.42*inch, f"{BRAND} Build Guide  |  Appendices B and C")
        c.drawRightString(letter[0] - 0.75*inch, 0.42*inch, f"Page {before + d.page}"); c.restoreState()
    doc.addPageTemplates([PageTemplate("b", [Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")], onPage=op)])
    S = insert_chart() + [Spacer(1, 14),
         Paragraph("Picture-by-picture assembly", H1),
         Paragraph("A quick visual reference, one panel per stage in build order: the new parts in colour, pulled out along dashed lines to "
                   "where they go, with what is already built in light grey, and what you need for that stage. The steps are in the section "
                   "named on each panel.", BODY),
         Spacer(1, 6), img(C("f_exploded.png"), W_TXT, 4.4*inch),
         Paragraph("The whole ROV pulled apart. Build order: thrusters, sled, pan-tilt, hull, pod, lights, stations, plates, belly pan, "
                   "junction box, wiring and sled, cowl.", CAP), PageBreak()]
    for i, (title, sec, image, pns, hw, *m) in enumerate(IKEA, 1):
        S += ikea_step(i, title, sec, image, pns, hw, *(m[:1]))   # each stage kept whole; they flow two to a page where they fit
    S.append(PageBreak())
    S += [Paragraph("Done", ParagraphStyle("dn", parent=H1, fontSize=26, leading=30)),
          img(C("f_front.png"), W_TXT, 4.6*inch), Spacer(1, 8),
          Paragraph("Before the first dive: leak tests, trim and the staged dives in section 18.", BODY), PageBreak(),
          Mark("cfirst")] + appendix_c()
    doc.build(S)
    from pypdf import PdfReader
    APPB["n"] = len(PdfReader(path).pages); APPB["c_at"] = before + MARKS["cfirst"]

if __name__ == "__main__":
    build_package()
    out = os.path.join(PKG, f"{FP}_Assembly_Guide.pdf")
    build_pdf(out)                                        # first pass: find where Appendix A and B land
    from pypdf import PdfReader
    n_tpl = len(PdfReader(TEMPLATE_PDF).pages)
    APP["blast"] = len(PdfReader(out).pages); APP["last"] = APP["blast"] - APPB["n"]; APP["first"] = APP["last"] - n_tpl + 1
    APP["cfirst"] = APPB["c_at"]
    build_pdf(out)                                        # second pass with the page numbers in the text
    assert len(PdfReader(out).pages) == APP["blast"], "page count moved between passes"
    print("done", PKG, "black g", G_B, "yellow g", G_Y)
