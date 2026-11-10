#!/bin/bash
# RSS round 2, controlled drift on session 1: label roots + data configs from outputs/rss2_fits/s1_k25_drift/fits_dr<T>_{stale,al}.json,
# then queue the students (queue B).  usage: rss2_drift_roots.sh <gpu> [levels="05 10 20 30"]
GPU=${1:-2}; LV=${2:-"05 10 20 30"}
cd /media/hdd/ihsuan/VisTacFusion/AlignTac; export PYTHONPATH=/media/hdd/ihsuan/VisTacFusion/AlignTac CUDA_VISIBLE_DEVICES=$GPU
G=/media/hdd/ihsuan/gs_blender; L=outputs/rss_logs; PY="conda run --no-capture-output -n vistacfusion python -u"; P=ablation/pilot_robosoft
for t in $LV; do for m in stale al; do n=dr${t}_$m
  until [ -f outputs/rss2_fits/s1_k25_drift/fits_$n.json ]; do sleep 20; done
  [ -f $G/real_pseudo_k25_ro_$n/pseudo_manifest.json ] || $PY scripts/tactile_render/pseudo_label_rc.py --src-root $G/real_pseudo_k25_ro_ng --out-root $G/real_pseudo_k25_ro_$n \
     --run B_k25_realonly --prefix pilot150_ --gan outputs/tactile_gan_k25 --fits outputs/rss2_fits/s1_k25_drift/fits_$n.json --keep-frac 1.0 --pose-all --eval-gt > $L/rss2_root_k25_$n.log 2>&1 \
     || { echo "$(date '+%m-%d %H:%M') root $n FAILED"; tail -3 $L/rss2_root_k25_$n.log; continue; }
  sed "s#real_pseudo_k25_ro_al\$#real_pseudo_k25_ro_$n#" $P/data_T_k25_rf.yaml > $P/data_T_k25_$n.yaml
  grep -q "real_pseudo_k25_ro_$n\$" $P/data_T_k25_$n.yaml || { echo "config $n: root not substituted"; continue; }
  grep -q "^rss2_T_k25_$n	" $L/rss2_jobs_b.tsv || printf 'rss2_T_k25_%s\tbash ablation/pilot_robosoft/rss2_train.sh rss2_ T_k25_%s testA >> outputs/rss_logs/rss2_train.log 2>&1\n' $n $n >> $L/rss2_jobs_b.tsv
  echo "$(date '+%m-%d %H:%M') root + config + job: $n"
done; done
