# MeshTac paper — notes for revising the manuscript

Companion to `main.tex` (6-page RoboSoft 2027 submission) and `main_long.tex` (15-page extended
version, same story, every result). Everything that is *in* the paper is not repeated here; this file
says where the numbers come from, how paper terms map to code names, and what must not be changed
without re-checking.

Deadline date: RoboSoft 2027, **2026-10-15**. Official homepage says 23:59 PT but CFP says GMT; confirm the time in PaperPlaza. Page limit 6 + up to 2 paid pages; `main.pdf` is
exactly 6 pages including references.

## Short-version readability and argument revision (2026-10-08; latest)

Revised the abstract in `main.tex` and all six short sections, keeping the renderer-free MeshTac main setting, current title, author-updated Fig. 1 (0.9 text width), and all raw results. `main.pdf` remains six pages. See the newest entry in `EDITORIAL_REVIEW.md` for papers read, before/after content corrections, and verification. Long-version sources/PDF, architecture/figure assets, shared `data/tables.tex`, and `refs.bib` are unchanged. This round has not been pushed to Overleaf.

The prose now distinguishes the observed gains from their interpretation: corrected contact state improves labels and student predictions; synthetic augmentation has small within-session gains at K=10 but no consistent additional gain across budgets, and helps session 2 at K=100. Self-training does improve contact metrics at larger budgets. Sensor-B pose gains are less consistent than contact gains. Table-II students share architecture/schedule but use different teachers; rows 3 and 5 share the real-only teacher and directly compare unrefined/refined mesh labels. The L1-search half-depth gate and all-frame pose supervision are explicit. Section E now uses **Label Budgets**, avoiding an implication of validation/test leakage. Do not restore either the renderer-assisted main setting or the retired terminology.

**Checkpoint policy (2026-10-08, unified; supersedes the exceptions note and the final-epoch policy):** every table and figure reports dense metrics at `best_depth.pt` (lowest validation depth MSE) and pose metrics at `best_pose.pt` (lowest validation rotation error). Sensor A: `build_tables.hist()` / `make_paper_figs.pose_ckpt()` take the best-validation-rotation epoch from history.json (no final-epoch checkpoint is saved). Session 2 and sensor B: re-evaluated with `eval_cross_session.py --ckpt best_pose.pt` into tags `cross_session_fv_bp` and `sensorB_mesh_bp` (dense metrics still from `cross_session_fv` / `sensorB_mesh`). `eval_pose_refine.py` already loads `best_pose.pt`. Translation is the mean absolute coordinate error in mm everywhere: `eval_cross_session.py` sums |dx|+|dy|, so `trans_l1 * 41 / 2`; history.json and the refinement script already average the two coordinates. Final-epoch vs selected-epoch rotation differ by <= 0.25 deg on sensor A.

**Translation aggregation (now stated in setup/captions):** sensor-A budget metrics (`engine/eval.py`) and test-time refinement (`eval_pose_refine.py`) average absolute errors over x and y. Sensor-B/session-2 evaluation (`eval_cross_session.py`) sums the two axes and averages over frames. Fig. 4(c)/(f) and Tables III/IV therefore use different aggregation; the text now makes this explicit without changing shared table data or rescaling results. Direct cross-table comparisons would require a unified evaluation protocol.

The abstract keeps the existing quantitative results and explicitly identifies the real-only comparison, two sensor-specific models and 12 ridge-pattern objects. Discussion now includes contact-state accuracy, the distinction between full-image and contact metrics, simulation coverage, pose ambiguity, validation-label cost and future work in connected paragraphs. PBR contact-tuning split/K-budget provenance remains unconfirmed; the author has been asked, and no train-only/K-only guarantee was invented.

## Short-version full-text revision (2026-10-07; historical)

This round edits only `sections/*.tex` and rebuilds `main.pdf` (6 pages). See the newest entry in `EDITORIAL_REVIEW.md` for primary papers read, section-level changes, before/after factual corrections, captions, and verification. The existing abstract, title and five experiment headings remain. Method now specifies the actual student losses; setup explicitly states that the object embedding conditions the pose head. Cross-session renderer benefits are budget-dependent (K=100 improves; at K=25 renderer-free MAE is slightly lower). Test-time refinement's 0.4–1.2° range applies to K >= 25, whose session-2 medians are 1.5–1.8°. The held-out-object caption now explicitly exempts the all-pairs renderer from the exclusion of those objects' real training contacts. For the half-gated L1-search control, depth is gated per object but pose supervision uses all search results (`pose_all=True`).

No long-version or shared figure/table/bibliography files were edited by this round. An external update to the long experiment section and shared plots was detected during the work and preserved; the final short captions were checked against the current six-panel K-shot plot. No Overleaf synchronization was run during editing; the author subsequently requested a push, and the six short-section files were pushed and verified at commit `a233bb8` (latest remote base: `89d0ac5`). Physical-renderer contact-tuning split provenance remains unconfirmed.

## Reframing (2026-10-07, author decision after an external review)

- **Fig. 1 training/inference version (author-approved and pushed):** the short version now includes `figures/fig_arch_training_inference.pdf`, built from `architecture_diagram_training_inference.tex`. Both teacher and student are expanded as the same frozen SITR-B/18 encoder, DPT decoder and Pose MLP; object embedding connects only to pose. Training shows registered and mesh-aligned labels supervising the student; inference separates student-only prediction from optional mesh-assisted refinement, including real-image and mesh inputs. The short caption describes panels (a) and (b). Pushed to Overleaf and verified at `180a0f0`, on remote base `05717b2`; local and remote short manuscripts compile to six pages with no unresolved references or overfull boxes. The original `figures/fig_arch.pdf` and long-version sources remain unchanged. `main_fig1_preview.pdf` is a preview copy of the updated short manuscript.
- **L1-search explanation (author-requested clarification):** the short-version ablation now explicitly states teacher-pose initialization, fitting the mesh to teacher depth, 567 nearby candidate poses, learned-renderer RGB generation, and selecting the pose with minimum full-image RGB L1 against the real tactile image as the pose pseudo-label. The adjacent results paragraph was shortened to avoid repeating table values and retain six pages. This is the search baseline only; the renderer-free MeshTac framing is unchanged. Long-version sources and shared figures/tables were not edited in this clarification. Pushed to Overleaf as `83753bb`; the remote commit was verified and the short version still compiles to six pages.
- **MeshTac = renderer-free pipeline** (code names `rf` / `maplnr_m`: real-only teacher, aligner trained on real perturbations only, student without synthetic frames). The former main configuration (`al2` / `mapl_m`, K-pair learned renderer in aligner, teacher and student) is now the variant "+ synthetic frames" and appears as an indented row under MeshTac. Fig. 3, Fig. 5 (predictions of the rf models), Table I-IV and all numbers in the text follow this. Do not swap back.
- **Checkpoints**: dense metrics at the best-validation-depth checkpoint; pose metrics (rotation, translation) at the best-validation-rotation checkpoint, uniformly (see the 2026-10-08 policy note above). The text still reports final-epoch depth MSE for the seed comparison.
- **Table I** has Normal (deg) and Trans. (mm) columns; translation = normalized L1 x 41 mm (`HALF_MM`).
- **"leaky" is retired** -> "all-pairs renderer / all-pairs reference" everywhere (tables, figure legends, text).
- **Fig. 5** frames = the object's median MeshTac contact MAE (not the median improvement).
- **Aligner convergence** (`scripts/aligner_convergence.py` -> `ablation/pilot_robosoft/aligner_convergence.json`, `fig_conv.pdf`, shown in both versions): from the teacher pose 5.6 -> 2.1 (1 it.) -> 1.1 deg (3 it.), min 1.05 at 5; six updates recover perturbations up to 15 deg (0.6 deg), 20 deg -> 0.8, 25 -> 1.5, 30 -> 3.2.
- Contribution 2 is phrased as an empirical finding (renderer study), contribution 3 no longer claims MeshTac on held-out objects. Title: "Contact Geometry" (was "Tactile Geometry").
- Test-time refinement table uses the rf models (`pose_refine_results.json` keys `pilot150_B_k{K}_rf_realonly/*`).

## Abstract and terminology (2026-10-07, author decision)

The abstract now leads with the registration needed to obtain mesh-derived contact labels, introduces MeshTac in the second sentence, and groups its mechanism, experimental evidence, and implications in that order. It specifies sensor-specific models and ridge-pattern objects, adds the cross-session finding, and ends with the implications for alignment and renderer supervision. The quantitative findings remain: contact depth error -20% on sensor A and -36% on GelSlim 4.0 at K=25; all-pairs renderer 24-26% versus matched 0-3%. Keep these numbers; this supersedes the 2026-10-06 note below. The abstract structure was revised after directly reading seven related abstracts; see the latest entry in EDITORIAL_REVIEW.md. Both abstracts contain approximately 207 words; the compiled short and extended versions remain 6 and 15 pages.
The coined term "label accounting" is retired everywhere; use "matched-budget protocol / matched budgets / renderer supervision counted in the label budget". Do not reintroduce it.

## Latest prose revision (2026-10-06)

The author now prefers an abstract without quantitative results. Both abstracts use qualitative findings; exact effect sizes and half-budget comparisons remain in Experiments. This supersedes the earlier request to restore numbers in the abstract. The contributions are consolidated into three: the MeshTac method, matched-budget label accounting, and systematic empirical characterization (including optional test-time refinement). The qualified pose-bottleneck conclusion and extended practical recipe/reporting remain. Introduction, related work, method transitions and experimental paragraphs were revised using TACTO, Taxim, DeepIM and Sparsh as structural references (see `EDITORIAL_REVIEW.md`). The paper explicitly targets known-object tactile perception and distinguishes mesh-projected geometry from physical elastomer deformation. No figure, result table or bibliography changed. Short: 6 pages; extended: 15 pages.

## Author-directed follow-up (2026-10-06, America/New_York)

Fig. 1 uses the author's latest `fig_arch.pdf` (superseding the earlier v1 request); Fig. 4 retains Claude's four solid lines.
Restored the abstract's label-accounting motivation and concrete half-budget comparisons,
a separate label-accounting contribution, the qualified pose-bottleneck interpretation,
and the extended version's practical recipe/reporting sections. All protocol corrections remain.
Short version: 6 pages; extended: 15 pages.

## Editorial revision (2026-10-05, America/New_York)

See `EDITORIAL_REVIEW.md` for the full change log (its open items on PBR provenance and the translation/checkpoint protocol were resolved on 2026-10-08; see the policy note above).
Both documents default to anonymous review; define `MeshTacAuthorVersion` for an author copy.
K is a **training-label** budget; additional validation labels select checkpoints.
GAN-full exceeds K in the few-shot protocol, but never trains on validation images. In LOO it sees real frames of evaluation objects.
The cross-session `A_realonly` reference uses nine training objects, not all twelve; its comparison with K-shot methods is not matched for object coverage.
Main sensor-A aligner logs include synthetic examples (24 real + 40 synthetic per batch), all generated by the same-K renderer. Renderer-free and sensor-B aligners use real examples only. No additional real training labels are consumed.

## 1. Files

| What | Where |
|---|---|
| 6-page paper | `main.tex`, `sections/01_intro … 06_conclusion.tex` |
| Extended version | `main_long.tex`, `sections_long/01_intro, 02_related, 03_setup, 04_mapl, 05_experiments, 06_conclusion.tex` |
| Shared | `refs.bib`, `ieeeconf.cls`, `data/tables.tex` (generated), `figures/` |
| Overview figure (Fig. 1) | Short: **`figures/fig_arch_training_inference.pdf`**, author-approved TRAINING/INFERENCE figure with expanded teacher/student architectures. Long: original **`figures/fig_arch.pdf`** (preserved). |
| Tables | `scripts/build_tables.py` → `data/tables.tex`; one `\newcommand{\tab<name>}` per table body |
| Figures | `scripts/make_paper_figs.py`; `scripts/make_arch_assets.py` (thumbnails of Fig. 1); `scripts/dump_qual_preds.py` (predictions for Fig. 5) |
| Overleaf | project `6ab1c9afe47f399544728ef3`; `OVERLEAF_TOKEN=… bash sync_overleaf.sh push "<msg>"` (also `pull`) |

Compile from this directory: `pdflatex main; bibtex main; pdflatex main; pdflatex main` (same for
`main_long`). Regenerate tables/figures from the repo root (`/media/hdd/ihsuan/VisTacFusion`):

```
conda run -n vistacfusion python paper_RoboSoft/scripts/build_tables.py
conda run -n vistacfusion python paper_RoboSoft/scripts/make_paper_figs.py paper_RoboSoft/figures
cd paper_RoboSoft && pdflatex -output-directory=figures -jobname=fig_arch architecture_diagram.tex
```

Short-paper tables use the `*short`/`*main` macros (`\tabkshotshort`, `\tabrcablmain`, `\tabcrossshortb`,
`\tabsbshortb`, `\tabposeref`, `\tabloomain`); the long version uses the full ones (`\tabkshot`,
`\tabseeds`, `\tabrcabl`, `\tabcross`, `\tabsbmapl`, `\tabsensorb`, `\tabloo`, `\tabvariants`).

## 2. Paper term ↔ code / run name

The method was called MAPL (and briefly SnapTac) during development; code, run directories and result
keys still use the old names. Do **not** rename anything in code.

| Paper | Runs / dirs (sensor A) | Runs (sensor B) |
|---|---|---|
| Real only | `B_k{K}_realonly` | `S_k{K}_realonly_m` |
| Physical renderer | `B_k{K}_blender` | — |
| Learned renderer (GAN-K) | `B_k{K}_gank`; renderer `outputs/tactile_gan_k{K}` | `S_k25_gan40m`; `outputs/tactile_gan40_k25` |
| Self-training (teacher depth as label) | `B_k{K}_semipm_pseudo` | `S_k25_semipm_m` |
| Teacher depth + teacher pose | `B_k25_tp` | — |
| L1 render-and-compare search (½ gated) | `B_k25_rcp` (also `rc50`, `rc100`, `rcp00/25/75`) | — |
| **MeshTac** (aligner labels, renderer retrained on aligned pairs) | `B_k{K}_al2`; labels `gs_blender/real_pseudo_k{K}_al`; renderer `outputs/tactile_gan_al_k{K}`, sim images `renders_v3/*/samples_a_k{K}`; aligner `outputs/aligner_k{K}` | `S_k25_mapl_m`; labels `real_pseudo_S_k25_m_al`; renderer `tactile_gan40m_al_k25`; aligner `outputs/aligner_S_k{K}_m` |
| MeshTac, no renderer (real-only teacher, no synthetic frames) | `B_k{K}_rf`; labels `real_pseudo_k{K}_ro_al`; aligner `outputs/aligner_k{K}_realonly` | `S_k{K}_maplnr_m`; labels `real_pseudo_S_k{K}_m_al` |
| MeshTac, sim-free student only | `B_k{K}_al0` | — |
| Unlabeled fraction 25/50 % | `B_k25_al2u25`, `B_k25_al2u50` | — |
| Second round (student as teacher) | `B_k{10,25}_al2_r2` | — |
| Leaky renderer (GAN-full) | `B_k{K}_ganfull` | — |
| Teacher f0 | the `gank` model of the same K (sensor A); the `realonly_m` model (sensor B) | |

Prefix `pilot150_` = 150-epoch run (all main sensor-A numbers), `pilot_` = 50-epoch run (seeds, ablation
table, all sensor-B runs). Seeds: `<run>_seed1`, `<run>_seed2` (seed 0 has no suffix). Checkpoints in
`/media/hdd/ihsuan/VisTacFusion/AlignTac/runs/<prefix><run>/{best_depth.pt,best_pose.pt,history.json}`
(`latest.pt` was deleted to free disk; nothing in the paper needs it). Logs: `outputs/pilot_logs/`.

Method code: `scripts/tactile_render/train_aligner.py` (aligner), `scripts/tactile_render/pseudo_label.py`
(teacher labels), `scripts/tactile_render/pseudo_label_rc.py` (alignment / L1 search → mesh labels),
`scripts/tactile_render/train_tactile_gan.py` + `generate_tactile.py` (learned renderer),
`scripts/tactile_render/fit_mesh_pose.py` + `scripts/canonicalize_gs40_poses.py` + `scripts/build_gelslim40_mesh.py`
(sensor-B mesh registration), `ablation/pilot_robosoft/eval_masked.py`, `eval_cross_session.py`,
`eval_pose_refine.py` (evaluation).

## 3. Where every number comes from

All result files are in `ablation/pilot_robosoft/` (repo root). Keys are `<prefix><run>/<split or tag>`.

| Quantity | File / key | Notes |
|---|---|---|
| Depth MSE, normal MSE, rotation, translation (val) | `<outputs>/<run>/history.json` via `build_tables.hist()` | depth metrics at the best-val-depth epoch, pose at the best-val-rotation epoch |
| Contact MAE, IoU, normal angular error (val, TEST) | `masked_results.json`, keys `…/val`, `…/TEST` | TEST = the three held-out objects (A runs) |
| Second session (sensor A) | `cross_session_results.json`, tag **`cross_session_fv`** only | tags `cross_session_curated` / `curated361` / `curated854` are from a label-scale bug and must not be used |
| Sensor B | `sensorB_results.json`, tag `sensorB_mesh` (mesh-registered labels, used in the paper) and `sensorB_test` (original public labels, mentioned once) | |
| Test-time alignment | `pose_refine_results.json`, keys `pilot150_<run>/{val,session2}`, fields `rot`, `rot_al`, medians, IoU/cMAE of mesh@aligned | |
| Label quality of pseudo labels (IoU / contact MAE / pose error vs withheld GT) | `outputs/pilot_logs/pseudo_k{K}_al.log` (sensor A, K=10,50,100), `pseudo_S_k{K}_m_al.log` (sensor B), lines `teacher (all)` / `mesh (kept)`; also `stats` in `gs_blender/real_pseudo_*/pseudo_manifest.json` | the sensor-A K=25 log was overwritten; its values (teacher 0.55/0.32/5.3°, aligned 0.71/0.24/1.1°) are hard-coded in `make_paper_figs._label_quality` and in `\tabrcablmain` via `labq("real_pseudo_k25_al", …)` |
| Renderer fidelity | `outputs/pilot_logs/renderer_fidelity_all.log`, `data/renderer_fidelity*.txt` | |
| Seeds (mean ± std) | `build_tables.seeds()` over seed 0/1/2 of `pilot_<run>` | |

Numbers quoted in prose (percentages, "halves the labels", "93 %") are derived by hand from the tables;
if a table changes, re-derive them. Current canonical values:

**Sensor A, 150 ep (depth MSE / contact MAE / IoU / rot°), real only → MeshTac**
K=10: 0.0642/0.330/0.625/9.6 → 0.0559/0.288/0.682/4.0 · K=25: 0.0558/0.312/0.664/5.6 → 0.0450/0.249/0.727/3.7 ·
K=50: 0.0482/0.283/0.690/4.3 → 0.0307/0.206/0.769/3.7 · K=100: 0.0369/0.235/0.744/3.2 → 0.0232/0.168/0.803/3.7.
Leaky K=100: 0.0274/0.205/0.777. No-renderer MeshTac: 0.0521/0.0433/0.0291/0.0227.
Seeds (50 ep) K=25: 0.0447±0.0009 vs 0.0551±0.0010; K=100: 0.0229±0.0003 vs 0.0366±0.0008.
Derived: depth MSE −13/−19/−36/−37 %, contact MAE −13/−20/−27/−28 %.

**Sensor B, 50 ep, mesh-registered labels, real only → MeshTac (no renderer)**
K=10: 0.0314/0.180/0.780/14.0 → 0.0170/0.121/0.856/9.5 · K=25: 0.0182/0.127/0.847/13.4 → 0.0076/0.081/0.911/9.2 ·
K=50: 0.0088/0.083/0.899/9.0 → 0.0041/0.061/0.933/9.8 · K=100: 0.0051/0.066/0.932/8.4 → 0.0034/0.056/0.944/9.1.
K=25 with renderer: 0.0075/0.078/0.904/9.9; learned renderer 0.0148/0.111/0.877; self-training 0.0175/0.135/0.846.
Seeds K=25: real 0.0179±0.0004 / 0.127±0.001 / 0.849; MeshTac 0.0075±0.0001 / 0.078±0.0003 / 0.903.
Original public labels, K=25: contact MAE 0.137 → 0.098. Derived: contact MAE −33/−36/−26/−15 %, depth MSE −46/−58/−53/−33 %.

**Label quality (IoU, teacher → aligned)**: sensor A 0.53→0.65, 0.55→0.71, 0.64→0.76, 0.66→0.81 (pose 1.6/1.1/1.1/0.7°);
sensor B 0.78→0.85, 0.85→0.91, 0.90→0.94, 0.93→0.95 (pose 2.3/1.4/0.9/0.8°, teacher 6.6–11.4°).

**Cross-session (sensor A, `cross_session_fv`, contact MAE / IoU)**: nine-object real-only reference 0.315/0.675; K=25 real 0.368/0.598,
self-training 0.335/0.598, MeshTac 0.310/0.660 (no renderer 0.306/0.654); K=100 real 0.351/0.657,
self-training 0.300/0.707, MeshTac 0.252/0.743 (no renderer 0.288/0.707).

**Test-time alignment (rot°, pred → aligned)**: val, real only 9.6/5.6/4.3/3.2 → 2.8/1.2/1.2/0.4; MeshTac
4.0/3.7/3.7/3.7 → 1.5/0.9/1.2/0.8. Session 2, real only 20.2/16.2/13.8/12.9 → 11.4/5.5/4.8/4.9; MeshTac
8.8/9.0/10.6/10.2 → 4.9/4.8/5.2/4.8. Unseen objects (aligner trained on 9 objects): 4.8–6.8° → 0.6–1.0°.

## 4. Terminology and conventions (keep)

- **GT** = ground truth = the object mesh projected at the recorded pose (sensor A) or at the pose fitted
  to the public label (sensor B). Defined once in Setup ("ground-truth (GT) depth and normals are …");
  use "GT" everywhere afterwards, not "reference" (the word "reference" is kept only for "leaky
  reference" / "as a reference for common practice").
- Method name **MeshTac**; expanded as "mesh-aligned pseudo-labeling". Earlier names MAPL/SnapTac must
  not reappear (MAPL and TacAlign collide with existing papers).
- `$\Kreal$` = K, labeled frames per object. Few-label regime = K ≤ 25 (3 % and 7 % of sensor-A training
  frames); K = 50, 100 are "the trend". Headline claims use K = 10–25; do not advertise "10–100".
- Table rows are **methods** ("Real only", "Learned renderer", "Self-training", "MeshTac (ours)",
  "Leaky renderer"), no "+" prefix; column header "Method". Leaky rows italic, never bold.
- Caption style: short bold noun-phrase title ("Overview of MeshTac.", "K-shot results on sensor A."),
  details after, conclusions in the text.
- Teacher = f0, student = f1, aligner = A; the same aligner is used for labeling and for test-time
  refinement (same weights). Student architecture = teacher architecture = standard frozen SITR-B/18
  encoder + DPT decoder + pose MLP; the contribution is the labeling, not the network.
- Sensor A = GelSlim 5.0 (`\sensor`), sensor B = GelSlim 4.0 (`\sensorB`, public dataset, Sipos et al.).
- Metrics: depth MSE over all pixels (mm²); contact MAE inside the GT contact region (mm); IoU over the union of predicted (>0.05 mm) and GT (>0) masks;
  normal angular error inside the contact (deg); rotation error (deg). Dense metrics come from
  `best_depth.pt`; all pose metrics use `best_pose.pt` (tags `*_bp` for session 2 and sensor B). The old `cross_session_fv` / `sensorB_mesh` rotation and translation values were taken at the depth checkpoint and are no longer used in the paper.

## 5. Facts that are easy to get wrong

- **Sensor B labels were re-registered to the meshes.** The public labels are mesh depth clipped at
  1 mm and Gaussian-blurred, not exact projections. We fitted the mesh pose that best explains each label
  (0.018 mm mean residual) and canonicalized it against the object's rotational symmetry. Every method is
  trained and tested on these labels (`real_gelslim40_{train,test}_mesh`); the paper also reports
  MeshTac vs real-only on the original labels (`sensorB_test`) as a check. An earlier sensor-B result
  (MeshTac contact MAE 0.227/0.210, "MAPL does not help on sensor B", "condition: aligned mesh must beat
  the teacher") came from a gel-view bug and is **invalid**; it survives only in git history and in
  `*_bugview` directories. Nothing in the paper may cite it.
- **Second session**: only tag `cross_session_fv` (labels re-rendered at the full view by
  `scripts/fix_session2_view.py`) is correct; earlier tags scored against labels magnified 1.225×.
- **"93 % of the frames"**: at K = 25 the few-shot renderer's render at the *true* pose is farther from
  the frame (image L1) than its render at the pose the search selected, on 93 % of frames — i.e. the
  renderer scores a wrong pose above the true one. It does not mean the search is wrong on 93 %.
- **"halves the labels"**: MeshTac at K lands at or below real only at 2K (sensor A: 0.0307 at K=50 vs
  0.0369 at K=100; sensor B contact MAE 0.081 at 25 vs 0.083 at 50, 0.061 at 50 vs 0.066 at 100).
- **Rotation on sensor B** improves only at K = 10, 25 (14.0→9.5°, 13.4→9.2°); at K ≥ 50 it is ≈9° either
  way. Sensor-A rotation at K = 100: real only 3.2° < MeshTac 3.7° until test-time alignment.
- **No K = 0 points** in Fig. 3: real only, learned renderer, self-training and MeshTac need labels;
  only the physical and leaky renderers exist at K = 0 (reported in the long version only).
- **Fig. 5 frames** are chosen by rule (per object, the frame whose contact-MAE improvement is the
  object's median), not hand-picked; the sensor-B objects shown are pattern_04, pattern_33, pattern_06
  (pattern_37, the hardest object, is not shown but is in every average). Predictions are cached in
  `/media/hdd/ihsuan/VisTacFusion/AlignTac/outputs/robosoft_qual/qual_{A,B}.npz` (130 MB each; keep them out of
  `data/`, which is synced to Overleaf).
- **Fig. 1**: the author selected the latest `fig_arch.pdf`. Its student-output thumbnails are actual predictions (`make_arch_assets.py`, `pilot150_B_k25_al2/best_depth.pt`), not the earlier GT placeholders. The caption also notes the omitted synthetic training branches. **Fig. 4 must retain four solid lines.**
- **Second round** (student as teacher) gives no gain (K=10: 0.0570 vs 0.0559; K=25: 0.0445 vs 0.0450).
  Unlabeled fraction 25/50/100 %: 0.0453/0.0452/0.0447 (long version only).
- **Leave-object-out**: held-out objects pattern_04_3_lines_angle_2, pattern_31_rod, pattern_33
  (1,244 frames); runs `A_*` (prefix `pilot150_` for the main rows).
- The renderer-free variant is equal or better *within* a session but worse *across* sessions
  (K=100 contact MAE 0.288 vs 0.252); that is why the renderer stays in the main method.
- Real data counts: sensor A 4,669 frames (222–568 per object, 472 val, one session per object), session 2
  854 curated frames of 11 objects; sensor B 1,620 test frames, ~270 training frames per object.
  Simulated contacts: 5,345. Trainable parameters: 12 M. Unlabeled pool per K: 4,077 / 3,897 / 3,597 /
  2,997 frames (sensor A), 3,120 / 2,940 / 2,640 / 2,040 (sensor B).

## 6. Known weaknesses a reviewer will raise (address in wording, not by over-claiming)

1. Only 12 ridge-pattern objects; no curved or textured objects. Not fixable without new data.
2. Needs the mesh and the identity of the object in every unlabeled frame; test-time alignment needs
   them at test time too. Scope: known objects (industrial parts, calibration objects).
3. No downstream robot task.
4. Sensor-B GT is our re-registration of public labels (see §5); three seeds on sensor B at every budget (real-only and AlignTac).
5. GT is a geometric projection, not a measured membrane deformation (both sensors).
6. RoboSoft audience: keep the first paragraph of the introduction readable for non-ML reviewers; avoid
   unexplained ML jargon.

## 7. Authors and metadata

I-Hsuan Huang*, Xiaohao Xu*, Xiangdong Wang, Xiaonan Huang, Nima Fazeli (University of Michigan;
* equal contribution). Correspondence `{ihsuan, xiaohaox}@umich.edu`. Check the author list before
submission.

- PBR calibration provenance (confirmed by the author 2026-10-08): one no-contact image for the automatic illumination fit, one contact image of one object outside the training set for manual gel/contact tuning; no labels used, nothing counted in K.

- 2026-10-08: short version replaces the pose-refinement table with paired bars (`figures/fig_poseref.pdf`, `make_paper_figs.fig_poseref`, 2x2 single column: rotation/translation x session 1/2; hollow = predictor, filled = +align). The long version keeps the table (`\tabposeref`).

- 2026-10-08 (late): short version drops Fig. 3 (renderer examples, `fig_renders_small.pdf`), Fig. 5 (label quality vs K, `fig_labels.pdf`) and the sensor-B block of Table III (`\tabsbT`); their content is summarized in one sentence each (Sec. B label IoU numbers, Sec. C sensor-B IoU). Files and macros are still generated for the long version. Freed space went to Fig. 2 (0.92 columnwidth), Table II (scriptsize, no resizebox, 7pt group gap, row "Aligner (ours)") and larger Figs. 3/4/6.

- 2026-10-09: CLEAN PROTOCOL IN THE SHORT VERSION. All sensor-A within-session numbers (Table I, Table II student columns, Table III session-2 rows, Fig. 3 a-c, Fig. 5 sensor A, Fig. 6 a,c and the text) now come from the T_* runs (trained without the 530 held-out frames) evaluated on `gs_blender/real_filtered_testA`: dense from best_depth.pt (`testA_results.json` tag testA), pose from best_pose.pt (tag testA_bp), refinement keys `pilot150_T_k{K}_{realonly,rf}_realonly/testA` in pose_refine_results.json, session-2 keys `pilot150_T_*/cross_session_fv(_bp)`. Self-training and Table II rows are renderer-free (T_k*_semipm, T_k25_{tp,rf0,rcp} with sim train_samples_per_session 0). Headline numbers: contact MAE -15/-20/-31/-29% (K=10/25/50/100), depth MSE -18/-22/-30/-36%; full renderer 17-23% vs budget-matched 2-3%; session 2 MeshTac -15/-20%, +synth K=100 0.248 (-31%). PBR students (T_k*_blender) retrained 2026-10-09 09:01 for Fig. 3. Old B_* numbers remain in the long version.

## 2026-10-09 — v6 review round (GPT review of the clean-protocol PDF)
- **Verified, not a leak:** the full-set learned renderer (`outputs/tactile_ganT`) was retrained with `--exclude-frames testA_frames.json`; its log reports `pairs: train=3667 val=472`. The short-version text still said 4,197 (legacy count) — fixed to 3,667 in Sec. IV; long version now states both counts (legacy 4,197 / clean 3,667).
- Sec. V-E percentages were stale (0–3% / 24–26%): now 2–3% (budget-matched) vs 17–23% (full-set) at K=10–25, computed from `testA_results.json` (gank 2.5/1.7%, ganfull 22.6/16.7%), matching the abstract.
- Single-checkpoint reference added to Sec. V-A: the final-epoch checkpoint of MeshTac K=25 gives MSE 0.041 / IoU 0.74 / rot 3.2° / trans 0.88 mm simultaneously (`testA_final` tag).
- Wording softened: abstract first sentence (contact-state estimation, not "image registered to mesh"), "no synthetic tactile images", contribution 2 ("critical for" instead of "determines"), Sec. V-B closing sentence, Sec. V-E held-out-object interpretation (object-specific pose supervision, not rendering fidelity), related-work contrast with inference-time refinement, aligner first-layer init (depth filters = mean of RGB filters, per `train_aligner.py`), sensor-B per-frame mesh fitting defines labels only.
- Table II rows 2–3 (Teacher/Teacher = `T_k25_tp`, Mesh/Teacher = `T_k25_rf0`) were single-seed; seeds 1–2 launched 2026-10-09 16:34 on GPUs 0–1 (`worker_T.sh`, jobs `train50 … e50_pm 1|2`), evaluated by `finisher_seeds.sh` → tags testA/testA_bp. `build_tables.py` already averages whatever seeds exist (n=3 for both rows). After eval: rebuild tables and drop "except rows 2–3" from Sec. V-B.
- Row 2 (Teacher/Teacher) is the "stronger self-training" baseline the review asked for (teacher depth + normals + pose pseudo-labels); the text now says so.
- **Seeds done (2026-10-09 17:26):** Table II rows 2–3 now average three 50-epoch seeds on the 530 test frames. Teacher/Teacher: IoU 0.63 / cMAE 0.30 / rot 6.1° / trans 1.2 mm (was 6.2° single seed); Mesh/Teacher: IoU 0.48 / cMAE 0.36 / rot 6.0° / trans 1.2 mm (IoU was 0.51 single seed), depth MSE 0.058 (was 0.060) vs 0.049 real-only. Aligner row remains best in every column; all Sec. V-B statements re-checked. Runs: `pilot_T_k25_{rf0,tp}_seed{1,2}` under `/home/shared/vtf_outputs_T`.

## 2026-10-10 — co-author pass (X. Xu on Overleaf, commit 34f2646) + eight-page version
- Pulled the co-author's Overleaf edits: method renamed **MeshTac → AlignTac**, new title ("AlignTac: Aligning Real Tactile Images with Simulated Geometry for Label-Efficient Contact Learning"), new abstract, expanded intro/method (problem formulation, numbered equations), pastel rank colors in tables (`table_style.tex`: \rankfirst/\ranksecond/\rankthird, grey "reference" rows), section titles. `data/tables.tex` now carries **manual** rank-color edits — `build_tables.py` refuses to run without `--force`; re-apply the coloring after any regeneration.
- RoboSoft allows 6 + 2 purchased pages; the user approved 8 pages. Added: intro teaser `figures/fig_teaser.pdf` (`scripts/fig_teaser.py`: real registration vs. simulated appearance vs. AlignTac, frame pattern_06 #0479), restored Fig. labels (pseudo-label quality vs K, both sensors), the sensor-B block of Table III (`\tabsbT`), and the renders figure (`fig_renders_small.pdf`) in Sec. V-E.
- Fig. 4 caption now states why PBR / full-set renderer are absent on sensor B (PBR scene calibrated to sensor A; full-set renderer is a non-matched reference).
- Sensor naming per co-author: sensor A = "marker-free variant of the GelSlim 4.0 design (17.5 mm view, six colored LEDs)", sensor B = "the public GelSlim 4.0 with markers". GelSlim 5.0 stays only in the author-version macro.
- Figures regenerated with the AlignTac legend (`make_paper_figs.py`); Fig. 1 rebuilt from the local diagram source. `sync_overleaf.sh` FILES now include `table_style.tex` and `architecture_diagram_training_inference.tex`. Long version renamed too and compiles (17 pages).

## 2026-10-10 (later) — co-author revision 2 pulled; K=5 and no-identity runs
- Pulled X. Xu's Overleaf revision (20a2cfb): his own intro figure (`figures/intro_figure/`, replaces our `fig_teaser`), TikZ pipeline (`figures/pipeline.tex`), `notation.tex` (f^t, f^s), caption/paragraph/bibliography layout files, `build.py`; both sensors named as GelSlim 4.0 variants (marker-free = A, dot-marker = B). All numbers verified unchanged.
- K=5 (clean protocol, 530 test frames; runs `pilot150_T_k5_{realonly,blender,semipm,rf}`, labels `real_pseudo_k5_ro_{ng,al}`, aligner `outputs/aligner_k5_realonly`): real only MSE 0.0656 / cMAE 0.348 / IoU 0.599 / rot 14.0 / trans 2.05; PBR 0.0656 / 0.368 / 0.591 / 6.5 / 1.21; self-training 0.0580 / 0.346 / 0.543 / 14.7 / 2.20; AlignTac 0.0553 / 0.313 / 0.642 / 6.3 / 1.24. Label quality: teacher IoU 0.475, rot 13.84 -> aligned 0.580, 5.96. Reported as one sentence in Sec. V-A only (user decision: no table/figure change). `pilot150_T_k5_tp` = an accidental teacher-pose variant (root _ro_ng without skip_pseudo), not used.
- No-object-identity students (`pilot150_T_k{25,100}_{rf,realonly}_noid`, model `tac_sitr_single_noobj.yaml`, `eval_cross_session.py --model`): dense metrics unchanged, rotation worse (AlignTac 7.0/7.1 deg, real-only 17.2/7.8 deg at K=25/100). User decision: NOT included in the paper.

## 2026-10-10 (evening) — story reframing, Fig. 1 mock, session-2 unlabeled-pool experiment
- Story (agreed with the user): images are easy to collect, mesh-registered labels are not. Problem = image–geometry pairs need calibration + verification (real) or sensor-response modeling (sim). Obstacle to "just project the mesh" = label sensitivity to the contact state, no direct depth-vs-RGB alignment signal, only K registered contacts to learn from. Intro paragraphs 1, 2, 4 and two Setup sentences edited accordingly (the co-author's \FinalLine box at the end of intro paragraph 2 was removed because the paragraph ending changed). Renderer figure width 0.9\columnwidth to stay at eight pages.
- Setup now states: registered = recorded pose after per-object calibration and an image–mesh agreement check (`gs_blender/filter_real_data.py`); in session 2 the session-1 calibration no longer held, per-run corrections averaged 11.4 deg and 1.6/1.7 mm (`new_real_test/validation/pose_calibration_new.json`, 48 runs).
- Fig. 1 reference mock for the PPT revision: `figures/intro_figure/mock_fig1_v2.{tex,pdf,png}` (NOT used by main.tex); overlay assets `figures/intro_figure/v2_assets/` from `scripts/fig1_assets.py` (mesh outline on the real image at teacher / aligned state for frame pattern_06 #0479; second-session frame at the old calibration vs verified pose). The #0479 example was chosen for a large alignment gain (teacher translation error 4.6 mm), not a median sample.
- Session-2 unlabeled-pool experiment (running): `ablation/pilot_robosoft/make_s2_split.py` alternates the 194 presses per object -> pool (1,208 contact frames, stride 2, `gs_blender/real_s2_pool`, poses never used; 1,066 train-split frames labeled) and test half (464 curated frames, `real_s2_testhalf`). Labels: `real_pseudo_s2_k{25,100}_{ng,al}` (teacher `T_k{K}_realonly`, aligner `outputs/aligner_k{K}_realonly`); merged roots `real_merge_k{K}_{rf,semipm}_s2`; runs `pilot150_T_k{K}_{rf,semipm}_s2`; eval tags `s2half`, `s2half_bp` in cross_session_results.json (`finisher_s2.sh`). Pool label quality on 162 frames with a curated label (`s2_label_quality.py`): K=25 teacher IoU 0.51 / rot 16.2 (median 15.3) -> aligned 0.58 / 8.6 (2.7); K=100 0.57 / 19.6 (18.6) -> 0.63 / 4.4 (2.0).
- 2026-10-10 22:30: Fig. 1 is now the user's PowerPoint export `figures/intro_figure/AlignTac_Fig1.png` (transparent background, 2400 px wide); caption rewritten to match. Superseded versions removed: co-author's `AlignTac_Figure1_Updated.{pdf,pptx}` + caption, the v2 mock (`mock_fig1_v2.*`, `AlignTac_Figure1_v2.pptx`, `scripts/fig1_pptx.py`), and the earlier TikZ teaser (`teaser_diagram.tex`, `figures/fig_teaser.*`). Kept: thumbnail/overlay assets (`figures/teaser/`, `figures/intro_figure/{assets,v2_assets}`, `scripts/fig_teaser.py`, `scripts/fig1_assets.py`) and the co-author's generator files (`motivation_*`, `export_motivation_pptx.py`, used by `build.py --figures`). Co-author's title edit ("…Label-Efficient Contact Learning") merged.
- Session-2 unlabeled-pool RESULT (2026-10-10 22:21; held-out half of session 2, 464 curated frames; dense at best_depth.pt, pose at best_pose.pt; single seed; tags `s2half`, `s2half_bp`). cMAE / IoU / rot / trans(mm):
  K=25: real only 0.356 / 0.625 / 14.8 / 1.79; self-training 0.347 / 0.603 / 17.4 / 1.96; self-training + s2 pool 0.340 / 0.592 / 19.6 / 1.98; AlignTac 0.304 / 0.663 / 10.2 / 1.49; AlignTac + s2 pool 0.288 / 0.652 / 7.8 / 1.32.
  K=100: real only 0.366 / 0.658 / 12.4 / 1.64; self-training 0.336 / 0.679 / 14.9 / 1.85; self-training + s2 pool 0.347 / 0.668 / 14.7 / 1.84; AlignTac 0.294 / 0.710 / 9.4 / 1.54; AlignTac + s2 pool 0.269 / 0.707 / 7.4 / 1.34.
  Reading: unregistered second-session images labeled by the session-1 aligner lower contact MAE by a further 5% (K=25) / 8% (K=100) and rotation by 2.0-2.4 deg, translation by 0.2 mm; IoU unchanged (slightly lower at K=25); teacher-labeled pool gives no gain. Not yet in the paper (awaiting the user's decision).
- 2026-10-10 22:50: session-2 unlabeled-pool result IN THE PAPER (user decision; presented as a contribution). Table III bottom block = `\tabstwoadapt` (hand-added to data/tables.tex; the sensor-B block `\tabsbT` was dropped from the short version, sensor-B numbers remain in Fig. 4d-f and the text). New Sec. V-C paragraph "Using a new session without re-registration"; abstract clause (5-8% further MAE reduction); new contribution bullet 3; Table III caption rewritten. To stay at eight pages: renderer figure (old Fig. 9, `fig_renders.pdf`) removed from the short version (Fig. 1b shows PBR / learned / real at one contact; the removed block is saved in scratchpad `removed_fig_renders_block.tex` and remains in the long version), closing sentence of Sec. V-C shortened. Numbers are single-seed; seeds 1-2 of `T_k{25,100}_{rf,rf_s2}` (150 ep, `train150s`, `train_pilot_e150_pm_seed{1,2}.yaml`) started 22:26 on GPUs 0-1, evaluated by `finisher_s2seed.sh` (tags s2half / s2half_bp) -> update the block and text with three-seed means when done.

## Session-2 label-free adaptation: three seeds (2026-10-11)
Runs `pilot150_T_k{25,100}_{rf,rf_s2}{,_seed1,_seed2}` (150 epochs), tags `s2half` / `s2half_bp` in `ablation/pilot_robosoft/cross_session_results.json`, 464 held-out session-2 frames.
Three-seed means (cMAE / IoU / rot / trans mm): K=25 AlignTac 0.309 / 0.665 / 10.4 / 1.51 -> + session 2 0.290 / 0.651 / 7.9 / 1.33 (-5.9% cMAE); K=100 0.286 / 0.710 / 9.7 / 1.54 -> 0.270 / 0.708 / 7.3 / 1.35 (-5.8%).
Per-seed cMAE change: K=25 -5.5 / -5.5 / -6.7 %; K=100 -8.4 / -8.4 / -0.5 % (lower in every seed; one K=100 seed marginal). Rotation gain is the most stable (seed std 0.06-0.5 deg).
Paper: abstract and Sec. V-C say "a further 6%"; Table III bottom AlignTac rows are three-seed means (asterisk), the other rows single seed.

## Additional (non-ridge) objects on sensor A (2026-10-22)
Paper: Sec. V-C paragraph "Additional objects" (three-seed means), Fig. 6 middle group (layout wide, seed-0 models); long version Sec. "Additional Objects" + Table tab:addobj. Ridge wording removed from setup/conclusion (user: do not stress ridge objects).
Data: button, edge, hex_key, marble (meshes `gs_blender/meshes/*_v2.obj`, 3,156 contacts, `gs_blender/real_filtered_plus4`); GT = mesh at the robot pose after a per-object placement calibration (theta offset + xy, fitted to image contact masks; mean press fixed at 1.0 mm), `aligntac_newobj/calibrate_newobj.py`. 489 test frames (`real_filtered_testP4`, same index rule as testA, excluded from every component).
Runs (16 objects, K=25): `pilot150_P4_k25_{realonly,rf}{,_seed1,_seed2}`, `pilot150_P4_k25_semipm` (seed 0 only); eval `aligntac_newobj/eval_newobj.py` -> `aligntac_newobj/eval_newobj.json` (object-ID map from build_datasets!).
Three-seed means, new objects (cMAE / IoU / rot / trans mm): real only 0.167 / 0.867 / 7.65 / 0.83; AlignTac 0.146 / 0.889 / 7.16 / 0.70 (-12% cMAE; lower in every seed: 0.163/0.170/0.168 vs 0.159/0.139/0.141). Self-training (1 seed) 0.174 / 0.724 / 8.0 / 0.88.
Per object cMAE: button 0.202 -> 0.186, edge 0.131 -> 0.115, hex key 0.218 -> 0.180, marble 0.078 -> 0.083 (no gain). Button rotation ~23 deg for both (near-symmetric); edge along-edge translation unobservable.
Same models on the 12 ridge objects (testA): real only 0.287 / 6.3 deg -> AlignTac 0.243 / 2.9 deg.
Label quality (unlabeled train frames, teacher -> aligned IoU): button 0.69 -> 0.85, edge 0.84 -> 0.94, hex key 0.69 -> 0.81, marble 0.39 -> 0.93 (`aligntac_newobj/label_quality_newobj.json`).
Fig. 6 candidates: `paper_RoboSoft/scripts/fig_qual_plus4.py` (layouts wide / tall).

### 2026-10-24 correction: z-map bug, all additional-object numbers re-run
`build_real_filtered_new.get_zmap` gave every triangle its lowest vertex z (no interpolation); the coarsely meshed wedges (edge_v2 = triangular prism on a plate, hex_key_v2) became flat tops, marble off by ~0.15 mm. Fixed with exact barycentric rasterization for `*_v2` meshes only (`exact_zmap`, `use_exact_zmap`); the 12 session-1 objects keep the per-face minimum used for every published result (their pseudo-labels / aligner inputs are flattened by ~0.05 mm on ridge flanks; session-1 GT is not, session-2 GT ~0.06 mm). Recalibrated (`calib_newobj.json`; old fit `calib_newobj_facemin_zmap.json`), GT rebuilt, full chain re-run (`aligntac_newobj/chain_p4_v3.sh`, 4 GPUs); old runs kept as `*_facemin`.
Three-seed means, new objects (cMAE / IoU / rot / trans): real only 0.235 / 0.701 / 7.7 / 0.82; AlignTac 0.204 / 0.774 / 7.5 / 0.74 (-13%; lower in every seed: 0.236/0.234/0.237 vs 0.205/0.204/0.202). Self-training (1 seed) 0.225 / 0.544 / 8.3 / 0.86.
Per object cMAE: button 0.215 -> 0.186, hex key 0.317 -> 0.266, edge 0.292 -> 0.268, marble 0.090 -> 0.074 (real-only marble varies 0.074-0.114 over seeds). Label IoU teacher -> aligned: 0.62 -> 0.85, 0.43 -> 0.61, 0.41 -> 0.66, 0.33 -> 0.93 (pooled 0.43 -> 0.76). 12 session-1 objects with the same models: 0.304 -> 0.232, rot 6.1 -> 3.0.
Eval: `aligntac_newobj/eval_newobj_v2.json`. Fig. 6 middle group: author-chosen frames in `figures/qualitative_assets/fig_qual_picks.json` (button, hex key, marble; edge = median until chosen).

### 2026-10-24 session-2 GT re-rendered with the exact z-map
Session-2 GT (`real_filtered_new_curated_pred_r2_fv`, `real_s2_testhalf`, `real_s2_poolcheck`) came from `gt_depth_mm` with the per-face-minimum z-map; re-rendered at the same poses with exact rasterization (`aligntac_newobj/regen_gt_exact.py` -> `*_exact` roots; face-min re-render reproduces the stored GT to 1e-7, change 0.056 mm over contact). All 138 `cross_session_fv` / `s2half` entries re-evaluated (`aligntac_newobj/reeval_s2_exact.sh`); pose metrics identical (< 1e-3 deg), contact MAE -0.006 to -0.023 mm. `ablation/pilot_robosoft/cross_session_results.json` now holds the exact-GT values (old: `cross_session_results_facemin_gt.json`; `_bp` entries unchanged).
Paper: zero-shot AlignTac vs real only 14-21% (was 15-20%); + learned synth. K=100 0.235 mm, -32% (was 0.248, -31%); adaptation a further 5% (three-seed: K=25 0.295 -> 0.280, -5.1%; K=100 0.271 -> 0.256, -5.5%; per seed -4.3/-4.3/-6.4 and -7.8/-6.1/-2.7; was 6%), abstract and long conclusion too. Table III MAE/IoU and ranks updated by hand in data/tables.tex; long tabcross regenerated (was not hand-edited); pool label IoU 0.50 -> 0.58 (K=25), 0.56 -> 0.62 (K=100); legacy session-2 paragraph numbers updated.
- Author decision (2026-10-25): the per-face-minimum z-map inside the 12-object pseudo-labels / aligner inputs is left as is and NOT mentioned in the paper.

### 2026-10-25 figures folder layout
`figures/fig1_teaser.pdf` ... `figures/fig8_poseref.pdf` = conference-paper figures in order; `figures/long/` = extended-version-only figures; `figures/src/` = TikZ wrappers, grids, curves and PPT sources (`python build.py --figures` rebuilds fig4-6 from them). Everything else moved to `figures_archive/` (local only, not synced to Overleaf). Fig. 6 grid: `scripts/fig_qual_plus4.py paper_RoboSoft/figures/src wide`, rename to `fig6_image_grid.pdf`.

### 2026-10-25 co-author (X. Xu) figure suggestions
- Fig. 6: last row of each group now shows surface normals (mean angular error over GT contact) instead of a fourth depth row — depth MAE can understate differences (marble: MAE 0.089 vs 0.098 but normals 9.7 -> 4.0 deg). Set-level normal error real only -> AlignTac: A 27.1 -> 23.1, B 19.0 -> 15.9, new objects 20.0 -> 15.5 deg. Dumps now store normals (`dump_qual_preds.py`, `eval_newobj.py`); grid `fig_qual_plus4.py`.
- Fig. 7(b): "after 6 iterations" replaced by curves after 1/2/3/6 updates on a log axis with the no-update diagonal (`make_paper_figs.fig_conv`); same data (`aligner_convergence.json`).
- 2026-10-26 (author): Fig. 6 examples now chosen by largest real-only minus AlignTac error among frames whose AlignTac error is at most the object median (`FIG6_SELECT=gain`, default; `median` restores the old rule; the 2026-10-23 manual picks are kept in `figures/src/fig6_picks_author_2026-10-23.json`). Axis titles simplified: Fig. 4/8 x-axis "K" (caption defines K), Fig. 4 panel titles carry units, Fig. 7 y-axis "Rotation error [deg]", (b) titled "After n updates" with n at the curve ends. Fig. 7 1.5 in tall, Fig. 8 1.85 in (page budget).
- 2026-10-26 (author, round 2): Fig. 6 numbers sit in the corner with the fewest contact pixels (`free_corner`); hex key example = frame 145 (`figures/src/fig6_picks.json`). Fig. 7 fonts reduced, (b) colours saturated, n=0 label, grid ends at 30 deg (labels outside the axes). Fig. 4 tick labels 5.8 pt and headers closer; Fig. 5 now the plain matplotlib export (wrapper no longer re-typesets labels); Fig. 8 tick labels 5.8 pt.
- 2026-10-26 (video): result slides no longer use paper-figure screenshots. `scripts/video_plots.py` renders dark, large-font video versions from the same data as `make_paper_figs.py` / `fig_qual_plus4.py`: `video/plots/kshot_anim.mp4` (Fig. 4 contact MAE, one method revealed at a time), `labels_anim.mp4` (Fig. 5, teacher curves then aligned curves), `align_toggle.mp4` (Fig. 3 frames: mesh at teacher pose <-> aligned pose with IoU), `qual_cycle.mp4` (Fig. 6 picks, two samples at a time, depth + normal rows with errors), `align_anim_plot.mp4` (slide 7: alignment strips + Fig. 7(a) curve growing update by update), `conv_b.png` / `poseref.png` (Fig. 7(b) / Fig. 8 restyled). Deck 178 s, 12.6 MB, 1920x1080 30 fps. Pipeline: `video_deck.py` (and with `DECK_POSTER=1`) -> `soffice --convert-to pdf` of the poster deck -> `pdftoppm -r 144 -png ... bg` into `video/render/` -> `video_render.py`.
- 2026-10-26 (video, white version): deck switched to a white background and Arial (no font requirement from RoboSoft), titles 32 pt; numbers are tables (`video_deck.table`, "No Style, Table Grid"); stream clips trimmed (`video_stream_clips.py --pred-sec/--label-sec`, in seconds of the 4 fps clip: pattern 32 prediction 6-12.5 s, labeling 5-13.5 s, pattern 36 prediction from 7 s), pose glyph removed, "after aligner updates" header; `write_clip` now clears stale frames (old frames were being concatenated). Clips with GIFs are embedded as animated GIFs in the pptx (`movie(..., gif=)`); the mp4 render uses the mp4s. Slide 9 shows all six Fig. 4 panels (`video_plots.kshot6`); slide 11 cycles the four additional objects with depth + normal rows (`video_plots.qual_p4`) next to a results table. All clip canvases and plots are white (`video_align_anim.py`, `video_perturb_clip.py`, `video_newobj_scan.py`, `video_plots.py`). 178 s, 13.1 MB.
- 2026-10-26 (video, slide 7): alignment strips on top, the live Fig. 7(a) curve bottom-left (`video/plots/conv_live.mp4`, same 8.57 s timing as `align_anim.mp4` so the two loop in sync), and a table over all 530 test frames bottom-right: rotation / translation from the paper's `aligner_convergence.json`, mesh-label IoU / contact MAE per update from `aligner_convergence.py --label-metrics --real-root real_filtered_testA` -> `aligner_convergence_video.json` (its own rot/trans differ from the paper file by <= 0.15 deg, GPU re-run; the paper file stays the reference).
- 2026-10-26 (video, author's deck): the author's hand-edited deck `video/AlignTac Video.pptx` is now the source (backup `AlignTac Video_orig_2026-10-26.pptx`). `scripts/video_render_pptx.py` renders any deck: movie objects and animated GIFs are the clips (deck crops honoured, groups flattened for LibreOffice, seconds from the notes), and it checks that every clip region changes between two moments. Video wording uses "depth MAE" (the paper keeps "contact MAE"): `video_plots.py` takes `MAE_NAME`, `QUAL_NOHDR=1` (qual_cycle without its header row) and `ALIGN_TOGGLE_INTILE=1` (phase label inside the mesh tile); outputs in `video/plots_depthmae/`.
- 2026-10-27 (cleanup): `paper_RoboSoft/video/` reduced to the author's deck, the rendered mp4, `clips_in_deck/` and `plots/` (old generated decks, render dirs and raw clip outputs removed; `video_deck.py` / `video_render.py` deleted, `video_render_pptx.py` is the renderer). Unused runs: `CLEANUP_PLAN_2026-10-27.md` lists what the table/figure builders read (access-logged run of `build_tables.py --force` with `tables.tex` redirected, plus `make_paper_figs.py`). Tier 1 deleted (34 run dirs on hdd2: facemin, bugview, rcp00/25/75, al2u25/u50, al2_r2, semi/semi_pseudo, 3dcal, dav2/t3, bgsub, 50-epoch ganloo; `robosoft_qual/bak`, `qual_P4_facemin.npz`, `aligner_p4_k25_realonly_facemin`, `tactile_gan40m_al_k25_bugview`, the facemin p4 pseudo sets, aligntac_newobj facemin files, their yamls). Renderer/aligner model dirs (C) are kept.
- 2026-10-27 (cleanup, cont.): tier 2 deleted as well (37 run dirs, 37 GB: 50-epoch pilot_A_* protocol runs, pilot_B_k10/k50 sweeps and seeds, superseded sensor-B seeds) with their now-orphaned yamls; pseudo-label sets (B) and renderer/aligner models (C) kept. 229 paper runs remain on hdd2.
- 2026-10-28: the marker-free sensor is now named GelSlim 5.0 (arXiv:2610.31334, `wang2026gelslim`; `\sensor` macro = "GelSlim~5.0"); sensor B stays "dot-marker GelSlim~4.0". Wording "two GelSlim sensors" / "both sensors" replaces "GelSlim 4.0 variants"; Sec. V-C title "Robustness Across Sessions, Sensors and Objects"; "Cross-sensor applicability". Bibliography: 30 records, new entry tied in `bibliography_layout.tex`. Co-author Overleaf edits merged first (abstract/intro wording, Sec. V-D moved before V-E, Fig. 1/2 PDFs). Video deck text updated the same way and the mp4 re-rendered.

## 2026-11-01 — RSS experiments, round 1 (ICP / optimization baselines, calibration-free initialization, new-object labeling)
Scripts: `scripts/tactile_render/fit_baselines.py` (teacher-pose init -> grid / ICP / gradient descent / aligner / global search; `--perturb`
basin-of-convergence sweep from the GT state), `ablation/pilot_robosoft/make_loo3_split.py` (held-out objects pattern_04_3_lines_angle_2,
pattern_31_rod, pattern_33: odd frame index = unlabeled pool, even = TEST, roots `gs_blender/real_loo3{,_test}`), `chain_loo3.sh`
(teacher pilot150_A_bgcondloo -> aligner `outputs/aligner_loo9` trained on the 9 seen objects, all their labels, GAN-LOO sim -> roots
`real_pseudo_loo3_{ng,al,tp}` -> merged roots `real_loo3_merge_{al,tp,oracle}` + `data_A_loo3_*.yaml`), `train_loo3.sh` (150 ep, eval on
`real_loo3_test`, json `loo3_results.json`, tags loo3test / loo3test_bp). Logs in `outputs/rss_logs/`.
- Optimization baselines (K=25, teacher B_k25_realonly, 650 of the 3,897 unlabeled session-1 frames, `fit_baselines_k25.json`), IoU / cMAE / rot:
  mesh @ teacher pose 0.476 / 0.400 / 5.7; local grid search on the teacher depth 0.627 / 0.303 / 2.8; point-to-point ICP 0.601 / 0.348 / 3.0;
  Adam on the dense depth L1 0.638 / 0.337 / 2.3; learned aligner 0.712 / 0.241 / 1.0.  Global search (360 deg x +-7 mm, no initial pose)
  0.634 / 0.302; global + aligner 0.706 / 0.246 (pose only up to the mesh symmetry: symmetry-aware rot 4.5, median 0.9).
- Basin of convergence (325 frames, GT state rotated by +-d, 0.5 mm shift): aligner IoU 0.71 / 0.71 / 0.70 / 0.70 / 0.67 at 10/15/20/25/30 deg;
  grid 0.64 / 0.64 / 0.55 / 0.42 / 0.32; ICP 0.62 / 0.55 / 0.49 / 0.46 / 0.43; gradient descent 0.64 / 0.62 / 0.58 / 0.53 / 0.46.
- Session 2 (162 pool frames with a curated label, `fit_baselines_s2_k25.json`): mesh @ teacher pose 0.291 / 0.548 / 17.0; grid 0.484 / 0.404;
  ICP 0.494 / 0.425; GD 0.511 / 0.442; aligner 0.580 / 0.326 / 8.6 (median 2.7); global + aligner 0.601 / 0.320 (no teacher pose at all).
  Two-line patterns remain hard for every method (IoU 0.4); the aligner holds IoU 0.60 up to 25 deg of initial error, ICP drops from 15 deg.
- New-object label quality (1,118 train-split frames of the three held-out objects, aligner never saw them): teacher depth 0.575 / 0.322 / 4.9;
  mesh @ teacher pose 0.409 / 0.472 / 4.9; mesh @ aligner_loo9 0.594 / 0.331 / 1.4.  Students (al / tp / oracle) training; reference models
  on the 635 TEST frames: A_bgcondloo cMAE 0.327 / IoU 0.631 / rot 4.6; A_ganloo 0.335 / 0.616 / 5.6; A_realonly 0.363 / 0.578 / 54.

## 2026-11-09/10 — project moved to /media/hdd; RSS round 2 started (task list: /media/hdd/ihsuan/VisTacFusion/RSS_ROUND2_TASKS.md)
- Move: every `/media/hdd2/ihsuan` path in AlignTac, VisTacFusion sources/configs, gs_blender manifests and 608,708 symlinks rewritten to `/media/hdd/ihsuan`
  (commit 464e356 on branch `rss-round2`). New run dirs live on `/media/hdd2/users/ihsuan/AlignTac_runs` (symlinked into `runs/`).
- The SITR encoder checkpoint (`gsrl/datasets/checkpoints/SITR_B18.pth`) was deleted with `gsrl/`; rebuilt from the frozen encoder tensors stored in
  run checkpoints (bit-identical across pilot150_T_k25_rf, A_bgcondloo, T_k100_realonly, pilot_T_k25_tp) -> `VisTacFusion/weights/SITR_B18.pth`;
  re-evaluating pilot150_T_k25_rf on testA reproduces the stored numbers exactly (MSE 0.038343, cMAE 0.233292, IoU 0.737425). All `tac_sitr_*.yaml` updated.
  The conda env's editable install also pointed at hdd2; fixed. Scripts run as files must set PYTHONPATH=AlignTac (rss2_train.sh does) so that
  evaluation imports the same `vistacfusion` snapshot the training used (`python -m` picks it up from the cwd).
- Naming: new tables call `*_realonly` "Labeled only". Infrastructure: `rss2_queue.py` (GPU queue; jobs `outputs/rss_logs/rss2_jobs*.tsv`), `rss2_train.sh`,
  `rss2_build_roots.sh`, `rss2_subset_root.py`; mean teacher in `vistacfusion/engine/train.py` behind `mean_teacher.enabled` (configs `train_pilot_e150_pm_mt_w{1,10,50}*.yaml`,
  data `data_T_k25_mt*.yaml` = teacher-depth root `real_pseudo_k25_ro_ng`, labels of pseudo frames never enter a loss).
- P0-1 labels (`rss2_fit_s1_k25_full.json`, all 3,897 K=25 pool frames, IoU / cMAE / rot): teacher depth 0.554/0.315/6.0; mesh@teacher 0.47/0.40/6.0;
  grid 0.608/0.340/3.1; ICP 0.636/0.337/2.6; GD 0.630/0.298/3.0; aligner 0.719/0.235/1.1. Roots `real_pseudo_k25_ro_{icp,gd,grid}` (pseudo_label_rc --fits), configs `data_T_k25_{icp,gd,grid}.yaml`.
- P0-3 / T2 (`rss2_fit_s2_k{25,100}.json`, 162 curated pool frames): recorded pose + session-1 calibration ("old calibration") IoU 0.352 / cMAE 0.504 / rot 4.9 (med 2.5) / trans 1.91 mm;
  K=25 aligner 0.580/0.326/8.6 (2.7)/1.41; ICP 0.494/0.425; GD 0.511/0.442; global+aligner 0.601/0.320. K=100 aligner 0.628/0.300/4.4 (2.0).
  Recorded pose -> aligner (no teacher; `rss2_s2_consensus_k*.json` stepB): K=25 0.564/0.353/4.2/1.24, K=100 0.626/0.306/2.7/1.06.
- DRIFT NUMBER: curated label minus recorded pose, per-run medians over 38 runs = mean 3.42 deg / 3.02 mm, median 1.41 deg / 1.44 mm. This disagrees with the
  paper's "11.4 deg / 1.6 mm" (pose_calibration_new.json, v2 per-object grid fit). Open question for the user before any text changes.
- P2-8 Step A (`rss2_s2_consensus_k25.json`): run consensus (aligner from the recorded pose) vs curated reference: rot median 1.12 / mean 2.85 deg, trans median 1.61 / mean 2.36 mm,
  21% of runs within 2 deg / 1 mm; 20 presses per run: 1.1 deg / 1.4 mm. Within-run scatter of curated-minus-recorded ~0.8 mm -> offset not rigid. GATE NOT MET.
  consensus -> aligner labels: K=25 0.591/0.326, K=100 0.646/0.287 (vs 0.580 / 0.628). Roots `real_pseudo_s2_k25_{oldcal,recal,consal}` + merged `real_merge_k25_rf_s2{oldcal,recal,consal}`, configs `data_T_k25_rf_s2{oldcal,recal,consal}.yaml`.
- P1-5 (`rss2_confidence_s{1,2}_k25.json`): conf = mean rank of multi-start agreement, global-start agreement, teacher-depth IoU, 1 - last correction. Spearman vs cMAE / 1-IoU / rot:
  S1 0.36 / 0.34 / 0.21 (n=3897), S2 0.44 / 0.60 / 0.62 (n=162). Keeping 75% by conf: S1 IoU 0.719->0.751, cMAE 0.235->0.210 (random unchanged; oracle 0.803/0.166);
  S2 0.580->0.658, rot 8.6->2.3. Roots `real_pseudo_k25_ro_al_{conf,rand,oracle}{75,50}` (`rss2_subset_root.py`), oversample 3 / 4 to keep epoch size.
- P1-6 roots `real_pseudo_k25_ro_al_u{25,50}`, `real_pseudo_k25_u{25,50}` (same frame subset, `--like`), oversample 7/4 (rf) and 3/2 (semipm).
- P0-4: `pilot150_A_loo3_{al,tp,oracle}` (5-epoch fragments from 11-01) retrained from scratch in place + `rss2_A_loo3_*_seed{1,2}`; eval tag loo3test(_bp) in loo3_results.json.
- Queue A (`rss2_jobs.tsv`): 9 LOO-3 + 3 mean-teacher runs. Queue B (`rss2_jobs_b.tsv`, 27 jobs): icp/gd/grid/tp + seeds, realonly/semipm seeds, s2 oldcal/consal/recal, u25/u50, conf/rand/oracle filters.
  Queue B's first attempt (11-09 21:30-21:48) failed on the missing SITR checkpoint; restarted 11-10 02:40 with a clean state.
- 2026-11-10 (user decision): drift wording changed in `sections/03_setup.tex`, `sections_long/03_setup.tex` and both `05_experiments.tex` ("Label-free cross-session
  adaptation"): the old "per-run corrections averaged 11 deg / 1.6 mm" (pose_calibration_new.json grid search, which locks onto wrong rotations for the symmetric
  two-line patterns) is replaced by the curated-GT-vs-recorded-pose drift (medians 1.4 deg / 1.4 mm, means 3.4 deg / 3.0 mm over 38 runs; `rss2_s2_consensus_k25.json`
  "drift") and its consequence (recorded-pose labels IoU 0.35 / cMAE 0.50; `rss2_fit_s2_k25.json` "old calibration"). PDF not rebuilt, Overleaf not pushed.
- 2026-11-10 two-line patterns / aligner range (`rss2_multistart_s2_k25.json`, `rss2_fit_s{1,2}_k25_range2.json`, `outputs/aligner_k25_realonly_range2`):
  on the 162 curated session-2 frames the three two-line patterns (pattern_01_2_lines_angle_{1_2,2,3}, n=31) stay at IoU 0.40 (teacher init 15-25 deg off; session 1: 0.60-0.68).
  Multi-start (teacher / global / recorded / teacher+period/2) + label-free selection by the aligner's residual correction: all 0.580 -> 0.607, two-line 0.396 -> 0.434;
  oracle best-of-4 only 0.473 on two-line -> not only an initialization problem. Selecting by renderer L1 is harmful (0.538), by black-hat mask IoU 0.605.
  Aligner retrained with the paper's recipe (K=25 real labels only, no synthetic frames) but 2x perturbation range (+-16 deg, +-3 mm, +-0.3 mm):
  session 1 IoU 0.721 / cMAE 0.231 / rot 1.10 (default 0.712 / 0.241 / 1.04); basin: IoU 0.72 at 20 deg and 0.715 at 30 deg (default 0.70 / 0.67);
  session 2 0.589 / 0.323 / rot 5.8 (default 0.580 / 0.326 / 8.6). Small, consistent gain; NOT adopted as the default (would invalidate the 3-seed students) -> report as a robustness ablation.
- 2026-11-10 P1-7 localization (`rss2_localize.json`, `rss2_localize.py`; sym.-aware rot, trans = mean|dx|,|dy|, success = rot<2 & trans<0.5 mm): testA K=25
  Labeled only head 5.7 deg / 1.09 mm / 16% -> +align 0.8 / 0.65 / 69%; AlignTac head 3.1 / 0.87 / 33% -> +align 0.6 / 0.64 / 69% (3-seed means); global search on
  predicted depth + align 66-67%. K=100 +align 0.3 deg / 0.28 mm / 86%. s2half: heads 15 / 10 deg, +align ~5 deg (median 1.2-1.3), 35% success for every method.
- 2026-11-10 mean teacher, first sweep (`rss2_T_k25_mt_w{1,10,50}`, EMA teacher evaluated): validation depth MSE degrades with training (w=1: 0.052 at ep 20 -> 0.10 at
  ep 129; w=10: 0.10 -> 0.15; w=50: 0.20 -> 0.47; Labeled only stays ~0.057). Consistency on the unlabeled pool reinforces the teacher's own errors and the weight is far
  too large relative to the uncertainty-weighted supervised terms (train depth MSE 1e-4). Second sweep launched: w = 0.1, 0.01 and 0 (strong augmentation only, isolates
  the augmentation effect). Incident: rss2_train.sh was edited in place while 28 jobs were running; bash reads scripts incrementally, so the post-training step of those
  jobs executes a garbled line (seen for mt_w10: "line 20: data_T_k25_mt_w10.yaml: Permission denied"). Training itself is unaffected (final.pt written);
  `rss2_finisher.sh` (10-min loop) evaluates any finished run without results, and rss2_train.sh now skips training when final.pt exists; the file is replaced atomically from now on.
- 2026-11-10 students, round 2 (testA; `rss2_testA_results.json`): ICP labels 0.309 / 0.469 (3 seeds, IoU 0.38-0.58, unstable), GD labels 0.322 / 0.688 (2 seeds),
  teacher pose + mesh 0.307 / 0.620, Labeled only 0.291 / 0.676, AlignTac 0.233 / 0.737. Mean teacher sweep (EMA teacher evaluated): w=50 0.298 / 0.224, w=10 0.282 / 0.350,
  w=1 0.295 / 0.684; best validation depth MSE w=0 0.0515, w=1 0.0517, w=0.1 0.0537, w=0.01 0.0548 (Labeled only 0.0561, AlignTac 0.0426) -> consistency adds
  nothing beyond the strong augmentation; w=1 chosen by validation, seeds 1-2 queued. P0-3 student `rss2_T_k25_rf_s2oldcal` on the session-2 test half:
  cMAE 0.447 / IoU 0.481 / rot 5.5 / trans 1.58 mm vs AlignTac without session 2 0.292 / 0.659 / 10.2 / 1.49 and recalibrated 0.280 / 0.652 / 7.8 / 1.32;
  on testA unchanged (0.241 / 0.732). Stale-calibration labels actively hurt the drifted session. Note: "train FAILED" lines dated after 06:12 for
  mt_w1, mt_w50 and A_loo3_oracle_seed1 come from shells that were started before the atomic replace of rss2_train.sh (they still read the old inode);
  their final.pt exist and the finisher evaluated them. Paused low-priority jobs resumed on GPUs 1-3; GPU-0 ones resume automatically when the LOO-3 runs finish.
- 2026-11-10 LOO-3 students complete (`loo3_results.json`, 635 test frames of pattern_04_3_lines_angle_2 / pattern_31_rod / pattern_33, 3 seeds):
  AlignTac labels 0.332+-0.001 / 0.622+-0.003 / rot 3.2; teacher pose + mesh 0.426 / 0.486 / 4.5; oracle labels 0.233 / 0.725 / 3.0; teacher itself
  (A_bgcondloo) 0.327 / 0.631 / 4.6; Labeled only on 9 objects 0.363 / 0.578 / 53.6. Pose claim confirmed, dense gain over the teacher not
  confirmed on unseen objects (labels are at teacher-depth level on cMAE). Written as T3 in RSS_ROUND2_RESULTS.md with an open question on framing.
- 2026-11-10 18:53 mean teacher sweep complete (testA cMAE / IoU, EMA teacher): w=0 0.288 / 0.669, w=0.01 0.298 / 0.680, w=0.1 0.293 / 0.687, w=1 0.295 / 0.684,
  w=10 0.282 / 0.350, w=50 0.298 / 0.224; Labeled only 0.291 / 0.676. No weight helps; T1 updated.
- 2026-11-10 19:05 batch of students finished (testA cMAE / IoU / rot): Labeled only 2 seeds 0.300 / 0.677 / 5.8; self-training 3 seeds 0.300 / 0.627 / 8.5;
  teacher pose + mesh 3 seeds 0.302 / 0.624 / 5.5; grid labels 0.294 / 0.684 / 4.0. Unlabeled quantity (F2): AlignTac 25 / 50 / 100 % = 0.247 / 0.244 / 0.233 cMAE,
  self-training 0.308 / 0.294 / 0.301. Confidence filtering: conf-50 % 0.239 / 0.731, oracle-75 % 0.230 / 0.741. Session-2 test half: run-consensus labels
  (no recalibration) 0.292 / 0.667 / rot 5.5 / 1.18 mm vs recalibrated 0.280 / 0.652 / 7.8 / 1.32 -> strongest recalibration-free student result.
  Still training: realonly_seed1, gd_seed2, rf_s2recal, conf75, rand75, rand50, oracle50, mt_w1 seeds 1-2.
- 2026-11-10 20:45: `rf_s2recal` (recorded pose -> aligner, no consensus) on the session-2 test half 0.295 / 0.659 / rot 5.4 / 1.21 mm = consensus version within noise;
  GD seed 2 0.323 / 0.693 (3 seeds 0.322 / 0.689); mean teacher w=1 seed 1 0.279 / 0.687; filter students rand-75 % 0.242 / 0.721, oracle-50 % 0.237 / 0.735.
  Remaining: realonly_seed1, mt_w1_seed2, conf75, rand50.
- 2026-11-10 SESSION-2 GT PROVENANCE AND NOISE (user question). The 854 curated frames (`real_filtered_new_curated_pred_r2[_fv]`, `scripts/curate_new_real_test.py --mask pred`):
  recorded robot pose + session-1 OBJ_MAP + per-run calibration (best of v1 per-run / v2 per-object) -> per-frame local refinement of (theta, x, y) within +-3.5 deg / +-1.75 mm
  (final step 0.25 deg / 0.125 mm) maximising IoU between the projected mesh contact and the contact mask of the PREDICTED depth of the user's earlier VisTacFusion model
  (`new_real_test/output`); press depth from the robot (not refined); keep refined IoU >= 0.75 x best of the object (final set: mean 0.84, min 0.64); review grids approved by the user
  (pattern_04_3_lines_angle_2 dropped as "all wrong"). So the session-2 reference is a fitted label, not a calibration-based one. Noise estimate: on the 28 frames that also have a
  black-hat-mask refinement (`curated_selection.json`) the two refined poses differ by median 3.1 deg / 0.84 mm (p90 6.8 deg / 1.9 mm); this is an upper bound (black-hat masks are
  noisier). Consequence: session-2 pose errors below ~2-3 deg / ~1 mm (label rot medians 2-2.7 deg, drift median 1.4 deg / 1.4 mm, localization success at 2 deg / 0.5 mm,
  the 0.8 mm within-run scatter that failed the P2-8 gate) are at the level of the reference noise and should not be over-interpreted. Session-1 GT is calibration-based.
- 2026-11-10 20:45 more students: rand75 0.242 / 0.721, oracle75 0.230 / 0.741, conf50 0.239 / 0.731, oracle50 0.237 / 0.735 (filtering is flat on session 1);
  GD seed 2 0.323 / 0.693; mean teacher w=1 seed 1 0.279 / 0.687; session-2 test half: rf_s2recal (aligner from the recorded pose) 0.295 / 0.659 / rot 5.4 / 1.21 mm,
  rf_s2consal 0.292 / 0.667 / 5.5 / 1.18 -> both recalibration-free variants match the recalibrated student (0.280 / 0.652 / 7.8 / 1.32).
- 2026-11-10 21:30 round-2 students complete. Last four (testA cMAE / IoU / rot): Labeled only seed 1 0.299 / 0.672 / 6.1 (3 seeds 0.299 +- 0.009 / 0.675 +- 0.003);
  mean teacher w=1 seed 2 0.286 / 0.652 (3 seeds 0.287 +- 0.008 / 0.675 +- 0.019); conf-75 % 0.244 / 0.730; random-50 % 0.251 / 0.722.
  Queue B and the finisher loop stopped (nothing left to run). All tables in RSS_ROUND2_RESULTS.md are final for round 2 except P2-9 (not started).
- 2026-11-10 21:30-22:30 ROUND 2b (details and tables: RSS_ROUND2_RESULTS.md, section "Round 2b").
  CORRECTION: `pilot150_T_k25_rf_s2` is teacher -> aligner with the recorded poses never used; it was wrongly called "recalibrated" in the T2 student table. No recalibrated-label student exists.
  Controlled drift on session 1 (`rss2_drift_s1.py`): stale-label IoU 0.94 / 0.74 / 0.56 / 0.30 / 0.19 / 0.14 at 0 / 0.5 / 1 / 2 / 3 / 4 mm; aligner from the stale pose 0.725 at every level.
  Students `rss2_T_k25_dr{05,10,20,30}_{stale,al}` queued 21:42 (roots `real_pseudo_k25_ro_dr*`, fits `outputs/rss2_fits/s1_k25_drift`, `rss2_drift_roots.sh`).
  Unseen-object diagnosis (`rss2_loo3_diag.py`): error is translation only and anisotropic (aperture problem on line / rod objects, seen or unseen); aligner fixed point from the TRUE state
  is IoU 0.725 seen / 0.614 unseen; pattern_33 generalizes (0.736), rod and 3-lines do not. Run-level fusion (`rss2_run_consensus_s1.py`): seen 0.719 / 0.235 -> 0.901 / 0.082 (0.08 deg, 0.10 mm);
  with teacher / grid / ICP / GD as the per-touch method 0.79 / 0.85 / 0.85 / 0.85; unseen 0.594 -> 0.663. train_aligner.py gained --synth-ranges / --synth-weight (objects seen only as
  synthetic frames); aligners loo9_syn3, loo9_syn3_r2, loo9_r2 training. Queue B and the finisher had been terminated at 21:15 (after the last round-2 job); restarted detached (setsid).
- 2026-11-10 22:25 aligner_loo9_syn3_r2 (9 seen objects + synthetic-only frames of the 3 new meshes, pose ranges from the teacher's predictions on unlabeled frames, 2x range):
  unseen per-touch labels 0.594 / 0.331 -> 0.624 / 0.312 (rot 0.8, trans 0.99 mm); pattern_33 0.767 / 0.190 (= seen level), rod 0.597, 3-lines 0.500; fixed point from the TRUE state 0.626.
  Now above the teacher depth (0.575 / 0.322) on both metrics; line / rod objects stay at the single-touch limit. (`rss2_loo3_diag_unseen_syn3_r2_early.json`; syn3 and r2 controls still training.)
  Metric definition for the record: IoU = |{label or predicted depth > 0.05 mm} AND {reference depth > 0}| / union, both from depth maps (reference = mesh rendered at the reference pose);
  no mask is extracted from the tactile image at evaluation time. Image-derived masks enter only in the construction of the session-2 reference poses.
- 2026-11-11 INFRA: reboot at 11-10 23:52. Mount points swapped again (project disk now /media/hdd2, overflow disk /media/hdd-slam, /media/hdd is a 9.1T NTFS disk).
  No path rewrite: shim symlinks /media/hdd/ihsuan/{VisTacFusion,gs_blender} -> /media/hdd2/ihsuan/...; 50 run symlinks re-pointed to /media/hdd-slam/users/ihsuan/AlignTac_runs;
  rss2_train.sh picks the existing overflow path. The 8 drift students were killed at epochs 79-111 and resumed with --resume latest.pt (train.py now truncates history to the
  resumed epoch and restores the best validation rotation so best_pose.pt is not overwritten by a worse epoch). rss2_queue.py now reserves memory for jobs it started that have
  not allocated yet (--job-mib). A teammate's jobs hold ~40 GB per GPU: queue runs one of our jobs per GPU (--min-free 7500).
- 2026-11-11 NEW OBJECTS (section D4 of RSS_ROUND2_RESULTS.md): aligner onboarding from the mesh (`outputs/aligner_loo9_syn3_r2`, synthetic-only frames of the 3 new meshes, 2x range)
  + observability-aware fusion (`rss2_obs_fusion.py`, hybrid: rotation median, translation information form with W = J^T J of the mesh depth): unseen labels 0.594 / 0.331 -> 0.769 / 0.177
  (teacher depth 0.575 / 0.322; seen per-touch 0.719 / 0.235). Controls: 2x range only 0.574 -> 0.678, synthetic only 0.612 -> 0.757, round-1 aligner 0.594 -> 0.735; plain median fusion 0.663 / 0.718.
  Roots `real_pseudo_loo3_{obsf,obsf9,syn}`, merged roots `real_loo3_merge_*`, configs `data_A_loo3_{obsf,obsf9,syn}.yaml` (`rss2_loo3_obsf_roots.sh`); students queued.
  Literature notes for the session-2 reference labels in section D5.
- 2026-11-11 SESSION-2 REFERENCE AND FUSION ON SESSION 2 (section D6). Rigid per-run re-fit of the session-2 reference rejected: residual about a run constant 0.63 mm (shared sensor-frame
  offset does not help), same-press repeatability 0.37 mm, press means 1.02 mm, split-half 0.94 deg / 1.09 mm, black-hat IoU curated 0.307 vs rigid 0.240 vs recorded 0.171.
  Decision: curated labels stay the session-2 reference for dense metrics only; no session-2 pose claims below ~1 mm / 2 deg. Session-1 controlled drift predicts session-2 stale-label IoU
  (1.23 mm -> 0.565 vs 0.56; 2.34 mm -> 0.220 vs 0.30 / 0.19). Run fusion on session 2 (`rss2_s2_fusion.py`): rigid 0.478-0.515 vs per touch 0.564 (recorded start), MAP rho=4 0.579, adaptive 0.550;
  teacher start: per touch 0.580, rigid 0.47, adaptive 0.538. NOT a gain under the curated reference, which is biased towards per-touch fits -> fusion is validated on session 1 only.
  `adaptive_map()` in rss2_obs_fusion.py (rigidity sigma_r estimated per run): session 1 seen 0.824, unseen 0.683 (rigid 0.898 / 0.769). No session-2 fusion student queued.

- 2026-11-11 PORTABLE KIT: `portable/` (build_bundle.sh, verify_bundle.sh, setup.sh, run_jobs.py, AlignTac_colab.ipynb, README.md, jobs_{loo3,drift}.tsv). Bundle being built at /media/hdd-slam/users/ihsuan/aligntac_bundle (01_code, 02_real_core, 02b_real_rest, 03_sim_subset; paths relative to /media/hdd/ihsuan). rss2_train.sh accepts PY and RUNS_DIR from the environment. Nothing uploaded anywhere; the user moves the archives.
- 2026-11-11 PORTABLE BUNDLE VERIFIED: `/media/hdd-slam/users/ihsuan/aligntac_bundle` (01_code 5.1 GB, 02_real_core 2.2 GB, 03_sim_subset 12.6 GB, 02b_real_rest 6.7 GB; 60 GB extracted for the first three). Checks, all on the server in a mount namespace where the project disk is hidden: (1) `verify_data.py` -> BUNDLE OK, 0 dangling links; (2) every item of `data_A_loo3_syn` (16,756 train + 346 val) read in an environment holding only the pinned requirements; (3) `run_jobs.py --bench` (2.69 steps/s on a shared RTX 6000 Ada) and a 3-epoch job interrupted and resumed with the same command, evaluated; (4) `setup_local.sh` dry run from an empty home without conda (Miniforge, env `aligntac`, torch 2.5.1+cu121, extraction) -> BUNDLE OK. Local Windows goes through WSL2 (native Windows unsupported: absolute-path symlinks, bash job scripts). Local job list `portable/jobs_local.tsv` = `rss2_A_loo3_syn_seed{1,2}` (not in the server queue).
- 2026-11-11 LINK-TARGET BUG FOUND BY THE BUNDLE CHECK: roots built after the 11-10 reboot (`real_pseudo_loo3_{obsf,obsf9,syn}`, 3,390 links) pointed at the physical mount `/media/hdd2/ihsuan/...` because `pseudo_label_rc.py` used `realpath`; they would have broken at the next mount swap. Re-pointed atomically to `/media/hdd/ihsuan/...` (same files; the running `rss2_A_loo3_obsf` job was not disturbed) and `pseudo_label_rc.py` now maps the physical project path back to the stable one. Other scripts that link with `realpath` (`rss2_subset_root.py`, `make_*_split.py`, `rss2_s2_rigid_gt.py`) have the same hazard if run while the shim is in place: check new roots with `find <root> -type l -lname '/media/hdd2/*'`.
- 2026-11-11 QUEUE WATCHDOG + BACKFILL: `ablation/pilot_robosoft/rss2_watchdog.sh` (detached) restarts the queue / finisher loop if either dies; the queue polls every 30 s and starts a job on any GPU with >= 7.5 GB free (cap 4 of ours per GPU). After a reboot only the watchdog needs starting. Backfill appended to `rss2_jobs_b.tsv` at lowest priority: seeds 1 and 2 of the 8 controlled-drift students (16 jobs, error bars for D1); they only run once the primary jobs (dr30_al, A_loo3_{syn,obsf9,obsf_seed1,obsf_seed2}) have started. First drift students (seed 0, testA): 0.5 mm stale 0.232/0.727 vs aligned 0.233/0.740; 1 mm stale 0.316/0.580 vs aligned 0.229/0.742.
- 2026-11-12 CONTROLLED-DRIFT STUDENTS AND NEW-OBJECT STUDENTS DONE (RESULTS.md D1, D4; all 60 queued jobs finished rc 0). Drift students, 3 seeds, testA (cMAE / IoU / rot / trans):
  aligner labels 0.231 / 0.742, 0.231 / 0.741, 0.232 / 0.740, 0.231 / 0.741 at 0.5 / 1 / 2 / 3 mm (2.9 deg, 0.68-0.75 mm); stale labels 0.228 / 0.730, 0.330 / 0.548, 0.439 / 0.426, 0.494 / 0.353
  (3.3-3.4 deg, 0.69 / 0.90 / 1.44 / 2.04 mm). From 1 mm on the stale student is worse than Labeled only (0.299 / 0.675); at 0.5 mm the two are equal within seed noise (crossover, state it).
  New-object students (635 test frames): teacher 0.327 / 0.631; per touch 0.332 / 0.622; + mesh-only onboarding per touch 0.315 / 0.644 (3 seeds, sd < 0.001); fusion only 0.285 / 0.672 (1 seed);
  onboarding + observability-aware fusion 0.276 +- 0.003 / 0.688 +- 0.001, 3.0 deg / 1.39 mm (3 seeds); oracle 0.233 / 0.725. Fusion caveat unchanged (rigid by construction on session 1).
  T1 AlignTac row now 3 seeds: `pilot150_T_k25_rf_seed{1,2}` (trained 10-10, never scored on testA) evaluated into rss2_testA_results.json -> 0.235 +- 0.003 / 0.736 +- 0.001 / 3.2 deg / 0.87 mm.
  The user did not run the two `loo3_syn` seeds locally (kit installed and verified on an RTX 4060 Laptop under WSL2: BUNDLE OK, 1.75 steps/s, 5.9 GB); they ran on the server instead.
  Queue refilled with 12 seed jobs: `rss2_T_k25_grid_seed{1,2}`, `rss2_A_loo3_obsf9_seed{1,2}`, `rss2_T_k25_{rf,semipm}_u{25,50}_seed{1,2}` (error bars for T1 grid row, D4 fusion-only row, F2).
- 2026-11-13 NEW OBJECTS PER OBJECT + SECOND FOLD STARTED (RESULTS.md D4 per-object table, D7). `rss2_eval_per_object.py` (same data path as eval_cross_session.py; "all" reproduces stored numbers).
  Pose: every pseudo-labeled student = oracle on every held-out object; residual translation error of rod / 3-lines is on one pose axis (2.1-3.8 vs 0.6-1.1 mm), also for the oracle.
  Dense (cMAE / IoU): pattern_33 teacher 0.179 / 0.795, per touch + onboarding 0.185 / 0.800, + fusion 0.136 / 0.872, oracle 0.102 / 0.882; rod: oracle 0.349 / 0.614, all variants 0.332-0.358 (ceiling);
  3-lines: teacher 0.429 / 0.525, + onboarding 0.430 / 0.527, + fusion 0.318 / 0.660, oracle 0.211 / 0.760. CORRECTION: the aggregate "onboarding alone beats the teacher" (0.315 vs 0.327) is the rod only;
  dense gains on new objects come from fusion. One object per shape class -> second fold: held out pattern_01_2_lines_angle_1_2, pattern_32, pattern_35 (rule fixed in advance, see D7).
  `rss2_make_fold.py f2 ...` wrote roots real_f2 (1,373) / real_f2_test (692), f2_test_frames.json, data_A_f2_{teacher,realonly}.yaml; `rss2_fold.sh A|B` = queue jobs rss2_f2_chain{A,B}
  (inserted before the pending F2 seed jobs); rss2_train.sh / rss2_finisher.sh got the `f2` evaluation target (f2_results.json, tag f2test). Log: outputs/rss_logs/rss2_f2_chain.log.
  LINK FIX: the 11-11 patch of pseudo_label_rc.py did nothing under the current layout (/media/hdd/ihsuan is a real directory holding two shim links); it now maps per shim (gs_blender, VisTacFusion).

## 2026-11-13 LABEL CONVERSION: TRANSLATION NOT ROTATED WITH THE TOOL YAW (found, not yet acted on)
- Context: user confirmed the setup for a re-capture (objects screwed to a base that slides on a rail; arm presses; between sessions the
  sensor and the base were re-installed; "calibration" = sensor frame <-> robot frame; the capture program accepts specified poses).
  Testing the re-capture analysis script on existing session-2 data showed image-to-image press motion disagreeing with the labels.
- `rss2_recapture/rss2_recapture_check.py` (pairs / across modes; stored 224-px images cover 17.502 mm, the 0.816 crop is applied by the
  loader). Evidence scripts + pair data in `rss2_recapture/kinematics_check/` (s2_press_pairs, s1_label_pairs, abs_ridge_iou).
- Session 2, 125 press pairs / 15 runs / objects 32, 33, 35, 36: current conversion leaves 1.84 mm (median) unexplained, rotated model
  0.19 mm with no free parameter (free 2x2 fit = reflection, singular values 1.00 / 1.00, det -1.00; lever arm 0.2 mm).
  Session 1, 480 label pairs: 1.07 mm -> 0.24 mm. Session-1 filter kept 100 % of frames with predicted error < 0.5 mm and 0 - 20 % above 2 mm.
- Consequences and open decision: RSS_ROUND2_RESULTS.md D8 and open question 11. Re-capture on hold until the labels are corrected.
- Second fold: chain A started 11-13 02:20, chain B 04:23 (both renderers training); they use the current labels.

## 2026-11-13 CORRECTED LABELS BUILT AND VERIFIED (steps a, b of open question 11; user go-ahead)
- `reorganize_to_sim_format.py` (session-1 conversion) is not on this server (searched gs_blender, the project, /home/shared, the overflow disk).
- `rss2_recapture/rss2_relabel.py` (fit / build / overlay), `rss2_relabel_check.py`, `rss2_mirror_kin.py`; logs `outputs/rss_logs/rss2_relabel_*.log`.
  Roots: `gs_blender/real_filtered_kin` (4,669), `real_filtered_kin_testA` (530), `real_s2_kin_curated854` (854). Stored label values kept as `label_v1` in each pose file.
- Held-out NCC with the image: session 1 0.779 vs 0.598 stored (12/12 objects better); session 2 0.776 vs 0.574 curated vs 0.316 recorded pose (11/11).
  Split-half of the constants 0.05 mm / 0.11 deg (s1), 0.15 mm / 0.53 deg (s2). dtheta about +2.8 deg on every object in BOTH sessions (a constant of the old convention, not drift).
- True re-installation offset (session-1 constants on session-2 frames): 0.37 mm median plate offset, 0.31 deg, stale label error 0.38 mm; pattern_06_5 remounted 18 deg off.
- The existing students learnt the displaced labels (stored vs corrected test masks overlap at IoU 0.617 while students reach 0.736 against the stored ones);
  curated session-2 labels were fitted to model predictions and inherit the displacement.
- The loader reads the new roots unchanged (530 test frames, identical images). Details: RSS_ROUND2_RESULTS.md D9. Nothing re-trained.

