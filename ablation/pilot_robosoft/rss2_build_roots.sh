#!/bin/bash
# RSS round 2: write label roots + data configs from fitted poses (no training).  usage: rss2_build_roots.sh <s1|s2>
cd /media/hdd/ihsuan/VisTacFusion/AlignTac
G=/media/hdd/ihsuan/gs_blender; L=outputs/rss_logs; PY="conda run --no-capture-output -n vistacfusion python -u"; P=ablation/pilot_robosoft
case $1 in
s1)  # P0-1: optimization-based labels for the K=25 session-1 pool (same 3,897 frames as T_k25_rf)
  for m in icp gd grid; do
    [ -f $G/real_pseudo_k25_ro_$m/pseudo_manifest.json ] || $PY scripts/tactile_render/pseudo_label_rc.py --src-root $G/real_pseudo_k25_ro_ng --out-root $G/real_pseudo_k25_ro_$m \
       --run B_k25_realonly --prefix pilot150_ --gan outputs/tactile_gan_k25 --fits outputs/rss2_fits/s1_k25/fits_$m.json --keep-frac 1.0 --pose-all --eval-gt > $L/rss2_root_k25_$m.log 2>&1
    grep -A4 "^labels" $L/rss2_root_k25_$m.log | head -3
    sed "s#real_pseudo_k25_ro_al\$#real_pseudo_k25_ro_$m#" $P/data_T_k25_rf.yaml > $P/data_T_k25_$m.yaml; grep -n "real_pseudo" $P/data_T_k25_$m.yaml
  done ;;
s2)  # P0-3 / P2-8: session-2 pool labels from the recorded pose (old calibration) and from consensus -> aligner
  for m in oldcal consal recal; do
    [ -f $G/real_pseudo_s2_k25_$m/pseudo_manifest.json ] || $PY scripts/tactile_render/pseudo_label_rc.py --src-root $G/real_pseudo_s2_k25_ng --real-root $G/real_s2_pool --run T_k25_realonly \
       --gan outputs/tactile_gan_k25 --fits outputs/rss2_fits/s2_k25/fits_${m}_all.json --out-root $G/real_pseudo_s2_k25_$m --keep-frac 1.0 --pose-all > $L/rss2_root_s2_k25_$m.log 2>&1
    tail -3 $L/rss2_root_s2_k25_$m.log | head -2
    M=$G/real_merge_k25_rf_s2$m; rm -rf $M
    for o in $G/real_pseudo_k25_ro_al/pattern_*; do n=$(basename $o); mkdir -p $M/$n
      for s in $o/session_*; do ln -s $s $M/$n/$(basename $s); done
      for s in $G/real_pseudo_s2_k25_$m/$n/session_*; do [ -d "$s" ] && ln -s $s $M/$n/$(basename $s); done; done
    sed "s#real_merge_k25_rf_s2\$#real_merge_k25_rf_s2$m#" $P/data_T_k25_rf_s2.yaml > $P/data_T_k25_rf_s2$m.yaml; grep -n "real_merge" $P/data_T_k25_rf_s2$m.yaml
  done ;;
esac
