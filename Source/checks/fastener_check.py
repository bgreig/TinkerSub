"""
Fastener check: follows every screw hole in the assembled ROV through every part on its axis, and checks that a screw
can actually go in and hold.

How: every round hole of fastener size in every printed part (holes.py) is placed in the assembly (rov_v6.inst).
Along each hole axis, rays at several radii through all parts give the bore profile: where there is plastic, which
part it belongs to, and the hole diameter at each point. Consecutive bore segments between two ends make a "stack".

Errors (the build stops):
  BLIND      a screw can't get in: both ends of the stack are closed (e.g. a clearance hole that stops in the part's own
             plastic with nothing open below it: the 2026-10-22 belly pan bug)
  COVERED    an insert or tapped hole whose mouth is closed by another part with no hole in it
  LENGTH     the screw declared in assembly/fasteners.py for this joint is too short to reach the thread, or so long it
             bottoms out / pokes out where it must not
  UNDECLARED a screw joint the table doesn't know (every joint must name its screw, so the shopping list follows)
  STALE      a joint in the table that no longer exists in the model
Warnings: holes that mate with nothing in the model (bought parts not modelled: servos, SP13 sockets, boards, glands).

usage: python3 fastener_check.py [assembly_v6.json] [report.json]     (run from the build folder; build.py parts runs it)
"""
import sys, os, json, re, collections
import numpy as np, trimesh
import rov_v6 as V6
import holes as H
import part_keys as K

# ---------------------------------------------------------------- hole classes
# Probe radii sit between the hole sizes used in this design (holes are polygons with 8-80 sides: free radius 0.92-1.0 x
# nominal), so the
# largest probe that fits names the hole: 2.1 M2.5 pilot, 2.5 M3 tap pilot, 3.2-3.5 M3 clearance, 4.0 M3 insert,
# 4.5 M4 clearance, 5.5 M5 clearance / 5.6 M4 insert, 6.4 M5 insert, bigger = counterbore or open.
PROBES = np.array([0.0, 0.9, 0.95, 1.12, 1.42, 1.8, 2.05, 2.5, 2.9, 3.5, 4.6])
KIND = {0.9: "small", 0.95: "M2.5 pilot", 1.12: "M3 pilot", 1.42: "M3 clearance", 1.8: "M3 insert", 2.05: "M4 clearance",
        2.5: "M4 insert / M5 clearance", 2.9: "M5 insert", 3.5: "counterbore", 4.6: "open"}
ANG = np.linspace(0, 2 * np.pi, 8, endpoint=False)
FASTENER_D = (1.9, 6.7)
DRILLED = {"hull", "pod"}                                  # PVC pipe: drilled through at assembly (guide sections 10, 11)
FILLERS = re.compile(r"^(rod|stud|pt_pan_servo|pt_tilt_servo|pt_camera|cell|motor|e_.*)$")   # bought parts that sit in holes

def world_meshes():
    """[(key, instance index, trimesh in assembly coordinates)]"""
    base, out = {}, []
    for i, (k, M, g, ex) in enumerate(V6.inst):
        if k not in base:
            gm = V6.parts[k][0].to_mesh(); base[k] = (np.asarray(gm.vert_properties[:, :3], float), np.asarray(gm.tri_verts))
        v, f = base[k]
        vw = v @ np.asarray(M)[:3, :3].T + np.asarray(M)[:3, 3]
        out.append((k, i, trimesh.Trimesh(vw, f, process=False)))
    return out, base

def lines(base):
    """every hole axis in assembly coordinates, merged when two parts' holes share an axis"""
    import hashlib
    cache_f = "fastener_holes_cache.json"                  # hole finding is slow (~50 s): cached per part mesh
    cache = json.load(open(cache_f)) if os.path.exists(cache_f) else {}
    found, new = {}, {}
    for k, (v, f) in base.items():
        if FILLERS.match(k) or k in DRILLED: continue
        hk = hashlib.md5(str(H.VERSION).encode() + np.ascontiguousarray(v, np.float32).tobytes() + np.ascontiguousarray(f, np.int64).tobytes()).hexdigest()
        if hk not in cache:
            cache[hk] = [{**h, "axis": list(map(float, h["axis"])), "point": list(map(float, h["point"]))} for h in H.find_holes(v, f)]
        new[hk] = cache[hk]
        found[k] = [{**h, "axis": np.array(h["axis"]), "point": np.array(h["point"])} for h in cache[hk]]
    json.dump(new, open(cache_f, "w"))
    L = []
    for i, (k, M, g, ex) in enumerate(V6.inst):
        for h in found.get(k, []):
            if not (FASTENER_D[0] <= 2 * h["r"] <= FASTENER_D[1]): continue
            R, T = np.asarray(M)[:3, :3], np.asarray(M)[:3, 3]
            a = R @ h["axis"]; a /= np.linalg.norm(a)
            p = R @ h["point"] + T
            t0, t1 = sorted((h["t0"] * 1.0, h["t1"] * 1.0))
            c = R @ (h["point"] + h["axis"] * (t0 + t1) / 2) + T
            for l in L:
                if abs(abs(np.dot(l["a"], a)) - 1) > 1e-4: continue
                off = c - l["p"]; off -= np.dot(off, l["a"]) * l["a"]
                if np.linalg.norm(off) < 0.35: l["src"].append((k, i, 2 * h["r"])); l["tc"].append(float(np.dot(c - l["p"], l["a"]))); break
            else:
                L.append({"p": c, "a": a, "src": [(k, i, 2 * h["r"])], "tc": [0.0]})
    return L

def profile(line, meshes, span=70.0, dt=0.1):
    """free radius and owner along the line. Returns t[], R[] (bore radius, 0 = solid on the axis, AIR_R+ = open),
    owner[] (instance index of the nearest plastic, -1 = none)"""
    a, p = line["a"], line["p"]
    lo, hi = min(line["tc"]) - span, max(line["tc"]) + span
    u = np.cross(a, [1, 0, 0] if abs(a[0]) < 0.9 else [0, 1, 0]); u /= np.linalg.norm(u); w = np.cross(a, u)
    offs = [np.zeros(3)] + [r * (np.cos(t) * u + np.sin(t) * w) for r in PROBES[1:] for t in ANG]
    ridx = [0] + [j for j in range(1, len(PROBES)) for _ in ANG]
    origins = np.array([p + a * lo + o for o in offs]); dirs = np.tile(a, (len(origins), 1))
    tt = np.arange(lo, hi, dt); n = len(tt)
    solid = np.zeros((len(origins), n), bool); owner = np.full((len(origins), n), -1)
    seg_min, seg_max = p + a * lo, p + a * hi
    for k, i, m in meshes:
        bmin, bmax = m.bounds
        if np.any(np.maximum(seg_min, seg_max) + 5 < bmin) or np.any(np.minimum(seg_min, seg_max) - 5 > bmax): continue
        loc, ri, _ = m.ray.intersects_location(origins, dirs, multiple_hits=True)
        if not len(ri): continue
        d = np.einsum("ij,j->i", loc - origins[ri], a)
        inside0 = m.contains(origins[np.unique(ri)]) if len(ri) else []
        ins = dict(zip(np.unique(ri), inside0))
        for r in np.unique(ri):
            ds = np.sort(d[ri == r]); ds = ds[np.concatenate([[True], np.diff(ds) > 1e-4])]
            state = bool(ins[r]); prev = 0.0
            for x in list(ds) + [hi - lo + 1]:
                if state:
                    j0, j1 = int(max(0, prev) / dt), int(min(x, hi - lo) / dt)
                    solid[r, j0:j1] = True; owner[r, j0:j1] = i
                state = not state; prev = x
    # bore radius at each t: the largest probe radius with every probe at or inside it in air
    ridx = np.array(ridx); n_lv = len(PROBES)
    lv_solid = np.zeros((n_lv, n), bool); lv_owner = np.full((n_lv, n), -1)
    for q in range(n_lv):
        rows = np.nonzero(ridx == q)[0]
        s_ = solid[rows]; lv_solid[q] = s_.any(0)
        first = np.argmax(s_, axis=0); lv_owner[q] = np.where(lv_solid[q], owner[rows][first, np.arange(n)], -1)
    first_lv = np.where(lv_solid.any(0), np.argmax(lv_solid, axis=0), n_lv)
    R = np.where(first_lv == 0, 0.0, PROBES[np.maximum(first_lv - 1, 0)])
    R[first_lv == n_lv] = PROBES[-1]
    # a bore has plastic all round: at the first probe radius that touches plastic, at least 6 of the 8 rays must hit.
    # One-sided contact is a surface beside the axis (a curved wall, a cone, an edge), not a hole: call it open.
    frac = np.zeros(n)
    for q in range(1, n_lv):
        rows = np.nonzero(ridx == q)[0]; m = first_lv == q
        frac[m] = solid[rows][:, m].mean(0)
    R[(first_lv > 0) & (first_lv < n_lv) & (frac < 0.74)] = PROBES[-1]
    own = np.where(first_lv < n_lv, lv_owner[np.minimum(first_lv, n_lv - 1), np.arange(n)], -1)
    return tt, R, own

def segments(tt, R, own):
    out = []
    j = 0
    while j < len(tt):
        k = j
        while k + 1 < len(tt) and R[k + 1] == R[j] and own[k + 1] == own[j]: k += 1
        out.append([tt[j], tt[k], R[j], own[j]]); j = k + 1
    return out

# ---------------------------------------------------------------- stacks: runs of bores between two ends
GAP = 2.0          # an air gap up to this between two bores is a joint line or a clamp slot (1.6 mm), not open air
HEAD = {"M2": (1.9, 2.0), "M2.5": (2.25, 2.5), "M3": (2.75, 3.0), "M4": (3.5, 4.0), "M5": (4.25, 5.0)}   # SHCS head radius, height
NUT = {"M3": (3.2, 4.0), "M4": (4.05, 5.0), "M5": (4.6, 5.0)}         # nyloc: radius across corners, height
CLEAR = {"M2.5": 1.12, "M3": 1.42, "M4": 2.05, "M5": 2.5}             # smallest probe class a screw of this size passes
ENGAGE = {"insert": {"M3": 3.5, "M4": 4.5, "M5": 5.5}, "tapped": {"M3": 4.5}, "self-tap": {"M2.5": 5.0}}

def stacks(segs, names, keys):
    """[{bores: [[t0, t1, R, inst]], lo/hi: end segment or None, filled}] along one line"""
    S = []
    for a, b, r, o in segs:
        k = keys.get(o)
        kind = "solid" if r == 0 else ("open" if r >= PROBES[-1] else "bore")
        if kind == "solid" and k in DRILLED: kind = "drilled"
        S.append([a, b, r, o, kind])
    M_ = []                                                   # merge neighbouring air segments (different nearest parts)
    for x in S:
        if M_ and x[4] == "open" and M_[-1][4] == "open": M_[-1][1] = x[1]
        else: M_.append(x)
    S = M_
    for i in range(1, len(S) - 1):
        if S[i][4] == "open" and S[i][1] - S[i][0] <= GAP and S[i - 1][4] in ("bore", "drilled") and S[i + 1][4] in ("bore", "drilled"):
            S[i][4] = "gap"
    out, i = [], 0
    while i < len(S):
        if S[i][4] != "bore": i += 1; continue
        j = i
        while j + 1 < len(S) and S[j + 1][4] in ("bore", "gap", "drilled"): j += 1
        while i > 0 and (S[i - 1][4] == "drilled" or (S[i - 1][4] == "gap" and i > 1 and S[i - 2][4] == "drilled")): i -= 1   # pipe wall drilled at assembly
        while S[j][4] in ("gap",): j -= 1
        body = [x + [k > i and S[k - 1][4] == "gap"] for k, x in enumerate(S[i:j + 1], start=i) if x[4] in ("bore", "drilled")]
        out.append({"segs": body, "lo": S[i - 1] if i > 0 else None, "hi": S[j + 1] if j + 1 < len(S) else None})
        i = j + 1
    return out

ROOM_R = (1.3, 1.6, 2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5, 3.75, 4.05, 4.25, 4.6, 5.0)
def free_radius(meshes, p, a, t_from, direction, length):
    """largest radius round the axis that is clear for `length` beyond t_from (head / nut / key room)"""
    best = 0.0
    for r in ROOM_R:
        if room(meshes, p, a, t_from, direction, r, length) >= length - 1e-6: best = r
        else: break
    return best

def room(meshes, p, a, t_from, direction, radius, length, skip=()):
    """free space for a head / nut / key: rays parallel to the axis at `radius`, from t_from outward for `length`.
    Returns the length of clear space found (== length if clear)."""
    u = np.cross(a, [1, 0, 0] if abs(a[0]) < 0.9 else [0, 1, 0]); u /= np.linalg.norm(u); w = np.cross(a, u)
    d = a * direction
    orig = np.array([p + a * (t_from + 0.35 * direction) + radius * (np.cos(t) * u + np.sin(t) * w) for t in np.linspace(0, 2 * np.pi, 16, endpoint=False)])
    best = length
    for k, i, m in meshes:
        if i in skip: continue
        bmin, bmax = m.bounds; c = p + a * t_from
        if np.any(c + radius + length + 2 < bmin) or np.any(c - radius - length - 2 > bmax): continue
        loc, ri, _ = m.ray.intersects_location(orig, np.tile(d, (len(orig), 1)), multiple_hits=False)
        if len(ri):
            dist = np.einsum("ij,j->i", loc - orig[ri], d)
            if m.contains(orig).any(): best = 0.0
            best = min(best, float(dist.min()))
        elif m.contains(orig).any(): best = 0.0
    return max(0.0, best)

# ---------------------------------------------------------------- one stack -> a joint (or a finding)
SIZES = ("M2.5", "M3", "M4", "M5")
THREAD_R = {("insert", "M3"): 1.8, ("insert", "M4"): 2.5, ("insert", "M5"): 2.9, ("tapped", "M3"): 1.12, ("self-tap", "M2.5"): 0.95}
SHORT = 0.8        # bore steps shorter than this are cones (countersinks, nose tips, chamfers), not holes

def walk(segs, order, dt_side):
    """walk in from one open end. Returns (size, thread, passage idxs, receiver idxs) or None.
    The screw passes every bore at least its clearance; the thread is the first bore after the passage that matches an
    insert / tapped / self-tap size of a screw no bigger than the narrowest bore passed."""
    passage = []
    for n, j in enumerate(order):
        s_ = segs[j]
        if s_[4] == "drilled": passage.append(j); continue
        R = s_[2]
        if passage:
            pmin = min(segs[q][2] if segs[q][4] != "drilled" else 9 for q in passage)
            for (th, sz), tr in THREAD_R.items():
                # the screw passes every bore so far, and isn't obviously a size bigger (unless the way in is drilled pipe only)
                if R == tr and CLEAR[sz] <= pmin and (sz == "M5" or pmin < CLEAR.get(SIZES[SIZES.index(sz) + 1], 9) or th != "insert" or pmin == 9):
                    rec = [j]
                    for q in order[n + 1:]:
                        if segs[q][2] == R and segs[q][4] == "bore" and segs[q][3] == s_[3]: rec.append(q)
                        else: break
                    return sz, th, passage, rec
        if R >= CLEAR["M2.5"]: passage.append(j); continue
        return None
    return None

def analyse(line, st, meshes, names, keys):
    a, p = line["a"], line["p"]
    segs = [s_ for s_ in st["segs"] if s_[4] == "drilled" or s_[1] - s_[0] >= SHORT - 0.05]
    J = {"at": None, "axis": [round(float(x), 3) for x in a]}
    if not segs: J["type"] = "other"; return J
    mid = (segs[0][0] + segs[-1][1]) / 2
    parts = []
    for s_ in segs:
        n = names[s_[3]]
        if not parts or parts[-1] != n: parts.append(n)
    lo, hi = st["lo"], st["hi"]
    def end(e):
        if e is None or e[4] == "open": return ("open", None)
        return ("solid", e[3])
    elo, ehi = end(lo), end(hi)
    J.update({"at": [round(float(x), 1) for x in p + a * mid], "parts": parts,
              "bores": [[names[s_[3]], "drilled" if s_[4] == "drilled" else KIND.get(s_[2]), round(s_[1] - s_[0] + 0.1, 1)] for s_ in segs],
              "ends": [elo[0] + ("" if elo[1] is None else " " + names[elo[1]]), ehi[0] + ("" if ehi[1] is None else " " + names[ehi[1]])]})
    for e in (elo, ehi):
        if e[0] == "solid" and FILLERS.match(keys[e[1]] or ""): J["type"] = "filled"; return J
    n = len(segs)
    tries = []
    if elo[0] == "open": tries.append(("lo", list(range(n)), elo, ehi))
    if ehi[0] == "open": tries.append(("hi", list(range(n - 1, -1, -1)), ehi, elo))
    found = [(side, w, far) for side, order, e, far in tries for w in [walk(segs, order, side)] if w]
    if found:
        side, (size, thread, passage, rec), far = max(found, key=lambda f: len(f[1][2]))
        J.update(type="screw", size=size, thread=thread, receiver=names[segs[rec[0]][3]], head_part=names[segs[passage[0]][3]])
        slot = any(s_[5] for s_ in segs)                             # a clamp slot between head and thread (pylon pinch)
        if all(segs[q][3] == segs[rec[0]][3] for q in passage) and not slot:
            J["type"] = "unmated"; J["note"] = f"{thread} {size} hole with a counterbore in {names[segs[rec[0]][3]]}: mates with nothing in the model"; return J
        sgn = 1 if side == "lo" else -1                   # +1: walking toward +t
        # head seat: the end of the head pocket (bores wider than the clearance at the open end)
        pocket = []                                       # head pocket: bores at the open end at least as wide as the head
        for q in passage:
            if segs[q][4] != "drilled" and segs[q][2] >= min(HEAD[size][0] - 0.15, 3.5): pocket.append(q)
            else: break
        first = passage[len(pocket)] if len(pocket) < len(passage) else passage[-1]
        seat = segs[first][0] if sgn > 0 else segs[first][1]
        mouth = segs[rec[0]][0] if sgn > 0 else segs[rec[0]][1]
        rec_end = segs[rec[-1]][1] if sgn > 0 else segs[rec[-1]][0]
        grip = abs(mouth - seat); depth = abs(rec_end - mouth)
        # beyond the thread: plastic of the same part = blind; anything else = the tip may pass on
        nxt = rec[-1] + sgn
        beyond = "blind"
        if 0 <= nxt < n: beyond = "bore"
        elif far[0] == "open": beyond = "open"
        elif far[0] == "solid" and far[1] != segs[rec[0]][3]: beyond = "against " + names[far[1]]
        extra = 0.0 if beyond.startswith(("blind", "against")) else (6.0 if beyond == "open" else 2.0)
        emin = ENGAGE[thread].get(size, 4.0)
        J.update(grip=round(grip, 1), depth=round(depth, 1), beyond=beyond,
                 length_ok=[round(grip + min(emin, depth), 1), round(grip + depth - (0.5 if extra == 0 else -extra), 1)])
        hr, hh = HEAD.get(size, (2.75, 3.0))
        J["head_free_r"] = free_radius(meshes, p, a, seat - sgn * 0.6, -sgn, hh - 0.6)   # room for the head (seat found to +/-0.5)
        J["key_free"] = round(room(meshes, p, a, seat - sgn * hh, -sgn, 1.3, 30.0), 1)   # straight run for a hex key
        if depth < min(emin, 3.0): J["error"] = f"SHALLOW: the {thread} hole for the {size} screw is only {depth:.1f} mm deep"
        return J
    # no thread on this axis: a bolt and nut through clearance holes, or a hole that mates with nothing
    rs = [s_[2] for s_ in segs if s_[4] != "drilled"]
    pmin = min(rs) if rs else 9
    size = max([sz for sz in SIZES if CLEAR[sz] <= pmin], default=None, key=SIZES.index)
    if size == "M2.5" or size is None: J["type"] = "other"; return J
    J["size"] = size
    if len(set(s_[3] for s_ in segs)) == 1 and not any(s_[4] == "drilled" for s_ in segs):
        J["type"] = "unmated"; J["note"] = "hole in one part only: mates with a bought part not in the model, or nothing"
        if elo[0] == "solid" and ehi[0] == "solid": J["error"] = "BLIND: hole closed at both ends (" + " / ".join(J["ends"]) + ")"
        return J
    J["type"] = "bolt"
    if elo[0] != "open" or ehi[0] != "open":
        J["error"] = "BLIND: no way through for a bolt (" + " / ".join(J["ends"]) + ")"; return J
    # head / nut pockets at the ends
    def pocket_end(order):                               # head or nut pocket at an end
        k = 0
        while k < len(order) and segs[order[k]][2] >= min(HEAD[size][0] - 0.15, 3.5): k += 1
        return k
    kl, kh = pocket_end(list(range(n))), pocket_end(list(range(n - 1, -1, -1)))
    t_lo = segs[kl][0] if kl < n else segs[0][0]; t_hi = segs[n - 1 - kh][1] if kh < n else segs[-1][1]
    grip = t_hi - t_lo
    hr, hh = HEAD[size]; nr, nh = NUT.get(size, (3.2, 4.0))
    J.update(thread="nut", grip=round(grip, 1), length_ok=[round(grip + nh + 0.5, 1), round(grip + nh + 8, 1)])
    J["end_free_r"] = [free_radius(meshes, p, a, t_lo, -1, nh), free_radius(meshes, p, a, t_hi, +1, nh)]   # head / nut room
    J["key_free"] = [round(room(meshes, p, a, t_lo - nh, -1, 1.3, 30.0), 1), round(room(meshes, p, a, t_hi + nh, +1, 1.3, 30.0), 1)]
    return J

# ---------------------------------------------------------------- main
def run(asm=None, report="fastener_report.json"):
    meshes, base = world_meshes()
    names = {i: K.pn_of(k) for k, i, m in meshes}; keys = {i: k for k, i, m in meshes}
    joints = []
    for l in lines(base):
        tt, R, own = profile(l, meshes)
        for st in stacks(segments(tt, R, own), names, keys):
            joints.append(analyse(l, st, meshes, names, keys))
    # the same physical stack is found once per hole on its axis: keep one
    uniq, seen = [], set()
    for j in joints:
        if j["at"] is None: continue
        key = (tuple(np.round(j["at"], 0)), tuple(np.abs(np.round(j["axis"], 2))))
        if key in seen: continue
        seen.add(key); uniq.append(j)
    return uniq


# ---------------------------------------------------------------- verdicts against assembly/fasteners.py
import itertools as _it
NUT_AF = {"M3": 2.75, "M4": 3.5, "M5": 4.0}            # nyloc across flats / 2: room a held nut needs
BUTTON_R = {"M3": 2.85, "M4": 3.8}
CSK_H = {"M3": 1.7, "M4": 2.3}
TOL = 0.26                                              # probe-radius step: a free radius is known to about this

def _match(parts, decl):
    P = sorted(set(parts))
    if len(P) != len(decl): return False
    for perm in _it.permutations(P):
        if all(p in g.split("|") for p, g in zip(perm, decl)): return True
    return False

def verdicts(joints, FT, guide_text=None):
    errors, warnings, table = [], [], []
    found = collections.defaultdict(list)
    for j in joints:
        where = f"at ({', '.join(f'{x:.0f}' for x in j['at'])})"
        if "error" in j:
            errors.append(f"{j['error']} -- parts {'+'.join(j.get('parts', []))} {where}"); continue
        t = j.get("type")
        if t in ("screw", "bolt"):
            ds = [d for d in FT.JOINTS if _match(j["parts"], d["parts"]) and (d["thread"] == "nut") == (t == "bolt")]
            if not ds:
                errors.append(f"UNDECLARED: {j.get('size')} {j.get('thread')} joint through {'+'.join(j['parts'])} {where} is not in assembly/fasteners.py "
                              f"(screw length that fits: {j['length_ok'][0]:.1f}-{j['length_ok'][1]:.1f} mm)"); continue
            d = ds[0]; found[d["name"]].append(j)
            if d["size"] != j.get("size"):
                errors.append(f"SIZE: {d['name']}: the holes take {j.get('size')}, the table says {d['size']} {where}"); continue
            lo, hi = j["length_ok"]; s = FT.SHIM.get(d["name"], 0.0)
            extra = CSK_H.get(d["size"], 0) if d["head"] == "csk" else 0.0
            if not (lo + s + extra - 0.05 <= d["length"] <= hi + s + extra + 0.05):
                errors.append(f"LENGTH: {d['name']}: {d['size']} x {d['length']} doesn't fit {where}: grip {j['grip']} mm, "
                              f"a {d['size']} x {lo + s + extra:.1f} to {hi + s + extra:.1f} would ({'tip ' + j['beyond'] if j.get('beyond') else 'nut'})")
            if t == "screw" and d["head"] != "csk":
                need = BUTTON_R.get(d["size"], 2.85) if d["head"] == "button" else HEAD[d["size"]][0]
                if j["head_free_r"] < need - TOL:
                    errors.append(f"HEAD ROOM: {d['name']} {where}: {j['head_free_r']} mm free round the axis, the {d['size']} head needs {need}")
                if j.get("key_free", 99) < 8: warnings.append(f"key: {d['name']} {where}: only {j['key_free']} mm straight for a hex key (use a ball-end or short key)")
            if t == "bolt":
                r1, r2 = sorted(j["end_free_r"], reverse=True)
                if r1 < HEAD[d["size"]][0] - TOL or r2 < NUT_AF[d["size"]] - TOL:
                    errors.append(f"ROOM: {d['name']} {where}: {j['end_free_r']} mm free at the ends; head needs {HEAD[d['size']][0]}, nut {NUT_AF[d['size']]}")
        elif t == "unmated":
            ok = [n for p_, h_, n in FT.NOT_JOINTS if p_ in j["parts"] and any(b[1] == h_ for b in j["bores"])]
            if not ok:
                errors.append(f"UNMATED: {' + '.join(b[0] + ' ' + b[1] for b in j['bores'])} {where} mates with nothing in the model. "
                              f"A hole that lines up with nothing is how the top-arm and belly-pan bugs looked. If it is for a bought part, list it in NOT_JOINTS.")
    for d in FT.JOINTS:
        n = len(found[d["name"]])
        if n != d["n"]: errors.append(f"COUNT: {d['name']}: the table says {d['n']}, the model has {n}")
        js = found[d["name"]]
        if js:
            lo = max(j["length_ok"][0] for j in js) + FT.SHIM.get(d["name"], 0); hi = min(j["length_ok"][1] for j in js) + FT.SHIM.get(d["name"], 0)
            table.append([d["name"], n, f"{d['size']} x {d['length']} {d['head']}", d["thread"], f"{lo:.1f}-{hi:.1f}"])
    if guide_text is not None:                         # every screw size the guide names must be one in the table
        ok = {f"{d['size']} x {d['length']}" for d in FT.JOINTS}
        # a size that is not a joint must be named with the whole OTHER_SPECS phrase ("M3 x 6 screws"), so a stale joint
        # size can't hide behind a bought-part screw of the same size
        bad = {}
        for mo in re.finditer(r"\bM\d(?:\.5)? x \d+\b(?!\.?\d)", guide_text):
            m = mo.group(0); here = guide_text[mo.start():mo.start() + 40]
            if m in ok or any(here.startswith(o) for o in FT.OTHER_SPECS): continue
            bad.setdefault(m, []).append(guide_text[max(0, mo.start() - 40):mo.end() + 20].replace("\n", " "))
        for m, ctx in sorted(bad.items()):
            errors.append(f"GUIDE TEXT names '{m}', which is not a screw in assembly/fasteners.py (stale size?): ..." + " | ".join(ctx[:3]) + "...")
    return errors, warnings, table

if __name__ == "__main__":
    import fasteners as FT
    rep = sys.argv[1] if len(sys.argv) > 1 else "fastener_report.json"
    gt = None
    gpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "guide", "build_guide_final.py")
    if os.path.exists(gpath): gt = open(gpath).read()
    J = run()
    errors, warnings, table = verdicts(J, FT, gt)
    json.dump({"errors": errors, "warnings": warnings, "joints": table, "detail": J}, open(rep, "w"), indent=1)
    w = max(len(r[0]) for r in table) if table else 10
    print(f"{'joint':{w}s}  n   screw                 thread    fits")
    for r in table: print(f"{r[0]:{w}s}  {r[1]:<3d} {r[2]:21s} {r[3]:9s} {r[4]} mm")
    for x in warnings: print("warning:", x)
    for x in errors: print("ERROR:", x)
    print(f"fastener check: {len(table)} joint kinds, {sum(r[1] for r in table)} screws, {len(errors)} errors, {len(warnings)} warnings")
    sys.exit(1 if errors else 0)
