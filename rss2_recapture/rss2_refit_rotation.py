"""Object constants for a session-2 object with a full search over the plate rotation (line patterns have near-symmetric wrong optima that a
local search from the nominal angle can fall into).  usage: python rss2_recapture/rss2_refit_rotation.py <object> <out.json>"""
import sys, json, math, numpy as np
from concurrent.futures import ProcessPoolExecutor
from scipy.optimize import minimize
sys.path.insert(0, "rss2_recapture"); import rss2_relabel_full as Fu
R = Fu.R; obj = sys.argv[1]; sc = R.SENSOR["s2"]

def prep():
    fr = Fu.frames_raw_s2(obj)
    for f in fr:
        f["ridge"] = R.ridge(Fu.read224(f["img"])); f["rmask"] = f["ridge"] > 0.25
    use = [f for f in fr if f["press"] >= 0.6 and f["rmask"].mean() >= 0.04]
    return use

def coarse(dth):
    use = prep(); sub = use[::max(1, len(use) // 40)]; prior = np.array(sub[0]["prior"]); best = (-1, None)
    for dx in np.arange(-5, 5.01, 0.5):
        for dy in np.arange(-5, 5.01, 0.5):
            p = np.array([dth, prior[0] + dx, prior[1] + dy]); v = R.score(obj, sub, p, sc)
            if v > best[0]: best = (v, p.tolist())
    return best

if __name__ == "__main__":
    with ProcessPoolExecutor(24) as ex:
        res = list(ex.map(coarse, list(np.arange(-180, 180, 7.5))))
    res.sort(key=lambda t: -t[0]); use = prep(); groups = sorted(set(f["group"] for f in use)); ga = set(groups[0::2])
    A = [f for f in use if f["group"] in ga]; Bh = [f for f in use if f["group"] not in ga]; out = []
    for v, p in res[:5]:
        f = lambda q, fr: -R.score(obj, fr, q, sc)
        r = minimize(f, p, args=(use,), method="Powell", options={"xtol": 1e-2, "ftol": 1e-5})
        ra = minimize(f, r.x, args=(A,), method="Powell", options={"xtol": 1e-2, "ftol": 1e-5})
        out.append({"coarse": v, "constants": r.x.tolist(), "ncc_all": -r.fun, "ncc_heldout": R.score(obj, Bh, ra.x, sc)})
        print(f"start dtheta {p[0]:+7.1f}: constants {np.round(r.x, 2).tolist()} NCC all {-r.fun:.3f} held-out {out[-1]['ncc_heldout']:.3f}", flush=True)
    out.sort(key=lambda t: -t["ncc_heldout"]); json.dump({"obj": obj, "n_frames": len(use), "candidates": out}, open(sys.argv[2], "w"), indent=1)
