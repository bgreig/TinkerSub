"""
v4 compact rail-end light ("bullet" head): replaces the slip cap on the front of each upper float rail.

Head frame: z = 0 is the open end of the socket, the 3/4" rail goes in to SOCK (glued, it closes the float);
+z is the beam direction (straight ahead, parallel to the rail). Overall 42 mm dia x 53 mm.

  rear body (printed)    old rail socket at the back (now the cable's potted strain relief), 2 mm wall with the
                         cable hole + fill / vent holes, potting cavity behind the LED,
                         3x 2.1 mm pilot holes in the front face (M2.5 screws thread straight in)
  heat-sink disc (Al)    42 x 5 mm, 6061: LED star bonded to its front face with thermal epoxy; its rim is in the
                         water and carries the heat (about 18 K rise at 5 W). 4 mm hole for the LED wires (potted).
  spacer (printed)       holds the window off the LED
  window                 28 x 3 mm polycarbonate (or acrylic), O-ring 24 x 1.5 against the front lip
  front ring (printed)   lip + face O-ring groove against the disc, 3x M2.5 x 16 through ring + disc into the body

The cable (2-core, 18 AWG) leaves straight out of the back and is potted in place (2026-10-16; it used to leave
sideways, which the cowl's nose sleeve has no room for).
"""
import numpy as np
from manifold3d import Manifold
import pvc as PV

def cyl(r, z0, z1, n=96): return Manifold.cylinder(z1 - z0, r, r, n).translate((0, 0, z0))
def ycyl(r, y0, y1, x, z, n=32): return Manifold.cylinder(y1 - y0, r, r, n).rotate((-90, 0, 0)).translate((x, y0, z))

R = 21.0
SOCK = PV.F34_SOCK                      # 23
Z_WALL, Z_CAV, Z_DISC, Z_RING, Z_FRONT = SOCK, SOCK + 2.0, SOCK + 11.0, SOCK + 16.0, SOCK + 30.0
CAV_R, SCREW_R = 13.0, 18.5
WIN_R, WIN_T = 14.0, 3.0
Z_WIN = Z_FRONT - 4.0 - WIN_T           # window sits behind a 4 mm lip
CABLE_Z = Z_CAV + 4.5
CABLE_R, FILL_R = 3.2, 8.5              # rear cable hole (6.4 mm, 2-core OD 5-6 mm); fill / vent holes on r 8.5

def _screws(z0, z1, r):
    m = Manifold()
    for k in range(3):
        a = np.radians(90 + 120*k)
        m = m + cyl(r, z0, z1, 24).translate((SCREW_R*np.cos(a), SCREW_R*np.sin(a), 0))
    return m

def rear_body():
    b = cyl(R, 0, Z_DISC)
    b = b - cyl(PV.P34_OD/2 + 0.12, -1, SOCK)                     # rail socket
    b = b - cyl(CAV_R, Z_CAV, Z_DISC + 1)                          # potting cavity
    # (2026-10-16) cable leaves straight out of the back, through the rear wall into the old rail socket, so the head
    # can slide into the cowl's nose sleeve (bore 43 mm) cable first. Two 3 mm holes beside it: fill + vent for potting
    # the cavity from the back with the head nose-down; the socket behind is then filled as the cable's strain relief.
    b = b - cyl(CABLE_R, Z_WALL - 1, Z_CAV + 1, 32)
    for a in (0.0, np.pi):
        b = b - cyl(1.5, Z_WALL - 1, Z_CAV + 1, 20).translate((FILL_R*np.cos(a), FILL_R*np.sin(a), 0))
    # (2026-10-20) 2.1 mm pilots: M2.5 screws thread straight into the PETG. (2026-10-23) 12 mm deep (was 8): from the head
    # seat in the front ring through ring + disc is 16.5 mm, so the M2.5 x 16 the guide used to list never reached the body.
    # M2.5 x 25 now: 8.5 mm of thread.
    b = b - _screws(Z_DISC - 12, Z_DISC + 1, 1.05)
                                                                   # Was 3.6 mm for heat-set inserts: only 0.7 mm of wall to the outside, which bulges.
    # rear chamfer so the head blends into the pipe
    cone = Manifold.cylinder(7.0, PV.P34_OD/2 + 3.0, R + 1.2, 96).translate((0, 0, -0.01))
    b = b - (cyl(R + 2, -1, 6) - cone)
    return b

def disc():
    d = cyl(R, Z_DISC, Z_RING) - cyl(2.0, Z_DISC - 1, Z_RING + 1, 24)
    return d - _screws(Z_DISC - 1, Z_RING + 1, 1.45)

def spacer():
    return cyl(WIN_R - 0.2, Z_RING, Z_WIN) - cyl(11.0, Z_RING - 1, Z_WIN + 1)

def window(): return cyl(WIN_R - 0.1, Z_WIN, Z_WIN + WIN_T)

def front_ring():
    f = cyl(R, Z_RING, Z_FRONT)
    f = f - cyl(WIN_R + 0.1, Z_RING - 1, Z_WIN + WIN_T)            # window + spacer bore
    f = f - cyl(11.5, Z_RING, Z_FRONT + 1)                         # aperture
    f = f - (cyl(15.2 + 1.3, Z_RING - 1, Z_RING + 1.1) - cyl(15.2, Z_RING - 2, Z_RING + 2))   # face O-ring groove (disc)
    f = f - _screws(Z_RING - 1, Z_FRONT + 1, 1.45) - _screws(Z_FRONT - 2.5, Z_FRONT + 1, 2.4)  # M2.5 + head counterbore
    cone = Manifold.cylinder(4.0, R + 0.01, R - 4.0, 96).translate((0, 0, Z_FRONT - 4.0))
    return f - (cyl(R + 2, Z_FRONT - 4, Z_FRONT + 1) - cone)        # front chamfer

def led(): return cyl(10.0, Z_RING, Z_RING + 1.6, 48) + cyl(3.5, Z_RING + 1.6, Z_RING + 3.2, 32)

POD_PARTS = {"lt_rear": rear_body, "lt_disc": disc, "lt_spacer": spacer, "lt_window": window,
             "lt_front": front_ring, "lt_led": led}
CABLE_EXIT = (0.0, 0.0, -4.0)          # cable leaves here, in head coordinates: straight out of the back (-z)

if __name__ == "__main__":
    import trimesh, os
    os.makedirs("out", exist_ok=True)
    ps = {k: f() for k, f in POD_PARTS.items()}
    names = list(ps)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            v = (ps[names[i]] ^ ps[names[j]]).volume()
            if v > 0.05: print("overlap", names[i], names[j], round(v, 2))
    for name, m, flip in [("light_rear_body", ps["lt_rear"], False), ("light_front_ring", ps["lt_front"], True),
                          ("light_spacer", ps["lt_spacer"], False)]:
        if flip: m = m.rotate((180, 0, 0))
        g = m.to_mesh(); tm = trimesh.Trimesh(g.vert_properties[:, :3], g.tri_verts)
        tm.apply_translation(-tm.bounds[0] * np.array([0, 0, 1]))
        tm.export(f"out/rov_{name}.stl")
        print(f"{name:18s} watertight={tm.is_watertight} bodies={len(tm.split(only_watertight=False))} size={np.round(tm.extents, 1)}")
