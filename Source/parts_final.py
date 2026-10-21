"""
Final printed-parts list (one clean set of file names) and the copy step that fills out_final/ with them.
Colour: the top cowl is printed in YELLOW PETG, every other printed part in BLACK PETG.
Run: python3 parts_final.py <vols.json>   (copies STLs into out_final/ and adds their volumes to the table)
"""
import os, sys, json, shutil, trimesh

OUTF = "out_final"
CAM = "rov_project/camera_mount"
# (section, final stem, source path, qty, material, print notes, used for)
_SRC = {}
def P(sec, stem, src, qty, mat, note, use):
    _SRC[stem] = src
    return (sec, stem, OUTF, qty, mat, note, use)

BK, YL = "PETG, black", "PETG, yellow"
PRINTED_A = [   # ROV_Frame.3mf
 P("Stations + brackets", "rov_station_top_port", "out_v5/rov5_station_top_port", 2, BK, "Flat, no supports. 2x M5 + 1x M3 heat-set inserts.", "Station top, port half: hull top + upper arm"),
 P("Stations + brackets", "rov_station_top_stbd", "out_v5/rov5_station_top_stbd", 2, BK, "Flat, no supports. 2x M5 + 1x M3 heat-set inserts.", "Station top, starboard half"),
 P("Stations + brackets", "rov_station_mid", "out_v5/rov5_station_mid", 2, BK, "Flat, no supports. M4 nuts in the pockets.", "Station middle: hull bottom + pod top"),
 P("Stations + brackets", "rov_station_bot_port", "out_v5/rov5_station_bot_port", 2, BK, "Flat, no supports. 2x M5 + 1x M4 inserts.", "Station bottom, port half: pod bottom + lower arm"),
 P("Stations + brackets", "rov_station_bot_stbd", "out_v5/rov5_station_bot_stbd", 2, BK, "Flat, no supports. 2x M5 + 1x M4 inserts.", "Station bottom, starboard half"),
 P("Stations + brackets", "rov_junction_deck", "out_v5/rov5_junction_deck", 1, BK, "Flat. 4x M3 heat-set inserts.", "Carries the junction box (501)"),
 P("Stations + brackets", "rov_bracket_corner_a", "out_v5/rov5_bracket_corner_a", 2, BK, "Plate face down. 5 walls, 40 %. 4x M3 + 2x M5 inserts.", "Front-port + rear-starboard thruster bracket"),
 P("Stations + brackets", "rov_bracket_corner_b", "out_v5/rov5_bracket_corner_b", 2, BK, "Plate face down. 5 walls, 40 %. 4x M3 + 2x M5 inserts.", "Front-starboard + rear-port thruster bracket"),
 P("Thruster pylons", "pylon_clamp", "out/pylon_clamp", 6, BK, "Rear end down, no supports. M4 + M3 inserts.", "Clamps each thruster body"),
 P("Belly pan", "rov_belly_pan", "out_v5/rov5_belly_pan", 1, BK, "Floor down, no supports.", "Lead ballast tray under the pod"),
 P("Top cowl (YELLOW)", "rov_cowl_rear_port", "out_v5/rov5_cowl_rear_port", 1, YL, "Rear end down. The 3 mm shell prints solid.", "Top cowl, rear, port (v2)"),
 P("Top cowl (YELLOW)", "rov_cowl_rear_stbd", "out_v5/rov5_cowl_rear_stbd", 1, YL, "Rear end down.", "Top cowl, rear, starboard (v2)"),
 P("Top cowl (YELLOW)", "rov_cowl_mid_port", "out_v5/rov5_cowl_mid_port", 1, YL, "Seam face down. Tree supports (vertical thruster sleeve).", "Top cowl, middle, port (v2)"),
 P("Top cowl (YELLOW)", "rov_cowl_mid_stbd", "out_v5/rov5_cowl_mid_stbd", 1, YL, "Seam face down. Tree supports.", "Top cowl, middle, starboard (v2)"),
 P("Top cowl (YELLOW)", "rov_cowl_front_port", "out_v5/rov5_cowl_front_port", 1, YL, "Nose down (light sleeve vertical).", "Top cowl, front, port (v2)"),
 P("Top cowl (YELLOW)", "rov_cowl_front_stbd", "out_v5/rov5_cowl_front_stbd", 1, YL, "Nose down.", "Top cowl, front, starboard (v2)"),
]
PRINTED_B = [   # ROV_Core.3mf
 P("Thrusters", "housing_no_foot", "out/housing_no_foot", 6, BK, "Threaded rear end down, brim, 5 walls.", "Thruster body + Kort duct"),
 P("Thrusters", "tail_cone_comp", "out/tail_cone_comp", 6, BK, "Tip down, brim. Tap the tip M12 x 1.5.", "Tail cone with oil compensator"),
 P("Thrusters", "prop_hub_RH", "out/prop_hub_RH", 3, BK, "Back face down, tree supports under the blades.", "Right-hand prop"),
 P("Thrusters", "prop_hub_LH", "out/prop_hub_LH", 3, BK, "Back face down, tree supports under the blades.", "Left-hand prop"),
 P("Thrusters", "nose_cone", "out/nose_cone", 6, BK, "Base down.", "Prop spinner"),
 P("Thrusters", "coupler_gauge", "out/coupler_gauge", 1, BK, "Tool only, any material.", "Sets the coupler height"),
 P("Hull + sled", "br_flange_rear", "rov_project/br_flange_rear", 1, BK, "Ring face down. SOLID: 100 % infill (holds water out).", "Hull rear flange (your design)"),
 P("Hull + sled", "rov_endcap_rear_5hole", "out/rov_endcap_rear_5hole", 1, BK, "Flat. SOLID: 100 % infill (holds water out).", "Hull rear cap: 4 glands + vent"),
 P("Hull + sled", "br_flange_front_dome", "rov_project/br_flange_front_dome", 1, BK, "Ring face down. SOLID: 100 % infill (holds water out).", "Dome flange (your design)"),
 P("Hull + sled", "dome_retaining_ring", "rov_project/dome_retaining_ring", 1, BK, "Flat.", "Dome clamp ring (your design)"),
 P("Hull + sled", "m03r7-001-00a", f"{CAM}/m03r7-001-00a", 1, BK, "As supplied.", "Sled front bulkhead (your design)"),
 P("Hull + sled", "sled_rail_port", "prep/sled_rail_port", 1, BK, "Flat outer face down, no supports.", "Sled side rail, port (12 V side)"),
 P("Hull + sled", "sled_rail_stbd", "prep/sled_rail_stbd", 1, BK, "Flat outer face down, no supports.", "Sled side rail, starboard (logic side)"),
 P("Hull + sled", "sled_deck", "prep/sled_deck", 1, BK, "Flat. 4 walls, 40 %.", "Sled deck: boards on both faces"),
 P("Hull + sled", "sled_bulkhead_rear_v2", "prep/sled_bulkhead_rear_v2", 1, BK, "Front face down, pockets up.", "Sled rear bulkhead: 12 V bus + LED drivers"),
 P("Hull + sled", "pantilt_base", "prep/pantilt_base", 1, BK, "Plate face down, no supports. 5 walls.", "Pan-tilt base v2: on the sled rods, carries the pan servo"),
 P("Hull + sled", "pantilt_yoke", "prep/pantilt_yoke", 1, BK, "Base down, no supports. 5 walls, 40 % infill.", "Pan-tilt yoke v2: on the pan horn, tilt servo in a closed pocket"),
 P("Hull + sled", "pantilt_cradle", "prep/pantilt_cradle", 1, BK, "On its side, axle up. Tree supports ON (under the port cheek). 100 %.", "Pan-tilt camera cradle"),
 P("Hull + sled", "pantilt_lever", "prep/pantilt_lever", 1, BK, "Flat. 100 %.", "Tilt lever on the cradle axle"),
 P("Battery pod", "rov_pod_flange_3in", "out/rov_pod_flange_3in", 2, BK, "Socket end down. SOLID: 100 % infill. 6x M5 inserts each.", "3\" pod flange, one at each end"),
 P("Battery pod", "rov_pod_endcap_3in_rear", "out/rov_pod_endcap_3in", 1, BK, "Plate down. SOLID: 100 % infill (holds water out).", "3\" pod rear cap: M16 gland + vent"),
 P("Battery pod", "rov_pod_endcap_3in_front", "out_v5/rov6_pod_endcap_3in_blank", 1, BK, "Plate down. SOLID: 100 % infill (holds water out).", "3\" pod front cap, blank (no holes)"),
 P("Battery pod", "rov_cell_plate_8_v2", "prep/rov_cell_plate_8_v2", 6, BK, "Grooved face down.", "18650 holder plate"),
 P("Battery pod", "rov_cell_spacer_3mm", "prep/rov_cell_spacer_3mm", 8, BK, "Flat.", "Rod spacer between groups"),
 P("Lights", "rov_light_rear_body", "out/rov_light_rear_body", 2, BK, "Socket end down. 5 walls. (ASA also fine.)", "Light head rear body (v2)"),
 P("Lights", "rov_light_front_ring", "out/rov_light_front_ring", 2, BK, "Front face down. SOLID: 100 % infill (seals the window).", "Light head front ring"),
 P("Lights", "rov_light_spacer", "out/rov_light_spacer", 2, BK, "Flat.", "Window spacer"),
 P("Junction boxes", "rov_junction_box", "out/rov_junction_box", 1, BK, "Base down, no supports. 5 walls.", "Junction box: 6 thruster + 2 light SP13 sockets, 12-core + 4-core out"),
 P("Junction boxes", "rov_junction_lid", "out/rov_junction_lid", 1, BK, "Top face down (as exported), no supports.", "Junction box lid with the socket map"),
]
PRINTED = PRINTED_A + PRINTED_B
def is_yellow(stem): return "cowl" in stem
# scene keys (assembly + thumbnails) that are printed parts: rendered black, except the cowl (yellow)
SRC = _SRC

if __name__ == "__main__":
    os.makedirs(OUTF, exist_ok=True)
    vols = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else {}
    for stem, src in SRC.items():
        shutil.copy(src + ".stl", f"{OUTF}/{stem}.stl")
        t = trimesh.load(f"{OUTF}/{stem}.stl"); vols[stem] = [t.volume/1000, list(map(float, t.extents))]
    if len(sys.argv) > 1: json.dump(vols, open(sys.argv[1], "w"))
    print(len(SRC), "parts,", sum(p[3] for p in PRINTED), "pieces")

# ------------------------------------------------------------------ part numbers + debossed labels
# PN: three digits, first digit = subsystem (1 thrusters, 2 hull + sled, 3 battery pod, 4 lights, 5 junction boxes,
#     6 stations + brackets, 7 belly pan, 8 top cowl, 9 cut HDPE plates). Every printed part carries its number.
PN = {"housing_no_foot": "101", "tail_cone_comp": "102", "prop_hub_RH": "103", "prop_hub_LH": "104", "nose_cone": "105",
      "pylon_clamp": "106", "coupler_gauge": "107",
      "br_flange_rear": "201", "rov_endcap_rear_5hole": "202", "br_flange_front_dome": "203", "dome_retaining_ring": "204",
      "ETRAY4-ROV-TRAY-R2": "205", "rov_sled_bulkhead_rear": "206", "m03r7-001-00a": "207", "m03r7-002-00a": "208",
      "m03r7-003-00a": "209", "m03r7-004-00a": "210", "m03r7-005-00a": "211",
      "rov_pod_flange_3in": "301", "rov_pod_endcap_3in_rear": "302", "rov_pod_endcap_3in_front": "303", "rov_cell_plate_8": "304",
      "rov_light_rear_body": "401", "rov_light_front_ring": "402", "rov_light_spacer": "403",
      "rov_junction_box": "501", "rov_junction_lid": "503",          # 502 retired (old lights box)
      "rov_station_top_port": "601", "rov_station_top_stbd": "602", "rov_station_mid": "603", "rov_station_bot_port": "604",
      "rov_station_bot_stbd": "605", "rov_junction_deck": "606", "rov_bracket_corner_a": "607", "rov_bracket_corner_b": "608",
      "rov_belly_pan": "701",
      "rov_cowl_rear_port": "801", "rov_cowl_rear_stbd": "802", "rov_cowl_mid_port": "803", "rov_cowl_mid_stbd": "804",
      "rov_cowl_front_port": "805", "rov_cowl_front_stbd": "806"}
PN_CUT = {"rov_side_plate_port": "901", "rov_side_plate_stbd": "902"}
def L(text, anchor=None, hmax=6.0, level="top", hmin=2.4, side=None, margin=1.2): return {"text": text, "anchor": anchor, "hmax": hmax, "level": level, "hmin": hmin, "side": side, "margin": margin}
# labels beyond the part number (which every part gets): where things mount / which way round
LABELS = {
 "rov_endcap_rear_5hole": [L("MOTORS", (30, 35), 4.5, "bottom"), L("LIGHTS", (-30, 35), 4.5, "bottom"),
                           L("BATTERY", (-30, -35), 4.5, "bottom"), L("TETHER", (30, -35), 4.5, "bottom"), L("VENT", (0, 12), 3.5, "bottom")],
 "rov_pod_endcap_3in_rear": [L("REAR", (0, 44), 4.5, "bottom"), L("BATTERY", (0, -28), 4.5, "bottom"), L("VENT", (0, 26), 3.5, "bottom")],
 "rov_pod_endcap_3in_front": [L("FRONT", (0, 30), 5, "bottom")],
 "rov_cell_plate_8": [L("TAB", (0, 31), 3.0, "bottom", 2.0)],
 "ETRAY4-ROV-TRAY-R2": [L("< FRONT", (14, 50), 5), L("LOGIC 5V / 3.3V", (55, 88), 4.5), L("PI ZERO 2W", (45, 50), 5),
                        L("PICO", (85, 50), 5), L("12V POWER", (165, 88), 4.5), L("MOTOR DRIVERS", (150, 50), 4.5),
                        L("LED DRIVERS", (150, 14), 4), L("BUCK 5V", (200, 75), 4), L("FUSE", (205, 30), 4)],
 "rov_sled_bulkhead_rear": [L("REAR - GLAND SIDE", (0, 0), 4)],
 "rov_junction_deck": [L("JUNCTION BOX", (0, 0), 5, "bottom")],
 "rov_station_top_port": [L("PORT", None, 6)], "rov_station_top_stbd": [L("STBD", None, 6)],
 "rov_station_bot_port": [L("PORT", None, 6)], "rov_station_bot_stbd": [L("STBD", None, 6)],
 "rov_bracket_corner_a": [L("A  FP/RS", None, 5)], "rov_bracket_corner_b": [L("B  FS/RP", None, 5)],
 "prop_hub_RH": [L("RH", None, 4, "bottom")], "prop_hub_LH": [L("LH", None, 4, "bottom")],
 "rov_cowl_rear_port": [L("REAR PORT", None, 5)], "rov_cowl_rear_stbd": [L("REAR STBD", None, 5)],
 "rov_cowl_mid_port": [L("MID PORT", None, 5)], "rov_cowl_mid_stbd": [L("MID STBD", None, 5)],
 "rov_cowl_front_port": [L("FRONT PORT", None, 5)], "rov_cowl_front_stbd": [L("FRONT STBD", None, 5)],
}

# part-number label overrides (where the default "biggest flat face" doesn't suit the part)
PN_LABEL = {"prop_hub_RH": L("103", None, 4, "bottom", 1.8), "prop_hub_LH": L("104", None, 4, "bottom", 1.8),
            "rov_junction_box": L("501", None, 6, "bottom")}
SMALL = dict(hmin=1.6, margin=0.5)

PN_LABEL["rov_light_spacer"] = L("403", None, 3.0, "bottom", 1.3, margin=0.3)

# ---- camera pan-tilt (replaces 208-211); base on the sled rods in front of 207
PN.update({"sled_rail_port": "212", "sled_rail_stbd": "213", "sled_deck": "214", "sled_bulkhead_rear_v2": "215", "rov_cell_plate_8_v2": "305", "rov_cell_spacer_3mm": "306", "pantilt_base": "216", "pantilt_yoke": "217", "pantilt_cradle": "218", "pantilt_lever": "219"})
LABELS.update({"pantilt_base": [L("TOP", (0, 40), 5), L("PAN SERVO", (0, -20), 4)],
               "pantilt_yoke": [L("TILT", None, 4)]})
PN_LABEL["pantilt_lever"] = L("219", None, 2.5, "top", 1.4, margin=0.4)

PRE_LABELED = {"sled_rail_port", "sled_rail_stbd", "sled_deck", "sled_bulkhead_rear_v2", "rov_cell_plate_8_v2", "rov_cell_spacer_3mm"}   # engraved by the electronics chat

# ------------------------------------------------------------------ final lists use the labelled files: <PN>_<stem>.stl in out_lbl/
BASE_A, BASE_B = PRINTED_A, PRINTED_B
def _pn(lst): return [(sec, f"{PN[st]}_{st}", "out_lbl", q, mat, note, use) for sec, st, src, q, mat, note, use in lst]
PRINTED_A, PRINTED_B = _pn(BASE_A), _pn(BASE_B)
PRINTED = PRINTED_A + PRINTED_B
BASE_PRINTED = BASE_A + BASE_B
def base(stem): return stem.split("_", 1)[1] if stem[:3].isdigit() and stem[3:4] == "_" else stem
def pn(stem): return stem[:3] if stem[:3].isdigit() else PN.get(stem, "")
