"""Observed press-to-press image motion vs robot motion: which kinematic model explains it?  (scratch analysis)"""
import sys, json, math, itertools, glob, pickle, os
import numpy as np
sys.path.insert(0, "rss2_recapture")
import rss2_recapture_check as R
from concurrent.futures import ProcessPoolExecutor

def run_pairs(run):
    P = R.presses(run); rows = []
    for a, b in itertools.combinations(sorted(P), 2):
        pa, pb = P[a], P[b]
        dth, dx, dy, s0, s1 = R.register(pa, pb)
        th0 = pb["theta"] - pa["theta"]; c, s = math.cos(th0), math.sin(th0)
        t0 = pb["c"] - np.array([c * pa["c"][0] - s * pa["c"][1], s * pa["c"][0] + c * pa["c"][1]])
        d = math.radians(dth); cc, ss = math.cos(d), math.sin(d)
        t_obs = np.array([cc * t0[0] - ss * t0[1], ss * t0[0] + cc * t0[1]]) + [dx, dy]
        rows.append(dict(run=run, a=a, b=b, th_a=pa["theta"], th_b=pb["theta"], dth_obs=th0 + d, t_obs=t_obs.tolist(),
                         de=((np.array(pb["ee"][:2]) - np.array(pa["ee"][:2])) * 1000).tolist(), ee_a=pa["ee"], ee_b=pb["ee"], s1=s1, unexpl=[dx, dy], dth=dth))
    return rows

if __name__ == "__main__":
    out = sys.argv[1]; runs = sys.argv[2:]
    with ProcessPoolExecutor(12) as ex:
        rows = [r for rr in ex.map(run_pairs, runs) for r in rr]
    json.dump(rows, open(out, "w"))
    print(len(rows), "pairs")
