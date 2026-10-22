"""
Mesh -> STEP solids for CAD apps (Fusion 360, Onshape, FreeCAD, SolidWorks).
Each triangle mesh becomes a closed solid; coplanar triangles are merged into single planar faces, so flat faces,
slots and pockets come in as clean faces you can Press-Pull / Move. Curved surfaces stay faceted.
"""
import numpy as np, trimesh
from OCP.gp import gp_Pnt, gp_Trsf, gp_Ax1, gp_Dir, gp_Vec
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace, BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid, BRepBuilderAPI_Transform
from OCP.TopoDS import TopoDS
from OCP.TopAbs import TopAbs_SHELL
from OCP.TopExp import TopExp_Explorer
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCP.ShapeFix import ShapeFix_Solid

def mesh_to_solid(t):
    t = t.copy(); t.merge_vertices(); t.remove_unreferenced_vertices()
    P = [gp_Pnt(*map(float, v)) for v in t.vertices]
    sew = BRepBuilderAPI_Sewing(1e-4)
    for a, b, c in t.faces:
        poly = BRepBuilderAPI_MakePolygon(P[a], P[b], P[c], True)
        if not poly.IsDone(): continue
        f = BRepBuilderAPI_MakeFace(poly.Wire(), True)
        if f.IsDone(): sew.Add(f.Face())
    sew.Perform()
    sh = sew.SewedShape()
    ex = TopExp_Explorer(sh, TopAbs_SHELL)
    ms = BRepBuilderAPI_MakeSolid()
    while ex.More(): ms.Add(TopoDS.Shell(ex.Current())); ex.Next()
    fx = ShapeFix_Solid(ms.Solid()); fx.Perform()
    u = ShapeUpgrade_UnifySameDomain(fx.Solid(), True, True, False); u.SetLinearTolerance(1e-4); u.SetAngularTolerance(1e-4); u.Build()
    return u.Shape()

def transformed(shape, M):
    """M: 4x4 numpy placement matrix"""
    tr = gp_Trsf()
    tr.SetValues(*[float(M[i, j]) for i in range(3) for j in range(4)])
    return BRepBuilderAPI_Transform(shape, tr, True).Shape()
