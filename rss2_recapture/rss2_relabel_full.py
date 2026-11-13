"""All captured presses of both sessions with the corrected labels: which frames are usable?  (scan -> per-frame table; build -> new roots)

Sources: session 1 = raw capture /media/hdd2/xiangdong/gelslim_depth/data (every pressed sample; real_filtered holds the 4,669 that survived the
old IoU filter); session 2 = new_real_test (every contact frame, stride 3 inside a press as in build_real_filtered_new.py).
Per frame: corrected pose (constants of rss2_relabel.py; nothing per frame), ridge evidence in the image (fraction of ridge pixels), label
coverage (fraction of contact pixels), agreement of the two (NCC).  A frame is usable when the image shows a ridge, the label has contact
and the two agree; frames without a pressed ridge (background) are dropped.

usage (AlignTac root):
  python rss2_recapture/rss2_relabel_full.py scan  --out rss2_recapture/full_scan.json
  python rss2_recapture/rss2_relabel_full.py build --scan rss2_recapture/full_scan.json --session s1|s2 --out-root <root> [--only-new]
"""
import argparse, collections, glob, json, math, os, os.path as osp, sys
from concurrent.futures import ProcessPoolExecutor
import cv2
import numpy as np

sys.path.insert(0, osp.dirname(osp.abspath(__file__)))
import rss2_relabel as R            # noqa: E402
B = R.B
X = "/media/hdd2/xiangdong/gelslim_depth"
BATCH = {b["sim_name"]: b for b in json.load(open(f"{X}/data/batch_config.json"))}
CAL = json.load(open(f"{X}/data/pose_calibration.json"))["objects"]
HERE = osp.dirname(osp.abspath(__file__))
NCC_MIN, RIDGE_MIN, LABEL_MIN = 0.45, 0.02, 0.01


def read224(path):
    im = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB)
    return im if im.shape[:2] == (224, 224) else cv2.resize(im, (224, 224), interpolation=cv2.INTER_LINEAR)


def frames_raw_s1(obj):
    real = BATCH[obj]["real_name"]; off = math.radians(BATCH[obj].get("theta_offset_deg", 0.0))
    tp = json.load(open(f"{X}/data/tactile_image/{real}/tactile_poses.json"))
    full = {str(i["sample_id"]): i for i in json.load(open(f"{X}/data/pose/{real}.json")) if i["robot_state"] == "pressed_pose"}
    kept = {}
    for p in glob.glob(f"{R.S1_ROOT}/{obj}/session_000/sensor_0000/raw_data/*_pose.json"):
        kept[str(json.load(open(p))["original_sample_id"])] = osp.basename(p)[:4]
    bias = np.array([CAL[real]["bias_x_mm"], CAL[real]["bias_y_mm"]]); out = []
    for sid in sorted(full, key=int):
        img = f"{X}/data/tactile_image/{real}/{sid}.jpg"
        if sid not in tp or not osp.exists(img):
            continue
        p = tp[sid]; oc = full[sid]["object_center_coord"]; d = (np.array(p[:2]) - [oc["x"], oc["y"]]) * 1000
        cL = np.array([d[1], d[0]]) + bias; yaw = -2 * math.atan2(p[3], p[4])
        out.append({"img": img, "rgb": f"{X}/data/rgb_image/{real}/{sid}_off.jpg", "sid": sid, "yaw": yaw, "off": off, "cL": cL.tolist(),
                    "press": full[sid]["press_depth"] * 1000, "old": [yaw + off, cL[0], cL[1]], "in_old_root": kept.get(sid)})
    return out


def frames_raw_s2(obj):
    real = R.SIM2REAL[obj]; off = B.OBJ_MAP[real][1]; bias = np.array(B.OBJ_MAP[real][2:]) * 1000; out = []
    cur = set()
    for p in glob.glob(f"{R.S2_ROOT}/{obj}/session_*/sensor_0000/raw_data/*_pose.json"):
        s = json.load(open(p))["source"]; cur.add((str(s["run"]), s["frame"]))
    for run in sorted((d for d in os.listdir(f"{B.T}/{real}") if d.isdigit()), key=int):
        tpj = f"{B.T}/{real}/{run}/tactile_images/poses.json"
        if not osp.exists(tpj):
            continue
        m = json.load(open(tpj)); cz = m["contact_z_m"]; k = 0; prev = False
        for f in m["frames"]:
            if abs(f["pose_ros_timestamp_sec"] - f["image_ros_timestamp_sec"]) > 0.5:
                continue
            e = f["robot_pose_xyz_xyzw"]; press = (cz - e[2]) * 1000
            if press < 0.3:
                prev = False; continue
            k = k + 1 if prev else 0; prev = True
            if k % 3 and (run, f["frame_id"]) not in cur:
                continue
            d = (np.array(e[:2]) - B.OBJ_CENTER) * 1000; cL = np.array([d[1], d[0]]); yaw = -2 * math.atan2(e[3], e[4])
            out.append({"img": f"{B.T}/{real}/{run}/tactile_images/{f['filename']}", "sid": f"{run}/{f['frame_id']}", "run": run, "frame": f["frame_id"],
                        "iteration": f["iteration"], "t": f["image_ros_timestamp_sec"], "yaw": yaw, "off": off, "cL": cL.tolist(), "press": press,
                        "old": [yaw + off, cL[0] + bias[0], cL[1] + bias[1]], "in_old_root": (run, f["frame_id"]) in cur, "prior": bias.tolist(),
                        "group": int(run) * 100 + f["iteration"]})
    return out


def scan_object(a):
    session, obj, const = a
    frames = frames_raw_s1(obj) if session == "s1" else frames_raw_s2(obj); sc = R.SENSOR[session]
    for f in frames:
        f["ridge"] = R.ridge(read224(f["img"])); f["rmask"] = f["ridge"] > 0.25
    fitted = False
    if const is None:                      # object without constants (not in the curated session-2 set): fit them on the frames that show a ridge
        use = [f for f in frames if f["press"] >= 0.5 and f["rmask"].mean() >= RIDGE_MIN]
        use = use[::max(1, math.ceil(len(use) / 150))]
        const = R.fit_constants(obj, use, sc, np.array(frames[0]["prior"])).tolist(); fitted = True
    rows = []
    for f in frames:
        th, c = R.pose(f, np.array(const), sc); mm = R.mesh_map(obj, th, c, f["press"])
        d = B.gt_depth_mm(obj, th, c[0], -c[1], max(f["press"], 0.3))
        mo = R.mesh_map(obj, f["old"][0], np.array(f["old"][1:]), f["press"])
        rows.append({k: f[k] for k in ("sid", "press", "in_old_root") if k in f} | {
            "yaw_deg": math.degrees(f["yaw"]), "ridge_frac": float(f["rmask"].mean()), "label_frac": float((d > 0.05).mean()),
            "ncc": R.ncc(f["ridge"], mm), "ncc_old_formula": R.ncc(f["ridge"], mo), "theta": th, "c": c.tolist(),
            "old_err_mm": float(np.linalg.norm(c - np.array(f["old"][1:])))} | ({"run": f["run"], "frame": f["frame"], "iteration": f["iteration"]} if session == "s2" else {}))
    return session, obj, const, fitted, rows


def cmd_scan(args):
    F = {"s1": json.load(open(f"{HERE}/fits_s1.json")), "s2": json.load(open(f"{HERE}/fits_s2.json"))}
    jobs = [("s1", o, F["s1"][o]["constants"]) for o in sorted(F["s1"])]
    jobs += [("s2", o, F["s2"][o]["constants"] if o in F["s2"] else None) for o in sorted(R.SIM2REAL) if osp.isdir(f"{B.T}/{R.SIM2REAL[o]}")]
    out = json.load(open(args.out)) if osp.exists(args.out) else {"s1": {}, "s2": {}}
    with ProcessPoolExecutor(args.workers) as ex:
        for session, obj, const, fitted, rows in ex.map(scan_object, jobs):
            out[session][obj] = {"constants": const, "fitted_here": fitted, "rows": rows}
            ok = [r for r in rows if usable(r)]; old = [r for r in rows if r["in_old_root"]]
            print(f"{session} {obj:30s} captured {len(rows):5d} | in the old root {len(old):4d} | usable with the corrected labels {len(ok):5d} "
                  f"(of them new {sum(1 for r in ok if not r['in_old_root']):4d}) | old-root frames that fail {sum(1 for r in old if not usable(r)):3d} | no ridge in the image {sum(1 for r in rows if r['ridge_frac'] < RIDGE_MIN):4d}"
                  + (f" | constants fitted here {np.round(const, 2).tolist()}" if fitted else ""), flush=True)
            json.dump(out, open(args.out, "w"))


def pose_json(obj, r, sc, const, extra):
    c = r["c"]; s = 1.0 / 1000.0
    return {"obj_name": obj, "sample_x": float(c[0] * 1e-3), "sample_y": float(-c[1] * 1e-3), "sample_z": float(r["press"] * 1e-3),
            "location": [float(c[0] * 1e-3), float(c[1] * 1e-3), float(-r["press"] * 1e-3 - B.Z_ANCHOR)], "rotation_euler": [0.0, 0.0, float(r["theta"])],
            "scale": [s] * 3, "fixed_scale": 1000.0, "label_ncc": r["ncc"],
            "kin_fix": {"yaw_rad": math.radians(r["yaw_deg"]), "dtheta_deg": const[0], "k_mm": list(const[1:]), "eps_deg": sc["eps"], "lever_mm": sc["lever"]}} | extra


def write_frame(obj, ou, idx, r, img, rgb, pj):
    cv2.imwrite(f"{ou}/samples/{idx}.png", cv2.cvtColor(read224(img), cv2.COLOR_RGB2BGR))
    if rgb and osp.exists(rgb):
        cv2.imwrite(f"{ou}/rgb/{idx}.png", cv2.cvtColor(read224(rgb), cv2.COLOR_RGB2BGR))
    json.dump(pj, open(f"{ou}/raw_data/{idx}_pose.json", "w"))
    g = B.gt_depth_mm(obj, r["theta"], r["c"][0], -r["c"][1], r["press"]) * 1e-3
    np.save(f"{ou}/raw_data/{idx}_gt.npy", g.astype(np.float32))


def build_s1(a):
    """session_000 = the frames of real_filtered_kin (same indices, so every existing split and label subset stays valid);
    session_001 = usable presses that the old filter had deleted or that were never selected."""
    obj, entry, out = a; B.use_exact_zmap = lambda name: True; sc = R.SENSOR["s1"]; real = BATCH[obj]["real_name"]
    os.makedirs(f"{out}/{obj}"); os.symlink(f"{R.G}/real_filtered_kin/{obj}/session_000", f"{out}/{obj}/session_000")
    ou = f"{out}/{obj}/session_001/sensor_0000"
    for sub in ("samples", "rgb", "raw_data"):
        os.makedirs(f"{ou}/{sub}")
    os.symlink(R.stable(f"{R.S1_ROOT}/{obj}/session_000/session.json"), f"{out}/{obj}/session_001/session.json")
    man = []; n = 0
    for r in entry["rows"]:
        if r["in_old_root"] or not usable(r):
            continue
        idx = f"{n:04d}"; sid = r["sid"]
        write_frame(obj, ou, idx, r, f"{X}/data/tactile_image/{real}/{sid}.jpg", f"{X}/data/rgb_image/{real}/{sid}_off.jpg",
                    pose_json(obj, r, sc, entry["constants"], {"original_sample_id": sid, "recovered": True}))
        man.append({"idx": idx, "sample_id": sid, "ncc": r["ncc"]}); n += 1
    json.dump({i["idx"]: i["sample_id"] for i in man}, open(f"{ou}/id_map.json", "w"))
    return obj, n, man


def build_s2(a):
    """One session per run (as before), every usable contact frame; frames of the curated 854 set are flagged in the pose file and the manifest."""
    obj, entry, out = a; B.use_exact_zmap = lambda name: True; sc = R.SENSOR["s2"]; real = R.SIM2REAL[obj]; off = B.OBJ_MAP[real][1]
    by = collections.defaultdict(list); man = []
    for r in entry["rows"]:
        if usable(r):
            by[r["run"]].append(r)
    for run, rows in sorted(by.items(), key=lambda t: int(t[0])):
        sess = f"{out}/{obj}/session_{int(run):03d}"; ou = f"{sess}/sensor_0000"
        for sub in ("samples", "rgb", "raw_data"):
            os.makedirs(f"{ou}/{sub}")
        tm = {f["frame_id"]: f for f in json.load(open(f"{B.T}/{real}/{run}/tactile_images/poses.json"))["frames"]}
        rp = f"{B.T}/{real}/{run}/rgb_images/poses.json"
        rgb_t = sorted((f["image_ros_timestamp_sec"], f["filename"]) for f in json.load(open(rp))["frames"]) if osp.exists(rp) else []
        for n, r in enumerate(sorted(rows, key=lambda q: q["frame"])):
            idx = f"{n:04d}"; f = tm[r["frame"]]; rgb = None
            if rgb_t:
                j = min(range(len(rgb_t)), key=lambda q: abs(rgb_t[q][0] - f["image_ros_timestamp_sec"])); rgb = f"{B.T}/{real}/{run}/rgb_images/{rgb_t[j][1]}"
            write_frame(obj, ou, idx, r, f"{B.T}/{real}/{run}/tactile_images/{f['filename']}", rgb,
                        pose_json(obj, r, sc, entry["constants"], {"source": {"run": run, "frame": r["frame"], "iteration": r["iteration"]}, "in_curated854": bool(r["in_old_root"])}))
            man.append({"session": f"session_{int(run):03d}", "idx": idx, "run": run, "frame": r["frame"], "iteration": r["iteration"], "ncc": r["ncc"], "in_curated854": bool(r["in_old_root"])})
        json.dump({"obj": obj, "base_rotation": [0.0, 0.0, float(off)], "rotation_step": 0.0, "fixed_scale": 1000.0, "_target_size_mm": 82.0,
                   "NUM_OBJ_SAMPLES": len(rows), "OBJ_DEPTH_MIN": 0.0008, "OBJ_DEPTH_MAX": 0.0012, "z_anchor": -B.Z_ANCHOR,
                   "capture": "new_real_test (session 2), corrected kinematics, all usable contact frames", "source_run": run, "valid_cells": []},
                  open(f"{sess}/session.json", "w"), indent=1)
    return obj, len(man), man


def cmd_build(args):
    D = json.load(open(args.scan))[args.session]; out = args.out_root.rstrip("/")
    assert not osp.exists(out) and out.startswith("/media/hdd/ihsuan/"), "destination exists or is not on the stable path"
    os.makedirs(out); fn = build_s1 if args.session == "s1" else build_s2; man = {}
    with ProcessPoolExecutor(args.workers) as ex:
        for obj, n, m in ex.map(fn, [(o, D[o], out) for o in sorted(D)]):
            man[obj] = m; print(f"{obj}: {n} frames written", flush=True)
    json.dump({"session": args.session, "thresholds": {"ncc": NCC_MIN, "ridge_frac": RIDGE_MIN, "label_frac": LABEL_MIN}, "sensor": R.SENSOR[args.session],
               "constants": {o: D[o]["constants"] for o in D}, "frames": man}, open(f"{out}/kin_manifest.json", "w"))
    print("total", sum(len(m) for m in man.values()))



def usable(r):
    return r["ridge_frac"] >= RIDGE_MIN and r["label_frac"] >= LABEL_MIN and r["ncc"] >= NCC_MIN


def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan"); s.add_argument("--out", required=True); s.add_argument("--workers", type=int, default=24)
    b = sub.add_parser("build"); b.add_argument("--scan", required=True); b.add_argument("--session", choices=["s1", "s2"], required=True)
    b.add_argument("--out-root", required=True); b.add_argument("--workers", type=int, default=12)
    args = ap.parse_args(); {"scan": cmd_scan, "build": cmd_build}[args.cmd](args)


if __name__ == "__main__":
    main()
