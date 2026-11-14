#!/bin/bash
# Label-free cross-session adaptation (paper Table "second session", rows "+ session 2") re-run on the corrected labels, K = 25.
# Same steps and arguments as the paper's chain (real_pseudo_s2_k25_{ng,al}, real_merge_k25_{rf,semipm}_s2), with the corrected
# session-1 teacher / renderer / aligner (rss2_kin_chain.sh) and the paper's press split applied to the corrected session-2 frames
# (rss2_kin_s2_split.py): pool presses -> images only, poses discarded; test presses -> evaluation (s2test 904, s2half 464 = paper's).
# usage: CUDA_VISIBLE_DEVICES=<gpu> bash ablation/pilot_robosoft/rss2_kin_s2adapt.sh      (every step is skipped if already done)
cd /media/hdd/ihsuan/VisTacFusion/AlignTac; export PYTHONPATH=/media/hdd/ihsuan/VisTacFusion/AlignTac PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
G=/media/hdd/ihsuan/gs_blender; L=outputs/rss_logs; P=ablation/pilot_robosoft; S=scripts/tactile_render; J=$L/rss2_jobs_kin.tsv
PY="conda run --no-capture-output -n vistacfusion python -u"; M=ablation/encoder/tac_sitr_single.yaml
N=kin_k25; T=${N}_realonly; GAN=outputs/rss2_tactile_gan_$N; AL=outputs/rss2_aligner_$N; POOL=$G/real_s2_kin_pool; JS=$P/rss2_kin_s2adapt_results.json
step() { echo "$(date '+%m-%d %H:%M') [kin s2adapt] $*" >> $L/rss2_kin_s2adapt.log; }
fail() { step "FAILED: $*"; exit 1; }
exec 9> $L/rss2_kin_s2adapt.lock; flock -n 9 || { step "another instance is running, leaving"; exit 0; }
queue() { for r in "$@"; do grep -q "^rss2_$r	" $J 2>/dev/null || printf 'rss2_%s\tbash %s/rss2_train.sh rss2_ %s kins2 >> %s/rss2_train.log 2>&1\n' $r $P $r $L >> $J; done; step "queued: $*"; }

[ -d $POOL ] || python3 $P/rss2_kin_s2_split.py >> $L/rss2_kin_s2adapt.log 2>&1 || fail split
if [ ! -f $G/real_pseudo_kin_s2_k25_ng/pseudo_manifest.json ]; then step "teacher labels + pose, session-2 pool"
  $PY $S/pseudo_label.py --run $T --prefix rss2_ --k 25 --real-root $POOL --out-root $G/real_pseudo_kin_s2_k25_ng --device cuda:0 --pose --unlabeled-only --iou-thr 0 > $L/rss2_pseudo_kin_s2_k25_ng.log 2>&1 || fail "teacher labels s2"; fi
if [ ! -f $G/real_pseudo_kin_s2_k25_al/pseudo_manifest.json ]; then step "aligned mesh labels, session-2 pool"
  $PY $S/pseudo_label_rc.py --run $T --prefix rss2_ --gan $GAN --aligner $AL/aligner.pt --keep-frac 1.0 --pose-all --eval-gt --device cuda:0 \
    --src-root $G/real_pseudo_kin_s2_k25_ng --real-root $POOL --out-root $G/real_pseudo_kin_s2_k25_al > $L/rss2_pseudo_kin_s2_k25_al.log 2>&1 || fail "rc s2"; fi
step "labels (session-2 pool): $(grep -A3 '^labels' $L/rss2_pseudo_kin_s2_k25_al.log | tr '\n' '|')"
for m in rf:al st:ng; do v=${m%%:*}; s1=$G/real_pseudo_${N}_${m#*:}; s2=$G/real_pseudo_kin_s2_k25_${m#*:}; R=$G/real_merge_${N}_${v}_s2
  if [ ! -d $R ]; then for o in $s1/pattern_*; do n=$(basename $o); mkdir -p $R/$n; ln -s $o/session_000 $R/$n/session_000
      for s in $s2/$n/session_*; do [ -d "$s" ] && ln -s $s $R/$n/$(basename $s); done; done; fi
  [ -f $P/data_${N}_${v}_s2.yaml ] || sed "s#root: $s1\$#root: $R#" $P/data_${N}_${v}.yaml > $P/data_${N}_${v}_s2.yaml
  grep -q "root: $R\$" $P/data_${N}_${v}_s2.yaml || fail "data_${N}_${v}_s2.yaml does not point at $R"
  step "merged root ${v}_s2: $(find -L $R -name '*_gt.npy' | wc -l) label files"
done
queue ${N}_rf_s2 ${N}_rf_s2_seed1 ${N}_rf_s2_seed2 ${N}_st_s2 ${N}_st_s2_seed1 ${N}_st_s2_seed2
# zero-shot rows of the same table, on the same test frames
has() { python3 -c "import json,os,sys; d=json.load(open('$1')) if os.path.exists('$1') else {}; sys.exit(0 if '$2' in d else 1)"; }
for r in ${N}_realonly ${N}_st ${N}_rf; do for sd in "" _seed1 _seed2; do for r2 in real_s2_kin_testhalf:s2test real_s2_kin_testhalf_c464:s2half; do
  for ck in best_depth.pt best_pose.pt; do t=${r2#*:}; [ $ck = best_pose.pt ] && t=${t}_bp; has $JS "rss2_$r$sd/$t" && continue
    flock $L/eval.lock $PY $P/eval_cross_session.py --device cuda:0 --batch 16 --ckpt $ck --json $JS --root $G/${r2%%:*} --tag $t --model $M $r$sd:rss2_ 2>&1 | grep -v Warning | tail -1 >> $L/rss2_kin_s2adapt.log
  done; done; done; done
step "zero-shot rows evaluated on the test presses; chain done"
