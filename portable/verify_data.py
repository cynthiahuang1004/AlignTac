"""Check that an extracted bundle is self-contained: no dangling symlink, datasets of the student configs load, the frozen
encoder checkpoint and the meshes load, one CPU forward pass works.  Run from the AlignTac folder: python portable/verify_data.py"""
import glob, json, os, random, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, ROOT); sys.path.insert(0, "scripts")
import numpy as np, torch
from vistacfusion.engine.train import merge_configs
from vistacfusion.data.dataset import build_datasets
from vistacfusion.models.model import build_model
B = "/media/hdd/ihsuan"; P = "ablation/pilot_robosoft"; ok = True
n = subprocess.run(f"find {B}/gs_blender {B}/VisTacFusion -xtype l | wc -l", shell=True, capture_output=True, text=True).stdout.strip()
ex = subprocess.run(f"find {B}/gs_blender {B}/VisTacFusion -xtype l | head -5", shell=True, capture_output=True, text=True).stdout
print(f"dangling symlinks: {n}"); print(ex, end=""); ok &= (n == "0")
cfgs = sys.argv[1:] or [f"{P}/data_T_k25_rf.yaml", f"{P}/data_T_k25_dr10_al.yaml", f"{P}/data_A_loo3_obsf.yaml", f"{P}/data_A_loo3_syn.yaml", f"{P}/data_T_k25_rf_s2recal.yaml"]
model = None
for d in cfgs:
    try:
        cfg = merge_configs("ablation/encoder/tac_sitr_single.yaml", f"{P}/train_pilot_e150_pm.yaml", d)
        tr, va = build_datasets(cfg); random.seed(0)
        for i in random.sample(range(len(tr)), min(150, len(tr))) :
            b = tr[i]
        for i in random.sample(range(len(va)), min(50, len(va))):
            b = va[i]
        print(f"OK   {d}: train {len(tr)}, val {len(va)}; sample keys {sorted(b)[:6]}")
        if model is None:
            model = build_model(cfg).eval()
            x = {k: (v[None] if torch.is_tensor(v) else torch.as_tensor([v]) if isinstance(v, (int, np.integer)) else v) for k, v in b.items()}
            with torch.no_grad():
                out = model(x["rgb"], x["tactile"], config="tactile", object_ids=x.get("object"))
            print(f"OK   model forward on CPU: depth {tuple(out['depth'].shape)}")
    except Exception as e:
        ok = False; print(f"FAIL {d}: {type(e).__name__}: {str(e)[:300]}")
for r in ("real_filtered_testA", "real_loo3_test", "real_s2_testhalf", "real_s2_poolcheck"):
    pj = glob.glob(f"{B}/gs_blender/{r}/*/session_*/sensor_0000/raw_data/*_pose.json"); bad = 0
    for p in pj:
        u = os.path.dirname(os.path.dirname(p)); i = os.path.basename(p)[:4]
        bad += not (os.path.exists(p.replace("_pose.json", "_gt.npy")) and os.path.exists(f"{u}/samples/{i}.png"))
    print(f"{'OK  ' if pj and not bad else 'FAIL'} eval root {r}: {len(pj)} frames, {bad} incomplete"); ok &= bool(pj) and not bad
try:
    import build_real_filtered_new as BR
    for o in sorted(os.listdir(f"{B}/gs_blender/real_filtered")):
        BR.get_zmap(o)
    print("OK   mesh height maps for", len(os.listdir(f"{B}/gs_blender/real_filtered")), "objects")
except Exception as e:
    ok = False; print("FAIL meshes:", repr(e)[:200])
print("BUNDLE", "OK" if ok else "INCOMPLETE")
