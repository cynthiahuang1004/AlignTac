"""Session-level registration from many touches (RSS round 2, P2-8) + conventional (old-calibration) labels (P0-3).

After re-placement the object pose error is (to first order) one planar offset per run, while the robot's recorded motion
between presses stays accurate.  For every session-2 pool press we have
  old-calibration state   recorded robot pose + SESSION-1 calibration (fit_baselines.oldcal_pose; no per-run correction)
  aligned state           teacher pose + learned aligner on that press alone (rc_fits.json of real_pseudo_s2_k{K}_al)
Per press the implied placement offset is  aligned - old-calibration  (theta, x, y, press).  Step A: within-run spread, robust
consensus per run (median, then mean of the inliers), comparison with the manual per-run correction
(new_real_test/validation/pose_calibration_new.json; never used to compute the consensus), and consensus error vs the number of presses.
Step B (labels): consensus state = old-calibration + run consensus for EVERY press (also those the aligner failed on);
optionally refined again by the aligner from that start ("consensus + aligner").  Label quality is scored on the pool frames
that have a curated label (real_s2_poolcheck).  Fits are written in the rc_fits.json format for pseudo_label_rc.py --fits.

usage: python ablation/pilot_robosoft/s2_consensus.py --k 25 [--device cuda:0]
"""
import argparse, collections, glob, json, math, os, os.path as osp, sys
import numpy as np, torch
from PIL import Image
ROOT = osp.dirname(osp.dirname(osp.dirname(osp.abspath(__file__))))
sys.path.insert(0, ROOT); sys.path.insert(0, osp.join(ROOT, "scripts")); sys.path.insert(0, osp.join(ROOT, "scripts", "tactile_render"))
import fit_baselines as FB  # noqa: E402
from fit_baselines import B, oldcal_pose, quality, rot_err  # noqa: E402

G = "/media/hdd/ihsuan/gs_blender"


def wrap(d, period=360.0):
    return (d + period / 2) % period - period / 2


def circ_median(deg, period):
    """Median of angles (deg) modulo `period`: the sample minimizing the summed wrapped distance, refined by the median around it."""
    a = np.asarray(deg, float)
    c = a[np.argmin([np.abs(wrap(a - x, period)).sum() for x in a])]
    return float(c + np.median(wrap(a - c, period)))


def consensus(off, period, thr=(3.0, 0.5)):
    """off [n, 4] (dtheta deg, dx, dy, dp) -> robust estimate: component-wise (circular) median, then mean over the inliers."""
    off = np.asarray(off, float)
    med = np.array([circ_median(off[:, 0], period), np.median(off[:, 1]), np.median(off[:, 2]), np.median(off[:, 3])])
    inl = (np.abs(wrap(off[:, 0] - med[0], period)) < thr[0]) & (np.abs(off[:, 1] - med[1]) < thr[1]) & (np.abs(off[:, 2] - med[2]) < thr[1])
    if inl.sum() >= 3:
        est = np.array([med[0] + wrap(off[inl, 0] - med[0], period).mean(), off[inl, 1].mean(), off[inl, 2].mean(), off[inl, 3].mean()])
    else:
        est = med
    return est, inl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=25)
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--out", default=None)
    ap.add_argument("--fits-dir", default=None)
    args = ap.parse_args()
    os.chdir(ROOT); K = args.k; dev = args.device
    out = args.out or f"ablation/pilot_robosoft/rss2_s2_consensus_k{K}.json"
    fits_dir = args.fits_dir or f"outputs/rss2_fits/s2_k{K}"
    al_root = f"{G}/real_pseudo_s2_k{K}_al"; pool = f"{G}/real_s2_pool"
    fits = json.load(open(f"{al_root}/rc_fits.json"))
    sym = json.load(open(FB.SYM)); period = lambda o: sym.get(o, {}).get("period_deg", 360.0)  # noqa: E731
    manual = json.load(open(f"{B.T}/validation/pose_calibration_new.json"))
    sim2real = {v[0]: k for k, v in B.OBJ_MAP.items()}
    gtmap = {}
    for pj in glob.glob(f"{G}/real_s2_poolcheck/*/session_*/sensor_0000/raw_data/*_pose.json"):
        d = json.load(open(pj)); gtmap[(pj.split("/")[-5], pj.split("/")[-4], int(d["source"]["frame"]))] = pj
    items = []
    for tac in sorted(fits):
        unit = osp.dirname(osp.dirname(tac)); idx = osp.basename(tac)[:4]; obj = unit.split("/")[-3]; sess = unit.split("/")[-2]
        pj = osp.join(unit, "raw_data", idx + "_pose.json"); src = json.load(open(pj))["source"]
        oc = oldcal_pose(pj); f = fits[tac]; al = tuple(f["pose"]) + (f["p"],)
        off = (wrap(math.degrees(al[0] - oc[0])), al[1] - oc[1], al[2] - oc[2], al[3] - oc[3])
        items.append(dict(tac=tac, obj=obj, sess=sess, run=f"{sim2real[obj]}/{src['run']}", press=(src["run"], src["iteration"]), oc=oc, al=al, off=off,
                          tp=tuple(f["tp"]), gt=gtmap.get((obj, sess, int(src["frame"])))))
    runs = collections.defaultdict(list)
    for it in items:
        runs[it["run"]].append(it)
    for o in sorted({it["obj"] for it in items}):
        B.get_zmap(o)
    from train_aligner import Aligner, refine
    Aln = Aligner().to(dev).eval(); Aln.load_state_dict(torch.load(f"outputs/aligner_k{K}_realonly/aligner.pt", map_location=dev))

    def align(key_in, key_out):
        for k0 in range(0, len(items), 64):
            its = items[k0:k0 + 64]
            img = torch.from_numpy(np.stack([np.array(Image.open(it["tac"]).convert("RGB"), np.float32).transpose(2, 0, 1) / 127.5 - 1 for it in its])).to(dev)
            pz = refine(Aln, [it["obj"] for it in its], img, torch.tensor([it[key_in] for it in its], dtype=torch.float32, device=dev), dev, iters=6)
            for j, it in enumerate(its):
                it[key_out] = tuple(pz[j].tolist())

    def offsets(its, key):
        return np.array([(wrap(math.degrees(it[key][0] - it["oc"][0])), it[key][1] - it["oc"][1], it[key][2] - it["oc"][2], it[key][3] - it["oc"][3]) for it in its])

    def run_consensus(key, out_key, inl_key):
        est_all = {}
        for run, its in runs.items():
            est, inl = consensus(offsets(its, key), period(its[0]["obj"]))
            est_all[run] = est
            for it, i in zip(its, inl):
                it[out_key] = (it["oc"][0] + math.radians(est[0]), it["oc"][1] + est[1], it["oc"][2] + est[2], float(np.clip(it["oc"][3] + est[3], 0.3, 1.6)))
                it[inl_key] = bool(i)
        return est_all

    # reference placement offset per run: median of (curated label - recorded pose) over ALL curated frames of the run
    ref = collections.defaultdict(list)
    for pj in glob.glob(f"{G}/real_filtered_new_curated_pred_r2_fv/*/session_*/sensor_0000/raw_data/*_pose.json"):
        Pg = json.load(open(pj)); obj = pj.split("/")[-5]; oc = oldcal_pose(pj)
        ref[f"{sim2real[obj]}/{Pg['source']['run']}"].append((wrap(math.degrees(Pg["rotation_euler"][2] - oc[0])), Pg["sample_x"] * 1e3 - oc[1], Pg["sample_y"] * 1e3 - oc[2], 0.0))
    ref = {k: consensus(np.array(v), period(runs[k][0]["obj"]))[0] for k, v in ref.items() if len(v) >= 5 and k in runs}

    def stepA(est_all, title):
        rows = []
        for run, est in sorted(est_all.items()):
            its = runs[run]; P = period(its[0]["obj"]); r = dict(run=run, n=len(its), est=[float(v) for v in est])
            if run in ref:
                r.update(ref=[float(v) for v in ref[run][:3]], err_rot=float(abs(wrap(est[0] - ref[run][0], P))), err_trans=float(math.hypot(est[1] - ref[run][1], est[2] - ref[run][2])))
            rows.append(r)
        wm = [r for r in rows if "err_rot" in r]
        A = dict(n_runs=len(rows), n_with_ref=len(wm), err_rot_median=float(np.median([r["err_rot"] for r in wm])), err_rot_mean=float(np.mean([r["err_rot"] for r in wm])),
                 err_trans_median=float(np.median([r["err_trans"] for r in wm])), err_trans_mean=float(np.mean([r["err_trans"] for r in wm])),
                 within_2deg_05mm=float(np.mean([(r["err_rot"] < 2) and (r["err_trans"] < 0.5) for r in wm])), within_2deg_1mm=float(np.mean([(r["err_rot"] < 2) and (r["err_trans"] < 1.0) for r in wm])),
                 within_5deg_1mm=float(np.mean([(r["err_rot"] < 5) and (r["err_trans"] < 1.0) for r in wm])), rows=rows)
        print(f"Step A [{title}]: run consensus vs curated reference over {len(wm)} runs: rot median {A['err_rot_median']:.2f} mean {A['err_rot_mean']:.2f} deg | trans median {A['err_trans_median']:.2f} "
              f"mean {A['err_trans_mean']:.2f} mm | within 2deg/0.5mm {100 * A['within_2deg_05mm']:.0f}%, 2deg/1mm {100 * A['within_2deg_1mm']:.0f}%, 5deg/1mm {100 * A['within_5deg_1mm']:.0f}%")
        return A

    refm = np.array([[abs(v[0]), math.hypot(v[1], v[2])] for v in ref.values()])
    print(f"K={K}: {len(items)} pool frames, {len(runs)} runs, {len(ref)} with a curated reference; recorded-pose drift (curated - recorded, run medians): "
          f"mean {refm[:, 0].mean():.2f} deg / {refm[:, 1].mean():.2f} mm, median {np.median(refm[:, 0]):.2f} deg / {np.median(refm[:, 1]):.2f} mm")
    res = {"drift": dict(rot_mean=float(refm[:, 0].mean()), trans_mean=float(refm[:, 1].mean()), rot_median=float(np.median(refm[:, 0])), trans_median=float(np.median(refm[:, 1])), n_runs=len(ref))}
    # (1) teacher-initialized aligner (the paper's session-2 labels)
    res["A_teacher_init"] = stepA(run_consensus("al", "cons_t", "inl_t"), "teacher init -> aligner")
    # (2) aligner started from the recorded pose (stale calibration)
    align("oc", "al_oc")
    res["A_recorded_init"] = stepA(run_consensus("al_oc", "cons", "inl"), "recorded pose -> aligner")
    # (3) second pass: aligner restarted from the run consensus, consensus again, gate
    align("cons", "cons_al")
    res["A_second_pass"] = stepA(run_consensus("cons_al", "cons2", "inl2"), "consensus -> aligner -> consensus")
    for it in items:
        it["hybrid"] = it["cons_al"] if it["inl2"] else it["cons2"]
    # consensus error vs number of presses (recorded-pose init)
    rng = np.random.RandomState(0); curve = collections.defaultdict(list)
    for run, its in runs.items():
        if run not in ref:
            continue
        P = period(its[0]["obj"]); off = offsets(its, "al_oc")
        for n in (1, 2, 3, 5, 8, 12, 20):
            if n <= len(its):
                for _ in range(50):
                    e, _i = consensus(off[rng.choice(len(its), n, replace=False)], P)
                    curve[n].append((abs(wrap(e[0] - ref[run][0], P)), math.hypot(e[1] - ref[run][1], e[2] - ref[run][2])))
    res["curve"] = {str(n): dict(rot_median=float(np.median([c[0] for c in v])), trans_median=float(np.median([c[1] for c in v])),
                                 within_2deg_1mm=float(np.mean([(c[0] < 2) and (c[1] < 1.0) for c in v]))) for n, v in sorted(curve.items())}
    for n, c in res["curve"].items():
        print(f"  frames per run {n:>2s}: rot {c['rot_median']:.2f} deg, trans {c['trans_median']:.2f} mm, within 2deg/1mm {100 * c['within_2deg_1mm']:.0f}%")
    variants = {"old calibration (recorded pose)": "oc", "teacher -> aligner (paper)": "al", "recorded -> aligner": "al_oc", "run consensus": "cons",
                "consensus -> aligner": "cons_al", "run consensus (2nd pass)": "cons2", "consensus-gated aligner": "hybrid"}
    gts = [it for it in items if it["gt"]]
    print(f"\nStep B: label quality on {len(gts)} pool frames with a curated label")
    res["stepB"] = {}; per_frame = {}
    for name, key in variants.items():
        rws = []
        for it in gts:
            Pg = json.load(open(it["gt"])); g = (Pg["rotation_euler"][2], Pg["sample_x"] * 1e3, Pg["sample_y"] * 1e3, Pg["sample_z"] * 1e3)
            gt = np.load(it["gt"].replace("_pose.json", "_gt.npy")) * 1000; th, x, y, p = it[key]
            iou, cmae = quality(B.gt_depth_mm(it["obj"], th, x, y, p), gt)
            rws.append(dict(iou=iou, cmae=cmae, rot=rot_err(th, g[0]), rot_sym=rot_err(th, g[0], period(it["obj"])), trans=(abs(x - g[1]) + abs(y - g[2])) / 2, dp=abs(p - g[3])))
        res["stepB"][name] = FB.summarize(rws); per_frame[name] = rws; print(FB.fmt(name[:18], res["stepB"][name]) + "  <- " + name)
    # confidence: does agreement with the run consensus predict the per-press label error?  (recorded -> aligner states)
    from scipy.stats import spearmanr
    dev_c = [abs(wrap(math.degrees(it["al_oc"][0] - it["cons"][0]), period(it["obj"]))) / 3.0 + math.hypot(it["al_oc"][1] - it["cons"][1], it["al_oc"][2] - it["cons"][2]) / 0.75 for it in gts]
    res["confidence"] = dict(spearman_dev_vs_cmae=float(spearmanr(dev_c, [r["cmae"] for r in per_frame["recorded -> aligner"]]).correlation),
                             spearman_dev_vs_iou=float(spearmanr(dev_c, [r["iou"] for r in per_frame["recorded -> aligner"]]).correlation),
                             inlier_frac=float(np.mean([it["inl"] for it in items])), inlier2_frac=float(np.mean([it["inl2"] for it in items])))
    inl_g = np.array([it["inl"] for it in gts]); cm = np.array([r["cmae"] for r in per_frame["recorded -> aligner"]]); io = np.array([r["iou"] for r in per_frame["recorded -> aligner"]])
    print(f"confidence (deviation from run consensus) vs label error: Spearman rho {res['confidence']['spearman_dev_vs_cmae']:.2f} (cMAE), {res['confidence']['spearman_dev_vs_iou']:.2f} (IoU); "
          f"inliers {inl_g.mean():.2f}: IoU {io[inl_g].mean():.3f} / cMAE {cm[inl_g].mean():.3f}   outliers: IoU {io[~inl_g].mean():.3f} / cMAE {cm[~inl_g].mean():.3f}")
    os.makedirs(fits_dir, exist_ok=True)
    for name, key in (("oldcal", "oc"), ("recal", "al_oc"), ("consal", "cons_al"), ("consensus", "cons2"), ("consgate", "hybrid")):
        json.dump({it["tac"]: dict(pose=list(it[key][:3]), p=float(it[key][3]), err=0.0 if it["inl2"] else 1.0, tp=list(it["tp"])) for it in items},
                  open(osp.join(fits_dir, f"fits_{name}_all.json"), "w"))
    res["args"] = vars(args)
    json.dump(res, open(out, "w"), indent=1)
    print("->", out, "| fits in", fits_dir)


if __name__ == "__main__":
    main()
