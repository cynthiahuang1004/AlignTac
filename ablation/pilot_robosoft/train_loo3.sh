#!/bin/bash
# Train one new-object student and evaluate it on the held-out TEST frames.  usage: train_loo3.sh <gpu> <variant: al|tp|oracle> [train yaml]
GPU=$1; V=$2; T=${3:-ablation/pilot_robosoft/train_pilot_e150.yaml}; cd /media/hdd2/ihsuan/VisTacFusion/AlignTac
export CUDA_VISIBLE_DEVICES=$GPU PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
G=/media/hdd2/ihsuan/gs_blender; L=outputs/rss_logs; PY="conda run --no-capture-output -n vistacfusion python"; P=ablation/pilot_robosoft
M=ablation/encoder/tac_sitr_single.yaml; R=A_loo3_$V; OUT=runs/pilot150_$R
step() { echo "$(date '+%m-%d %H:%M') [loo3 $V] $*"; }
step "train $R on GPU $GPU"
$PY -m vistacfusion.engine.train --model $M --train $T --data $P/data_$R.yaml --output-dir $OUT > $L/150ep_$R.log 2>&1 || { step "train FAILED"; tail -5 $L/150ep_$R.log; exit 1; }
step "evaluate on real_loo3_test"
for ck in best_depth.pt best_pose.pt; do tag=loo3test; [ $ck = best_pose.pt ] && tag=loo3test_bp
  $PY $P/eval_cross_session.py --device cuda:0 --batch 16 --ckpt $ck --json $P/loo3_results.json --root $G/real_loo3_test --tag $tag $R:pilot150_ 2>&1 | grep -v Warning
done
step "done"
