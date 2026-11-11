"""RSS round 2b: an OBJECTIVE session-2 reference.  The curated session-2 labels are per-frame mask-IoU fits (+ visual review).
Here every run gets ONE rigid correction of the recorded robot poses, estimated from all curated frames of the run:
  reference_i = recorded_i (session-1 calibration) + c_run,   c_run = robust consensus_j (curated_j - recorded_j).
For the label of frame i the frames of the same press are left out, so a frame's reference never depends on its own per-frame fit.
Reports: which rigid model the offsets follow (constant in state space vs rotating with theta), within-run scatter (= per-frame fit
noise), split-half agreement of c_run (= uncertainty of the reference), agreement of both references with the image (black-hat ridge
mask, an evidence the per-frame fits were not tuned on), and writes mirrored roots <root>_rigid.
usage: python ablation/pilot_robosoft/rss2_s2_rigid_gt.py [--write]
"""
import argparse, collections, glob, json, math, os, os.path as osp, sys
import numpy as np
from PIL import Image
ROOT = osp.dirname(osp.dirname(osp.dirname(osp.abspath(__file__))))
sys.path.insert(0, ROOT); sys.path.insert(0, osp.join(ROOT, "scripts")); sys.path.insert(0, osp.join(ROOT, "scripts", "tactile_render")); sys.path.insert(0, osp.dirname(osp.abspath(__file__)))
import fit_baselines as FB  # noqa: E402
from fit_baselines import B, oldcal_pose, quality  # noqa: E402
from s2_consensus import consensus, wrap  # noqa: E402
from calibrate_new_real_poses import blackhat_mask  # noqa: E402
G = "/media/hdd/ihsuan/gs_blender"; CUR = f"{G}/real_filtered_new_curated_pred_r2_fv"


def frames(root):
    out = []
    for pj in sorted(glob.glob(f"{root}/*/session_*/sensor_0000/raw_data/*_pose.json")):
        P = json.load(open(pj)); unit = osp.dirname(osp.dirname(pj)); idx = osp.basename(pj)[:4]; oc = oldcal_pose(pj)
        out.append(dict(pj=pj, unit=unit, idx=idx, obj=P["obj_name"], run=(P["obj_name"], str(P["source"]["run"])), press=int(P["source"]["iteration"]), frame=int(P["source"]["frame"]),
                        cur=(P["rotation_euler"][2], P["sample_x"] * 1e3, P["sample_y"] * 1e3, P["sample_z"] * 1e3), oc=oc, P=P))
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--write", action="store_true"); ap.add_argument("--out", default="ablation/pilot_robosoft/rss2_s2_rigid_gt.json")
    args = ap.parse_args(); os.chdir(ROOT)
    sym = json.load(open(FB.SYM)); period = lambda o: sym.get(o, {}).get("period_deg", 360.0)  # noqa: E731
    F = frames(CUR)
    for o in sorted({f["obj"] for f in F}):
        B.get_zmap(o)
    for f in F:
        f["off"] = np.array([wrap(math.degrees(f["cur"][0] - f["oc"][0]), period(f["obj"])), f["cur"][1] - f["oc"][1], f["cur"][2] - f["oc"][2], f["cur"][3] - f["oc"][3]])
    runs = collections.defaultdict(list)
    for f in F:
        runs[f["run"]].append(f)
    res = {"n_frames": len(F), "n_runs": len(runs)}
    # sanity: the stored reference depth is reproduced from its pose
    d = [float(np.abs(B.gt_depth_mm(f["obj"], *f["cur"]) - np.load(f["pj"].replace("_pose.json", "_gt.npy")) * 1e3).max()) for f in F[::20]]
    res["rerender_max_abs_diff_mm"] = float(np.max(d)); print(f"{len(F)} curated frames, {len(runs)} runs; re-render check: max |diff| {np.max(d):.2e} mm")
    # ---- which rigid model?  A: constant (dx, dy);  B+/B-: R(+-theta) d;  C+/C-: constant + R(+-theta) d
    def fit(its, model):
        th = np.array([f["cur"][0] for f in its]); y = np.array([f["off"][1:3] for f in its]).reshape(-1)
        cols = []
        if model in ("A", "C+", "C-"):
            cols += [np.tile([1, 0], len(its)), np.tile([0, 1], len(its))]
        if model != "A":
            s = 1 if model.endswith("+") else -1; c_, s_ = np.cos(s * th), np.sin(s * th)
            cols += [np.stack([c_, s_], 1).reshape(-1), np.stack([-s_, c_], 1).reshape(-1)]
        X = np.stack(cols, 1); w = np.ones(len(y))
        for _ in range(5):                                             # IRLS (Cauchy)
            beta = np.linalg.lstsq(X * w[:, None], y * w, rcond=None)[0]; r = y - X @ beta
            w = 1 / np.sqrt(1 + (r / max(1.4826 * np.median(np.abs(r)), 1e-3) / 2.4) ** 2)
        return r.reshape(-1, 2)
    res["model"] = {}
    for m in ("A", "B+", "B-", "C+", "C-"):
        R = np.concatenate([fit(its, m) for its in runs.values() if len(its) >= 8]); mag = np.hypot(R[:, 0], R[:, 1])
        res["model"][m] = dict(median=float(np.median(mag)), rms_inlier=float(np.sqrt(np.mean(mag[mag < np.percentile(mag, 90)] ** 2))))
        print(f"  rigid model {m:2s}: translation residual median {np.median(mag):.2f} mm, rms (best 90%) {res['model'][m]['rms_inlier']:.2f} mm")
    th_span = [math.degrees(np.ptp([f["cur"][0] for f in its])) for its in runs.values()]
    res["theta_span_deg_median"] = float(np.median(th_span)); print(f"  rotation span within a run: median {np.median(th_span):.0f} deg")
    # ---- within-run scatter and split-half agreement
    sc, sh = [], []
    for r, its in runs.items():
        O = np.array([f["off"] for f in its]); est, inl = consensus(O, period(its[0]["obj"]))
        resid = O - est; resid[:, 0] = wrap(resid[:, 0], period(its[0]["obj"]))
        sc.append([1.4826 * np.median(np.abs(resid[:, 0])), 1.4826 * np.median(np.hypot(resid[:, 1], resid[:, 2])), float(inl.mean())])
        pr = sorted({f["press"] for f in its}); a = [f for f in its if pr.index(f["press"]) % 2 == 0]; b = [f for f in its if pr.index(f["press"]) % 2 == 1]
        if len(a) >= 4 and len(b) >= 4:
            ea = consensus(np.array([f["off"] for f in a]), period(its[0]["obj"]))[0]; eb = consensus(np.array([f["off"] for f in b]), period(its[0]["obj"]))[0]
            sh.append([abs(wrap(ea[0] - eb[0], period(its[0]["obj"]))), math.hypot(ea[1] - eb[1], ea[2] - eb[2]), len(its)])
    sc, sh = np.array(sc), np.array(sh)
    res["within_run_scatter"] = dict(rot_deg_median=float(np.median(sc[:, 0])), trans_mm_median=float(np.median(sc[:, 1])), inlier_frac=float(sc[:, 2].mean()))
    res["split_half"] = dict(n_runs=len(sh), rot_median=float(np.median(sh[:, 0])), rot_mean=float(sh[:, 0].mean()), rot_p90=float(np.percentile(sh[:, 0], 90)),
                             trans_median=float(np.median(sh[:, 1])), trans_mean=float(sh[:, 1].mean()), trans_p90=float(np.percentile(sh[:, 1], 90)))
    print(f"  within-run scatter of (curated - recorded): rot {np.median(sc[:, 0]):.2f} deg, trans {np.median(sc[:, 1]):.2f} mm (robust std, median over runs); inliers {100 * sc[:, 2].mean():.0f}%")
    s = res["split_half"]; print(f"  split-half agreement of the run correction ({len(sh)} runs): rot median {s['rot_median']:.2f} / mean {s['rot_mean']:.2f} / p90 {s['rot_p90']:.2f} deg; "
                                 f"trans median {s['trans_median']:.2f} / mean {s['trans_mean']:.2f} / p90 {s['trans_p90']:.2f} mm  -> uncertainty of the full-run correction ~ half of these")
    # ---- rigid reference (leave-one-press-out) for a frame list
    def rigid(f):
        its = [g for g in runs[f["run"]] if g["press"] != f["press"]]
        if len(its) < 4:
            its = runs[f["run"]]
        est = consensus(np.array([g["off"] for g in its]), period(f["obj"]))[0]
        return (f["oc"][0] + math.radians(est[0]), f["oc"][1] + est[1], f["oc"][2] + est[2], f["cur"][3]), len(its)
    # ---- agreement with the image (black-hat ridge mask) and between the two references
    rows = []
    for f in F:
        f["rig"], f["n_ref"] = rigid(f)
        im = np.asarray(Image.open(osp.join(f["unit"], "samples", f["idx"] + ".png")).convert("RGB")); m = blackhat_mask(im)
        dc, dr, do = (B.gt_depth_mm(f["obj"], *p) for p in (f["cur"], f["rig"], f["oc"]))
        iou = lambda a, b: float((a & b).sum() / max(1, (a | b).sum()))  # noqa: E731
        rows.append(dict(obj=f["obj"], bh_ok=bool(m.mean() >= 0.01), bh_cur=iou(m, dc > 0), bh_rig=iou(m, dr > 0), bh_old=iou(m, do > 0), cur_vs_rig=quality(dr, dc)[0],
                         drot=abs(wrap(math.degrees(f["rig"][0] - f["cur"][0]), period(f["obj"]))), dtrans=math.hypot(f["rig"][1] - f["cur"][1], f["rig"][2] - f["cur"][2])))
    ok = [r for r in rows if r["bh_ok"]]
    res["image_agreement"] = dict(n=len(ok), curated=float(np.mean([r["bh_cur"] for r in ok])), rigid=float(np.mean([r["bh_rig"] for r in ok])), recorded=float(np.mean([r["bh_old"] for r in ok])))
    res["curated_vs_rigid"] = dict(iou=float(np.mean([r["cur_vs_rig"] for r in rows])), rot_median=float(np.median([r["drot"] for r in rows])), rot_mean=float(np.mean([r["drot"] for r in rows])),
                                   trans_median=float(np.median([r["dtrans"] for r in rows])), trans_mean=float(np.mean([r["dtrans"] for r in rows])))
    a = res["image_agreement"]; c = res["curated_vs_rigid"]
    print(f"  black-hat mask IoU ({a['n']} frames): per-frame curated {a['curated']:.3f} | rigid per run {a['rigid']:.3f} | recorded pose (stale calibration) {a['recorded']:.3f}")
    print(f"  curated vs rigid reference: depth-mask IoU {c['iou']:.3f}; pose difference rot median {c['rot_median']:.2f} / mean {c['rot_mean']:.2f} deg, trans median {c['trans_median']:.2f} / mean {c['trans_mean']:.2f} mm")
    res["per_object"] = {o: dict(n=sum(r["obj"] == o for r in rows), bh_cur=float(np.mean([r["bh_cur"] for r in ok if r["obj"] == o] or [np.nan])), bh_rig=float(np.mean([r["bh_rig"] for r in ok if r["obj"] == o] or [np.nan])),
                                 cur_vs_rig=float(np.mean([r["cur_vs_rig"] for r in rows if r["obj"] == o])), dtrans=float(np.median([r["dtrans"] for r in rows if r["obj"] == o]))) for o in sorted({r["obj"] for r in rows})}
    for o, v in res["per_object"].items():
        print(f"    {o[8:]:24s} n={v['n']:3d}  black-hat IoU curated {v['bh_cur']:.2f} / rigid {v['bh_rig']:.2f}   curated-vs-rigid IoU {v['cur_vs_rig']:.2f}, trans diff {v['dtrans']:.2f} mm")
    json.dump(res, open(args.out, "w"), indent=1); print("->", args.out)
    if not args.write:
        return
    for name in ("real_s2_testhalf", "real_s2_poolcheck"):
        src, dst = f"{G}/{name}", f"{G}/{name}_rigid"; n = 0
        if osp.exists(dst):
            print(f"{dst} exists, not overwritten"); continue
        for f in frames(src):
            if f["run"] not in runs:
                continue
            ou = f["unit"].replace(src, dst); os.makedirs(f"{ou}/raw_data", exist_ok=True)
            for nm in os.listdir(f["unit"]):
                if nm != "raw_data" and not osp.lexists(f"{ou}/{nm}"):
                    os.symlink(osp.realpath(f"{f['unit']}/{nm}"), f"{ou}/{nm}")
            sj = osp.join(osp.dirname(f["unit"]), "session.json")
            if osp.exists(sj) and not osp.lexists(osp.join(osp.dirname(ou), "session.json")):
                os.symlink(osp.realpath(sj), osp.join(osp.dirname(ou), "session.json"))
            pose, nref = rigid(f); P = dict(f["P"])
            P["rotation_euler"] = [P["rotation_euler"][0], P["rotation_euler"][1], float(pose[0])]; P["sample_x"] = float(pose[1] * 1e-3); P["sample_y"] = float(pose[2] * 1e-3)
            if "location" in P:
                P["location"] = [P["sample_x"], -P["sample_y"], P["location"][2]]
            P["source"] = dict(P["source"], reference="rigid per run, leave-one-press-out", n_ref_frames=nref, curated_pose=[float(v) for v in f["cur"]])
            json.dump(P, open(f"{ou}/raw_data/{f['idx']}_pose.json", "w"))
            np.save(f"{ou}/raw_data/{f['idx']}_gt.npy", (B.gt_depth_mm(f["obj"], *pose) * 1e-3).astype(np.float32)); n += 1
        print(f"{n} frames -> {dst}")


if __name__ == "__main__":
    main()
