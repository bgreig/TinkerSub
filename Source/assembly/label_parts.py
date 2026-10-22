"""Deboss part numbers + mounting labels into every printed part. Writes out_lbl/<PN>_<stem>.stl and a report."""
import os, sys, json, trimesh
from concurrent.futures import ProcessPoolExecutor
import parts_final as PF
from engrave import engrave_all

OUT = "out_lbl"; os.makedirs(OUT, exist_ok=True)
def job(stem):
    t = trimesh.load(f"out_final/{stem}.stl")
    pnl = PF.PN_LABEL.get(stem, PF.L(PF.PN[stem], None, 6.0, "top", 2.0))
    t2, rep = engrave_all(t, [pnl] + PF.LABELS.get(stem, []))
    if any("did not fit" in r for r in rep[:1]):                     # narrow part: smaller text, tighter margin, then the walls
        for alt in (PF.L(PF.PN[stem], None, 4.0, "top", **PF.SMALL),) + tuple(PF.L(PF.PN[stem], None, 4.0, "top", side=sd, **PF.SMALL) for sd in ("+y", "-y", "+x", "-x")):
            t3, r3 = engrave_all(t, [alt] + PF.LABELS.get(stem, []))
            if not any("did not fit" in r for r in r3[:1]): t2, rep = t3, r3; break
    t2.export(f"{OUT}/{PF.PN[stem]}_{stem}.stl")
    return stem, rep, bool(t2.is_watertight)

if __name__ == "__main__":
    stems = [s for _, s, *__ in PF.BASE_PRINTED if s not in PF.PRE_LABELED] if len(sys.argv) < 2 else sys.argv[1:]
    with ProcessPoolExecutor(4) as ex:
        res = list(ex.map(job, stems))
    bad = 0
    for stem, rep, wt in res:
        flag = "" if wt and not any("did not fit" in r for r in rep) else "   <-- CHECK"
        bad += bool(flag); print(f"{PF.PN[stem]} {stem:28s} {'; '.join(rep)}{flag}")
    print("issues:", bad)
    if len(sys.argv) < 2:                       # parts drawn with their labels already engraved: copied as they are
        import shutil
        for s_ in PF.PRE_LABELED: shutil.copy(f"out_final/{s_}.stl", f"{OUT}/{PF.PN[s_]}_{s_}.stl")
