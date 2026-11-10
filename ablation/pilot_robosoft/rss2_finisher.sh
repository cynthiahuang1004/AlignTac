#!/bin/bash
# Safety net: evaluate every finished round-2 run that has no evaluation entry yet (covers jobs whose post-training step failed).
# Runs once per invocation; rss2_finisher_loop runs it every 10 min.  usage: rss2_finisher.sh [gpu]
GPU=${1:-0}; cd /media/hdd/ihsuan/VisTacFusion/AlignTac
export CUDA_VISIBLE_DEVICES=$GPU PYTHONPATH=/media/hdd/ihsuan/VisTacFusion/AlignTac
G=/media/hdd/ihsuan/gs_blender; P=ablation/pilot_robosoft; PY="conda run --no-capture-output -n vistacfusion python -u"; M=ablation/encoder/tac_sitr_single.yaml
has() { python3 -c "import json,sys; d=json.load(open('$1')) if __import__('os').path.exists('$1') else {}; sys.exit(0 if '$2' in d else 1)"; }
for d in runs/rss2_* runs/pilot150_A_loo3_*; do
  [ -f $d/final.pt ] || continue; name=$(basename $d); [ -f $d/.train_done ] || touch $d/.train_done
  case $name in pilot150_*) pre=pilot150_; run=${name#pilot150_};; *) pre=rss2_; run=${name#rss2_};; esac
  case $run in A_loo3*) root=$G/real_loo3_test; tag=loo3test; js=$P/loo3_results.json;; *_s2*) root=$G/real_s2_testhalf; tag=s2half; js=$P/rss2_cross_session_results.json;; *) root=$G/real_filtered_testA; tag=testA; js=$P/rss2_testA_results.json;; esac
  for ck in best_depth.pt best_pose.pt; do t=$tag; [ $ck = best_pose.pt ] && t=${tag}_bp
    has $js "$pre$run/$t" && continue
    echo "$(date '+%m-%d %H:%M') finisher: eval $name $ck -> $js/$t"
    flock outputs/rss_logs/eval.lock $PY $P/eval_cross_session.py --device cuda:0 --batch 16 --ckpt $ck --json $js --root $root --tag $t --model $M $run:$pre 2>&1 | grep -v Warning | tail -1
  done
  case $run in *_s2*) for ck in best_depth.pt best_pose.pt; do t=testA; [ $ck = best_pose.pt ] && t=testA_bp; has $P/rss2_testA_results.json "$pre$run/$t" && continue
    flock outputs/rss_logs/eval.lock $PY $P/eval_cross_session.py --device cuda:0 --batch 16 --ckpt $ck --json $P/rss2_testA_results.json --root $G/real_filtered_testA --tag $t --model $M $run:$pre 2>&1 | grep -v Warning | tail -1; done;; esac
done
