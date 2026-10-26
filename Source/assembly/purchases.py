"""
Everything to buy for one TinkerSub KB-1: one line per item with its total quantity and exact size, for the guide's
"Everything to buy" page and Parts_to_buy.csv.

Screws, nuts, washers and heat-set inserts are not typed in here: they are counted from assembly/fasteners.py (the
table the fastener check proves against the model), and the insert totals are checked against the insert chart
(guide/insert_map.py EXPECT x printed quantities) when the guide builds. Everything else is listed in ITEMS below.

O-ring sizes were measured from the grooves in the parts (2026-10-25): hull radial AS568-238, rear cap face -237,
dome face -240, pod caps 72 x 2.5, tail cone spigot 32 x 2, compensator 5 x 1.5, light ring face 30 x 1.5, light window 24 x 1.5.
"""
from collections import Counter, OrderedDict
import fasteners as FT

HEAD = {"SHCS": "socket head cap screw", "button": "button head screw", "csk": "countersunk screw"}
NUT = {"M3": "M3 nyloc nut", "M4": "M4 hex nut"}             # every nut joint: M3 ones are nyloc, the M4 station joints plain
WASHERS = {"Vertical pylon through the plate": ("M3 washer, 1 mm thick (shim)", 1)}   # per joint
EXTRA_INSERTS = Counter()   # inserts the model has but no joint uses (none since the 2026-10-26 deck screws to both stations)

def fastener_lines():
    """[(qty, description, used for)] counted from the fastener table"""
    screws, uses = Counter(), OrderedDict()
    nuts, washers, inserts = Counter(), Counter(), Counter()
    for j in FT.JOINTS:
        k = (j["size"], j["length"], j["head"]); screws[k] += j["n"]
        uses.setdefault(k, []).append(j["name"].lower())
        if j["thread"] == "nut": nuts[NUT[j["size"]]] += j["n"]
        if j["thread"] == "insert": inserts[j["size"]] += j["n"]
        if j["name"] in WASHERS: w, per = WASHERS[j["name"]]; washers[w] += per * j["n"]
    inserts += EXTRA_INSERTS
    out = []
    for (size, length, head), n in sorted(screws.items(), key=lambda kv: (float(kv[0][0][1:]), kv[0][1])):
        out.append((n, f"{size} x {length} mm {HEAD[head]}, stainless", "; ".join(uses[(size, length, head)])))
    for d, n in sorted(nuts.items()): out.append((n, f"{d}, stainless", "screw joints with a nut"))
    for d, n in washers.items(): out.append((n, d, "vertical pylons"))
    for s in ("M3", "M4", "M5"): out.append((inserts[s], f"{s} brass heat-set insert (for 3D prints)", "Appendix B chart"))
    return out, inserts

# (group, qty, exact description, used for, rough US price, source). Quantities are per ROV; spares are noted where worth buying.
ITEMS = [
 ('Printed parts', '{black} kg', 'PETG filament, black', 'every printed part except the cowl (includes ~10 % for brims and reprints)', '$45-60', 'Bambu / Amazon'),
 ('Printed parts', '{yellow} kg', 'PETG filament, yellow', 'the six top cowl sections', '$20-25', 'Bambu / Amazon'),
 ('Thrusters', '6', '1200 GPH bilge pump motor cartridge', 'T1-T6', '$20-25 each', 'Amazon / marine store'),
 ('Thrusters', '6', 'Brass shaft coupler, 3 mm to 5 mm, 9 mm OD x 20 mm', 'motor shaft to prop stud', '$12 (6)', 'Amazon'),
 ('Thrusters', '6', 'M5 x 20 mm set screw (grub screw), stainless', 'prop stud in each coupler', '$4 (pack)', 'Hardware store'),
 ('Thrusters', '6', 'M5 hex nut, stainless', 'jam nut, drives the prop hub', '$2 (pack)', 'Hardware store'),
 ('Thrusters', '6', 'M5 nyloc nut, stainless', 'holds the prop hub on', '$2 (pack)', 'Hardware store'),
 ('Thrusters', '12', 'M4 x 4 mm set screw (grub screw), stainless', 'oil fill and bleed ports, 2 per tail cone', '$3 (pack)', 'Hardware store'),
 ('Thrusters', '6', 'O-ring 32 x 2 mm (ID x cross-section), nitrile', 'tail cone spigot', '$6 (kit)', 'Amazon'),
 ('Thrusters', '6', 'O-ring 5 x 1.5 mm, nitrile', 'holds each compensator bladder on its nipple', 'in the 1.5 mm kit', 'Amazon'),
 ('Thrusters', '6 (+4 spare)', 'Nitrile finger cot', 'compensator bladders', '$6 (pack)', 'Pharmacy / Amazon'),
 ('Thrusters', '500 ml', 'Mineral oil (white, food or USP grade)', 'oil fill', '$6', 'Pharmacy'),
 ('Thrusters', '6', 'Cable gland M12 x 1.5, nylon, clamping range 3-6.5 mm', 'motor lead out of each tail cone', '$8 (10-pack)', 'Amazon'),
 ('Hull', '1', '4" Sch40 PVC pipe, 406 mm (16")', 'electronics hull', '$15', 'Hardware store'),
 ('Hull', '1', 'Acrylic dome 100 mm, 115 mm flange (UQISOVI, Amazon B0DR2HP4YQ)', 'camera dome', '$15-25', 'Amazon'),
 ('Hull', '4', 'O-ring AS568-238 (94.84 x 3.53 mm / 3.734 x 0.139"), nitrile 70A', 'flanges 201 and 203, two radial grooves each', '$5 (pack)', 'Amazon / McMaster'),
 ('Hull', '1', 'O-ring AS568-237 (91.67 x 3.53 mm / 3.609 x 0.139"), nitrile 70A', 'rear cap face seal, on 201', '$5 (pack)', 'Amazon / McMaster'),
 ('Hull', '1', 'O-ring AS568-240 (101.19 x 3.53 mm / 3.984 x 0.139"), nitrile 70A', 'dome face seal, on 203', '$5 (pack)', 'Amazon / McMaster'),
 ('Hull', '2', 'Cable gland M16 x 1.5, nylon, clamping range 5-10 mm', 'MOTORS and BATTERY in the rear cap', '$8 (5-pack)', 'Amazon'),
 ('Hull', '2', 'Cable gland M12 x 1.5, nylon, clamping range 3-6.5 mm', 'LIGHTS and TETHER in the rear cap', '$8 (10-pack)', 'Amazon'),
 ('Hull + pod', '2', 'M10 x 1.0 x 12 mm hex bolt (fine pitch), stainless', 'VENT plugs in 202 and 302', '$4', 'Hardware store / Amazon'),
 ('Hull + pod', '4', 'M10 bonded sealing washer (Dowty)', 'under the vent bolts and the test barb (2 spare)', '$6 (pack)', 'Amazon'),
 ('Hull + pod', '1', 'M10 x 1.0 male to 6 mm (1/4") hose barb, brass', 'vacuum tests', '$6', 'Amazon'),
 ('Sled', '2', 'M3 threaded rod, 1 m, stainless', 'cut 4 sled rods of 340 mm', '$4 each', 'Hardware store'),
 ('Sled', '24', 'M3 hex nut, stainless', 'sled rods (16) and pan-tilt base (8)', '$3 (pack)', 'Hardware store'),
 ('Sled', '12', 'M3 x 8 mm male-female standoff, brass', 'IBT_2 boards', '$10 (standoff kit)', 'Amazon'),
 ('Sled', '12', 'M3 x 8 mm female-female standoff, brass', 'IBT_2 boards', 'in the standoff kit', 'Amazon'),
 ('Sled', '24', 'M3 x 6 mm screw', 'IBT_2 boards', '$3 (pack)', 'Hardware store'),
 ('Sled', '4', 'M3 x 10 mm male-female standoff, brass', 'Pico breakout', 'in the standoff kit', 'Amazon'),
 ('Sled', '4', 'M3 x 6 mm screw', 'Pico breakout onto its standoffs', '$3 (pack)', 'Hardware store'),
 ('Sled', '4', 'M2.5 x 8 mm male-female standoff, brass', 'Pi Zero', '$6 (kit)', 'Amazon'),
 ('Sled', '4', 'M2.5 x 6 mm screw', 'Pi Zero onto its standoffs', 'in the M2.5 kit', 'Amazon'),
 ('Camera', '1', 'Arducam for Pi Zero (Pi Camera v2 size board) + 150-200 mm Pi Zero ribbon', 'camera', '$20-30', 'Arducam / Amazon'),
 ('Camera', '2', 'MG90S metal-gear micro servo (with its screws and horns)', 'pan and tilt', '$10 (2)', 'Amazon'),
 ('Camera', '9', 'M2 x 6 mm self-tapping screw', 'servo horn (4), camera (4), tilt lever (1)', '$6 (M2 kit)', 'Amazon / hobby shop'),
 ('Camera', '1', 'M2 x 8 mm self-tapping screw', 'cradle pivot', 'in the M2 kit', 'Amazon / hobby shop'),
 ('Camera', '4', 'M2 x 2 mm spacer / standoff', 'under the camera board', 'in the M2 kit', 'Amazon / hobby shop'),
 ('Camera', '1', 'M2 flat washer', 'tilt lever', 'in the M2 kit', 'Amazon / hobby shop'),
 ('Camera', '100 mm', '1 mm steel music wire', 'tilt pushrod', '$3', 'Hobby shop'),
 ('Battery pod', '1', '3" Sch40 PVC pipe, 300 mm', 'battery pod', '$12', 'Hardware store'),
 ('Battery pod', '4', 'O-ring 72 x 2.5 mm, nitrile', 'pod caps, two per cap', '$5 (pack)', 'Amazon'),
 ('Battery pod', '1', 'Cable gland M16 x 1.5, nylon, clamping range 5-10 mm', 'battery lead out of the rear cap', '$8 (5-pack)', 'Amazon'),
 ('Battery pod', '24', '18650 Li-ion cell, matched (same model and batch)', '3S8P pack', '$3-5 each', 'Battery supplier'),
 ('Battery pod', '1', '3S BMS, 40 A, with balancing', 'pack', '$12', 'Amazon'),
 ('Battery pod', '1', 'M4 threaded rod, 1 m, stainless', 'cut 4 pack tie rods of ~225 mm', '$4', 'Hardware store'),
 ('Battery pod', '16', 'M4 hex nut, stainless', 'pack tie rods', '$3 (pack)', 'Hardware store'),
 ('Battery pod', '3 m', 'Pure nickel strip, 8 x 0.2 mm (not nickel-plated steel)', 'cell links', '$10', 'Amazon'),
 ('Battery pod', '1 + 1', 'Inline ATO fuse holder, 12 AWG + 35 A ATO fuse', 'pack fuse', '$5', 'Auto parts store'),
 ('Battery pod', '1 set', 'Fish-paper insulator rings (18650), Kapton tape, silica gel packs', 'pack', '$15', 'Amazon'),
 ('Battery pod', '1', '2-part marine epoxy (JB Weld Marine or West System)', 'bonds the pod flanges to the pipe', '$10', 'Hardware store'),
 ('Lights', '2 (+1 spare)', 'Cree XHP50.2 LED, 6 V version, 5000-6500 K, on a 20 mm copper DTP star', 'light heads', '$8-12 each', 'Amazon / Satisled / KaiDomain'),
 ('Lights', '2', 'Mean Well LDD-700HW constant-current LED driver', 'inside the hull', '$8-10 each', 'Amazon / Jameco / Digi-Key'),
 ('Lights', '2', 'Glass lens 28 x 3 mm, AR coated', 'light windows', '$8 (pack)', 'Amazon'),
 ('Lights', '1', '6061 aluminium round bar, 1-3/4" x 6"', 'two 5 mm heat-sink discs', '$12', 'Amazon'),
 ('Lights', '1', 'Thermal adhesive (Arctic Alumina)', 'LED star onto the disc', '$10', 'Amazon'),
 ('Lights', '2', 'O-ring 30 x 1.5 mm, nitrile', 'front ring face groove', '$10 (1.5 mm kit)', 'Amazon'),
 ('Lights', '2', 'O-ring 24 x 1.5 mm, nitrile', 'window, under the front lip', 'in the 1.5 mm kit', 'Amazon'),
 ('Lights', '2', 'M3 x 8 mm set screw (grub screw), stainless', 'locks each light head in the cowl', '$2 (pack)', 'Hardware store'),
 ('Frame', '1', 'Black HDPE sheet, 1/2" (12.7 mm), 24 x 24" (at least 605 mm one way)', 'both side plates', '$40-60', 'Amazon / plastics supplier'),
 ('Frame', '1.6-2.3 kg', 'Lead shot in sealed bags (or lead bar)', 'belly pan ballast', '$15-25', 'Sporting goods'),
 ('Cowl', '1.0-1.7 L', 'Depth-rated closed-cell foam (PVC core foam such as H80, or 2-lb closed-cell PU)', 'buoyancy blocks in the cowl', '$20-35', 'Composites supplier / Amazon'),
 ('Junction box', '6 pairs', 'SP13 IP68 2-pin connector: panel socket (rear nut) + cable plug, 4-6.5 mm cable', 'thrusters T1-T6', '$18-25', 'Amazon / AliExpress'),
 ('Junction box', '2 pairs', 'SP13 IP68 3-pin connector: panel socket (rear nut) + cable plug, 4-6.5 mm cable', 'lights L1, L2', '$6-9', 'Amazon / AliExpress'),
 ('Junction box', '1', 'MG Chemicals 832B epoxy potting compound', 'junction box and light cavities', '$35-40', 'Amazon'),
 ('Wiring', '4 m', '2-core 18 AWG marine cable, OD 5-6 mm', '6 thruster leads + 2 light leads', '$15', 'Amazon'),
 ('Wiring', '0.8 m', '12-core control cable, 0.5 mm2 cores, OD 8-10 mm', 'junction box to the hull (motors)', '$10', 'Amazon'),
 ('Wiring', '0.5 m', '4-core cable, 0.5-0.75 mm2 cores, OD 3-6.5 mm', 'junction box to the hull (lights)', '$4', 'Amazon'),
 ('Wiring', '0.6 m', '2-core 12 AWG silicone or marine cable, OD 5-10 mm', 'battery pod to the hull', '$6', 'Amazon'),
 ('Wiring', 'as needed', 'Cat6 cable, slim (OD 6.5 mm or less), + strain relief', 'tether (data only)', '$20-40', 'Amazon'),
 ('Electronics', '6', 'IBT_2 (BTS7960) H-bridge motor driver', 'U1-U6', '$40-60 (6)', 'Amazon'),
 ('Electronics', '2', 'Mini MP1584EN buck board, fixed 5 V, 1.8 A', 'U9A, U9B', '$8 (pack)', 'Amazon'),
 ('Electronics', '1', 'Raspberry Pi Pico with headers + 57 x 63 mm screw-terminal breakout board', 'U10', '$12', 'Pi reseller / Amazon'),
 ('Electronics', '1', 'Raspberry Pi Zero 2W with header', 'U11', '$15-18', 'Pi reseller'),
 ('Electronics', '1', 'Waveshare ETH/USB HUB HAT (RTL8152B) for Pi Zero', 'U12', '$15-20', 'Waveshare / Amazon'),
 ('Electronics', '1', 'Cat6 patch lead 0.3 m, one end 90-degree', 'HAT to the tether', '$6', 'Amazon'),
 ('Electronics', '1', 'RJ45 inline coupler', 'patch lead to the tether', '$3', 'Amazon'),
 ('Electronics', '1 + 1', 'Inline ATO/ATC fuse holder, 12 AWG + 30 A fuse', 'F1', '$7', 'Auto parts store'),
 ('Electronics', '1 + 1', 'Inline mini-blade fuse holder + 3 A fuse', 'F2', '$4', 'Auto parts store'),
 ('Electronics', '1', 'Capacitor 1000 uF 25 V low-ESR electrolytic', 'C1', '$1', 'DigiKey / Mouser'),
 ('Electronics', '1', 'Capacitor 470 uF 10 V electrolytic', 'C2', '$0.50', 'DigiKey / Mouser'),
 ('Electronics', '1', '1N5817 Schottky diode', 'D1', '$0.25', 'DigiKey / Mouser'),
 ('Electronics', '3', 'Resistor 10 k, 1/4 W', 'R1, R2, R4', '$0.10 each', 'Any'),
 ('Electronics', '1', 'Resistor 33 k, 1/4 W', 'R3', '$0.10', 'Any'),
 ('Electronics', '2', 'Wago 221-415 lever connector (5-way)', '12 V and GND bus', '$6 (2)', 'Amazon'),
 ('Electronics', '1 m + 1 m', '14 AWG silicone wire, red + black', 'bus to the top driver boards', '$8', 'Amazon'),
 ('Electronics', '0.5 m + 0.5 m', '16 AWG silicone wire, red + black', 'jumpers to the bottom driver boards', '$6', 'Amazon'),
 ('Electronics', '1 m + 1 m', '20 AWG silicone wire, red + black', 'aux branch', '$5', 'Amazon'),
 ('Electronics', '1 set', 'Dupont female housings + 22 AWG hook-up wire', 'logic wiring', '$8', 'Amazon'),
 ('Supplies', '1', 'Silicone O-ring grease (not petroleum)', 'every O-ring', '$6', 'Hardware store'),
 ('Supplies', '1', 'Silicone dielectric grease', 'SP13 plug threads and pins', '$6', 'Hardware store'),
 ('Supplies', '1', 'Clear silicone sealant (RTV), small tube', 'gland threads and oil-port set screws', '$6', 'Hardware store'),
 ('Supplies', '1 set', 'Heat-shrink assortment incl. 20-25 mm clear, double-sided foam tape, zip ties 2.5-3.6 mm', 'splices, buck boards, harness', '$8', 'Any'),
]

FASTENER_PRICE = {"screw": ("$3-5 (pack)", "Amazon / hardware store"), "nut": ("$3 (pack)", "Amazon / hardware store"),
                  "washer": ("$2 (pack)", "Hardware store"), "insert": ("$8-10 (pack)", "Amazon")}

def buy_list(black_kg, yellow_kg):
    """[(group, qty, description, used for, price, source)] for the whole ROV, fasteners counted from the fastener table"""
    rows = [(g, q.format(black=black_kg, yellow=yellow_kg), d, u, c, s) for g, q, d, u, c, s in ITEMS]
    fl, _ = fastener_lines()
    def price(d): return next(v for k, v in FASTENER_PRICE.items() if k in d)
    i = next(k for k, r in enumerate(rows) if r[0] == "Thrusters")
    return rows[:i] + [("Fasteners", str(n), d, u) + price(d) for n, d, u in fl] + rows[i:]
