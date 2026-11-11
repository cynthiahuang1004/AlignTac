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

## Local machine: Ubuntu, or Windows through WSL2 (e.g. RTX 3060, 8 GB)
Native Windows (PowerShell / Anaconda Prompt) is not supported: the data set is ~600k symlinks with absolute Linux paths and the
job scripts are bash.  WSL2 is Ubuntu running inside Windows with direct access to the NVIDIA GPU; nothing is dual-booted.

Windows only, once (PowerShell as administrator), then reboot and choose a user name / password when Ubuntu opens:
```powershell
wsl --install -d Ubuntu-22.04
```
Requirements: a current NVIDIA driver installed in Windows (do not install a driver or CUDA inside WSL), about 95 GB free on
the drive that holds WSL (C: by default; 20 GB archives, which can be deleted after setup, + 60 GB extracted + 7 GB environment
+ 2 GB of checkpoints per student), Windows sleep
turned off while jobs run.  With 16 GB of RAM give WSL 12 GB: create `C:\Users\<you>\.wslconfig` containing
`[wsl2]` / `memory=12GB`, then `wsl --shutdown`.

In the Ubuntu terminal (`<user>@<server>` is your usual ssh login):
```bash
mkdir -p ~/aligntac_bundle
rsync -avP --exclude '02b_*' <user>@<server>:/media/hdd-slam/users/ihsuan/aligntac_bundle/ ~/aligntac_bundle/   # 20 GB; re-run to resume
bash ~/aligntac_bundle/setup_local.sh ~/aligntac_bundle          # env "aligntac" (python 3.11, torch 2.5.1+cu121), extraction, sudo once
conda activate aligntac && cd /media/hdd/ihsuan/VisTacFusion/AlignTac
python portable/verify_data.py                                   # must end with BUNDLE OK
python portable/run_jobs.py --bench                              # steps/s, GPU memory, hours per student
nohup python portable/run_jobs.py --jobs portable/jobs_local.tsv --parallel 1 --workers 6 > ~/aligntac_jobs.log 2>&1 &
tail -f ~/aligntac_jobs.log outputs/rss_logs/rss2_A_loo3_syn_seed1.log
```
Keep everything inside the Linux home folder (`~`), not under `/mnt/c`.  One job at batch 32 takes about 5.5 GB of GPU memory.
A job that was interrupted (reboot, closed laptop, `wsl --shutdown`) resumes from the last finished epoch when the same
`run_jobs.py` command is run again.  Do not change the batch size: results would no longer be comparable with the server runs.
From Windows the Linux files are visible in Explorer under `\\wsl$\Ubuntu-22.04\home\<user>\`.

## Bringing results back
Local machine (from the AlignTac folder; a new folder on the server, nothing there is overwritten):
```bash
rsync -avP ablation/pilot_robosoft/loo3_results.json ablation/pilot_robosoft/rss2_testA_results.json outputs/rss_logs/rss2_*.log \
      <user>@<server>:/media/hdd-slam/users/ihsuan/aligntac_results_local/
```
then tell Claude, who merges the new keys (`<run>/<tag>`) into `ablation/pilot_robosoft/` without touching existing ones.
Colab: the same files are in `MyDrive/aligntac_runs/_results/`.  Checkpoints (`runs/<run>/{best_depth.pt,best_pose.pt,final.pt,history.json}`,
0.5 GB each) are only needed on the server if the model itself is to be re-evaluated there.
The overflow disk is mounted as `/media/hdd-slam` or `/media/hdd2` depending on the boot: use whichever has `users/ihsuan/aligntac_bundle`.
