"""
Side plate cutting files for 1/2" HDPE:
  out_final/rov_side_plate_port.dxf / _stbd.dxf   order-ready (mm, closed contours, outside face up)
  out_final/rov_side_plate_templates.pdf          1:1 paper templates, tiled on US Letter, with hole centres + drill sizes
"""
import math, ezdxf, numpy as np
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import mm
import rov_v5 as V

DRILL = {1.7: ("3.5 mm", "M3"), 2.2: ("4.5 mm", "M4"), 2.75: ("5.5 mm", "M5")}
def tag(side, z, y, k):
    """what bolts through this hole (part numbers as engraved on the printed parts)"""
    port = side == "port"
    if k == "arm":  return ("601" if port else "602") + " ARM" if y > -60 else ("604" if port else "605") + " ARM"
    if k == "brk":  return ("607 A" if port else "608 B") if z > 0 else ("608 B" if port else "607 A")
    if k == "pylon": return "T5 PYLON" if port else "T6 PYLON"
    if k == "cowl": return "COWL FOOT"
    return ""
def geom(side):
    """outline + windows as (h, v) polylines and holes as (h, v, r), seen from OUTSIDE. port: front on the left."""
    s = -1 if side == "port" else 1
    polys = [[(s*(-u)*-1 if False else (-u)*s, v) for u, v in p] for p in V._solid.to_polygons()]
    polys = [[(s*z, y) for z, y in [(-u, v) for u, v in p]] for p in V._solid.to_polygons()]
    holes = [(s*z, y, r, kind) for z, y, r, kind in V.HOLES if kind not in ("lap", "splice")]   # one-piece plate: no seam bolts
    return polys, holes

from manifold3d import CrossSection
def starters(polys):
    """one 10 mm jigsaw starter-hole point inside each window, 8 mm in from its edge"""
    big = max(polys, key=lambda p: abs(CrossSection([p]).area()))
    pts = []
    for p in polys:
        if p is big: continue
        cs = CrossSection([p if CrossSection([p]).area() > 0 else p[::-1]]).offset(-8, circular_segments=16)
        q = cs.to_polygons()
        if q: pts.append(tuple(max(q[0], key=lambda v: v[1] - 0.3*v[0])))
    return pts

def dxf(side, path):
    polys, holes = geom(side)
    d = ezdxf.new("R2010"); d.units = ezdxf.units.MM; m = d.modelspace()
    for p in polys: m.add_lwpolyline(p, close=True)
    for h, v, r, k in holes: m.add_circle((h, v), r)
    d.saveas(path)

def cover(c, W, H):
    M = 14*mm
    c.setFont("Helvetica-Bold", 16); c.drawString(M, H - M - 4*mm, "TinkerSub KB-1 side plates: cutting templates for one 24 x 24 in sheet of 1/2 in HDPE")
    c.setFont("Helvetica", 8.5 if W > H else 6.6)
    lines = [
     "1  Print every page at 100 % / Actual size, NOT 'Scale to fit'. Measure the 100 mm bar on a page: it must be exactly 100 mm (about 3 15/16 in).",
     "2  Each plate is several tiles (rows A, B, C from the top, columns 1, 2, 3 from the left). Trim a tile on its grey dashed line, overlap",
     "    the next tile, line up the red circles and tape the joints on the front.",
     "3  Lay both templates on the sheet as shown on the right, 5 mm apart (the sheet has only ~2 mm to spare at each edge: measure it first).",
     "    Spray adhesive (3M Super 77) or glue stick holds them; peel off afterwards.",
     "4  Centre-punch every crosshair, then drill: 3.5 mm (M3), 4.5 mm (M4), 5.5 mm (M5) as printed beside each hole.",
     "    Drill straight (drill press if you have one), slow speed, back the sheet with scrap wood.",
     "5  Drill the 10 mm blue starter hole in each window, then cut the windows with a jigsaw: fine-tooth blade, slow speed,",
     "    so the HDPE does not melt and re-weld behind the blade. Cut just outside the line.",
     "6  Cut the two plate outlines, then file / sand every edge smooth and break the sharp corners.",
     "7  The two plates are mirror images: PORT has the front of the ROV on the left, STARBOARD on the right (seen from outside).",
     "    Mark each plate's outside face before you peel the template off.",
     "Tools: jigsaw + fine blades, drill + 3.5 / 4.5 / 5.5 / 10 mm bits, centre punch, clamps, file or sandpaper.",
    ]
    y = H - M - 14*mm
    for ln in lines:
        c.drawString(M, y, ln); y -= 5.2*mm
    # sheet layout sketch (right half)
    if W > H: S = 609.6; sc = (W/2 - 2*M)/S; ox, oy = W/2 + M, M + 10*mm
    else: S = 609.6; sc = min(W - 2*M, y - 2*M - 20*mm)/S; ox, oy = (W - S*sc)/2, M + 10*mm      # portrait: sketch under the text
    c.setLineWidth(1); c.setStrokeColorRGB(0.4, 0.4, 0.4); c.rect(ox, oy, S*sc, S*sc)
    c.setFont("Helvetica", 7); c.drawString(ox, oy - 5*mm, "24 x 24 in sheet (609.6 mm), both plates outside face up")
    gap = 4.8
    for i, side in enumerate(("port", "stbd")):
        polys, holes = geom(side)
        pts = np.array([p for q in polys for p in q]); mn, mx = pts.min(0), pts.max(0); h = mx[1] - mn[1]
        off = np.array([(S - (mx[0] - mn[0]))/2 - mn[0], (S - 2*h - gap)/2 + i*(h + gap) - mn[1]])
        c.setStrokeColorRGB(0, 0, 0); c.setLineWidth(0.6)
        for poly in polys:
            pa = c.beginPath(); q = np.array(poly) + off; pa.moveTo(ox + q[0][0]*sc, oy + q[0][1]*sc)
            for v in q[1:]: pa.lineTo(ox + v[0]*sc, oy + v[1]*sc)
            pa.close(); c.drawPath(pa, stroke=1, fill=0)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(ox + S*sc/2, oy + (off[1] + mn[1] + h/2)*sc - 1*mm, "PORT (front left)" if side == "port" else "STARBOARD (front right)")
    c.showPage()

def pdf(path, size=None):
    size = size or landscape(letter)
    c = canvas.Canvas(path, pagesize=size)
    W, H = size
    MARG, OVER = 7*mm, 8*mm
    cover(c, W, H)
    for side in ("port", "stbd"):
        polys, holes = geom(side)
        allpts = np.array([pt for p in polys for pt in p])
        x0, y0 = allpts.min(0) - 8; x1, y1 = allpts.max(0) + 8
        tw, th = (W - 2*MARG)/mm - OVER/mm, (H - 2*MARG)/mm - 18 - OVER/mm   # usable tile step (mm)
        nx, ny = math.ceil((x1 - x0)/tw), math.ceil((y1 - y0)/th)
        for j in range(ny - 1, -1, -1):
            for i in range(nx):
                ox, oy = x0 + i*tw, y0 + j*th
                def P(x, y): return (MARG + (x - ox)*mm, MARG + 16*mm + (y - oy)*mm)
                c.saveState()
                p = c.beginPath(); p.rect(MARG, MARG + 16*mm, W - 2*MARG, H - 2*MARG - 16*mm); c.clipPath(p, stroke=0)
                c.setLineWidth(0.8); c.setStrokeColorRGB(0, 0, 0)
                for poly in polys:
                    pa = c.beginPath(); pa.moveTo(*P(*poly[0]))
                    for pt in poly[1:]: pa.lineTo(*P(*pt))
                    pa.close(); c.drawPath(pa, stroke=1, fill=0)
                c.setLineWidth(0.4)
                _done = []
                for h, v, r, k in holes:
                    X, Y = P(h, v); c.circle(X, Y, r*mm, stroke=1, fill=0)
                    c.line(X - 4*mm, Y, X + 4*mm, Y); c.line(X, Y - 4*mm, X, Y + 4*mm)
                    c.setFont("Helvetica", 5.5); c.drawString(X + 2.5*mm, Y + 1.5*mm, DRILL[r][0])
                    tg = tag(side, h * (-1 if side == "port" else 1), v, k)
                    if tg and any(t0 == tg and abs(h - h0) < 20 and abs(v - v0) < 20 for t0, h0, v0 in _done): tg = ""
                    if tg: _done.append((tg, h, v))
                    if tg: c.setFont("Helvetica-Bold", 6); c.drawString(X + 2.5*mm, Y - 3.2*mm, tg)
                c.setStrokeColorRGB(0.1, 0.35, 0.8); c.setLineWidth(0.5)
                for sx, sy in starters(polys):
                    X, Y = P(sx, sy); c.circle(X, Y, 5*mm); c.line(X - 2*mm, Y, X + 2*mm, Y); c.line(X, Y - 2*mm, X, Y + 2*mm)
                    c.setFont("Helvetica", 5.5); c.setFillColorRGB(0.1, 0.35, 0.8); c.drawString(X + 5.5*mm, Y - 1*mm, "10 mm starter hole"); c.setFillColorRGB(0, 0, 0)
                c.setStrokeColorRGB(0.6, 0.6, 0.6); c.setDash(2, 2)                 # overlap band + registration marks
                for gx in (ox + tw, ):
                    X, _ = P(gx, oy); c.line(X, MARG + 16*mm, X, H - MARG)
                for gy in (oy + th, ):
                    _, Y = P(ox, gy); c.line(MARG, Y, W - MARG, Y)
                c.setDash()
                for gx in (ox, ox + tw):
                    for gy in (oy, oy + th):
                        X, Y = P(gx, gy); c.setStrokeColorRGB(0.85, 0, 0); c.circle(X, Y, 3*mm); c.line(X - 5*mm, Y, X + 5*mm, Y); c.line(X, Y - 5*mm, X, Y + 5*mm)
                c.restoreState()
                # footer: label, scale bar
                c.setFont("Helvetica-Bold", 9)
                if W > H: c.drawString(MARG, MARG + 8*mm, f"TinkerSub KB-1 side plate {'901 PORT' if side == 'port' else '902 STARBOARD'}  -  tile {chr(65 + (ny - 1 - j))}{i + 1} of {nx*ny}  -  seen from OUTSIDE, front of the ROV to the {'left' if side == 'port' else 'right'}")
                else:
                    c.drawString(MARG, MARG + 11*mm, f"{'901 PORT' if side == 'port' else '902 STARBOARD'}  -  tile {chr(65 + (ny - 1 - j))}{i + 1} of {nx*ny}")
                    c.setFont("Helvetica", 7); c.drawString(MARG, MARG + 7.8*mm, f"seen from OUTSIDE, front of the ROV to the {'left' if side == 'port' else 'right'}")
                c.setFont("Helvetica", 7 if W > H else 6)
                if W > H: c.drawString(MARG, MARG + 3*mm, "Print at 100 % / Actual size (no scaling). Check the 100 mm bar. Trim one tile edge, overlap the next on the dashed line, match the red marks, tape.  Holes: 3.5 mm = M3, 4.5 mm = M4, 5.5 mm = M5.")
                else:
                    c.drawString(MARG, MARG + 4.5*mm, "Print at 100 % / Actual size (no scaling). Check the 100 mm bar. Trim one tile edge, overlap the next on the dashed line,")
                    c.drawString(MARG, MARG + 1.5*mm, "match the red marks, tape.  Holes: 3.5 mm = M3, 4.5 mm = M4, 5.5 mm = M5.")
                bx = W - MARG - 100*mm; by = MARG + 13.5*mm
                c.setLineWidth(1.2); c.line(bx, by, bx + 100*mm, by); c.line(bx, by - 1.5*mm, bx, by + 1.5*mm); c.line(bx + 100*mm, by - 1.5*mm, bx + 100*mm, by + 1.5*mm)
                c.setFont("Helvetica", 7); c.drawString(bx + 38*mm, by + 2*mm, "100 mm")
                c.showPage()
    c.save()

def pdf_full(path):
    """(2026-10-17) the same templates untiled: one plate per 24 x 18 in (ARCH C) page at 1:1, for a print shop or plotter"""
    W, H = 24*72.0, 18*72.0
    c = canvas.Canvas(path, pagesize=(W, H))
    for side in ("port", "stbd"):
        polys, holes = geom(side)
        pts = np.array([pt for p in polys for pt in p]); mn, mx = pts.min(0), pts.max(0)
        ox = (W/mm - (mx[0] - mn[0]))/2 - mn[0]; oy = (H/mm - (mx[1] - mn[1]))/2 - mn[1] + 10
        def P(x, y): return ((x + ox)*mm, (y + oy)*mm)
        c.setLineWidth(0.8)
        for poly in polys:
            pa = c.beginPath(); pa.moveTo(*P(*poly[0]))
            for pt in poly[1:]: pa.lineTo(*P(*pt))
            pa.close(); c.drawPath(pa, stroke=1, fill=0)
        c.setLineWidth(0.4); _done = []
        for h, v, r, k in holes:
            X, Y = P(h, v); c.circle(X, Y, r*mm, stroke=1, fill=0)
            c.line(X - 4*mm, Y, X + 4*mm, Y); c.line(X, Y - 4*mm, X, Y + 4*mm)
            c.setFont("Helvetica", 6); c.drawString(X + 2.5*mm, Y + 1.5*mm, DRILL[r][0])
            tg = tag(side, h * (-1 if side == "port" else 1), v, k)
            if tg and any(t0 == tg and abs(h - h0) < 20 and abs(v - v0) < 20 for t0, h0, v0 in _done): tg = ""
            if tg: _done.append((tg, h, v)); c.setFont("Helvetica-Bold", 6.5); c.drawString(X + 2.5*mm, Y - 3.4*mm, tg)
        c.setStrokeColorRGB(0.1, 0.35, 0.8); c.setLineWidth(0.5)
        for sx, sy in starters(polys):
            X, Y = P(sx, sy); c.circle(X, Y, 5*mm); c.line(X - 2*mm, Y, X + 2*mm, Y); c.line(X, Y - 2*mm, X, Y + 2*mm)
            c.setFont("Helvetica", 6); c.setFillColorRGB(0.1, 0.35, 0.8); c.drawString(X + 5.5*mm, Y - 1*mm, "10 mm starter hole"); c.setFillColorRGB(0, 0, 0)
        c.setStrokeColorRGB(0, 0, 0)
        M = 12*mm
        c.setFont("Helvetica-Bold", 14)
        c.drawString(M, H - M - 2*mm, f"TinkerSub KB-1 side plate {'901 PORT' if side == 'port' else '902 STARBOARD'}  -  full size, seen from OUTSIDE, front of the ROV to the {'left' if side == 'port' else 'right'}")
        c.setFont("Helvetica", 9)
        c.drawString(M, H - M - 8*mm, "Print on 24 x 18 in (ARCH C) paper at 100 % / Actual size, no scaling. Check both bars below before you cut: 200 mm and 8 in exactly.")
        c.drawString(M, H - M - 13*mm, f"Plate {mx[0] - mn[0]:.0f} x {mx[1] - mn[1]:.0f} mm, 1/2 in HDPE. Holes: 3.5 mm = M3, 4.5 mm = M4, 5.5 mm = M5. Centre-punch every crosshair; drill the blue starter holes before cutting the windows.")
        bx, by = M, M + 4*mm
        for L, lab, yy in ((200*mm, "200 mm", by + 8*mm), (8*72.0, "8 in", by)):
            c.setLineWidth(1.4); c.line(bx, yy, bx + L, yy); c.line(bx, yy - 2*mm, bx, yy + 2*mm); c.line(bx + L, yy - 2*mm, bx + L, yy + 2*mm)
            c.setFont("Helvetica", 8); c.drawString(bx + L + 3*mm, yy - 1*mm, lab)
        c.showPage()
    c.save()

def pdf_nest(path):
    """(2026-10-19) both plates on ONE 24 x 36 in (ARCH D) page at 1:1, nested exactly as on the 24 x 24 in HDPE sheet (4.8 mm apart),
    for a plotter / print shop. Fits a 24 in roll. Glue the whole print onto the sheet."""
    W, H = 24*72.0, 36*72.0
    c = canvas.Canvas(path, pagesize=(W, H))
    S, gap = 609.6, 4.8
    geo = {sd: geom(sd) for sd in ("port", "stbd")}
    hh = {}
    for sd, (polys, holes) in geo.items():
        pts = np.array([pt for p in polys for pt in p]); hh[sd] = (pts.min(0), pts.max(0))
    hp = hh["port"][1][1] - hh["port"][0][1]
    base = 60.0                                                   # mm from the page bottom to the bottom of the port plate
    for i, side in enumerate(("port", "stbd")):
        polys, holes = geo[side]; mn, mx = hh[side]
        ox = (W/mm - (mx[0] - mn[0]))/2 - mn[0]; oy = base + i*(hp + gap) - mn[1]
        def P(x, y): return ((x + ox)*mm, (y + oy)*mm)
        c.setStrokeColorRGB(0, 0, 0); c.setLineWidth(0.8)
        for poly in polys:
            pa = c.beginPath(); pa.moveTo(*P(*poly[0]))
            for pt in poly[1:]: pa.lineTo(*P(*pt))
            pa.close(); c.drawPath(pa, stroke=1, fill=0)
        c.setLineWidth(0.4); _done = []
        for h, v, r, k in holes:
            X, Y = P(h, v); c.circle(X, Y, r*mm, stroke=1, fill=0)
            c.line(X - 4*mm, Y, X + 4*mm, Y); c.line(X, Y - 4*mm, X, Y + 4*mm)
            c.setFont("Helvetica", 6); c.drawString(X + 2.5*mm, Y + 1.5*mm, DRILL[r][0])
            tg = tag(side, h * (-1 if side == "port" else 1), v, k)
            if tg and any(t0 == tg and abs(h - h0) < 20 and abs(v - v0) < 20 for t0, h0, v0 in _done): tg = ""
            if tg: _done.append((tg, h, v)); c.setFont("Helvetica-Bold", 6.5); c.drawString(X + 2.5*mm, Y - 3.4*mm, tg)
        c.setStrokeColorRGB(0.1, 0.35, 0.8); c.setLineWidth(0.5)
        for sx, sy in starters(polys):
            X, Y = P(sx, sy); c.circle(X, Y, 5*mm); c.line(X - 2*mm, Y, X + 2*mm, Y); c.line(X, Y - 2*mm, X, Y + 2*mm)
            c.setFont("Helvetica", 6); c.setFillColorRGB(0.1, 0.35, 0.8); c.drawString(X + 5.5*mm, Y - 1*mm, "10 mm starter hole"); c.setFillColorRGB(0, 0, 0)
        c.setFillColorRGB(0.55, 0.55, 0.55); c.setFont("Helvetica-Bold", 22)
        cx, cy = P((mn[0] + mx[0])/2, mn[1] + 0.80*(mx[1] - mn[1]))
        c.drawCentredString(cx, cy, "901 PORT  (front of ROV on the left)" if side == "port" else "902 STARBOARD  (front of ROV on the right)")
        c.setFillColorRGB(0, 0, 0)
    M = 15*mm; c.setStrokeColorRGB(0, 0, 0)
    top = (base + 2*hp + gap)*mm
    c.setFont("Helvetica-Bold", 16); c.drawString(M, H - M - 4*mm, "TinkerSub KB-1 side plates 901 + 902: full-size cutting template, both plates, 1/2 in HDPE")
    c.setFont("Helvetica", 10)
    lines = ["Print on 24 x 36 in (ARCH D) paper or a 24 in roll at 100 % / Actual size: no scaling, no 'fit to page'.",
             "Before cutting anything, check both bars at the bottom: exactly 200 mm and exactly 8 in. Each plate outline must measure 478 x 300 mm.",
             "Both plates are drawn outside face up, 4.8 mm apart, exactly as they sit on one 24 x 24 in HDPE sheet: trim the paper to about 2 mm",
             "outside the two plates and glue the whole thing on (3M Super 77 or glue stick), plates centred left to right, ~2 mm from the top and bottom edges.",
             "Centre-punch every crosshair. Drill 3.5 mm (M3), 4.5 mm (M4), 5.5 mm (M5) as printed. Drill each blue 10 mm starter hole, then jigsaw the windows",
             "and outlines just outside the line, slow speed, fine blade. Mark 901 / 902 and the hole tags on the outside faces before peeling the paper off."]
    y = H - M - 12*mm
    for ln in lines: c.drawString(M, y, ln); y -= 5.6*mm
    bx, by = M, 18*mm
    for L, lab, yy in ((200*mm, "200 mm", by + 10*mm), (8*72.0, "8 in", by)):
        c.setLineWidth(1.4); c.line(bx, yy, bx + L, yy); c.line(bx, yy - 2*mm, bx, yy + 2*mm); c.line(bx + L, yy - 2*mm, bx + L, yy + 2*mm)
        c.setFont("Helvetica", 9); c.drawString(bx + L + 3*mm, yy - 1*mm, lab)
    c.showPage(); c.save()
    return top/mm

if __name__ == "__main__":
    pdf_nest("out_final/rov_side_plates_both_24x36.pdf")
    for s in ("port", "stbd"): dxf(s, f"out_final/rov_side_plate_{s}.dxf")
    pdf("out_final/rov_side_plate_templates.pdf")
    pdf_full("out_final/rov_side_plate_templates_fullsize_24x18.pdf")
    pdf("out_final/rov_side_plate_templates_letter_portrait.pdf", letter)     # (2026-10-17) portrait tiles: prints right at the default portrait setting
    print("ok")

def nest(path):
    """both plates on one 24 x 24 in (609.6 mm) sheet, 4.8 mm apart, sheet outline on its own layer"""
    d = ezdxf.new("R2010"); d.units = ezdxf.units.MM; m = d.modelspace()
    d.layers.add("SHEET_24x24_DO_NOT_CUT", color=8)
    S = 609.6
    pass                                                  # no sheet outline: cutters treat the largest closed loop as the part
    gap = 4.8
    for i, side in enumerate(("port", "stbd")):
        polys, holes = geom(side)
        pts = np.array([p for q in polys for p in q]); mn, mx = pts.min(0), pts.max(0)
        off = np.array([(S - (mx[0] - mn[0]))/2 - mn[0], (S - 2*(mx[1] - mn[1]) - gap)/2 + i*((mx[1] - mn[1]) + gap) - mn[1]])
        for p in polys: m.add_lwpolyline([tuple(np.array(q) + off) for q in p], close=True)
        for h, v, r, k in holes: m.add_circle(tuple(np.array((h, v)) + off), r)
    d.saveas(path)
    return S - 2*(mx[1] - mn[1]) - gap

if __name__ == "__main__":
    print("spare height on the sheet (mm):", round(nest("out_final/rov_side_plates_24x24_nest.dxf"), 1))

# ---------------------------------------------------------------- (2026-10-19) corner-registered tiles: skid + front end on factory edges
def _xf(side, polys):
    """drawing transform for the factory-edge layout: port as is (front left, skid down); starboard turned 180 deg in plane
    (still outside face up: front left, skid UP), so both front ends sit on the same sheet edge."""
    pts = np.array([p for q in polys for p in q]); mn, mx = pts.min(0), pts.max(0); c = (mn + mx)/2
    if side == "port": return lambda h, v: (h, v)
    return lambda h, v: (2*c[0] - h, 2*c[1] - v)

def _factory_segs(side, polys):
    """outline segments lying on the skid (lowest y) or the front end (front = -z: left for port, right for stbd as seen from outside)"""
    big = max(polys, key=lambda p: np.ptp(np.array(p)[:, 0]) * np.ptp(np.array(p)[:, 1]))     # outline = largest bounding box (winding-independent)
    pts = np.array(big); mn, mx = pts.min(0), pts.max(0)
    fx = mn[0] if side == "port" else mx[0]
    segs = []
    for a, b in zip(big, big[1:] + big[:1]):
        if abs(a[1] - mn[1]) < 0.3 and abs(b[1] - mn[1]) < 0.3: segs.append((a, b, "skid"))
        if abs(a[0] - fx) < 0.3 and abs(b[0] - fx) < 0.3: segs.append((a, b, "front"))
    return segs

def pdf_edges(path):
    size = landscape(letter); W, H = size
    c = canvas.Canvas(path, pagesize=size)
    MARG, OVER = 7*mm, 8*mm
    GREEN = (0.1, 0.55, 0.45)
    # ---- cover
    M = 14*mm
    c.setFont("Helvetica-Bold", 15); c.drawString(M, H - M - 4*mm, "TinkerSub KB-1 side plates: templates for one 24 x 24 in HDPE sheet, using two factory edges per plate")
    c.setFont("Helvetica", 8.3)
    lines = [
     "Each plate's skid (bottom) edge and front end sit on factory edges of the sheet: those are the GREEN lines. Don't cut them.",
     "Check first: the sheet's two diagonals must match within about 2 mm (square corners). If not, use the standard templates instead.",
     "1  Print every page at 100 % / Actual size, NOT 'Scale to fit'. Measure the 100 mm bar on each page: exactly 100 mm.",
     "2  Each plate is 4 tiles, A1 A2 / B1 B2 (map in each tile's corner). Cut every tile on its black box line, all four sides. Butt the",
     "    edges together, A1 beside A2 and above B1, so the tick marks and the drawing run straight across the joint, and tape on the back.",
     "3  Trim the taped template EXACTLY on its two green lines, so the paper edge is the plate edge. The rest of the outline can stay untrimmed.",
     "4  Lay it on the sheet with its green edges flush against the sheet edges (layout on the right): PORT in the bottom-left corner,",
     "    STARBOARD in the top-left corner. Starboard is printed turned end for end (skid at the top): it is still outside face up.",
     "    Glue down (3M Super 77 or glue stick). Slide a straightedge along each green edge to check it is flush the whole way.",
     "5  Centre-punch every crosshair. Drill 3.5 mm (M3), 4.5 mm (M4), 5.5 mm (M5) as printed, slow, on a scrap-wood backer.",
     "6  Drill each blue 10 mm starter hole, jigsaw the windows, then the RED outline only: the two top edges (9.6 mm waste strip between",
     "    them: one cut just outside each line), the rear ends and the corners. Fine blade, slow speed, just outside the line.",
     "7  Sand the cut edges, break the corners, mark 901 PORT / 902 STBD and the hole tags on the outside faces, peel the paper off.",
     "A 131 x 610 mm offcut is left at the right-hand side of the sheet: keep it (crossbar, brackets).",
    ]
    y = H - M - 13*mm
    for ln in lines: c.drawString(M, y, ln); y -= 4.6*mm
    S = 609.6; sc = min((W - 2*M)*0.42, y - M - 8*mm)/S; ox, oy = W - M - S*sc, M + 6*mm
    c.setStrokeColorRGB(0.3, 0.3, 0.3); c.setLineWidth(1); c.rect(ox, oy, S*sc, S*sc)
    c.setFont("Helvetica", 7); c.setFillColorRGB(0, 0, 0); c.drawString(ox, oy - 4.5*mm, "24 x 24 in sheet (609.6 mm), outside faces up")
    for side in ("port", "stbd"):
        polys, holes = geom(side); f = _xf(side, polys)
        tp = [[f(*q) for q in p] for p in polys]
        pts = np.array([q for p in tp for q in p]); mn, mx = pts.min(0), pts.max(0)
        off = np.array([-mn[0], -mn[1] if side == "port" else S - mx[1]])
        c.setStrokeColorRGB(0, 0, 0); c.setLineWidth(0.5)
        for poly in tp:
            pa = c.beginPath(); q = np.array(poly) + off; pa.moveTo(ox + q[0][0]*sc, oy + q[0][1]*sc)
            for v in q[1:]: pa.lineTo(ox + v[0]*sc, oy + v[1]*sc)
            pa.close(); c.drawPath(pa, stroke=1, fill=0)
        c.setStrokeColorRGB(*GREEN); c.setLineWidth(2.2)
        for a, b, _ in _factory_segs(side, polys):
            A = np.array(f(*a)) + off; B = np.array(f(*b)) + off
            c.line(ox + A[0]*sc, oy + A[1]*sc, ox + B[0]*sc, oy + B[1]*sc)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(ox + (mx[0] - mn[0])/2*sc, oy + (off[1] + (mn[1] + mx[1])/2)*sc, "901 PORT (skid down)" if side == "port" else "902 STARBOARD (skid up)")
    c.setFont("Helvetica", 6.5); c.setFillColorRGB(*GREEN)
    c.drawString(ox, oy + S*sc + 1.5*mm, "green = factory edge, no cut   (front ends of both plates on the left edge)"); c.setFillColorRGB(0, 0, 0)
    c.showPage()
    # ---- tiles: butt joints. Each tile prints exactly its own cell of the plate, boxed by a solid CUT line; cut on the line,
    #      butt the cut edges together (ticks and the drawing continue across the joint) and tape on the back. No overlaps.
    for side in ("port", "stbd"):
        polys, holes = geom(side); f = _xf(side, polys)
        tp = [[f(*q) for q in p] for p in polys]
        allpts = np.array([pt for p in tp for pt in p])
        x0, y0 = allpts.min(0) - 8; x1, y1 = allpts.max(0) + 8
        aw, ah = (W - 2*MARG)/mm, (H - 2*MARG)/mm - 22               # usable drawing area (mm), footer below
        nx, ny = math.ceil((x1 - x0)/aw), math.ceil((y1 - y0)/ah)
        tw, th = (x1 - x0)/nx, (y1 - y0)/ny                          # equal cells, no overlap
        st = [f(*q) for q in starters(polys)]
        segs = [(f(*a), f(*b)) for a, b, _ in _factory_segs(side, polys)]
        for j in range(ny - 1, -1, -1):
            for i in range(nx):
                ox, oy = x0 + i*tw, y0 + j*th
                bx0 = MARG + (aw - tw)/2*mm; by0 = MARG + 22*mm + (ah - th)/2*mm      # cell centred in the drawing area
                def P(x, y): return (bx0 + (x - ox)*mm, by0 + (y - oy)*mm)
                name = f"{chr(65 + (ny - 1 - j))}{i + 1}"
                c.saveState()
                p = c.beginPath(); p.rect(bx0, by0, tw*mm, th*mm); c.clipPath(p, stroke=0)
                c.setLineWidth(0.8); c.setStrokeColorRGB(0.8, 0.1, 0.1)
                for poly in tp:
                    pa = c.beginPath(); pa.moveTo(*P(*poly[0]))
                    for pt in poly[1:]: pa.lineTo(*P(*pt))
                    pa.close(); c.drawPath(pa, stroke=1, fill=0)
                c.setStrokeColorRGB(*GREEN); c.setLineWidth(3.0)
                for a, b in segs: c.line(*P(*a), *P(*b))
                c.setFillColorRGB(*GREEN); c.setFont("Helvetica-Bold", 7)
                for a, b in segs:
                    (ax_, ay_), (bx_, by_) = P(*a), P(*b); mx_, my_ = (ax_ + bx_)/2, (ay_ + by_)/2
                    if abs(ay_ - by_) < 1: c.drawCentredString(mx_, my_ + (2.5*mm if side == "port" else -5*mm), "FACTORY EDGE (skid) - no cut")
                    else:
                        c.saveState(); c.translate(mx_ + 4.5*mm, my_); c.rotate(90); c.drawCentredString(0, 0, "FACTORY EDGE (front end) - no cut"); c.restoreState()
                c.setFillColorRGB(0, 0, 0); c.setStrokeColorRGB(0, 0, 0); c.setLineWidth(0.4)
                _done = []
                for h, v, r, k in holes:
                    X, Y = P(*f(h, v)); c.circle(X, Y, r*mm, stroke=1, fill=0)
                    c.line(X - 4*mm, Y, X + 4*mm, Y); c.line(X, Y - 4*mm, X, Y + 4*mm)
                    c.setFont("Helvetica", 5.5); c.drawString(X + 2.5*mm, Y + 1.5*mm, DRILL[r][0])
                    tg = tag(side, h * (-1 if side == "port" else 1), v, k)
                    if tg and any(t0 == tg and abs(h - h0) < 20 and abs(v - v0) < 20 for t0, h0, v0 in _done): tg = ""
                    if tg: _done.append((tg, h, v)); c.setFont("Helvetica-Bold", 6); c.drawString(X + 2.5*mm, Y - 3.2*mm, tg)
                c.setStrokeColorRGB(0.1, 0.35, 0.8); c.setLineWidth(0.5)
                for sx, sy in st:
                    X, Y = P(sx, sy); c.circle(X, Y, 5*mm); c.line(X - 2*mm, Y, X + 2*mm, Y); c.line(X, Y - 2*mm, X, Y + 2*mm)
                    c.setFont("Helvetica", 5.5); c.setFillColorRGB(0.1, 0.35, 0.8); c.drawString(X + 5.5*mm, Y - 1*mm, "10 mm starter hole"); c.setFillColorRGB(0, 0, 0)
                c.restoreState()
                # cut box + joint marks
                c.setStrokeColorRGB(0, 0, 0); c.setLineWidth(0.6); c.rect(bx0, by0, tw*mm, th*mm)
                c.setFont("Helvetica-Bold", 6.5); c.setFillColorRGB(0, 0, 0)
                nb = {"right": f"{chr(65 + (ny - 1 - j))}{i + 2}" if i < nx - 1 else None, "left": f"{chr(65 + (ny - 1 - j))}{i}" if i > 0 else None,
                      "top": f"{chr(65 + (ny - 2 - j))}{i + 1}" if j < ny - 1 else None, "bottom": f"{chr(65 + (ny - j))}{i + 1}" if j > 0 else None}
                c.setLineWidth(0.6)
                for edge, other in nb.items():
                    if not other: continue
                    if edge in ("left", "right"):
                        X = bx0 + (tw*mm if edge == "right" else 0); n = int(th // 30)
                        for k2 in range(1, n + 1):
                            Y = by0 + k2*th/(n + 1)*mm; c.line(X - 3*mm, Y, X + 3*mm, Y)
                        c.saveState(); c.translate(X + (-2.2*mm if edge == "right" else 3.6*mm), by0 + th/2*mm); c.rotate(90)
                        c.drawCentredString(0, 0, f"joins {other}"); c.restoreState()
                    else:
                        Y = by0 + (th*mm if edge == "top" else 0); n = int(tw // 30)
                        for k2 in range(1, n + 1):
                            X = bx0 + k2*tw/(n + 1)*mm; c.line(X, Y - 3*mm, X, Y + 3*mm)
                        c.drawCentredString(bx0 + tw/2*mm, Y + (-3.6*mm if edge == "top" else 1.6*mm), f"joins {other}")
                # scissors note on the box
                c.setFont("Helvetica", 6); c.setFillColorRGB(0.35, 0.35, 0.35)
                c.drawString(bx0, by0 + th*mm + 1.2*mm, "CUT ON THE BLACK BOX LINE (all four sides), then butt the edges together and tape on the back")
                c.setFillColorRGB(0, 0, 0)
                # mini map of the tile grid
                mw, mh = 16*mm, 16*mm*th*ny/(tw*nx); mx0, my0 = W - MARG - mw, MARG + 2*mm
                for jj in range(ny):
                    for ii in range(nx):
                        cw, ch = mw/nx, mh/ny; rx, ry = mx0 + ii*cw, my0 + (ny - 1 - jj)*ch
                        here = (jj == ny - 1 - j and ii == i)
                        c.setFillColorRGB(*((0.2, 0.2, 0.2) if here else (0.92, 0.92, 0.92))); c.rect(rx, ry, cw, ch, stroke=1, fill=1)
                        c.setFillColorRGB(*((1, 1, 1) if here else (0.3, 0.3, 0.3))); c.setFont("Helvetica-Bold", 5.5)
                        c.drawCentredString(rx + cw/2, ry + ch/2 - 2, f"{chr(65 + jj)}{ii + 1}")
                c.setFillColorRGB(0, 0, 0)
                c.setFont("Helvetica-Bold", 9)
                c.drawString(MARG, MARG + 12*mm, f"{'901 PORT (skid DOWN)' if side == 'port' else '902 STARBOARD (turned end for end: skid UP)'}  -  tile {name} of {nx*ny}  -  outside face up, front of the ROV on the LEFT")
                c.setFont("Helvetica", 6.6)
                c.drawString(MARG, MARG + 7.5*mm, "100 %, no scaling; check the 100 mm bar. Green = factory edge (no cut, trim paper flush later). Red = cut in the HDPE.  3.5 mm = M3, 4.5 = M4, 5.5 = M5.")
                c.drawString(MARG, MARG + 4*mm, "Paper: cut each tile on its black box, butt the edges so the ticks and lines meet, tape on the back.")
                bx = W - MARG - 22*mm - 100*mm; by = MARG + 15*mm
                c.setLineWidth(1.2); c.line(bx, by, bx + 100*mm, by); c.line(bx, by - 1.5*mm, bx, by + 1.5*mm); c.line(bx + 100*mm, by - 1.5*mm, bx + 100*mm, by + 1.5*mm)
                c.setFont("Helvetica", 7); c.drawString(bx + 38*mm, by + 2*mm, "100 mm")
                c.showPage()
    c.save()

if __name__ == "__main__":
    pdf_edges("out_final/rov_side_plate_templates_factory_edges.pdf")
