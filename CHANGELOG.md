# Changelog

Changes to the TinkerSub KB-1 files. Part numbers are the three digits debossed on each printed part.

## 2026-10-25
- **102 tail cone v2:** the compensator nipple sat under the spigot lip, 10 mm down, so the finger cot was very hard to fit and impossible to tie. The nipple now stands clear of the lip with its tip 2.5 mm below the rim: the cot pushes straight down over it, and a 5 x 1.5 mm O-ring rolled into a groove holds it (no tie). The vent runs down the nipple and out of the cone's side at 45 degrees, clear of the gland. Tail cones printed before this: reprint them (about 25 g each).
- Guide 4.1 **Everything to buy** (new page before the prices) and `Parts_to_buy.csv`: every bought part for one ROV with its total quantity and exact size. Screw, nut and insert counts come from `Source/assembly/fasteners.py`; the insert totals are checked against the Appendix B chart at build time. List in `Source/assembly/purchases.py`.
- **O-ring sizes corrected** (measured from the grooves; the original flange script had the dash numbers wrong): hull flange radial seals **AS568-238** (was -240), rear cap face **AS568-237** (was -239), dome face AS568-240 (unchanged); pod caps **72 x 2.5** (was 74 x 2.5: looser than its groove); light front ring **30 x 1.5** (was 31 x 1.5). Gland clamping ranges added (M16: 5-10 mm), and the tether must be slim Cat6 (OD 6.5 mm or less) to fit its M12 gland.
- Guide 7.3, the picture-by-picture thruster page and the shopping list updated. The compensator section figure is now drawn from the part geometry (`Source/guide/comp_fig.py`) instead of by hand; the unused, out-of-date `Images/Diagrams/compensator_cutaway.png` is removed.

## 2026-10-24
- `SECURITY.md`: what to report privately (firmware vulnerabilities and safety defects), how, what to expect, and the control system's security model (no authentication on the tether link: keep it a direct cable). Linked from the README, CONTRIBUTING and the new-issue page.
- New-issue page: the bug report is now a form for the firmware, topside program, video, build scripts and generated files (area, commit, steps, logs, setup), replacing GitHub's generic web-app template.

## 2026-10-23
Fastener audit: every screw hole in the assembled ROV is now followed through every part by `Source/checks/fastener_check.py`, which runs in every build and stops it on any problem. Every screw is listed in `Source/assembly/fasteners.py`, and the shopping list takes its screw rows from that table. What the audit found and fixed:
- **701 belly pan:** the hanger holes stopped 16 mm short of the bottom of the posts, so no screw could go in. Now straight through; **M4 x 50** up from below (was M4 x 30). Printed pans: drill each hole through from the top with a 4.5 mm bit.
- **601 / 602 station tops:** the arm-end M5 inserts were 0.75 mm below the side-plate holes. Moved to the plate-hole height. Printed tops: open the plates' four upper holes to 7 mm and use washers.
- **601 / 602 centre rib:** the M4 bolt had no room for its head or nut (the hull clamp ring is 3.2 mm below it). Now an M3 hole 1 mm higher; **M3 x 20 + nyloc, no washers** fits both the new and the old (4.5 mm) hole.
- **401 light rear body:** the M2.5 x 16 screws never reached the body (16.5 mm of ring and disc first). Pilots now 12 mm deep; **M2.5 x 25**. Printed bodies: drill the three 2.1 mm holes to 12 mm.
- **801-806 top cowl:** the section-seam holes were closed by the 45-degree flange ramps, the side seam bolts sat too close to the wall for a head, the outer roof holes broke out of the flange, and the centre-seam holes ignored the sloping nose and tail. All fixed; nothing printed yet should be reprinted from the old files.
- **Shopping list lengths** that didn't fit: plates to arms and brackets **M5 x 20** (was 25: bottoms out in the 10 mm inserts), pylons to brackets **M3 x 16** (was 12: 2.8 mm into the insert), vertical pylons **M3 x 30** (was 25: too short for the nut), dome ring **M3 x 12** (was 16: bottoms out), pod rear cap **M5 x 14** (was 16: bottoms out; the front cap stays M5 x 16), nose cones **M3 x 8** button (was 6).
- The model's sled rods are now 340 mm, as in the guide (they stopped short of the flanges' locating holes).
- Guide 7.1-7.2 and the picture-by-picture thruster page: set the coupler height with gauge 107 on the bare coupler, then fit the M5 stud and jam nut (with the stud in first, it hits the gauge's ceiling and sets the coupler too low). Nose cone screws on the picture page corrected to M3 x 8. The guide-text check now also catches a stale size at the end of a sentence and a joint size hiding behind a bought-part screw of the same size.

## 2026-10-22
- `Source/` reorganised by job (`geometry/`, `assembly/`, `outputs/`, `checks/`, `guide/`, `render/`, `inputs/`) with one entry point: `python3 Source/build.py all` rebuilds every part, project, template, figure, render and the guide, then lists what changed against the repository; `install` copies the changes in. See `Source/README.md`.
- 303 pod front cap: the generator wrote it plug-down; now plate-down, matching the STL that was already shipped (no reprint).
- Every guide picture now lives in `Images/` (new: `Labels/`, `Inserts/`, `Picture_by_picture/`), so the guide rebuilds from a checkout.
- Part pictures 216 (pan-tilt base) and 503 (junction lid) re-rendered from the current parts; the electronics renderer's missing three.js file added.
- Guide section 6: the template-tile, finished-plate and sheet-layout figures redrawn from the current plate CAD (they still showed the rear cowl-foot hole in its old place). `Source/guide/plate_figs.py` makes them.
- Battery pack build guide added as `docs/Battery_Pack_Build.md` (was a private link). Pack tie rods corrected to ~225 mm (were listed as ~215 mm, too short).
- License texts added: `LICENSE` (CERN-OHL-S-2.0), `LICENSES/` (CC BY-SA 4.0, MIT).
- `Source/` is complete: every module the generators import, the input parts, `requirements.txt` and `Source/README.md`. A clean checkout rebuilds every printed part to match `STL/`.
- 207 renamed from `207_m03r7-001-00a` to `207_sled_bulkhead_front` (same part).
- Shopping list: XHP50.2 LEDs must be the 6 V version; 5000-6500 K both fine.
- Contributing guide, issue templates and this changelog added.

## 2026-10-21
- Project named TinkerSub, first version KB-1.
- Light sleeves in the front cowl sections (805, 806) aimed 15 deg nose-down, so the beam covers the camera's whole tilt range. Reprint 805 / 806 only if you want the new aim.

## 2026-10-20
- Cowl v2 (801-806): side walls run down into the feet. v1 had a loose strip beside a slot that failed partway through printing. Reprint all six if yours have the slot.
- Rear cowl-foot hole on the side plates moved to 38 mm from the rear end (it missed the cowl). Plates cut earlier: add one 3.5 mm hole (guide section 6).
- Pressure parts print solid: 201, 202, 203, 301, 302, 303, 402. Parts printed earlier at normal infill: reprint, or seal with epoxy (guide section 5).
- 401 light rear body v2: 2.1 mm pilot holes for the M2.5 screws instead of inserts.
- 216 pan-tilt base v2: full-length ribs beside the pan servo.
- 218 pan-tilt cradle: tree supports on.
- Heat-set insert chart and picture-by-picture assembly pages added to the guide (Appendix B).
- `TinkerSub_KB-1_Reprint_2026-10-20.3mf` holds only the parts changed on this date.
