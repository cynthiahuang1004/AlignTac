"""RSS round 2b: observability-aware fusion on the REAL second session (K = 25; pool = 1,066 frames, recorded poses with the stale
session-1 calibration, no recalibration, no session-2 label).  Per run:
  e_i = aligned_i - recorded_i                      (aligner started from the recorded pose, or from the teacher)
  c   = rotation: circular median;  translation: information form  (sum s_i W_i)^-1 sum s_i W_i e_i,  W_i = J^T J of the mesh depth
  rigid label_i = recorded_i + c
  MAP label_i   = argmin_x (x - aligned_i)^T Wn_i (x - aligned_i) + rho^-1 |x - (recorded_i + c)|^2      (Wn_i: W_i / its largest eigenvalue)
The MAP label keeps the touch's own evidence where the touch can see and takes the run estimate where it cannot; rho is the assumed
variance ratio (placement non-rigidity : per-touch noise).  Scored on the 162 pool frames with a curated label.
usage: python ablation/pilot_robosoft/rss2_s2_fusion.py [--init recal|teacher] [--rho 1.0]
"""
import argparse, collections, glob, json, math, os, os.path as osp, sys
import numpy as np
from concurrent.futures import ProcessPoolExecutor
ROOT = osp.dirname(osp.dirname(osp.dirname(osp.abspath(__file__))))
sys.path.insert(0, ROOT); sys.path.insert(0, osp.join(ROOT, "scripts")); sys.path.insert(0, osp.join(ROOT, "scripts", "tactile_render")); sys.path.insert(0, osp.dirname(osp.abspath(__file__)))
import fit_baselines as FB  # noqa: E402
from fit_baselines import B, quality, rot_err  # noqa: E402
from s2_consensus import circ_median, wrap  # noqa: E402
from rss2_obs_fusion import adaptive_map, fuse, info  # noqa: E402
G = "/media/hdd/ihsuan/gs_blender"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=25); ap.add_argument("--init", default="recal", choices=["recal", "teacher"]); ap.add_argument("--rho", type=float, default=0.0, help="<= 0: adaptive MAP labels are written")
    ap.add_argument("--workers", type=int, default=12); ap.add_argument("--out", default=None)
    args = ap.parse_args(); os.chdir(ROOT); K = args.k; fd = f"outputs/rss2_fits/s2_k{K}"
    out = args.out or f"ablation/pilot_robosoft/rss2_s2_fusion_k{K}_{args.init}.json"
    sym = json.load(open(FB.SYM)); period = lambda o: sym.get(o, {}).get("period_deg", 360.0)  # noqa: E731
    OC = json.load(open(f"{fd}/fits_oldcal_all.json")); AL = json.load(open(f"{fd}/fits_recal_all.json")) if args.init == "recal" else json.load(open(f"{G}/real_pseudo_s2_k{K}_al/rc_fits.json"))
    gtmap = {}
    for pj in glob.glob(f"{G}/real_s2_poolcheck/*/session_*/sensor_0000/raw_data/*_pose.json"):
        d = json.load(open(pj)); gtmap[(pj.split("/")[-5], pj.split("/")[-4], int(d["source"]["frame"]))] = pj
    items = []
    for tac in sorted(OC):
        unit = osp.dirname(osp.dirname(tac)); idx = osp.basename(tac)[:4]; obj = unit.split("/")[-3]; sess = unit.split("/")[-2]
        src = json.load(open(osp.join(unit, "raw_data", idx + "_pose.json")))["source"]
        items.append(dict(tac=tac, obj=obj, run=(obj, str(src["run"])), oc=np.array(list(OC[tac]["pose"]) + [OC[tac]["p"]]), al=np.array(list(AL[tac]["pose"]) + [AL[tac]["p"]]),
                          tp=list(OC[tac]["tp"]), gt=gtmap.get((obj, sess, int(src["frame"])))))
    for o in sorted({it["obj"] for it in items}):
        B.get_zmap(o)
    with ProcessPoolExecutor(args.workers) as ex:
        Ws = list(ex.map(info, [(it["obj"],) + tuple(it["al"]) for it in items], chunksize=16))
    runs = collections.defaultdict(list)
    for it, w in zip(items, Ws):
        it["W"] = w[1:, 1:]; runs[it["run"]].append(it)
    for run, its in runs.items():
        P = period(its[0]["obj"]); e = np.array([[wrap(math.degrees(it["al"][0] - it["oc"][0]), P), it["al"][1] - it["oc"][1], it["al"][2] - it["oc"][2], it["al"][3] - it["oc"][3]] for it in its])
        cth = circ_median(e[:, 0], P); cmed = np.median(e[:, 1:3], 0); cinf = fuse(e[:, 1:3], np.array([it["W"] for it in its])) if len(its) >= 3 else cmed; cp = np.median(e[:, 3])
        for it, ei in zip(its, e):
            th_run = it["oc"][0] + math.radians(cth); p_run = float(np.clip(it["oc"][3] + cp, 0.3, 1.6))
            it["rigid median"] = np.array([th_run, it["oc"][1] + cmed[0], it["oc"][2] + cmed[1], p_run])
            it["rigid information"] = np.array([th_run, it["oc"][1] + cinf[0], it["oc"][2] + cinf[1], p_run])
            ev = np.linalg.eigvalsh(it["W"]); Wn = it["W"] / max(ev[1], 1e-12); prior = it["rigid information"][1:3]
            th = it["al"][0] if abs(wrap(ei[0] - cth, P)) < 3.0 else th_run                     # rotation: the touch's own unless it disagrees with the run
            for rho in (0.25, 1.0, 4.0, 16.0):
                x = np.linalg.solve(Wn + np.eye(2) / rho, Wn @ it["al"][1:3] + prior / rho)
                it[f"MAP rho={rho:g}"] = np.array([th, x[0], x[1], it["al"][3]])
            it["per touch"] = it["al"]; it["recorded (stale calibration)"] = it["oc"]; it["_th"] = th
        x, sr = adaptive_map(np.array([it["al"][1:3] for it in its]), np.array([it["rigid information"][1:3] for it in its]), np.array([it["W"] for it in its]))
        for it, xi in zip(its, x):
            it["adaptive MAP"] = np.array([it["_th"], xi[0], xi[1], it["al"][3]]); it["sigma_r"] = sr
    gts = [it for it in items if it["gt"]]; res = {"n": len(items), "n_gt": len(gts), "args": vars(args)}
    names = ["recorded (stale calibration)", "per touch", "rigid median", "rigid information", "MAP rho=0.25", "MAP rho=1", "MAP rho=4", "MAP rho=16", "adaptive MAP"]
    print(f"K={K}, aligner start = {args.init}: {len(items)} pool frames, {len(runs)} runs; scored on {len(gts)} frames with a curated label")
    for name in names:
        rws = []
        for it in gts:
            Pg = json.load(open(it["gt"])); g = (Pg["rotation_euler"][2], Pg["sample_x"] * 1e3, Pg["sample_y"] * 1e3, Pg["sample_z"] * 1e3)
            th, x, y, p = it[name]; iou, cmae = quality(B.gt_depth_mm(it["obj"], th, x, y, p), np.load(it["gt"].replace("_pose.json", "_gt.npy")) * 1000)
            rws.append(dict(iou=iou, cmae=cmae, rot=rot_err(th, g[0]), rot_sym=rot_err(th, g[0], period(it["obj"])), trans=(abs(x - g[1]) + abs(y - g[2])) / 2, dp=abs(p - g[3]), obj=it["obj"]))
        res[name] = FB.summarize(rws); res[name]["per_object"] = {o: FB.summarize([r for r in rws if r["obj"] == o]) for o in sorted({r["obj"] for r in rws})}
        print(FB.fmt(name[:18], res[name]) + "  <- " + name, flush=True)
    sr = [its[0]["sigma_r"] for its in runs.values()]; res["sigma_r"] = dict(median=float(np.median(sr)), q25=float(np.percentile(sr, 25)), q75=float(np.percentile(sr, 75)))
    print(f"  estimated non-rigidity sigma_r per run: median {np.median(sr):.2f} mm (IQR {np.percentile(sr, 25):.2f}-{np.percentile(sr, 75):.2f})")
    key = "adaptive MAP" if args.rho <= 0 else f"MAP rho={args.rho:g}"
    json.dump({it["tac"]: dict(pose=[float(v) for v in it[key][:3]], p=float(it[key][3]), err=0.0, tp=it["tp"]) for it in items}, open(f"{fd}/fits_obsf_{args.init}_all.json", "w"))
    json.dump({it["tac"]: dict(pose=[float(v) for v in it["rigid information"][:3]], p=float(it["rigid information"][3]), err=0.0, tp=it["tp"]) for it in items}, open(f"{fd}/fits_obsfrigid_{args.init}_all.json", "w"))
    json.dump(res, open(out, "w"), indent=1); print("->", out)


if __name__ == "__main__":
    main()
