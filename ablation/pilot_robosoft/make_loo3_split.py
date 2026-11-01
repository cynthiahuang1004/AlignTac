"""New-object labeling (leave-three-objects-out): roots for labeling the held-out objects from the mesh alone.

Held-out objects (as in the paper's held-out-object study): pattern_04_3_lines_angle_2, pattern_31_rod, pattern_33.
Session-1 frames are independent presses (one press per frame), so the split is by frame index:
  odd index  -> UNLABELED POOL: pseudo-labeled (teacher pose + aligner trained on the 9 seen objects), used for training
  even index -> TEST: evaluation only (true labels never used for training or validation; includes the idx % 10 == 0 val frames)
Writes: gs_blender/real_loo3 (symlink root with the three objects only, all frames; labeled by pseudo_label.py --unlabeled-only),
        gs_blender/real_loo3_test (mirror root with the TEST frames and their true labels),
        ablation/pilot_robosoft/loo3_test_frames.json (exclude_frames for the merged training roots).
"""
import glob, json, os, os.path as osp, shutil
G = "/media/hdd2/ihsuan/gs_blender"; REAL = f"{G}/real_filtered"
HELD = ["pattern_04_3_lines_angle_2", "pattern_31_rod", "pattern_33"]
os.chdir(osp.dirname(osp.dirname(osp.dirname(osp.abspath(__file__)))))
def mirror(root, keep):
    shutil.rmtree(root, ignore_errors=True); n = 0
    for o in HELD:
        for unit in sorted(glob.glob(f"{REAL}/{o}/session_*/sensor_0000")):
            sess = unit.split("/")[-2]; ou = f"{root}/{o}/{sess}/sensor_0000"
            for sub in ("samples", "raw_data", "rgb"):
                os.makedirs(f"{ou}/{sub}", exist_ok=True)
            for name in ("calibration", "id_map.json"):
                if osp.exists(f"{unit}/{name}"):
                    os.symlink(osp.realpath(f"{unit}/{name}"), f"{ou}/{name}")
            os.symlink(osp.realpath(f"{osp.dirname(unit)}/session.json"), f"{root}/{o}/{sess}/session.json")
            for png in sorted(glob.glob(f"{unit}/samples/*.png")):
                idx = osp.basename(png)[:4]
                if not keep(int(idx)):
                    continue
                for src in (f"samples/{idx}.png", f"raw_data/{idx}_gt.npy", f"raw_data/{idx}_pose.json", f"rgb/{idx}.png"):
                    if osp.exists(f"{unit}/{src}"):
                        os.symlink(osp.realpath(f"{unit}/{src}"), f"{ou}/{src}")
                n += 1
    return n
n_all = mirror(f"{G}/real_loo3", lambda i: True)
n_test = mirror(f"{G}/real_loo3_test", lambda i: i % 2 == 0)
frames = []
for o in HELD:
    for png in sorted(glob.glob(f"{REAL}/{o}/session_*/sensor_0000/samples/*.png")):
        idx = int(osp.basename(png)[:4])
        if idx % 2 == 0:
            frames.append(f"{o}/{png.split('/')[-4]}/sensor_0000/{idx:04d}")
json.dump({"root": "merged roots real_loo3_merge_*", "rule": "held-out objects: even frame index = TEST (never trained on); odd = unlabeled pool",
           "frames": frames}, open("ablation/pilot_robosoft/loo3_test_frames.json", "w"), indent=0)
print(f"real_loo3: {n_all} frames; real_loo3_test: {n_test} frames; exclude list {len(frames)}")
