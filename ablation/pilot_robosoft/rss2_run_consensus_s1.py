"""RSS round 2: run-level fusion of per-touch alignments on SESSION 1 (registered poses are calibration-based).
In this setup a label state is  robot reading + one constant (dtheta, dx, dy, dpress) per placement  (build_real_filtered_new.robot_to_gt:
the calibration is additive in state space).  A single touch cannot observe the translation along an extruded ridge, but the robot knows
the relative motion between touches exactly, so the placement constant can be estimated from ALL touches of a run:
    c_hat = robust mean_i (aligned_i - robot_i),      label_i = robot_i + c_hat.
Here robot_i = registered_i - c_true with c_true unknown to the method; label_i - registered_i = robust mean_i(aligned_i - registered_i),
so the experiment needs only the aligner's per-touch results (rc_fits.json) and never uses a label of the evaluated frames.
usage: python ablation/pilot_robosoft/rss2_run_consensus_s1.py --al-root <pseudo root> --real-root <root> --out <json> [--n-touches 3,5,10,20,50]
"""
import argparse, json, math, os, os.path as osp, sys
import numpy as np
ROOT = osp.dirname(osp.dirname(osp.dirname(osp.abspath(__file__))))
sys.path.insert(0, ROOT); sys.path.insert(0, osp.join(ROOT, "scripts")); sys.path.insert(0, osp.join(ROOT, "scripts", "tactile_render"))
from fit_baselines import B, load_frames, score, summarize, fmt, SYM  # noqa: E402


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--al-root", required=True); ap.add_argument("--real-root", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--fits", default=None, help="other per-touch results for the same frames (default: <al-root>/rc_fits.json)")
    ap.add_argument("--n-touches", default="3,5,10,20,50"); ap.add_argument("--trials", type=int, default=20)
    args = ap.parse_args(); os.chdir(ROOT)
    sym = json.load(open(SYM)) if osp.exists(SYM) else {}
    period = lambda o: sym.get(o, {}).get("period_deg", 360.0)  # noqa: E731
    items = load_frames(args.al_root, args.real_root, None, 1)
    if args.fits:
        F = json.load(open(args.fits))
        for it in items:
            it["al"] = tuple(F[it["tac"]]["pose"]) + (F[it["tac"]]["p"],)
    objs = sorted({it["obj"] for it in items})
    for o in objs:
        B.get_zmap(o)
    E = {o: np.array([[wrap(it["al"][0] - it["gt_pose"][0])] + [it["al"][k] - it["gt_pose"][k] for k in (1, 2, 3)] for it in items if it["obj"] == o]) for o in objs}
    def labels(est):                     # est: {obj: 4-vector}
        return [tuple(np.array(it["gt_pose"]) + est[it["obj"]]) for it in items]
    def rep(name, ps):
        rows = [score(it, p, period(it["obj"])) for it, p in zip(items, ps)]
        s = summarize(rows); po = {o: summarize([r for r, it in zip(rows, items) if it["obj"] == o]) for o in objs}
        print(fmt(name, s), flush=True); return dict(summary=s, per_object=po)
    out = {"args": vars(args), "n": len(items), "objects": objs}
    out["per-touch aligner"] = rep("per-touch aligner", [it["al"] for it in items])
    out["run fusion (mean)"] = rep("fusion mean", labels({o: E[o].mean(0) for o in objs}))
    out["run fusion (median)"] = rep("fusion median", labels({o: np.median(E[o], 0) for o in objs}))
    out["run fusion (median), aligner press kept"] = rep("fusion med, own p", [tuple(np.array(it["gt_pose"][:3]) + np.median(E[it["obj"]], 0)[:3]) + (it["al"][3],) for it in items])
    out["placement_error"] = {o: dict(dtheta_deg=float(np.degrees(np.median(E[o], 0)[0])), dx_mm=float(np.median(E[o], 0)[1]), dy_mm=float(np.median(E[o], 0)[2]),
                                      dp_mm=float(np.median(E[o], 0)[3]), n=int(len(E[o]))) for o in objs}
    for o in objs:
        p = out["placement_error"][o]; print(f"  {o[8:]:26s} n={p['n']:4d} placement error after fusion: {p['dtheta_deg']:+.2f} deg, ({p['dx_mm']:+.2f}, {p['dy_mm']:+.2f}) mm, press {p['dp_mm']:+.3f} mm")
    rng = np.random.RandomState(0); out["n_touches"] = {}
    for n in [int(v) for v in args.n_touches.split(",")]:
        rot, tr = [], []
        for _ in range(args.trials):
            for o in objs:
                j = rng.choice(len(E[o]), min(n, len(E[o])), replace=False); m = np.median(E[o][j], 0)
                rot.append(abs(math.degrees(m[0]))); tr.append((abs(m[1]) + abs(m[2])) / 2)
        out["n_touches"][str(n)] = dict(rot_mean=float(np.mean(rot)), rot_p90=float(np.percentile(rot, 90)), trans_mean=float(np.mean(tr)), trans_p90=float(np.percentile(tr, 90)))
        print(f"  fusion of {n:3d} touches: placement rot {np.mean(rot):.2f} deg (p90 {np.percentile(rot, 90):.2f}), trans {np.mean(tr):.2f} mm (p90 {np.percentile(tr, 90):.2f})")
    json.dump(out, open(args.out, "w"), indent=1); print("->", args.out)


if __name__ == "__main__":
    main()
