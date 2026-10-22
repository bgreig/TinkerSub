"""
Junction box 501 + lid 503 (replaces the two potted boxes 501 / 502; 502 retired).

One printed box on the junction deck (606) over the rear station, under the cowl:
  - 6 x SP13 2-pin IP68 panel sockets (rear-nut type) for the thrusters, 3 on each side face, so each lead comes in
    from its own side: port face T1 (front), T5 (vertical), T3 (rear); starboard face T2, T6, T4.
  - 2 x SP13 3-pin sockets on the front face for the lights (L1 port, L2 starboard). 3-pin so a light can never be
    plugged into a motor socket.
  - aft face: 12-core (MOTORS gland) and 4-core (LIGHTS gland) cable exits.
  - inside: solder the cores to the socket cups, then pot the box to just below the rim. The potting keeps water that
    gets past a connector away from the cables to the hull. The lid (503) screws on top and only covers the potting.
Every socket is labelled on the box face below it, and the lid carries the same map.

Print frame (mm): x = starboard (+) / port (-), y = forward, z = up, base at z = 0 (right-handed).
Assembly: box frame -> ROV frame (-x, z + DECK_TOP, y + JB_ZC)  (ROV frame: x = port, y = up, z = forward).
SP13 panel cutout: 13.2 mm round with an anti-rotation flat 12.3 mm from the opposite edge (check your connector).
usage: python3 jbox.py  (writes out/rov_junction_box.stl, out/rov_junction_lid.stl)
"""
import numpy as np
from manifold3d import Manifold, CrossSection
from rov_parts import box, cyl, xcyl, ycyl
from engrave import text_cs, DEPTH

W, L, H = 68.0, 116.0, 30.0            # across, along the hull, height
WALL, FLOOR = 3.0, 3.0
SOCK_Z = 16.5                           # socket axis height above the base
SOCK_D, SOCK_FLAT = 13.2, 12.3
MOTOR_Y = (18.0, -9.0, -36.0)          # front, middle, rear socket on each side
MOTORS = {-1: ("T1", "T5", "T3"), +1: ("T2", "T6", "T4")}      # -1 = port face, +1 = starboard face
LIGHT_X = {"L1": -12.0, "L2": 12.0}                         # L1 port, L2 starboard
EXITS = {"12-CORE": (-13.0, 5.2), "4-CORE": (15.0, 3.5)}   # x, hole radius (12-core OD <= 10 mm, 4-core 3-6.5 mm)
EXIT_Z = 15.0
BOSS = [(sx * (W / 2 - 6.5), sy * (L / 2 - 6.5)) for sx in (-1, 1) for sy in (-1, 1)]   # lid screws, M3 inserts
BASE_SCREWS = [(sx * 20.0, sy * 36.0) for sx in (-1, 1) for sy in (-1, 1)]               # M3 into the deck inserts
LID_T, LIP = 3.0, 2.0

def rrect(x0, x1, y0, y1, r):
    return CrossSection.square((x1 - x0 - 2 * r, y1 - y0 - 2 * r)).translate((x0 + r, y0 + r)).offset(r, circular_segments=24)

def dhole(axis, c, length):
    """SP13 D-shaped panel hole along axis 'x' or 'y' centred at c, flat at the bottom."""
    cs = CrossSection.circle(SOCK_D / 2, 48) ^ CrossSection.square((40, 40)).translate((-20, -SOCK_D / 2 + (SOCK_D - SOCK_FLAT) , ))
    m = Manifold.extrude(cs, length).translate((0, 0, -length / 2))          # along z, profile in xy (y = up)
    if axis == "x":   # profile (u, v) -> (y, z), extrude along x
        m = m.transform([[0, 0, 1, c[0]], [1, 0, 0, c[1]], [0, 1, 0, c[2]]])
    else:             # profile (u, v) -> (x, z), extrude along y
        m = m.transform([[1, 0, 0, c[0]], [0, 0, -1, c[1]], [0, 1, 0, c[2]]])
    return m

def deboss(face, text, h, cu, cv):
    """text cut DEPTH into an outer face; (cu, cv) = position on the face as seen from outside (u right, v up)."""
    cs = text_cs(text, h)
    t = Manifold.extrude(cs, DEPTH + 0.3)
    X, Y = W / 2, L / 2
    M = {"+x": [[0, 0, 1, X - DEPTH], [1, 0, 0, cu], [0, 1, 0, cv]],
         "-x": [[0, 0, -1, -X + DEPTH], [-1, 0, 0, -cu], [0, 1, 0, cv]],
         "+y": [[-1, 0, 0, -cu], [0, 0, 1, Y - DEPTH], [0, 1, 0, cv]],
         "-y": [[1, 0, 0, cu], [0, 0, -1, -Y + DEPTH], [0, 1, 0, cv]],
         "top": [[1, 0, 0, cu], [0, 1, 0, cv], [0, 0, 1, LID_T - DEPTH]]}[face]
    return t.transform(M)

def sockets():
    """(name, face, axis, centre) for every socket; centre on the outer face."""
    out = []
    for sx, names in MOTORS.items():
        for n, y in zip(names, MOTOR_Y): out.append((n, "+x" if sx > 0 else "-x", "x", (sx * W / 2, y, SOCK_Z)))
    for n, x in LIGHT_X.items(): out.append((n, "+y", "y", (x, L / 2, SOCK_Z)))
    return out

def junction_box():
    outer = Manifold.extrude(rrect(-W / 2, W / 2, -L / 2, L / 2, 5.0), H)
    inner = Manifold.extrude(rrect(-W / 2 + WALL, W / 2 - WALL, -L / 2 + WALL, L / 2 - WALL, 2.5), H).translate((0, 0, FLOOR))
    b = outer - inner
    for x, y in BOSS:                                                     # lid screw bosses with M3 heat-set holes
        b = b + (cyl(5.0, H, 0) .translate((x, y, 0)) ^ outer)
        b = b - cyl(2.0, 7.0, H - 6.5).translate((x, y, 0))
    for n, face, axis, c in sockets():
        b = b - dhole(axis, c, WALL * 3 + 2)
    for n, (x, r) in EXITS.items():
        b = b - ycyl(r, -L / 2 - 1, -L / 2 + WALL + 1, x, EXIT_Z)
    for x, y in BASE_SCREWS:                                              # M3 x 8 down into the deck, heads end up potted
        b = b - cyl(1.7, FLOOR + 2, -1).translate((x, y, 0)) - cyl(3.0, 2.0, FLOOR - 1.2).translate((x, y, 0))
    b = b - box(-W / 2 - 1, W / 2 + 1, -L / 2 - 1, L / 2 + 1, H - 0.01, H + 5)   # clean top rim
    # labels on the faces, below each socket and beside each exit
    for n, face, axis, c in sockets():
        u = c[1] if face == "+x" else (-c[1] if face == "-x" else -c[0])
        b = b - deboss(face, n, 4.2, u, 4.0)
    for n, (x, r) in EXITS.items():
        b = b - deboss("-y", n.replace("-CORE", ""), 3.6, x, 4.0)
    return b

def junction_lid():
    """Flat lid with a locating lip underneath; 4 x M3 x 8 countersunk screws into the box bosses.
    Exported flipped (top face on the bed, lip up) so it prints without supports; the socket map is debossed in the top."""
    top = Manifold.extrude(rrect(-W / 2, W / 2, -L / 2, L / 2, 5.0), LID_T)
    lip_o = rrect(-W / 2 + WALL + 0.35, W / 2 - WALL - 0.35, -L / 2 + WALL + 0.35, L / 2 - WALL - 0.35, 2.2)
    lip_i = rrect(-W / 2 + WALL + 2.0, W / 2 - WALL - 2.0, -L / 2 + WALL + 2.0, L / 2 - WALL - 2.0, 1.0)
    lip = Manifold.extrude(lip_o - lip_i, LIP).translate((0, 0, -LIP))
    m = top + lip
    for x, y in BOSS:
        m = m - cyl(1.7, LID_T + LIP + 2, -LIP - 1).translate((x, y, 0))
        m = m - Manifold.cylinder(1.7, 1.7, 3.3, 24).translate((x, y, LID_T - 1.7))   # countersink
        m = m - cyl(6.0, LIP + 0.1, -LIP - 0.05).translate((x, y, 0))     # lip clears the bosses
    # socket map on the top face: front of the ROV = +y
    for sx, names in MOTORS.items():
        for n, y in zip(names, MOTOR_Y):
            m = m - deboss("top", n, 5.0, sx * (W / 2 - 13.0), y)
    for n, x in LIGHT_X.items(): m = m - deboss("top", n, 5.0, x, L / 2 - 11.0)
    m = m - deboss("top", "FWD", 4.0, 0, L / 2 - 22.0)
    for n, (x, r) in EXITS.items(): m = m - deboss("top", n, 3.4, x, -L / 2 + 10.0)
    return m

# ---------------- bought-part mockups for the assembly and renders (mated SP13 plug + socket flange + cable)
def plugs():
    m = Manifold()
    for n, face, axis, c in sockets():
        s = cyl(9.5, 2.5, 0) + cyl(9.0, 34.0, 2.5) + cyl(6.5, 12.0, 36.5) + cyl(2.9, 30.0, 48.5)   # along +z from the face
        if face == "+x": M = [[0, 0, 1, c[0]], [0, 1, 0, c[1]], [-1, 0, 0, c[2]]]
        elif face == "-x": M = [[0, 0, -1, c[0]], [0, 1, 0, c[1]], [1, 0, 0, c[2]]]
        else: M = [[1, 0, 0, c[0]], [0, 0, 1, c[1]], [0, -1, 0, c[2]]]
        m = m + s.transform(M)
    return m

if __name__ == "__main__":
    import trimesh
    for name, part, flip in (("rov_junction_box", junction_box(), False), ("rov_junction_lid", junction_lid(), True)):
        if flip: part = part.rotate((180, 0, 0))
        g = part.to_mesh(); t = trimesh.Trimesh(g.vert_properties[:, :3], g.tri_verts)
        t.apply_translation([-(t.bounds[0][0] + t.bounds[1][0]) / 2, -(t.bounds[0][1] + t.bounds[1][1]) / 2, -t.bounds[0][2]])
        t.export(f"out/{name}.stl")
        print(f"{name:20s} watertight={t.is_watertight} bodies={len(t.split(only_watertight=False))} size={np.round(t.extents, 1)}")
