"""Validation summary of the corrected labels (rss2_relabel.py) and the re-installation offset between the two sessions.

usage (AlignTac root): python rss2_recapture/rss2_relabel_check.py --s1 rss2_recapture/fits_s1.json --s2 rss2_recapture/fits_s2.json --out rss2_recapture/relabel_check.json
Tables: (1) per object and session: held-out agreement with the image (NCC of ridge map and mesh map; constants fitted on the other half of the
presses), split-half stability of the constants, distance of the corrected labels from the stored ones;
(2) session-2 frames labelled with the session-1 constants and the correct kinematics = what a stale calibration really costs;
the object constant is K = (conversion constant of the stored label) + k, in end-effector coordinates, so K_s2 - K_s1 is how far the plate moved.
Assumption for (2): the stored session-1 labels were made with the object constants of build_real_filtered_new.OBJ_MAP (its comment says so).
"""
import argparse
import json
import math
import sys
import os.path as osp
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, osp.dirname(osp.abspath(__file__)))
import rss2_relabel as R          # noqa: E402


def stale_object(a):
    obj, c1, c2 = a
    frames = R.load(R.frames_s2(obj)); use = [f for f in frames if f["press"] >= 0.5] or frames
    bias = np.array(frames[0]["prior"])
    stale = np.array([c1[0], bias[0] + c1[1], bias[1] + c1[2]])                    # session-1 object constants in session-2 coordinates
    out = {"obj": obj, "n": len(use),
           "ncc": {"corrected_s2_constants": R.score(obj, use, np.array(c2), R.SENSOR["s2"]),
                   "s1_constants_s1_sensor": R.score(obj, use, stale, R.SENSOR["s1"]),
                   "s1_constants_s2_sensor": R.score(obj, use, stale, R.SENSOR["s2"]),
                   "curated_per_frame": R.score_pose(obj, use, "old"), "recorded_pose_old_conversion": R.score_pose(obj, use, "stale")},
           "plate_moved_mm": (np.array(c2[1:]) - stale[1:]).tolist(), "plate_rotated_deg": float(c2[0] - c1[0])}
    d = []
    for f in use:                                                                  # label error of the stale constants, per frame, against the corrected labels
        th2, x2 = R.pose(f, np.array(c2), R.SENSOR["s2"]); th1, x1 = R.pose(f, stale, R.SENSOR["s1"])
        d.append([math.degrees(th1 - th2), float(np.linalg.norm(x1 - x2))])
    d = np.array(d); out["stale_label_error"] = {"rot_deg": float(np.abs(d[:, 0]).mean()), "shift_mm_median": float(np.median(d[:, 1])), "shift_mm_p90": float(np.percentile(d[:, 1], 90))}
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--s1", required=True); ap.add_argument("--s2", required=True); ap.add_argument("--out", required=True)
    args = ap.parse_args(); F1, F2 = json.load(open(args.s1)), json.load(open(args.s2)); out = {"per_object": {}, "stale": {}}
    for name, F in (("session 1", F1), ("session 2", F2)):
        print(f"\n== {name}: object | frames | dtheta, k | split-half | held-out NCC corrected / stored" + (" / recorded pose" if name == "session 2" else "") + " | corrected - stored (median, p90 mm; deg)")
        for o, r in sorted(F.items()):
            c = r["constants"]; n = r["ncc_heldout"]; v = r["vs_old_label"]
            print(f"{o:30s} {r['n_frames']:4d} | {c[0]:+5.2f} deg ({c[1]:+5.2f}, {c[2]:+5.2f}) | {r['split_half_diff']['dtheta_deg']:.2f} deg {r['split_half_diff']['k_mm']:.2f} mm | "
                  f"{n['corrected']:.3f} / {n['old_label']:.3f}" + (f" / {n['stale_recorded_pose']:.3f}" if "stale_recorded_pose" in n else "")
                  + f" | {v['shift_mm']['median']:.2f}, {v['shift_mm']['p90']:.2f}; {v['rot_deg']['median_abs']:.2f}")
        a = lambda k: float(np.mean([r["ncc_heldout"][k] for r in F.values() if k in r["ncc_heldout"]]))
        out["per_object"][name] = {"mean_ncc_corrected": a("corrected"), "mean_ncc_stored": a("old_label"),
                                   "median_shift_vs_stored_mm": float(np.median([r["vs_old_label"]["shift_mm"]["median"] for r in F.values()])),
                                   "split_half_k_mm_median": float(np.median([r["split_half_diff"]["k_mm"] for r in F.values()])),
                                   "split_half_dtheta_deg_median": float(np.median([r["split_half_diff"]["dtheta_deg"] for r in F.values()]))}
        print("   mean:", json.dumps(out["per_object"][name]))
    both = sorted(set(F1) & set(F2))
    with ProcessPoolExecutor(len(both)) as ex:
        res = list(ex.map(stale_object, [(o, F1[o]["constants"], F2[o]["constants"]) for o in both]))
    print("\n== session 2 with the session-1 constants (correct kinematics): object | plate moved (mm), rotated (deg) | label error of the stale constants | NCC: corrected / stale / curated per frame / recorded pose, old conversion")
    for r in res:
        out["stale"][r["obj"]] = r; n = r["ncc"]; m = r["plate_moved_mm"]; e = r["stale_label_error"]
        print(f"{r['obj']:30s} ({m[0]:+5.2f}, {m[1]:+5.2f}) = {math.hypot(*m):.2f} mm, {r['plate_rotated_deg']:+.2f} deg | {e['shift_mm_median']:.2f} mm (p90 {e['shift_mm_p90']:.2f}), {e['rot_deg']:.2f} deg | "
              f"{n['corrected_s2_constants']:.3f} / {n['s1_constants_s1_sensor']:.3f} / {n['curated_per_frame']:.3f} / {n['recorded_pose_old_conversion']:.3f}")
    mv = np.array([r["plate_moved_mm"] for r in res])
    out["stale_summary"] = {"plate_moved_mm_mean": mv.mean(0).tolist(), "plate_moved_mm_std": mv.std(0).tolist(), "norm_median": float(np.median(np.hypot(*mv.T))),
                            "rot_deg_median_abs": float(np.median(np.abs([r["plate_rotated_deg"] for r in res]))),
                            "stale_label_error_mm_median": float(np.median([r["stale_label_error"]["shift_mm_median"] for r in res]))}
    print("   summary:", json.dumps(out["stale_summary"]))
    json.dump(out, open(args.out, "w"), indent=1)


if __name__ == "__main__":
    main()
