"""
Where every guide picture lives: in the build folder (what the guide reads) and in the package (Images/...).
build_guide_final.build_package() copies build -> package with this table; build.py carries pictures the other way
(package -> build) for anything the current run didn't regenerate, so the guide always builds from a checkout.
"""
CROP = "render/final/crop"

RENDERS = ("front", "rear", "side", "top", "under", "open", "exploded")
STEPS = ("thr_ex", "thr_as", "sled", "hull", "pod", "pack", "light_ex", "light_as", "lightsleeve", "lightmount", "station", "plate",
         "thrusters", "belly", "deck", "cowl", "tile", "pantilt", "pantilt_top", "pantilt_fit")
ELECTRONICS = (("e_layout_top", "sled_top_face"), ("e_layout_bot", "sled_bottom_face"), ("e_stack", "stacked_pair"), ("e_rear", "rear_bay"),
               ("e_wire_port", "harness_port"), ("e_wire_stbd", "harness_starboard"), ("e_hull", "sled_in_hull"),
               ("elec_sch1", "schematic_1_power_and_drivers"), ("elec_sch2", "schematic_2_control_and_lights"), ("elec_wiring", "wiring_diagram"))
LABELS = ("L_bh215", "L_deck", "L_deck214", "L_jbox", "L_rearcap", "L_station")          # label close-ups (no generator: kept as pictures)
PICTURE_STEPS = ("sled", "pantilt", "hull", "pod", "stations", "plates", "belly", "jbox", "sledin", "cowl")   # Appendix B
INSERT_PARTS = ("106", "201", "203", "301", "501", "601", "602", "604", "605", "606", "607", "608", "801", "802", "803", "804", "805", "806")
FP = "TinkerSub_KB-1"

def image_map(printed_stems):
    """[(path in the build folder, path in the package)] for every picture the guide uses"""
    m = [(f"{CROP}/pf_{s}.png", f"Images/Parts/{s}.png") for s in printed_stems]
    m += [(f"{CROP}/f_{f}.png", f"Images/Renders/{f}.png") for f in RENDERS]
    m += [(f"{CROP}/f_{f}.png", f"Images/Assembly_steps/{f}.png") for f in STEPS]
    m += [(f"{CROP}/f_{f}.png", f"Images/Electronics/{n}.png") for f, n in ELECTRONICS]
    m += [(f"out/{f}.png", f"Images/Diagrams/{f}.png") for f in ("prop_hex_section", "compensator_section", "compensator_cutaway")]
    m += [(f"{CROP}/f_layout.png", "Images/Diagrams/thruster_layout.png"), (f"{CROP}/f_nest.png", "Images/Diagrams/side_plates_on_24x24_sheet.png")]
    m += [(f"outdir/ROV_{n}_plates.png", f"Images/Diagrams/{FP}_{n}_plates.png") for n in ("Frame", "Core")]
    m += [(f"{CROP}/{f}.png", f"Images/Labels/{f}.png") for f in LABELS]
    m += [(f"{CROP}/f_ik_{f}.png", f"Images/Picture_by_picture/{f}.png") for f in PICTURE_STEPS]
    m += [(f"{CROP}/f_ins_{p}.png", f"Images/Inserts/{p}.png") for p in INSERT_PARTS]
    return m
