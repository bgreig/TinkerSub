"""Realistic renders with render_real.html, plus optional callout labels drawn after the render.
usage: python3 shoot_real.py views.json outdir
A view may carry "labels": [[anchor_xyz, label_xy_fraction, text], ...]: a leader line from the projected 3D point to the
label at (fx, fy) of the canvas. The image is then cropped to the content (model + labels) with a margin."""
import sys, json, threading, http.server, functools, numpy as np
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

views, outdir = json.load(open(sys.argv[1])), sys.argv[2]
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8766), functools.partial(Q, directory="."))
threading.Thread(target=srv.serve_forever, daemon=True).start()
FONT = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
INK, LEAD = (34, 38, 43), (60, 66, 72)

def annotate(path, labels, anch, bg, margin, legend):
    """Numbered callouts: [anchor_xyz, [dx, dy], text] puts a numbered badge at anchor + (dx, dy) px with a leader to the
    anchor; the texts go to the legend list (set as text in the guide). [anchor_xyz, "C", text] writes a short tag on the part."""
    im = Image.open(path).convert("RGB"); d = ImageDraw.Draw(im)
    fb = ImageFont.truetype(FONT, 34); ft = ImageFont.truetype(FONT, 34)
    n = 0
    for i, (_, off, text) in enumerate(labels):
        ax, ay = anch[f"L{i}"]
        if off == "C":
            tw = d.textlength(text, font=ft); p = 9
            d.rounded_rectangle([ax - tw / 2 - p, ay - 21 - p * 0.5, ax + tw / 2 + p, ay + 21 + p * 0.5], radius=8, fill=(255, 255, 255), outline=LEAD, width=2)
            d.text((ax - tw / 2, ay - 21), text, font=ft, fill=INK); continue
        n += 1; legend.append(text)
        bx, by = ax + off[0], ay + off[1]
        d.line([(ax, ay), (bx, by)], fill=(255, 255, 255), width=7); d.line([(ax, ay), (bx, by)], fill=INK, width=3)
        d.ellipse([ax - 7, ay - 7, ax + 7, ay + 7], fill=(255, 255, 255), outline=INK, width=3)
        r = 27; d.ellipse([bx - r, by - r, bx + r, by + r], fill=(28, 92, 170), outline=(255, 255, 255), width=4)
        t = str(n); tw = d.textlength(t, font=fb); d.text((bx - tw / 2, by - 21), t, font=fb, fill=(255, 255, 255))
    im.save(path)

def crop(path, margin, bg):
    im = Image.open(path).convert("RGB"); a = np.asarray(im).astype(int)
    m = np.abs(a - np.array(bg)).sum(2) > 10
    ys, xs = np.where(m)
    im.crop((max(xs.min() - margin, 0), max(ys.min() - margin, 0), min(xs.max() + margin, im.width), min(ys.max() + margin, im.height))).save(path)

LEG = {}
with sync_playwright() as p:
    b = p.chromium.launch(args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
    for name, cfg in views.items():
        cfg = {"w": 2000, "h": 1400, **cfg}
        labels = cfg.pop("labels", [])
        cfg["anchors"] = {f"L{i}": l[0] for i, l in enumerate(labels)}
        pg = b.new_page(viewport={"width": cfg["w"], "height": cfg["h"]})
        pg.add_init_script(f"window.CFG = {json.dumps(cfg)};")
        pg.on("console", lambda m: print("  console:", m.text) if m.type == "error" else None)
        pg.goto("http://127.0.0.1:8766/render_real.html")
        pg.wait_for_function("window.DONE === true", timeout=600000)
        anch = pg.evaluate("window.ANCH")
        out = f"{outdir}/{name}.png"
        pg.locator("canvas").screenshot(path=out)
        bgc = cfg.get("bg", 0xe9edf0); bg = ((bgc >> 16) & 255, (bgc >> 8) & 255, bgc & 255)
        leg = []
        if labels: annotate(out, labels, anch, bg, cfg.get("margin", 30), leg)
        crop(out, cfg.get("margin", 30), bg)
        LEG[name] = leg
        print(name, Image.open(out).size, flush=True)
        pg.close()
    b.close()
srv.shutdown()
json.dump(LEG, open(f"{outdir}/legends.json", "w"), indent=1)
