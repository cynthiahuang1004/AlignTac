"""Session-2 press-level split on the corrected labels (D12 follow-up: label-free cross-session adaptation re-run).
Same presses as the paper (make_s2_split.py -> s2_pool_presses.json): per object the presses (run, iteration) are sorted and
alternated, even -> unlabeled pool, odd -> test. Applied to the corrected roots:
  real_s2_kin_pool          pool presses, all usable frames of real_s2_kin_all (images only; labels used for --eval-gt reports only)
  real_s2_kin_testhalf      test presses, all usable frames of real_s2_kin_all (corrected labels)
  real_s2_kin_testhalf_c464 test presses, curated frames only (real_s2_kin_curated854) = the paper's 464-frame test half
Symlinks, re-indexed per unit as in make_s2_split.py. Existing roots are never touched (rerun is a no-op)."""
import collections, glob, json, os, os.path as osp, sys
sys.path.insert(0, "scripts")
import build_real_filtered_new as B

G = "/media/hdd/ihsuan/gs_blender"
pool = json.load(open("ablation/pilot_robosoft/s2_pool_presses.json"))
poolset = {(k.rsplit("/", 1)[0], int(k.rsplit("/", 1)[1]), int(it)) for k, its in pool.items() for it in its}
sim2real = {v[0]: k for k, v in B.OBJ_MAP.items()}


def mirror(src, dst, want_pool):
    if osp.exists(dst):
        print(f"{dst} exists, left as is"); return None
    n = collections.Counter()
    for unit in sorted(glob.glob(f"{src}/*/session_*/sensor_0000")):
        obj, sess = unit.split("/")[-3], unit.split("/")[-2]; k = 0
        for pj in sorted(glob.glob(f"{unit}/raw_data/*_pose.json")):
            s = json.load(open(pj))["source"]
            if ((sim2real[obj], int(s["run"]), int(s["iteration"])) in poolset) != want_pool:
                continue
            idx = osp.basename(pj)[:4]; ou = f"{dst}/{obj}/{sess}/sensor_0000"
            for sub in ("samples", "raw_data", "rgb"):
                os.makedirs(f"{ou}/{sub}", exist_ok=True)
            for a, b in ((f"samples/{idx}.png", f"samples/{k:04d}.png"), (f"raw_data/{idx}_gt.npy", f"raw_data/{k:04d}_gt.npy"),
                         (f"raw_data/{idx}_pose.json", f"raw_data/{k:04d}_pose.json"), (f"rgb/{idx}.png", f"rgb/{k:04d}.png")):
                if osp.exists(f"{unit}/{a}"):
                    os.symlink(f"{unit}/{a}", f"{ou}/{b}")      # stable /media/hdd/ihsuan path (mount points swap across reboots)
            k += 1; n[obj] += 1
        if k:
            sj = json.load(open(f"{osp.dirname(unit)}/session.json")); sj["NUM_OBJ_SAMPLES"] = k
            if "valid_cells" in sj:
                sj["valid_cells"] = sj["valid_cells"][:k]
            json.dump(sj, open(f"{dst}/{obj}/{sess}/session.json", "w"))
    print(f"{dst}: {sum(n.values())} frames {dict(n)}")
    return n


mirror(f"{G}/real_s2_kin_all", f"{G}/real_s2_kin_pool", want_pool=True)
mirror(f"{G}/real_s2_kin_all", f"{G}/real_s2_kin_testhalf", want_pool=False)
mirror(f"{G}/real_s2_kin_curated854", f"{G}/real_s2_kin_testhalf_c464", want_pool=False)
