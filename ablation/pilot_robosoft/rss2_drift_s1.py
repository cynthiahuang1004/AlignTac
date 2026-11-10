"""RSS round 2: CONTROLLED drift on session 1 (K = 25 protocol, 3,897 pool frames whose registered pose is known).
A re-placement is simulated by adding one rigid offset per object to the registered (theta, x, y) of all its pool frames
(translation of Euclidean length T in a random direction, rotation +-R; press unchanged).  For every level we score
  stale        the mesh at the drifted pose (what a pipeline with a stale calibration would label), and
  stale->al    the K=25 aligner started from the drifted pose (no teacher, no recalibration),
against the registered labels, and (for --student-levels) write fits_dr<T>_{stale,al}.json for pseudo_label_rc.py --fits.
usage: python ablation/pilot_robosoft/rss2_drift_s1.py --out ablation/pilot_robosoft/rss2_drift_s1_k25.json
"""
import argparse, json, math, os, os.path as osp, sys
import numpy as np, torch
ROOT = osp.dirname(osp.dirname(osp.dirname(osp.abspath(__file__))))
sys.path.insert(0, ROOT); sys.path.insert(0, osp.join(ROOT, "scripts")); sys.path.insert(0, osp.join(ROOT, "scripts", "tactile_render")); sys.path.insert(0, osp.dirname(osp.abspath(__file__)))
from fit_baselines import B, load_frames, score, summarize, fmt, SYM  # noqa: E402
from train_aligner import Aligner  # noqa: E402
from rss2_loo3_diag import run_aligner  # noqa: E402
G = "/media/hdd/ihsuan/gs_blender"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--al-root", default=f"{G}/real_pseudo_k25_ro_al"); ap.add_argument("--real-root", default=f"{G}/real_filtered")
    ap.add_argument("--aligner", default="outputs/aligner_k25_realonly/aligner.pt")
    ap.add_argument("--trans", default="0,0.25,0.5,0.75,1,1.5,2,3,4"); ap.add_argument("--rot", default="0,2,5,10")
    ap.add_argument("--student-levels", default="0.5,1,2,3", help="translation levels (with --student-rot) whose fits are written for all frames")
    ap.add_argument("--student-rot", type=float, default=2.0)
    ap.add_argument("--grid-step", type=int, default=3, help="frame subsampling for the quality grid")
    ap.add_argument("--fits-dir", default="outputs/rss2_fits/s1_k25_drift"); ap.add_argument("--out", required=True); ap.add_argument("--device", default="cuda:0")
    args = ap.parse_args(); os.chdir(ROOT); dev = args.device; os.makedirs(args.fits_dir, exist_ok=True)
    sym = json.load(open(SYM)) if osp.exists(SYM) else {}
    period = lambda o: sym.get(o, {}).get("period_deg", 360.0)  # noqa: E731
    items = load_frames(args.al_root, args.real_root, None, 1)
    objs = sorted({it["obj"] for it in items})
    for o in objs:
        B.get_zmap(o)
    A = Aligner().to(dev).eval(); A.load_state_dict(torch.load(args.aligner, map_location=dev))
    rng = np.random.RandomState(0)
    off = {o: (rng.uniform(0, 2 * math.pi), int(rng.choice([-1, 1]))) for o in objs}      # per-object direction and rotation sign (fixed over levels)
    def drift(its, T, R):
        return [(it["gt_pose"][0] + off[it["obj"]][1] * math.radians(R), it["gt_pose"][1] + T * math.cos(off[it["obj"]][0]),
                 it["gt_pose"][2] + T * math.sin(off[it["obj"]][0]), it["gt_pose"][3]) for it in its]
    def rep(its, ps):
        rows = [score(it, p, period(it["obj"])) for it, p in zip(its, ps)]
        return summarize(rows), {o: summarize([r for r, it in zip(rows, its) if it["obj"] == o]) for o in objs}
    out = {"args": vars(args), "offsets": {o: dict(direction_rad=off[o][0], rot_sign=off[o][1]) for o in objs}, "n": len(items), "grid": {}, "student": {}}
    for T in [float(v) for v in args.student_levels.split(",")]:
        st = drift(items, T, args.student_rot); al = run_aligner(A, items, st, dev)
        tag = f"dr{int(round(T * 10)):02d}"
        for name, ps in (("stale", st), ("al", al)):
            json.dump({it["tac"]: dict(pose=list(p[:3]), p=float(p[3]), err=0.0, tp=list(it["tp"])) for it, p in zip(items, ps)}, open(osp.join(args.fits_dir, f"fits_{tag}_{name}.json"), "w"))
            s, po = rep(items, ps); out["student"][f"{tag}_{name}"] = dict(T=T, R=args.student_rot, summary=s, per_object=po)
            print(f"[student T={T:g} mm R={args.student_rot:g}] " + fmt(name, s), flush=True)
    sub = items[::args.grid_step]
    for R in [float(v) for v in args.rot.split(",")]:
        for T in [float(v) for v in args.trans.split(",")]:
            st = drift(sub, T, R); al = run_aligner(A, sub, st, dev)
            out["grid"][f"T{T:g}_R{R:g}"] = dict(T=T, R=R, stale=rep(sub, st)[0], al=rep(sub, al)[0])
            g = out["grid"][f"T{T:g}_R{R:g}"]
            print(f"[grid T={T:g} R={R:g}] stale IoU {g['stale']['iou']:.3f} cMAE {g['stale']['cmae']:.3f} | aligner IoU {g['al']['iou']:.3f} cMAE {g['al']['cmae']:.3f} rot {g['al']['rot']:.2f} trans {g['al']['trans']:.2f}", flush=True)
            json.dump(out, open(args.out, "w"), indent=1)
    json.dump(out, open(args.out, "w"), indent=1); print("->", args.out)


if __name__ == "__main__":
    main()
