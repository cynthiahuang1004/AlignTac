# Running AlignTac away from the server

Everything in the code base (configs, dataset manifests, ~600k symlinks) uses absolute paths under `/media/hdd/ihsuan`.
The bundle is therefore extracted anywhere and `/media/hdd/ihsuan` is made a symlink to it (`setup.sh`).

## Bundle (built by `portable/build_bundle.sh`, checked by `portable/verify_bundle.sh`)
| Archive | Content | Needed for |
|---|---|---|
| `01_code.tar.zst` | `VisTacFusion/AlignTac` (code, configs, result JSONs, paper, session-2 raw captures, aligners, learned renderers, git history; no `runs/`), `VisTacFusion/weights/SITR_B18.pth` | everything |
| `02_real_core.tar.zst` | meshes, session-1 labeled root and test split, K = 25 pseudo-label roots (all variants), new-object roots, session-2 roots | K = 25 students, new-object students, session-2 |
| `03_sim_subset.tar.zst` | 12 pattern objects of `renders_v3`: depth, pose, normals, RGB and the `samples_a_k25`, `samples_bc_loo`, `samples_bc_k25` renderings | required by the data loader of every student; training frames for the new-object students |
| `02b_real_rest.tar.zst` | all other `gs_blender/real_*` roots (K = 10 / 50 / 100, sensor B, additional objects) | other K values, sensor B; not needed for the round-2 jobs |
Not in the bundle: `runs/` (student checkpoints, 300+ GB) and the full `renders_v3` (187 GB).

## Colab
Upload the archives and `setup.sh` to `MyDrive/aligntac_bundle/`, open `portable/AlignTac_colab.ipynb`, pick a GPU runtime, run the cells.

## Local Linux or WSL2 (e.g. RTX 3060, 8 GB)
```bash
bash setup.sh /path/to/archives ~/aligntac                 # asks for sudo once to create /media/hdd/ihsuan -> ~/aligntac
cd /media/hdd/ihsuan/VisTacFusion/AlignTac
export TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1
python portable/run_jobs.py --bench
python portable/run_jobs.py --jobs portable/jobs_loo3.tsv --parallel 1 --sync-to ~/aligntac_runs
```
One job at batch 32 takes about 5.5 GB of GPU memory; an interrupted job resumes from `latest.pt` when the same command is run again.

## Bringing results back
Copy `aligntac_runs/_results/*.json` to the server and merge them into `ablation/pilot_robosoft/` (keys are `<run>/<tag>`, plain dict update);
copy `aligntac_runs/<run>/{best_depth.pt,best_pose.pt,final.pt,history.json}` into `AlignTac/runs/<run>/` if the checkpoints are wanted there.
