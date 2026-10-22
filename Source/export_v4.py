"""
Exports every new v4 printed part to out/ in print orientation (mm), and reports size / watertightness.
Run: python3 export_v4.py
"""
import os
import numpy as np, trimesh
import frame_clamp as FC, rov_parts as RP, lights as LT

def save(name, m, rot=None):
    if rot is not None: m = m.rotate(rot)
    g = m.to_mesh(); t = trimesh.Trimesh(g.vert_properties[:, :3], g.tri_verts)
    t.apply_translation([-(t.bounds[0][0] + t.bounds[1][0])/2, -(t.bounds[0][1] + t.bounds[1][1])/2, -t.bounds[0][2]])
    t.export(f"out/{name}.stl")
    print(f"{name:30s} watertight={t.is_watertight} bodies={len(t.split(only_watertight=False))} size={np.round(t.extents, 1)}")

def lead_tray_50():
    FC.TRAY_L = 50.0
    t = FC.lead_tray(FC.SKID4)
    FC.TRAY_L = 100.0
    return t

if __name__ == "__main__":
    os.makedirs("out", exist_ok=True)
    save("rov_frame_clamp_top_cap", FC.top_cap())
    save("rov_frame_clamp_corner", FC.body4(FC.CORNER_YAW))
    save("rov_frame_clamp_mid", FC.body4(0.0))
    save("rov_frame_clamp_pod", FC.pod_bottom4())
    save("rov_lead_tray_50", lead_tray_50())
    save("rov_junction_bridge", FC.junction_bridge())
    save("rov_junction_box_6", FC.junction_box(6))
    save("rov_junction_box_2", FC.junction_box(2))
    save("rov_endcap_rear_5hole", FC.endcap_rear_5hole())
    save("rov_pod_flange_3in", RP.battery_flange())
    save("rov_pod_endcap_3in", RP.battery_endcap(), rot=(180, 0, 0))        # plate down
    save("rov_cell_plate_8", RP.battery_cell_plate())
    save("rov_light_rear_body", LT.rear_body())
    save("rov_light_front_ring", LT.front_ring(), rot=(180, 0, 0))          # front face down
    save("rov_light_spacer", LT.spacer())
