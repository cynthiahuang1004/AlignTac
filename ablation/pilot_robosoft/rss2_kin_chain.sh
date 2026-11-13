#!/bin/bash
# K=25 pipeline on the corrected labels (RSS_ROUND2_RESULTS.md D8-D10).  Same steps and arguments as the paper's K=25 chain
# (renderer -> Labeled-only teacher -> aligner -> teacher labels -> aligned mesh labels -> students), new names, nothing overwritten.
#   labeled root   real_filtered_kin       (same frames / indices as real_filtered; K=25 frames and testA frames unchanged)
#   recovered pool real_filtered_kin_plus/<obj>/session_001 (4,964 presses the old filter had dropped): UNLABELED only, their
#                  corrected labels are never used for training (only for the label-quality report of pseudo_label_rc --eval-gt)
#   students       kin_k25_{realonly, st, rf0, rf, rfp}[_seed1,_seed2]  (queued in $J by this script once their roots exist)
# usage: CUDA_VISIBLE_DEVICES=<gpu> bash ablation/pilot_robosoft/rss2_kin_chain.sh      (every step is skipped if already done)
cd /media/hdd/ihsuan/VisTacFusion/AlignTac; export PYTHONPATH=/media/hdd/ihsuan/VisTacFusion/AlignTac PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
G=/media/hdd/ihsuan/gs_blender; L=outputs/rss_logs; P=ablation/pilot_robosoft; S=scripts/tactile_render; J=$L/rss2_jobs_kin.tsv
PY="conda run --no-capture-output -n vistacfusion python -u"
R=$G/real_filtered_kin; N=kin_k25; T=${N}_realonly; GAN=outputs/rss2_tactile_gan_$N; AL=outputs/rss2_aligner_$N; POOL=$G/real_kin_pool_rec
step() { echo "$(date '+%m-%d %H:%M') [kin chain] $*" >> $L/rss2_kin_chain.log; }
fail() { step "FAILED: $*"; exit 1; }
exec 9> $L/rss2_kin_chain.lock; flock -n 9 || { step "another instance is running, leaving"; exit 0; }
queue() { for r in "$@"; do grep -q "^rss2_$r	" $J 2>/dev/null || printf 'rss2_%s\tbash %s/rss2_train.sh rss2_ %s kin >> %s/rss2_train.log 2>&1\n' $r $P $r $L >> $J; done; step "queued: $*"; }
rc() { $PY $S/pseudo_label_rc.py --run $T --prefix rss2_ --gan $GAN --aligner $AL/aligner.pt --keep-frac 1.0 --pose-all --eval-gt --device cuda:0 "$@"; }

if [ ! -f $GAN/G_final.pt ]; then step "renderer (K=25 labeled frames, corrected labels)"
  $PY $S/train_tactile_gan.py --real-root $R --per-object 25 --min-steps 30000 --device cuda:0 --out $GAN > $L/rss2_gan_$N.log 2>&1 || fail renderer; fi
if [ ! -f $AL/aligner.pt ]; then step "aligner (K=25 labeled frames)"
  $PY $S/train_aligner.py --k 25 --gan $GAN --out $AL --steps 8000 --bs-real 64 --bs-sim 0 --real-root $R --device cuda:0 > $L/rss2_aligner_$N.log 2>&1 || fail aligner; fi
step "waiting for the teacher (rss2_$T)"
for i in $(seq 4320); do [ -f runs/rss2_$T/.train_done ] && break; sleep 60; done; [ -f runs/rss2_$T/.train_done ] || fail "teacher missing"
if [ ! -f $G/real_pseudo_${N}_ng/pseudo_manifest.json ]; then step "teacher labels + pose"
  $PY $S/pseudo_label.py --run $T --prefix rss2_ --k 25 --real-root $R --out-root $G/real_pseudo_${N}_ng --device cuda:0 --pose --link-val --iou-thr 0 > $L/rss2_pseudo_${N}_ng.log 2>&1 || fail "teacher labels"; fi
queue ${N}_st ${N}_st_seed1 ${N}_st_seed2
if [ ! -f $G/real_pseudo_${N}_al/pseudo_manifest.json ]; then step "aligned mesh labels"
  rc --src-root $G/real_pseudo_${N}_ng --real-root $R --out-root $G/real_pseudo_${N}_al > $L/rss2_pseudo_${N}_al.log 2>&1 || fail "rc al"; fi
step "labels (aligned): $(grep -A3 '^labels' $L/rss2_pseudo_${N}_al.log | tr '\n' '|')"
queue ${N}_rf ${N}_rf_seed1 ${N}_rf_seed2
if [ ! -f $G/real_pseudo_${N}_tp0/pseudo_manifest.json ]; then step "mesh at the teacher pose (control)"
  rc --aligner-iters 0 --src-root $G/real_pseudo_${N}_ng --real-root $R --out-root $G/real_pseudo_${N}_tp0 > $L/rss2_pseudo_${N}_tp0.log 2>&1 || fail "rc tp0"; fi
queue ${N}_rf0 ${N}_rf0_seed1 ${N}_rf0_seed2
# ---- recovered presses as additional unlabeled pool ----
if [ ! -d $POOL ]; then for o in $G/real_filtered_kin_plus/pattern_*; do n=$(basename $o); mkdir -p $POOL/$n; ln -s $o/session_001 $POOL/$n/session_001; done; fi
if [ ! -f $G/real_pseudo_${N}_rec_ng/pseudo_manifest.json ]; then step "teacher labels, recovered pool"
  $PY $S/pseudo_label.py --run $T --prefix rss2_ --k 25 --real-root $POOL --out-root $G/real_pseudo_${N}_rec_ng --device cuda:0 --pose --unlabeled-only --iou-thr 0 > $L/rss2_pseudo_${N}_rec_ng.log 2>&1 || fail "teacher labels rec"; fi
if [ ! -f $G/real_pseudo_${N}_rec_al/pseudo_manifest.json ]; then step "aligned mesh labels, recovered pool"
  rc --src-root $G/real_pseudo_${N}_rec_ng --real-root $POOL --out-root $G/real_pseudo_${N}_rec_al > $L/rss2_pseudo_${N}_rec_al.log 2>&1 || fail "rc rec al"; fi
step "labels (recovered pool): $(grep -A3 '^labels' $L/rss2_pseudo_${N}_rec_al.log | tr '\n' '|')"
M=$G/real_merge_${N}_rfp
if [ ! -d $M ]; then for o in $G/real_pseudo_${N}_al/pattern_*; do n=$(basename $o); mkdir -p $M/$n
    ln -s $o/session_000 $M/$n/session_000; [ -d $G/real_pseudo_${N}_rec_al/$n/session_001 ] && ln -s $G/real_pseudo_${N}_rec_al/$n/session_001 $M/$n/session_001; done; fi
step "merged root rfp: $(find -L $M -name '*_gt.npy' | wc -l) label files"
queue ${N}_rfp ${N}_rfp_seed1 ${N}_rfp_seed2
step "chain done"
