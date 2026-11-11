"""RSS round 2b: OBSERVABILITY-AWARE run-level fusion (session 1; registered poses are calibration-based).
For every touch the mesh itself tells which pose directions the touch can observe: with J = d(mesh depth)/d(theta, x, y) at the aligned
state, the Gauss-Newton information matrix is W = J^T J (a structure tensor; an extruded ridge gives rank-deficient W along the ridge).
Fusing the per-touch corrections e_i of one placement in information form,   c = (sum_i s_i W_i)^-1 sum_i s_i W_i e_i,
uses only the component each touch can see (s_i: Cauchy robust weights), instead of the plain median of rss2_run_consensus_s1.py.
Also reports how well the analytic observability predicts the per-touch translation error (Spearman).
usage: python ablation/pilot_robosoft/rss2_obs_fusion.py --al-root <pseudo root> --real-root <root> --out <json> [--aligner a.pt --range-scale s]
"""
import argparse, json, math, os, os.path as osp, sys
import numpy as np, torch
from concurrent.futures import ProcessPoolExecutor
ROOT = osp.dirname(osp.dirname(osp.dirname(osp.abspath(__file__))))
sys.path.insert(0, ROOT); sys.path.insert(0, osp.join(ROOT, "scripts")); sys.path.insert(0, osp.join(ROOT, "scripts", "tactile_render")); sys.path.insert(0, osp.dirname(osp.abspath(__file__)))
from fit_baselines import B, load_frames, score, summarize, fmt, SYM  # noqa: E402


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def info(a):
    """3x3 information matrix of (theta [rad], x [mm], y [mm]) from finite differences of the mesh depth at the given state."""
    obj, th, x, y, p = a
    B.get_zmap(obj)
    J = []
    for d in ((math.radians(0.5), 0, 0), (0, 0.1, 0), (0, 0, 0.1)):
        hi = B.gt_depth_mm(obj, th + d[0], x + d[1], y + d[2], p); lo = B.gt_depth_mm(obj, th - d[0], x - d[1], y - d[2], p)
        J.append(((hi - lo) / (2 * max(d))).ravel()[::4])
    J = np.stack(J, 1).astype(np.float64)
    return J.T @ J


def spearman(a, b):
    ra = np.argsort(np.argsort(a)); rb = np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def fuse(E, W, iters=8):
    """E [n,3] corrections, W [n,3,3] information. Robust information-form mean."""
    Wn = W / np.trace(W, axis1=1, axis2=2).mean()                      # scale-free
    c = np.median(E, 0); s = np.ones(len(E)); d = E.shape[1]
    for _ in range(iters):
        A = (s[:, None, None] * Wn).sum(0) + 1e-6 * np.eye(d); b = (s[:, None] * np.einsum("nij,nj->ni", Wn, E)).sum(0)
        c = np.linalg.solve(A, b)
        r = E - c; q = np.einsum("ni,nij,nj->n", r, Wn, r)
        s = 1.0 / (1.0 + q / max(np.median(q), 1e-9) / 4.0)
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--al-root", required=True); ap.add_argument("--real-root", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--aligner", default=None, help="re-run this aligner from the teacher pose instead of reading rc_fits.json"); ap.add_argument("--range-scale", type=float, default=1.0)
    ap.add_argument("--write-fits", default=None, help="json: hybrid-fusion labels in rc_fits format (plus *_pertouch.json)")
    ap.add_argument("--n-touches", default="3,5,10,20,50"); ap.add_argument("--trials", type=int, default=20); ap.add_argument("--workers", type=int, default=24); ap.add_argument("--device", default="cuda:0")
    args = ap.parse_args(); os.chdir(ROOT)
    sym = json.load(open(SYM)) if osp.exists(SYM) else {}
    period = lambda o: sym.get(o, {}).get("period_deg", 360.0)  # noqa: E731
    items = load_frames(args.al_root, args.real_root, None, 1)
    objs = sorted({it["obj"] for it in items})
    for o in objs:
        B.get_zmap(o)
    if args.aligner:
        import train_aligner as TA; TA.SCALE = TA.SCALE * args.range_scale
        from rss2_loo3_diag import run_aligner
        A = TA.Aligner().to(args.device).eval(); A.load_state_dict(torch.load(args.aligner, map_location=args.device))
        inits = [it["tp"] + (float(np.clip(np.load(it["dep"]).max() * 1000, 0.3, 1.6)),) for it in items]
        for it, a in zip(items, run_aligner(A, items, inits, args.device)):
            it["al"] = a
    with ProcessPoolExecutor(args.workers) as ex:
        Ws = np.array(list(ex.map(info, [(it["obj"],) + tuple(it["al"]) for it in items], chunksize=16)))
    idx = {o: [i for i, it in enumerate(items) if it["obj"] == o] for o in objs}
    E = np.array([[wrap(it["al"][0] - it["gt_pose"][0]), it["al"][1] - it["gt_pose"][1], it["al"][2] - it["gt_pose"][2]] for it in items])
    dp = np.array([it["al"][3] - it["gt_pose"][3] for it in items])
    def labels(est):
        return [tuple(np.array(it["gt_pose"]) + np.append(est[it["obj"]], np.median(dp[idx[it["obj"]]]))) for it in items]
    def rep(name, ps):
        rows = [score(it, p, period(it["obj"])) for it, p in zip(items, ps)]
        s = summarize(rows); print(fmt(name, s), flush=True)
        return dict(summary=s, per_object={o: summarize([rows[i] for i in idx[o]]) for o in objs})
    out = {"args": vars(args), "n": len(items)}
    out["per-touch"] = rep("per-touch", [it["al"] for it in items])
    med = {o: np.median(E[idx[o]], 0) for o in objs}; inf = {o: fuse(E[idx[o]], Ws[idx[o]]) for o in objs}
    out["fusion median"] = rep("fusion median", labels(med)); out["fusion information"] = rep("fusion info", labels(inf))
    # hybrid: rotation is observable in every touch -> median; translation -> information form on the 2x2 translation block
    hyb = {o: np.append(med[o][0], fuse(E[idx[o]][:, 1:], Ws[idx[o]][:, 1:, 1:])) for o in objs}
    out["fusion hybrid"] = rep("fusion hybrid", labels(hyb))
    if args.write_fits:
        os.makedirs(osp.dirname(args.write_fits) or ".", exist_ok=True)
        json.dump({it["tac"]: dict(pose=[float(v) for v in p[:3]], p=float(p[3]), err=0.0, tp=list(it["tp"])) for it, p in zip(items, labels(hyb))}, open(args.write_fits, "w"))
        json.dump({it["tac"]: dict(pose=[float(v) for v in it["al"][:3]], p=float(it["al"][3]), err=0.0, tp=list(it["tp"])) for it in items}, open(args.write_fits.replace(".json", "_pertouch.json"), "w"))
    out["placement"] = {}
    for o in objs:
        f = lambda c: f"{math.degrees(c[0]):+.2f} deg ({c[1]:+.2f}, {c[2]:+.2f}) mm"  # noqa: E731
        out["placement"][o] = dict(median=med[o].tolist(), information=inf[o].tolist(), n=len(idx[o]))
        print(f"  {o[8:]:26s} n={len(idx[o]):4d} placement error  median: {f(med[o])}   information: {f(inf[o])}")
    # observability as a label-free confidence: weakest translation eigenvalue of W (relative) vs the true per-touch translation error
    ev = np.linalg.eigvalsh(Ws[:, 1:, 1:]); aniso = ev[:, 0] / np.maximum(ev[:, 1], 1e-12); terr = np.hypot(E[:, 1], E[:, 2])
    out["observability"] = dict(spearman_lmin_vs_trans_err=spearman(-ev[:, 0], terr), spearman_aniso_vs_trans_err=spearman(-aniso, terr),
                                trans_err_by_aniso_quartile=[float(terr[(aniso >= a) & (aniso <= b)].mean()) for a, b in zip(np.quantile(aniso, [0, .25, .5, .75]), np.quantile(aniso, [.25, .5, .75, 1]))])
    print(f"  observability vs per-touch translation error: Spearman {out['observability']['spearman_lmin_vs_trans_err']:.2f} (min eigenvalue), {out['observability']['spearman_aniso_vs_trans_err']:.2f} (eigenvalue ratio); "
          f"mean trans error by observability quartile (worst->best): {[round(v, 2) for v in out['observability']['trans_err_by_aniso_quartile']]}")
    rng = np.random.RandomState(0); out["n_touches"] = {}
    for n in [int(v) for v in args.n_touches.split(",")]:
        r = {"median": [], "information": []}
        for _ in range(args.trials):
            for o in objs:
                j = np.array(idx[o])[rng.choice(len(idx[o]), min(n, len(idx[o])), replace=False)]
                for k, c in (("median", np.median(E[j], 0)), ("information", np.append(np.median(E[j], 0)[0], fuse(E[j][:, 1:], Ws[j][:, 1:, 1:])))):
                    r[k].append((abs(math.degrees(c[0])), (abs(c[1]) + abs(c[2])) / 2))
        out["n_touches"][str(n)] = {k: dict(rot=float(np.mean([v[0] for v in r[k]])), trans=float(np.mean([v[1] for v in r[k]])), trans_p90=float(np.percentile([v[1] for v in r[k]], 90))) for k in r}
        print(f"  {n:3d} touches: median {out['n_touches'][str(n)]['median']['rot']:.2f} deg / {out['n_touches'][str(n)]['median']['trans']:.2f} mm (p90 {out['n_touches'][str(n)]['median']['trans_p90']:.2f})"
              f"   information {out['n_touches'][str(n)]['information']['rot']:.2f} deg / {out['n_touches'][str(n)]['information']['trans']:.2f} mm (p90 {out['n_touches'][str(n)]['information']['trans_p90']:.2f})")
    json.dump(out, open(args.out, "w"), indent=1); print("->", args.out)


if __name__ == "__main__":
    main()
