"""Multi-start alignment with label-free selection (session 2 two-line-pattern failures).

Per frame, candidates = aligner from (a) the teacher pose, (b) the global depth-search start, (c) the stale recorded pose, and
(d) the teacher pose rotated by the object's symmetry period / 2 (two-line patterns: 90 deg) -- all refined by the aligner.
Selection scores (no label used): black-hat ridge-mask IoU with the mesh contact (as in calibrate_new_real_poses.py), the
K-shot renderer's image L1 (pseudo_label_rc.render_error), and the aligner's residual correction.  Reports label quality of each
candidate and of each selection rule, overall and for the two-line patterns, on the 162 curated pool frames.
usage: python ablation/pilot_robosoft/rss2_multistart.py --k 25 [--device cuda:0]
"""
import argparse, glob, json, math, os, os.path as osp, sys
import numpy as np, torch
from PIL import Image
ROOT = osp.dirname(osp.dirname(osp.dirname(osp.abspath(__file__))))
sys.path.insert(0, ROOT); sys.path.insert(0, osp.join(ROOT, "scripts")); sys.path.insert(0, osp.join(ROOT, "scripts", "tactile_render"))
import fit_baselines as FB  # noqa: E402
from fit_baselines import B, quality, rot_err, global_fit, oldcal_pose  # noqa: E402
from pseudo_label_rc import render_error  # noqa: E402
from train_aligner import Aligner, refine, depth_batch  # noqa: E402
from train_tactile_gan import UNetG  # noqa: E402
from calibrate_new_real_poses import blackhat_mask  # noqa: E402
G = "/media/hdd/ihsuan/gs_blender"; TWO = ("pattern_01_2_lines_angle_1_2", "pattern_01_2_lines_angle_2", "pattern_01_2_lines_angle_3")

ap = argparse.ArgumentParser(); ap.add_argument("--k", type=int, default=25); ap.add_argument("--device", default="cuda:0"); ap.add_argument("--aligner", default=None)
args = ap.parse_args(); os.chdir(ROOT); dev = args.device; K = args.k
al_root = f"{G}/real_pseudo_s2_k{K}_al"; fits = json.load(open(f"{al_root}/rc_fits.json")); src = f"{G}/real_pseudo_s2_k{K}_ng"
sym = json.load(open(FB.SYM)); period = lambda o: sym.get(o, {}).get("period_deg", 360.0)  # noqa: E731
gtmap = {}
for pj in glob.glob(f"{G}/real_s2_poolcheck/*/session_*/sensor_0000/raw_data/*_pose.json"):
    d = json.load(open(pj)); gtmap[(pj.split("/")[-5], pj.split("/")[-4], int(d["source"]["frame"]))] = pj
items = []
for tac in sorted(fits):
    unit = osp.dirname(osp.dirname(tac)); idx = osp.basename(tac)[:4]; obj = unit.split("/")[-3]; pj = osp.join(unit, "raw_data", idx + "_pose.json")
    g = gtmap.get((obj, unit.split("/")[-2], int(json.load(open(pj))["source"]["frame"])))
    if g:
        items.append(dict(tac=tac, obj=obj, dep=osp.join(unit.replace(f"{G}/real_s2_pool", src), "raw_data", idx + "_gt.npy"), tp=tuple(fits[tac]["tp"]), pj=pj, gt=g))
for o in sorted({it["obj"] for it in items}):
    B.get_zmap(o)
A = Aligner().to(dev).eval(); A.load_state_dict(torch.load(args.aligner or f"outputs/aligner_k{K}_realonly/aligner.pt", map_location=dev))
Gn = UNetG(in_ch=3).to(dev).eval(); Gn.load_state_dict(torch.load(f"outputs/tactile_gan_k{K}/G_final.pt", map_location=dev))
names = ["teacher", "global", "recorded", "teacher+90"]
for k0 in range(0, len(items), 32):
    its = items[k0:k0 + 32]; ob = [it["obj"] for it in its]; n = len(its)
    img = torch.from_numpy(np.stack([np.array(Image.open(it["tac"]).convert("RGB"), np.float32).transpose(2, 0, 1) / 127.5 - 1 for it in its])).to(dev)
    Dt = [np.load(it["dep"]) * 1000 for it in its]; p0 = [float(np.clip(d.max(), 0.3, 1.6)) for d in Dt]
    starts = {"teacher": [it["tp"] + (p,) for it, p in zip(its, p0)],
              "global": [global_fit(o, d, p, dev) + (p,) for o, d, p in zip(ob, Dt, p0)],
              "recorded": [oldcal_pose(it["pj"]) for it in its],
              "teacher+90": [(it["tp"][0] + math.radians(period(it["obj"]) / 2 if period(it["obj"]) < 360 else 180), it["tp"][1], it["tp"][2], p) for it, p in zip(its, p0)]}
    with torch.no_grad():
        for name in names:
            pz = refine(A, ob, img, torch.tensor(starts[name], dtype=torch.float32, device=dev), dev, iters=6)
            dm = depth_batch(ob, pz, dev); last = A(img, dm).abs().mean(1).cpu().numpy(); dm = dm.cpu().numpy()
            for j, it in enumerate(its):
                th, x, y, p = pz[j].tolist(); im8 = ((img[j].cpu().numpy().transpose(1, 2, 0) + 1) * 127.5).astype(np.uint8)
                bh = blackhat_mask(im8); m = dm[j] > 0.05
                rerr = float(render_error(Gn, it["obj"], pz[j:j + 1, :3], p, img[j], None, dev)[0])
                Pg = json.load(open(it["gt"])); gt = np.load(it["gt"].replace("_pose.json", "_gt.npy")) * 1000
                q = quality(dm[j], gt)
                it.setdefault("cand", {})[name] = dict(pose=(th, x, y, p), bh_iou=float((m & bh).sum() / max(1, (m | bh).sum())), rerr=rerr, last=float(last[j]),
                                                      iou=q[0], cmae=q[1], rot=rot_err(th, Pg["rotation_euler"][2], period(it["obj"])))
def report(tag, pick):
    rows = [it["cand"][pick(it)] for it in items]; two = [r for r, it in zip(rows, items) if it["obj"] in TWO]
    f = lambda rs: f"IoU {np.mean([r['iou'] for r in rs]):.3f} cMAE {np.nanmean([r['cmae'] for r in rs]):.3f} rot {np.mean([r['rot'] for r in rs]):5.1f} (med {np.median([r['rot'] for r in rs]):.1f})"  # noqa: E731
    print(f"{tag:34s} all n={len(rows)}: {f(rows)} | two-line n={len(two)}: {f(two)}")
print(f"K={K}, {len(items)} curated pool frames")
for name in names:
    report(f"start = {name}", lambda it, n=name: n)
report("oracle best-of-4 (by true IoU)", lambda it: max(it["cand"], key=lambda n: it["cand"][n]["iou"]))
report("select: black-hat mask IoU", lambda it: max(it["cand"], key=lambda n: it["cand"][n]["bh_iou"]))
report("select: renderer L1", lambda it: min(it["cand"], key=lambda n: it["cand"][n]["rerr"]))
report("select: residual correction", lambda it: min(it["cand"], key=lambda n: it["cand"][n]["last"]))
report("select: mask IoU, teacher vs global only", lambda it: max(("teacher", "global"), key=lambda n: it["cand"][n]["bh_iou"]))
report("select: renderer, teacher vs global only", lambda it: min(("teacher", "global"), key=lambda n: it["cand"][n]["rerr"]))
json.dump([{k: v for k, v in it.items() if k in ("tac", "obj", "cand")} for it in items], open(f"ablation/pilot_robosoft/rss2_multistart_s2_k{K}.json", "w"))
