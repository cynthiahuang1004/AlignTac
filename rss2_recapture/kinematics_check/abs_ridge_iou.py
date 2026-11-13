"""Absolute check: does re-rotating the label translation with the tool yaw make the mesh agree better with the image?  (scratch)
label pose (theta, c_L) -> corrected c = R(theta - theta_off) (c_L + k), k = one constant per object, fitted on half of the frames."""
import sys, json, math, glob, random
import numpy as np, cv2
sys.path.insert(0, "scripts"); sys.path.insert(0, "/media/hdd/ihsuan/gs_blender")
from build_real_filtered_new import gt_depth_mm
from calibrate_new_real_poses import blackhat_mask
from concurrent.futures import ProcessPoolExecutor
OFF = math.radians(90)

def crop(im):
    H = im.shape[0]; c = int(round(H * 0.816)); a = (H - c) // 2
    return cv2.resize(im[a:a + c, a:a + c], (224, 224), interpolation=cv2.INTER_LINEAR)

def iou(a, b):
    return (a & b).sum() / max(1, (a | b).sum())

def run(a):
    root, o, n = a; random.seed(0)
    fr = []
    for sess in sorted(glob.glob(f"{root}/{o}/session_*")):
        u = f"{sess}/sensor_0000"
        for p in sorted(glob.glob(f"{u}/raw_data/*_pose.json")):
            fr.append((u, p.split("/")[-1][:4]))
    random.shuffle(fr); fr = fr[:n]; D = []
    for u, i in fr:
        p = json.load(open(f"{u}/raw_data/{i}_pose.json"))
        m = blackhat_mask(crop(cv2.cvtColor(cv2.imread(f"{u}/samples/{i}.png"), cv2.COLOR_BGR2RGB)))
        g = np.load(f"{u}/raw_data/{i}_gt.npy") > 0
        D.append(dict(th=p["rotation_euler"][2], c=np.array([p["sample_x"], -p["sample_y"]]) * 1000, press=p["sample_z"] * 1000, m=m, g=g))
    def mask(d, k, rot=True):
        c = d["c"] + k
        if rot:
            a = d["th"] - OFF; c = np.array([math.cos(a) * c[0] - math.sin(a) * c[1], math.sin(a) * c[0] + math.cos(a) * c[1]])
        return gt_depth_mm(o, d["th"], c[0], -c[1], max(d["press"], 0.3)) > 0
    def mean_iou(idx, k, rot):
        return float(np.mean([iou(D[i]["m"], mask(D[i], k, rot)) for i in idx]))
    fit, test = list(range(0, len(D), 2)), list(range(1, len(D), 2))
    res = {"obj": o, "n": len(D), "stored": float(np.mean([iou(D[i]["m"], D[i]["g"]) for i in test])),
           "rerender_stored": float(np.mean([iou(D[i]["g"], mask(D[i], np.zeros(2), False)) for i in test]))}
    for rot in (False, True):
        best = (-1, None)
        for step, span in ((1.0, 8.0), (0.25, 1.0), (0.05, 0.25)):
            c0 = best[1] if best[1] is not None else np.zeros(2)
            for dx in np.arange(-span, span + 1e-9, step):
                for dy in np.arange(-span, span + 1e-9, step):
                    k = c0 + [dx, dy]; v = mean_iou(fit, k, rot)
                    if v > best[0]: best = (v, k)
        res["rot" if rot else "norot"] = dict(k=best[1].round(2).tolist(), fit=best[0], test=mean_iou(test, best[1], rot))
    return res

if __name__ == "__main__":
    root, n = sys.argv[1], int(sys.argv[2])
    with ProcessPoolExecutor(4) as ex:
        for r in ex.map(run, [(root, o, n) for o in sys.argv[3:]]):
            print(f"{r['obj']} ({r['n']} frames; held-out half): ridge-mask IoU of stored label {r['stored']:.3f} (re-render check {r['rerender_stored']:.2f}) | "
                  f"current form + best constant {r['norot']['test']:.3f} (k {r['norot']['k']}) | yaw-rotated + best constant {r['rot']['test']:.3f} (k {r['rot']['k']})", flush=True)
