TINKERSUB KB-1  BUILD PACKAGE
A printable, open-source ROV you can build and change.
(4" electronics hull, 3" battery pod, 1/2" HDPE side plates, yellow top cowl, 6x 1200 GPH vectored thrusters)

Name: TinkerSub is the project, KB-1 is this version, named for Kings Bay in Crystal River, Florida.

Start with TinkerSub_KB-1_Assembly_Guide.pdf: it takes you from ordering and printing through to the first dive.

Colours: the six top cowl sections are printed in YELLOW PETG; every other printed part is BLACK PETG.

Part numbers: every printed part has a three-digit part number debossed into it, and every file name starts with it
(601_rov_station_top_port.stl). The guide refers to parts by number. First digit = subsystem: 1 thrusters,
2 hull + sled + camera, 3 battery pod, 4 lights, 5 junction box + lid, 6 stations + brackets, 7 belly pan,
8 top cowl (yellow), 9 HDPE side plates (901 port, 902 starboard, marked from the template).
Sled 212-215 and battery plates 305 / 306 come from the electronics work (their labels are engraved too).
Camera pan-tilt 216-219 replaces the old fixed camera mount and fits the 100 mm dome (checked at every angle).
Electronics: guide section 9 (sled parts list, board layout, schematic, wiring diagram, wire list, pinout, bench test).
Firmware details: the ROV Electronics page and Documents/ROV/Firmware. Battery pack build: the ROV Battery Pack Build doc.

TinkerSub_KB-1_Frame.3mf   Bambu Studio project: station frames, junction deck, corner brackets, thruster pylons, belly pan (black),
                           top cowl (yellow, on its own 3 plates). Plate map:
                           Images/Diagrams/TinkerSub_KB-1_Frame_plates.png
TinkerSub_KB-1_Core.3mf    Bambu Studio project (all black): thrusters, hull flanges + caps, electronics sled, camera pan-tilt,
                           battery pod, lights, junction box + lid. Plate map:
                           Images/Diagrams/TinkerSub_KB-1_Core_plates.png
TinkerSub_KB-1_Reprint_2026-10-20.3mf   only the parts changed on 2026-10-20, for builders who printed earlier
BOM_printed_parts.csv   every printed part: project, file, qty, filament colour, print notes, grams
BOM_hardware.csv        everything to buy, including filament and the 24 x 24 in HDPE sheet
Pipe_cut_list.csv       4" hull 406 mm, 3" pod 300 mm
Wire_list.csv           every wire inside the hull, numbered as in the wiring diagram (guide section 9.4)
STL/                    1_Thrusters 2_Hull_and_sled 3_Battery_pod 4_Lights 5_Junction_boxes
                        6_Stations_and_brackets 7_Belly_pan 8_Top_cowl_YELLOW   (print orientation, mm)
CAD/                    side plates, 1/2" (12.7 mm) black HDPE, 478 x 300 mm each, both from one 24 x 24 in sheet
                          rov_side_plate_templates.pdf          1:1 paper templates. PRINT AT 100 % / "Actual size", check the 100 mm bar
                          rov_side_plate_templates_letter_portrait.pdf   the same templates laid out on Letter portrait
                          rov_side_plate_templates_fullsize_24x18.pdf    each plate whole on one 24 x 18 in sheet (print shop, 100 %)
                          rov_side_plate_port.dxf / _stbd.dxf   one plate per file, mm (for a CNC shop)
                          rov_side_plates_24x24_nest.dxf/.stl   both plates as laid out on the sheet
                          rov_side_plate_port.stl / _stbd.stl   the plates as 3D models
CAD/STEP/               for Fusion 360 / any CAD app (see README_Fusion.txt there)
                          TinkerSub_KB-1_assembly.step       whole ROV, named + coloured components in place
                          parts/*.step            each printed part with its labels
                          TinkerSub_KB-1_assembly_mesh.3mf   whole ROV as meshes (Insert Mesh)
Images/                 Renders, Assembly_steps, Parts, Diagrams, Electronics (schematic sheets, wiring diagram, sled renders)
Source/                 Python generators for the parts, frame and this package
