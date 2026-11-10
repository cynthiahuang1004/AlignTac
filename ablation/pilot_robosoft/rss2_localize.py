"""Single-touch localization (RSS round 2, P1-7): estimate the planar contact state on a known mesh from ONE press.

Methods, per student (pose from best_pose.pt, depth from best_depth.pt):
  head            the student's pose head
  head+align      + test-time alignment with the K-shot aligner (six updates)
  global          exhaustive search (theta in [0, 360), x, y in +-7 mm, 3 deg / 0.5 mm steps) of the mesh depth against the student's
                  PREDICTED depth inside the model's 0.816 view; no pose head, no object-specific prior beyond the mesh
  global+align    + alignment from that start
The search window is +-7 mm around the sensor centre (local localization on a known object, not whole-object search as in Tac2Pose).
Metrics: rotation error mean / median, symmetry-aware (modulo the mesh's rotational period), translation = mean(|dx|, |dy|) in mm,
success = (symmetry-aware rot < 2 deg and trans < 0.5 mm) and the looser (5 deg, 1 mm).
usage: python ablation/pilot_robosoft/rss2_localize.py --device cuda:0 T_k25_realonly:pilot150_:25 T_k25_rf:pilot150_:25
"""
import argparse, contextlib, copy, io, json, math, os, os.path as osp, sys
import cv2, numpy as np, torch
from PIL import Image
from torch.utils.data import DataLoader
ROOT = osp.dirname(osp.dirname(osp.dirname(osp.abspath(__file__))))
sys.path.insert(0, ROOT); sys.path.insert(0, osp.join(ROOT, "scripts")); sys.path.insert(0, osp.join(ROOT, "scripts", "tactile_render"))
import fit_baselines as FB  # noqa: E402
from fit_baselines import B, mesh_depth_bilinear, rot_err  # noqa: E402
from train_aligner import Aligner, refine  # noqa: E402
from vistacfusion.data.dataset import SimVisuoTactileDataset  # noqa: E402
from vistacfusion.engine.train import load_checkpoint  # noqa: E402
from vistacfusion.models.model import build_model  # noqa: E402
from vistacfusion.utils.config import merge_configs  # noqa: E402

OUT = osp.join(ROOT, "runs"); G = "/media/hdd/ihsuan/gs_blender"
SIDE = int(math.floor(224 * 0.816)); OFF = (224 - SIDE) // 2
SPLITS = {"testA": f"{G}/real_filtered_testA", "s2half": f"{G}/real_s2_testhalf"}
_u = np.arange(0, 224, 4) + 2.0; _win = (_u >= OFF) & (_u < OFF + SIDE)


@torch.no_grad()
def global_fit_crop(obj, pred_crop_mm, p, dev):
    """Global search against the predicted depth inside the model's view.  pred_crop_mm: [224, 224] prediction of the 0.816 crop."""
    full = np.zeros((224, 224), np.float32); full[OFF:OFF + SIDE, OFF:OFF + SIDE] = cv2.resize(pred_crop_mm, (SIDE, SIDE), interpolation=cv2.INTER_LINEAR)
    tgt = torch.from_numpy(full[2::4, 2::4]).to(dev); w = torch.from_numpy(_win).to(dev); tgt = tgt[w][:, w]
    c = torch.cartesian_prod(torch.deg2rad(torch.arange(0, 360, 3.0)), torch.arange(-7, 7.01, 0.5), torch.arange(-7, 7.01, 0.5)).to(dev)
    pose = torch.cat([c, torch.full((len(c), 1), float(p), device=dev)], 1); best = (1e9, None)
    for i in range(0, len(pose), 8192):
        cc = pose[i:i + 8192]; e = (mesh_depth_bilinear(obj, cc, dev, stride=4)[:, w][:, :, w] - tgt[None]).abs().mean((1, 2)); j = int(e.argmin())
        if float(e[j]) < best[0]:
            best = (float(e[j]), cc[j].tolist())
    return best[1]


@torch.no_grad()
def run_split(mp, md, A, ds, dev, period, do_global=True):
    rows = []; i0 = 0
    for b in DataLoader(ds, batch_size=32, num_workers=4):
        n = len(b["tactile"]); units = [ds.samples[i0 + j] for j in range(n)]; i0 += n
        x = b["tactile"].to(dev); oid = b["object"].to(dev)
        se2 = mp(x, x, config="tactile", object_ids=oid)["se2"].float().cpu()
        dmap = md(x, x, config="tactile", object_ids=oid)["depth"][:, 0].float().clamp(min=0).cpu().numpy()
        objs = [u.split("/")[-3] for u, _ in units]; half = [ds.unit_meta[u]["half"] * 1e3 for u, _ in units]
        img = torch.from_numpy(np.stack([np.array(Image.open(osp.join(u, "samples", f"{s:04d}.png")).convert("RGB"), np.float32).transpose(2, 0, 1) / 127.5 - 1 for u, s in units])).to(dev)
        press = [float(np.clip(dmap[j].max(), 0.3, 1.6)) for j in range(n)]
        est = {"head": torch.tensor([[math.atan2(float(se2[j, 1]), float(se2[j, 0])), float(se2[j, 2]) * half[j], float(se2[j, 3]) * half[j], press[j]] for j in range(n)], device=dev)}
        est["head+align"] = refine(A, objs, img, est["head"].clone(), dev, iters=6)
        if do_global:
            est["global"] = torch.tensor([global_fit_crop(objs[j], dmap[j], press[j], dev) for j in range(n)], dtype=torch.float32, device=dev)
            est["global+align"] = refine(A, objs, img, est["global"].clone(), dev, iters=6)
        for j, (u, s) in enumerate(units):
            P = json.load(open(osp.join(u, "raw_data", f"{s:04d}_pose.json"))); g = (P["rotation_euler"][2], P["sample_x"] * 1e3, P["sample_y"] * 1e3)
            r = {"obj": objs[j]}
            for k, pz in est.items():
                th, xx, yy = (float(v) for v in pz[j, :3])
                r[k] = (rot_err(th, g[0]), rot_err(th, g[0], period(objs[j])), (abs(xx - g[1]) + abs(yy - g[2])) / 2)
            rows.append(r)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+", help="run:prefix:K"); ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--splits", default="testA,s2half"); ap.add_argument("--json", default=osp.join(ROOT, "ablation/pilot_robosoft/rss2_localize.json"))
    args = ap.parse_args(); os.chdir(ROOT); dev = args.device
    sym = json.load(open(FB.SYM)); period = lambda o: sym.get(o, {}).get("period_deg", 360.0)  # noqa: E731
    res = json.load(open(args.json)) if osp.exists(args.json) else {}
    for spec in args.runs:
        run, prefix, K = spec.split(":")[:3]; base = __import__("re").sub(r"(_seed\d+)+$", "", run)
        cfg = merge_configs("ablation/encoder/tac_sitr_single.yaml", "ablation/pilot_robosoft/train_pilot_e50.yaml", f"ablation/pilot_robosoft/data_{base}.yaml")
        with contextlib.redirect_stdout(io.StringIO()):
            c0 = copy.deepcopy(cfg); c0["real"]["root"] = f"{G}/real_filtered"; c0["real"].pop("exclude_frames", None)
            ref = SimVisuoTactileDataset(c0, cfg.image_size, augment=False, split="val", data_section="real")
            mp = build_model(cfg).to(dev).eval(); load_checkpoint(osp.join(OUT, prefix + run, "best_pose.pt"), mp, device=dev)
            md = build_model(cfg).to(dev).eval(); load_checkpoint(osp.join(OUT, prefix + run, "best_depth.pt"), md, device=dev)
        A = Aligner().to(dev).eval(); A.load_state_dict(torch.load(f"outputs/aligner_k{K}_realonly/aligner.pt", map_location=dev))
        for o in ref._obj_to_id:
            try:
                B.get_zmap(o)
            except Exception:
                pass
        for name in args.splits.split(","):
            with contextlib.redirect_stdout(io.StringIO()):
                c = copy.deepcopy(cfg); c["real"]["root"] = SPLITS[name]; c["real"]["val_every"] = 1; c["real"].pop("exclude_frames", None); c["real"].pop("test_objects", None)
                ds = SimVisuoTactileDataset(c, cfg.image_size, augment=False, split="all", data_section="real", shared_obj_map=ref._obj_to_id)
            rows = run_split(mp, md, A, ds, dev, period)
            for m in [k for k in rows[0] if k != "obj"]:
                v = np.array([r[m] for r in rows])
                out = dict(rot=float(v[:, 0].mean()), rot_median=float(np.median(v[:, 0])), rot_sym=float(v[:, 1].mean()), rot_sym_median=float(np.median(v[:, 1])),
                           trans=float(v[:, 2].mean()), trans_median=float(np.median(v[:, 2])), succ_2deg_05mm=float(((v[:, 1] < 2) & (v[:, 2] < 0.5)).mean()),
                           succ_5deg_1mm=float(((v[:, 1] < 5) & (v[:, 2] < 1.0)).mean()), n=len(v))
                res[f"{prefix}{run}/{name}/{m}"] = out
                print(f"{run:22s} {name:7s} {m:13s} rot {out['rot']:6.2f} (med {out['rot_median']:5.2f}) sym {out['rot_sym']:6.2f} (med {out['rot_sym_median']:5.2f})  trans {out['trans']:.2f} (med {out['trans_median']:.2f}) mm  "
                      f"succ 2deg/0.5mm {100 * out['succ_2deg_05mm']:5.1f}%  5deg/1mm {100 * out['succ_5deg_1mm']:5.1f}%  n={out['n']}", flush=True)
            json.dump(res, open(args.json, "w"), indent=1)


if __name__ == "__main__":
    main()
