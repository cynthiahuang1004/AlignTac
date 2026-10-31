# AlignTac

Aligning real tactile images with simulated geometry for label-efficient contact learning (RoboSoft 2027 submission, now being extended for RSS).

Layout
- `paper/` — LaTeX sources (`main.tex` 8-page, `main_long.tex` extended), figure sources, `scripts/` for tables/figures/video, `PAPER_NOTES.md` (running log of every number), `sync_overleaf.sh`.
- `vistacfusion/`, `configs/` — snapshot of the predictor code (SITR encoder, DPT decoder, pose head) copied from the VisTacFusion repository; training/eval run from this directory with `python -m vistacfusion.engine.train`.
- `scripts/tactile_render/` — renderers (PBR / learned), aligner training (`train_aligner.py`), pseudo-labeling (`pseudo_label_rc.py`), mesh fitting.
- `scripts/` — real-data builders and calibration (session 2, GelSlim 4.0 public set, new objects).
- `ablation/pilot_robosoft/` — every run config (`data_*.yaml`, `train_*.yaml`), evaluation scripts and cached result JSONs that the paper tables read.
- `ablation/encoder/tac_sitr_single*.yaml` — predictor configs.
- `aligntac_newobj/` — calibration, GT and evaluation of the four additional objects.
- `new_real_test/` — session-2 raw captures (ignored) and the curated selections (`validation/*.json`, tracked).
- `notes/` — side notes (literature review, checkpoint lists); `paper/overleaf_backups/` — Overleaf snapshots.
- Local only (ignored): `runs/` (training runs; `/media/hdd2/ihsuan/VisTacFusion/AlignTac/runs` is a symlink to it), `outputs/` (aligners, renderer models, qualitative dumps, logs), `data -> /media/hdd2/ihsuan/gs_blender` (datasets, meshes, pseudo-label sets), `weights -> ../weights` (frozen encoder checkpoints).

Environment: conda env `vistacfusion` (Python 3.11, PyTorch 2.5.1+cu121). Run everything from this directory, e.g. `python paper/scripts/make_paper_figs.py paper/figures`, `python paper/build.py`.
