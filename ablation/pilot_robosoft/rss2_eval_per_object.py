"""Per-object breakdown of a student's test metrics (same data path and metric definitions as eval_cross_session.py).

usage: python ablation/pilot_robosoft/rss2_eval_per_object.py --root <test root> --tag loo3test --json <out.json> run:prefix ...
Each run is scored at best_depth.pt (dense metrics) and best_pose.pt (pose metrics); the "all" entry must reproduce the stored
numbers of eval_cross_session.py.  Translation is also split into its two pose-frame axes (|dx|, |dy|).
"""
import argparse
import contextlib
import copy
import io
import json
import math
import os.path as osp
import re

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader

from vistacfusion.data.dataset import SimVisuoTactileDataset
from vistacfusion.engine.train import load_checkpoint
from vistacfusion.models.model import build_model
from vistacfusion.utils.config import merge_configs

OUT = "/media/hdd/ihsuan/VisTacFusion/AlignTac/runs"
TRAIN = "ablation/pilot_robosoft/train_pilot_e50.yaml"
IOU_THR = 0.05
MM = 41.14   # one normalized pose unit in mm (trans_l1 * MM / 2 = mean coordinate error in mm, as in RSS_ROUND2_RESULTS.md)


@torch.no_grad()
def per_frame(model, loader, device):
    rows = []
    for b in loader:
        b = {k: (v.to(device) if torch.is_tensor(v) else v) for k, v in b.items()}
        out = model(b["rgb"], b["tactile"], config="tactile", object_ids=b.get("object"))
        pred, gt = out["depth"].float(), b["depth"].float()
        m = gt > 0
        err = (pred - gt).abs()
        pn = F.normalize(out["normal"].float(), dim=1); gn = F.normalize(b["normal"].float(), dim=1)
        ang = torch.acos((pn * gn).sum(1).clamp(-1 + 1e-6, 1 - 1e-6)) * 180 / math.pi
        pm = pred > IOU_THR
        iou = (pm & m).flatten(1).sum(1).float() / (pm | m).flatten(1).sum(1).float().clamp(min=1)
        se2, gp = out["se2"], b["pose"]
        dcos = (se2[:, 0] * gp[:, 0] + se2[:, 1] * gp[:, 1]).clamp(-1 + 1e-6, 1 - 1e-6)
        rot = torch.acos(dcos) * 180 / math.pi
        d = (se2[:, 2:] - gp[:, 2:]).abs()
        for i in range(pred.shape[0]):
            mi = m[i]
            rows.append((int(b["object"][i]), float((err[i] * mi).sum()), int(mi.sum()), float((ang[i] * mi[0]).sum()),
                         float(iou[i]), float(rot[i]), float(d[i, 0]), float(d[i, 1])))
    return np.array(rows, dtype=np.float64)


def summarize(r):
    return {"n": int(len(r)), "c_mae": float(r[:, 1].sum() / max(1, r[:, 2].sum())), "normal_deg": float(r[:, 3].sum() / max(1, r[:, 2].sum())),
            "iou": float(r[:, 4].mean()), "rot_deg": float(r[:, 5].mean()), "rot_med": float(np.median(r[:, 5])),
            "trans_mm": float((r[:, 6] + r[:, 7]).mean() / 2 * MM), "dx_mm": float(r[:, 6].mean() * MM), "dy_mm": float(r[:, 7].mean() * MM)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--root", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--json", required=True)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--model", default="ablation/encoder/tac_sitr_single.yaml")
    args = ap.parse_args()
    results = json.load(open(args.json)) if osp.exists(args.json) else {}
    for spec in args.runs:
        run, prefix = spec.split(":")
        base = re.sub(r'(_seed\d+|_cls)+$', '', run)
        data_cfg = f"ablation/pilot_robosoft/data_{base}.yaml"
        if not osp.exists(data_cfg):
            data_cfg = "ablation/pilot_robosoft/data_A_realonly.yaml"
        cfg = merge_configs(args.model, TRAIN, data_cfg)
        with contextlib.redirect_stdout(io.StringIO()):
            old_ds = SimVisuoTactileDataset(cfg, cfg.image_size, augment=False, split="val", data_section="real")
            cfg_new = copy.deepcopy(cfg)
            cfg_new["real"]["root"] = args.root
            cfg_new["real"]["val_every"] = 1
            cfg_new["real"].pop("test_objects", None)
            cfg_new["real"].pop("exclude_frames", None)
            if cfg_new["real"].get("bg_subtract"):     # kept identical to eval_cross_session.py so that "all" reproduces its numbers
                cfg_new["real"]["bg_subtract"] = "real_new"
            ds =SimVisuoTactileDataset(cfg_new, cfg.image_size, augment=False, split="all", data_section="real",
                                        shared_obj_map=old_ds._obj_to_id)
            model = build_model(cfg).to(args.device).eval()
        names = {v: k for k, v in old_ds._obj_to_id.items()}
        dl = DataLoader(ds, batch_size=args.batch, shuffle=False, num_workers=4)
        for ck, tag in (("best_depth.pt", args.tag), ("best_pose.pt", args.tag + "_bp")):
            path = osp.join(OUT, prefix + run, ck)
            if not osp.exists(path):
                print(f"{prefix}{run}: no {ck}", flush=True); continue
            with contextlib.redirect_stdout(io.StringIO()):
                load_checkpoint(path, model, device=args.device)
            r = per_frame(model, dl, args.device)
            res = {"all": summarize(r)}
            for o in sorted(set(r[:, 0].astype(int))):
                res[names.get(o, str(o))] = summarize(r[r[:, 0] == o])
            results[f"{prefix}{run}/{tag}"] = res
            a = res["all"]
            print(f"{prefix}{run:24s} {ck:14s} all: cMAE {a['c_mae']:.4f} IoU {a['iou']:.3f} rot {a['rot_deg']:.2f} trans {a['trans_mm']:.2f} mm n {a['n']}", flush=True)
            json.dump(results, open(args.json, "w"), indent=1)


if __name__ == "__main__":
    main()
