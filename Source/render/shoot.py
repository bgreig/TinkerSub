"""Render guide views with render.html (three.js) in headless Chromium, then crop to the model like the guide's crop/ images.
usage: python3 shoot.py views.json outdir"""
import sys, json, threading, http.server, functools, numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

views, outdir = json.load(open(sys.argv[1])), sys.argv[2]
H = functools.partial(http.server.SimpleHTTPRequestHandler, directory=".")
class Q(H.func):
    def log_message(self, *a): pass
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8765), functools.partial(Q, directory="."))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BG = np.array([223, 228, 232])

def crop(path, margin):
    im = Image.open(path).convert("RGB"); a = np.asarray(im).astype(int)
    m = np.abs(a - BG).sum(2) > 12
    ys, xs = np.where(m)
    x0, x1, y0, y1 = max(xs.min() - margin, 0), min(xs.max() + margin, im.width), max(ys.min() - margin, 0), min(ys.max() + margin, im.height)
    im.crop((x0, y0, x1, y1)).save(path)

with sync_playwright() as p:
    b = p.chromium.launch(args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
    for name, cfg in views.items():
        cfg = {"w": 1600, "h": 1200, **cfg}
        pg = b.new_page(viewport={"width": cfg["w"], "height": cfg["h"]})
        pg.add_init_script(f"window.CFG = {json.dumps(cfg)};")
        pg.on("console", lambda m: print("  console:", m.text) if m.type == "error" else None)
        pg.goto("http://127.0.0.1:8765/" + cfg.get("page", "render.html"))
        pg.wait_for_function("window.DONE === true", timeout=300000)
        out = f"{outdir}/{name}.png"
        pg.locator("canvas").screenshot(path=out)
        crop(out, cfg.get("margin", 24))
        print(name, Image.open(out).size, flush=True)
        pg.close()
    b.close()
srv.shutdown()
