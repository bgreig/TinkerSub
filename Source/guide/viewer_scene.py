"""
Scene for the interactive 3D viewer: the whole ROV with the electronics, the harness inside the hull and the cables outside it.

  - every assembled part from render/asm.json, with clean names and part numbers
  - the electronics sled from render/elec_scene.json (boards, bus, fuses, LED drivers, harness), moved from the sled frame into
    the assembly frame: x -> -x, z -> 145 - z (checked: rails, bulkhead 215, deck 214 and the rear cap land exactly on the assembly's)
  - the cables outside the hull, routed between the real connection points: each thruster's tail gland to its junction-box
    socket (the mated SP13 plug's tail), each light's rear exit to its socket, the box's 12-core and 4-core exits to the MOTORS and
    LIGHTS glands in the rear cap, the battery lead from the pod's rear cap to the BATTERY gland, and the tether from the TETHER
    gland. The end points come from the model; the paths between them are drawn, not measured.

Writes two files (each under the 16 MB a published page file may be): <out>/viewer_model.json (parts + outside cables) and
<out>/viewer_electronics.json (the sled electronics and harness).
usage: python3 viewer_scene.py render/asm.json render/elec_scene.json <out_dir>
"""
import sys, os, json, base64, re
import numpy as np, trimesh
import rov_v5 as V, jbox as JB, lights as LT

ASM, ELEC, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
SLED2WORLD = np.array([[-1, 0, 0, 0], [0, 1, 0, 0], [0, 0, -1, 145.0], [0, 0, 0, 1]], float)
def M16(M): return np.asarray(M, float).T.flatten().round(5).tolist()          # three.js Matrix4.fromArray: column-major

# ---------------------------------------------------------------- names
NAMES = {"hub": "103 / 104  Prop hub, right / left hand", "bh_front": "207  Sled front bulkhead", "tail": "102  Tail cone with oil compensator",
  "cap_rear": "202  Hull rear end cap (4 glands + vent)", "fl_rear": "201  Hull rear flange", "fl_front": "203  Hull front (dome) flange",
  "dome_ring": "204  Dome retaining ring", "dome": "Acrylic camera dome, 100 mm", "hull": "Hull: 4\" Sch40 PVC pipe, 406 mm",
  "pod": "Battery pod: 3\" Sch40 PVC pipe, 300 mm", "pod_fl": "301  Battery pod flange (rear)", "pod_fl_front": "301  Battery pod flange (front)",
  "pod_cap": "302  Battery pod rear cap (gland + vent)", "pod_cap_front": "303  Battery pod front cap", "cell": "18650 Li-ion cell (24, 3S8P)",
  "cell_plate": "305  Cell holder plate", "rod": "M3 threaded rod, 340 mm (sled)", "housing": "101  Thruster housing with Kort duct",
  "nose": "105  Nose cone", "pylon": "106  Pylon clamp", "lt_rear": "401  Light rear body", "lt_front": "402  Light front ring",
  "lt_spacer": "403  Light window spacer", "lt_disc": "Light heat-sink disc, 42 x 5 mm aluminium", "lt_window": "Light window, 28 x 3 mm glass",
  "lt_led": "Cree XHP50.2 LED on 20 mm star", "st_top_port": "601  Station top, port", "st_top_stbd": "602  Station top, starboard",
  "st_mid": "603  Station middle", "st_bot_port": "604  Station bottom, port", "st_bot_stbd": "605  Station bottom, starboard",
  "jdeck": "606  Junction deck", "belly": "701  Belly pan (lead ballast)", "jbox": "501  Junction box (SP13 sockets)", "jlid": "503  Junction box lid",
  "sp13_plugs": "SP13 IP68 plugs, mated", "hdpe_port": "901  Side plate, port (1/2\" HDPE)", "hdpe_stbd": "902  Side plate, starboard (1/2\" HDPE)",
  "pt_pan_servo": "Pan servo, MG90S", "pt_tilt_servo": "Tilt servo, MG90S", "pt_camera": "Arducam camera for Pi Zero",
  "cowl_rear_port": "801  Top cowl, rear port", "cowl_rear_stbd": "802  Top cowl, rear starboard", "cowl_mid_port": "803  Top cowl, middle port",
  "cowl_mid_stbd": "804  Top cowl, middle starboard", "cowl_front_port": "805  Top cowl, front port", "cowl_front_stbd": "806  Top cowl, front starboard",
  "brk_corner_a": "607  Corner thruster bracket A", "brk_corner_b": "608  Corner thruster bracket B",
  "sl_rail_p": "212  Sled side rail, port", "sl_rail_s": "213  Sled side rail, starboard", "sl_deck": "214  Sled deck", "sl_bh": "215  Sled rear bulkhead",
  "pt_base": "216  Pan-tilt base", "pt_yoke": "217  Pan-tilt yoke", "pt_cradle": "218  Camera cradle", "pt_lever": "219  Tilt lever"}
ELEC_NAMES = {"ibt_T1": "IBT_2 motor driver T1 (U1)", "ibt_T2": "IBT_2 motor driver T2 (U2)", "ibt_T3": "IBT_2 motor driver T3 (U3)",
  "ibt_T4": "IBT_2 motor driver T4 (U4)", "ibt_T5": "IBT_2 motor driver T5 (U5)", "ibt_T6": "IBT_2 motor driver T6 (U6)",
  "pizero": "Raspberry Pi Zero 2W (U11)", "pihat": "Waveshare ETH/USB HUB HAT (U12)", "pico": "Raspberry Pi Pico (U10)",
  "pico_brk": "Pico screw-terminal breakout (U10)", "pico_hdr": "Pico headers", "pico_term": "Breakout screw terminals", "pico_term_hole": "Breakout screw terminals",
  "pico_term_sc": "Breakout screw terminals", "mini_buck": "MP1584EN 5 V buck boards (U9A, U9B)", "mini_buck_hs": "Heat-shrink over the 5 V bucks",
  "ldd1": "Mean Well LDD-700HW LED driver, L1 (U7)", "ldd2": "Mean Well LDD-700HW LED driver, L2 (U8)",
  "wago_12v": "Wago 221-415, +12 V bus", "wago_gnd": "Wago 221-415, GND bus", "wago_lever": "Wago levers", "wago_slot": "Wago 221-415",
  "f1": "Fuse F1, 30 A (battery feed)", "f2": "Fuse F2, 3 A (lights + 5 V)", "c1": "C1, 1000 uF (5 V bucks' 12 V feed)", "c2": "C2, 470 uF (servo supply)",
  "d1": "D1, 1N5817 (5 V to Pico VSYS)", "d1_w": "D1 leads", "glands": "Rear cap cable glands + vent", "standoffs": "Board standoffs",
  "screws": "Board screws", "rj_coupler": "RJ45 inline coupler", "cat6": "Cat6: tether to the HAT", "ribbon": "Camera ribbon",
  "feed_B+": "14 AWG +12 V feeds to the top drivers", "feed_B-": "14 AWG GND feeds to the top drivers", "jump_B+": "16 AWG +12 V jumpers to the bottom drivers",
  "jump_B-": "16 AWG GND jumpers to the bottom drivers", "bat_jacket": "Battery lead, 12 AWG twin", "bat_red": "Battery +, 12 AWG", "bat_red2": "Battery + after F1",
  "bat_blk": "Battery -, 12 AWG", "aux_red": "20 AWG aux +12 V (F2 branch)", "aux_blk": "20 AWG aux GND", "c1_w": "C1 leads",
  "motor_cable": "12-core motor cable (from the junction box)", "motor_cores": "Motor pairs to M+ / M- of each driver",
  "lights_cable": "4-core lights cable (from the junction box)", "lights_cores": "LED pairs to the LDD outputs",
  "dupont": "Dupont plugs at the driver headers", "dupont_w": "Logic wires: drivers to the Pico", "dim_w": "Lights DIM wire", "servo_w": "Servo leads",
  "cpt_out": "5 V wires to the Pi and Pico", "splice": "Solder splices", "solder_sleeve": "Solder sleeves", "harness_tie": "Harness zip ties", "ziptie": "Zip ties"}
# parts the assembly already has (the electronics scene carries its own copies for its renders)
ELEC_SKIP = {"hull", "fl_front", "fl_rear", "cap_rear", "dome", "dome_ring", "rail_212", "rail_213", "deck_214", "bh_207", "bh_215", "rods",
             "pt", "pt_cam", "pt_servo"}

def hexcol(c): return int(c.lstrip("#"), 16) if isinstance(c, str) else int(c)

def enc(t, color, label, **kw):
    v, f = np.asarray(t.vertices, np.float32), np.asarray(t.faces, np.uint32)
    return {"v": base64.b64encode(v.tobytes()).decode(), "i": base64.b64encode(f.tobytes()).decode(), "color": color, "label": label, **kw}

# ---------------------------------------------------------------- cables
def smooth(pts, r=14.0, n=6):
    """polyline with every corner replaced by a quadratic fillet"""
    P = [np.asarray(p, float) for p in pts]; out = [P[0]]
    for a, b, c in zip(P, P[1:], P[2:]):
        u, w = b - a, c - b; f = min(r, np.linalg.norm(u) / 2.1, np.linalg.norm(w) / 2.1)
        p0, p1 = b - u / np.linalg.norm(u) * f, b + w / np.linalg.norm(w) * f
        out += [(1 - t) ** 2 * p0 + 2 * (1 - t) * t * b + t ** 2 * p1 for t in np.linspace(0, 1, n)]
    return out + [P[-1]]

def cable(pts, r):
    """round cable: cylinders between the smoothed points, spheres at the joints"""
    P = smooth(pts); parts = []
    for a, b in zip(P, P[1:]):
        L = np.linalg.norm(b - a)
        if L < 1e-3: continue
        c = trimesh.creation.cylinder(radius=r, height=L, sections=12)
        c.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], (b - a) / L)); c.apply_translation((a + b) / 2); parts.append(c)
    parts += [trimesh.creation.icosphere(1, radius=r).apply_translation(p) for p in P[1:-1]]
    return trimesh.util.concatenate(parts)

def outside_cables(asm):
    def inst(k): return [np.array(i["m"]).reshape(4, 4).T for i in asm["instances"] if i["k"] == k]
    def pt(M, p): return (M @ np.r_[p, 1.0])[:3]
    out = []
    # junction box sockets: the mated plug's cable tail (jbox.plugs(): 78.5 mm out from the face)
    NRM = {"-x": (-1, 0, 0), "+x": (1, 0, 0), "+y": (0, 1, 0)}
    sock = {}
    for n, face, _ax, c in JB.sockets():
        nl = np.array(NRM[face], float)
        sock[n] = (pt(V.JB_M, np.array(c) + nl * 78.5), V.JB_M[:3, :3] @ nl)
    # thruster tail glands: tip of each 102 plus the M12 gland, named by position (x + is port, z + is forward)
    for M in inst("tail"):
        tip, ax = pt(M, (0, 0, -23.0 - 12.0)), M[:3, :3] @ np.array([0, 0, -1.0])
        x, z = M[0, 3], M[2, 3]
        name = ("T5" if x > 0 else "T6") if abs(z) < 60 else (("T1" if x > 0 else "T2") if z > 0 else ("T3" if x > 0 else "T4"))
        s, sn = sock[name]
        a1, s1 = tip + ax * 25, s + sn * 30
        mid = (a1 + s1) / 2; mid[1] = max(a1[1], s1[1]) + 8
        out.append((f"lead_{name}", cable([tip, a1, mid, s1, s], 2.75), 0x1b1d20, f"Thruster lead {name}: 2-core 18 AWG, tail cone gland to its junction box socket"))
    # light leads: out of the back of each 401 to L1 (port) / L2 (starboard) on the box's front face
    for M in inst("lt_rear"):
        ex = pt(M, (0, 0, LT.CABLE_EXIT[2] - 2)); back = M[:3, :3] @ np.array([0, 0, -1.0])
        name = "L1" if M[0, 3] > 0 else "L2"; s, sn = sock[name]
        e1 = ex + back * 25; s1 = s + sn * 30
        mid = np.array([(e1[0] + s1[0]) / 2, max(e1[1], s1[1]) + 4, (e1[2] + s1[2]) / 2])
        out.append((f"lead_{name}", cable([ex, e1, mid, s1, s], 2.8), 0x1b1d20, f"Light lead {name}: 2-core 18 AWG, light head to its junction box socket"))
    # rear cap glands, world: the electronics scene's gland centres (sled frame x, y) mirrored, just outside the cap face (z -223.2)
    GZ = -223.2 - 16.0
    GL = {"MOTORS": (18.4, 18.4), "LIGHTS": (-18.4, 18.4), "BATTERY": (-18.4, -18.4), "TETHER": (18.4, -18.4)}
    def into_gland(name, pts, r, col, label):
        gx, gy = GL[name]; g = np.array([gx, gy, GZ])
        out.append((f"cab_{name.lower()}", cable(pts + [g + [0, 0, -40], g], r), col, label))
    for n, (x, r) in JB.EXITS.items():                             # 12-core and 4-core out of the box's back face
        e = pt(V.JB_M, (x, -JB.L / 2 - 2.0, JB.EXIT_Z)); bk = V.JB_M[:3, :3] @ np.array([0, -1.0, 0])
        gn = "MOTORS" if n == "12-CORE" else "LIGHTS"; gx, gy = GL[gn]
        pts = [e, e + bk * 18, np.array([e[0], 68.0, e[2] - 30]), np.array([(e[0] + gx) / 2, 66.0, -200.0]), np.array([gx, gy + 34, -258.0])]
        into_gland(gn, pts, 4.5 if n == "12-CORE" else 2.9, 0x5d6268,
                   "12-core motor cable: junction box to the hull's MOTORS gland" if n == "12-CORE" else "4-core lights cable: junction box to the hull's LIGHTS gland")
    M = inst("pod_cap")[0]                                         # battery lead: pod rear cap gland -> BATTERY gland
    pg, pn = pt(M, (0, 12.0, 22.0 + 14.0)), M[:3, :3] @ np.array([0, 0, 1.0])
    gx, gy = GL["BATTERY"]
    into_gland("BATTERY", [pg, pg + pn * 30, np.array([gx, gy - 30, pg[2] + pn[2] * 30 - 40]), np.array([gx, gy - 12, -262.0])], 4.0, 0x1b1c1f,
               "Battery lead: 12 AWG twin, battery pod to the hull's BATTERY gland")
    gx, gy = GL["TETHER"]; g = np.array([gx, gy, GZ])               # tether: trails off behind the ROV
    out.append(("cab_tether", cable([g, g + [0, 0, -30], g + [0, -18, -90], g + [0, -40, -230]], 3.1), 0x2b5fa8, "Cat6 tether to the topside (data only)"))
    return out

# ---------------------------------------------------------------- build
asm = json.load(open(ASM))
model = {"meshes": {}, "instances": []}
used = []
for it in asm["instances"]:
    if it["k"] not in used: used.append(it["k"])
for k in used:
    m = dict(asm["meshes"][k]); base = re.sub(r"_\d+$", "", k)
    m["label"] = NAMES.get(k, NAMES.get(base, re.sub(r"^\d{3}\s+", "", m["label"])))
    model["meshes"][k] = m
model["instances"] = [dict(i) for i in asm["instances"]]
for k, t, col, label in outside_cables(asm):
    model["meshes"][k] = enc(t, col, label)
    model["instances"].append({"k": k, "m": M16(np.eye(4)), "g": "wiring", "ex": [0, 0, 0]})

E = json.load(open(ELEC))["meshes"]
elec = {"meshes": {}, "instances": []}
for k, m in E.items():
    base = k.split("|")[0]
    if base in ELEC_SKIP: continue
    mm = {"v": m["v"], "i": m["i"], "color": hexcol(m["color"]), "label": ELEC_NAMES.get(base, base.replace("_", " ")),
          "rough": m.get("rough", 0.55), "metal": m.get("metal", 0), "opacity": m.get("opacity", 1)}
    key = "e_" + re.sub(r"[^A-Za-z0-9_+-]", "_", k)
    elec["meshes"][key] = mm
    elec["instances"].append({"k": key, "m": M16(SLED2WORLD), "g": "electronics", "ex": [0, 0, -200]})   # explodes with the sled

os.makedirs(OUT, exist_ok=True)
for name, d in (("viewer_model.json", model), ("viewer_electronics.json", elec)):
    p = os.path.join(OUT, name); json.dump(d, open(p, "w"), separators=(",", ":"))
    print(f"{name}: {len(d['meshes'])} meshes, {len(d['instances'])} instances, {os.path.getsize(p)/1e6:.1f} MB")
