#!/bin/bash
# Train one student and evaluate it.  usage: rss2_train.sh <prefix> <run> <eval: testA|loo3|s2half|none> [extra train args]
#   run dir = runs/<prefix><run> (new dirs live on /media/hdd2/users/ihsuan/AlignTac_runs, symlinked into runs/);
#   data config = ablation/pilot_robosoft/data_<run without _seedN>.yaml; train yaml = train_pilot_e150_pm[_seedN].yaml
#   (override with TRAIN_YAML=...).  CUDA_VISIBLE_DEVICES is set by the caller (rss2_queue.py).
PRE=$1; RUN=$2; EV=${3:-testA}; shift 3
cd /media/hdd/ihsuan/VisTacFusion/AlignTac
export PYTHONPATH=/media/hdd/ihsuan/VisTacFusion/AlignTac   # scripts run as files must import the SAME package snapshot the training used
G=/media/hdd/ihsuan/gs_blender; L=outputs/rss_logs; PY=${PY:-conda run --no-capture-output -n vistacfusion python -u}; P=ablation/pilot_robosoft   # PY="python -u" on Colab / a local machine
M=${MODEL_YAML:-ablation/encoder/tac_sitr_single.yaml}
BASE=$(echo $RUN | sed -E 's/(_seed[0-9]+)+$//'); SEED=$(echo $RUN | grep -oE '_seed[0-9]+$')
T=${TRAIN_YAML:-$P/train_pilot_e150_pm$SEED.yaml}; D=${DATA_YAML:-$P/data_$BASE.yaml}
OUT=runs/$PRE$RUN
OVER=${RUNS_DIR:-/media/hdd2/users/ihsuan/AlignTac_runs}; [ -d $OVER ] || OVER=/media/hdd-slam/users/ihsuan/AlignTac_runs   # the 20T overflow disk changes mount point across reboots
if [ ! -e $OUT ]; then mkdir -p $OVER/$PRE$RUN && ln -s $OVER/$PRE$RUN $OUT; fi
step() { echo "$(date '+%m-%d %H:%M') [$PRE$RUN] $*"; }
# NOTE: never edit this file in place while jobs run (bash reads scripts incrementally); replace it atomically (write tmp + mv).
if [ -f $OUT/final.pt ] && [ ! -f $OUT/.train_done ]; then touch $OUT/.train_done; fi   # training finished earlier (e.g. post-step garbled)
if [ ! -f $OUT/.train_done ]; then
  step "train (data $D, train $T, gpu $CUDA_VISIBLE_DEVICES)"
  $PY -m vistacfusion.engine.train --model $M --train $T --data $D --output-dir $OUT "$@" > $L/$PRE$RUN.log 2>&1 || { step "train FAILED"; tail -5 $L/$PRE$RUN.log; exit 1; }
  touch $OUT/.train_done
fi
ev() {  # ev <root> <tag> <json>
  for ck in best_depth.pt best_pose.pt; do tag=$2; [ $ck = best_pose.pt ] && tag=$2_bp
    flock outputs/rss_logs/eval.lock $PY $P/eval_cross_session.py --device cuda:0 --batch 16 --ckpt $ck --json $3 --root $1 --tag $tag --model $M $RUN:$PRE 2>&1 | grep -v Warning | tail -1
  done; }
case $EV in
  testA)  ev $G/real_filtered_testA testA $P/rss2_testA_results.json ;;
  loo3)   ev $G/real_loo3_test loo3test $P/loo3_results.json ;;
  f2)     ev $G/real_f2_test f2test $P/f2_results.json ;;
  s2half) ev $G/real_s2_testhalf s2half $P/rss2_cross_session_results.json; ev $G/real_filtered_testA testA $P/rss2_testA_results.json ;;
  kin)    ev $G/real_filtered_kin_testA testA $P/rss2_kin_testA_results.json; ev $G/real_s2_kin_all s2kin $P/rss2_kin_s2_results.json ;;   # corrected labels (D8-D10)
  s2all)  ev $G/real_s2_testhalf s2half $P/rss2_cross_session_results.json; ev $G/real_filtered_testA testA $P/rss2_testA_results.json ;;
esac
step "done"
