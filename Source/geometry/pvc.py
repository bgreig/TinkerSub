"""
Off-the-shelf PVC for the ROV frame: 3/4" Sch40 pipe, slip tees, slip caps, and a 4" Sch40 slip cap.
Fitting sizes are nominal ASTM D2466 values; real fittings vary by a mm or two.
"""
import numpy as np
from manifold3d import Manifold

P34_OD, P34_ID = 26.67, 20.93
F34_OD, F34_SOCK, TEE_C2E, CAP34_L = 33.5, 23.0, 37.0, 28.0
P4_OD = 114.3
CAP4_OD, CAP4_SOCK, CAP4_L = 125.0, 51.0, 66.0

def _cyl(r, z0, z1, n=64):
    return Manifold.cylinder(z1 - z0, r, r, n).translate((0, 0, z0))

def pipe34(L):
    return _cyl(P34_OD/2, 0, L) - _cyl(P34_ID/2, -1, L + 1)

def cap34():
    """z=0 is the open end, pipe goes in to z=SOCK."""
    c = _cyl(F34_OD/2, 0, CAP34_L - 3) + (Manifold.sphere(F34_OD/2, 48).scale((1, 1, 0.25)).translate((0, 0, CAP34_L - 3)))
    return c - _cyl(P34_OD/2 + 0.05, -1, F34_SOCK)

def tee34():
    """Run along z (centered on 0), branch along -x."""
    run = _cyl(F34_OD/2, -TEE_C2E, TEE_C2E)
    br = _cyl(F34_OD/2, 0, TEE_C2E).rotate((0, -90, 0))
    t = run + br
    t = t - _cyl(P34_OD/2 + 0.05, -TEE_C2E - 1, -TEE_C2E + F34_SOCK) - _cyl(P34_OD/2 + 0.05, TEE_C2E - F34_SOCK, TEE_C2E + 1)
    t = t - _cyl(P34_ID/2, -TEE_C2E, TEE_C2E)
    t = t - _cyl(P34_OD/2 + 0.05, TEE_C2E - F34_SOCK, TEE_C2E + 1).rotate((0, -90, 0))
    t = t - _cyl(P34_ID/2, 0, TEE_C2E).rotate((0, -90, 0))
    return t

def cap4():
    """4" Sch40 slip cap. z=0 is the open end, pipe bottoms at z=CAP4_SOCK."""
    body = _cyl(CAP4_OD/2, 0, CAP4_SOCK + 4, 128)
    crown = Manifold.sphere(CAP4_OD/2, 128).scale((1, 1, (CAP4_L - CAP4_SOCK - 4) / (CAP4_OD/2)))
    crown = crown ^ _cyl(CAP4_OD/2 + 1, 0, 100, 128)
    c = body + crown.translate((0, 0, CAP4_SOCK + 4))
    return c - _cyl(P4_OD/2 + 0.1, -1, CAP4_SOCK, 128)

def align_z(axis, origin):
    """4x4 matrix taking +z to `axis`, placed at `origin`."""
    z = np.asarray(axis, float); z /= np.linalg.norm(z)
    a = np.array([0, 0, 1.0]) if abs(z[2]) < 0.9 else np.array([1.0, 0, 0])
    x = np.cross(a, z); x /= np.linalg.norm(x); y = np.cross(z, x)
    M = np.eye(4); M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = x, y, z, origin
    return M

if __name__ == "__main__":
    for n, m in [("pipe", pipe34(100)), ("cap34", cap34()), ("tee34", tee34()), ("cap4", cap4())]:
        print(n, round(m.volume()), m.bounding_box())

P3_OD = 88.9
CAP3_OD, CAP3_SOCK, CAP3_L = 100.0, 46.0, 60.0
def cap3():
    """3" Sch40 slip cap. z=0 is the open end, pipe bottoms at z=CAP3_SOCK."""
    body = _cyl(CAP3_OD/2, 0, CAP3_SOCK + 4, 128)
    crown = Manifold.sphere(CAP3_OD/2, 128).scale((1, 1, (CAP3_L - CAP3_SOCK - 4) / (CAP3_OD/2)))
    crown = crown ^ _cyl(CAP3_OD/2 + 1, 0, 100, 128)
    c = body + crown.translate((0, 0, CAP3_SOCK + 4))
    return c - _cyl(P3_OD/2 + 0.1, -1, CAP3_SOCK, 128)
