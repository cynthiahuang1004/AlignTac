"""Session-1 labels vs image-to-image motion: fit alternative conversions (scratch)."""
import sys, json, math, glob, random
import numpy as np, cv2
sys.path.insert(0, "rss2_recapture")
import rss2_recapture_check as R
from concurrent.futures import ProcessPoolExecutor

def load(root, o, sess, idx):
    u = f"{root}/{o}/{sess}/sensor_0000"; p = json.load(open(f"{u}/raw_data/{idx}_pose.json"))
    im = cv2.cvtColor(cv2.imread(f"{u}/samples/{idx}.png"), cv2.COLOR_BGR2RGB)
    return {"theta": p["rotation_euler"][2], "c": np.array([p["sample_x"], -p["sample_y"]]) * 1000, "ridge": R.ridge(im)}

def job(a):
    root, o, sess, i, j = a
    pa, pb = load(root, o, sess, i), load(root, o, sess, j)
    dth, dx, dy, s0, s1 = R.register(pa, pb)
    th0 = pb["theta"] - pa["theta"]; c, s = math.cos(th0), math.sin(th0)
    t0 = pb["c"] - np.array([c * pa["c"][0] - s * pa["c"][1], s * pa["c"][0] + c * pa["c"][1]])
    d = math.radians(dth); cc, ss = math.cos(d), math.sin(d)
    t_obs = np.array([cc * t0[0] - ss * t0[1], ss * t0[0] + cc * t0[1]]) + [dx, dy]
    return dict(obj=o, i=i, j=j, dth=dth, unexpl=[dx, dy], s1=s1, th_a=pa["theta"], th_b=pb["theta"], c_a=pa["c"].tolist(), c_b=pb["c"].tolist(),
                dth_obs=th0 + d, t_obs=t_obs.tolist())

if __name__ == "__main__":
    root, n, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]; random.seed(1); jobs = []
    for o in sys.argv[4:]:
        sess = sorted(glob.glob(f"{root}/{o}/session_*"))[0]
        ids = sorted(p.split("/")[-1][:4] for p in glob.glob(f"{sess}/sensor_0000/samples/*.png"))
        P = {i: json.load(open(f"{sess}/sensor_0000/raw_data/{i}_pose.json")) for i in ids}
        k = 0; tries = 0
        while k < n and tries < 50000:
            tries += 1; i, j = random.sample(ids, 2)
            d = math.hypot(P[i]["sample_x"] - P[j]["sample_x"], P[i]["sample_y"] - P[j]["sample_y"]) * 1000
            if d < 5.0:
                jobs.append((root, o, sess.split("/")[-1], i, j)); k += 1
    with ProcessPoolExecutor(12) as ex:
        rows = list(ex.map(job, jobs, chunksize=4))
    json.dump(rows, open(out, "w")); print(len(rows))
