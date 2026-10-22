# Changelog

Changes to the TinkerSub KB-1 files. Part numbers are the three digits debossed on each printed part.

## 2026-10-22
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
