"""
Builds the ROV build package: BOM CSVs, assembly guide PDF, folder of STLs / images / sources.
Usage: python3 build_guide.py <render_dir> <out_dir>
"""
import sys, os, csv, json, shutil, datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Image, Table, TableStyle,
                                PageBreak, KeepTogether, NextPageTemplate, CondPageBreak)
from PIL import Image as PILImage

RD, OUT = sys.argv[1], sys.argv[2]
CROP = os.path.join(RD, "crop")
VOLS = json.load(open(os.path.join(os.path.dirname(RD.rstrip("/")), "vols.json")))
PKG = os.path.join(OUT, "ROV_Build_Package")
TODAY = datetime.date.today().strftime("%B %-d, %Y")

# ------------------------------------------------------------------ printed parts
# (section, file stem, source dir, qty, material, orientation / print notes, used in)
CAM = "rov_project/camera_mount"
PRINTED = [
 ("Thrusters", "housing_no_foot", "out", 6, "PETG", "Threaded rear end down, brim, no supports. 5 walls (thread + O-ring seat).", "Thruster body + Kort duct"),
 ("Thrusters", "tail_cone_comp", "out", 6, "PETG", "Tip down, brim. Tap the tip M12x1.5 after printing.", "Thruster tail, oil compensator"),
 ("Thrusters", "prop_hub_RH", "out", 3, "PETG", "Back face down, tree supports under the blades only.", "Right-hand prop, one per pair"),
 ("Thrusters", "prop_hub_LH", "out", 3, "PETG", "Back face down, tree supports under the blades only.", "Left-hand prop, one per pair"),
 ("Thrusters", "nose_cone", "out", 6, "PETG", "Base down, no supports.", "Prop spinner"),
 ("Thrusters", "pylon_clamp", "out", 6, "PETG", "Rear end down, no supports. 2x M4 + 4x M3 heat-set inserts.", "Clamps each thruster body to a pad"),
 ("Tools", "coupler_gauge", "out", 1, "Any", "As exported. Tool only.", "Sets coupler height (1 mm below the face)"),
 ("Frame", "rov_frame_clamp_top_cap", "out", 3, "PETG", "Flat face down, no supports.", "Hull top half + upper rail bosses (all 3 stations)"),
 ("Frame", "rov_frame_clamp_corner", "out", 2, "PETG", "Flat face down, no supports. 8x M3 heat-set inserts (4 per 45 deg pad).", "Front + rear clamp body: hull + pod, corner thruster pads"),
 ("Frame", "rov_frame_clamp_mid", "out", 1, "PETG", "Flat face down, no supports. 8x M3 heat-set inserts.", "Mid clamp body: hull + pod, vertical thruster pads"),
 ("Frame", "rov_frame_clamp_pod", "out", 3, "PETG", "Flat face down, no supports. Tap the 2 skid grub screw holes M3.", "Pod bottom half + skid legs (all 3 stations)"),
 ("Frame", "rov_lead_tray_50", "out", 2, "PETG", "Standing on its end, no supports.", "Lead ballast, one each side of the mid clamp"),
 ("Frame", "rov_junction_bridge", "out", 1, "PETG", "Standing on its end (rings vertical), no supports. 4x M3 heat-set inserts.", "Carries both junction boxes across the upper rails"),
 ("Frame", "rov_junction_box_6", "out", 1, "PETG", "Base down, no supports.", "Potted junction: 6 thruster leads in, 1 multicore out"),
 ("Frame", "rov_junction_box_2", "out", 1, "PETG", "Base down, no supports.", "Potted junction: 2 light leads in, 1 cable out"),
 ("Hull + sled", "br_flange_rear", "rov_project", 1, "PETG", "Ring face down.", "Hull rear flange (yours)"),
 ("Hull + sled", "rov_endcap_rear_5hole", "out", 1, "PETG", "Flat. Tap 2x M16x1.5, 2x M12x1.5, vent.", "Hull rear cap: 4 glands + vent"),
 ("Hull + sled", "br_flange_front_dome", "rov_project", 1, "PETG", "Ring face down.", "Dome flange (yours)"),
 ("Hull + sled", "dome_retaining_ring", "rov_project", 1, "PETG", "Flat. Check dome flange thickness first.", "Dome clamp ring (yours)"),
 ("Hull + sled", "ETRAY4-ROV-TRAY-R2", "rov_project", 1, "PETG", "Flat.", "Electronics tray (yours)"),
 ("Hull + sled", "rov_sled_bulkhead_rear", "out", 1, "PETG", "Flat face down, boss up, no supports.", "Sled rear bulkhead: tray prongs, 4 rods, wiring windows"),
 ("Hull + sled", "m03r7-001-00a", CAM, 1, "PETG", "Flat, as supplied.", "Front bulkhead (yours)"),
 ("Hull + sled", "m03r7-002-00a", CAM, 1, "PETG", "As supplied.", "Camera mount frame (yours)"),
 ("Hull + sled", "m03r7-003-00a", CAM, 1, "PETG", "As supplied.", "Camera mount bracket (yours)"),
 ("Hull + sled", "m03r7-004-00a", CAM, 1, "PETG", "As supplied.", "Camera mount bracket (yours)"),
 ("Hull + sled", "m03r7-005-00a", CAM, 1, "PETG", "As supplied.", "Camera housing (yours)"),
 ("Battery pod", "rov_pod_flange_3in", "out", 1, "PETG", "Socket end down, no supports. 6x M5 heat-set inserts.", "3\" pod rear flange (glued on)"),
 ("Battery pod", "rov_pod_endcap_3in", "out", 1, "PETG", "Plate down. Tap M16x1.5 (battery) + M10 vent.", "3\" pod rear cap, 2 radial O-rings"),
 ("Battery pod", "rov_cell_plate_8", "out", 6, "PETG", "Flat, pockets up.", "18650 holder plate, 8 cells (2 per group)"),
 ("Lights", "rov_light_rear_body", "out", 2, "PETG or ASA", "Socket end down, no supports. 3x M2.5 heat-set inserts.", "Light head: rail socket + potting cavity"),
 ("Lights", "rov_light_front_ring", "out", 2, "PETG or ASA", "Front face down, no supports.", "Light head: window retainer"),
 ("Lights", "rov_light_spacer", "out", 2, "PETG or ASA", "Flat.", "Holds the window off the LED"),
]
SECTION_DIR = {"Thrusters": "1_Thrusters", "Tools": "1_Thrusters", "Frame": "2_Frame_clamps_and_junctions",
               "Hull + sled": "3_Hull_and_sled", "Battery pod": "4_Battery_pod", "Lights": "5_Lights"}

def grams(stem, qty):
    v, ext = VOLS[stem]
    fill = 0.9 if min(ext) <= 10 else 0.55            # thin plates print near solid; chunky parts ~4 walls / 25 %
    return round(v * 1.27 * fill * qty)                # PETG 1.27 g/cm3

# ------------------------------------------------------------------ hardware
# (group, qty, component, description, approx cost USD, source)
HW = [
 ("Thrusters (x6)", "6", "1200 GPH bilge pump motor cartridge", "35.7 x 57.3 mm, 80.1 mm overall. 4 on hand, 2 to buy", "$20-25 each", "Amazon / marine store"),
 ("Thrusters (x6)", "6", "Brass shaft coupler 3 -> 5 mm, 9 x 20 mm", "Ream the 3 mm end to 1/8\" (3.17 mm)", "$8 (2 more)", "Amazon"),
 ("Thrusters (x6)", "6 / 6 / 6", "M5 x 20 set screw, M5 hex nut, M5 nyloc", "Stud, jam nut (drives the hub), hub retainer. Stainless", "$8", "Hardware store"),
 ("Thrusters (x6)", "18", "M3 x 6 button head screw", "Nose cone to hub spigot", "$4", "Hardware store"),
 ("Thrusters (x6)", "6", "O-ring 32 x 2 mm, nitrile", "Tail cone spigot", "$6 (kit)", "Amazon"),
 ("Thrusters (x6)", "6", "Cable gland M12 x 1.5, nylon IP68, 3-6.5 mm", "Tail cone tip", "$8 (pack of 10)", "Amazon"),
 ("Thrusters (x6)", "12", "M4 set screw + thread sealant", "Oil fill and bleed ports", "$4", "Hardware store"),
 ("Thrusters (x6)", "6", "Nitrile finger cot", "Compensator bladder", "$6 (pack)", "Pharmacy / Amazon"),
 ("Thrusters (x6)", "1", "Mineral oil, 500 ml", "About 30-50 ml per thruster", "$6", "Pharmacy"),
 ("Thrusters (x6)", "12 + 12", "M4 x 30 SHCS + M4 heat-set inserts", "Pylon clamp pinch bolts", "$10", "Amazon"),
 ("Thrusters (x6)", "24", "M3 x 16 SHCS", "Pylon to clamp pad (4 each)", "$5", "Hardware store"),
 ("Frame", "40", "M3 heat-set inserts (kit)", "24 thruster pads, 4 junction bridge, + spares", "$10 (kit)", "Amazon"),
 ("Frame", "24 + 24", "M4 x 20 SHCS + M4 hex nuts", "Clamp joints: 8 per station (hull pair + pod pair), nuts in the pockets", "$8", "Hardware store"),
 ("Frame", "6", "M3 x 8 set screw", "Skid grub screws (2 per pod cap)", "$3", "Hardware store"),
 ("Frame", "2 + 2", "M3 x 20 SHCS + M3 nuts", "Junction bridge rail pinch screws", "(stock)", "-"),
 ("Frame", "4", "M3 x 10 SHCS", "Junction boxes to the bridge (heads get potted)", "(stock)", "-"),
 ("Frame", "~1.4 kg", "Lead shot (in bags) or lead bar", "Ballast in the two lead trays; trim in the water", "$15", "Sporting goods"),
 ("Frame", "1 pack", "UV-resistant zip ties, 3.6 mm", "Lead trays, cable dressing", "$5", "Hardware store"),
 ("Hull", "1", "4\" Sch40 PVC pipe, 16\" (406 mm)", "Main hull, electronics only", "$15 (2 ft)", "Hardware store"),
 ("Hull", "1", "4\" acrylic CCTV dome, 100 mm", "UQISOVI, Amazon B0DR2HP4YQ", "$15-25", "Amazon"),
 ("Hull", "4", "O-ring AS568-240", "Radial seals, 2 per hull flange", "$6", "Amazon / McMaster"),
 ("Hull", "1 + 1", "O-ring AS568-239, AS568-242", "Rear cap face seal; dome flange face seal", "$5", "Amazon / McMaster"),
 ("Hull", "12", "M3 x 16 SHCS", "Rear cap (6) and dome ring (6)", "$4", "Hardware store"),
 ("Hull", "6 + 6", "M3 x 10 SHCS + M3 heat-set inserts", "Radial flange retaining screws (3 per flange)", "(kit)", "-"),
 ("Hull", "8", "M3 heat-set inserts", "Sled holes, 4 per flange", "(kit)", "-"),
 ("Hull", "2 + 2", "Cable gland M16 x 1.5 / M12 x 1.5", "Rear cap: MOTORS + BATTERY (M16), LIGHTS + TETHER (M12)", "$10", "Amazon"),
 ("Hull", "2", "Vent plug M10 (Blue Robotics style)", "Hull rear cap + pod cap; also the vacuum test port", "$15-30", "Blue Robotics"),
 ("Electronics sled", "4 + 16", "M3 threaded rod (cut ~330 mm) + nuts", "Sled rods through both bulkheads into the flange inserts", "$6", "Hardware store"),
 ("Electronics sled", "1", "Raspberry Pi Camera Module 3 + 22-15 pin cable", "Lens at the dome centre", "$30", "Pi reseller"),
 ("Electronics sled", "4 + 4", "M2 x 6 screws + nuts", "Camera to your camera housing", "$2", "Hardware store"),
 ("Battery pod", "1", "3\" Sch40 PVC pipe, 300 mm (11-13/16\")", "Battery pod", "$12 (2 ft)", "Hardware store"),
 ("Battery pod", "1", "3\" Sch40 PVC slip cap", "Pod front, solvent welded", "$5", "Hardware store"),
 ("Battery pod", "2", "O-ring 74 x 2.5 mm, nitrile", "Pod cap plug, 2 radial grooves", "$5", "Amazon"),
 ("Battery pod", "6 + 6", "M5 x 16 SHCS + M5 heat-set inserts", "Pod cap to flange", "$6", "Amazon"),
 ("Battery pod", "1", "Cable gland M16 x 1.5", "Pod cap: battery lead", "(pack)", "-"),
 ("Battery pod", "24", "18650 cells (matched)", "3S8P: 3 groups of 8. On hand from your sled", "on hand", "-"),
 ("Battery pod", "1", "3S BMS, 40 A continuous, balancing", "6 thrusters can pull about 15-18 A", "$12", "Amazon"),
 ("Battery pod", "3 + 12", "M4 threaded rod (~215 mm) + nuts", "Tie the 6 cell plates into one pack", "$4", "Hardware store"),
 ("Battery pod", "1", "Nickel strip 0.15 x 8 mm + spot welder access", "Parallel groups and series links", "$10", "Amazon"),
 ("Battery pod", "1", "Closed-cell foam, ~75 mm disc x 70 mm", "Spacer at the front of the pack", "$3", "Craft store"),
 ("PVC frame", "~1.9 m", "3/4\" Sch40 PVC pipe", "2 upper rails 482 mm, 2 skids 470 mm (one 10 ft stick)", "$6", "Hardware store"),
 ("PVC frame", "6", "3/4\" slip cap", "Skid ends (4), upper rail rear ends (2)", "$4", "Hardware store"),
 ("PVC frame", "1", "PVC primer + cement; marine epoxy", "PVC to PVC: cement. Printed part to PVC (light heads): epoxy", "$20", "Hardware store"),
 ("Lights (x2)", "2", "LED on 20 mm star, 3-5 W (e.g. Cree XP-G3 / XM-L2)", "About 400 lm each, cool or neutral white", "$10", "Amazon / LED supplier"),
 ("Lights (x2)", "2", "Constant-current LED driver, 700-1000 mA, 12 V in, PWM dim", "Inside the hull, one per light", "$10", "Amazon"),
 ("Lights (x2)", "2", "Aluminium disc 42 x 5 mm, 6061", "Slice of 1-3/4\" round bar. 4 mm centre hole, 3x 2.9 mm on a 37 mm circle", "$10", "Online metals"),
 ("Lights (x2)", "2", "Polycarbonate disc 28 x 3 mm", "Window", "$6", "Amazon"),
 ("Lights (x2)", "2 + 2", "O-rings 24 x 1.5 and 31 x 1.5 mm", "Window lip seal; disc face seal", "$5 (kit)", "Amazon"),
 ("Lights (x2)", "6 + 6", "M2.5 x 16 SHCS + M2.5 heat-set inserts", "Front ring + disc into the rear body", "$5", "Amazon"),
 ("Lights (x2)", "1", "Thermal epoxy", "LED star to the disc", "$10", "Amazon"),
 ("Wiring", "~4 m", "2-core 18 AWG marine cable (OD 5-6 mm)", "6 thruster leads + 2 light leads to the junction boxes", "$15", "Amazon"),
 ("Wiring", "0.5 m", "12-core 0.5 mm2 control cable (OD <= 10 mm)", "MOTORS junction to hull (6 pairs)", "$8", "Amazon"),
 ("Wiring", "0.5 m", "3-core 0.5 mm2 cable", "LIGHTS junction to hull (2 channels + common)", "$4", "Amazon"),
 ("Wiring", "0.6 m", "2-core 14 AWG silicone cable (OD <= 10 mm)", "Battery pod to hull", "$6", "Amazon"),
 ("Wiring", "250 ml", "Potting compound (2-part urethane or epoxy)", "Both junction boxes, light cavities", "$15", "Amazon"),
 ("Wiring", "1", "Cat6 tether + strain relief", "Data only (power is on board)", "-", "-"),
 ("Electronics", "3", "Dual-channel brushed DC motor driver, >= 5 A/ch, 3.3 V logic inputs", "6 thrusters. The Pico's GPIO is 3.3 V only: check the driver's logic threshold", "$15-30", "Amazon / Pololu"),
 ("Electronics", "-", "Pi Zero 2W, Pico, buck converter, MOSFET board, main fuse", "Per your control-stack plan (shown as mockups)", "on hand", "-"),
]

# ------------------------------------------------------------------ PVC cut list
CUTS = [("3/4\" upper float rails", 2, 482), ("3/4\" skids", 2, 470), ("4\" hull", 1, 406), ("3\" battery pod", 1, 300)]

# ------------------------------------------------------------------ package folders
def build_package():
    if os.path.exists(PKG): shutil.rmtree(PKG)
    for d in list(SECTION_DIR.values()) + ["Images/Renders", "Images/Assembly_steps", "Images/Parts", "Images/Diagrams", "Source"]:
        os.makedirs(os.path.join(PKG, "STL" if not d.startswith(("Images", "Source")) else "", d), exist_ok=True)
    for sec, stem, src, qty, *_ in PRINTED:
        shutil.copy(os.path.join(src, stem + ".stl"), os.path.join(PKG, "STL", SECTION_DIR[sec], stem + ".stl"))
    for f in os.listdir(CROP):
        if f.startswith("p_"): shutil.copy(os.path.join(CROP, f), os.path.join(PKG, "Images/Parts", f[2:]))
        elif f.startswith(("s0", "t0")): shutil.copy(os.path.join(CROP, f), os.path.join(PKG, "Images/Assembly_steps", f))
    for f in os.listdir(CROP):
        if f.startswith("r_"): shutil.copy(os.path.join(CROP, f), os.path.join(PKG, "Images/Renders", f[2:]))
    for f in ["prop_hex_section.png", "compensator_section.png", "compensator_cutaway.png"]:
        shutil.copy(os.path.join("out", f), os.path.join(PKG, "Images/Diagrams", f))
    shutil.copy(C("s05b_layout.png"), os.path.join(PKG, "Images/Diagrams", "thruster_layout_and_mixing.png"))
    for f in ["thruster.py", "pylon.py", "ring.py", "bracket.py", "rov_parts.py", "frame_clamp.py", "lights.py", "pvc.py",
              "rov_assembly.py", "wiring.py", "balance.py", "export_v4.py", "scenes.py", "scene_v4.py", "build_guide.py",
              "make_3mf.py", "plate_preview.py"]:
        shutil.copy(f, os.path.join(PKG, "Source", f))
    with open(os.path.join(PKG, "BOM_printed_parts.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["Section", "File", "Qty", "Material", "Print notes", "Used for", "Est. filament (g, total)"])
        for sec, stem, src, qty, mat, note, use in PRINTED:
            w.writerow([sec, f"STL/{SECTION_DIR[sec]}/{stem}.stl", qty, mat, note, use, grams(stem, qty)])
    with open(os.path.join(PKG, "BOM_hardware.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["Group", "Qty", "Component", "Description", "Approx. Cost", "Source"])
        for row in HW: w.writerow(row)
    with open(os.path.join(PKG, "PVC_cut_list.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["Piece", "Qty", "Length (mm)", "Length (in)"])
        for n, q, L in CUTS: w.writerow([n, q, L, round(L/25.4, 2)])

# ------------------------------------------------------------------ PDF
INK, MUTED, ACCENT, RULE, SOFT = colors.HexColor("#1d2329"), colors.HexColor("#5b6670"), colors.HexColor("#1f6f9a"), \
    colors.HexColor("#d5dbe0"), colors.HexColor("#eef2f5")
ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=INK, spaceAfter=6)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=INK, spaceBefore=10, spaceAfter=4, keepWithNext=1)
H3 = ParagraphStyle("H3", parent=ss["Heading3"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=ACCENT, spaceBefore=6, spaceAfter=2, keepWithNext=1)
BODY = ParagraphStyle("B", parent=ss["BodyText"], fontName="Helvetica", fontSize=9.5, leading=13.2, textColor=INK, spaceAfter=4)
SMALL = ParagraphStyle("S", parent=BODY, fontSize=8, leading=10.5, textColor=MUTED)
CAP = ParagraphStyle("C", parent=SMALL, alignment=TA_CENTER, spaceBefore=2, spaceAfter=8)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=7.8, leading=9.6, spaceAfter=0)
CELLB = ParagraphStyle("cellb", parent=CELL, fontName="Helvetica-Bold")
NOTE = ParagraphStyle("N", parent=BODY, backColor=SOFT, borderPadding=(5, 6, 5, 6), leftIndent=6, rightIndent=6, spaceBefore=6, spaceAfter=8)
STEPN = ParagraphStyle("SN", parent=BODY, fontName="Helvetica-Bold", textColor=colors.white, alignment=TA_CENTER, fontSize=9)

W_TXT = letter[0] - 1.5*inch

def img(path, width=W_TXT, max_h=4.3*inch):
    w, h = PILImage.open(path).size
    s = min(width / w, max_h / h)
    return Image(path, width=w*s, height=h*s)

def fig(path, caption, width=W_TXT, max_h=4.3*inch):
    return KeepTogether([img(path, width, max_h), Paragraph(caption, CAP)])

def steps(items, start=1):
    """numbered sub-steps as a two-column table with round-ish number badges"""
    rows = []
    for i, t in enumerate(items, start):
        rows.append([Paragraph(str(i), STEPN), Paragraph(t, BODY)])
    tb = Table(rows, colWidths=[0.28*inch, W_TXT - 0.36*inch])
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
          ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    for r in range(len(rows)):
        st.append(("BACKGROUND", (0, r), (0, r), ACCENT))
    tb.setStyle(TableStyle(st))
    return tb

def table(header, rows, widths, zebra=True, font=CELL):
    data = [[Paragraph(h, CELLB) for h in header]] + [[Paragraph(str(c), font) for c in r] for r in rows]
    t = Table(data, colWidths=widths, repeatRows=1)
    st = [("LINEBELOW", (0, 0), (-1, 0), 0.8, INK), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
          ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
    if zebra:
        for i in range(1, len(data)):
            if i % 2 == 0: st.append(("BACKGROUND", (0, i), (-1, i), SOFT))
    t.setStyle(TableStyle(st))
    return t

def on_page(c, doc):
    c.saveState()
    c.setStrokeColor(RULE); c.setLineWidth(0.6)
    c.line(0.75*inch, 0.6*inch, letter[0] - 0.75*inch, 0.6*inch)
    c.setFont("Helvetica", 7.5); c.setFillColor(MUTED)
    c.drawString(0.75*inch, 0.42*inch, "ROV Build Guide v4  |  4\" hull, 3\" battery pod, 6x 1200 GPH vectored thrusters")
    c.drawRightString(letter[0] - 0.75*inch, 0.42*inch, f"Page {doc.page}")
    c.restoreState()

def on_cover(c, doc):
    c.saveState()
    c.setFillColor(INK); c.rect(0, letter[1] - 0.35*inch, letter[0], 0.35*inch, stroke=0, fill=1)
    c.restoreState()

def C(f): return os.path.join(CROP, f)
def R(f): return os.path.join(RD, f)

def build_pdf(path):
    doc = BaseDocTemplate(path, pagesize=letter, leftMargin=0.75*inch, rightMargin=0.75*inch, topMargin=0.7*inch,
                          bottomMargin=0.8*inch, title="ROV Build Guide", author="Brian")
    fr = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
    doc.addPageTemplates([PageTemplate("cover", [fr], onPage=on_cover), PageTemplate("body", [fr], onPage=on_page)])
    S = []

    MIX = json.load(open(os.path.join(RD, "mix.json")))
    # ---------------- cover
    S += [Spacer(1, 0.3*inch), Paragraph("ROV Build Guide", ParagraphStyle("T", parent=H1, fontSize=30, leading=34)),
          Paragraph("4\" PVC electronics hull, 3\" battery pod underneath, six 1200 GPH oil-filled thrusters in a vectored layout, "
                    "printed frame clamps and compact rail-end lights",
                    ParagraphStyle("st", parent=BODY, fontSize=12, leading=16, textColor=MUTED)),
          Spacer(1, 0.15*inch), img(C("s09_front.png"), W_TXT, 3.7*inch), Spacer(1, 0.1*inch),
          Paragraph(f"Version 4  |  {TODAY}", SMALL), Spacer(1, 0.15*inch)]
    toc = [("1", "What's in the package"), ("2", "Before you start: tools, materials, print settings"),
           ("3", "Printed parts list"), ("4", "Hardware list (purchased)"), ("5", "Build the thrusters (x6)"),
           ("6", "Build the electronics sled"), ("7", "Close up the hull"), ("8", "Build the battery pod"),
           ("9", "Frame clamps: join hull and pod"), ("10", "Mount the thrusters"),
           ("11", "Float rails, skids and lead trays"), ("12", "Lights"), ("13", "Junction boxes and wiring"),
           ("14", "Leak test, trim and first dive"), ("15", "Reference views and layout")]
    S += [table(["#", "Section"], toc, [0.4*inch, W_TXT - 0.4*inch], zebra=False), NextPageTemplate("body"), PageBreak()]

    # ---------------- 1 package
    S += [Paragraph("1  What's in the package", H1),
          Paragraph("Everything is in one folder. Parts are in print orientation, in millimetres.", BODY),
          table(["Folder / file", "Contents"], [
              ["ROV_Assembly_Guide.pdf", "This guide."],
              ["ROV_printed_parts.3mf", "Bambu Studio project: every printed part laid out on plates for the A1, settings applied."],
              ["BOM_printed_parts.csv", "Every part to print: file, quantity, material, orientation, rough filament weight."],
              ["BOM_hardware.csv", "Everything to buy: Qty, Component, Description, Approx. Cost, Source."],
              ["PVC_cut_list.csv", "Pipe lengths: hull, pod, upper rails, skids."],
              ["STL/1_Thrusters", "Housing, tail cone, RH and LH prop hubs, nose cone, pylon clamp, coupler gauge."],
              ["STL/2_Frame_clamps_and_junctions", "Top cap, corner body, mid body, pod cap, lead tray, junction bridge, 6-lead and 2-lead junction boxes."],
              ["STL/3_Hull_and_sled", "Your BR-style flanges, dome ring and ETRAY4 tray, the 4-gland rear cap, the rear bulkhead, your front bulkhead and camera mount (m03r7-001..005)."],
              ["STL/4_Battery_pod", "3\" pod flange, 3\" pod cap, 8-cell holder plate."],
              ["STL/5_Lights", "Light rear body, front ring, window spacer."],
              ["Images/", "Assembly step images, part thumbnails, renders, diagrams (prop drive, compensator, thruster layout)."],
              ["Source/", "The Python generators. Change a dimension at the top of a script and re-run it."]],
              [2.1*inch, W_TXT - 2.1*inch]),
          Spacer(1, 6),
          Paragraph("Not included: anything electronic. Cables and electronics in the pictures are mockups to show routing only.", NOTE),
          Paragraph("Key numbers", H2),
          table(["Item", "Value"], [
              ["Overall size", "about 351 W x 335 H x 521 L mm (13.8 x 13.2 x 20.5 in) including the lights, without the tether"],
              ["Hull", "4\" Sch40 PVC, 16\" (406 mm), electronics only. BR-style flange both ends, 100 mm acrylic dome at the front"],
              ["Battery pod", "3\" Sch40 PVC, 300 mm, axis 116 mm below the hull. 24 x 18650 as 3S8P (3 groups of 8)"],
              ["Thrusters", "6x 1200 GPH, oil filled. 4 horizontal at the corners turned 45 deg (surge, sway, yaw), 2 vertical at the centre of gravity"],
              ["Frame", "3 clamp stations (z -95, -8, +95 mm), 2 sealed upper float rails, 2 flooded skids"],
              ["Weight / trim (est.)", "about 10.5 kg dry before lead, +1.65 kg buoyant in fresh water. About 1.4 kg of lead gives +0.4 kg and 29 mm between the centres of buoyancy and gravity"],
              ["Depth", "Target 60 ft. Printed end caps carry 100-150 kg at that depth: consider aluminium caps before going deep. Test in stages."],
              ["Lights", "2x 3-5 W LED heads on the front of the upper rails"]],
              [1.4*inch, W_TXT - 1.4*inch]),
          PageBreak()]

    # ---------------- 2 before you start
    S += [Paragraph("2  Before you start", H1), Paragraph("Tools", H2),
          table(["Tool", "Used for"], [
              ["3D printer (Bambu A1, 256 mm bed)", "Everything fits the A1 bed. The pod cap (206 mm) is the widest part."],
              ["Soldering iron with heat-set insert tip", "M2.5, M3, M4 and M5 brass inserts"],
              ["Taps: M16 x 1.5, M12 x 1.5, M3 x 0.5, M4 x 0.7", "Cable glands, skid grub screws, oil ports"],
              ["Drill + 1/8\" (3.17 mm) bit or reamer", "Open the brass coupler's 3 mm end for the motor shaft"],
              ["Lathe or drill press + files", "Aluminium light discs (or have them cut)"],
              ["PVC cutter or fine saw, deburring tool", "3/4\", 3\" and 4\" pipe"],
              ["Hex keys 2-4 mm, 7 / 8 mm nut drivers", "General assembly. The 8 mm driver fits inside the hub spigot."],
              ["Syringe (60 ml) with a short tube", "Oil fill"],
              ["Hand vacuum pump + gauge", "Hull and pod vacuum test through the vent plugs"],
              ["Spot welder (or a shop that has one)", "Nickel strip on the 18650 pack. Don't solder directly to cells."],
              ["Multimeter", "Wiring and pack checks"]],
              [2.4*inch, W_TXT - 2.4*inch]),
          Paragraph("Print settings", H2),
          table(["Setting", "Value"], [
              ["Material", "PETG for everything that goes in the water. ASA is a good choice for the light heads."],
              ["Walls / infill", "4-5 walls, 25 % gyroid (already set per part in the 3MF)."],
              ["Layer height", "0.2 mm. Use 0.12 mm for the housing thread and the prop hubs if you want smoother surfaces."],
              ["Supports", "None, except tree supports under the prop blades."],
              ["After printing", "Seal the housing, tail cone and light heads: a thin coat of epoxy on the outside closes any layer gaps."]],
              [1.4*inch, W_TXT - 1.4*inch]),
          Paragraph("Ground rules", H2),
          steps(["Measure your motor shaft before printing props: the design assumes 3.17 mm.",
                 "PVC cement only bonds PVC to PVC. Where a printed part meets PVC (light heads), use marine epoxy. The clamps are bolted, never glued.",
                 "The two upper rails are sealed air tubes (floats). Never drill or pin through them; the junction bridge clamps them with a pinch screw. "
                 "The skids flood: drill two 4 mm holes in each.",
                 "Grease every O-ring lightly with silicone grease. Never use petroleum grease on nitrile.",
                 "Keep the 12 V power path and the 3.3 V / 5 V logic apart. The Pico's GPIO is 3.3 V only and will not tolerate 12 V."]),
          PageBreak()]

    # ---------------- 3 printed parts
    rows, tot = [], 0
    for sec, stem, src, qty, mat, note, use in PRINTED:
        g = grams(stem, qty); tot += g
        rows.append([sec, f"{stem}.stl", qty, mat, note, use, g])
    S += [Paragraph("3  Printed parts list", H1),
          Paragraph(f"{sum(r[2] for r in rows)} printed parts in {len(rows)} files. Filament estimates assume PETG with 4 walls and 25 % infill; "
                    f"thin plates are counted as nearly solid. Total is roughly {round(tot/1000, 1)} kg. "
                    "Parts marked \"yours\" are your ROV Project files, unchanged.", BODY),
          table(["Section", "File", "Qty", "Material", "Print notes", "Used for", "g"], rows,
                [0.8*inch, 1.55*inch, 0.3*inch, 0.55*inch, 1.95*inch, 1.4*inch, 0.35*inch]),
          CondPageBreak(3.5*inch), Paragraph("Printed parts at a glance", H2)]
    cells, row = [], []
    for sec, stem, src, qty, *_ in PRINTED:
        row.append([img(C(f"p_{stem}.png"), 1.6*inch, 1.15*inch),
                    Paragraph(f"<b>{stem}</b>  x{qty}", ParagraphStyle("g", parent=CELL, alignment=TA_CENTER))])
        if len(row) == 4: cells.append(row); row = []
    if row: cells.append(row + [""] * (4 - len(row)))
    g = Table(cells, colWidths=[W_TXT/4]*4)
    g.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    S += [g, PageBreak()]

    # ---------------- 4 hardware
    S += [Paragraph("4  Hardware list (purchased)", H1),
          Paragraph("Costs are rough US prices for budgeting; check current prices before ordering. \"on hand\" items are already in your parts bin.", BODY),
          table(["Group", "Qty", "Component", "Description", "Approx. Cost", "Source"], HW,
                [0.95*inch, 0.5*inch, 1.75*inch, 2.1*inch, 0.75*inch, 0.95*inch]),
          PageBreak()]

    # ---------------- 5 thrusters
    S += [Paragraph("5  Build the thrusters (x6)", H1),
          Paragraph("Each thruster is a printed housing with the Kort duct built in, an oil-filled motor bay, a threaded tail cone with a "
                    "built-in compensator, and a two-piece prop driven by a brass coupler. Build all six the same way; "
                    "only the prop hand changes (3 RH, 3 LH: one of each per pair).", BODY),
          fig(C("t01_thr_ex.png"), "Exploded thruster, rear to front: motor lead gland, tail cone with its spigot O-ring, motor, housing "
              "(pylon clamp above), brass coupler, M5 stud with jam nut, prop hub, M5 nyloc, nose cone.", max_h=2.0*inch),
          Paragraph("5.1  Prepare the parts", H3),
          steps(["Tap the tail cone tip M12 x 1.5 and the two side ports M4. Thread the M12 gland in with a drop of sealant.",
                 "Ream the coupler's 3 mm end to 1/8\" (3.17 mm) so it slides onto the motor shaft with a light push fit.",
                 "Thread the M5 x 20 set screw halfway into the coupler's 5 mm end and lock it with its own grub screw. "
                 "Spin the M5 jam nut down onto it, flat side toward the coupler.",
                 "Press the M4 and M3 heat-set inserts into the pylon clamp."]),
          Paragraph("5.2  Motor, coupler and prop", H3),
          steps(["Lightly grease the motor's nose O-ring. Feed the motor lead out through the rear of the housing and push the motor in from "
                 "the back until the nose seats in the front bore.",
                 "Slide the coupler onto the shaft. Stand the coupler gauge over it, push the coupler up to the gauge's ceiling and tighten "
                 "its set screws through the gauge windows. The coupler now sits 1 mm below the housing face, so it can never rub.",
                 "Tighten the jam nut down against the coupler.",
                 "Drop the prop hub over the stud so the jam nut sits in the hub's hex pocket. Spin on the M5 nyloc with the 8 mm nut "
                 "driver through the hub spigot until it just seats; the hub should turn freely with no rub on the duct.",
                 "Slide the nose cone over the spigot and fit the 3 M3 x 6 button screws."], start=5),
          fig(os.path.join("out", "prop_hex_section.png"), "Section through the prop drive.", max_h=2.3*inch),
          Paragraph("5.3  Tail cone, oil fill and compensator", H3),
          steps(["Stretch a nitrile finger cot over the nipple inside the tail cone and tie it on. It is the compensator bladder: "
                 "water enters it through the 2 mm vent, oil stays outside it.",
                 "Pass the motor lead through the tail cone gland, grease the 32 x 2 O-ring on the spigot and thread the tail cone on hand tight.",
                 "Stand the thruster nose down. Fill through one M4 port with a syringe of mineral oil while air leaves the other; "
                 "rock it and spin the prop by hand to free bubbles. Top off, then seal both ports with M4 set screws and sealant.",
                 "Tighten the gland on the lead. Wait an hour and check for weeping at the thread and ports."], start=10),
          fig(os.path.join("out", "compensator_section.png"), "Oil fill and compensator, section through the axis.", max_h=2.3*inch),
          Paragraph("5.4  Pylon clamp", H3),
          steps(["Slide the pylon clamp over the housing body and close it with the 2 M4 x 30 pinch bolts. Leave it loose; "
                 "you set its position when it goes on the ROV."], start=14),
          fig(C("t02_thr_as.png"), "Finished thruster with pylon clamp.", max_h=1.9*inch),
          Paragraph("Label each thruster T1-T6 now (section 10) and note its prop hand: T1/T2 one RH + one LH, T3/T4 one RH + one LH, "
                    "T5/T6 one RH + one LH. Reverse the motor direction in software for the LH units so both of a pair push the same way.", NOTE),
          PageBreak()]

    # ---------------- 6 sled
    S += [Paragraph("6  Build the electronics sled", H1),
          Paragraph("The sled is two bulkheads 234 mm apart on four M3 rods with the ETRAY4 tray between them. The rods sit on the same "
                    "94 mm circle as the flange sled inserts, so they run straight through both bulkheads into the flanges. "
                    "With the battery in its own pod, the hull holds only the sled.", BODY),
          fig(C("s01_sled.png"), "Electronics sled: bulkheads, rods, tray and electronics (mockup). Shown with a simple camera stalk; build yours from m03r7-002 to -005.", max_h=2.5*inch),
          steps(["Cut four M3 rods to about 330 mm. Put a nut on each rod, slide on the rear bulkhead (boss toward the tray) and a second nut. "
                 "Drop the tray's rear prongs into the rear bulkhead's pockets, then fit the front bulkhead over the front prongs. "
                 "Set the bulkhead inner faces 234 mm apart and nip the nuts so the tray is clamped between them.",
                 "Front bulkhead and camera: use your front bulkhead (m03r7-001) and assemble your camera mount (m03r7-002 to -005) on its "
                 "outer face with M2 screws. Fit the Pi Camera Module 3 and route the ribbon back to the Pi Zero. The lens should end up at "
                 "the centre of the dome. Check your front bulkhead's rod holes line up with the flange inserts (see the note below).",
                 "Lay out the boards: Pi Zero 2W and Pico at the front, the three motor drivers and power at the rear near the glands, "
                 "fuse block on the underside. Keep the 12 V path and the 3.3 V / 5 V logic apart.",
                 "Press M3 heat-set inserts into the sled holes inside both hull flanges (4 per flange, 94 mm circle)."]),
          Paragraph("Open item: your front bulkhead (m03r7-001) has its rod holes on the prong-slot axis, while the flange inserts sit at 45 deg. "
                    "Either rotate the bulkhead 45 deg on the rods (if the camera allows) or drill two extra 3.1 mm holes at 45 deg.", NOTE),
          fig(C("s01c_bulkhead.png"), "Rear bulkhead: the tray's end prongs drop into the boss pockets.", max_h=2.0*inch),
          fig(C("s01b_camera.png"), "Camera position: the lens sits at the centre of the dome.", max_h=2.2*inch),
          PageBreak()]

    # ---------------- 7 hull
    S += [Paragraph("7  Close up the hull", H1),
          fig(C("s02_hull.png"), "Hull, exploded: dome and retaining ring, front flange, hull pipe (shown see-through), sled, rear flange and the 4-gland end cap.", max_h=2.4*inch),
          steps(["Cut the 4\" pipe square at 16\" (406 mm) and deburr inside and out. Chamfer the inside edge lightly so the O-rings don't nick.",
                 "Grease two AS568-240 O-rings into each flange's radial grooves. Press M3 inserts into each flange's 3 radial retaining holes.",
                 "Front: press the dome flange into the pipe. Seat the AS568-242 face O-ring, the dome, and the retaining ring; tighten its "
                 "6 M3 x 16 evenly in a star pattern. Fit the 3 radial M3 x 10 screws through the pipe wall.",
                 "Tap the rear end cap: M16 x 1.5 for MOTORS and BATTERY, M12 x 1.5 for LIGHTS and TETHER, and the centre vent hole M10. "
                 "Fit the glands and the vent plug.",
                 "Bolt the sled rods to the rear flange's sled inserts. Slide the sled and rear flange into the pipe from the rear until the "
                 "camera sits in the dome; fit the rear flange's 3 radial screws.",
                 "Pass the cables through the glands (section 13), seat the AS568-239 face O-ring and bolt the cap on with 6 M3 x 16."]),
          Paragraph("Rear end cap holes", H3),
          table(["Hole", "Thread", "Position", "Use"], [["MOTORS", "M16 x 1.5", "upper port", "12-core from the 6-lead junction box"],
                                           ["LIGHTS", "M12 x 1.5", "upper starboard", "3-core from the 2-lead junction box"],
                                           ["BATTERY", "M16 x 1.5", "lower starboard", "14 AWG lead from the battery pod"],
                                           ["TETHER", "M12 x 1.5", "lower port", "Cat6 tether"],
                                           ["VENT", "M10", "centre", "Vent plug / vacuum test port"]],
                [1.0*inch, 0.9*inch, 1.2*inch, W_TXT - 3.1*inch]),
          Paragraph("Was 14 holes in the earlier cap. Fewer penetrations, fewer leak paths: the motor and light leads now join in potted "
                    "junction boxes on the frame (section 13).", NOTE),
          PageBreak()]

    # ---------------- 8 pod
    S += [Paragraph("8  Build the battery pod", H1),
          Paragraph("The battery lives in its own 3\" tube under the hull, low and close to the middle, which is what keeps the ROV level "
                    "and stable. The 24 cells are repacked as 3S8P: three groups of 8 cells in parallel, the groups in series.", BODY),
          fig(C("s03_pod.png"), "Battery pod, exploded: 3\" PVC slip cap (front), pod pipe, 3\" flange (glued), 2-hole rear cap.", max_h=2.3*inch),
          fig(C("s03b_pack.png"), "3S8P pack: six holder plates, two per group, tied with three M4 rods.", max_h=2.0*inch),
          steps(["Cut the 3\" pipe to 300 mm (11-13/16\"). Deburr and chamfer the inside of the rear end.",
                 "Prime and solvent-weld the 3\" slip cap on the front end. Epoxy the printed flange on the rear end, pushed onto the pipe "
                 "until the pipe hits the flange's stop ledge. Let both cure fully.",
                 "Press 6 M5 heat-set inserts into the flange face.",
                 "Pack: in each group, sit 8 cells (all the same way round) between two holder plates. Spot-weld nickel strip across each "
                 "group's ends through the plate windows (parallel), then link the groups in series, alternating polarity. Add the 3S BMS "
                 "balance leads at each junction. Tie the six plates with three M4 rods (about 215 mm) and nuts. The pack is about 213 mm long.",
                 "Mount the BMS on the rear plate, solder the 14 AWG battery lead to the BMS output, and pass it through the M16 gland in the "
                 "rear cap. Fit the vent plug in the cap.",
                 "Put the foam spacer in the front of the pod, slide the pack in from the rear, grease the two 74 x 2.5 O-rings on the cap plug, "
                 "and bolt the cap to the flange with 6 M5 x 16."]),
          Paragraph("Charging: open the pod cap, or fit an inline waterproof connector on the battery lead and charge through it. "
                    "Always charge with the BMS in circuit, and never charge a wet pack.", NOTE),
          PageBreak()]

    # ---------------- 9 frame clamps
    S += [Paragraph("9  Frame clamps: join hull and pod", H1),
          Paragraph("Three clamp stations hold the hull and pod together and carry the thrusters, upper rails and skids. Each station is three "
                    "printed parts: a top cap (upper rail bosses), a body (hull bottom half + pod top half + two thruster pads), and a pod cap "
                    "(pod bottom half + skid legs). The front and rear stations use the corner body with 45 deg pads; the rear one is the same "
                    "part turned end for end. Positions are measured from the hull centre (0), front positive.", BODY),
          fig(C("s04b_clamp.png"), "One corner station, exploded: top cap, corner body with its 45 deg thruster pads, pod cap with skid legs.", max_h=3.0*inch),
          table(["Station", "Centre (z)", "Parts", "Thruster pads"], [
              ["Front", "+95 mm", "top cap + corner body + pod cap", "45 deg, T1 / T2"],
              ["Mid", "-8 mm", "top cap + mid body + pod cap", "square, T5 / T6 (vertical)"],
              ["Rear", "-95 mm", "top cap + corner body (turned 180 deg) + pod cap", "45 deg, T3 / T4"]],
              [0.8*inch, 0.9*inch, 2.9*inch, W_TXT - 4.6*inch]),
          steps(["Press 4 M3 heat-set inserts into each thruster pad (8 per body). Push M4 nuts into the hex pockets under the body's hull "
                 "ears and under the pod cap's ears. Tap the pod cap's skid grub screw holes M3.",
                 "Mark the three stations on the hull and pod with tape. Lay the hull upside down on a towel and sit the three bodies on it, "
                 "then lay the pod in the bodies' lower cradles with its flange toward the rear. The flange should sit just behind the rear clamp.",
                 "Fit the three top caps over the hull and the three pod caps under the pod. Bolt each joint with M4 x 20 (8 per station). "
                 "Snug them evenly so the hull and pod stay parallel, but don't torque them yet: you may slide stations a few mm when trimming."]),
          fig(C("s04_frame.png"), "All three stations on the hull and pod (top caps and pod caps lifted to show the bodies).", max_h=3.0*inch),
          PageBreak()]

    # ---------------- 10 thrusters on
    mixrows = [[m["name"], f'{m["x"]}, {m["z"]}', f'{m["surge"]:+.2f}', f'{m["sway"]:+.2f}', f'{m["heave"]:+.2f}', f'{m["yaw"]:+.2f}'] for m in MIX]
    S += [Paragraph("10  Mount the thrusters", H1),
          Paragraph("Four horizontal thrusters sit at the corners turned 45 deg in a diamond, the BlueROV-style vectored layout: together they "
                    "drive forward/back, strafe sideways and turn on the spot. The two verticals sit on the mid station, on the estimated "
                    "centre of gravity, so going up or down doesn't pitch the nose.", BODY),
          fig(C("s05_thrusters.png"), "All six thrusters on the clamp stations.", max_h=2.9*inch),
          steps(["Corner thrusters: bolt each pylon to a 45 deg pad with 4 M3 x 16, prop end facing outboard and the tail cone pointing in "
                 "toward the hull. Front pair = T1 (port) and T2 (starboard), rear pair = T3 and T4.",
                 "Vertical thrusters: bolt T5 (port) and T6 (starboard) to the mid body's square pads, axis vertical, prop up.",
                 "Slide each housing in its pylon until the duct clears everything, then tighten the pinch bolts.",
                 "Spin every prop by hand: nothing should touch the duct, the hull or a clamp."]),
          CondPageBreak(4.5*inch),
          Paragraph("Mixing (for the topside software)", H3),
          Paragraph("Coefficients for a + command (thrust toward the nose cone). Surge + = forward, sway + = to starboard, heave + = up, "
                    "yaw + = nose to port, normalised. Per thruster: command = surge*Fx + sway*Fy + yaw*Mz (+ heave for T5/T6), "
                    "then scale so no output exceeds 1. Flip the sign for any motor wired or propped the other way.", BODY),
          table(["Thruster", "x, z (mm)", "Surge", "Sway", "Heave", "Yaw"], mixrows,
                [1.6*inch, 1.0*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch]),
          Spacer(1, 6),
          fig(C("s05b_layout.png"), "Thruster layout, top view.", max_h=4.2*inch),
          PageBreak()]

    # ---------------- 11 rails, skids, trays
    cuts = [[n, q, L, f"{L/25.4:.2f}"] for n, q, L in CUTS]
    S += [Paragraph("11  Float rails, skids and lead trays", H1),
          fig(C("s06_rails.png"), "Upper float rails through the top cap bosses, skids through the pod cap bosses.", max_h=3.0*inch),
          Paragraph("Pipe cut list", H3),
          table(["Piece", "Qty", "mm", "in"], cuts, [3.4*inch, 0.6*inch, 0.8*inch, 0.8*inch]),
          steps(["Upper rails (2 x 482 mm): slide each through the three top cap bosses so it runs from z -250 to +232 (the rear end sits "
                 "about 27 mm behind the hull's rear cap). Slide the junction bridge's two rings on from the rear before capping. "
                 "Cement a 3/4\" slip cap on the rear end. The front end gets a light head (section 12), which closes the float.",
                 "Skids (2 x 470 mm): drill two 4 mm flood holes in each, slide through the pod cap bosses (z -235 to +235), cap both "
                 "ends, and lock with the M3 grub screws.",
                 "Lead trays: hook one tray over the skids each side of the mid station (centres about z +44 and -52), "
                 "fill with lead shot in bags, and zip-tie through the slots. Start with about 0.7 kg each and trim in the water."]),
          PageBreak()]

    # ---------------- 12 lights
    S += [Paragraph("12  Lights", H1),
          Paragraph("Each light is a 42 mm bullet head that glues onto the front end of an upper rail like a slip cap. A 3-5 W LED on a "
                    "20 mm star is bonded to an aluminium disc; the disc's rim is in the water and carries the heat. The cable leaves the "
                    "side of the head and is potted in place.", BODY),
          fig(C("s07b_light_ex.png"), "Light head, exploded along the beam: rail, rear body, aluminium disc, LED, spacer, window, front ring.", max_h=2.0*inch),
          fig(C("s07_lights.png"), "Assembled head on the rail end.", max_h=2.2*inch),
          steps(["Aluminium disc (42 x 5 mm): drill a 4 mm centre hole and 3 x 2.9 mm holes on a 37 mm circle. Deburr.",
                 "Press 3 M2.5 heat-set inserts into the rear body's front face.",
                 "Solder 2-core cable to the LED star, pass the wires back through the disc's centre hole, and bond the star to the disc's "
                 "front face with thermal epoxy. Test briefly at low current only: it needs water (or a heat sink) to stay cool.",
                 "Feed the cable out through the rear body's side hole, sit the disc on the rear body and fill the cavity behind it with "
                 "potting compound through the side hole until it seals the cable and the wires.",
                 "Seat the 31 x 1.5 O-ring in the front ring's back-face groove and the 24 x 1.5 O-ring under its lip. Drop in the window, "
                 "then the spacer, and screw the ring and disc to the rear body with 3 M2.5 x 16.",
                 "Epoxy the head onto the front end of each upper rail, with the cable exit turned up and outboard. This seals the float."]),
          Paragraph("Each LED needs a constant-current driver (700-1000 mA) inside the hull; PWM its dim input from the MOSFET board or Pico "
                    "(3.3 V logic).", NOTE),
          PageBreak()]

    # ---------------- 13 junctions + wiring
    S += [Paragraph("13  Junction boxes and wiring", H1),
          Paragraph("The thruster and light leads join in two potted junction boxes on the frame, so only one cable per group enters the "
                    "hull. The boxes screw to a bridge that clamps across the two upper rails just behind the rear clamp.", BODY),
          fig(C("s08b_junction.png"), "Junction bridge on the upper rails, with the 6-lead (motors) and 2-lead (lights) boxes lifted off.", max_h=2.6*inch),
          steps(["Bridge: press 4 M3 heat-set inserts into the plate. Its rings go onto the upper rails before the rear caps (section 11). "
                 "Set it at z -200 to -130 and tighten the two M3 pinch screws. No hole goes into the rails.",
                 "Screw each box to the bridge with 2 M3 x 10 through its floor, entries facing forward. The potting will cover the heads.",
                 "Thruster leads: run each from its tail gland up the hull side and along the top to the MOTORS box. Zip-tie to the clamps; "
                 "leave a drip loop at each thruster. Strip, solder each lead to its pair in the 12-core, sleeve every joint, and label T1-T6.",
                 "Light leads: run each back along the inboard side of its rail to the LIGHTS box and join them to the 3-core (two channels + common).",
                 "Fill both boxes with potting compound, a little at a time, tapping out bubbles. Let it cure fully.",
                 "Multicores: from each box's rear exit down to the MOTORS (M16) and LIGHTS (M12) glands on the hull cap.",
                 "Battery: from the pod cap's M16 gland straight up to the hull cap's BATTERY gland. Put the main fuse inside the hull, at the gland.",
                 "Tether: through the TETHER gland, with a strain relief tied to the frame so the gland never takes the pull. "
                 "Tighten every gland nut last, after the cables are dressed."]),
          fig(C("s08_wiring.png"), "Complete with cables and electronics (mockup), hull shown see-through.", max_h=3.0*inch),
          Paragraph("Keep the 12 V motor and light wiring physically separate from the 3.3 V / 5 V logic, fuse the battery lead before "
                    "anything else, and make sure the motor drivers accept 3.3 V logic from the Pico.", NOTE),
          PageBreak()]

    # ---------------- 14 testing
    S += [Paragraph("14  Leak test, trim and first dive", H1),
          steps(["Vacuum test the hull and the pod through their vent plugs: pull to about -10 inHg and watch the gauge for 15 minutes. "
                 "Any drop means a leak; re-grease and re-seat O-rings, check glands, and repeat until it holds.",
                 "Dunk test with the electronics removed (or a paper towel inside), 10 minutes, then open and check for moisture.",
                 "Thrusters: run each one in a bucket for 5 minutes at low power. Check for oil weeping and the direction of thrust "
                 "against the mixing table.",
                 "Trim in a pool: start with about 0.7 kg of lead in each tray. Add or remove lead until it just floats (about 0.2-0.4 kg "
                 "positive), then move lead between the front and rear trays until it sits level. Fine-tune by sliding the stations a few mm.",
                 "First dives: 10 ft, then 30 ft, then 60 ft. Check the hull, pod, lights and thrusters for water after each step."]),
          Paragraph("Estimated balance with about 1.4 kg of lead (from the 3D model): centre of gravity 67 mm below the hull axis, centre of "
                    "buoyancy 38 mm below it (29 mm above the centre of gravity, so it rights itself). Centre of buoyancy 7 mm ahead of "
                    "the centre of gravity, so nearly level fore-aft.", NOTE),
          Paragraph("Depth note: the thrusters' oil fill and compensator let them work below their 30 ft design depth. The printed hull "
                    "and pod caps take the full pressure load (100-150 kg at 60 ft), so step down gradually, or machine those caps from aluminium.", NOTE),
          PageBreak()]

    # ---------------- 15 reference
    S += [Paragraph("15  Reference views and layout", H1),
          fig(C("s09_side.png"), "Side view.", max_h=3.0*inch), fig(C("s09_top.png"), "Top view.", max_h=3.6*inch), PageBreak(),
          Paragraph("Layout along the hull", H2),
          Paragraph("z = 0 is the hull centre; + is toward the dome. x + is port, y + is up.", BODY),
          table(["Item", "z position (mm)", "Notes"], [
              ["Upper rails", "-250 to +232", "Sealed floats at x +/-75, y +112. Light heads to +262"],
              ["Hull rear end cap", "-223 to -213", "4 glands + vent face aft"],
              ["Junction bridge", "-200 to -130", "On the upper rails; boxes on top"],
              ["Battery pod", "-160 to +176", "Pipe -138 to +162; axis 116 mm below the hull"],
              ["Rear clamp station", "-112 to -78", "Corner body turned 180 deg; T3 / T4"],
              ["Lead tray (rear)", "-77 to -27", "Hooks over the skids"],
              ["Mid clamp station", "-25 to +9", "T5 / T6 vertical"],
              ["Lead tray (front)", "+19 to +69", ""],
              ["Front clamp station", "+78 to +112", "T1 / T2"],
              ["Hull pipe", "-203 to +203", "16\""],
              ["Dome", "+215 to +265", "Camera lens at the dome centre"],
              ["Skids", "-235 to +235", "x +/-85, y -182, flooded"]],
              [1.8*inch, 1.4*inch, W_TXT - 3.2*inch]),
          Spacer(1, 8),
          fig(C("r_front_end.png"), "Front view, to scale: 351 mm wide.", max_h=3.0*inch)]

    doc.build(S)

if __name__ == "__main__":
    build_package()
    build_pdf(os.path.join(PKG, "ROV_Assembly_Guide.pdf"))
    print("done", PKG)
