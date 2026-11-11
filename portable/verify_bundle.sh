#!/bin/bash
# Server-side check of a bundle: extract it to a scratch folder and run portable/verify_data.py in a mount namespace where
# /media/hdd/ihsuan is ONLY the extracted bundle and the original project folder is hidden.   usage: verify_bundle.sh <bundle dir> <scratch dir>
B=$1; V=$2; mkdir -p $V
for a in 01_code 02_real_core 03_sim_subset; do [ -f $V/.done_$a ] || { echo "$(date '+%m-%d %H:%M') extracting $a"; zstd -dc -T8 $B/$a.tar.zst | tar -x -C $V && touch $V/.done_$a; }; done
echo "$(date '+%m-%d %H:%M') extracted: $(du -sh $V | cut -f1)"
bwrap --dev-bind / / --bind $V /media/hdd/ihsuan --tmpfs /media/hdd2/ihsuan --chdir /media/hdd/ihsuan/VisTacFusion/AlignTac \
  env CUDA_VISIBLE_DEVICES= /home/shared/miniconda3/envs/vistacfusion/bin/python -u portable/verify_data.py 2>&1 | grep -v "Warning\|warn"
