"""
Every screw joint in TinkerSub KB-1, and the shopping-list rows they come from.

This table is the single source for screw sizes:
  - checks/fastener_check.py finds every joint in the assembled model and checks it against JOINTS: the screw must fit
    (long enough to hold, short enough not to bottom out), there must be room for the head and the nut, the number of
    joints must match, and every joint in the model must be listed here (the build stops otherwise).
  - assembly/purchases.py counts every screw, nut, washer and insert to buy from JOINTS (the guide's shopping list).
  - The guide text may only name screw sizes that are joints here or OTHER_SPECS (also checked at build time).

To change a screw: change it here, rebuild (python3 Source/build.py all), and fix any guide text the build points at.
"""

# ---------------------------------------------------------------- joints
# parts: the part numbers the screw goes through, head side first ("a|b" = either, for port / starboard pairs).
#        Bought parts by name: hull (drilled at assembly), lt_disc (the light's aluminium disc).
# n:     joints of this kind in the model; screw: (size, length, head) with head SHCS / button / csk;
# thread: insert | tapped | self-tap | nut.
def J(name, parts, n, size, length, thread, head="SHCS"):
    return {"name": name, "parts": parts, "n": n, "size": size, "length": length, "thread": thread, "head": head}

JOINTS = [
    J("Nose cone to prop hub", ("105", "103/104"), 18, "M3", 8, "tapped", head="button"),
    J("Pylon pinch bolt", ("106",), 12, "M4", 30, "insert"),
    J("Side plate to station arm", ("901|902", "601|602|604|605"), 16, "M5", 20, "insert"),
    J("Side plate to corner bracket", ("901|902", "607|608"), 8, "M5", 20, "insert"),
    J("Station top to middle (hull pair)", ("601|602", "603"), 4, "M4", 30, "nut"),
    J("Station middle to bottom (pod pair)", ("603", "604|605"), 4, "M4", 20, "nut"),
    J("Station top halves, centre rib", ("601", "602"), 2, "M3", 20, "nut"),
    J("Corner pylon to bracket", ("106", "607|608"), 16, "M3", 16, "insert"),
    J("Vertical pylon through the plate", ("106", "901|902"), 8, "M3", 30, "nut"),
    J("Belly pan hanger", ("701", "604|605"), 4, "M4", 50, "insert"),
    J("Cowl centre seam", ("801|803|805", "802|804|806"), 6, "M3", 20, "nut"),
    J("Cowl section seam", ("801|802|803|804", "803|804|805|806"), 12, "M3", 20, "nut"),
    J("Cowl foot to side plate", ("901|902", "801|802|803|804|805|806"), 8, "M3", 20, "insert"),
    J("Junction deck to station rib", ("606", "601|602"), 4, "M3", 10, "insert"),
    J("Junction box to deck", ("501", "606"), 4, "M3", 8, "insert"),
    J("Junction box lid", ("503", "501"), 4, "M3", 8, "insert", head="csk"),
    J("Hull rear cap", ("202", "201"), 6, "M3", 16, "tapped"),
    J("Dome ring", ("204", "203"), 6, "M3", 12, "tapped"),
    J("Radial flange screw through the pipe", ("hull", "201|203"), 6, "M3", 10, "insert"),
    J("Pod rear cap", ("302", "301"), 6, "M5", 14, "insert"),
    J("Pod front cap", ("303", "301"), 6, "M5", 16, "insert"),
    J("Light head: ring + disc to body", ("402", "lt_disc", "401"), 6, "M2.5", 25, "self-tap"),
]
# extra thread length a screw may need where the stack holds something the model leaves out (washers, shims)
SHIM = {"Vertical pylon through the plate": 1.0}

# ---------------------------------------------------------------- holes that are not screw joints in the model
# (part, hole as the checker names it, reason). Mostly holes for bought parts the model doesn't contain.
NOT_JOINTS = [
    ("101", "M4 clearance", "wire / oil passage along the motor, not a screw hole"),
    ("102", "M3 clearance", "oil fill + bleed ports: 3.3 mm, tapped M4 for the set screws"),
    ("102", "M2.5 pilot", "compensator vent, 2.2 mm"),
    ("103/104", "counterbore", "prop drive: M5 set screw + nut in the hub"),
    ("105", "counterbore", "nose cone tip"),
    ("106", "M4 clearance", "pylon pinch bolt, other half (counted with the pinch joint)"),
    ("207", "M3 pilot", "front bulkhead: pan-tilt servo / camera screws (bought parts)"),
    ("207", "M4 clearance", "front bulkhead: counterbore of the same screw holes"),
    ("214", "M2.5 pilot", "Pi Zero standoffs (M2.5 x 8)"),
    ("214", "M3 pilot", "Pico breakout standoffs (M3 x 10)"),
    ("217", "M3 pilot", "servo horn screw"),
    ("218", "M2.5 pilot", "camera board screws (M2)"),
    ("305", "M4 clearance", "battery pack tie rods (M4 threaded rod + nuts)"),
    ("401", "M3 clearance", "potting fill / vent holes, 3 mm"),
    ("401", "M5 insert", "cable exit, 6.4 mm"),
    ("805", "M3 pilot", "light set screw, tapped M3 in one pass (M3 x 8 set screw)"),
    ("806", "M3 pilot", "light set screw, tapped M3 in one pass (M3 x 8 set screw)"),
    ("lt_disc", "M3 insert", "the light's aluminium disc: centre hole"),
]
# screw specs the guide text may name that are not joints in the model (bought-part screws, set screws, standoffs, rods)
OTHER_SPECS = {"M5 x 20 set screw", "M3 x 8 set screw", "M3 x 8 male-female", "M3 x 8 female-female", "M3 x 6 screws", "M2.5 x 8 standoffs",
               "M3 x 10 standoffs", "M2 x 6", "M2 x 8", "M10 x 1.0 x 12", "M4 x 4 set screw"}
