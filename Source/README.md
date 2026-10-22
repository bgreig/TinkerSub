# TinkerSub KB-1: source

Everything in the build package is generated from the Python in this folder: the printed parts (STL), the Bambu Studio projects (3MF), the side-plate templates and DXFs, the STEP files, the renders and the build guide. The CAD is code: change a number, re-run, and every file downstream follows.

Run everything from this folder. Tested with Python 3.13 on Linux; `pip install -r requirements.txt`.

## What makes what

| Step | Command | Writes |
|---|---|---|
| Thrusters | `python3 thruster.py` | `out/` housing, tail cone, props, nose cone, coupler gauge (101-105, 107) |
| Pylon clamp | `python3 pylon.py` | `out/pylon_clamp.stl` (106) |
| Pod parts, lights | `python3 export_v4.py` | `out/` pod flange and caps, light heads (301-303, 401-403) |
| Junction box | `python3 jbox.py` | `out/rov_junction_box.stl`, `rov_junction_lid.stl` (501, 503) |
| Frame, cowl, plates | `python3 export_v5.py` | `out_v5/` stations, brackets, belly pan, cowl, side plates (601-608, 701, 801-806) |
| Pod front cap | `python3 export_v6.py` | `out_v5/rov6_pod_endcap_3in_blank.stl` (303) |
| Pan-tilt | `python3 -c "import pantilt_fit as P; P.export('prep')"` | `prep/pantilt_*.stl` (216-219) |
| Assembly + fit check | `python3 rov_v6.py` | `rov_viewer/assembly_v6.json`; prints any interference |
| Final file names | `python3 parts_final.py vols.json` | `out_final/<name>.stl`, part volumes |
| Part numbers + labels | `python3 label_parts.py` | `out_lbl/<PN>_<name>.stl`: the files in `STL/` |
| Bambu projects | `PLATE_PLAN=plates_core.json PRINTED_MOD=parts_final PRINTED_ATTR=PRINTED_B python3 make_3mf.py ps.json - - - n3/ROV_Core.3mf` (and `plates_frame.json` / `PRINTED_A` for the Frame project, `plates_reprint.json` / `reprint_parts` / `PRINTED_R` for the reprint) | `n3/*.3mf` |
| Plate maps | `python3 plate_preview.py n3/ROV_Core.3mf n3/ROV_Core_plates.png` | plate map images |
| Side plates | `python3 plate_templates_final.py` | `out_final/` DXFs and template PDFs |
| Side-plate guide figures | `python3 plate_figs.py render/final/crop`, then `cd render && python3 shoot.py views_plate.json ../render/final/crop` (rename `plate.png` to `f_plate.png`) | template tile, sheet layout and finished-plate pictures |
| STEP | `python3 make_step.py asm rov_viewer/assembly_v6.json`, `python3 make_step.py parts` | `out_final/step/` |
| Heat-set insert map | `python3 insert_map.py out_lbl render ins.json` | insert scenes for the Appendix B chart |
| Renders | `scene_final.py`, `light_scene.py`, `elec_scene.py` and `insert_map.py` write the scenes; `cd render && python3 shoot.py views_final.json out` renders them | guide pictures (three.js in headless Chromium via Playwright) |
| Guide + package | `python3 build_guide_final.py render/final outdir` | the guide PDF and the whole package |

The guide build needs the rendered pictures. To rebuild the guide after a text-only change without re-rendering, `prep_guide_inputs.py` pulls the pictures and files back out of an existing build package, and `guide_images_from_pdf.py` recovers the few pictures that only live inside the old guide PDF (label close-ups, Appendix B):

```
python3 prep_guide_inputs.py <old package folder> <old guide PDF>
python3 guide_images_from_pdf.py <old guide PDF>
python3 build_guide_final.py render/final outdir
```

## Where to change things

| To change | Edit |
|---|---|
| Stations, brackets, belly pan, cowl, side plates, light aim | `rov_v5.py` |
| Thruster body, duct, prop, tail cone | `thruster.py` |
| Pylon clamp | `pylon.py` |
| Light heads | `lights.py` |
| Pod flanges and caps, sled bulkhead | `rov_parts.py` |
| Camera pan-tilt | `pantilt_fit.py` (its `check()` runs the fit check against the dome at every angle) |
| Junction box and lid | `jbox.py` |
| Part numbers, print notes, labels | `parts_final.py` |
| Plate layouts in the 3MFs | `plates_*.json`, print settings in `make_3mf.py` |
| Guide text | `build_guide_final.py` |

## Input files

Some parts were drawn in CAD rather than generated, and are read in as they are:

| Folder | Contents |
|---|---|
| `rov_project/` | Hull flanges 201 / 203, dome ring 204 and the original rear end cap (STL + STEP, from `rov_br_style_caps.py`), the sled front bulkhead 207 (`camera_mount/`), and the reference parts the assembly loads |
| `New_parts/` | Sled rails, deck, rear bulkhead and battery plate (212-215, 305), drawn as CAD solids in the sled frame |
| `src_parts/` | Sled rails with the front wire opening cut (`rail_notch.py`), as used in the assembly |
| `prep/` | The same parts in print orientation with their labels engraved, plus the pan-tilt parts |

## Checks

- `rov_v6.py` prints every interference between parts in the assembly. It should say `none`.
- `print_review.py out_lbl report.json` checks every printed part for bed fit, loose columns, floating islands, overhangs and thin walls.
- `insert_walls.py` checks the plastic around every heat-set insert hole.
- `pantilt_fit.check()` sweeps the camera through its pan and tilt range inside the dome.

## License

MIT (see `LICENSE`). The parts these scripts make are covered by the hardware license, CERN-OHL-S-2.0, at the top of the repository.
