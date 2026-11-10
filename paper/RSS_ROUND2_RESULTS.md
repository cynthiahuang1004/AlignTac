# AlignTac — RSS 2027 round 2 results

Working document for the Stage-1 extended abstract (due 2026-12-04 AoE). Every number below comes from a JSON under
`ablation/pilot_robosoft/` (file named per section); run names, configs and logs (`outputs/rss_logs/`) are listed per task.
Branch `rss-round2` (not pushed). Last update: 2026-11-10 02:45 UTC.

## Status

| Task | Status | Notes |
|---|---|---|
| §1 Sanity check after the outage | done | data roots, meshes, checkpoints intact after the hdd2 → hdd move; SITR encoder checkpoint was lost with `gsrl/`, rebuilt from run checkpoints and verified bit-exact on testA |
| P0-1 Optimization labels → student | done (ICP ×3, GD ×3, grid ×1) | student table in the T1 section |
| P0-2 Mean teacher | done (6 weights, 3 seeds at w = 1) | no gain over Labeled only; see T1 |
| P0-3 Conventional labels under drift | done | `rf_s2oldcal`, `rf_s2consal`, `rf_s2recal` evaluated on the session-2 test half (T2) |
| P0-4 New objects (LOO-3) | done | 9 students (3 label sources × 3 seeds), T3 below |
| P1-5 Confidence | done | analysis + 6 filter students (F1) |
| P1-6 Unlabeled quantity | done (1 seed) | F2 below |
| P1-7 Single-touch localization | done | T4 below |
| P2-8 Session-level consensus | Step A done, **gate not met** | see section |
| P2-9 Multi-touch reconstruction | not started | |

## P0-3 / T2 — label quality on session 2 (`rss2_fit_s2_k25.json`, `rss2_fit_s2_k100.json`, `rss2_s2_consensus_k*.json`)

**K = 25** (162 session-2 pool frames with a curated label)

| Label source | IoU | Contact MAE (mm) | Rot mean / median (°) | Rot sym. (°) | Trans (mm) |
|---|---|---|---|---|---|
| Recorded pose, session-1 calibration (conventional) | 0.352 | 0.504 | 4.9 / 2.5 | 4.9 | 1.91 |
| Teacher depth (self-training label) | 0.506 | 0.387 | 17.0 / 17.4 | 17.0 | 2.24 |
| Mesh at teacher pose | 0.291 | 0.548 | 17.0 / 17.4 | 17.0 | 2.24 |
| Local grid search on teacher depth | 0.484 | 0.404 | 9.1 / 5.1 | 9.1 | 1.84 |
| ICP on teacher depth | 0.494 | 0.425 | 8.8 / 3.0 | 8.8 | 1.98 |
| Gradient descent on teacher depth | 0.511 | 0.442 | 8.1 / 2.5 | 8.1 | 1.80 |
| **AlignTac** (teacher → aligner) | 0.580 | 0.326 | 8.6 / 2.7 | 8.6 | 1.41 |
| Global search (no initial pose) → aligner | 0.601 | 0.320 | 54.8 / 4.3 | 9.2 | 1.76 |
| Recorded pose → aligner (no teacher) | 0.564 | 0.353 | 4.2 / 2.4 | 4.2 | 1.24 |
| Run consensus → aligner (P2-8) | 0.591 | 0.326 | 4.3 / 2.0 | 4.3 | 1.24 |

**K = 100** (162 session-2 pool frames with a curated label)

| Label source | IoU | Contact MAE (mm) | Rot mean / median (°) | Rot sym. (°) | Trans (mm) |
|---|---|---|---|---|---|
| Recorded pose, session-1 calibration (conventional) | 0.352 | 0.504 | 4.9 / 2.5 | 4.9 | 1.91 |
| Teacher depth (self-training label) | 0.571 | 0.393 | 12.7 / 11.1 | 12.7 | 2.04 |
| Mesh at teacher pose | 0.349 | 0.512 | 12.7 / 11.1 | 12.7 | 2.04 |
| Local grid search on teacher depth | 0.531 | 0.385 | 6.3 / 3.1 | 6.2 | 1.74 |
| ICP on teacher depth | 0.498 | 0.445 | 5.9 / 3.8 | 5.9 | 1.78 |
| Gradient descent on teacher depth | 0.583 | 0.426 | 5.7 / 2.6 | 4.8 | 1.49 |
| **AlignTac** (teacher → aligner) | 0.628 | 0.300 | 4.4 / 2.0 | 4.3 | 1.31 |
| Global search (no initial pose) → aligner | 0.623 | 0.310 | 63.0 / 4.4 | 23.6 | 2.41 |
| Recorded pose → aligner (no teacher) | 0.626 | 0.306 | 2.7 / 2.0 | 2.7 | 1.06 |
| Run consensus → aligner (P2-8) | 0.646 | 0.287 | 2.6 / 1.9 | 2.6 | 1.11 |

Takeaway: labels from the recorded pose with the stale calibration lose most of their IoU (0.35) through translation drift
(1.9 mm); their rotation error (4.9°) is lower than AlignTac's mean (8.6°, median 2.7°), so the drift story must be told in
IoU / contact MAE / translation, not rotation. AlignTac beats every optimization-based registration of the teacher depth, and
the aligner also works when started from the stale recorded pose instead of the teacher (K = 100: IoU 0.626 vs 0.628).

**Students on the session-2 test half** (464 frames; `rss2_cross_session_results.json`, references from `cross_session_results.json`;
dense at `best_depth.pt`, pose at `best_pose.pt`):

| Student (K = 25) → session-2 test half | Contact MAE (mm) | IoU | Normal (°) | Rot (°) | Trans (mm) |
|---|---|---|---|---|---|
| Labeled only (session-1 labels only) | 0.341 | 0.621 | 30.6 | 14.8 | 1.78 |
| AlignTac, session-1 pseudo-labels only | 0.292 | 0.659 | 27.5 | 10.2 | 1.49 |
| AlignTac + session-2 pseudo-labels, teacher → aligner, recorded poses never used (paper's `rf_s2`) | 0.280 | 0.652 | 27.5 | 7.8 | 1.32 |
| AlignTac + session-2 labels at the recorded poses, stale calibration (conventional) | 0.447 | 0.481 | 28.0 | 5.5 | 1.58 |
| AlignTac + session-2 pseudo-labels from the recorded poses → aligner, no recalibration (`rf_s2recal`) | 0.295 | 0.659 | 27.5 | 5.4 | 1.21 |
| AlignTac + session-2 pseudo-labels from run consensus, **no recalibration** (`rf_s2consal`) | 0.292 | 0.667 | 27.4 | 5.5 | 1.18 |

Takeaway (P0-3): adding session-2 frames labeled at the recorded poses with the stale calibration makes the student *worse*
than not using session 2 at all (IoU 0.481 vs 0.659, contact MAE 0.447 vs 0.292); the student learns the drifted contact masks.
Its rotation improves (5.5° vs 7.8°) because the pose targets are correct up to a small offset; only the dense targets are wrong.
On session 1 (testA) the same student is unaffected (0.241 / 0.732 vs 0.233 / 0.737), so the damage is confined to the drifted session.
CORRECTION (2026-11-10 21:50): an earlier version of this table called the paper's `rf_s2` row "recalibrated". It is not: it is the
teacher → aligner labeling that never reads the recorded poses. No student trained on recalibrated session-2 labels exists (only 390 pool
frames have a curated label), so the table has no recalibration upper bound. All three AlignTac rows are recalibration-free and differ only
in the aligner's starting point (teacher / stale recorded pose / run consensus); they agree on dense metrics (0.280–0.295 / 0.652–0.667),
and starting from the recorded pose gives better pose accuracy (5.4–5.5° / 1.2 mm vs 7.8° / 1.32 mm).

## P0-1 / T1 (label part) — session 1, K = 25, all 3,897 unlabeled frames (`rss2_fit_s1_k25_full.json`)
| Label source | IoU | Contact MAE (mm) | Rot mean / median (°) | Rot sym. (°) | Trans (mm) |
|---|---|---|---|---|---|
| Teacher depth | 0.554 | 0.315 | 6.0 / 3.7 | 5.9 | 1.14 |
| Mesh at teacher pose | 0.471 | 0.400 | 6.0 / 3.7 | 5.9 | 1.14 |
| Local grid search | 0.630 | 0.298 | 3.0 / 1.5 | 2.9 | 0.91 |
| ICP | 0.608 | 0.340 | 3.1 / 1.5 | 3.0 | 0.99 |
| Gradient descent | 0.636 | 0.337 | 2.6 / 1.2 | 2.3 | 0.90 |
| **AlignTac** | 0.719 | 0.235 | 1.1 / 0.4 | 0.9 | 0.67 |

Basin of convergence (325 frames, start = GT state rotated by ±d plus a 0.5 mm shift; `fit_baselines_k25.json`):

| Initial rotation error | 5° | 10° | 15° | 20° | 25° | 30° |
|---|---|---|---|---|---|---|
| grid IoU | 0.64 | 0.64 | 0.64 | 0.55 | 0.42 | 0.32 |
| icp IoU | 0.66 | 0.62 | 0.55 | 0.49 | 0.46 | 0.43 |
| gd IoU | 0.64 | 0.64 | 0.62 | 0.58 | 0.53 | 0.46 |
| aligner IoU | 0.71 | 0.71 | 0.71 | 0.70 | 0.70 | 0.67 |

Takeaway: the optimization baselines cannot beat the depth they fit (GD reaches contact MAE 0.298 vs. the teacher depth's 0.315);
the aligner, which reads the image, does (0.235). Student rows (testA, 530 session-1 frames; dense metrics at `best_depth.pt`, pose at `best_pose.pt`, translation = mean |dx|,|dy| in mm;
`rss2_testA_results.json`, references from `testA_results.json`):

| Student (K = 25) | n | Depth MSE | Contact MAE (mm) | IoU | Normal (°) | Rot (°) | Trans (mm) |
|---|---|---|---|---|---|---|---|
| Labeled only | 3 | 0.0486 | 0.299 ± 0.009 | 0.675 ± 0.003 | 27.1 | 5.9 ± 0.2 | 1.09 ± 0.02 |
| Self-training (teacher labels) | 3 | 0.0464 | 0.300 ± 0.003 | 0.627 ± 0.013 | 25.9 | 8.5 ± 0.1 | 1.50 ± 0.02 |
| Self-training, teacher pose + mesh | 3 | 0.0467 | 0.302 ± 0.005 | 0.624 ± 0.004 | 26.0 | 5.5 ± 0.0 | 1.10 ± 0.01 |
| Local grid search labels | 1 | 0.0471 | 0.294 | 0.684 | 26.0 | 4.0 | 0.96 |
| ICP labels | 3 | 0.0610 | 0.309 ± 0.011 | 0.469 ± 0.101 | 27.4 | 4.0 ± 0.0 | 1.00 ± 0.01 |
| Gradient-descent labels | 3 | 0.0465 | 0.322 ± 0.004 | 0.689 ± 0.003 | 25.7 | 3.8 ± 0.0 | 0.94 ± 0.01 |
| Mean teacher w=0 (strong aug only) | 1 | 0.0460 | 0.288 | 0.669 | 26.2 | 5.9 | 1.05 |
| Mean teacher w=0.01 | 1 | 0.0486 | 0.298 | 0.680 | 26.4 | 5.8 | 1.07 |
| Mean teacher w=0.1 | 1 | 0.0474 | 0.293 | 0.687 | 25.9 | 5.6 | 1.06 |
| Mean teacher w=1 | 3 | 0.0480 | 0.287 ± 0.008 | 0.675 ± 0.019 | 27.6 | 5.8 ± 0.1 | 1.07 ± 0.02 |
| Mean teacher w=10 | 1 | 0.0790 | 0.282 | 0.350 | 29.4 | 5.8 | 1.07 |
| Mean teacher w=50 | 1 | 0.1940 | 0.298 | 0.224 | 30.2 | 5.7 | 1.09 |
| AlignTac (paper run) | 1 | 0.0383 | 0.233 | 0.737 | 23.1 | 3.2 | 0.88 |
| AlignTac + session-2 old-calibration labels | 1 | 0.0370 | 0.241 | 0.732 | 23.2 | 3.1 | 0.88 |

Notes: Labeled only / self-training = the paper's T run + `rss2_T_k25_{realonly,semipm}_seed{1,2}`. The grid-search student (0.294 / 0.684) is the best optimization-based student on contact MAE but still 0.06 mm behind AlignTac. ICP labels are unstable across seeds (IoU 0.38–0.58):
the ICP label set has the worst label IoU of the three optimizers (0.608) and its students lose most of the contact-mask accuracy
although their pose error is fine. GD labels give the best optimization-based student (IoU 0.688, +0.012 over Labeled only) but
contact MAE 0.322 is *worse* than Labeled only (0.291): the fitted mesh is placed well but the depth it provides is not better than
what the student already learns from 25 labels. Only the AlignTac labels improve every metric (0.233 / 0.737).
Mean teacher: consistency weights 10 and 50 collapse the contact mask (IoU 0.35 / 0.22); w = 1 gives 0.295 / 0.684, i.e. the
Labeled only numbers (0.291 / 0.676) within seed noise; w = 0.1 / 0.01 / 0 give 0.293 / 0.687, 0.298 / 0.680 and 0.288 / 0.669,
all within the same band (validation depth MSE 0.052–0.055 for every w ≤ 1; w = 0 is the same pipeline with the strong augmentation
only, so the whole semi-supervised branch is worth nothing at K = 25). Weight chosen by validation:
**w = 1**; 3 seeds: 0.287 ± 0.008 / 0.675 ± 0.019 vs Labeled only 0.299 ± 0.009 / 0.675 ± 0.003. Conclusion for the paper: consistency regularization on the unlabeled
pool does not substitute for geometric labels at K = 25.

## P0-4 / T3 — new objects from the mesh only (LOO-3; `loo3_results.json`, `loo3_test_frames.json`)

Held-out objects: pattern_04_3_lines_angle_2, pattern_31_rod, pattern_33 (sensor A, session 1). Odd frame index = unlabeled pool
(1,118 frames, pseudo-labeled; no real label of these objects is ever used), even frame index = test (635 frames). Teacher =
`pilot150_A_bgcondloo` (trained on the 9 seen objects, all their labels, with GAN-LOO sim), aligner = `outputs/aligner_loo9`
(9 seen objects only). Students start from scratch on 9-object labels + the pseudo-labeled pool, 150 epochs, 3 seeds.

Label quality on the 1,118 pool frames (round 1):

| Label source for the 3 new objects | IoU | Contact MAE (mm) | Rot (°) |
|---|---|---|---|
| Teacher depth (self-training) | 0.575 | 0.322 | 4.9 |
| Mesh at teacher pose | 0.409 | 0.472 | 4.9 |
| Mesh at aligner pose (**AlignTac**) | 0.594 | 0.331 | 1.4 |

Students on the 635 test frames (dense at `best_depth.pt`, pose at `best_pose.pt`; mean ± std over 3 seeds):

| Student | Depth MSE | Contact MAE (mm) | IoU | Normal (°) | Rot (°) | Trans (mm) |
|---|---|---|---|---|---|---|
| Labeled only, 9 objects (lower bound; never saw the 3 objects) | | 0.363 | 0.578 | 30.9 | 53.6 | 3.91 |
| Teacher itself (`A_bgcondloo`, 9 objects + GAN-LOO sim) | | 0.327 | 0.631 | 29.4 | 4.6 | 1.55 |
| Mesh at teacher pose (self-training, teacher pose + mesh) | 0.1051 | 0.426 ± 0.005 | 0.486 ± 0.005 | 33.9 | 4.5 ± 0.1 | 1.70 ± 0.01 |
| **AlignTac** (mesh at aligner pose) | 0.0651 | 0.332 ± 0.001 | 0.622 ± 0.003 | 29.9 | 3.2 ± 0.0 | 1.56 ± 0.02 |
| Oracle (curated labels of the pool; upper bound) | 0.0353 | 0.233 ± 0.002 | 0.725 ± 0.002 | 21.8 | 3.0 ± 0.0 | 1.38 ± 0.04 |

Honest reading: on the new objects the AlignTac student confirms the claim for **pose** (rot 53.6° → 3.2°, better than the
teacher's 4.6°) and beats the self-training student by a wide margin (0.332 / 0.622 vs 0.426 / 0.486), but it does **not** improve
dense accuracy over the teacher it was distilled from (0.332 / 0.622 vs 0.327 / 0.631). The aligned labels themselves are only at
teacher-depth level on contact MAE (0.331 vs 0.322), so the student cannot exceed it; the oracle row (0.233 / 0.725) shows the
headroom is in label accuracy, not in the student. Framing for the paper: "a new object can be labeled from its mesh alone to the
accuracy of a teacher that saw it, with 3× lower rotation error"; the dense gain over the teacher that the within-object setting
shows (0.291 → 0.233) does not transfer to objects the aligner never saw. Seed variance is tiny (≤ 0.005), so the ranking is solid.

## P1-5 / F1 — pseudo-label confidence (`rss2_confidence_s1_k25.json`, `rss2_confidence_s2_k25.json`)
| Signal | ρ vs MAE (S1) | ρ vs 1−IoU (S1) | ρ vs rot (S1) | ρ vs MAE (S2) | ρ vs 1−IoU (S2) | ρ vs rot (S2) |
|---|---|---|---|---|---|---|
| c_last | 0.28 | 0.28 | 0.12 | 0.38 | 0.54 | 0.55 |
| agree_jit | -0.24 | -0.24 | -0.19 | -0.51 | -0.62 | -0.44 |
| agree_glob | -0.26 | -0.26 | -0.17 | -0.30 | -0.45 | -0.56 |
| teach_iou | -0.30 | -0.27 | -0.19 | -0.37 | -0.57 | -0.65 |
| render_err | 0.44 | 0.45 | 0.12 | 0.20 | 0.23 | 0.23 |
| conf | -0.36 | -0.34 | -0.21 | -0.44 | -0.60 | -0.62 |

`conf` = mean rank percentile of multi-start agreement (jittered starts), global-start agreement, teacher-depth agreement and
(1 − last-correction magnitude). Label quality of the kept fraction, session 1:

| Kept fraction | conf IoU / MAE | random IoU / MAE | oracle IoU / MAE |
|---|---|---|---|
| 1.0 | 0.719 / 0.235 | 0.719 / 0.235 | 0.719 / 0.235 |
| 0.9 | 0.739 / 0.220 | 0.720 / 0.234 | 0.758 / 0.200 |
| 0.75 | 0.751 / 0.210 | 0.721 / 0.233 | 0.803 / 0.166 |
| 0.5 | 0.772 / 0.193 | 0.719 / 0.235 | 0.863 / 0.122 |

Session 2 (162 frames): conf 75 % keeps IoU 0.658 / MAE 0.280 / rot 2.3° (all: 0.580 / 0.326 / 8.6°); random 75 %: 0.582 / 0.321 / 9.1°.
Students `rss2_T_k25_rf_{conf,rand,oracle}{75,50}` are queued.

**Filtering students** (testA; AlignTac labels, K = 25; kept fraction of the 3,897 pseudo-labels; 1 seed):

| Kept | by confidence | random | by true error (oracle) |
|---|---|---|---|
| 100 % | 0.233 / 0.737 / 3.2° | — | — |
| 75 % | 0.244 / 0.730 / 3.1° | 0.242 / 0.721 / 3.0° | 0.230 / 0.741 / 3.1° |
| 50 % | 0.239 / 0.731 / 3.4° | 0.251 / 0.722 / 3.3° | 0.237 / 0.735 / 3.9° |

(contact MAE / IoU / rot). Keeping the 50 % most confident labels costs almost nothing (0.239 vs 0.233); the oracle-75 % row shows the
ceiling of filtering is small too (0.230), i.e. the aligned labels are already good enough that dropping the worst quarter barely matters
on session 1. At 50 % kept, confidence (0.239 / 0.731) beats random (0.251 / 0.722) and is within 0.002 of the oracle (0.237 / 0.735); at 75 % the
three are within 0.014 (conf 0.244, random 0.242, oracle 0.230). So the score does pick the useful half, but every point of the curve
lies within 0.02 mm of using all labels (0.233): on session 1 the filtering curve is flat and F1 is a robustness statement, not a headline; its value is on session 2 (ρ 0.44–0.62, two-line patterns) where no student
has been trained yet.

## P2-8 / T5 — session-level consensus (`rss2_s2_consensus_k25.json`, `_k100.json`)
Reference per run = median of (curated label − recorded pose) over the run's curated frames (38 runs). Recorded-pose drift by that
reference: mean 3.4° / 3.0 mm, median 1.4° / 1.4 mm per run. Run consensus from the aligner started at the recorded pose:
rotation median 1.12° (mean 2.85°), translation median 1.61 mm (mean 2.36 mm);
21 % of runs within 2° / 1 mm. More presses barely help (20 presses: 1.1° / 1.4 mm).
**Gate (median < 2° and < 0.5 mm) not met**: the per-run offset is not rigid enough — curated-minus-recorded varies by ~0.8 mm (sd)
within a run. Consensus → aligner gives +0.02 IoU at K = 100 (0.646 vs 0.628) and nothing at K = 25. Recommendation: report as an
analysis, do not adopt as a method component.

## P1-6 / F2 — unlabeled-data quantity (`rss2_T_k25_{rf,semipm}_u{25,50}`, 1 seed, testA)

| Unlabeled pool used | AlignTac: cMAE / IoU / rot | Self-training: cMAE / IoU / rot |
|---|---|---|
| 0 % (Labeled only) | 0.300 / 0.677 / 5.8° | 0.300 / 0.677 / 5.8° |
| 25 % (974 frames) | 0.247 / 0.720 / 3.8° | 0.308 / 0.646 / 6.5° |
| 50 % (1,949 frames) | 0.244 / 0.726 / 3.5° | 0.294 / 0.624 / 7.0° |
| 100 % (3,897 frames) | 0.233 / 0.737 / 3.2° | 0.301 / 0.641 / 8.6° |

AlignTac improves monotonically with more unlabeled frames and already gets most of the gain from a quarter of the pool; self-training
stays flat at the Labeled only level on contact MAE and loses IoU and rotation as more teacher labels are added.

## P1-7 / T4 — single-touch localization (`rss2_localize.json`)
One press, known mesh; rotation is symmetry-aware (modulo the mesh's rotational period), translation = mean(|dx|, |dy|). Global
search = exhaustive (3°, 0.5 mm) fit of the mesh to the student's predicted depth within ±7 mm of the sensor centre (local
localization, not whole-object). Session 1 = 530 held-out frames, session 2 = 464 curated frames of the held-out half.

| Student | Method | S1 rot mean / median (°) | S1 trans (mm) | S1 succ 2°/0.5 mm | S1 succ 5°/1 mm | S2 rot mean / median (°) | S2 trans (mm) | S2 succ 2°/0.5 mm | S2 succ 5°/1 mm |
|---|---|---|---|---|---|---|---|---|---|
| Labeled only K=25 | pose head | 5.67 / 3.52 | 1.09 | 16 % | 45 % | 14.84 / 12.06 | 1.78 | 2 % | 12 % |
| Labeled only K=25 | pose head + alignment | 0.82 / 0.42 | 0.65 | 69 % | 85 % | 5.49 / 1.29 | 1.29 | 35 % | 69 % |
| Labeled only K=25 | global search on predicted depth | 4.81 / 1.70 | 0.98 | 32 % | 73 % | 6.46 / 2.87 | 1.81 | 15 % | 52 % |
| Labeled only K=25 | global search + alignment | 3.22 / 0.43 | 0.86 | 66 % | 82 % | 4.98 / 1.35 | 1.61 | 36 % | 69 % |
| AlignTac K=25 (3 seeds) | pose head | 3.09 / 1.80 | 0.87 | 33 % | 66 % | 10.28 / 6.66 | 1.51 | 7 % | 25 % |
| AlignTac K=25 (3 seeds) | pose head + alignment | 0.64 / 0.40 | 0.64 | 69 % | 87 % | 5.10 / 1.27 | 1.27 | 35 % | 69 % |
| AlignTac K=25 (3 seeds) | global search on predicted depth | 3.90 / 1.18 | 0.88 | 49 % | 81 % | 5.18 / 1.88 | 1.64 | 28 % | 59 % |
| AlignTac K=25 (3 seeds) | global search + alignment | 3.11 / 0.41 | 0.90 | 66 % | 83 % | 4.33 / 1.31 | 1.42 | 35 % | 70 % |
| Labeled only K=100 | pose head | 3.25 / 1.92 | 0.63 | 34 % | 67 % | 11.66 / 9.49 | 1.64 | 2 % | 12 % |
| Labeled only K=100 | pose head + alignment | 0.29 / 0.21 | 0.28 | 86 % | 94 % | 4.79 / 1.27 | 1.30 | 39 % | 68 % |
| Labeled only K=100 | global search on predicted depth | 4.42 / 1.52 | 0.92 | 48 % | 80 % | 12.87 / 2.83 | 1.92 | 23 % | 54 % |
| Labeled only K=100 | global search + alignment | 2.69 / 0.21 | 0.78 | 81 % | 85 % | 11.57 / 1.38 | 1.86 | 36 % | 62 % |
| AlignTac K=100 | pose head | 2.82 / 1.82 | 0.62 | 39 % | 73 % | 9.40 / 5.96 | 1.54 | 5 % | 24 % |
| AlignTac K=100 | pose head + alignment | 0.28 / 0.21 | 0.28 | 85 % | 93 % | 3.91 / 1.20 | 1.23 | 37 % | 66 % |
| AlignTac K=100 | global search on predicted depth | 4.04 / 1.22 | 0.84 | 60 % | 83 % | 5.23 / 1.94 | 1.51 | 34 % | 62 % |
| AlignTac K=100 | global search + alignment | 2.95 / 0.22 | 0.84 | 80 % | 86 % | 3.63 / 1.24 | 1.43 | 37 % | 70 % |

Takeaways: (i) the AlignTac student's own pose head localizes better than Labeled only (session 1: 3.1° vs 5.7°, success 33 % vs 16 %;
session 2: 10° vs 15°); (ii) test-time alignment is the larger lever and nearly equalizes the two students (0.6–0.8° and 69 %
success on session 1 at K=25; 0.3° and 86 % at K=100); (iii) global search on the predicted depth followed by alignment reaches
the same accuracy without any pose head (66–67 % vs 69 %), i.e. the aligner alone localizes a single touch; (iv) on session 2 all
methods plateau at ~35 % strict success (translation ~1.2–1.4 mm), consistent with the label-quality ceiling there.

## Side study — two-line patterns and the aligner's training range (`rss2_multistart_s2_k25.json`, `rss2_fit_s{1,2}_k25_range2.json`)
On session 2 the three two-line patterns (31 of the 162 curated frames) stay at IoU 0.40 with the paper's aligner (session 1: 0.60–0.68),
because the teacher's initial pose is 15–25° off after re-placement.

| Variant | all 162: IoU / MAE / rot | two-line 31: IoU / MAE |
|---|---|---|
| teacher start → aligner (paper) | 0.580 / 0.326 / 8.6° | 0.396 / 0.421 |
| global-search start → aligner | 0.601 / 0.320 / 9.2° | 0.427 / 0.449 |
| 4 starts, pick by residual correction (label-free) | 0.607 / 0.307 / 6.3° | 0.434 / 0.406 |
| 4 starts, oracle pick | 0.617 / 0.300 / 7.3° | 0.473 / 0.380 |
| aligner trained with 2× perturbation range (±16°) | 0.589 / 0.323 / 5.8° | mixed (0.44 / 0.29 / 0.44 per object) |

The 2× range aligner (same recipe otherwise) also improves session 1 (IoU 0.721 vs 0.712, MAE 0.231 vs 0.241) and holds the basin
to 30° (IoU 0.715 vs 0.668). Not adopted as the default for round 2 (all 3-seed students use the paper's aligner); proposed as a
robustness ablation. Even the oracle choice among four starts leaves the two-line patterns at 0.47, so confidence filtering remains
the mechanism that keeps them out of training; the per-object student table must show it.

## Round 2b (2026-11-10 evening) — controlled drift, unseen-object diagnosis, run-level fusion

### D1. Controlled drift on session 1 (`rss2_drift_s1.py`, `rss2_drift_s1_k25.json`; K = 25, pool frames, registered labels as reference)

One constant offset per object is added to the registered (θ, x, y) of all its pool frames (translation of length T in a random direction,
rotation ±R). This is exactly how a stale calibration acts in this setup (`robot_to_gt`: the calibration is additive in state space).
"Stale" = mesh at the drifted pose; "aligner" = K = 25 aligner started from the drifted pose (no teacher, no recalibration).

| T (mm) | stale IoU, R = 0° | R = 2° | R = 5° | R = 10° | aligner from the stale pose (R = 0°): IoU / cMAE / trans (mm) |
|---|---|---|---|---|---|
| 0 | 0.94 | 0.81 | 0.62 | 0.38 | 0.725 / 0.231 / 0.38 |
| 0.25 | 0.84 | 0.81 | 0.63 | 0.40 | 0.725 / 0.231 / 0.38 |
| 0.5 | 0.74 | 0.74 | 0.63 | 0.41 | 0.725 / 0.232 / 0.39 |
| 0.75 | 0.65 | 0.66 | 0.60 | 0.41 | 0.725 / 0.232 / 0.40 |
| 1 | 0.56 | 0.58 | 0.55 | 0.41 | 0.725 / 0.232 / 0.41 |
| 1.5 | 0.42 | 0.43 | 0.44 | 0.38 | 0.725 / 0.232 / 0.43 |
| 2 | 0.30 | 0.32 | 0.34 | 0.33 | 0.725 / 0.232 / 0.45 |
| 3 | 0.19 | 0.19 | 0.21 | 0.23 | 0.724 / 0.232 / 0.50 |
| 4 | 0.14 | 0.14 | 0.15 | 0.16 | 0.724 / 0.232 / 0.56 |

A 1 mm offset already costs 40 % of the label IoU (0.94 → 0.56) and 2 mm leaves 0.30, the level of the real session-2 stale labels (0.35 at
1.9 mm). The aligner returns to the same fixed point (0.725 / 0.232) from every start up to 4 mm, so its output is independent of the drift.
Honest crossover: below ≈ 0.5 mm of drift the stale labels are better than the aligner's (0.74 vs 0.725), because the aligner's own per-touch
accuracy is ≈ 0.4 mm. Students for T = 0.5 / 1 / 2 / 3 mm (R = 2°), stale vs aligner: `rss2_T_k25_dr{05,10,20,30}_{stale,al}` (training).

### D2. Why unseen objects look bad (`rss2_loo3_diag.py`, `rss2_loo3_diag_{unseen,seen_k25}.json`)

| Check | Unseen (aligner_loo9, 1,118 frames) | Seen (K = 25 aligner, 1,299 frames) |
|---|---|---|
| Aligner started from the teacher (pipeline): IoU / cMAE / rot / trans | 0.594 / 0.331 / 1.4° / 1.20 mm | 0.718 / 0.236 / 1.1° / 0.69 mm |
| Aligner started from the TRUE state | 0.614 / 0.317 / 0.7° / 0.55 mm | 0.725 / 0.231 / 0.6° / 0.38 mm |
| Pipeline result with the TRUE rotation swapped in | 0.594 | 0.725 |
| Pipeline result with the TRUE press swapped in | 0.605 | 0.718 |
| Pipeline result with the TRUE translation swapped in | 0.816 | 0.902 |

Per object (teacher-depth IoU → aligner IoU, translation error; std of the translation error along its minor / major axis):

| Object | Seen, K = 25 | Unseen |
|---|---|---|
| pattern_33 (non-line) | 0.539 → 0.767, 0.25 mm; 0.29 / 0.36 mm | 0.644 → 0.736, 0.23 mm; 0.19 / 0.37 mm |
| pattern_31_rod | 0.488 → 0.619, 2.04 mm; 0.62 / 4.16 mm | 0.562 → 0.569, 1.61 mm; 0.71 / 2.90 mm |
| pattern_04_3_lines_angle_2 | 0.529 → 0.686, 0.79 mm; 0.70 / 2.84 mm | 0.517 → 0.467, 1.60 mm; 0.90 / 3.64 mm |
| other non-line objects (32, 35, 36, 37) | → 0.79–0.83, 0.2 mm | — |
| other line objects (2 / 3 / 5 lines) | → 0.59–0.70, 0.4–1.5 mm | — |

Findings: (1) rotation and press are solved; the label error is translation only. (2) The translation error is strongly anisotropic on
every line / rod object, seen or unseen (3–4 mm along one axis, < 1 mm across): a single touch cannot observe the translation along an
extruded ridge (aperture problem), and periodic lines add a one-period ambiguity. (3) Even from the TRUE state the aligner moves away
(IoU 0.94 → 0.725 seen / 0.614 unseen): label accuracy is bounded by the aligner's per-touch fixed point, not by the initialization.
(4) Two of the three held-out objects are line / rod objects, the hardest class even when seen; the non-line held-out object generalizes
(0.736 vs 0.767 seen). The only real generalization failure is the three-line pattern (0.467 vs 0.686). The oracle student (0.233)
shows that neither the student nor the teacher architecture is the limit.

### D3. Run-level fusion of per-touch alignments (`rss2_run_consensus_s1.py`, `rss2_runfusion_*.json`)

A label state is the robot reading plus one constant (dθ, dx, dy, dpress) per placement, and the robot knows the relative motion between
touches. Estimating that constant as the median over all touches of a run of (aligned state − robot reading) and re-labeling every touch
with it removes the per-touch ambiguity. No label of the evaluated frames is used.

| Per-touch method | Per-touch IoU / cMAE / rot / trans | After run fusion | Placement error from 10 touches |
|---|---|---|---|
| Seen objects (3,897 pool frames, K = 25) | | | |
| Teacher pose head | 0.471 / 0.400 / 6.0° / 1.14 mm | 0.793 / 0.169 / 1.2° / 0.25 mm | 2.3° / 0.40 mm |
| Grid search on teacher depth | 0.630 / 0.298 / 3.0° / 0.91 mm | 0.854 / 0.123 / 0.8° / 0.19 mm | 1.0° / 0.26 mm |
| ICP | 0.608 / 0.340 / 3.1° / 0.99 mm | 0.851 / 0.147 / 0.7° / 0.16 mm | 1.0° / 0.29 mm |
| Gradient descent | 0.636 / 0.337 / 2.6° / 0.90 mm | 0.854 / 0.208 / 0.8° / 0.18 mm | 0.9° / 0.26 mm |
| **Aligner** | 0.719 / 0.235 / 1.1° / 0.67 mm | **0.901 / 0.082 / 0.08° / 0.10 mm** | 0.2° / 0.18 mm |
| Unseen objects (1,118 frames, aligner_loo9) | | | |
| Teacher pose head | 0.409 / 0.472 / 4.9° / 1.54 mm | 0.578 / 0.357 / 1.3° / 0.49 mm | 1.8° / 0.68 mm |
| **Aligner** | 0.594 / 0.331 / 1.4° / 1.20 mm | 0.663 / 0.284 / 0.5° / 0.37 mm | 0.5° / 0.55 mm |

Caveats: (a) session-1 registered labels were built with exactly this rigid model, so fusion is exact by construction here; on a real new
placement it holds as far as the fixture is rigid, the same assumption a manual recalibration makes. (b) Fusion helps every per-touch
method, so the aligner's margin shrinks in IoU (0.90 vs 0.85) but stays large in contact MAE (0.082 vs 0.123–0.208), rotation (0.08° vs
0.7–1.2°) and number of touches needed. (c) It uses the robot's readings of the unlabeled frames, which the current paper never uses;
it changes the premise from "pose-free per frame" to "uncalibrated robot + mesh, self-calibrated per run". (d) On unseen line / rod objects
the fused placement keeps a 0.6–1.0 mm bias: the aligner's errors are not zero-mean on shapes it never saw (aligners trained with synthetic
frames of the new meshes are being tested: `outputs/aligner_loo9_{syn3,syn3_r2,r2}`).

## Open questions
1. **Drift number.** The paper's "per-run corrections averaged 11.4° / 1.6 mm" comes from `pose_calibration_new.json` (grid search on
   contact masks), which does not agree with the curated labels. Curated − recorded is 3.4° / 3.0 mm (means), 1.4° / 1.4 mm (medians).
   Which number goes into the abstract / Fig. 1? (Suggestion: the curated-based one, phrased as "re-placement moved the contact by
   1–3 mm and a few degrees", with the conventional-label row of T2 as the consequence.)
2. **SITR checkpoint.** The original under `gsrl/` is gone; the rebuilt copy reproduces stored numbers exactly. If you still have the
   original file, drop it into `VisTacFusion/weights/`.
3. **LOO-3 run dirs.** `runs/pilot150_A_loo3_{al,tp,oracle}` held 5-epoch fragments of the interrupted 11-01 runs and were
   retrained from scratch in place (rule 1 technically violated; no results were lost).
7. **T3 framing.** On unseen objects AlignTac matches the teacher on dense metrics and only wins on pose. Present as "mesh-only
   labeling of new objects reaches teacher accuracy" (defensible) rather than as an improvement; or invest in an aligner
   that generalizes better across objects (more seen objects / synthetic frames of the new mesh) before the RSS deadline?
4. **P2-8**: stop here (recommended) or try a per-press offset model?
5. Two-line patterns stay at IoU ≈ 0.4 for every method on session 2; confidence filtering will mostly drop them.
6. **Mean teacher** gives nothing over Labeled only at K = 25 (T1). Keep it in T1 as the semi-supervised baseline (3 seeds at w = 1)
   or drop it from the paper and mention it in the text only?
8. **Session-2 reference labels are fitted, not calibrated.** They come from a per-frame mask-IoU refinement against the predicted depth of an
   earlier model, then visual review (details in PAPER_NOTES 2026-11-10). Two independent refinements of the same 28 frames differ by a median
   of 3.1° / 0.84 mm, so session-2 pose errors below about 2–3° / 1 mm are inside the reference noise. Options: (a) state this in the paper and
   report session 2 mainly with dense metrics; (b) hand-annotate ridge keypoints on ~100 session-2 frames as an independent reference;
   (c) run the drift study as a controlled experiment on session 1, whose labels are calibration-based.
9. **Method premise.** Run-level fusion (D3) lifts label IoU from 0.72 to 0.90 on session 1 and explains the unseen-object and session-2
   weaknesses, but it uses the robot readings of the unlabeled frames. Adopt it as the core of the RSS version ("self-calibrating labeling
   from an uncalibrated robot and a mesh") or keep the pose-free per-frame method and report fusion as an extension?

