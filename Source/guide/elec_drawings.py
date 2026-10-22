"""
Electronics drawings for the guide, written as SVG and rendered to PNG in headless Chromium:
  elec_sch1.png   schematic sheet 1: battery, fuses, 12 V bus, battery sense, six IBT_2 drivers and motors
  elec_sch2.png   schematic sheet 2: 5 V supply, Pico, Pi Zero, camera, Ethernet, servos, LED drivers and lights
  elec_wiring.png wiring diagram: every wire by colour and gauge, from the hull glands through the rear bulkhead to the boards
Net names: +12V (after F1), +12V_AUX (after F2), +5V (U9A out: Pi, Pico), +5V_SERVO (U9B out: servos only), 3V3 (Pico 3V3 OUT), GND (star point on the GND Wago).
Pin numbers and nets match the electronics page (Pico pinout table) and the 3D wiring scene (elec_scene.py).
usage: python3 elec_drawings.py <out_dir>
"""
import sys, os
from playwright.sync_api import sync_playwright
OUT = sys.argv[1]
INK, MUTED, RED, ORG, BLU, PUR, GRN, YEL, WIRE = "#1d2125", "#5d6670", "#c62828", "#e07b00", "#1f5fbf", "#7a3fb8", "#2e8b46", "#b8860b", "#2a2f35"

class SVG:
    def __init__(s, w, h): s.w, s.h, s.e = w, h, []
    def add(s, x): s.e.append(x)
    def line(s, pts, col=WIRE, w=2.2, dash=None):
        d = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f} {y:.1f}" for i, (x, y) in enumerate(pts))
        s.add(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"{f" stroke-dasharray={chr(34)}{dash}{chr(34)}" if dash else ""}/>')
    def text(s, x, y, t, size=15, col=INK, anchor="start", weight=500, family="Inter", italic=False):
        t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        s.add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" font-weight="{weight}" fill="{col}" text-anchor="{anchor}"{" font-style=" + chr(34) + "italic" + chr(34) if italic else ""}>{t}</text>')
    def rect(s, x, y, w, h, fill="#ffffff", stroke=INK, sw=2.2, rx=4, dash=None):
        s.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{f" stroke-dasharray={chr(34)}{dash}{chr(34)}" if dash else ""}/>')
    def dot(s, x, y, col=WIRE, r=4.2): s.add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}"/>')
    def circle(s, x, y, r, col=INK, fill="#fff", w=2.2): s.add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{col}" stroke-width="{w}"/>')
    def svg(s):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{s.w}" height="{s.h}" viewBox="0 0 {s.w} {s.h}">'
                f'<rect width="{s.w}" height="{s.h}" fill="#ffffff"/>' + "".join(s.e) + "</svg>")

NETCOL = {"+12V": RED, "+12V_AUX": RED, "+5V": ORG, "3V3": "#b5462a", "GND": INK}
def flag(s, x, y, name, side="right", col=None):
    """Net label: a pointed tag starting at (x, y). Same name = same net."""
    col = col or NETCOL.get(name, BLU)
    w = 11 + 8.6 * len(name); h = 22
    if side == "right": pts = [(x, y), (x + 9, y - h / 2), (x + 9 + w, y - h / 2), (x + 9 + w, y + h / 2), (x + 9, y + h / 2)]; tx = x + 9 + w / 2
    else: pts = [(x, y), (x - 9, y - h / 2), (x - 9 - w, y - h / 2), (x - 9 - w, y + h / 2), (x - 9, y + h / 2)]; tx = x - 9 - w / 2
    s.add('<polygon points="' + " ".join(f"{a:.1f},{b:.1f}" for a, b in pts) + f'" fill="#ffffff" stroke="{col}" stroke-width="1.8"/>')
    s.text(tx, y + 5, name, 13.5, col, "middle", 600)
def gnd(s, x, y):
    s.line([(x, y), (x, y + 12)], INK); s.line([(x - 13, y + 12), (x + 13, y + 12)], INK, 2.4)
    s.line([(x - 8, y + 18), (x + 8, y + 18)], INK, 2.2); s.line([(x - 3.5, y + 24), (x + 3.5, y + 24)], INK, 2)
def resistor(s, x, y0, y1, label, val, col=WIRE, lx=14):
    m = (y0 + y1) / 2; h = 44
    s.line([(x, y0), (x, m - h / 2)], col)
    pts = [(x, m - h / 2)] + [(x + (8 if i % 2 == 0 else -8), m - h / 2 + (i + 0.5) * h / 6) for i in range(6)] + [(x, m + h / 2)]
    s.line(pts, col, 2); s.line([(x, m + h / 2), (x, y1)], col)
    s.text(x + lx, m - 2, label, 14, INK, "start", 600); s.text(x + lx, m + 15, val, 13, MUTED)
def capacitor(s, x, y0, y1, label, val, polar=True, col=WIRE):
    m = (y0 + y1) / 2
    s.line([(x, y0), (x, m - 5)], col); s.line([(x - 14, m - 5), (x + 14, m - 5)], col, 2.6)
    s.add(f'<path d="M{x - 14} {m + 9} Q{x} {m + 1} {x + 14} {m + 9}" fill="none" stroke="{col}" stroke-width="2.6"/>')
    s.line([(x, m + 5), (x, y1)], col)
    if polar: s.text(x - 20, m - 9, "+", 14, INK, "middle", 600)
    s.text(x + 20, m - 2, label, 14, INK, "start", 600); s.text(x + 20, m + 15, val, 13, MUTED)
def fuse_h(s, x0, x1, y, label, val, col=RED):
    m = (x0 + x1) / 2
    s.line([(x0, y), (m - 22, y)], col); s.rect(m - 22, y - 8, 44, 16, "#fff", col, 2, 3); s.line([(m - 22, y), (m + 22, y)], col, 1.4)
    s.line([(m + 22, y), (x1, y)], col)
    s.text(m, y - 16, f"{label}  {val}", 14, INK, "middle", 600)
def fuse_v(s, x, y0, y1, label, val, col=RED):
    m = (y0 + y1) / 2
    s.line([(x, y0), (x, m - 22)], col); s.rect(x - 8, m - 22, 16, 44, "#fff", col, 2, 3); s.line([(x, m - 22), (x, m + 22)], col, 1.4)
    s.line([(x, m + 22), (x, y1)], col); s.text(x + 16, m - 2, label, 14, INK, "start", 600); s.text(x + 16, m + 15, val, 13, MUTED)
def diode_h(s, x0, x1, y, label, col=ORG):
    m = (x0 + x1) / 2
    s.line([(x0, y), (m - 9, y)], col); s.add(f'<polygon points="{m - 9},{y - 10} {m - 9},{y + 10} {m + 8},{y}" fill="{col}"/>')
    s.line([(m + 9, y - 10), (m + 9, y + 10)], col, 2.6); s.line([(m + 9, y), (x1, y)], col)
    s.text(m, y - 16, label, 14, INK, "middle", 600)
def block(s, x, y, w, h, title, sub=None, left=(), right=(), top=(), bottom=(), pitch=30, fill="#f6f8fa"):
    """Component box; pins given as (name, offset) lists along each side. Returns dict of pin end points."""
    s.rect(x, y, w, h, fill, INK, 2.4, 6)
    s.text(x + w / 2, y + h / 2 - (6 if sub else -5), title, 17, INK, "middle", 700)
    if sub: s.text(x + w / 2, y + h / 2 + 15, sub, 13, MUTED, "middle")
    P = {}
    for n, off in left:
        yy = y + off; s.line([(x - 26, yy), (x, yy)], INK, 2); s.text(x + 7, yy + 5, n, 13, INK, "start", 600); P[n] = (x - 26, yy)
    for n, off in right:
        yy = y + off; s.line([(x + w, yy), (x + w + 26, yy)], INK, 2); s.text(x + w - 7, yy + 5, n, 13, INK, "end", 600); P[n] = (x + w + 26, yy)
    for n, off in top:
        xx = x + off; s.line([(xx, y - 26), (xx, y)], INK, 2); s.text(xx, y + 18, n, 13, INK, "middle", 600); P[n] = (xx, y - 26)
    for n, off in bottom:
        xx = x + off; s.line([(xx, y + h), (xx, y + h + 26)], INK, 2); s.text(xx, y + h - 9, n, 13, INK, "middle", 600); P[n] = (xx, y + h + 26)
    return P
def pinno(s, p, n, side):
    s.text(p[0] + (10 if side == "L" else -10), p[1] - 6, str(n), 11.5, MUTED, "start" if side == "L" else "end")
def title(s, t, sub):
    s.text(40, 46, t, 26, INK, "start", 700); s.text(40, 74, sub, 15, MUTED)

# ================================================================== sheet 1: power + motor drivers
s = SVG(1700, 1180)
title(s, "Schematic 1 of 2: power and motor drivers", "Battery, fuses, 12 V bus, battery sense, six IBT_2 drivers (U1-U6) and the six 1200 GPH motors (M1-M6)")
Y = 150
s.rect(30, 104, 300, 196, "#fbf6ec", "#c9b48a", 1.4, 8, "6 5"); s.text(42, 126, "BATTERY POD", 13, "#8a6d2f", "start", 700)
bx = 90
s.line([(bx, Y), (bx, 176)], RED)
for w, yy in ((34, 176), (20, 186), (34, 196), (20, 206)): s.line([(bx - w / 2, yy), (bx + w / 2, yy)], INK, 3 if w > 25 else 2.2)
s.line([(bx, 206), (bx, 240)], INK); gnd(s, bx, 240)
s.text(bx - 26, 172, "+", 16, INK, "middle", 700)
s.text(bx + 30, 192, "BT1", 16, INK, "start", 700); s.text(bx + 30, 210, "3S8P 18650", 13, MUTED); s.text(bx + 30, 226, "11.1-12.6 V, BMS 40 A", 13, MUTED)
fuse_h(s, bx, 300, Y, "F0", "35 A at pack +")
s.line([(330, 104), (330, 300)], "#8a6d2f", 1.4, "4 4")
s.text(338, 274, "12 AWG twin lead", 12, MUTED); s.text(338, 290, "BATTERY gland", 12, MUTED)
s.line([(300, Y), (420, Y)], RED, 3.2)
fuse_h(s, 420, 520, Y, "F1", "30 A in hull")
s.line([(520, Y), (1660, Y)], RED, 3.2); s.text(1660, Y - 12, "+12V  (Wago 221-415 bus)", 15, RED, "end", 700)
s.dot(560, Y, RED); resistor(s, 560, Y, 236, "R3", "33 k"); s.dot(560, 236); s.line([(560, 236), (600, 236)]); flag(s, 600, 236, "VBAT_SENSE")
resistor(s, 560, 236, 318, "R4", "10 k"); gnd(s, 560, 318)
s.text(612, 268, "12.6 V -> 2.93 V at GP26", 12.5, MUTED)
s.dot(820, Y, RED); fuse_v(s, 820, Y, 260, "F2", "3 A"); s.line([(820, 260), (820, 284)], RED); flag(s, 820, 284, "+12V_AUX", "right")
s.text(900, 330, "+12V_AUX feeds both 5 V converters (U9A, U9B) and both LED drivers (U7, U8): sheet 2", 13, MUTED)
s.line([(1180, 240), (1660, 240)], INK, 3.2); s.text(1660, 228, "GND  (Wago 221-415, star point)", 15, INK, "end", 700)
s.dot(1180, 240, INK); s.line([(1180, 240), (1180, 262)], INK); gnd(s, 1180, 262)
s.text(1200, 290, "Every ground symbol is this net. Heavy returns go to the GND Wago;", 12.5, MUTED)
s.text(1200, 306, "the GND wire in each logic bundle is a signal reference only.", 12.5, MUTED)
T = [("T1", "front port", 2, 3), ("T2", "front stbd", 4, 5), ("T3", "rear port", 6, 7), ("T4", "rear stbd", 8, 9), ("T5", "vert port", 10, 11), ("T6", "vert stbd", 12, 13)]
for i, (tn, where, ga, gb) in enumerate(T):
    x0 = 92 + i * 268; y0 = 430
    P = block(s, x0, y0, 128, 300, f"U{i + 1}", f"IBT_2 {tn}",
              left=[("B+", 34), ("B-", 74)], right=[("RPWM", 34), ("LPWM", 66), ("R_EN", 98), ("L_EN", 130), ("VCC", 162), ("GND", 194), ("R_IS", 236), ("L_IS", 268)],
              bottom=[("M+", 40), ("M-", 88)])
    bp, bm = P["B+"], P["B-"]
    s.line([bp, (bp[0] - 14, bp[1]), (bp[0] - 14, 392)], RED); s.dot(bp[0] - 14, 392, RED); s.text(bp[0] - 14, 380, "+12V", 13, RED, "middle", 700)
    s.line([bm, (bm[0] - 14, bm[1]), (bm[0] - 14, bm[1] + 18)], INK); gnd(s, bm[0] - 14, bm[1] + 18)
    for n, net in (("RPWM", f"GP{ga}"), ("LPWM", f"GP{gb}"), ("R_EN", "ARM"), ("L_EN", "ARM"), ("VCC", "3V3"), ("GND", "GND")):
        flag(s, P[n][0], P[n][1], net, "right")
    for n in ("R_IS", "L_IS"):
        px, py = P[n]; s.line([(px - 6, py - 6), (px + 6, py + 6)], MUTED, 2); s.line([(px - 6, py + 6), (px + 6, py - 6)], MUTED, 2)
    mp, mm = P["M+"], P["M-"]; cx = (mp[0] + mm[0]) / 2
    s.line([mp, (mp[0], mp[1] + 20), (cx - 20, mp[1] + 40)], PUR); s.line([mm, (mm[0], mm[1] + 20), (cx + 20, mm[1] + 40)], PUR)
    s.circle(cx, mp[1] + 56, 26, PUR); s.text(cx, mp[1] + 63, "M", 20, PUR, "middle", 700)
    s.text(cx, mp[1] + 104, f"M{i + 1}  {tn}", 15, INK, "middle", 700); s.text(cx, mp[1] + 122, where, 13, MUTED, "middle")
    s.text(cx, mp[1] + 138, f"MOTORS pair {i + 1}", 12, MUTED, "middle")
s.text(40, 1110, "IBT_2 boards: VCC from the Pico's 3V3 OUT (never 5 V or 12 V); R_EN and L_EN of all six on ARM (GP15, R1 10 k to GND, sheet 2); R_IS and L_IS not connected.", 13, MUTED)
s.text(40, 1130, "Each stacked pair (T1/T4, T2/T5, T3/T6) takes one 14 AWG feed from the bus to the top board, jumped to the bottom board with 16 AWG. F1 is the only path into +12V.", 13, MUTED)
s.text(40, 1150, "M+ / M-: the motor pair in the 12-core MOTORS cable. Spin direction is set in firmware (THRUSTER_DIR), not by swapping wires.", 13, MUTED)
open(f"{OUT}/elec_sch1.svg", "w").write(s.svg())

# ================================================================== sheet 2: control, 5 V, lights
s = SVG(1700, 1300)
title(s, "Schematic 2 of 2: 5 V supply, control, camera, servos and lights", "U9A / U9B 5 V converters, U10 Pico, U11 Pi Zero 2W, U12 ETH/USB HUB HAT, J1 camera, SV1-SV2 servos, U7-U8 LED drivers and the two lights")
s.text(40, 150, "+12V_AUX", 14, RED, "start", 700); s.line([(40, 170), (264, 170)], RED)
s.dot(110, 170, RED); capacitor(s, 110, 170, 250, "C1", "1000 uF 25 V"); gnd(s, 110, 250)
P = block(s, 290, 130, 150, 110, "U9A", "MP1584 5 V 1.8 A", left=[("VIN", 40)], right=[("VOUT", 40)], bottom=[("GND", 75)])
gnd(s, P["GND"][0], P["GND"][1])
vo = P["VOUT"]; s.line([vo, (640, vo[1])], ORG, 2.8); s.text(590, vo[1] - 10, "+5V (logic)", 15, ORG, "middle", 700)
s.dot(520, vo[1], ORG); s.line([(520, vo[1]), (520, 262)], ORG)
s.add(f'<polygon points="510,262 530,262 520,280" fill="{ORG}"/>'); s.line([(510, 281), (530, 281)], ORG, 2.6)
s.line([(520, 281), (520, 304)], ORG); flag(s, 520, 304, "VSYS", "right", ORG); s.text(538, 276, "D1  1N5817", 14, INK, "start", 600)
s.text(40, 340, "D1 lets the Pico run from USB on the bench without back-feeding the converter.", 12.5, MUTED)
s.dot(640, vo[1], ORG); s.line([(640, vo[1]), (640, 214)], ORG); flag(s, 640, 214, "+5V_PI", "right", ORG)
s.line([(720, 250), (720, 552)], ORG)
s.text(40, 440, "+12V_AUX", 14, RED, "start", 700); s.line([(40, 460), (264, 460)], RED)
QB = block(s, 290, 420, 150, 110, "U9B", "MP1584 5 V 1.8 A", left=[("VIN", 40)], right=[("VOUT", 40)], bottom=[("GND", 75)])
gnd(s, QB["GND"][0], QB["GND"][1])
s.line([QB["VOUT"], (720, QB["VOUT"][1])], ORG, 2.8); s.dot(720, QB["VOUT"][1], ORG); s.text(600, QB["VOUT"][1] - 10, "+5V_SERVO", 15, ORG, "middle", 700)
s.text(40, 600, "U9A feeds the Pi, HAT, camera and Pico; U9B feeds only the servos, so a stalled servo", 12.5, MUTED)
s.text(40, 617, "can't pull the Pi's 5 V down. Never join the two 5 V outputs; the grounds are common.", 12.5, MUTED)
s.dot(720, 250, ORG); s.line([(720, 250), (790, 250)], ORG); capacitor(s, 790, 250, 330, "C2", "470 uF 10 V"); gnd(s, 790, 330)
for k, (nm, pos, sig, yy) in enumerate((("SV1", "pan", "GP16", 430), ("SV2", "tilt", "GP17", 530))):
    Pq = block(s, 900, yy - 40, 160, 82, nm, f"MG90S {pos}", left=[("SIG", 18), ("+5V", 42), ("GND", 66)])
    flag(s, Pq["SIG"][0], Pq["SIG"][1], sig, "left")
    s.line([Pq["+5V"], (720, Pq["+5V"][1])], ORG); s.dot(720, Pq["+5V"][1], ORG)
    g = Pq["GND"]; s.line([g, (g[0] - 30, g[1]), (g[0] - 30, g[1] + 8)], INK); gnd(s, g[0] - 30, g[1] + 8)
s.text(900, 610, "Signal 3.3 V straight from the Pico (no level shifter);", 12.5, MUTED)
s.text(900, 627, "power from +5V_SERVO (U9B) only, C2 at the servo plugs.", 12.5, MUTED)
PL = [(1, "GP0"), (2, "GP1"), (3, "GND"), (4, "GP2"), (5, "GP3"), (6, "GP4"), (7, "GP5"), (8, "GND"), (9, "GP6"), (10, "GP7"),
      (11, "GP8"), (12, "GP9"), (13, "GND"), (14, "GP10"), (15, "GP11"), (16, "GP12"), (17, "GP13"), (18, "GND"), (19, "GP14"), (20, "GP15")]
PR = [(39, "VSYS"), (38, "GND"), (36, "3V3 OUT"), (31, "GP26"), (29, "GP22"), (27, "GP21"), (26, "GP20"), (22, "GP17"), (21, "GP16")]
x0, y0 = 300, 680
s.rect(x0, y0, 230, 22 + 20 * 26, "#eef6f0", INK, 2.4, 6); s.text(x0 + 115, y0 + 260, "U10", 17, INK, "middle", 700); s.text(x0 + 115, y0 + 281, "Raspberry Pi Pico", 13, MUTED, "middle")
NETL = {"GP0": "UART_TX", "GP1": "UART_RX", "GP14": "DIM", "GP15": "ARM"}
for i, (num, n) in enumerate(PL):
    yy = y0 + 22 + i * 26; p = (x0 - 26, yy)
    s.line([p, (x0, yy)], INK, 2); s.text(x0 + 7, yy + 5, n, 13, INK, "start", 600); s.text(p[0] + 4, p[1] - 5, str(num), 11, MUTED)
    if n == "GND": s.line([p, (p[0] - 14, p[1])], INK); s.text(p[0] - 18, p[1] + 5, "GND", 13, INK, "end", 700)
    else: flag(s, p[0], p[1], NETL.get(n, n), "left")
RES = {"GP22": "reserved: leak probe", "GP21": "reserved: I2C0 SCL", "GP20": "reserved: I2C0 SDA"}
for i, (num, n) in enumerate(PR):
    yy = y0 + 22 + i * 40; p = (x0 + 230 + 26, yy)
    s.line([(x0 + 230, yy), p], INK, 2); s.text(x0 + 223, yy + 5, n, 13, INK, "end", 600); s.text(p[0] - 4, p[1] - 5, str(num), 11, MUTED, "end")
    if n == "GND": s.line([p, (p[0] + 14, p[1])], INK); s.text(p[0] + 18, p[1] + 5, "GND", 13, INK, "start", 700)
    elif n == "VSYS": flag(s, p[0], p[1], "VSYS", "right", ORG)
    elif n == "3V3 OUT": flag(s, p[0], p[1], "3V3", "right")
    elif n == "GP26": flag(s, p[0], p[1], "VBAT_SENSE", "right")
    elif n in ("GP16", "GP17"): flag(s, p[0], p[1], n, "right")
    else: s.line([p, (p[0] + 12, p[1])], MUTED, 1.6); s.text(p[0] + 16, p[1] + 5, RES[n], 12.5, MUTED)
s.text(40, 1262, "GP2-GP13: RPWM / LPWM of U1-U6 (sheet 1). GND pins 3, 8, 13, 18: the signal-ground wire of each logic bundle.", 12.5, MUTED)
for net, r, xx in (("ARM", "R1", 900), ("DIM", "R2", 1010)):
    flag(s, xx, 720, net, "right"); s.line([(xx, 720), (xx, 736)]); resistor(s, xx, 736, 820, r, "10 k"); gnd(s, xx, 820)
s.text(880, 880, "R1 holds all six bridges off until firmware raises ARM.", 12.5, MUTED)
s.text(880, 897, "R2 holds the lights off at power-up (an open DIM is full on).", 12.5, MUTED)
P = block(s, 1180, 140, 220, 230, "U11", "Pi Zero 2W", left=[("5V", 40), ("GND", 80), ("TXD", 120), ("RXD", 160)], right=[("CSI", 50), ("USB OTG", 130)], fill="#eef6f0")
for n, num in (("5V", 2), ("GND", 6), ("TXD", 8), ("RXD", 10)): s.text(P[n][0] + 13, P[n][1] - 7, str(num), 11, MUTED, "middle")
flag(s, P["5V"][0], P["5V"][1], "+5V_PI", "left", ORG)
s.line([P["GND"], (P["GND"][0] - 14, P["GND"][1])], INK); s.text(P["GND"][0] - 18, P["GND"][1] + 5, "GND", 13, INK, "end", 700)
flag(s, P["TXD"][0], P["TXD"][1], "UART_RX", "left"); flag(s, P["RXD"][0], P["RXD"][1], "UART_TX", "left")
s.text(1180, 400, "Pi TXD (GPIO14, pin 8) -> Pico GP1 RX;  Pi RXD (GPIO15, pin 10) <- Pico GP0 TX", 12.5, MUTED)
c = P["CSI"]; s.line([c, (c[0] + 40, c[1])], GRN, 3)
s.rect(c[0] + 40, c[1] - 30, 150, 60, "#f6f8fa", INK, 2.4, 6); s.text(c[0] + 115, c[1] - 4, "J1 camera", 16, INK, "middle", 700); s.text(c[0] + 115, c[1] + 15, "22-pin ribbon", 12.5, MUTED, "middle")
u = P["USB OTG"]; s.line([u, (u[0] + 40, u[1])], BLU, 3)
s.rect(u[0] + 40, u[1] - 30, 150, 60, "#f6f8fa", INK, 2.4, 6); s.text(u[0] + 115, u[1] - 4, "U12", 16, INK, "middle", 700); s.text(u[0] + 115, u[1] + 15, "ETH/USB HUB HAT", 12.5, MUTED, "middle")
s.line([(u[0] + 115, u[1] + 30), (u[0] + 115, u[1] + 80)], "#2f6fd1", 3); s.text(u[0] + 105, u[1] + 72, "Cat6 tether", 13, INK, "end", 600)
s.text(u[0] + 105, u[1] + 88, "TETHER gland", 12, MUTED, "end")
for k, (uu, led, y) in enumerate((("U7", "D2  LED 1", 1000), ("U8", "D3  LED 2", 1130))):
    P = block(s, 1180, y - 60, 170, 120, uu, "LDD-700HW", left=[("+Vin", 22), ("-Vin", 54), ("DIM", 92)], right=[("+Vo", 36), ("-Vo", 86)])
    s.line([P["+Vin"], (P["+Vin"][0] - 30, P["+Vin"][1])], RED); s.text(P["+Vin"][0] - 34, P["+Vin"][1] + 5, "+12V_AUX", 13, RED, "end", 700)
    s.line([P["-Vin"], (P["-Vin"][0] - 30, P["-Vin"][1])], INK); s.text(P["-Vin"][0] - 34, P["-Vin"][1] + 5, "GND", 13, INK, "end", 700)
    flag(s, P["DIM"][0], P["DIM"][1], "DIM", "left")
    vp, vm = P["+Vo"], P["-Vo"]; lx = vp[0] + 70
    s.line([vp, (lx, vp[1]), (lx, vp[1] + 12)], YEL); s.line([vm, (lx, vm[1]), (lx, vm[1] - 12)], YEL)
    s.add(f'<polygon points="{lx - 12},{vp[1] + 12} {lx + 12},{vp[1] + 12} {lx},{vm[1] - 12}" fill="{YEL}"/>'); s.line([(lx - 12, vm[1] - 12), (lx + 12, vm[1] - 12)], YEL, 2.6)
    s.text(lx + 22, (vp[1] + vm[1]) / 2 - 2, led, 15, INK, "start", 700); s.text(lx + 22, (vp[1] + vm[1]) / 2 + 16, "XHP50.2 6 V", 12.5, MUTED)
s.text(1180, 1215, "Each driver's +Vo / -Vo is its own pair in the 4-core LIGHTS cable.", 12.5, MUTED)
s.text(1180, 1232, "Never join -Vo to GND, -Vin or the other driver's -Vo.", 12.5, MUTED)
s.text(40, 1284, "Nets with the same name are connected. 3V3 = Pico 3V3 OUT (pin 36) to VCC of all six IBT_2. No Pico pin ever touches 12 V.", 12.5, MUTED)
open(f"{OUT}/elec_sch2.svg", "w").write(s.svg())

# ================================================================== wiring diagram (harness lanes)
s = SVG(1800, 1180)
title(s, "Wiring diagram: every wire, harness by harness", "Glands on the left, the rear bulkhead (215) in the middle, the deck (214) on the right with each top board drawn over its bottom partner. Numbers = wire list.")
s.rect(28, 100, 182, 1050, "#f4f5f6", "#c3c8cd", 1.2, 8); s.text(42, 124, "REAR CAP", 13, MUTED, "start", 700)
s.rect(222, 100, 386, 1050, "#fbf3ef", "#e1c4b8", 1.2, 8); s.text(236, 124, "REAR BAY + BULKHEAD 215", 13, "#a0563a", "start", 700)
s.rect(620, 100, 1152, 1050, "#f2f5f9", "#c3cfdf", 1.2, 8); s.text(634, 124, "DECK 214 (top face above the line, bottom face below)", 13, "#3d5f97", "start", 700)
s.line([(630, 560), (1762, 560)], "#9fb0c8", 1.6, "8 6"); s.text(1756, 552, "top face", 12, "#3d5f97", "end", 600); s.text(1756, 578, "bottom face", 12, "#3d5f97", "end", 600)
def box(x, y, w, h, t, sub=None, fill="#ffffff"):
    s.rect(x, y, w, h, fill, INK, 2, 6); s.text(x + w / 2, y + (h / 2 + 5 if not sub else h / 2 - 4), t, 15, INK, "middle", 700)
    if sub: s.text(x + w / 2, y + h / 2 + 14, sub, 11.5, MUTED, "middle")
def gl(y, n, sub):
    s.rect(46, y - 28, 130, 56, "#ffffff", INK, 2, 28); s.text(111, y - 2, n, 14.5, INK, "middle", 700); s.text(111, y + 15, sub, 11, MUTED, "middle")
def num(x, y, n, col=INK):
    s.circle(x, y, 11, col, "#ffffff", 1.6); s.text(x, y + 4.5, str(n), 11.5, col, "middle", 700)
def lab(x, y, t, col=INK, a="start"): s.text(x, y, t, 12, col, a, 600)
gl(170, "TETHER", "M12, Cat6"); gl(230, "MOTORS", "M16, 12-core"); gl(330, "BATTERY", "M16, 12 AWG"); gl(880, "LIGHTS", "M12, 4-core")
box(250, 300, 70, 34, "F1 30 A") ; s.rect(250, 300, 70, 34, "none", RED, 2.2, 4)
box(360, 360, 120, 150, "+12V", "Wago 221-415"); box(360, 560, 120, 150, "GND", "Wago 221-415")
box(500, 740, 90, 34, "F2 3 A"); s.rect(500, 740, 90, 34, "none", RED, 2.2, 4)
box(320, 820, 150, 100, "LDD 1", "LDD-700HW"); box(320, 960, 150, 100, "LDD 2", "LDD-700HW")
COLS = [("T3", "T6", 660), ("T2", "T5", 900), ("T1", "T4", 1140)]
for t, b, x in COLS:
    box(x, 380, 180, 120, f"IBT_2 {t}", "B+ B- M+ M- | logic hdr", "#fbecea"); box(x, 620, 180, 120, f"IBT_2 {b}", "B+ B- M+ M- | logic hdr", "#fbecea")
box(1420, 380, 200, 120, "Pi Zero 2W", "pins 2, 6, 8, 10 | CSI", "#eef6f0"); box(1440, 220, 160, 70, "ETH/USB HAT", "on the Pi, RJ45", "#f4f4f4")
box(1420, 620, 200, 120, "Pico", "pins 1-20 stbd row", "#eef6f0"); box(1450, 800, 140, 70, "U9A + U9B", "2 x MP1584, top", "#f4f4f4")
box(1650, 620, 100, 120, "Servos", "pan, tilt", "#f4f4f4")
# W1/W2 battery
s.line([(176, 322), (250, 322)], RED, 4.6); s.line([(320, 317), (340, 317), (340, 380), (360, 380)], RED, 4.6); num(214, 308, 1, RED)
s.line([(176, 342), (230, 342), (230, 590), (360, 590)], INK, 4.6); num(230, 470, 2)
s.text(111, 378, "12 AWG twin lead", 11.5, MUTED, "middle")
# W3-W8 14 AWG pair feeds, W9-W14 16 AWG jumpers
for i, (t, b, x) in enumerate(COLS):
    yr, yb = 330 - i * 26, 342 - i * 26
    s.line([(480, 400 + i * 14), (520 + i * 10, 400 + i * 14), (520 + i * 10, yr), (x + 16, yr), (x + 16, 380)], RED, 3.4)
    s.line([(480, 600 + i * 14), (565 + i * 10, 600 + i * 14), (565 + i * 10, yb), (x + 30, yb), (x + 30, 380)], INK, 3.4)
    num(x + 52, yr - 2, 3 + 2 * i, RED); num(x + 78, yb + 2, 4 + 2 * i)
    s.line([(x + 16, 500), (x + 16, 620)], RED, 2.6, "7 4"); s.line([(x + 30, 500), (x + 30, 620)], INK, 2.6, "7 4")
    num(x + 52, 540, 9 + i, RED)
# W15 motors: 12-core to a breakout, pairs to every board
s.line([(176, 232), (330, 232)], "#7d8389", 8)
s.circle(338, 232, 9, "#111", "#111")
for i, (t, b, x) in enumerate(COLS):
    s.line([(346, 226 - i * 6), (x + 150, 226 - i * 6), (x + 150, 380)], PUR, 2.4)
    s.line([(346, 238 + i * 6), (612, 238 + i * 6), (612, 790 - i * 10), (x + 150, 790 - i * 10), (x + 150, 740)], PUR, 2.4)
num(300, 214, 12, PUR)
# W16-W18 aux: +12V wago -> F2 -> LDDs + buck; GND -> LDDs + buck
s.line([(480, 480), (495, 480), (495, 757), (500, 757)], RED, 2); num(495, 640, 13, RED)
s.line([(590, 757), (600, 757), (600, 842), (470, 842)], RED, 2); s.line([(600, 842), (600, 982), (470, 982)], RED, 2)
s.line([(600, 757), (604, 757), (604, 1100), (1520, 1100), (1520, 870)], RED, 2); num(900, 1100, 14, RED)
s.line([(480, 690), (488, 690), (488, 862), (470, 862)], INK, 2); s.line([(488, 862), (488, 1002), (470, 1002)], INK, 2)
s.line([(488, 1002), (488, 1116), (1540, 1116), (1540, 870)], INK, 2); num(960, 1116, 15)
# W19 lights: two separate pairs
s.line([(176, 872), (250, 872), (250, 846), (320, 846)], "#9aa1a8", 2.6); s.line([(176, 880), (258, 880), (258, 870), (320, 870)], BLU, 2.6)
s.line([(176, 888), (266, 888), (266, 986), (320, 986)], "#8b5a2b", 2.6); s.line([(176, 896), (274, 896), (274, 1010), (320, 1010)], "#6b7280", 2.6)
num(214, 850, 16); s.text(111, 926, "two separate pairs,", 11.5, MUTED, "middle"); s.text(111, 941, "never joined", 11.5, MUTED, "middle")
# W20 tether
s.line([(176, 170), (1520, 170), (1520, 220)], "#2f6fd1", 4.4); num(700, 170, 17, "#2f6fd1")
s.line([(1520, 290), (1520, 380)], INK, 3); num(1520, 335, 18); lab(1534, 340, "USB OTG")
# W22 logic bundles (Dupont x 6 per board)
for i, (t, b, x) in enumerate(COLS):
    s.line([(x + 170, 500), (x + 170, 524 - i * 6), (1392 + i * 6, 524 - i * 6), (1392 + i * 6, 650 + i * 8), (1420, 650 + i * 8)], "#d4a017", 2.4)
    s.line([(x + 170, 620), (x + 170, 600 - i * 6), (1374 + i * 6, 600 - i * 6), (1374 + i * 6, 690 + i * 8), (1420, 690 + i * 8)], "#d4a017", 2.4)
num(1250, 512, 19, "#a8800e")
# W23 Pi <-> Pico through the deck slot; W24 5 V
s.line([(1560, 500), (1560, 620)], BLU, 2.4); num(1560, 560, 20, BLU); 
s.line([(1590, 800), (1590, 760), (1606, 760), (1606, 500)], ORG, 2.6); num(1606, 600, 21, ORG); 
s.line([(1500, 800), (1500, 740)], ORG, 2.6); num(1500, 772, 22, ORG); 
s.line([(1620, 680), (1650, 680)], "#e07b00", 2.4); num(1635, 700, 23, "#b0600a")
lab(1700, 760, "GP16 / GP17 + 5V", "#b0600a", "middle"); lab(1700, 776, "to the pan-tilt", MUTED, "middle")
# W27 DIM
s.line([(1420, 725), (1400, 725), (1400, 1070), (480, 1070), (480, 1040), (470, 1040)], PUR, 1.8)
s.line([(480, 1040), (480, 900), (470, 900)], PUR, 1.8); num(1100, 1070, 24, PUR)
# legend
s.rect(690, 860, 690, 186, "#ffffff", "#c3c8cd", 1.2, 6); s.text(706, 884, "LEGEND", 12, MUTED, "start", 700)
LEG = [("#2f6fd1", 4.4, None, "Cat6 tether"), ("#7d8389", 7, None, "12-core motor cable"), (PUR, 2.4, None, "motor pair M+ / M-"),
       (RED, 4.6, None, "12 AWG battery lead"), (RED, 3.4, None, "14 AWG +12V feed"), (INK, 3.4, None, "14 AWG GND feed"),
       (RED, 2.6, "7 4", "16 AWG jumper (+ and -)"), (RED, 2, None, "20 AWG aux (red +, black -)"), ("#d4a017", 2.4, None, "logic bundle"),
       (BLU, 2.4, None, "UART + GND"), (ORG, 2.6, None, "+5V"), (PUR, 1.8, None, "DIM")]
for k, (c, w, d, t) in enumerate(LEG):
    cx, cy = 706 + (k // 4) * 225, 910 + (k % 4) * 34
    s.line([(cx, cy), (cx + 46, cy)], c, w, d); s.text(cx + 56, cy + 4.5, t, 12.5, INK, "start", 500)
open(f"{OUT}/elec_wiring.svg", "w").write(s.svg())

# wire list for the guide (same numbers as the drawing)
WIRES = [
 (1, "BATTERY gland", "F1 -> +12V Wago, slot 1", "12 AWG red (twin lead)"),
 (2, "BATTERY gland", "GND Wago, slot 1", "12 AWG black (twin lead)"),
 (3, "+12V Wago", "T3 B+ (top)", "14 AWG red"), (4, "GND Wago", "T3 B- (top)", "14 AWG black"),
 (5, "+12V Wago", "T2 B+ (top)", "14 AWG red"), (6, "GND Wago", "T2 B- (top)", "14 AWG black"),
 (7, "+12V Wago", "T1 B+ (top)", "14 AWG red"), (8, "GND Wago", "T1 B- (top)", "14 AWG black"),
 (9, "T3 B+ / B-", "T6 B+ / B- (below)", "16 AWG red + black"), (10, "T2 B+ / B-", "T5 B+ / B- (below)", "16 AWG red + black"),
 (11, "T1 B+ / B-", "T4 B+ / B- (below)", "16 AWG red + black"),
 (12, "MOTORS gland", "M+ / M- of T1-T6", "12-core, one pair per board"),
 (13, "+12V Wago, slot 5", "F2 (3 A)", "20 AWG red"),
 (14, "F2", "LDD 1 +Vin, LDD 2 +Vin, U9A + U9B IN+", "20 AWG red, spliced; C1 across the converter feed"),
 (15, "GND Wago, slot 5", "LDD 1 -Vin, LDD 2 -Vin, U9A + U9B IN-", "20 AWG black, spliced"),
 (16, "LIGHTS gland", "LDD 1 +Vo/-Vo, LDD 2 +Vo/-Vo", "4-core: two separate pairs"),
 (17, "TETHER gland", "HAT RJ45 (on the Pi)", "Cat6, inline coupler + 90-degree patch lead"),
 (18, "HAT hub input", "Pi Zero USB OTG", "micro-USB link board (comes with the HAT)"),
 (19, "IBT_2 header (each)", "Pico breakout terminals (see pinout)", "x 6: RPWM, LPWM, R_EN+L_EN, VCC, GND; Dupont at the IBT_2"),
 (20, "Pi pins 6, 8, 10 (HAT stacking pins)", "Pico terminals 3, 2, 1", "soldered at the Pi: GND, TXD->GP1, RXD<-GP0"),
 (21, "U9A OUT+", "Pi pin 2 (5 V, HAT stacking pin)", "via the 5 V splice behind the Pi"),
 (22, "5 V splice; U9A OUT-", "D1 -> Pico VSYS (39); Pico GND (38)", "red + 1N5817; black"),
 (23, "Pico GP16 / GP17; U9B OUT+ / OUT-", "Pan / tilt servo plugs", "servo leads; C2 470 uF at the plugs"),
 (24, "Pico GP14 (pin 19)", "LDD 1 DIM, LDD 2 DIM", "spliced; R2 10 k to GND at the terminal"),
]
import json
json.dump(WIRES, open(f"{OUT}/elec_wires.json", "w"))

# ------------------------------------------------------------------ render
with sync_playwright() as p:
    b = p.chromium.launch()
    for n in ("elec_sch1", "elec_sch2", "elec_wiring"):
        svg = open(f"{OUT}/{n}.svg").read()
        import re
        w, h = map(int, re.search(r'width="(\d+)" height="(\d+)"', svg).groups())
        pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=2)
        pg.set_content(f"<html><body style='margin:0'>{svg}</body></html>"); pg.wait_for_timeout(300)
        pg.screenshot(path=f"{OUT}/{n}.png", full_page=True); pg.close(); print(n, w, h)
    b.close()
