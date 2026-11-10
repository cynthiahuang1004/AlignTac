"""Pseudo-label confidence (RSS round 2, P1-5): label-free signals for every aligned pool frame and their relation to the true label error.

Signals (none reads a label of the frame):
  c_last      mean |normalized correction| the aligner still predicts at its final state (non-convergence)
  agree_jit   multi-start agreement: mean depth-IoU between the label and the labels reached from 4 jittered teacher starts
              (+-4 deg, +-0.75 mm, +-0.075 mm press).  Agreement is measured on the rendered mesh depth, so poses that are
              equivalent under the object's symmetry count as agreeing.
  agree_glob  depth-IoU between the label and the label reached from the global-search start (no teacher pose)
  teach_iou / teach_l1   agreement between the aligned mesh depth and the teacher's depth prediction
  render_err  L1 between the K-shot renderer's image at the final state and the real image (rc_fits.json "err")
True error (evaluation only): contact MAE, IoU, rotation error of the mesh label vs the withheld / curated label.
Combined score `conf` = mean of the within-set rank percentiles of agree_jit, agree_glob, teach_iou and (1 - c_last rank).
Writes <out>.json (Spearman table, per-frame records) and, with --fits-dir, rc_fits-style files whose "err" orders the frames
for pseudo_label_rc.py / rss2_subset_root.py:  fits_conf.json (err = -conf), fits_rand.json (random), fits_oracle.json (true cMAE).

usage: python ablation/pilot_robosoft/rss2_confidence.py --al-root $G/real_pseudo_k25_ro_al --aligner outputs/aligner_k25_realonly/aligner.pt \
           --out ablation/pilot_robosoft/rss2_confidence_s1_k25.json --fits-dir outputs/rss2_fits/s1_k25
"""
import argparse, json, math, os, os.path as osp, sys
import numpy as np, torch
from PIL import Image
from scipy.stats import spearmanr, rankdata
ROOT = osp.dirname(osp.dirname(osp.dirname(osp.abspath(__file__))))
sys.path.insert(0, ROOT); sys.path.insert(0, osp.join(ROOT, "scripts")); sys.path.insert(0, osp.join(ROOT, "scripts", "tactile_render"))
import fit_baselines as FB  # noqa: E402
from fit_baselines import B, quality, rot_err, global_fit, mesh_depth_bilinear  # noqa: E402
import pseudo_label_rc as RC  # noqa: E402
from train_aligner import Aligner, refine, depth_batch, SCALE  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--al-root", required=True); ap.add_argument("--real-root", default=RC.REAL); ap.add_argument("--gt-root", default=None)
    ap.add_argument("--aligner", required=True); ap.add_argument("--out", required=True); ap.add_argument("--fits-dir", default=None)
    ap.add_argument("--step", type=int, default=1); ap.add_argument("--no-global", action="store_true"); ap.add_argument("--device", default="cuda:0")
    args = ap.parse_args()
    os.chdir(ROOT); dev = args.device; torch.manual_seed(0); np.random.seed(0)
    fits = json.load(open(osp.join(args.al_root, "rc_fits.json")))
    src = json.load(open(osp.join(args.al_root, "pseudo_manifest.json")))["args"]["src_root"]
    sym = json.load(open(FB.SYM)); period = lambda o: sym.get(o, {}).get("period_deg", 360.0)  # noqa: E731
    gtmap = None
    if args.gt_root:
        import glob
        gtmap = {}
        for pj in glob.glob(f"{args.gt_root}/*/session_*/sensor_0000/raw_data/*_pose.json"):
            d = json.load(open(pj)); gtmap[(pj.split("/")[-5], pj.split("/")[-4], int(d["source"]["frame"]))] = pj
    items = []
    for tac in sorted(fits)[::args.step]:
        unit = osp.dirname(osp.dirname(tac)); idx = osp.basename(tac)[:4]; obj = unit.split("/")[-3]
        f = fits[tac]; gpj = osp.join(unit, "raw_data", idx + "_pose.json")
        if gtmap is not None:
            gpj = gtmap.get((obj, unit.split("/")[-2], int(json.load(open(gpj))["source"]["frame"])))
        items.append(dict(tac=tac, obj=obj, dep=osp.join(unit.replace(args.real_root, src), "raw_data", idx + "_gt.npy"), al=tuple(f["pose"]) + (f["p"],),
                          tp=tuple(f["tp"]), render_err=float(f["err"]), gt=gpj))
    for o in sorted({it["obj"] for it in items}):
        B.get_zmap(o)
    A = Aligner().to(dev).eval(); A.load_state_dict(torch.load(args.aligner, map_location=dev)); sc = SCALE.to(dev)
    print(f"{len(items)} frames from {args.al_root}", flush=True)
    for k0 in range(0, len(items), 64):
        its = items[k0:k0 + 64]; ob = [it["obj"] for it in its]; n = len(its)
        img = torch.from_numpy(np.stack([np.array(Image.open(it["tac"]).convert("RGB"), np.float32).transpose(2, 0, 1) / 127.5 - 1 for it in its])).to(dev)
        Dt = [np.load(it["dep"]) * 1000 for it in its]
        p_al = torch.tensor([it["al"] for it in its], dtype=torch.float32, device=dev)
        p0 = torch.tensor([it["tp"] + (float(np.clip(d.max(), 0.3, 1.6)),) for it, d in zip(its, Dt)], dtype=torch.float32, device=dev)
        with torch.no_grad():
            d_main = depth_batch(ob, p_al, dev)
            last = A(img, d_main).abs().mean(1)
            m_main = d_main > 0.05
            iou = lambda a, b: ((a & b).flatten(1).sum(1).float() / (a | b).flatten(1).sum(1).clamp(min=1).float())  # noqa: E731
            aj = torch.zeros(n, device=dev); sp = torch.zeros(n, device=dev)
            for _ in range(4):
                pj = refine(A, ob, img, p0 + (torch.rand(n, 4, device=dev) * 2 - 1) * sc * 0.5, dev, iters=6)
                aj += iou(depth_batch(ob, pj, dev) > 0.05, m_main) / 4
                sp += ((pj[:, 0] - p_al[:, 0]).abs() / math.radians(1.0) + (pj[:, 1:3] - p_al[:, 1:3]).abs().sum(1) / 0.15) / 4
            if not args.no_global:
                g = torch.tensor([global_fit(o, d, float(p), dev) + (float(p),) for o, d, p in zip(ob, Dt, p0[:, 3])], dtype=torch.float32, device=dev)
                pg = refine(A, ob, img, g, dev, iters=6); ag = iou(depth_batch(ob, pg, dev) > 0.05, m_main)
            else:
                ag = torch.full((n,), float("nan"), device=dev)
        dm = d_main.cpu().numpy()
        for j, it in enumerate(its):
            ti, tl = quality(dm[j], np.where(Dt[j] > 0.05, Dt[j], 0.0))[0], float(np.abs(dm[j] - Dt[j]).mean())
            it.update(c_last=float(last[j]), agree_jit=float(aj[j]), spread_jit=float(sp[j]), agree_glob=float(ag[j]), teach_iou=ti, teach_l1=tl)
            if it["gt"]:
                Pg = json.load(open(it["gt"])); gt = np.load(it["gt"].replace("_pose.json", "_gt.npy")) * 1000
                q = quality(dm[j], gt); it.update(t_iou=q[0], t_cmae=q[1], t_rot=rot_err(it["al"][0], Pg["rotation_euler"][2], period(it["obj"])),
                                                  t_trans=(abs(it["al"][1] - Pg["sample_x"] * 1e3) + abs(it["al"][2] - Pg["sample_y"] * 1e3)) / 2)
        if (k0 // 64) % 10 == 0:
            print(f"  {k0}/{len(items)}", flush=True)
    pct = lambda v: (rankdata(v) - 1) / max(1, len(v) - 1)  # noqa: E731
    sigs = ["c_last", "agree_jit", "spread_jit", "agree_glob", "teach_iou", "teach_l1", "render_err"]
    comb = [pct([it["agree_jit"] for it in items]), pct([it["teach_iou"] for it in items]), 1 - pct([it["c_last"] for it in items])]
    if not args.no_global:
        comb.append(pct([it["agree_glob"] for it in items]))
    conf = np.mean(comb, 0)
    for it, c in zip(items, conf):
        it["conf"] = float(c)
    ev = [it for it in items if it["gt"] and not np.isnan(it.get("t_cmae", np.nan))]
    res = {"n": len(items), "n_eval": len(ev), "spearman": {}}
    print(f"\nSpearman rho with the true label error ({len(ev)} frames with a reference label)\n{'signal':12s} {'cMAE':>7s} {'1-IoU':>7s} {'rot':>7s}")
    for s in sigs + ["conf"]:
        v = np.array([it[s] for it in ev])
        if np.isnan(v).all():
            continue
        r = [float(spearmanr(v, [it[k] for it in ev]).correlation) for k in ("t_cmae", "t_iou", "t_rot")]; r[1] = -r[1]
        res["spearman"][s] = dict(cmae=r[0], one_minus_iou=r[1], rot=r[2]); print(f"{s:12s} {r[0]:7.3f} {r[1]:7.3f} {r[2]:7.3f}")
    # what filtering buys in label quality (global ranking)
    print("\nlabel quality of the kept fraction (IoU / cMAE / rot):")
    res["filter"] = {}
    order = {"conf": np.argsort([-it["conf"] for it in ev]), "oracle": np.argsort([it["t_cmae"] for it in ev]), "random": np.random.RandomState(0).permutation(len(ev))}
    for name, o in order.items():
        res["filter"][name] = {}
        for fr in (1.0, 0.9, 0.75, 0.5):
            k = [ev[i] for i in o[:int(round(len(ev) * fr))]]
            res["filter"][name][str(fr)] = dict(iou=float(np.mean([it["t_iou"] for it in k])), cmae=float(np.mean([it["t_cmae"] for it in k])), rot=float(np.mean([it["t_rot"] for it in k])))
        print(f"  {name:7s} " + "  ".join(f"{fr:.2f}: {v['iou']:.3f}/{v['cmae']:.3f}/{v['rot']:.2f}" for fr, v in ((float(a), b) for a, b in res["filter"][name].items())))
    res["frames"] = [{k: it.get(k) for k in ["tac", "obj"] + sigs + ["conf", "t_iou", "t_cmae", "t_rot", "t_trans"]} for it in items]
    res["args"] = vars(args)
    json.dump(res, open(args.out, "w"))
    if args.fits_dir:
        os.makedirs(args.fits_dir, exist_ok=True); rnd = np.random.RandomState(0).rand(len(items))
        for name, key in (("conf", lambda it, i: -it["conf"]), ("rand", lambda it, i: float(rnd[i])), ("oracle", lambda it, i: it.get("t_cmae", 0.0))):
            json.dump({it["tac"]: dict(pose=list(it["al"][:3]), p=float(it["al"][3]), err=float(key(it, i)), tp=list(it["tp"])) for i, it in enumerate(items)},
                      open(osp.join(args.fits_dir, f"fits_{name}.json"), "w"))
    print("->", args.out)


if __name__ == "__main__":
    main()
