"""Optimization baselines for mesh-to-frame alignment ("ICP / optimization baseline that fits the mesh to the teacher depth").

Every method starts from the teacher's planar pose (rc_fits.json "tp" of an aligned pseudo root) and the teacher's press
depth, and returns a contact state (theta, x_mm, y_mm, p_mm).  The mesh depth at that state is scored against the withheld
GT exactly like the aligner's labels (IoU, contact MAE, rotation / translation / press error).
  teacher   mesh at the teacher pose, no refinement
  grid      local coordinate-descent grid search on the dense depth L1 (pseudo_label_rc.coarse = first stage of the L1 search)
  icp       point-to-point ICP between the teacher's contact points and the mesh surface (SE(2) + press), closed-form updates
  gd        Adam on the dense depth L1 through a differentiable (bilinear) mesh-depth renderer
  aligner   learned residual aligner, six updates (train_aligner.refine)
  global    exhaustive search over theta in [0, 360) and +-7 mm (no initial pose) on the depth L1, then `grid`;
            global+aligner and global+icp refine from that start (calibration-free initialization)
--perturb d1,d2,...: every local method is also started from the GT state rotated by +-d degrees (random sign) and shifted
by --perturb-shift mm in a random direction, to measure the basin of convergence.
usage: python scripts/tactile_render/fit_baselines.py --al-root /media/hdd2/ihsuan/gs_blender/real_pseudo_k25_ro_al \
           --aligner outputs/aligner_k25_realonly/aligner.pt --out ablation/pilot_robosoft/fit_baselines_k25.json --step 6
       session 2: --al-root .../real_pseudo_s2_k25_al --real-root .../real_s2_pool --gt-root .../real_s2_poolcheck --step 1
"""
import argparse
import glob
import json
import math
import os
import os.path as osp
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import torch
from PIL import Image
from scipy.spatial import cKDTree

ROOT = osp.dirname(osp.dirname(osp.dirname(osp.abspath(__file__))))
sys.path.insert(0, ROOT); sys.path.insert(0, osp.join(ROOT, "scripts")); sys.path.insert(0, osp.dirname(osp.abspath(__file__)))
import pseudo_label_rc as RC  # noqa: E402  (sets B.VIEW to the sensor-A gel view)
from pseudo_label_rc import B, coarse, mesh_depth_t, quality  # noqa: E402

SYM = osp.join(ROOT, "outputs", "sensorB_mapl", "fits_train_canon_symmetry.json")   # rotational periods of the 12 meshes


# ----------------------------------------------------------------------------- geometry helpers
def world_xy_mm(stride=2):
    """Gel-plane coordinates (mm) of the pixel centres on a stride grid; same convention as mesh_depth_half."""
    u = np.arange(0, 224, stride) + stride / 2.0
    uu, vv = np.meshgrid(u, u)
    return -(uu - 112) * B.VIEW / 224 * 1000, -(vv - 112) * B.VIEW / 224 * 1000


def rot_err(th, th_gt, period=360.0):
    d = (math.degrees(th - th_gt) + 180) % 360 - 180
    if period < 360:
        d = (d + period / 2) % period - period / 2
    return abs(d)


# ----------------------------------------------------------------------------- ICP
_mesh_pts = {}


def mesh_points(obj, band=1.8, stride=2):
    """Mesh surface points (mesh frame, mm) within `band` mm of the top of the mesh, on a stride grid of the z-map."""
    if obj not in _mesh_pts:
        zmap, LO, BB, PPM, RS = B.get_zmap(obj); zmin = float(zmap.min())
        jy, jx = np.nonzero(zmap <= zmin + band)
        k = (jy % stride == 0) & (jx % stride == 0); jy, jx = jy[k], jx[k]
        pts = np.stack([LO[0] + (jx + 0.5) / PPM, LO[1] + (jy + 0.5) / PPM, zmap[jy, jx]], 1).astype(np.float64)
        _mesh_pts[obj] = (pts, cKDTree(pts), np.asarray(BB, np.float64), zmin)
    return _mesh_pts[obj]


def icp(obj, Dt, th, x, y, p, iters=60, stride=2, trim=3.0):
    """Point-to-point ICP of the teacher contact points onto the mesh surface.  Returns (theta, x, y, p)."""
    pts, tree, BB, zmin = mesh_points(obj)
    wx, wy = world_xy_mm(stride)
    D = Dt[stride // 2::stride, stride // 2::stride]
    m = D > 0.05
    if m.sum() < 20:
        return th, x, y, p
    w = np.stack([wx[m], wy[m]], 1); d = D[m].astype(np.float64)
    for _ in range(iters):
        c = np.array([x, -y]); R = np.array([[math.cos(th), math.sin(th)], [-math.sin(th), math.cos(th)]])
        q = (w - c) @ R.T + BB                                  # teacher points in the mesh frame (xy)
        z = zmin + p - d
        dist, j = tree.query(np.column_stack([q, z]), k=1)
        keep = dist <= trim * max(np.median(dist), 1e-3)
        if keep.sum() < 10:
            break
        mp = pts[j[keep]]; wk = w[keep]
        # rigid 2-D fit  R (w - c) + BB = m_xy
        qk = mp[:, :2] - BB; wb, qb = wk.mean(0), qk.mean(0)
        H = (wk - wb).T @ (qk - qb); U, _, Vt = np.linalg.svd(H); Rn = Vt.T @ U.T
        if np.linalg.det(Rn) < 0:
            Vt[-1] *= -1; Rn = Vt.T @ U.T
        th_n = math.atan2(Rn[0, 1], Rn[0, 0]); c_n = wb - Rn.T @ qb
        p_n = p + float(np.mean(mp[:, 2] - z[keep]))
        done = abs(th_n - th) < 1e-5 and np.abs(c_n - c).max() < 1e-4 and abs(p_n - p) < 1e-4
        th, x, y, p = th_n, float(c_n[0]), float(-c_n[1]), float(np.clip(p_n, 0.3, 1.6))
        if done:
            break
    return th, x, y, p


# ----------------------------------------------------------------------------- differentiable depth + gradient descent
_zt = {}


def mesh_depth_bilinear(obj, pose, dev, stride=2):
    """pose [N, 4] -> mesh depth (mm) [N, 224/stride, 224/stride], bilinear in the z-map (differentiable in the pose)."""
    if obj not in _zt:
        zmap, LO, BB, PPM, RS = B.get_zmap(obj)
        _zt[obj] = (torch.from_numpy(zmap).to(dev)[None, None], LO, BB, PPM, RS, float(zmap.min()))
    z, LO, BB, PPM, RS, zmin = _zt[obj]
    u = torch.arange(0, 224, stride, device=dev) + stride / 2.0
    vv, uu = torch.meshgrid(u, u, indexing="ij")
    dx = (-(uu - 112) * B.VIEW / 224)[None] - (pose[:, 1] * 1e-3)[:, None, None]
    dy = (-(vv - 112) * B.VIEW / 224)[None] + (pose[:, 2] * 1e-3)[:, None, None]
    c, s = torch.cos(pose[:, 0])[:, None, None], torch.sin(pose[:, 0])[:, None, None]
    gx = ((c * dx + s * dy) * 1000 + BB[0] - LO[0]) * PPM
    gy = ((-s * dx + c * dy) * 1000 + BB[1] - LO[1]) * PPM
    grid = torch.stack([gx / RS * 2 - 1, gy / RS * 2 - 1], -1)
    zs = torch.nn.functional.grid_sample(z.expand(len(pose), -1, -1, -1), grid, mode="bilinear", padding_mode="border", align_corners=False)[:, 0]
    return (zmin + pose[:, 3][:, None, None] - zs).clamp(min=0)


def gd(obj, Dts, poses0, dev, iters=200, lr=0.1):
    """Adam on the dense depth L1 for a batch of frames of one object.  poses0 [N, 4] -> [N, 4] (best iterate per frame)."""
    tgt = torch.from_numpy(np.stack([d[1::2, 1::2] for d in Dts])).float().to(dev)
    p0 = torch.tensor(poses0, dtype=torch.float32, device=dev)
    scale = torch.tensor([0.05, 0.3, 0.3, 0.05], device=dev)
    u = torch.zeros_like(p0, requires_grad=True)
    opt = torch.optim.Adam([u], lr=lr)
    best = p0.clone(); best_l = torch.full((len(p0),), float("inf"), device=dev)
    for _ in range(iters):
        pose = p0 + u * scale
        loss = (mesh_depth_bilinear(obj, pose, dev) - tgt).abs().mean((1, 2))
        with torch.no_grad():
            imp = loss < best_l; best_l[imp] = loss[imp]; best[imp] = pose[imp]
        opt.zero_grad(); loss.sum().backward(); opt.step()
        with torch.no_grad():
            u[:, 3].clamp_(-(p0[:, 3] - 0.3) / 0.05, (1.6 - p0[:, 3]) / 0.05)
    return best.detach().cpu().numpy()


# ----------------------------------------------------------------------------- global search
@torch.no_grad()
def global_fit(obj, Dt, p, dev, step_deg=3.0, lim=7.0, step_mm=0.5):
    """Exhaustive search (theta, x, y) at stride 4 on the depth L1; no initial pose.  Returns (theta, x, y)."""
    tgt = torch.from_numpy(Dt[2::4, 2::4]).float().to(dev)
    cands = torch.cartesian_prod(torch.deg2rad(torch.arange(0, 360, step_deg)), torch.arange(-lim, lim + 1e-6, step_mm),
                                 torch.arange(-lim, lim + 1e-6, step_mm)).to(dev)
    pose = torch.cat([cands, torch.full((len(cands), 1), float(p), device=dev)], 1)
    best = (1e9, None)
    for i in range(0, len(pose), 8192):
        c = pose[i:i + 8192]
        e = (mesh_depth_bilinear(obj, c, dev, stride=4) - tgt[None]).abs().mean((1, 2)); j = int(e.argmin())
        if float(e[j]) < best[0]:
            best = (float(e[j]), c[j, :3].tolist())
    return tuple(best[1])


# ----------------------------------------------------------------------------- data
def load_frames(al_root, real_root, gt_root, step):
    fits = json.load(open(osp.join(al_root, "rc_fits.json")))
    src = json.load(open(osp.join(al_root, "pseudo_manifest.json")))["args"]["src_root"]
    s2 = {}
    if gt_root:
        for pj in glob.glob(f"{gt_root}/*/session_*/sensor_0000/raw_data/*_pose.json"):
            d = json.load(open(pj)); s2[(pj.split("/")[-5], pj.split("/")[-4], int(d["source"]["frame"]))] = pj
    items = []
    for tac in sorted(fits)[::step]:
        unit = osp.dirname(osp.dirname(tac)); idx = osp.basename(tac)[:4]; obj = unit.split("/")[-3]
        dep = osp.join(unit.replace(real_root, src), "raw_data", idx + "_gt.npy")
        if gt_root:
            pj = osp.join(unit, "raw_data", idx + "_pose.json")
            key = (obj, unit.split("/")[-2], int(json.load(open(pj))["source"]["frame"]))
            if key not in s2:
                continue
            gpj = s2[key]
        else:
            gpj = osp.join(unit, "raw_data", idx + "_pose.json")
        P = json.load(open(gpj))
        items.append(dict(tac=tac, obj=obj, dep=dep, gt=gpj.replace("_pose.json", "_gt.npy"),
                          gt_pose=(P["rotation_euler"][2], P["sample_x"] * 1e3, P["sample_y"] * 1e3, P["sample_z"] * 1e3),
                          tp=tuple(fits[tac]["tp"]), al=tuple(fits[tac]["pose"]) + (fits[tac]["p"],)))
    return items


def score(it, pose, period):
    th, x, y, p = pose
    gt = np.load(it["gt"]) * 1000
    iou, cmae = quality(B.gt_depth_mm(it["obj"], th, x, y, p), gt)
    g = it["gt_pose"]
    return dict(iou=iou, cmae=cmae, rot=rot_err(th, g[0]), rot_sym=rot_err(th, g[0], period),
                trans=(abs(x - g[1]) + abs(y - g[2])) / 2, dp=abs(p - g[3]))


def summarize(rows):
    keys = ("iou", "cmae", "rot", "rot_sym", "trans", "dp")
    out = {k: float(np.nanmean([r[k] for r in rows])) for k in keys}
    out["rot_median"] = float(np.nanmedian([r["rot"] for r in rows])); out["n"] = len(rows)
    out["rot_lt5"] = float(np.mean([r["rot"] < 5 for r in rows]))
    return out


def fmt(name, s):
    return (f"{name:18s} n={s['n']:4d}  IoU {s['iou']:.3f}  cMAE {s['cmae']:.3f}  rot {s['rot']:6.2f} (med {s['rot_median']:5.2f}, sym {s['rot_sym']:5.2f}, "
            f"<5deg {100 * s['rot_lt5']:4.1f}%)  trans {s['trans']:.2f}  |dp| {s['dp']:.3f}")


# ----------------------------------------------------------------------------- main
def run_methods(items, inits, A, dev, methods, pool, tag=""):
    """inits: list of (theta, x, y, p) per item.  Returns {method: [pose per item]}."""
    out = {}
    t0 = time.time()
    if "grid" in methods:
        fits = list(pool.map(coarse, [(it["dep"], it["obj"], i[0], i[1], i[2]) for it, i in zip(items, inits)], chunksize=4))
        out["grid"] = [tuple(c) + (p,) for c, p in fits]
        print(f"  [{tag}] grid {time.time() - t0:.0f}s", flush=True); t0 = time.time()
    if "icp" in methods:
        out["icp"] = [icp(it["obj"], np.load(it["dep"]) * 1000, *i) for it, i in zip(items, inits)]
        print(f"  [{tag}] icp {time.time() - t0:.0f}s", flush=True); t0 = time.time()
    if "gd" in methods:
        res = [None] * len(items)
        for o in sorted({it["obj"] for it in items}):
            j = [k for k, it in enumerate(items) if it["obj"] == o]
            for k0 in range(0, len(j), 128):
                jj = j[k0:k0 + 128]
                r = gd(o, [np.load(items[k]["dep"]) * 1000 for k in jj], [inits[k] for k in jj], dev)
                for k, rr in zip(jj, r):
                    res[k] = tuple(float(v) for v in rr)
        out["gd"] = res
        print(f"  [{tag}] gd {time.time() - t0:.0f}s", flush=True); t0 = time.time()
    if "aligner" in methods and A is not None:
        from train_aligner import refine
        res = [None] * len(items)
        for k0 in range(0, len(items), 64):
            its = items[k0:k0 + 64]
            img = torch.from_numpy(np.stack([np.array(Image.open(it["tac"]).convert("RGB"), np.float32).transpose(2, 0, 1) / 127.5 - 1 for it in its])).to(dev)
            pz = torch.tensor([inits[k0 + j] for j in range(len(its))], dtype=torch.float32, device=dev)
            pz = refine(A, [it["obj"] for it in its], img, pz, dev, iters=6)
            for j in range(len(its)):
                res[k0 + j] = tuple(pz[j].tolist())
        out["aligner"] = res
        print(f"  [{tag}] aligner {time.time() - t0:.0f}s", flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--al-root", required=True, help="aligned pseudo root (rc_fits.json gives the teacher pose and the aligner's pose)")
    ap.add_argument("--real-root", default=RC.REAL, help="root the pseudo root was built from (frames + GT)")
    ap.add_argument("--gt-root", default=None, help="session 2: curated root whose labels are matched by object/session/source frame")
    ap.add_argument("--aligner", default=None)
    ap.add_argument("--step", type=int, default=6)
    ap.add_argument("--methods", default="grid,icp,gd,aligner,global")
    ap.add_argument("--perturb", default="", help="degrees, e.g. 5,10,15,20,30")
    ap.add_argument("--perturb-shift", type=float, default=0.5, help="mm")
    ap.add_argument("--perturb-step", type=int, default=3, help="extra subsampling of the frames for the perturbation sweep")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--device", default="cuda:0")
    args = ap.parse_args()
    os.chdir(ROOT); dev = args.device
    methods = args.methods.split(",")
    sym = json.load(open(SYM)) if osp.exists(SYM) else {}
    period = lambda o: sym.get(o, {}).get("period_deg", 360.0)  # noqa: E731
    items = load_frames(args.al_root, args.real_root, args.gt_root, args.step)
    print(f"{len(items)} frames from {args.al_root} (step {args.step}); objects {sorted({it['obj'] for it in items})}", flush=True)
    for o in sorted({it["obj"] for it in items}):
        B.get_zmap(o)
    A = None
    if args.aligner and "aligner" in methods:
        from train_aligner import Aligner
        A = Aligner().to(dev).eval(); A.load_state_dict(torch.load(args.aligner, map_location=dev))
    pool = ProcessPoolExecutor(args.workers)
    results = {}
    # ---- from the teacher pose ----
    inits = [it["tp"] + (float(np.clip(np.load(it["dep"]).max() * 1000, 0.3, 1.6)),) for it in items]
    poses = {"teacher": inits, "aligner (root)": [it["al"] for it in items]}
    poses.update(run_methods(items, inits, A, dev, methods, pool, tag="teacher init"))
    if "global" in methods:
        t0 = time.time()
        g = [global_fit(it["obj"], np.load(it["dep"]) * 1000, i[3], dev) + (i[3],) for it, i in zip(items, inits)]
        print(f"  global search {time.time() - t0:.0f}s", flush=True)
        poses["global"] = g
        sub = run_methods(items, g, A, dev, [m for m in ("grid", "icp", "aligner") if m in methods], pool, tag="global init")
        for k, v in sub.items():
            poses["global+" + k] = v
    results["from_teacher"] = {}
    for name, ps in poses.items():
        rows = [score(it, p, period(it["obj"])) for it, p in zip(items, ps)]
        results["from_teacher"][name] = dict(summary=summarize(rows),
                                             per_object={o: summarize([r for r, it in zip(rows, items) if it["obj"] == o]) for o in sorted({it["obj"] for it in items})})
        print(fmt(name, results["from_teacher"][name]["summary"]), flush=True)
    # ---- basin of convergence: from the GT state perturbed ----
    if args.perturb:
        rng = np.random.RandomState(0)
        sub_items = items[::args.perturb_step]
        results["perturb"] = {}
        for d in [float(v) for v in args.perturb.split(",")]:
            inits = []
            for it in sub_items:
                g = it["gt_pose"]; a = rng.uniform(0, 2 * math.pi); s = rng.choice([-1, 1])
                inits.append((g[0] + s * math.radians(d), g[1] + args.perturb_shift * math.cos(a), g[2] + args.perturb_shift * math.sin(a),
                              float(np.clip(np.load(it["dep"]).max() * 1000, 0.3, 1.6))))
            ps = {"init": inits}
            ps.update(run_methods(sub_items, inits, A, dev, [m for m in ("grid", "icp", "gd", "aligner") if m in methods], pool, tag=f"perturb {d:g}"))
            results["perturb"][str(d)] = {}
            for name, pp in ps.items():
                rows = [score(it, p, period(it["obj"])) for it, p in zip(sub_items, pp)]
                results["perturb"][str(d)][name] = summarize(rows)
                print(f"perturb {d:4.0f} deg  " + fmt(name, results["perturb"][str(d)][name]), flush=True)
    results["args"] = vars(args); results["n"] = len(items)
    os.makedirs(osp.dirname(args.out) or ".", exist_ok=True)
    json.dump(results, open(args.out, "w"), indent=1)
    print("->", args.out)
    pool.shutdown()


if __name__ == "__main__":
    main()
