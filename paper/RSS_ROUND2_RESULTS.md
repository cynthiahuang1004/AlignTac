# AlignTac — RSS 2027 round 2 results

Working document for the Stage-1 extended abstract (due 2026-12-04 AoE). Every number below comes from a JSON under
`ablation/pilot_robosoft/` (file named per section); run names, configs and logs (`outputs/rss_logs/`) are listed per task.
Branch `rss-round2` (not pushed). Last update: 2026-11-10 02:45 UTC.

## Status

| Task | Status | Notes |
|---|---|---|
| §1 Sanity check after the outage | done | data roots, meshes, checkpoints intact after the hdd2 → hdd move; SITR encoder checkpoint was lost with `gsrl/`, rebuilt from run checkpoints and verified bit-exact on testA |
| P0-1 Optimization labels → student | labels done, students queued | ICP / GD / grid roots written; `rss2_T_k25_{icp,gd,grid}` + seeds in queue B |
| P0-2 Mean teacher | running | implemented; weight sweep 1 / 10 / 50 at ~95/150 epochs |
| P0-3 Conventional labels under drift | labels done | student `rss2_T_k25_rf_s2oldcal` queued |
| P0-4 New objects (LOO-3) | running | 9 students (al / tp / oracle × 3 seeds) at ~60/150 epochs |
| P1-5 Confidence | analysis done, students queued | conf / random / oracle at 75 % and 50 % |
| P1-6 Unlabeled quantity | roots done, students queued | 25 % / 50 % pools for AlignTac and self-training |
| P1-7 Single-touch localization | running | sessions 1 and 2, K = 25 (3 seeds) and 100 |
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
the aligner, which reads the image, does (0.235). Student rows of T1 are pending (queue B).

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

## P2-8 / T5 — session-level consensus (`rss2_s2_consensus_k25.json`, `_k100.json`)
Reference per run = median of (curated label − recorded pose) over the run's curated frames (38 runs). Recorded-pose drift by that
reference: mean 3.4° / 3.0 mm, median 1.4° / 1.4 mm per run. Run consensus from the aligner started at the recorded pose:
rotation median 1.12° (mean 2.85°), translation median 1.61 mm (mean 2.36 mm);
21 % of runs within 2° / 1 mm. More presses barely help (20 presses: 1.1° / 1.4 mm).
**Gate (median < 2° and < 0.5 mm) not met**: the per-run offset is not rigid enough — curated-minus-recorded varies by ~0.8 mm (sd)
within a run. Consensus → aligner gives +0.02 IoU at K = 100 (0.646 vs 0.628) and nothing at K = 25. Recommendation: report as an
analysis, do not adopt as a method component.

## Open questions
1. **Drift number.** The paper's "per-run corrections averaged 11.4° / 1.6 mm" comes from `pose_calibration_new.json` (grid search on
   contact masks), which does not agree with the curated labels. Curated − recorded is 3.4° / 3.0 mm (means), 1.4° / 1.4 mm (medians).
   Which number goes into the abstract / Fig. 1? (Suggestion: the curated-based one, phrased as "re-placement moved the contact by
   1–3 mm and a few degrees", with the conventional-label row of T2 as the consequence.)
2. **SITR checkpoint.** The original under `gsrl/` is gone; the rebuilt copy reproduces stored numbers exactly. If you still have the
   original file, drop it into `VisTacFusion/weights/`.
3. **LOO-3 run dirs.** `runs/pilot150_A_loo3_{al,tp,oracle}` held 5-epoch fragments of the interrupted 11-01 runs and are being
   retrained from scratch in place (rule 1 technically violated; no results were lost).
4. **P2-8**: stop here (recommended) or try a per-press offset model?
5. Two-line patterns stay at IoU ≈ 0.4 for every method on session 2; confidence filtering will mostly drop them.
