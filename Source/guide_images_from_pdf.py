"""
Recover the guide images that are not shipped in the package (label close-ups L_*, Appendix B step renders f_ik_*,
insert-chart renders f_ins_*) from a previous guide PDF, so prep_guide_inputs.py can rebuild the guide after a text-only change.

How: build the guide once under a trace (missing images become grey placeholders, every drawImage call is recorded in
order), then pair the traced draw order with the old PDF's image placements, which come in the same order whatever the
pagination. Images already on disk are checked against the old PDF by pixel size; the recovered ones are written losslessly
(reportlab stores them as Flate RGB).
Usage (from the workspace folder, after prep_guide_inputs.py has copied everything else):
  python3 guide_images_from_pdf.py <old guide PDF> [render dir, default render/final]
"""
import sys, os, json, runpy, shutil, tempfile
from PIL import Image as PI
import reportlab.pdfgen.canvas as RC
import pymupdf

OLD_PDF = sys.argv[1]
RD = sys.argv[2] if len(sys.argv) > 2 else "render/final"
RECOVER = ("L_", "f_ik_", "f_ins_")
MISS, DRAWN = set(), []

_open, _di, _cp = PI.open, RC.Canvas.drawImage, shutil.copy
def placeholder(fp):
    if isinstance(fp, str) and fp.endswith(".png") and not os.path.exists(fp):
        MISS.add(fp); os.makedirs(os.path.dirname(fp) or ".", exist_ok=True); PI.new("RGB", (400, 300), (128, 128, 128)).save(fp)
def op(fp, *a, **k): placeholder(fp); return _open(fp, *a, **k)
def di(self, image, *a, **k): DRAWN.append(image if isinstance(image, str) else getattr(image, "fileName", "")); return _di(self, image, *a, **k)
def cp(src, dst, **k): placeholder(src); return _cp(src, dst, **k)
PI.open, RC.Canvas.drawImage, shutil.copy = op, di, cp

tmp = tempfile.mkdtemp()
for f in ("ROV_Frame.3mf", "ROV_Core.3mf", "ROV_Frame_plates.png", "ROV_Core_plates.png"):
    if os.path.exists(os.path.join("outdir", f)): _cp(os.path.join("outdir", f), tmp)
sys.path.insert(0, os.getcwd()); sys.argv = ["build_guide_final.py", RD, tmp]
runpy.run_path("build_guide_final.py", run_name="__main__")      # two passes: the second half of DRAWN is the final PDF
PI.open, RC.Canvas.drawImage, shutil.copy = _open, _di, _cp

doc = pymupdf.open(OLD_PDF)
old = [(i + 1, b["xref"], b["width"], b["height"]) for i, p in enumerate(doc) for b in p.get_image_info(xrefs=True)]
drawn = DRAWN[len(DRAWN) - len(old):]
assert len(DRAWN) == 2 * len(old), f"draw count {len(DRAWN)} vs old PDF {len(old)}: the guide's figure list changed, rebuild renders instead"
n, bad = 0, []
for fn, (pg, x, w, h) in zip(drawn, old):
    if os.path.basename(fn).startswith(RECOVER):
        pix = pymupdf.Pixmap(doc, x)
        if pix.alpha: pix = pymupdf.Pixmap(pix, 0)
        if pix.n > 3: pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
        pix.save(fn); n += 1; MISS.discard(fn)
    elif fn not in MISS and _open(fn).size != (w, h):
        bad.append((fn, pg))
if MISS: print("still missing (placeholders left in place):", sorted(MISS))
if bad: print("on disk but different from the old guide (fine if you changed them on purpose):", bad)
shutil.rmtree(tmp)
print("recovered", n, "images from", OLD_PDF)
