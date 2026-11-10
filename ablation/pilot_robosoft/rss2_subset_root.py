"""Frame-level subset of a pseudo-label root (symlinks only; nothing in the source root is modified).

Pool frames = entries of the source root's pseudo_manifest.json with kind "mesh" or "pseudo".  Labeled (K) frames, validation
links and all session metadata are always kept.  Two ways to choose the pool frames that stay:
  --fits F --keep-frac f   per object, keep the fraction f with the LOWEST "err" in F (rc_fits format; rss2_confidence.py writes
                           fits_conf.json = -confidence, fits_rand.json = random, fits_oracle.json = true contact MAE)
  --pool-frac f [--seed s] per object, a fixed random fraction f of the pool (unlabeled-data quantity study).  With --like R
                           the frames kept in root R (its rss2_subset.json) are reused, so two label types share the same subset.
usage: python ablation/pilot_robosoft/rss2_subset_root.py --src $G/real_pseudo_k25_ro_al --out $G/real_pseudo_k25_ro_al_conf75 --fits fits_conf.json --keep-frac 0.75
"""
import argparse, glob, json, os, os.path as osp, shutil
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--src", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--fits", default=None); ap.add_argument("--keep-frac", type=float, default=None)
ap.add_argument("--pool-frac", type=float, default=None); ap.add_argument("--seed", type=int, default=0); ap.add_argument("--like", default=None)
args = ap.parse_args()
rel = lambda tac: "/".join(tac.split("/")[-5:-2]) + "/" + osp.basename(tac)[:4]  # noqa: E731  obj/session/sensor/idx
man = json.load(open(osp.join(args.src, "pseudo_manifest.json")))["manifest"]
pool = sorted({rel(t) for t, k, _ in man if k in ("mesh", "pseudo")})
by_obj = {}
for r in pool:
    by_obj.setdefault(r.split("/")[0], []).append(r)
keep = set()
if args.like:
    keep = set(json.load(open(osp.join(args.like, "rss2_subset.json")))["kept"]) & set(pool)
elif args.fits:
    err = {rel(t): v["err"] for t, v in json.load(open(args.fits)).items()}
    for o, L in by_obj.items():
        L = sorted(L, key=lambda r: err[r]); keep.update(L[:int(round(len(L) * args.keep_frac))])
else:
    rng = np.random.RandomState(args.seed)
    for o, L in sorted(by_obj.items()):
        keep.update(np.array(L)[rng.permutation(len(L))[:int(round(len(L) * args.pool_frac))]].tolist())
drop = set(pool) - keep
shutil.rmtree(args.out, ignore_errors=True); n = 0
for unit in sorted(glob.glob(osp.join(args.src, "*", "session_*", "sensor_0000"))):
    ou = unit.replace(args.src, args.out); os.makedirs(osp.join(ou, "samples")); os.makedirs(osp.join(ou, "raw_data"))
    for name in ("rgb", "calibration", "id_map.json"):
        if osp.lexists(osp.join(unit, name)):
            os.symlink(osp.realpath(osp.join(unit, name)), osp.join(ou, name))
    if osp.lexists(osp.join(osp.dirname(unit), "session.json")):
        os.symlink(osp.realpath(osp.join(osp.dirname(unit), "session.json")), osp.join(osp.dirname(ou), "session.json"))
    base = "/".join(unit.split("/")[-3:])
    for png in sorted(os.listdir(osp.join(unit, "samples"))):
        idx = png[:4]
        if f"{base}/{idx}" in drop:
            continue
        for sub, fn in (("samples", png), ("raw_data", idx + "_gt.npy"), ("raw_data", idx + "_pose.json")):
            s = osp.join(unit, sub, fn)
            if osp.lexists(s):
                os.symlink(osp.realpath(s), osp.join(ou, sub, fn))
        n += 1
json.dump({"src": args.src, "args": vars(args), "pool": len(pool), "kept": sorted(keep), "dropped": len(drop)}, open(osp.join(args.out, "rss2_subset.json"), "w"))
print(f"{args.out}: pool {len(pool)} -> kept {len(keep)} ({len(drop)} dropped); {n} frames linked in total")
