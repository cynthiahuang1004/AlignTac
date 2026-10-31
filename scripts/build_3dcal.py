"""Convert the 3D Cal dataset (DIGIT / GelSight Mini, ruby sphere probe r=2 mm) to the
real_filtered layout used by VisTacFusion, with per-pixel depth and normal ground truth
computed analytically from the sphere equation.

The probe tip is a sphere of known radius R pressed to a known (x_mm, y_mm, penetration_depth_mm).
At pixel (u, v) with pixel size p (mm/px), the horizontal distance from the sphere centre is
  d = sqrt((u - cx)^2 + (v - cy)^2) * p
If d < R, the contact depth at that pixel is
  depth(u,v) = penetration_depth - (R - sqrt(R^2 - d^2))
clamped to [0, penetration_depth].  Normal = normalised gradient of depth.

Each (x, y, depth) location has 30 repeated images; we use one for train, one for val, one for test.

usage:
  python scripts/build_3dcal.py --sensor digit  --out /media/hdd2/ihsuan/gs_blender/real_3dcal_digit
  python scripts/build_3dcal.py --sensor gsmini --out /media/hdd2/ihsuan/gs_blender/real_3dcal_gsmini
"""
import argparse, csv, json, math, os, os.path as osp
import cv2, numpy as np
from PIL import Image

ROOT = "/media/hdd2/ihsuan/3dcal"
SENSOR_DIRS = {"digit": "digit/digit_calibration_data", "gsmini": "gsmini/gsmini_calibration_data"}
# output image size (our pipeline expects 224x224)
OUT_SIZE = 224


def sphere_depth_normal(cx_px, cy_px, R_mm, press_mm, px_per_mm, H, W):
    """Analytic depth and normal maps for a sphere pressed into a flat surface."""
    yy, xx = np.mgrid[:H, :W]
    d_px = np.sqrt((xx - cx_px) ** 2 + (yy - cy_px) ** 2)
    d_mm = d_px / px_per_mm
    inside = d_mm < R_mm
    # height of sphere surface above the flat gel at distance d from centre
    h = np.where(inside, R_mm - np.sqrt(np.maximum(R_mm ** 2 - d_mm ** 2, 0)), 0.0)
    depth = np.clip(press_mm - h, 0, None).astype(np.float32)
    depth[~inside] = 0.0
    # normal from gradient of the depth surface (finite differences)
    gy, gx = np.gradient(depth)
    gx_mm = gx * px_per_mm; gy_mm = gy * px_per_mm
    norm = np.stack([-gx_mm, -gy_mm, np.ones_like(gx_mm)], axis=-1)
    norm /= np.linalg.norm(norm, axis=-1, keepdims=True) + 1e-12
    return depth, norm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sensor", required=True, choices=list(SENSOR_DIRS))
    ap.add_argument("--out", required=True)
    ap.add_argument("--train-per-loc", type=int, default=1, help="images per location for train")
    ap.add_argument("--val-per-loc", type=int, default=1)
    ap.add_argument("--test-per-loc", type=int, default=1)
    ap.add_argument("--min-press", type=float, default=0.0, help="min penetration depth to include (mm)")
    a = ap.parse_args()
    sd = f"{ROOT}/{SENSOR_DIRS[a.sensor]}"
    meta = json.load(open(f"{sd}/annotations/metadata.json"))
    R = meta["probe_radius_mm"]; ppmm = meta["px_per_mm"]
    rows = list(csv.DictReader(open(f"{sd}/annotations/annotations.csv")))
    blank = np.asarray(Image.open(f"{sd}/blank_images/blank.png").convert("RGB"))
    H0, W0 = blank.shape[:2]
    print(f"{a.sensor}: R={R} mm, px/mm={ppmm}, image {W0}x{H0}, {len(rows)} rows", flush=True)

    # group by (x, y, depth)
    from collections import defaultdict
    groups = defaultdict(list)
    for r in rows:
        k = (float(r["x_mm"]), float(r["y_mm"]), float(r["penetration_depth_mm"]))
        groups[k].append(r)

    # centre crop to square
    crop = min(H0, W0)
    y0c, x0c = (H0 - crop) // 2, (W0 - crop) // 2
    blank_sq = cv2.resize(blank[y0c:y0c+crop, x0c:x0c+crop], (OUT_SIZE, OUT_SIZE), interpolation=cv2.INTER_AREA)

    obj_name = f"sphere_r{R}mm"
    os.makedirs(a.out, exist_ok=True)
    # one "session" per (x, y) location; multiple depths are different samples within the session
    xy_locs = sorted(set((k[0], k[1]) for k in groups))
    review_tiles = []
    total = {"train": 0, "val": 0, "test": 0}
    for si, (xm, ym) in enumerate(xy_locs):
        unit = f"{a.out}/{obj_name}/session_{si:03d}/sensor_0000"
        for sub in ("samples", "rgb", "raw_data"):
            os.makedirs(f"{unit}/{sub}", exist_ok=True)
        idx = 0; cells = []
        depth_keys = sorted(k for k in groups if k[0] == xm and k[1] == ym)
        for k in depth_keys:
            press = k[2]
            if press < a.min_press:
                continue
            imgs = groups[k]
            # split: first train_per_loc for train, next val, next test
            n_take = a.train_per_loc + a.val_per_loc + a.test_per_loc
            for ji, r in enumerate(imgs[:n_take]):
                cx_px = float(r["x_px"]); cy_px = float(r["y_px"])
                # crop and resize the pixel centre
                cx_c = (cx_px - x0c) * OUT_SIZE / crop
                cy_c = (cy_px - y0c) * OUT_SIZE / crop
                ppmm_out = ppmm * crop / OUT_SIZE
                depth, norm = sphere_depth_normal(cx_c, cy_c, R, press, ppmm_out, OUT_SIZE, OUT_SIZE)
                # depth in metres for our pipeline
                depth_m = (depth * 1e-3).astype(np.float32)
                im = np.asarray(Image.open(f"{sd}/probe_images/{r['img_name']}").convert("RGB"))
                im_sq = cv2.resize(im[y0c:y0c+crop, x0c:x0c+crop], (OUT_SIZE, OUT_SIZE), interpolation=cv2.INTER_AREA)
                Image.fromarray(im_sq).save(f"{unit}/samples/{idx:04d}.png")
                Image.fromarray(im_sq).save(f"{unit}/rgb/{idx:04d}.png")
                np.save(f"{unit}/raw_data/{idx:04d}_gt.npy", depth_m)
                np.save(f"{unit}/raw_data/{idx:04d}_normal.npy", ((norm * 0.5 + 0.5) * 255).astype(np.uint8))
                # pose: contact centre in metres, no rotation
                sx, sy = xm * 1e-3, ym * 1e-3
                json.dump({"obj_name": obj_name, "sample_x": sx, "sample_y": sy, "sample_z": float(press * 1e-3),
                           "location": [sx, -sy, float(-press * 1e-3)], "rotation_euler": [0.0, 0.0, 0.0],
                           "scale": [0.001]*3, "fixed_scale": 1000.0,
                           "source": {"dataset": "3dcal", "sensor": a.sensor, "file": r["img_name"],
                                      "cx_px": cx_c, "cy_px": cy_c, "R_mm": R, "press_mm": press}},
                          open(f"{unit}/raw_data/{idx:04d}_pose.json", "w"))
                split = "train" if ji < a.train_per_loc else ("val" if ji < a.train_per_loc + a.val_per_loc else "test")
                cells.append({"gx": idx, "gy": 0, "split": split, "press_mm": press})
                total[split] += 1
                if si % 50 == 0 and ji == 0 and len(review_tiles) < 24:
                    ov = im_sq.copy(); cs, _ = cv2.findContours((depth > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    cv2.drawContours(ov, cs, -1, (255, 255, 0), 1)
                    dc = cv2.applyColorMap((np.clip(depth / max(depth.max(), 1e-6), 0, 1) * 255).astype(np.uint8), cv2.COLORMAP_VIRIDIS)[:, :, ::-1]
                    review_tiles.append(np.concatenate([ov, dc], 1))
                idx += 1
        json.dump({"obj": obj_name, "base_rotation": [0.0, 0.0, 0.0], "rotation_step": 0.0,
                   "fixed_scale": 1000.0, "NUM_OBJ_SAMPLES": idx, "OBJ_DEPTH_MIN": 0.001, "OBJ_DEPTH_MAX": 0.003,
                   "z_anchor": 0.0, "capture": f"3DCal {a.sensor} (sphere probe r={R} mm)", "valid_cells": cells},
                  open(f"{a.out}/{obj_name}/session_{si:03d}/session.json", "w"), indent=1)
    # blank background
    os.makedirs(f"{a.out}/background", exist_ok=True)
    Image.fromarray(blank_sq).save(f"{a.out}/background/blank.png")
    # review grid
    if review_tiles:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        cols = 4; rows_n = -(-len(review_tiles) // cols)
        fig, axes = plt.subplots(rows_n, cols, figsize=(cols * 3.5, rows_n * 1.8), squeeze=False)
        for ax in axes.flat: ax.axis("off")
        for ax, im in zip(axes.flat, review_tiles): ax.imshow(im)
        fig.tight_layout(h_pad=0.2, w_pad=0.2); fig.savefig(f"{a.out}/review.png", dpi=100); plt.close(fig)
    print(f"done: {sum(total.values())} frames ({total}) in {len(xy_locs)} sessions -> {a.out}", flush=True)


if __name__ == "__main__":
    main()
