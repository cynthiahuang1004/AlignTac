"""Session 1 from the raw capture (teammate's folder, read only): (1) do the stored labels come from render_gt_blender_ortho.py's formula on this
raw data?  (2) press pairs straight from the raw robot poses and raw images, ALL pressed samples (also those the filter deleted): old vs new formula.
usage (AlignTac root): python rss2_recapture/kinematics_check/s1_raw_check.py <out.json> <real_name:sim_name> ..."""
import sys, json, math, glob, random, os
import numpy as np, cv2
sys.path.insert(0, "rss2_recapture")
import rss2_recapture_check as R
from concurrent.futures import ProcessPoolExecutor
X = "/media/hdd2/xiangdong/gelslim_depth"; G = "/media/hdd/ihsuan/gs_blender"
BATCH = {b["real_name"]: b for b in json.load(open(f"{X}/data/batch_config.json"))}
CAL = json.load(open(f"{X}/data/pose_calibration.json"))["objects"]

def raw(real):
    tp = json.load(open(f"{X}/data/tactile_image/{real}/tactile_poses.json"))
    full = {str(i["sample_id"]): i for i in json.load(open(f"{X}/data/pose/{real}.json")) if i["robot_state"] == "pressed_pose"}
    return tp, full

def old_label(real, p, full):
    """render_gt_blender_ortho.py, lines 228-237 and 286-290."""
    oc = full[next(iter(full))]["object_center_coord"]; d = np.array(p[:2]) - [oc["x"], oc["y"]]
    th = -2 * math.atan2(p[3], p[4]) + math.radians(BATCH[real].get("theta_offset_deg", 0.0))
    mx = d[1] + CAL[real]["bias_x_mm"] / 1000; my = d[0] + CAL[real]["bias_y_mm"] / 1000
    return th, mx, -my

def job(a):
    real, sa, sb = a; tp, full = raw(real); out = {}
    P = []
    for s in (sa, sb):
        im = cv2.resize(cv2.cvtColor(cv2.imread(f"{X}/data/tactile_image/{real}/{s}.jpg"), cv2.COLOR_BGR2RGB), (224, 224), interpolation=cv2.INTER_AREA)
        p = tp[s]; oc = full[s]["object_center_coord"]; d = (np.array(p[:2]) - [oc["x"], oc["y"]]) * 1000
        P.append({"theta": -2 * math.atan2(p[3], p[4]), "c": np.array([d[1], d[0]]), "ridge": R.ridge(im)})
    dth, dx, dy, s0, s1 = R.register(P[0], P[1])                       # prediction = old formula (object constants cancel only if the yaw is equal; added below)
    th0 = P[1]["theta"] - P[0]["theta"]; c, s = math.cos(th0), math.sin(th0)
    t0 = P[1]["c"] - np.array([c * P[0]["c"][0] - s * P[0]["c"][1], s * P[0]["c"][0] + c * P[0]["c"][1]])
    r = math.radians(dth); t_obs = np.array([math.cos(r) * t0[0] - math.sin(r) * t0[1], math.sin(r) * t0[0] + math.cos(r) * t0[1]]) + [dx, dy]
    b = np.array([CAL[real]["bias_x_mm"], CAL[real]["bias_y_mm"]]); Rd = np.array([[c, -s], [s, c]])
    t_old = (P[1]["c"] + b) - Rd @ (P[0]["c"] + b)                     # old formula incl. its object constant
    yb = P[1]["theta"]; Rb = np.array([[math.cos(yb), -math.sin(yb)], [math.sin(yb), math.cos(yb)]])
    t_new = Rb @ (P[1]["c"] - P[0]["c"])                               # new formula, no free parameter (eps = 0, lever = 0)
    return dict(real=real, a=sa, b=sb, s1=s1, yaw_a=math.degrees(P[0]["theta"]), yaw_b=math.degrees(yb), shift=float(np.linalg.norm(P[1]["c"] - P[0]["c"])),
                err_old=float(np.linalg.norm(t_obs - t_old)), err_new=float(np.linalg.norm(t_obs - t_new)), drot=float(dth))

if __name__ == "__main__":
    out = sys.argv[1]; random.seed(0); jobs = []; rep = {}
    for spec in sys.argv[2:]:
        real, sim = spec.split(":"); tp, full = raw(real)
        # (1) stored labels vs the formula on the raw data
        u = f"{G}/real_filtered/{sim}/session_000/sensor_0000"; idm = json.load(open(f"{u}/id_map.json")); dd = []; same = 0; nimg = 0
        for k, (idx, sid) in enumerate(sorted(idm.items())):
            pj = f"{u}/raw_data/{idx}_pose.json"
            if not os.path.exists(pj) or sid not in tp:
                continue
            j = json.load(open(pj)); th, sx, sy = old_label(real, np.array(tp[sid], float), full)
            dd.append([abs(j["rotation_euler"][2] - th), abs(j["sample_x"] - sx) * 1000, abs(j["sample_y"] - sy) * 1000])
            if k % 40 == 0:
                a = cv2.imread(f"{u}/samples/{idx}.png").astype(float); b = cv2.resize(cv2.imread(f"{X}/data/tactile_image/{real}/{sid}.jpg"), (224, 224)).astype(float)
                nimg += 1; same += float(np.abs(a - b).mean() < 3.0)
        dd = np.array(dd)
        rep[sim] = {"pressed_samples_raw": len(full), "frames_in_real_filtered": len(glob.glob(f"{u}/raw_data/*_pose.json")), "matched": len(dd),
                    "max_abs_diff": {"theta_rad": float(dd[:, 0].max()), "x_mm": float(dd[:, 1].max()), "y_mm": float(dd[:, 2].max())}, "images_same": f"{int(same)}/{nimg}"}
        print(sim, rep[sim], flush=True)
        ids = [s for s in full if s in tp and os.path.exists(f"{X}/data/tactile_image/{real}/{s}.jpg")]; n = 0; tries = 0
        while n < 150 and tries < 100000:
            tries += 1; a, b = random.sample(ids, 2)
            if np.linalg.norm(np.array(tp[a][:2]) - np.array(tp[b][:2])) * 1000 < 5.0:
                jobs.append((real, a, b)); n += 1
    with ProcessPoolExecutor(12) as ex:
        rows = list(ex.map(job, jobs, chunksize=4))
    ok = [r for r in rows if r["s1"] >= 0.7]
    st = lambda v: "median %.2f mean %.2f p90 %.2f mm" % (np.median(v), np.mean(v), np.percentile(v, 90))
    print(f"\nraw press pairs, all pressed samples: {len(ok)}/{len(rows)} reliable; yaw range {min(r['yaw_b'] for r in ok):.0f}..{max(r['yaw_b'] for r in ok):.0f} deg")
    print("  old formula (as in render_gt_blender_ortho.py):", st([r["err_old"] for r in ok]))
    print("  new formula (translation rotated by the yaw, no free parameter):", st([r["err_new"] for r in ok]))
    ya = np.abs([r["yaw_b"] for r in ok]); eo = np.array([r["err_old"] for r in ok]); en = np.array([r["err_new"] for r in ok])
    for lo, hi in ((0, 10), (10, 20), (20, 30), (30, 46)):
        m = (ya >= lo) & (ya < hi)
        if m.sum(): print(f"  |yaw| {lo:2d}-{hi:2d} deg ({m.sum():3d} pairs): old {np.median(eo[m]):.2f} mm, new {np.median(en[m]):.2f} mm")
    json.dump({"labels_vs_formula": rep, "pairs": rows}, open(out, "w"))
