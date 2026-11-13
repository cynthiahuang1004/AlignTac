"""Re-capture analysis: image-to-image registration of tactile imprints against the commanded robot motion (no mesh, no network).

For every pair of presses (within a run, or between runs taken at the same commanded poses) the ridge mask of press a is mapped
into press b with the motion the robot reports, then a small rigid correction (dtheta, dx, dy) is fitted to the image evidence.
The correction is what the robot readings do not explain:
  * within a placement  -> non-rigidity of the imprint + image noise      (protocol part A: rigidity)
  * between placements  -> the displacement of that placement             (parts A2 / B: fiducial offset)

Pose model = the one that produced every label of the project (scripts/build_real_filtered_new.py: robot_to_gt / gt_depth_mm):
  sensor-plane point of image pixel (u, v):   w = -((u, v) - S/2) * VIEW / S
  object point m is seen at                    w = R(theta) m + c,   theta = -2 atan2(qx, qy),   c = (ee_y - C_y, ee_x - C_x)
so press a -> press b is                       w_b = R(theta_b - theta_a) (w_a - c_a) + c_b      (object constants cancel).

usage:
  python rss2_recapture/rss2_recapture_check.py pairs  <run dir> [<run dir> ...] --json out.json      # all press pairs inside each run
  python rss2_recapture/rss2_recapture_check.py across <reference run dir> <run dir> [...] --json out.json   # same press index, run vs reference
A run dir holds tactile_images/poses.json as written by the capture program (new_real_test/<object>/<run>).
"""
import argparse
import collections
import itertools
import json
import math
import os.path as osp

import cv2
import numpy as np
from scipy.optimize import minimize

S = 224
VIEW_MM = 17.502                    # field of view of the stored 224-px image in mm (the 0.816 centre crop is applied later, by the data loader)
PX = VIEW_MM / S                    # mm per pixel
OBJ_CENTER = np.array([0.53809766, -0.102125])
uu, vv = np.meshgrid(np.arange(S) + 0.5, np.arange(S) + 0.5)
W = np.stack([-(uu - S / 2) * PX, -(vv - S / 2) * PX], -1)      # sensor-plane mm of every pixel


def ridge(im, ksize=31):
    """Soft ridge map in [0, 1]: black-hat of the brightness (dark thin ridges on a smooth illumination field), blurred."""
    g = cv2.GaussianBlur(cv2.cvtColor(im, cv2.COLOR_RGB2GRAY).astype(np.float32), (3, 3), 0)
    bh = cv2.morphologyEx(g, cv2.MORPH_BLACKHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ksize, ksize)))
    t = max(20.0, 0.45 * np.percentile(bh, 99))
    m = np.clip(bh / t, 0, 1.5) / 1.5
    m[bh < 0.5 * t] = 0
    return cv2.GaussianBlur(m, (0, 0), 1.5)


def presses(run_dir, min_press=0.5, tail=8):
    """One entry per press: mean ridge map and mean robot state over the last `tail` frames at (near) full press."""
    m = json.load(open(f"{run_dir}/tactile_images/poses.json")); cz = m["contact_z_m"]
    by = collections.defaultdict(list)
    for f in m["frames"]:
        if abs(f["pose_ros_timestamp_sec"] - f["image_ros_timestamp_sec"]) > 0.5:
            continue
        e = f["robot_pose_xyz_xyzw"]
        if (cz - e[2]) * 1000 >= min_press:
            by[f["iteration"]].append(f)
    out = {}
    for it, fr in sorted(by.items()):
        dep = np.array([(cz - f["robot_pose_xyz_xyzw"][2]) * 1000 for f in fr])
        fr = [f for f, d in zip(fr, dep) if d >= dep.max() - 0.05][-tail:]
        if len(fr) < 3:
            continue
        e = np.array([f["robot_pose_xyz_xyzw"] for f in fr]).mean(0)
        maps = [ridge(cv2.cvtColor(cv2.imread(f"{run_dir}/tactile_images/{f['filename']}"), cv2.COLOR_BGR2RGB)) for f in fr]
        out[it] = {"theta": -2 * math.atan2(e[3], e[4]), "c": np.array([e[1] - OBJ_CENTER[1], e[0] - OBJ_CENTER[0]]) * 1000,
                   "press": float((cz - e[2]) * 1000), "target_rot": fr[0].get("target_rotation_deg"), "ridge": np.mean(maps, 0),
                   "ee": e[:3].tolist(), "n": len(fr)}
    return out


def warp(src, th, t):
    """Resample map `src` (frame a) on the pixel grid of frame b, where w_b = R(th) w_a + t  (mm)."""
    c, s = math.cos(th), math.sin(th)
    d = W - t
    wa = np.stack([c * d[..., 0] + s * d[..., 1], -s * d[..., 0] + c * d[..., 1]], -1)       # R(-th) (w_b - t)
    mx = (S / 2 - wa[..., 0] / PX - 0.5).astype(np.float32); my = (S / 2 - wa[..., 1] / PX - 0.5).astype(np.float32)
    val = cv2.remap(src, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    ok = (mx >= 0) & (mx <= S - 1) & (my >= 0) & (my <= S - 1)
    return val, ok


def score(a, b, th, t):
    """Normalized correlation of the two ridge maps on their overlap (0 if the overlap is too small or empty of ridges)."""
    wa, ok = warp(a, th, t)
    if ok.sum() < 0.25 * S * S:
        return 0.0
    x, y = wa[ok], b[ok]
    if x.sum() < 30 or y.sum() < 30:
        return 0.0
    return float((x * y).sum() / math.sqrt((x * x).sum() * (y * y).sum() + 1e-9))


def register(pa, pb, max_shift=6.0, max_rot=12.0):
    """Residual rigid correction on top of the robot-reported motion a -> b.  Returns (dtheta deg, dx mm, dy mm, score before, after).
    The correction is expressed at the centre of frame b:  w_b = R(dth) [R(th_b - th_a)(w_a - c_a) + c_b] + d."""
    th0 = pb["theta"] - pa["theta"]; c, s = math.cos(th0), math.sin(th0)
    t0 = pb["c"] - np.array([c * pa["c"][0] - s * pa["c"][1], s * pa["c"][0] + c * pa["c"][1]])

    def tf(p):
        dth = math.radians(p[0]); cc, ss = math.cos(dth), math.sin(dth)
        return th0 + dth, np.array([cc * t0[0] - ss * t0[1], ss * t0[0] + cc * t0[1]]) + p[1:]

    f = lambda p: -score(pa["ridge"], pb["ridge"], *tf(np.asarray(p, float)))
    s0 = -f([0, 0, 0])
    best = (np.zeros(3), s0)
    for r in (0.0, -4.0, 4.0, -8.0, 8.0):                      # coarse search, then local refinement of the best starts
        for dx in np.arange(-max_shift, max_shift + 1e-6, 0.75):
            for dy in np.arange(-max_shift, max_shift + 1e-6, 0.75):
                v = -f([r, dx, dy])
                if v > best[1]:
                    best = (np.array([r, dx, dy]), v)
    res = minimize(f, best[0], method="Powell", options={"xtol": 1e-3, "ftol": 1e-5})
    p = res.x if -res.fun >= best[1] else best[0]
    if abs(p[0]) > max_rot or np.abs(p[1:]).max() > max_shift + 1.5:
        p = best[0]
    return float(p[0]), float(p[1]), float(p[2]), float(s0), float(-f(p))


def stats(rows, key):
    v = np.array([r[key] for r in rows], float)
    return {"median": float(np.median(v)), "mean": float(v.mean()), "p90": float(np.percentile(v, 90)), "max": float(v.max())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["pairs", "across"])
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--json", required=True)
    ap.add_argument("--min-score", type=float, default=0.5, help="pairs whose registered ridge maps correlate less are reported as unreliable")
    args = ap.parse_args()
    out = {"mode": args.mode, "mm_per_px": PX, "runs": {}}
    P = {r: presses(r) for r in args.runs}
    for r, p in P.items():
        print(f"{r}: {len(p)} presses " + " ".join(f"[{i}: rot {math.degrees(v['theta']):.1f} c ({v['c'][0]:.1f}, {v['c'][1]:.1f}) press {v['press']:.2f}]" for i, v in p.items()), flush=True)
    jobs = []
    if args.mode == "pairs":
        for r, p in P.items():
            jobs += [(r, r, a, b) for a, b in itertools.combinations(sorted(p), 2)]
    else:
        ref = args.runs[0]
        for r in args.runs[1:]:
            jobs += [(ref, r, i, i) for i in sorted(set(P[ref]) & set(P[r]))]
    for ra, rb, a, b in jobs:
        pa, pb = P[ra][a], P[rb][b]
        dth, dx, dy, s0, s1 = register(pa, pb)
        row = {"a": a, "b": b, "dtheta_deg": dth, "dx_mm": dx, "dy_mm": dy, "shift_mm": math.hypot(dx, dy), "score_before": s0, "score_after": s1,
               "commanded_rot_deg": math.degrees(pb["theta"] - pa["theta"]), "commanded_shift_mm": float(np.linalg.norm(pb["c"] - pa["c"])),
               "press_a": pa["press"], "press_b": pb["press"], "reliable": bool(s1 >= args.min_score)}
        key = rb if ra == rb else f"{rb} vs {ra}"
        out["runs"].setdefault(key, {"rows": []})["rows"].append(row)
        print(f"{osp.basename(osp.dirname(rb))}/{osp.basename(rb)} press {a}->{b}: commanded {row['commanded_rot_deg']:6.1f} deg {row['commanded_shift_mm']:5.2f} mm | "
              f"unexplained {dth:6.2f} deg ({dx:6.2f}, {dy:6.2f}) = {row['shift_mm']:.2f} mm | corr {s0:.2f} -> {s1:.2f}{'' if row['reliable'] else '  UNRELIABLE'}", flush=True)
    allrows = []
    for k, v in out["runs"].items():
        ok = [r for r in v["rows"] if r["reliable"]]; allrows += ok
        if ok:
            v["summary"] = {"n": len(ok), "n_unreliable": len(v["rows"]) - len(ok), "shift_mm": stats(ok, "shift_mm"),
                            "abs_dtheta_deg": stats([{**r, "a_": abs(r["dtheta_deg"])} for r in ok], "a_"),
                            "mean_dx_dy_dtheta": [float(np.mean([r[q] for r in ok])) for q in ("dx_mm", "dy_mm", "dtheta_deg")]}
            s = v["summary"]
            print(f"== {k}: {s['n']} pairs ({s['n_unreliable']} unreliable): unexplained shift median {s['shift_mm']['median']:.2f} mm (p90 {s['shift_mm']['p90']:.2f}), "
                  f"rotation median {s['abs_dtheta_deg']['median']:.2f} deg; mean offset ({s['mean_dx_dy_dtheta'][0]:.2f}, {s['mean_dx_dy_dtheta'][1]:.2f}) mm {s['mean_dx_dy_dtheta'][2]:.2f} deg", flush=True)
    if allrows:
        out["all"] = {"n": len(allrows), "shift_mm": stats(allrows, "shift_mm"), "abs_dtheta_deg": stats([{**r, "a_": abs(r["dtheta_deg"])} for r in allrows], "a_")}
        print(f"ALL: {len(allrows)} reliable pairs: unexplained shift median {out['all']['shift_mm']['median']:.2f} mm, p90 {out['all']['shift_mm']['p90']:.2f} mm; "
              f"rotation median {out['all']['abs_dtheta_deg']['median']:.2f} deg")
    json.dump(out, open(args.json, "w"), indent=1)


if __name__ == "__main__":
    main()
