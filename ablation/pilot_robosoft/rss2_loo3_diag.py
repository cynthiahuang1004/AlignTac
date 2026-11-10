"""RSS round 2 diagnostic: why are aligned labels of UNSEEN objects no better than the teacher depth?
Runs the aligner on the pool frames of a pseudo root from several starts and swaps state components with the truth.
  starts:  teacher (pipeline), GT state (fixed point of the aligner), GT pose + teacher press, GT + 5 deg / 0.5 mm
  swaps (on the pipeline result): true press, true pose, true rotation, true translation
usage: python ablation/pilot_robosoft/rss2_loo3_diag.py --al-root <pseudo root> --real-root <root> --aligner <aligner.pt> --out <json> [--step 1]
"""
import argparse, json, math, os, os.path as osp, sys
import numpy as np, torch
from PIL import Image
ROOT = osp.dirname(osp.dirname(osp.dirname(osp.abspath(__file__))))
sys.path.insert(0, ROOT); sys.path.insert(0, osp.join(ROOT, "scripts")); sys.path.insert(0, osp.join(ROOT, "scripts", "tactile_render"))
import fit_baselines as FB  # noqa: E402
from fit_baselines import B, load_frames, score, summarize, fmt, SYM  # noqa: E402
from train_aligner import Aligner, refine  # noqa: E402


def run_aligner(A, items, inits, dev, iters=6):
    res = []
    for k0 in range(0, len(items), 64):
        its = items[k0:k0 + 64]
        img = torch.from_numpy(np.stack([np.array(Image.open(it["tac"]).convert("RGB"), np.float32).transpose(2, 0, 1) / 127.5 - 1 for it in its])).to(dev)
        pz = torch.tensor([inits[k0 + j] for j in range(len(its))], dtype=torch.float32, device=dev)
        pz = refine(A, [it["obj"] for it in its], img, pz, dev, iters=iters)
        res += [tuple(v) for v in pz.tolist()]
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--al-root", required=True); ap.add_argument("--real-root", required=True); ap.add_argument("--aligner", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--step", type=int, default=1); ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--range-scale", type=float, default=1.0, help="must match the aligner's training --range-scale")
    args = ap.parse_args(); os.chdir(ROOT); dev = args.device
    import train_aligner as TA; TA.SCALE = TA.SCALE * args.range_scale
    sym = json.load(open(SYM)) if osp.exists(SYM) else {}
    period = lambda o: sym.get(o, {}).get("period_deg", 360.0)  # noqa: E731
    items = load_frames(args.al_root, args.real_root, None, args.step)
    objs = sorted({it["obj"] for it in items})
    for o in objs:
        B.get_zmap(o)
    A = Aligner().to(dev).eval(); A.load_state_dict(torch.load(args.aligner, map_location=dev))
    rng = np.random.RandomState(0)
    tpress = [float(np.clip(np.load(it["dep"]).max() * 1000, 0.3, 1.6)) for it in items]
    gt = [it["gt_pose"] for it in items]
    starts = {"teacher pose, teacher press (pipeline)": [it["tp"] + (p,) for it, p in zip(items, tpress)],
              "teacher pose, TRUE press": [it["tp"] + (g[3],) for it, g in zip(items, gt)],
              "TRUE pose, teacher press": [(g[0], g[1], g[2], p) for g, p in zip(gt, tpress)],
              "TRUE state": [tuple(g) for g in gt]}
    pert = []
    for g in gt:
        a = rng.uniform(0, 2 * math.pi); s = rng.choice([-1, 1])
        pert.append((g[0] + s * math.radians(5), g[1] + 0.5 * math.cos(a), g[2] + 0.5 * math.sin(a), g[3]))
    starts["TRUE state + 5 deg / 0.5 mm"] = pert
    out = {"n": len(items), "objects": objs, "args": vars(args), "start": {}, "final": {}, "swap": {}, "per_object": {}}
    def rep(sec, name, ps):
        rows = [score(it, p, period(it["obj"])) for it, p in zip(items, ps)]
        out[sec][name] = summarize(rows)
        out["per_object"][sec + " | " + name] = {o: summarize([r for r, it in zip(rows, items) if it["obj"] == o]) for o in objs}
        print(f"[{sec:5s}] " + fmt(name[:18], out[sec][name]) + f"   <- {name}", flush=True)
    rows = []
    for it in items:
        q = FB.quality(np.load(it["dep"]) * 1000, np.load(it["gt"]) * 1000); g = it["gt_pose"]
        rows.append(dict(iou=q[0], cmae=q[1], rot=FB.rot_err(it["tp"][0], g[0]), rot_sym=FB.rot_err(it["tp"][0], g[0], period(it["obj"])),
                         trans=(abs(it["tp"][1] - g[1]) + abs(it["tp"][2] - g[2])) / 2, dp=float("nan")))
    out["teacher_depth"] = summarize(rows); out["per_object"]["teacher depth"] = {o: summarize([r for r, it in zip(rows, items) if it["obj"] == o]) for o in objs}
    print("        " + fmt("teacher depth", out["teacher_depth"]), flush=True)
    finals = {}
    for name, ps in starts.items():
        rep("start", name, ps)
        finals[name] = run_aligner(A, items, ps, dev)
        rep("final", name, finals[name])
    al = finals["teacher pose, teacher press (pipeline)"]
    rep("swap", "aligner result with TRUE press", [(a[0], a[1], a[2], g[3]) for a, g in zip(al, gt)])
    rep("swap", "aligner result with TRUE rotation", [(g[0], a[1], a[2], a[3]) for a, g in zip(al, gt)])
    rep("swap", "aligner result with TRUE translation", [(a[0], g[1], g[2], a[3]) for a, g in zip(al, gt)])
    rep("swap", "aligner result with TRUE pose (only its press)", [(g[0], g[1], g[2], a[3]) for a, g in zip(al, gt)])
    # signed press bias and per-object lines
    out["press_bias_mm"] = {o: float(np.mean([a[3] - g[3] for a, g, it in zip(al, gt, items) if it["obj"] == o])) for o in objs}
    out["teacher_press_bias_mm"] = {o: float(np.mean([p - g[3] for p, g, it in zip(tpress, gt, items) if it["obj"] == o])) for o in objs}
    print("signed press error of the aligner result (mm):", {o: round(v, 3) for o, v in out["press_bias_mm"].items()})
    print("signed press error of the teacher init (mm):  ", {o: round(v, 3) for o, v in out["teacher_press_bias_mm"].items()})
    for o in objs:
        print(o); 
        for k in ("teacher depth", "final | teacher pose, teacher press (pipeline)", "final | TRUE state"):
            print("   " + fmt(k[-18:], out["per_object"][k][o]) + f"   <- {k}")
    json.dump(out, open(args.out, "w"), indent=1); print("->", args.out)


if __name__ == "__main__":
    main()
