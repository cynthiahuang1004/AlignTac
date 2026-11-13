"""Corrected real labels: the end-effector translation is rotated into the sensor frame with the tool yaw (RSS_ROUND2_RESULTS.md D8).

Existing labels (both sessions):   theta_L = yaw + off,                 c_L = swap(ee_xy - C) [+ object constant]      (image-plane mm)
Corrected:                         theta   = yaw + off + dtheta,        c   = R(yaw + eps) (c_L + k) - lever
  eps, lever : sensor constants per session, from mesh-free press pairs (rss2_recapture_check.py; kinematics_check/)
  dtheta, k  : object constants per session (how the plate sits on the base), fitted here to the image ridges of all frames.
Nothing is fitted per frame.  Stored 224-px images and the labels written here cover the full 17.502 mm view (the loader crops both).

usage (from the AlignTac root):
  python rss2_recapture/rss2_relabel.py fit   --session s1 --out rss2_recapture/fits_s1.json [--objects ...]
  python rss2_recapture/rss2_relabel.py fit   --session s2 --out rss2_recapture/fits_s2.json
  python rss2_recapture/rss2_relabel.py build --session s1 --fits rss2_recapture/fits_s1.json --out-root <new root>   (refuses to overwrite)
"""
import argparse
import collections
import glob
import json
import math
import os
import os.path as osp
import sys
from concurrent.futures import ProcessPoolExecutor

import cv2
import numpy as np
from scipy.optimize import minimize

HERE = osp.dirname(osp.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, osp.join(osp.dirname(HERE), "scripts")); sys.path.insert(0, "/media/hdd/ihsuan/gs_blender")
import build_real_filtered_new as B                      # noqa: E402
from rss2_recapture_check import ridge                   # noqa: E402

B.VIEW = 0.017502                                         # full view: stored images and loader-ready labels
G = "/media/hdd/ihsuan/gs_blender"
S1_ROOT = f"{G}/real_filtered"
S2_ROOT = f"{G}/real_filtered_new_curated_pred_r2_fv"     # 854 curated session-2 frames (per-frame image fits, full view)
T = B.T                                                   # raw session-2 capture (new_real_test)
# sensor constants from the press pairs (kinematics_check/, 2026-11-13): eps deg, lever mm
SENSOR = {"s1": {"eps": 1.71, "lever": [-0.27, -0.15]}, "s2": {"eps": 1.81, "lever": [-0.19, 0.20]}}
SIM2REAL = {v[0]: k for k, v in B.OBJ_MAP.items()}
LAMBDA = 2e-4                                             # tie-breaker towards the prior constant (per mm^2), for directions the images do not see


def rot(a, v):
    c, s = math.cos(a), math.sin(a)
    return np.array([c * v[0] - s * v[1], s * v[0] + c * v[1]])


def frames_s1(obj):
    out = []
    for sess in sorted(glob.glob(f"{S1_ROOT}/{obj}/session_*")):
        rz0 = json.load(open(f"{sess}/session.json"))["base_rotation"][2]; u = f"{sess}/sensor_0000"
        for p in sorted(glob.glob(f"{u}/raw_data/*_pose.json")):
            i = osp.basename(p)[:4]; j = json.load(open(p))
            out.append({"img": f"{u}/samples/{i}.png", "unit": u, "idx": i, "yaw": j["rotation_euler"][2] - rz0, "off": rz0,
                        "cL": [j["sample_x"] * 1000, -j["sample_y"] * 1000], "press": j["sample_z"] * 1000,
                        "old": [j["rotation_euler"][2], j["sample_x"] * 1000, -j["sample_y"] * 1000], "group": int(i)})
    return out


_poses = {}


def frames_s2(obj):
    real = SIM2REAL[obj]; off = B.OBJ_MAP[real][1]; bias = np.array(B.OBJ_MAP[real][2:]) * 1000; out = []
    for sess in sorted(glob.glob(f"{S2_ROOT}/{obj}/session_*")):
        u = f"{sess}/sensor_0000"
        for p in sorted(glob.glob(f"{u}/raw_data/*_pose.json")):
            i = osp.basename(p)[:4]; j = json.load(open(p)); run = j["source"]["run"]; key = f"{real}/{run}"
            if key not in _poses:
                m = json.load(open(f"{T}/{key}/tactile_images/poses.json")); _poses[key] = {f["frame_id"]: f for f in m["frames"]}
            e = _poses[key][j["source"]["frame"]]["robot_pose_xyz_xyzw"]
            yaw = -2 * math.atan2(e[3], e[4]); d = (np.array(e[:2]) - B.OBJ_CENTER) * 1000
            cL = np.array([d[1], d[0]])
            out.append({"img": f"{u}/samples/{i}.png", "unit": u, "idx": i, "yaw": yaw, "off": off, "cL": cL.tolist(), "press": j["sample_z"] * 1000,
                        "old": [j["rotation_euler"][2], j["sample_x"] * 1000, -j["sample_y"] * 1000],          # curated per-frame fit
                        "stale": [yaw + off, cL[0] + bias[0], cL[1] + bias[1]],                                # recorded pose + session-1 constants
                        "group": int(run) * 100 + j["source"]["iteration"], "prior": bias.tolist()})
    return out


def pose(f, p, sc):
    """(theta, c) of a frame for object constants p = (dtheta deg, kx, ky) and sensor constants sc."""
    c = rot(f["yaw"] + math.radians(sc["eps"]), np.array(f["cL"]) + p[1:]) - np.array(sc["lever"])
    return f["yaw"] + f["off"] + math.radians(p[0]), c


def mesh_map(obj, th, c, press):
    d = B.gt_depth_mm(obj, th, c[0], -c[1], max(press, 0.3))
    return cv2.GaussianBlur(np.clip(d / max(press, 0.3), 0, 1), (0, 0), 1.5)


def ncc(r, m):
    den = math.sqrt(float((r * r).sum()) * float((m * m).sum()))
    return float((r * m).sum() / den) if den > 1e-6 else 0.0


def load(frames):
    for f in frames:
        f["ridge"] = ridge(cv2.cvtColor(cv2.imread(f["img"]), cv2.COLOR_BGR2RGB))
        f["rmask"] = f["ridge"] > 0.25
    return frames


def score(obj, frames, p, sc):
    return float(np.mean([ncc(f["ridge"], mesh_map(obj, *pose(f, p, sc), f["press"])) for f in frames]))


def score_pose(obj, frames, key):
    v = [ncc(f["ridge"], mesh_map(obj, f[key][0], np.array(f[key][1:]), f["press"])) for f in frames]
    return float(np.mean(v))


def fit_constants(obj, frames, sc, prior, span=4.0):
    sub = frames[::max(1, len(frames) // 60)]
    obj_f = lambda p, fr: -(score(obj, fr, p, sc) - LAMBDA * float(((np.asarray(p[1:]) - prior) ** 2).sum()))
    cand = []
    for dth in (-4.0, -2.0, 0.0, 2.0, 4.0):
        for dx in np.arange(-span, span + 1e-9, 0.5):
            for dy in np.arange(-span, span + 1e-9, 0.5):
                p = np.array([dth, prior[0] + dx, prior[1] + dy]); cand.append((obj_f(p, sub), p))
    cand.sort(key=lambda t: t[0]); best = None; seen = []
    for v, p in cand:
        if any(np.abs(p - q).max() < 1.01 for q in seen):
            continue
        seen.append(p)
        r = minimize(obj_f, p, args=(frames,), method="Powell", options={"xtol": 1e-2, "ftol": 1e-5})
        if best is None or r.fun < best[0]:
            best = (float(r.fun), np.asarray(r.x, float))
        if len(seen) == 3:
            break
    return best[1]


def fit_object(a):
    session, obj = a
    frames = load(frames_s1(obj) if session == "s1" else frames_s2(obj)); sc = SENSOR[session]
    prior = np.array(frames[0].get("prior", [0.0, 0.0]))
    use = [f for f in frames if f["press"] >= 0.5] or frames
    use = use[::max(1, math.ceil(len(use) / 240))]            # three constants per object: 240 frames are plenty
    groups = sorted(set(f["group"] for f in use)); ga = set(groups[0::2])
    A = [f for f in use if f["group"] in ga]; Bh = [f for f in use if f["group"] not in ga]
    pA, pB, pAll = fit_constants(obj, A, sc, prior), fit_constants(obj, Bh, sc, prior), fit_constants(obj, use, sc, prior)
    res = {"obj": obj, "session": session, "n_frames": len(frames), "n_fit": len(use), "n_groups": len(groups), "constants": pAll.tolist(),
           "half_a": pA.tolist(), "half_b": pB.tolist(), "split_half_diff": {"dtheta_deg": float(abs(pA[0] - pB[0])), "k_mm": float(np.linalg.norm(pA[1:] - pB[1:]))},
           "ncc_heldout": {"corrected": 0.5 * (score(obj, Bh, pA, sc) + score(obj, A, pB, sc)), "old_label": score_pose(obj, use, "old")},
           "sensor": sc, "prior": prior.tolist()}
    if session == "s2":
        res["ncc_heldout"]["stale_recorded_pose"] = score_pose(obj, use, "stale")
    # per-frame comparison of the corrected pose with the stored label (session 1: registered label; session 2: curated per-frame fit)
    d = []
    for f in frames:
        th, c = pose(f, pAll, sc); d.append([math.degrees((th - f["old"][0] + math.pi) % (2 * math.pi) - math.pi), *(c - np.array(f["old"][1:]))])
    d = np.array(d); sh = np.hypot(d[:, 1], d[:, 2])
    res["vs_old_label"] = {"shift_mm": {"median": float(np.median(sh)), "mean": float(sh.mean()), "p90": float(np.percentile(sh, 90)), "max": float(sh.max())},
                           "rot_deg": {"median_abs": float(np.median(np.abs(d[:, 0]))), "mean": float(d[:, 0].mean())}}
    return res


def cmd_fit(args):
    objs = args.objects or sorted(os.listdir(S1_ROOT if args.session == "s1" else S2_ROOT))
    out = json.load(open(args.out)) if osp.exists(args.out) else {}
    with ProcessPoolExecutor(args.workers) as ex:
        for r in ex.map(fit_object, [(args.session, o) for o in objs]):
            out[r["obj"]] = r; c = r["constants"]; n = r["ncc_heldout"]
            print(f"{r['obj']:30s} {r['n_fit']:4d} frames / {r['n_groups']:3d} groups | dtheta {c[0]:+.2f} deg k ({c[1]:+.2f}, {c[2]:+.2f}) mm | split-half {r['split_half_diff']['dtheta_deg']:.2f} deg "
                  f"{r['split_half_diff']['k_mm']:.2f} mm | held-out NCC corrected {n['corrected']:.3f} vs stored label {n['old_label']:.3f}"
                  + (f" vs recorded pose {n['stale_recorded_pose']:.3f}" if "stale_recorded_pose" in n else "")
                  + f" | corrected - stored: {r['vs_old_label']['shift_mm']['median']:.2f} mm median (p90 {r['vs_old_label']['shift_mm']['p90']:.2f}), {r['vs_old_label']['rot_deg']['median_abs']:.2f} deg", flush=True)
            json.dump(out, open(args.out, "w"), indent=1)


STABLE = "/media/hdd/ihsuan"


def stable(p):
    """Link target on the stable path (the project disk's mount point changes across reboots)."""
    t = osp.realpath(p)
    for sub in ("gs_blender", "VisTacFusion"):
        phys = osp.realpath(f"{STABLE}/{sub}")
        if t.startswith(phys + "/"):
            return f"{STABLE}/{sub}" + t[len(phys):]
    return t


def build_object(a):
    session, obj, const, src_root, out_root = a
    B.use_exact_zmap = lambda name: True          # exact rasterization: reproduces the stored session-1 labels (IoU 0.99), = `_fv_exact` for session 2
    frames = frames_s1(obj) if session == "s1" else frames_s2(obj); sc = SENSOR[session]; done = set(); n = 0
    for f in frames:
        u = f["unit"]; ou = u.replace(src_root, out_root)
        if ou not in done:
            os.makedirs(f"{ou}/raw_data", exist_ok=True); done.add(ou)
            for name in os.listdir(u):
                if name != "raw_data":
                    os.symlink(stable(f"{u}/{name}"), f"{ou}/{name}")
            sj = osp.join(osp.dirname(u), "session.json")
            if osp.exists(sj):
                os.symlink(stable(sj), osp.join(osp.dirname(ou), "session.json"))
            for name in os.listdir(f"{u}/raw_data"):                      # anything that is not a label (e.g. raw sensor depth) is linked
                if not (name.endswith("_gt.npy") or name.endswith("_pose.json")):
                    os.symlink(stable(f"{u}/raw_data/{name}"), f"{ou}/raw_data/{name}")
        th, c = pose(f, const, sc); i = f["idx"]
        j = json.load(open(f"{u}/raw_data/{i}_pose.json"))
        j["label_v1"] = {"sample_x": j["sample_x"], "sample_y": j["sample_y"], "rotation_z": j["rotation_euler"][2]}
        j["sample_x"], j["sample_y"] = float(c[0] * 1e-3), float(-c[1] * 1e-3); j["rotation_euler"][2] = float(th)
        if "location" in j:
            j["location"][0], j["location"][1] = j["sample_x"], -j["sample_y"]
        j.pop("world_matrix", None); j.pop("world_matrix_inv", None)
        j["kin_fix"] = {"yaw_rad": f["yaw"], "dtheta_deg": const[0], "k_mm": list(const[1:]), "eps_deg": sc["eps"], "lever_mm": sc["lever"]}
        json.dump(j, open(f"{ou}/raw_data/{i}_pose.json", "w"))
        g = B.gt_depth_mm(obj, th, c[0], -c[1], f["press"]) * 1e-3
        np.save(f"{ou}/raw_data/{i}_gt.npy", g.astype(np.float32)); n += 1
    return obj, n


def cmd_build(args):
    fits = json.load(open(args.fits)); src = S1_ROOT if args.session == "s1" else S2_ROOT; out = args.out_root.rstrip("/")
    assert not osp.exists(out), f"{out} exists: not overwriting"
    assert out.startswith(STABLE + "/"), "write the root under the stable path"
    os.makedirs(out)
    with ProcessPoolExecutor(args.workers) as ex:
        for obj, n in ex.map(build_object, [(args.session, o, r["constants"], src, out) for o, r in sorted(fits.items())]):
            print(f"{obj}: {n} frames", flush=True)
    for extra in glob.glob(f"{src}/*.json"):
        os.symlink(stable(extra), f"{out}/{osp.basename(extra)}")
    json.dump({"source_root": src, "session": args.session, "sensor": SENSOR[args.session], "objects": {o: r["constants"] for o, r in fits.items()},
               "model": "theta = yaw + off + dtheta; c = R(yaw + eps)(c_L + k) - lever; exact rasterization, full 17.502 mm view"},
              open(f"{out}/kin_fix.json", "w"), indent=1)
    print("dangling links:", sum(1 for r, d, fs in os.walk(out) for x in fs + d if osp.islink(osp.join(r, x)) and not osp.exists(osp.join(r, x))))


def contour(img, mask, color):
    cs, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(img, cs, -1, color, 1)


def cmd_overlay(args):
    """Contact sheet per session: stored label (red) and corrected label (white) on the tactile image, full view."""
    fits = json.load(open(args.fits)); sc = SENSOR[args.session]; rows = []; B.use_exact_zmap = lambda name: True
    for obj in sorted(fits):
        frames = frames_s1(obj) if args.session == "s1" else frames_s2(obj)
        frames = [f for f in frames if f["press"] >= 0.7] or frames
        sel = frames[::max(1, len(frames) // args.n)][:args.n]; tiles = []
        for f in sel:
            im = cv2.resize(cv2.imread(f["img"]), (448, 448), interpolation=cv2.INTER_LINEAR)
            old = B.gt_depth_mm(obj, f["old"][0], f["old"][1], -f["old"][2], f["press"]) > 0.15
            th, c = pose(f, fits[obj]["constants"], sc); new = B.gt_depth_mm(obj, th, c[0], -c[1], f["press"]) > 0.15
            contour(im, cv2.resize(old.astype(np.uint8), (448, 448), interpolation=cv2.INTER_NEAREST), (0, 0, 255))
            contour(im, cv2.resize(new.astype(np.uint8), (448, 448), interpolation=cv2.INTER_NEAREST), (255, 255, 255))
            tiles.append(im)
        while len(tiles) < args.n:
            tiles.append(np.zeros((448, 448, 3), np.uint8))
        row = np.concatenate(tiles, 1); cv2.putText(row, obj, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2); rows.append(row)
    os.makedirs(osp.dirname(args.out), exist_ok=True); cv2.imwrite(args.out, np.concatenate(rows, 0), [cv2.IMWRITE_JPEG_QUALITY, 88]); print("wrote", args.out)



def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fit"); f.add_argument("--session", choices=["s1", "s2"], required=True); f.add_argument("--out", required=True)
    f.add_argument("--objects", nargs="*"); f.add_argument("--workers", type=int, default=12)
    b = sub.add_parser("build"); b.add_argument("--session", choices=["s1", "s2"], required=True); b.add_argument("--fits", required=True)
    b.add_argument("--out-root", required=True); b.add_argument("--workers", type=int, default=12)
    o = sub.add_parser("overlay"); o.add_argument("--session", choices=["s1", "s2"], required=True); o.add_argument("--fits", required=True)
    o.add_argument("--out", required=True); o.add_argument("--n", type=int, default=6)
    args = ap.parse_args()
    {"fit": cmd_fit, "build": cmd_build, "overlay": cmd_overlay}[args.cmd](args)


if __name__ == "__main__":
    main()
