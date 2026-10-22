"""
STEP files for Fusion 360 / any CAD app.
  out_final/step/TinkerSub_KB-1_assembly.step   complete ROV: every part as a named, coloured component in place, grouped by
                                         subsystem (Z up, front of the ROV toward -Y, mm)
  out_final/step/parts/<stem>.step       every printed part on its own, in print orientation (same as the STLs)
Parts are converted from their meshes: flat faces are merged into single faces; curved faces stay faceted.
Parts over MAXTRI triangles are simplified first (marked _simplified).
"""
import os, sys, json, re, time
import numpy as np, trimesh
from step_export import mesh_to_solid
from OCP.gp import gp_Trsf
from OCP.TopLoc import TopLoc_Location
from OCP.TDocStd import TDocStd_Document
from OCP.XCAFApp import XCAFApp_Application
from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ColorGen
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.STEPCAFControl import STEPCAFControl_Writer
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
from OCP.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCP.Interface import Interface_Static
import parts_final as PF

OUTD = "out_final/step"; os.makedirs(OUTD + "/parts", exist_ok=True)
MAXTRI = int(os.environ.get("MAXTRI", 8000))
Interface_Static.SetCVal_s("write.step.unit", "MM"); Interface_Static.SetCVal_s("write.step.schema", "AP214IS")

def simplify(t, n):
    if len(t.faces) <= n: return t, False
    s = t.simplify_quadric_decimation(face_count=n)
    return (s if s.is_watertight else t), s.is_watertight

EDITABLE = ("st_", "brk_", "cowl_", "belly", "jdeck", "hdpe_", "cell_plate", "jbox", "pod_cap", "pt_base", "pt_yoke", "pt_cradle", "pt_lever")
def light(t, n):
    if len(t.faces) <= n: return t
    try: d = t.simplify_quadric_decimation(face_count=n, aggression=8)
    except Exception: d = t
    return d if len(d.faces) <= 2*n and d.is_watertight else t.convex_hull     # last resort: outer envelope
def name(lbl, s): TDataStd_Name.Set_s(lbl, TCollection_ExtendedString(s))
def rgb(c): return Quantity_Color(((c >> 16) & 255)/255, ((c >> 8) & 255)/255, (c & 255)/255, Quantity_TOC_RGB)

def write_part(stem, src):
    t = trimesh.load(f"{src}/{stem}.stl"); t, simp = simplify(t, MAXTRI)
    w = STEPControl_Writer(); w.Transfer(mesh_to_solid(t), STEPControl_AsIs)
    fn = f"{OUTD}/parts/{stem}{'_simplified' if simp else ''}.step"; w.Write(fn); return fn

def write_assembly(asm_json, path, keymap):
    import rov_v6 as V6
    d = json.load(open(asm_json))
    app = XCAFApp_Application.GetApplication_s(); doc = TDocStd_Document(TCollection_ExtendedString("MDTV-XCAF"))
    app.InitDocument(doc)
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main()); ct = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    root = st.NewShape(); name(root, "TinkerSub KB-1")
    GN = {"thrusters": "Thrusters", "frame": "Frame and side plates", "cowl": "Top cowl (yellow)", "hull": "Hull",
          "sled": "Electronics sled", "battery": "Battery pod", "lights": "Lights", "junction": "Junction boxes"}
    groups, parts = {}, {}
    Zup = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)   # y-up -> z-up, front to -Y
    for k, M, g, ex in V6.inst:
        m, col, label = V6.parts[k]
        if k not in parts:
            gm = m.to_mesh(); t = trimesh.Trimesh(gm.vert_properties[:, :3], gm.tri_verts)
            if not k.startswith(EDITABLE): t = light(t, 400)      # reference geometry only: keeps the file small
            lbl = st.AddShape(mesh_to_solid(t), False)
            nm = re.sub(r"\s*\((NEW|new|ROV Project)[^)]*\)", "", d["meshes"][k]["label"])
            if k in keymap:
                v = keymap[k]; pnum = PF.PN.get(v, PF.PN_CUT.get(v, ""))
                name(lbl, f"{pnum} {v} - {nm}".strip())
            else: name(lbl, nm)
            ct.SetColor(lbl, rgb(d["meshes"][k]["color"]), XCAFDoc_ColorGen)
            parts[k] = lbl; print("  part", k, len(t.faces), flush=True)
        if g not in groups:
            gl = st.NewShape(); name(gl, GN.get(g, g.capitalize())); groups[g] = gl
        P = Zup @ M; tr = gp_Trsf(); tr.SetValues(*[float(P[i, j]) for i in range(3) for j in range(4)])
        st.AddComponent(groups[g], parts[k], TopLoc_Location(tr))
    for g, gl in groups.items(): st.AddComponent(root, gl, TopLoc_Location(gp_Trsf()))
    st.UpdateAssemblies()
    w = STEPCAFControl_Writer(); w.SetNameMode(True); w.SetColorMode(True); w.Transfer(doc, STEPControl_AsIs); w.Write(path)

KEYMAP = {"st_top_port": "rov_station_top_port", "st_top_stbd": "rov_station_top_stbd", "st_mid": "rov_station_mid",
          "st_bot_port": "rov_station_bot_port", "st_bot_stbd": "rov_station_bot_stbd", "jdeck": "rov_junction_deck",
          "brk_corner_a_0": "rov_bracket_corner_a", "brk_corner_a_3": "rov_bracket_corner_a", "brk_corner_b_1": "rov_bracket_corner_b",
          "brk_corner_b_2": "rov_bracket_corner_b", "belly": "rov_belly_pan", "pylon": "pylon_clamp", "housing": "housing_no_foot",
          "tail": "tail_cone_comp", "hub": "prop_hub", "nose": "nose_cone", "cell_plate": "rov_cell_plate_8_v2",
          "pod_fl": "rov_pod_flange_3in", "pod_fl_front": "rov_pod_flange_3in", "pod_cap": "rov_pod_endcap_3in_rear",
          "pod_cap_front": "rov_pod_endcap_3in_front", "jbox": "rov_junction_box", "jlid": "rov_junction_lid",
          "lt_rear": "rov_light_rear_body", "lt_front": "rov_light_front_ring", "lt_spacer": "rov_light_spacer",
          "cap_rear": "rov_endcap_rear_5hole", "fl_rear": "br_flange_rear", "fl_front": "br_flange_front_dome",
          "dome_ring": "dome_retaining_ring", "tray": "ETRAY4-ROV-TRAY-R2", "bh_rear": "rov_sled_bulkhead_rear",
          "hdpe_port": "rov_side_plate_port", "sl_rail_p": "sled_rail_port", "sl_rail_s": "sled_rail_stbd", "sl_deck": "sled_deck", "sl_bh": "sled_bulkhead_rear_v2", "pt_base": "pantilt_base", "pt_yoke": "pantilt_yoke", "pt_cradle": "pantilt_cradle", "pt_lever": "pantilt_lever", "hdpe_stbd": "rov_side_plate_stbd",
          **{f"cowl_{a}_{b}": f"rov_cowl_{a}_{b}" for a in ("front", "mid", "rear") for b in ("port", "stbd")}}

if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    t0 = time.time()
    if what in ("all", "asm"):
        write_assembly(sys.argv[2] if len(sys.argv) > 2 else "rov_viewer_v6/assembly.json", f"{OUTD}/TinkerSub_KB-1_assembly.step", KEYMAP)
        print("assembly", round(time.time() - t0), "s", flush=True)
    if what in ("all", "parts"):
        for sec, stem, src, *_ in PF.PRINTED:
            if len(trimesh.load(f"{src}/{stem}.stl").faces) > MAXTRI:     # curved / threaded: use the STL + Fusion Convert Mesh
                print("  skip", stem, flush=True); continue
            print(" ", write_part(stem, src), round(time.time() - t0), "s", flush=True)
        import shutil
        for s, n in (("port", "901"), ("stbd", "902")):
            shutil.copy(f"out_final/rov_side_plate_{s}.stl", f"out_lbl/{n}_rov_side_plate_{s}.stl")
            print(" ", write_part(f"{n}_rov_side_plate_{s}", "out_lbl"), flush=True)
    print("done", round(time.time() - t0), "s")
