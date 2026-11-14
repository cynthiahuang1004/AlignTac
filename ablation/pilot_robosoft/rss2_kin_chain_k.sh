#!/bin/bash
# K-shot AlignTac chain on the corrected labels for K != 25 (K = 25: rss2_kin_chain.sh). Same steps and arguments as the K = 25 chain:
# renderer (K labeled frames, --min-steps 30000) -> aligner (8000 steps, real only) -> Labeled-only teacher (rss2_kin_k<K>_realonly,
# already trained) -> teacher labels -> aligned mesh labels -> students kin_k<K>_{realonly seeds 1-2, st, rf} x 3 seeds.
# Starts only when the GPUs are free of our earlier jobs (waits for the files in WAIT_FOR to exist), then uses the GPU with most free memory.
# usage: setsid nohup bash ablation/pilot_robosoft/rss2_kin_chain_k.sh 10 &
K=$1; [ -n "$K" ] || { echo "usage: $0 K"; exit 1; }
cd /media/hdd/ihsuan/VisTacFusion/AlignTac; export PYTHONPATH=/media/hdd/ihsuan/VisTacFusion/AlignTac PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
G=/media/hdd/ihsuan/gs_blender; L=outputs/rss_logs; P=ablation/pilot_robosoft; S=scripts/tactile_render; J=$L/rss2_jobs_kin.tsv
PY="conda run --no-capture-output -n vistacfusion python -u"
R=$G/real_filtered_kin; N=kin_k$K; T=${N}_realonly; GAN=outputs/rss2_tactile_gan_$N; AL=outputs/rss2_aligner_$N
WAIT_FOR=${WAIT_FOR:-"runs/rss2_kin_k25_rf_s2/.train_done runs/rss2_kin_k25_rf_s2_seed1/.train_done runs/rss2_kin_k25_rf_s2_seed2/.train_done runs/rss2_kin_k25_st_s2/.train_done runs/rss2_kin_k25_st_s2_seed1/.train_done runs/rss2_kin_k25_st_s2_seed2/.train_done"}
step() { echo "$(date '+%m-%d %H:%M') [kin k$K chain] $*" >> $L/rss2_kin_chain_k$K.log; }
fail() { step "FAILED: $*"; exit 1; }
exec 9> $L/rss2_kin_chain_k$K.lock; flock -n 9 || { step "another instance is running, leaving"; exit 0; }
queue() { for r in "$@"; do grep -q "^rss2_$r	" $J 2>/dev/null || printf 'rss2_%s\tbash %s/rss2_train.sh rss2_ %s kin >> %s/rss2_train.log 2>&1\n' $r $P $r $L >> $J; done; step "queued: $*"; }

step "waiting for the GPUs (earlier jobs: $WAIT_FOR)"
while :; do ok=1; for f in $WAIT_FOR; do [ -f $f ] || ok=0; done; [ $ok = 1 ] && break; sleep 600; done
[ -f runs/rss2_$T/.train_done ] || fail "teacher rss2_$T missing"
export CUDA_VISIBLE_DEVICES=$(nvidia-smi --query-gpu=index,memory.free --format=csv,noheader,nounits | sort -t, -k2 -nr | head -1 | cut -d, -f1)
step "start on GPU $CUDA_VISIBLE_DEVICES"
queue ${T}_seed1 ${T}_seed2
if [ ! -f $GAN/G_final.pt ]; then step "renderer (K=$K labeled frames, corrected labels)"
  $PY $S/train_tactile_gan.py --real-root $R --per-object $K --min-steps 30000 --device cuda:0 --out $GAN > $L/rss2_gan_$N.log 2>&1 || fail renderer; fi
if [ ! -f $AL/aligner.pt ]; then step "aligner (K=$K labeled frames)"
  $PY $S/train_aligner.py --k $K --gan $GAN --out $AL --steps 8000 --bs-real 64 --bs-sim 0 --real-root $R --device cuda:0 > $L/rss2_aligner_$N.log 2>&1 || fail aligner; fi
if [ ! -f $G/real_pseudo_${N}_ng/pseudo_manifest.json ]; then step "teacher labels + pose"
  $PY $S/pseudo_label.py --run $T --prefix rss2_ --k $K --real-root $R --out-root $G/real_pseudo_${N}_ng --device cuda:0 --pose --link-val --iou-thr 0 > $L/rss2_pseudo_${N}_ng.log 2>&1 || fail "teacher labels"; fi
if [ ! -f $G/real_pseudo_${N}_al/pseudo_manifest.json ]; then step "aligned mesh labels"
  $PY $S/pseudo_label_rc.py --run $T --prefix rss2_ --gan $GAN --aligner $AL/aligner.pt --keep-frac 1.0 --pose-all --eval-gt --device cuda:0 \
    --src-root $G/real_pseudo_${N}_ng --real-root $R --out-root $G/real_pseudo_${N}_al > $L/rss2_pseudo_${N}_al.log 2>&1 || fail "rc al"; fi
step "labels (aligned): $(grep -A3 '^labels' $L/rss2_pseudo_${N}_al.log | tr '\n' '|')"
for v in st:ng rf:al; do D=$P/data_${N}_${v%%:*}.yaml; src=$P/data_kin_k25_${v%%:*}.yaml
  [ -f $D ] || sed "s#root: $G/real_pseudo_kin_k25_${v#*:}\$#root: $G/real_pseudo_${N}_${v#*:}#" $src > $D
  grep -q "root: $G/real_pseudo_${N}_${v#*:}\$" $D || fail "$D does not point at real_pseudo_${N}_${v#*:}"; done
queue ${N}_st ${N}_st_seed1 ${N}_st_seed2 ${N}_rf ${N}_rf_seed1 ${N}_rf_seed2
step "chain done"
