# AlignTac — RSS 2027 round 2 results

Working document for the Stage-1 extended abstract (due 2026-12-04 AoE). Every number below comes from a JSON under
`ablation/pilot_robosoft/` (file named per section); run names, configs and logs (`outputs/rss_logs/`) are listed per task.
Branch `rss-round2` (not pushed). Last update: 2026-11-13 (D8: the robot pose -> label conversion does not rotate the translation with the tool yaw; D9: corrected label roots for both sessions built and verified; no table re-run yet).

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
| AlignTac (paper run + 2 seeds) | 3 | 0.0376 | 0.235 ± 0.003 | 0.736 ± 0.001 | 23.2 | 3.2 ± 0.0 | 0.87 ± 0.01 |
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
accuracy is ≈ 0.4 mm.

**Students under controlled drift** (`rss2_T_k25_dr{05,10,20,30}_{stale,al}`, 3 seeds each, R = 2°; testA, 530 frames; dense at
`best_depth.pt`, pose at `best_pose.pt`; `rss2_testA_results.json`; finished 2026-11-12). The 25 labels are untouched; only the labels of
the 3,897 pool frames differ.

| Drift T (mm) | Pool labels | Depth MSE | Contact MAE (mm) | IoU | Normal (°) | Rot (°) | Trans (mm) |
|---|---|---|---|---|---|---|---|
| 0.5 | mesh at the stale pose | 0.0347 | 0.228 ± 0.004 | 0.730 ± 0.007 | 23.4 | 3.3 ± 0.1 | 0.69 ± 0.01 |
| 0.5 | aligner from the stale pose | 0.0378 | 0.231 ± 0.003 | 0.742 ± 0.002 | 23.1 | 2.9 ± 0.1 | 0.68 ± 0.01 |
| 1 | mesh at the stale pose | 0.0564 | 0.330 ± 0.018 | 0.548 ± 0.044 | 29.1 | 3.3 ± 0.0 | 0.90 ± 0.01 |
| 1 | aligner from the stale pose | 0.0378 | 0.231 ± 0.003 | 0.741 ± 0.003 | 23.1 | 2.9 ± 0.0 | 0.69 ± 0.01 |
| 2 | mesh at the stale pose | 0.0866 | 0.439 ± 0.016 | 0.426 ± 0.019 | 31.9 | 3.4 ± 0.1 | 1.44 ± 0.01 |
| 2 | aligner from the stale pose | 0.0383 | 0.232 ± 0.003 | 0.740 ± 0.003 | 23.3 | 2.9 ± 0.0 | 0.72 ± 0.00 |
| 3 | mesh at the stale pose | 0.1063 | 0.494 ± 0.010 | 0.353 ± 0.017 | 32.4 | 3.4 ± 0.0 | 2.04 ± 0.00 |
| 3 | aligner from the stale pose | 0.0380 | 0.231 ± 0.001 | 0.741 ± 0.001 | 23.2 | 2.9 ± 0.1 | 0.75 ± 0.01 |

References on the same test set: Labeled only 0.299 / 0.675 / 5.9° / 1.09 mm; AlignTac from the teacher 0.235 / 0.736 / 3.2° / 0.87 mm.
Reading: (1) the aligner students are flat in every dense metric from 0.5 to 3 mm (0.231–0.232 / 0.740–0.742); only their translation error
creeps up (0.68 → 0.75 mm), following the label translation error (0.39 → 0.50 mm). (2) The stale students degrade monotonically, and from
1 mm on they are worse than Labeled only (0.330 / 0.548 vs 0.299 / 0.675): drifted labels are worse than no pseudo-labels. Their translation
error grows with the offset (2.04 mm at 3 mm: the student learns the drift), their rotation does not (R is only 2°). (3) Honest crossover,
as predicted by the label table: at 0.5 mm the two students are equal within seed noise on contact MAE (0.228 vs 0.231) and differ by 0.012
in IoU. The claim is "independent of drift", not "better at any drift". (4) Starting the aligner from a recorded pose gives slightly better
pose accuracy than starting from the teacher (2.9° / 0.68 mm vs 3.2° / 0.87 mm), as on session 2 (T2).

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

### D4. New objects: observability-aware fusion and mesh-only aligner onboarding (`rss2_obs_fusion.py`, `rss2_obsfusion_loo3_*.json`, 2026-11-11)

Two changes, neither uses a real label of the new objects:
1. **Onboarding from the mesh.** The aligner is trained on the 9 seen objects plus synthetic-only frames of the 3 new meshes (learned
   renderer; pose ranges taken from the teacher's predictions on the unlabeled frames; `train_aligner.py --synth-ranges`), 2× perturbation range.
2. **Observability-aware fusion.** For every touch the mesh gives the information matrix W = JᵀJ, J = ∂(mesh depth)/∂(θ, x, y) at the aligned
   state (a structure tensor: rank-deficient along an extruded ridge). The placement constant is estimated per run with rotation by the
   median and translation in information form, c = (Σ sᵢWᵢ)⁻¹ Σ sᵢWᵢeᵢ (Cauchy weights sᵢ), so each touch contributes only what it can see.

Label quality on the 1,118 pool frames of the three held-out objects (IoU / contact MAE / rot / trans):

| Aligner | Per touch | + median fusion | + observability-aware fusion |
|---|---|---|---|
| Teacher depth (self-training label) | 0.575 / 0.322 / 4.9° / 1.54 mm | | |
| 9 seen objects (round 1) | 0.594 / 0.331 / 1.4° / 1.20 mm | 0.663 / 0.284 / 0.5° / 0.37 mm | 0.735 / 0.207 / 0.5° / 0.27 mm |
| + 2× range only | 0.574 / 0.354 / 0.8° / 1.19 mm | 0.622 / 0.326 | 0.678 / 0.268 |
| + synthetic frames of the new meshes | 0.612 / 0.318 / 1.3° / 1.13 mm | 0.686 / 0.263 | 0.757 / 0.187 |
| + synthetic frames of the new meshes, 2× range | 0.624 / 0.312 / 0.8° / 0.99 mm | 0.718 / 0.232 | **0.769 / 0.177 / 0.6° / 0.22 mm** |

For reference, per-touch labels of SEEN objects at K = 25 are 0.719 / 0.235. Observability as a label-free confidence: Spearman between the
weakest translation eigenvalue ratio and the true per-touch translation error is 0.60–0.69 on unseen objects (quartile means 2.4–3.0 mm →
0.6 mm) and 0.27 on seen objects (worst quartile 2.2 mm vs 0.6–0.8 mm). On seen objects information weighting equals the median
(0.896 vs 0.901): per-touch errors are zero-mean there; the weighting matters when the aligner is biased along unobservable directions.
With 10 touches the placement translation error on unseen objects is 0.43 mm (median fusion 0.51 mm); 20 touches 0.33 mm (0.46 mm).

**Students** (9 seen objects with labels + pool frames of the 3 new objects with these labels, 150 epochs; 635 test frames of the new
objects; dense at `best_depth.pt`, pose at `best_pose.pt`; `loo3_results.json`; finished 2026-11-12):

| Labels for the 3 new objects | n | Depth MSE | Contact MAE (mm) | IoU | Normal (°) | Rot (°) | Trans (mm) |
|---|---|---|---|---|---|---|---|
| Teacher itself (reference, from T3) | 1 | 0.0588 | 0.327 | 0.631 | 29.4 | 4.6 | 1.55 |
| AlignTac per touch, 9-object aligner (T3) | 3 | 0.0651 | 0.332 ± 0.001 | 0.622 ± 0.003 | 29.9 | 3.2 ± 0.0 | 1.56 ± 0.02 |
| + mesh-only onboarding, per touch (`loo3_syn`) | 3 | 0.0588 | 0.315 ± 0.000 | 0.644 ± 0.001 | 28.8 | 3.1 ± 0.1 | 1.50 ± 0.02 |
| 9-object aligner + observability-aware fusion (`loo3_obsf9`) | 1 | 0.0488 | 0.285 | 0.672 | 26.6 | 3.0 | 1.42 |
| + mesh-only onboarding + observability-aware fusion (`loo3_obsf`) | 3 | 0.0472 | 0.276 ± 0.003 | 0.688 ± 0.001 | 25.3 | 3.0 ± 0.1 | 1.39 ± 0.03 |
| Oracle (curated labels of the pool; T3) | 3 | 0.0353 | 0.233 ± 0.002 | 0.725 ± 0.002 | 21.8 | 3.0 ± 0.0 | 1.38 ± 0.04 |

Reading: (1) the label gains carry over to the students in the same order. (2) With onboarding alone the method keeps its pose-free,
per-frame premise and now beats the teacher on dense accuracy (0.315 / 0.644 vs 0.327 / 0.631); the margin is small but the seed spread
is < 0.001, and in round 1 this comparison was a tie-to-loss (0.332 / 0.622). (3) Fusion adds most of the gain: the full student closes
54 % of the teacher → oracle gap in contact MAE (0.327 → 0.276, oracle 0.233) and 61 % in IoU, and reaches the oracle's pose accuracy
(3.0° / 1.39 mm vs 3.0° / 1.38 mm). (4) Caveat unchanged from D3 / D6: fusion assumes a rigid placement and uses the robot readings; the
session-1 reference is rigid by construction, and fusion has not been shown to help after a real re-placement. (5) Student accuracy lags
label accuracy (labels 0.769 / 0.177 → student 0.688 / 0.276; oracle labels → 0.725 / 0.233): about half of the remaining gap to the
oracle is label error, the rest is what a student reaches on these three objects with ~370 pseudo-labeled frames each.
Extra seeds of the fusion-only row (`rss2_A_loo3_obsf9_seed{1,2}`) started 2026-11-12.

**Per object** (`rss2_eval_per_object.py`, `rss2_loo3_per_object.json`; same checkpoints, the "all" rows reproduce the table above; contact
MAE / IoU at `best_depth.pt`; rot mean / trans / trans along the two pose axes |dx|, |dy| in mm at `best_pose.pt`; 3 seeds unless marked):

| Student | pattern_33 (non-line, 179 frames) | pattern_31_rod (302) | pattern_04_3_lines_angle_2 (154) |
|---|---|---|---|
| Labeled only, 9 objects (1 seed) | 0.182 / 0.781; 58.7°, 3.17 (3.1, 3.2) | 0.424 / 0.513; 16.6°, 4.73 (8.1, 1.4) | 0.469 / 0.469; 157°, 4.05 (3.7, 4.4) |
| Teacher (1 seed) | 0.179 / 0.795; 4.3°, 0.92 (0.8, 1.1) | 0.366 / 0.588; 3.8°, 1.47 (2.1, 0.9) | 0.429 / 0.525; 6.7°, 2.44 (3.9, 1.0) |
| Mesh at teacher pose | 0.383 / 0.530; 4.2°, 0.99 | 0.412 / 0.511; 3.4°, 1.59 | 0.492 / 0.386; 7.0°, 2.76 |
| AlignTac per touch | 0.201 / 0.787; 2.7°, 0.59 (0.6, 0.6) | 0.353 / 0.590; 1.8°, 1.59 (2.3, 0.9) | 0.445 / 0.495; 6.5°, 2.67 (4.0, 1.3) |
| + mesh-only onboarding | 0.185 / 0.800; 2.6°, 0.58 | 0.332 / 0.612; 1.9°, 1.50 (2.2, 0.8) | 0.430 / 0.527; 5.9°, 2.57 (3.9, 1.3) |
| Fusion only (1 seed) | 0.169 / 0.830; 2.7°, 0.62 | 0.358 / 0.583; 1.9°, 1.40 | 0.306 / 0.661; 5.7°, 2.37 |
| + onboarding + fusion | 0.136 / 0.872; 2.5°, 0.56 (0.6, 0.6) | 0.353 / 0.593; 1.8°, 1.34 (2.1, 0.6) | 0.318 / 0.660; 5.9°, 2.44 (3.7, 1.2) |
| Oracle | 0.102 / 0.882; 2.6°, 0.55 (0.6, 0.5) | 0.349 / 0.614; 1.7°, 1.34 (2.1, 0.6) | 0.211 / 0.760; 6.0°, 2.45 (3.8, 1.1) |

Seen-object reference (K = 25 AlignTac student on testA, `rss2_testA_per_object.json`, 3 seeds): pattern_33 0.197 / 0.789, 1.9°, 0.27 mm;
rod 0.302 / 0.660, 1.5°, 2.06 mm (3.3, 0.8); 3-lines angle 2 0.237 / 0.749, 2.9°, 1.00 mm (1.5, 0.6); non-line objects 32 / 35 / 36:
0.15–0.20 / 0.78–0.84, 0.3 mm; other line objects 0.20–0.33 / 0.61–0.72, 0.4–1.5 mm.

Reading (corrects the summary above): (1) **Pose is solved on every object.** Every pseudo-labeled student equals the oracle per object
(e.g. full: 2.5° / 0.56, 1.8° / 1.34, 5.9° / 2.44 mm vs oracle 2.6° / 0.55, 1.7° / 1.34, 6.0° / 2.45 mm). The remaining translation error of
the rod and the 3-line pattern sits on one pose axis (2.1–3.8 mm vs 0.6–1.1 mm), for the oracle too, and for the rod also when it is a seen
object: it is the single-touch ambiguity along the ridge, not label error. (2) **Dense accuracy differs by object.** Rod: the oracle itself
reaches only 0.349 / 0.614, all AlignTac variants are at that ceiling (0.332–0.358). Non-line object: per-touch labels only match the teacher
(0.185 / 0.800 vs 0.179 / 0.795; even the student that never saw the object gets 0.182 / 0.781 on dense, its failure is pose); fusion brings it
to 0.136 / 0.872, IoU within 0.01 of the oracle. 3-line pattern: per-touch labels equal the teacher (0.430 / 0.527 vs 0.429 / 0.525); fusion
closes half of the gap to the oracle (0.318 / 0.660 vs 0.211 / 0.760); this object is the real generalization gap. (3) Therefore the
aggregate "onboarding alone beats the teacher" (0.315 vs 0.327) comes from the rod only; without fusion the dense value of the labels is
"teacher level", and the dense gains on new objects come from fusion (with its rigidity caveat). (4) With one object per shape class the
split cannot support class-level statements: a second fold (pattern_01_2_lines_angle_1_2, pattern_32, pattern_35) is running, see below.
Note on protocol (both folds): the placement constant of the fusion is estimated from all train-split frames of a held-out object (1,118 in
fold 1), which include test-half images but never a label; 10–20 touches already suffice (D4 label table).

### D7. Second held-out fold (started 2026-11-13; `rss2_make_fold.py`, `rss2_fold.sh`, results in `f2_results.json`, tag `f2test`)

Held out: pattern_01_2_lines_angle_1_2 (2 lines), pattern_32, pattern_35 (non-line): 1,373 frames, odd index = pool (681), even = test (692).
Selection rule, fixed before any result: two non-line objects and one line object so that the two folds together hold 3 line / rod and 3
non-line objects; within a class the object with the most frames not in fold 1; the line object from a pattern family not held out in fold 1.
Identical pipeline with everything re-trained without the three objects: renderers `outputs/tactile_gan{,_bgcond}_loo_f2`, sim renderings
`samples_bc_loo_f2`, teacher `rss2_A_f2_teacher`, aligners `outputs/aligner_f2_{loo9,syn3_r2}`, label roots `real_pseudo_f2_*`, students
`rss2_A_f2_{tp,al,syn,obsf9,obsf,oracle}` (3 seeds for al / syn / obsf / oracle) and the lower bound `rss2_A_f2_realonly`. Results pending.

### D8. Robot pose -> label conversion: the translation is not rotated with the tool yaw (2026-11-13; `rss2_recapture/`)

Found while testing the analysis script for the planned re-capture (`rss2_recapture/rss2_recapture_check.py`: ridge maps of two
presses are registered image to image, no mesh and no network, and compared with the motion the robot reports).
**Not yet acted on: no label, root or result was changed.** Scripts and pair data: `rss2_recapture/kinematics_check/`.

Label model everywhere (`scripts/build_real_filtered_new.py: robot_to_gt`, and the session-1 pose files): an object point m appears at
`w = R(theta) m + c` with `theta = yaw + object offset` and `c = swap(ee_xy - C) + object offset`, i.e. the end-effector displacement
is used as the image-plane translation **without rotating it by the tool yaw**. Tested alternative: `c = R(yaw) (swap(ee_xy - C) + k)`.

| Check (non-line objects 32, 33, 35, 36) | Current conversion | Translation rotated with the yaw |
|---|---|---|
| Session 2, press pairs inside a run (125 pairs, 15 runs; commanded shift 3.1 mm median, yaw -20 .. -50 deg): unexplained image shift, median / p90 | 1.84 / 3.34 mm (1.81 with a free offset per object) | **0.19 / 0.39 mm with no free parameter**; fitted 2x2 matrix is a reflection with singular values 1.00 / 1.00, lever arm 0.2 mm |
| Session 1 (`real_filtered`), 480 frame pairs, label-implied motion vs image | 1.07 / 2.19 mm (0.57 mm for pairs < 5 deg apart, 1.4 mm for > 30 deg) | 0.24 / 0.56 mm |
| Session 1, ridge-mask IoU of the mesh on held-out frames, best constant per object | 0.368 / 0.371 / 0.405 / 0.334 | 0.411 / 0.475 / 0.473 / 0.403 |
| Session 2 (`real_filtered_new`), same | 0.219 / 0.176 / 0.253 / 0.211 | 0.257 / 0.246 / 0.327 / 0.310 |

Session-1 quality filter (`gs_blender/filter_real_data.py`, IoU >= 0.30 against the image) versus the error the alternative predicts
for each frame, `|(R(yaw) - I) c|`, computed from the pose file alone (patterns 35, 33, 32; `real_data` vs `real_filtered`):

| Predicted error | Frames | Kept by the filter |
|---|---|---|
| < 0.5 mm | 337 | 100 % |
| 0.5 - 1 mm | 285 | 93 - 100 % |
| 1 - 2 mm | 333 | 60 - 80 % |
| 2 - 4 mm | 228 | 3 - 20 % |
| > 4 mm | 17 | 0 % |

Kept frames: predicted error median 0.57 - 0.70 mm, p90 1.35 - 1.66 mm; deleted frames: median 2.3 - 2.4 mm.

Reading. (1) The imprint is rigid: with the right kinematics two presses of a run agree to about 0.2 mm, so the press-to-press scatter
of about 1 mm in D6 was the conversion, not the gel. (2) The registered session-1 labels (training and test labels of every table)
carry a deterministic translation error of about 0.6 - 0.7 mm (median) that the filter bounded by deleting the worst third of the frames.
(3) In session 2 the yaw is 20 - 50 deg away from the session-1 centre, so the same conversion is off by about 1.8 mm: a large part of
what T2 and the paper call re-placement drift is this conversion, not the re-installation. The true re-installation offset is the
constant k (plus a rotation constant) per object and session and has to be re-measured after the correction.
Not checked yet: line / rod objects (image registration is ambiguous along the lines), the rotation labels (pairwise rotation
residual 1.0 - 1.5 deg, may be registration noise), a rotation constant and lever arm per session.
**Source confirmed (2026-11-13, later).** The session-1 conversion is `/media/hdd2/xiangdong/gelslim_depth/scripts/data_scripts/render_gt_blender_ortho.py`
(lines 228-237: `theta = -2 atan2(qx, qy) + theta_offset`, `mesh_x = dy + bias_x`, `mesh_y = dx + bias_y`, `sample_x = mesh_x`, `sample_y = -mesh_y`;
no rotation of the translation). Re-computing it from the raw capture in that folder reproduces all 4,669 stored labels of `real_filtered` exactly
(difference 0 in theta, x, y; images identical on 194 / 194 checked frames; same object centre and the same per-object constants as `OBJ_MAP`).
On the raw data, all pressed samples including those the filter deleted (600 pairs, 4 objects, yaw -44 .. 44 deg): old formula 2.13 mm median
unexplained shift, new formula 0.30 mm with no free parameter, flat over the yaw (`kinematics_check/s1_raw_check.py`). The raw folder holds
696 - 1,017 pressed samples per object (4,669 survive in `real_filtered`), so the deleted frames can be recovered from it.
Pose-head targets: for real data the loader uses `(sx, sy) / half` unrotated (`dataset.py: _load_pose`), i.e. the same un-rotated value as the
depth maps: pose targets and depth maps are consistent with each other and displaced together. (An earlier line here said the loader rotates
them; that is the sim branch only.) The teammate's notes (`data/calibration_experiments_summary.md`) record an unexplained offset between the
GT depth and the tactile image whose preferred sign differed from object to object.

### D9. Corrected labels for both sessions: built and verified (2026-11-13; `rss2_recapture/rss2_relabel.py`, `fits_s{1,2}.json`, `relabel_check.json`)

Model: `theta = yaw + object offset + dtheta`, `c = R(yaw + eps) (c_L + k) - lever`. Sensor constants per session from the mesh-free
press pairs of D8 (session 1: eps 1.71 +- 0.17 deg, lever (-0.27, -0.15) mm; session 2: eps 1.81 +- 0.20 deg, lever (-0.19, 0.20) mm; image
scale 0.997 / 1.001 of the nominal 17.502 mm). Object constants `dtheta, k` (3 numbers per object and session, **nothing per frame**) fitted
to the image ridges (normalized correlation, NCC, of the black-hat ridge map and the mesh map). No trained model is involved anywhere.
Rasterization: exact z-buffer (reproduces the stored session-1 depth maps at IoU 0.99; per-face minimum only 0.87).

New roots (nothing overwritten; same frames, indices and images as the roots they mirror; `label_v1` in every pose file keeps the old values):

| Root | Mirrors | Frames |
|---|---|---|
| `gs_blender/real_filtered_kin` | `real_filtered` (session 1, 12 objects) | 4,669 |
| `gs_blender/real_filtered_kin_testA` | `real_filtered_testA` (`rss2_mirror_kin.py`) | 530 |
| `gs_blender/real_s2_kin_curated854` | `real_filtered_new_curated_pred_r2_fv` (session 2, 11 objects) | 854 |

Verification (held-out = constants fitted on the other half of the presses; overlays in `rss2_recapture/figs/overlay_s{1,2}.jpg`):

| | Session 1 (12 objects) | Session 2 (11 objects) |
|---|---|---|
| Held-out NCC, corrected labels (mean; range) | **0.779** (0.62 - 0.88) | **0.776** (0.63 - 0.86) |
| Held-out NCC, stored labels | 0.598 (0.50 - 0.71) registered | 0.574 (0.44 - 0.69) curated per-frame fits; 0.316 recorded pose |
| Objects where corrected > stored | 12 / 12 (line and rod objects included) | 11 / 11 |
| Split-half stability of the constants (median) | 0.11 deg, 0.05 mm | 0.53 deg, 0.15 mm |
| Corrected - stored label, per-object median (range) | 0.84 mm (0.67 - 1.50), p90 1.5 - 2.7 mm | 1.17 mm (0.59 - 2.40; rod 6.9 mm along the rod) |
| Rotation constant dtheta | +2.2 .. +3.4 deg on every object | +1.9 .. +4.5 deg (pattern_06_5: +21.0) |

On the 530 test frames the stored and corrected depth masks overlap with IoU 0.617 and the pose targets differ by 0.74 / 0.65 mm (x / y).
The stored label is a deterministic function of the true pose, so a network can learn it: the existing students (IoU 0.736 against the stored
test labels) have learnt the displaced convention, and the curated session-2 labels, which were fitted to the predicted depth of such a
model, inherit it. Scoring existing students against the corrected labels is therefore not a validation (`eval_existing_students_*.json`,
for reference only).

**What the re-installation between the sessions really changed** (session-2 frames labelled with the session-1 constants and the correct
kinematics; assumes the stored session-1 labels used the object constants of `OBJ_MAP`):

| Quantity | Value |
|---|---|
| Plate position, session 2 - session 1, per object | 0.15 - 0.87 mm, median 0.37 mm; mean over objects (-0.11, +0.07) +- (0.38, 0.18) mm: no common shift |
| Plate rotation | median 0.31 deg, at most 1.2 deg; **pattern_06_5: +18.0 deg** (mounted differently) |
| Sensor: lever arm / yaw offset | (-0.27, -0.15) -> (-0.19, 0.20) mm (0.36 mm); 1.71 -> 1.81 deg |
| Label error of the stale (session-1) constants on session 2 | median 0.38 mm (per object 0.12 - 1.08 mm) |
| NCC with the image: fresh constants / stale constants / curated per-frame / recorded pose with the old conversion | 0.63 - 0.86 / 0.59 - 0.85 (pattern_06_5: 0.30) / 0.44 - 0.69 / 0.08 - 0.62 |

Consequences. (1) Session 2 now has a calibration-based reference that agrees with the images better than the per-frame fits; pose errors
can be reported to a few tenths of a millimetre (split-half 0.15 mm). The re-capture is not needed for this. (2) The drift the paper
motivates with (1.4 - 3 mm; "11.4 deg / 1.6 mm") was mostly the conversion. The real re-installation moved the contact by about 0.4 mm and
under 1.2 deg, which is at the crossover of the controlled-drift study (D1: stale labels equal AlignTac at 0.5 mm), with one exception:
one of 11 plates came back 18 deg rotated and its stale labels are useless. (3) Every table was trained and scored on the displaced
labels; sim data has correctly aligned labels, so real and sim supervision disagreed. All numbers have to be re-run on the corrected
roots before any claim is kept (open question 11c).
Not done: frames the session-1 filter deleted (the unfiltered source `real_data` covers 10 objects and is not a superset of
`real_filtered`); the full session-2 pool (all contact frames) as a corrected root; corrected versions of the derived training roots.

### D10. All captured presses with the corrected labels (2026-11-13; `rss2_recapture/rss2_relabel_full.py`, `full_scan.json`)

Sources: session 1 raw capture `/media/hdd2/xiangdong/gelslim_depth/data` (every pressed sample), session 2 `new_real_test` (every contact frame,
stride 3 inside a press). A frame is usable when the image shows a ridge (ridge pixels >= 2 %), the corrected label has contact (>= 1 %) and the
two agree (NCC >= 0.45); the NCC of each frame is stored in its pose file (`label_ncc`) so stricter subsets can be drawn.

| | Captured | In the old roots | Usable with the corrected labels | Newly usable |
|---|---|---|---|---|
| Session 1 (12 objects) | 9,738 | 4,669 | 9,605 (98.6 %) | 4,964 |
| Session 2 (12 objects, 48 runs) | 2,167 | 854 (curated) | 1,813 | 967 |

Session 1: 133 presses rejected (NCC), 28 of them inside the old root. Session 2: 354 rejected, all by NCC; the sampled ones are presses where
the gel shows no ridge although the robot was below the contact height (background frames). pattern_04_3_lines_angle_2 was missing from the
curated session-2 set. Its first fit (dtheta -30.4 deg, NCC 0.63) was a symmetric wrong optimum, caught by the user on the contact sheet
(one branch of the label had no ridge in the image); a search over the full rotation (`rss2_refit_rotation.py`) gives dtheta -177.0 deg,
k (1.81, -0.45) mm, held-out NCC 0.84, in line with the other plates (105 usable frames; the wrong labels are kept aside in
`gs_blender/real_s2_kin_all__wrong_rotation_pattern_04_3_lines_angle_2`). Random recovered frames of every object were checked by the
user on `figs/recovered_s{1,2}.jpg` (2026-11-13): all other objects correct.
Roots: `gs_blender/real_filtered_kin_plus` (session_000 = link to `real_filtered_kin`, same indices, so existing splits and label subsets stay
valid; session_001 = the 4,964 recovered presses) and `gs_blender/real_s2_kin_all` (one session per run, 1,813 frames, `in_curated854` flag;
`kin_manifest.json` in both). The loader reads 9,503 and 1,813 frames (130 session-1 frames are skipped by the loader, cause not looked at).

### D5. Session-2 reference labels: what others do and what we can do

| Work | How the real reference pose is obtained |
|---|---|
| Tac2Pose (Bauza et al., IJRR 2023) | objects mounted at known poses; overhead camera, then refined until the simulated contact shape matches the observed one (same kind of image-based refinement as ours) |
| MidasTouch / YCB-Slide (Suresh et al., CoRL 2022) | OptiTrack markers on sensor and object, trajectories post-processed onto the mesh surface |
| YOTO (2026) | motion capture instead of arm forward kinematics |
| 3D Cal (2025) | a 3D printer as an automated prober: machine kinematics give the label |
| T-LESS / BOP | state the accuracy of the reference poses; BOP re-annotated its datasets; rule: reference error must be well below the method error |
| BOP-Distrib (Meden et al., WACV 2026) | per-image pose *distributions* under visual ambiguity; re-evaluation changes the ranking of methods |

Options for session 2: (a) replace the per-frame fits by one rigid correction per run estimated from all frames (no per-frame fitting, no manual
selection) and report its uncertainty by split-half agreement; (b) report session 2 with ambiguity-invariant quantities (dense depth metrics,
pose error only along observable directions), as BOP-Distrib argues; (c) state the reference accuracy in the paper (two refinements differ by
3.1° / 0.84 mm; within-run scatter 0.8 mm); (d) for the full paper, a short re-capture with a fiducial object in the same placement
(independent of the image evidence) or motion capture.

### D6. Session-2 reference: can it be made objective? and fusion on the real second session (2026-11-11)

**Rigid re-fit tested and rejected** (`rss2_s2_rigid_gt.py`, `rss2_s2_rigid_gt.json`, `rss2_s2_reference_precision.json`; 854 curated frames, 42 runs).
One correction per run (reference = recorded pose + run constant, leave-one-press-out) does not reproduce the curated labels:

| Check | Result |
|---|---|
| Re-rendering the stored reference from its pose | exact (1e-7 mm) |
| Residual of (curated − recorded) about a run constant | median 0.63 mm; adding one sensor-frame offset shared by all runs: 0.55 mm (no TCP-offset explanation) |
| Same press, different depths (repeatability of the per-frame fit) | 0.37 mm std |
| Press-to-press within a run | 1.02 mm std of press means; linear drift over a run 1.1 mm end to end |
| Split-half agreement of the run correction (32 runs) | median 0.94° / 1.09 mm, p90 3.4° / 2.8 mm |
| Agreement with the image (black-hat ridge mask IoU, 853 frames) | per-frame curated 0.307, rigid per run 0.240, recorded pose 0.171 |
| Curated vs rigid reference | depth-mask IoU 0.564; 0.75° / 0.99 mm (medians) |
| Deviation vs fit quality | Spearman −0.39 with the refined IoU; by object 0.07–0.12 mm (patterns 35, 37) up to 1.1–1.3 mm (2-lines 1_2, rod) |

So a rigid per-run reference would be *worse* by the only image evidence available, and it cannot be told from this data whether the
press-to-press deviations (≈ 1 mm) are imprint shifts on the gel or errors of the per-frame fits. Handling adopted: keep the curated labels
as the session-2 reference for **dense** metrics (the review checked contour overlays, i.e. exactly the directions the depth maps are
sensitive to; sliding along a ridge or by one period does not change the depth map), state its precision (0.4 mm within a press, ≈ 1 mm
press to press against a rigid model), and do not report session-2 pose errors below ≈ 1 mm / 2°. Quantitative claims rest on session 1.

**Session 1 predicts session 2.** Splitting the 162 scored pool frames by how far the recorded poses are from the reference:

| Session-2 subset | Stale-label translation error | Stale-label IoU | Controlled drift on session 1 (D1) | AlignTac labels IoU |
|---|---|---|---|---|
| patterns 01_3, 32, 35, 36 (n = 62) | 1.23 mm | 0.565 | 0.56 at 1 mm | 0.611 |
| other seven objects (n = 100) | 2.34 mm | 0.220 | 0.30 at 2 mm, 0.19 at 3 mm | 0.560 |

**Run-level fusion on the real second session** (`rss2_s2_fusion.py`, `rss2_s2_fusion_k25_{recal,teacher}.json`; K = 25, 1,066 pool frames, 45 runs,
scored on 162 frames against the curated reference; IoU / contact MAE):

| Labels | Aligner started from the recorded pose | from the teacher |
|---|---|---|
| Recorded pose, stale calibration | 0.352 / 0.504 | |
| Per touch (aligner) | 0.564 / 0.353 | 0.580 / 0.326 |
| Rigid run fusion, median | 0.478 / 0.418 | 0.466 / 0.415 |
| Rigid run fusion, observability-aware | 0.515 / 0.391 | 0.471 / 0.414 |
| Touch evidence where observable + run estimate elsewhere (MAP, ρ = 4) | 0.579 / 0.346 | 0.547 / 0.354 |
| Same with the rigidity estimated per run (adaptive) | 0.550 / 0.365 | 0.538 / 0.355 |

Against this reference a rigid run estimate is worse than the per-touch labels, and the combination is at best equal. The reference is
itself a per-frame image fit, so it favours per-touch methods and cannot settle whether fusion helps after a real re-placement.
On session 1 the adaptive estimator gives 0.824 / 0.144 on seen objects (rigid 0.898, per touch 0.719) and 0.683 / 0.261 on the unseen
objects (rigid 0.769, per touch 0.624): it does not separate aligner noise from non-rigidity well enough to match the rigid estimate
where the run is rigid. **Status of fusion: demonstrated on session 1 (whose reference is rigid by construction), not demonstrated on a
real re-placement.** Settling this needs an independent reference (open question 10).

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
10. **Independent reference for a real re-placement.** Neither the session-2 pose accuracy nor the value of run-level fusion after a real
    re-placement can be decided with image-fitted references. A short capture would settle both: in each new placement (a) press an
    isotropic pattern (35 or 37; their fits are self-consistent to 0.1 mm) to obtain the placement independently, (b) repeat a few presses at
    identical commanded poses to measure press-to-press repeatability of the imprint. About one hour on the robot. Do it before the full paper?
11. **Label conversion (D8).** The real labels of both sessions place the mesh with an un-rotated end-effector translation; with the
    translation rotated by the tool yaw, presses agree with each other to 0.2 mm instead of 1.1 - 1.8 mm. Proposed: (a) rebuild corrected
    label roots for both sessions under new names (per object and session: one translation constant, one rotation constant, lever arm;
    all frames, including the third the filter deleted), (b) verify on held-out frames and on the line objects, (c) re-run the main
    tables on the corrected labels. This replaces the re-capture as the first step (rigidity is answered; session 2 gets a
    calibration-based reference from existing data). It changes every number and the size of the drift the paper motivates with, and
    the ICRA VisTacFusion real-data labels come from the same conversion. Go ahead with (a) and (b)? Is the original session-1 conversion
    script (`reorganize_to_sim_format.py`, not on this server) available?
    **Update 2026-11-13:** (a) and (b) done on the user's go-ahead (D9). Open: (c) re-run the main tables on the corrected roots, and how to
    frame the paper now that the real re-installation offset is about 0.4 mm / under 1.2 deg (one plate 18 deg) instead of millimetres.
    **Update 2026-11-14:** (c) done for the K = 25 minimal set (D11). With correct GT, AlignTac's in-session margin over Labeled only is
    IoU +0.004 (old labels: +0.066). Most paper tables (`B_`, `T_`, `P4_` families) still use the old `real_filtered` labels.
12. **Recovered presses.** `rfp` is worse than `rf` on dense metrics (session 2 IoU 0.820 vs 0.853). Keep them out of the pool, or switch
    to one unified session-1 pool with an even-interval train / val / test split (needs a full chain re-run, D11 "Split facts")?
    The user prefers no artificial session_000 / session_001 distinction; decision on the re-split pending.
13. **Where the method has headroom.** In-session K = 25 is near saturation (Labeled only 0.909, oracle 0.934). Candidates: AlignTac at
    K = 10 / 50 on the corrected labels (Labeled-only teachers `kin_k{10,50}_realonly` exist), and session-2 adaptation (14).
14. **Cross-session.** The session-2 rotation gap is half yaw coverage, half a real session shift (D12). Report with a yaw-matched
    session-1 control and Rot calib; re-run the session-2 adaptation (AlignTac labels on unlabeled session-2 frames, no recalibration,
    old-label P0-3) on the corrected labels? Needs an adapt / test split of the 1,813 session-2 frames.

## D11. Re-run on the corrected labels (started 2026-11-13 17:51, in progress)

Decision (user, 2026-11-13): use the corrected labels; the 4,964 recovered session-1 presses are **unlabeled pool only for now**
(test set = the same 530 testA frames, K=25 labeled frames unchanged). **After the minimal set finishes, ask the user whether later
runs keep this allocation.** The 14 old-label fold-2 jobs were stopped (their run dirs are kept, unfinished).

Pipeline `ablation/pilot_robosoft/rss2_kin_chain.sh` (same steps/arguments as the paper's K=25 chain; log `outputs/rss_logs/rss2_kin_chain.log`),
queue `outputs/rss_logs/rss2_jobs_kin.tsv` (GPUs 1-3, 3 per GPU; chain steps on GPU 0), evaluation mode `kin` of `rss2_train.sh`:
`rss2_kin_testA_results.json` (530 testA frames, corrected labels) and `rss2_kin_s2_results.json` (session 2, 1,813 frames, corrected labels).

| Run (`rss2_` + name, seeds 0-2) | Training data |
|---|---|
| `kin_k25_realonly` | Labeled only (300 frames, `real_filtered_kin`); seed 0 = teacher |
| `kin_k25_st` | + teacher labels on the pool (`real_pseudo_kin_k25_ng`) |
| `kin_k25_rf0` | + mesh at the teacher pose (`real_pseudo_kin_k25_tp0`) |
| `kin_k25_rf` | AlignTac, same pool as before (`real_pseudo_kin_k25_al`) |
| `kin_k25_rfp` | AlignTac, pool + recovered presses (`real_merge_kin_k25_rfp`) |
| `kin_k{10,50,100}_realonly`, `kin_all_oracle` (seed 0) | Labeled only at other K (teachers for later chains); all 3,667 pool labels (upper bound) |

Renderer `outputs/rss2_tactile_gan_kin_k25`, aligner `outputs/rss2_aligner_kin_k25`. Pool note: the teacher config excludes the testA
frames, so the pseudo-labeled pool is 3,367 frames (the old chain labeled 3,897 and excluded the test frames at student time; the
student training set is the same).

**Results (2026-11-14; all runs finished, 3 seeds mean ± std unless noted).** Rot calib = rotation error after removing a per-object
constant offset (circular median), as computed by `eval_cross_session.py`. Trans L1 is in normalized units.

Pseudo-label quality (`--eval-gt`, chain log): original pool 3,367 frames, mesh IoU 0.897 / cMAE 0.097 / rot 0.95°; recovered pool
4,345 frames, mesh IoU 0.765 / cMAE 0.186 / rot 6.72° (teacher alone: 0.641 / 0.151 / 14.74°).

testA (530 frames)

| Method | IoU | cMAE | Rot (°) | Rot calib (°) | Trans L1 |
|---|---|---|---|---|---|
| All labels (oracle, 1 seed) | 0.934 | 0.040 | 3.65 | 3.27 | 0.036 |
| Labeled only | 0.909 ± 0.000 | 0.084 ± 0.000 | 7.55 ± 0.36 | 6.75 ± 0.35 | 0.070 ± 0.003 |
| Teacher-label self-training (`st`) | 0.767 ± 0.001 | 0.096 ± 0.001 | 12.67 ± 1.31 | 12.02 ± 1.14 | 0.098 ± 0.009 |
| Mesh at teacher pose (`rf0`) | 0.543 ± 0.036 | 0.243 ± 0.006 | 13.52 ± 1.08 | 12.69 ± 0.85 | 0.108 ± 0.007 |
| **AlignTac (`rf`)** | 0.913 ± 0.001 | 0.085 ± 0.004 | 6.91 ± 1.72 | 5.77 ± 1.02 | 0.062 ± 0.010 |
| AlignTac + recovered pool (`rfp`) | 0.901 ± 0.005 | 0.090 ± 0.004 | 6.58 ± 2.15 | 5.45 ± 1.44 | 0.060 ± 0.013 |

session 2 (1,813 frames, never trained on)

| Method | IoU | cMAE | Rot (°) | Rot calib (°) | Trans L1 |
|---|---|---|---|---|---|
| All labels (oracle, 1 seed) | 0.855 | 0.130 | 14.66 | 6.55 | 0.086 |
| Labeled only | 0.845 ± 0.001 | 0.140 ± 0.001 | 21.06 ± 0.30 | 6.52 ± 0.20 | 0.113 ± 0.000 |
| Teacher-label self-training (`st`) | 0.740 ± 0.004 | 0.143 ± 0.003 | 30.50 ± 3.03 | 6.27 ± 0.18 | 0.139 ± 0.018 |
| Mesh at teacher pose (`rf0`) | 0.497 ± 0.057 | 0.291 ± 0.007 | 31.65 ± 2.43 | 6.43 ± 0.04 | 0.150 ± 0.005 |
| **AlignTac (`rf`)** | 0.853 ± 0.001 | 0.135 ± 0.005 | 18.58 ± 2.15 | 5.98 ± 0.39 | 0.111 ± 0.015 |
| AlignTac + recovered pool (`rfp`) | 0.820 ± 0.019 | 0.145 ± 0.004 | 17.27 ± 2.65 | 7.04 ± 1.15 | 0.098 ± 0.009 |

Reading:
- The corrected labels remove most of AlignTac's old margin. Old labels (testA): Labeled only → AlignTac IoU 0.674 → 0.739 (+0.066),
  rot 9.73° → 5.97°. Corrected labels: 0.909 → 0.913 (+0.004), rot 7.55° → 6.91°. The old Labeled-only depth was poor because its GT
  was misplaced; with correct GT, 300 labels already reach IoU 0.909 (oracle 0.934), so there is little in-session headroom at K = 25.
- The only clean gain of `rf` is IoU (in-session +0.004, session 2 +0.008, both with std ≤ 0.001). Its raw rotation gains are inside
  the seed spread (rf testA rot per seed 7.19 / 8.86 / 4.67°).
- `rfp` (recovered presses as extra unlabeled pool) is **worse** than `rf` on dense metrics, most clearly on session 2
  (IoU 0.820 ± 0.019 vs 0.853 ± 0.001; seed 0 alone 0.797). Its raw rotation looks better but is within the seed spread, and its
  calibrated rotation on session 2 is worse (7.04° vs 5.98°). The recovered pool's pseudo-labels are worse (mesh IoU 0.765 vs 0.897).
  CORRECTION: on 2026-11-14 the assistant first reported rfp from two finished seeds as "depth only slightly worse, pose better";
  the third seed changed this.
- Split facts (for the allocation decision): the recovered presses are the same capture as `session_000` (identical `session.json`,
  manifest `session: s1`; both keep `original_sample_id`, 9,633 presses, no id collisions). In `rfp`, the 501 recovered presses with
  index % 10 == 0 never entered training (pseudo_label.py skips the val slot and the chain did not pass `--link-val`). A unified
  even-interval split by capture order (rank % 10 in {5, 8} test, rank % 10 == 0 val) would give 6,741 pool / 968 val / 1,924 test,
  but needs the whole chain re-run (new K = 25 frames, new test set).

## D12. Session 2 with the corrected labels: labels are right, the rotation gap is yaw coverage + a real session shift (2026-11-14)

Scripts in the session scratchpad (`s2_label_check.py`, `yaw_bias.py`, `subsess.py`, `dist.py`, `eval_sym.py`, `offset.py`,
`inrange.py`, `sameband.py`, `sameband_rf.py`, figures `s1_vs_s2_page{1,2}.png`, `s2_label_pairs_page{1,2}.png`); not committed.

1. **The session-2 labels match the tactile images.** Mesh-at-label vs stored GT depth: IoU 0.951 (s1) / 0.941 (s2), but this is
   circular (both come from the same kinematic model). The independent test: sweep a yaw offset and find the offset that best aligns
   the mesh footprint with the measured contact (image minus background). s1: median +1.0°, mean |offset| 1.50°, 93 % within ±3°;
   s2: median +1.0°, mean |offset| 3.18°, 78 % within ±3°. No systematic bias; session 2 is about twice as noisy. Per sub-session,
   `session_007` is off (+29° to +50°, inconsistent between frames) but has only 12 frames. Visual check of 24 random s2 frames
   (label outline over contact): aligned except two frames a few degrees off and one press mostly outside the gel. The −177° and +21°
   fitted dθ of `pattern_04_3_lines_angle_2` / `pattern_06_5_lines_angle_1` in `real_s2_kin_all/kin_manifest.json` are 360°-wrap /
   absorbed-constant artifacts; their labels align with the images (median offset +2° / +1°).
2. **Not a symmetry artifact.** Six objects are rotationally symmetric (k = 2: the three two-line patterns and 31_rod; k = 3:
   04_3_lines_angle_1; k = 5: 06_5_lines_angle_1). Folding the model's rotation error by the object's symmetry changes nothing
   (all errors are below half the period).
3. **The model has a per-object constant yaw bias on session 2 only.** Labeled only (seed 0), signed circular-median error per object:
   testA −7.3° … +4.0°; session 2 +4.0° … +38.8° (session-wide +20.6°, except 31_rod +4.0° and 32 −10.4°). Removing it leaves
   2.8–10.8° on session 2, the same range as testA (4.5–13°). This is why Rot (21.06°) and Rot calib (6.52°) differ so much.
4. **Session 2 covers a narrow yaw band at one edge of session 1's range.** Per object, s1 spans about 90° of yaw, s2 about 25°,
   placed at the low end of the s1 range (e.g. 01_2_lines_angle_1_2: s1 −39.5° … +47.8°, s2 −44.7° … −21.2°). 81 % of s2 frames lie
   inside the s1 range. Restricting session 2 to those frames barely helps (Labeled only 21.06° → 20.24°, bias +20.3° → +19.9°), so
   evaluating on the overlap is **not** a fix.
5. **Decomposition with a yaw-matched session-1 control.** Session-1 frames that fall inside each object's s2 yaw band and were never
   trained on by either model (testA + val slots, 110 frames), 3 seeds:

   | Model | s1 outside band: bias / rot | **s1 inside s2 band**: bias / rot | s2: bias / rot | session part of the bias |
   |---|---|---|---|---|
   | Labeled only | −0.5° / 7.06° | +8.7° ± 1.2 / 11.27° | +20.3° ± 1.2 / 21.06° | ≈ +11.6° |
   | AlignTac (`rf`) | −0.8° / 6.34° | +4.9° ± 3.0 / 9.33° | +16.4° ± 3.4 / 18.58° | ≈ +11.5° |

   (With 474 band frames unseen by Labeled only, its band bias is +9.4° / 12.76°.) About half of the session-2 rotation bias appears on
   session 1 at the same yaw: the band is at the edge of the training distribution, where K = 25 gives each object only a few labels.
   AlignTac roughly halves this edge part (pseudo-labels cover the whole pool), which is all of its session-2 rotation gain; the
   remaining ≈ +11.5° is a genuine session shift that no session-1-only training touches. The all-labels oracle still has
   14.66° raw / 6.55° calibrated on session 2.
6. **Reporting.** Session-2 rotation should be reported next to the yaw-matched session-1 control (same objects, same yaw band) and
   with Rot calib; otherwise "cross-session" mixes a yaw-coverage effect with the session shift. Old-label P0-3 (top of this file)
   already showed the method's answer to the session part: AlignTac labels on unlabeled session-2 frames, no recalibration
   (rot 10.2° → 5.4–7.8° on the old session-2 test half). That experiment has not been re-run on the corrected labels.
