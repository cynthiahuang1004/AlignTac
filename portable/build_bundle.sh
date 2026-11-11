#!/bin/bash
# Build the portable bundle (code + data needed to train / evaluate AlignTac students away from the server).
# usage: bash portable/build_bundle.sh <out dir> [parts="01 02 02b 03"]
# Archives are relative to /media/hdd/ihsuan (see portable/setup.sh).  Nothing on the server is modified.
OUT=$1; PARTS=${2:-"01 02 02b 03"}; R=/media/hdd/ihsuan; mkdir -p $OUT; cd $R || exit 1
Z="zstd -T12 -8 -q -f"; step() { echo "$(date '+%m-%d %H:%M') $*"; }
A=VisTacFusion/AlignTac
for p in $PARTS; do case $p in
01) step "01_code"
  { ls -A $A | grep -v -x -e runs -e runs_local -e outputs | sed "s#^#$A/#"
    for d in $A/outputs/aligner_* $A/outputs/tactile_gan_k10 $A/outputs/tactile_gan_k25 $A/outputs/tactile_gan_k50 $A/outputs/tactile_gan_k100 $A/outputs/tactile_gan_loo $A/outputs/rss2_fits \
             $A/outputs/sensorB_mapl/fits_train_canon_symmetry.json; do [ -e $d ] && echo $d; done
    echo VisTacFusion/weights/SITR_B18.pth; } > $OUT/01_code.list
  tar -cf - --exclude='__pycache__' --exclude='*.pyc' -T $OUT/01_code.list | $Z -o $OUT/01_code.tar.zst ;;
02) step "02_real_core"
  { echo gs_blender/meshes; for d in gs_blender/real_filtered gs_blender/real_filtered_testA gs_blender/real_filtered_sel* gs_blender/real_filtered_new* gs_blender/real_loo3* gs_blender/real_pseudo_loo3_* gs_blender/real_s2_* \
      gs_blender/real_pseudo_s2_k25_* gs_blender/real_merge_k25_* gs_blender/real_pseudo_k25_ro_* gs_blender/real_pseudo_k25_u* gs_blender/real_pseudo_k25 gs_blender/real_pseudo_k25_al gs_blender/real_pseudo_k25_ng; do [ -e $d ] && echo $d; done; } | sort -u > $OUT/02_real_core.list
  tar -cf - -T $OUT/02_real_core.list | $Z -o $OUT/02_real_core.tar.zst ;;
02b) step "02b_real_rest"
  ls -d gs_blender/real_* | grep -v '\.zip$' | sort -u | grep -v -x -F -f $OUT/02_real_core.list > $OUT/02b_real_rest.list
  tar -cf - -T $OUT/02b_real_rest.list | $Z -o $OUT/02b_real_rest.tar.zst ;;
03) step "03_sim_subset"
  for u in gs_blender/renders_v3/pattern_*/session_*; do echo $u/session.json
    for s in calibration parameters.txt raw_data rgb norms dmaps samples_a_k25 samples_bc_loo samples_bc_k25; do [ -e $u/sensor_0000/$s ] && echo $u/sensor_0000/$s; done; done > $OUT/03_sim_subset.list
  tar -cf - -T $OUT/03_sim_subset.list | $Z -o $OUT/03_sim_subset.tar.zst ;;
esac; done
step "done"; ls -la $OUT/*.tar.zst | awk '{printf "%.1f GB  %s\n", $5/1e9, $9}'; (cd $OUT && sha256sum *.tar.zst > SHA256SUMS)
