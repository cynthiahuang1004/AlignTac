"""New-object study, additional held-out fold: split roots + data configs (generalizes make_loo3_split.py, which is fold 1).

usage: python ablation/pilot_robosoft/rss2_make_fold.py <tag> <held-out object> ...
Session-1 frames are independent presses, so the split of the held-out objects is by frame index, exactly as in fold 1:
  odd index  -> UNLABELED POOL (pseudo-labeled, used for training)      even index -> TEST (true labels never used for training)
Writes (refuses to overwrite): gs_blender/real_<tag> (held-out objects, all frames), gs_blender/real_<tag>_test (TEST frames),
  ablation/pilot_robosoft/<tag>_test_frames.json, data_A_<tag>_teacher.yaml (= data_A_bgcondloo.yaml with the new held-out objects
  and sim renderings samples_bc_loo_<tag>) and data_A_<tag>_realonly.yaml (lower bound: real labels of the 9 seen objects only).
"""
import glob, json, os, os.path as osp, sys
import yaml

STABLE = "/media/hdd/ihsuan"; G = f"{STABLE}/gs_blender"; REAL = f"{G}/real_filtered"; P = "ablation/pilot_robosoft"
tag, HELD = sys.argv[1], sys.argv[2:]
os.chdir(osp.dirname(osp.dirname(osp.dirname(osp.abspath(__file__)))))
assert len(HELD) >= 1 and all(osp.isdir(f"{REAL}/{o}") for o in HELD), HELD


def target(p):
    """Link target on the stable path (the project disk's mount point changes across reboots; STABLE holds two shim links)."""
    t = osp.realpath(p)
    for sub in ("gs_blender", "VisTacFusion"):
        phys = osp.realpath(f"{STABLE}/{sub}")
        if t.startswith(phys + "/"):
            return f"{STABLE}/{sub}" + t[len(phys):]
    return t


def mirror(root, keep):
    assert not osp.exists(root), f"{root} exists: not overwriting"
    n = 0
    for o in HELD:
        for unit in sorted(glob.glob(f"{REAL}/{o}/session_*/sensor_0000")):
            sess = unit.split("/")[-2]; ou = f"{root}/{o}/{sess}/sensor_0000"
            for sub in ("samples", "raw_data", "rgb"):
                os.makedirs(f"{ou}/{sub}", exist_ok=True)
            for name in ("calibration", "id_map.json"):
                if osp.exists(f"{unit}/{name}"):
                    os.symlink(target(f"{unit}/{name}"), f"{ou}/{name}")
            os.symlink(target(f"{osp.dirname(unit)}/session.json"), f"{root}/{o}/{sess}/session.json")
            for png in sorted(glob.glob(f"{unit}/samples/*.png")):
                idx = osp.basename(png)[:4]
                if not keep(int(idx)):
                    continue
                for src in (f"samples/{idx}.png", f"raw_data/{idx}_gt.npy", f"raw_data/{idx}_pose.json", f"rgb/{idx}.png"):
                    if osp.exists(f"{unit}/{src}"):
                        os.symlink(target(f"{unit}/{src}"), f"{ou}/{src}")
                n += 1
    return n


n_all = mirror(f"{G}/real_{tag}", lambda i: True)
n_test = mirror(f"{G}/real_{tag}_test", lambda i: i % 2 == 0)
frames = []
for o in HELD:
    for png in sorted(glob.glob(f"{REAL}/{o}/session_*/sensor_0000/samples/*.png")):
        idx = int(osp.basename(png)[:4])
        if idx % 2 == 0:
            frames.append(f"{o}/{png.split('/')[-4]}/sensor_0000/{idx:04d}")
fj = f"{P}/{tag}_test_frames.json"; assert not osp.exists(fj)
json.dump({"root": f"merged roots real_{tag}_merge_*", "rule": "held-out objects: even frame index = TEST (never trained on); odd = unlabeled pool",
           "frames": frames}, open(fj, "w"), indent=0)
for name, src, sub in ((f"A_{tag}_teacher", "A_bgcondloo", f"samples_bc_loo_{tag}"), (f"A_{tag}_realonly", "A_realonly", None)):
    c = yaml.safe_load(open(f"{P}/data_{src}.yaml"))
    assert sorted(c["real"]["test_objects"]) == ["pattern_04_3_lines_angle_2", "pattern_31_rod", "pattern_33"]
    c["real"]["test_objects"] = list(HELD)
    if sub:
        assert c["sim"]["tactile_subdir"] == "samples_bc_loo"; c["sim"]["tactile_subdir"] = sub
    out = f"{P}/data_{name}.yaml"; assert not osp.exists(out)
    yaml.safe_dump(c, open(out, "w"), sort_keys=False); print("wrote", out)
print(f"real_{tag}: {n_all} frames; real_{tag}_test: {n_test} frames; exclude list {len(frames)}")
