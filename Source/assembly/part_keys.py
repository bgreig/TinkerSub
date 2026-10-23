"""Assembly keys (rov_v6.parts / inst) -> part file stems and three-digit part numbers."""
import parts_final as PF

KEYMAP = {"st_top_port": "rov_station_top_port", "st_top_stbd": "rov_station_top_stbd", "st_mid": "rov_station_mid",
          "st_bot_port": "rov_station_bot_port", "st_bot_stbd": "rov_station_bot_stbd", "jdeck": "rov_junction_deck",
          "brk_corner_a_0": "rov_bracket_corner_a", "brk_corner_a_3": "rov_bracket_corner_a", "brk_corner_b_1": "rov_bracket_corner_b",
          "brk_corner_b_2": "rov_bracket_corner_b", "belly": "rov_belly_pan", "pylon": "pylon_clamp", "housing": "housing_no_foot",
          "tail": "tail_cone_comp", "hub": "prop_hub", "nose": "nose_cone", "cell_plate": "rov_cell_plate_8_v2",
          "pod_fl": "rov_pod_flange_3in", "pod_fl_front": "rov_pod_flange_3in", "pod_cap": "rov_pod_endcap_3in_rear",
          "pod_cap_front": "rov_pod_endcap_3in_front", "jbox": "rov_junction_box", "jlid": "rov_junction_lid",
          "lt_rear": "rov_light_rear_body", "lt_front": "rov_light_front_ring", "lt_spacer": "rov_light_spacer",
          "cap_rear": "rov_endcap_rear_5hole", "fl_rear": "br_flange_rear", "fl_front": "br_flange_front_dome",
          "dome_ring": "dome_retaining_ring", "tray": "ETRAY4-ROV-TRAY-R2", "bh_rear": "rov_sled_bulkhead_rear",
          "hdpe_port": "rov_side_plate_port", "sl_rail_p": "sled_rail_port", "sl_rail_s": "sled_rail_stbd", "sl_deck": "sled_deck", "sl_bh": "sled_bulkhead_rear_v2", "pt_base": "pantilt_base", "pt_yoke": "pantilt_yoke", "pt_cradle": "pantilt_cradle", "pt_lever": "pantilt_lever", "hdpe_stbd": "rov_side_plate_stbd",
          **{f"cowl_{a}_{b}": f"rov_cowl_{a}_{b}" for a in ("front", "mid", "rear") for b in ("port", "stbd")}}

EXTRA = {"bh_front": "sled_bulkhead_front", "hub": "prop_hub_RH"}

def stem_of(k): return KEYMAP.get(k, EXTRA.get(k, k))

def pn_of(k):
    """three-digit part number of an assembly key, or the key itself for bought parts (hull, pod, rod, ...)"""
    s = stem_of(k)
    p = PF.PN.get(s, PF.PN_CUT.get(s))
    if k == "hub": return "103/104"
    return p or k
