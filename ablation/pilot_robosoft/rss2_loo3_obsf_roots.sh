#!/bin/bash
# RSS round 2b, new objects: label roots + merged roots + configs + queue entries for labels written by rss2_obs_fusion.py --write-fits.
# usage: rss2_loo3_obsf_roots.sh <device> <variant>=<fits json> ...     e.g.  cpu obsf=outputs/rss2_fits/loo3/fits_obsf_syn3_r2.json
DEV=$1; shift
cd /media/hdd/ihsuan/VisTacFusion/AlignTac; export PYTHONPATH=/media/hdd/ihsuan/VisTacFusion/AlignTac
G=/media/hdd/ihsuan/gs_blender; L=outputs/rss_logs; PY="conda run --no-capture-output -n vistacfusion python -u"; P=ablation/pilot_robosoft
HELD="pattern_04_3_lines_angle_2 pattern_31_rod pattern_33"
for a in "$@"; do v=${a%%=*}; f=${a#*=}
  [ -f $G/real_pseudo_loo3_$v/pseudo_manifest.json ] || $PY scripts/tactile_render/pseudo_label_rc.py --src-root $G/real_pseudo_loo3_ng --real-root $G/real_loo3 --run A_bgcondloo --prefix pilot150_ \
     --gan outputs/tactile_gan_loo --fits $f --out-root $G/real_pseudo_loo3_$v --keep-frac 1.0 --pose-all --eval-gt --device $DEV > $L/pseudo_loo3_$v.log 2>&1 \
     || { echo "root $v FAILED"; tail -3 $L/pseudo_loo3_$v.log; continue; }
  grep -A6 "^labels" $L/pseudo_loo3_$v.log | head -8
  M=$G/real_loo3_merge_$v
  if [ ! -d $M ]; then for o in $G/real_filtered/pattern_*; do n=$(basename $o); mkdir -p $M/$n
      src=$o; case " $HELD " in *" $n "*) src=$G/real_pseudo_loo3_$v/$n;; esac
      for s in $src/session_*; do [ -d "$s" ] && ln -s $s $M/$n/$(basename $s); done; done; fi
  sed "s#real_loo3_merge_al\$#real_loo3_merge_$v#" $P/data_A_loo3_al.yaml > $P/data_A_loo3_$v.yaml
  grep -q "real_loo3_merge_$v\$" $P/data_A_loo3_$v.yaml || { echo "config $v: root not substituted"; continue; }
  echo "$(date '+%m-%d %H:%M') root + merged root + config: $v ($(find -L $M -name '*_gt.npy' | wc -l) label files)"
done
