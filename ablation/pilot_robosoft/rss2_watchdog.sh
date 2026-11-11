#!/bin/bash
# Keeps the round-2 job queue and the finisher loop alive (checks every 2 min, restarts whichever is missing).
# The queue itself polls the GPUs every 30 s and starts the next job as soon as one has room.
# stop: touch outputs/rss_logs/rss2_watchdog.stop      (the queue has its own stop file: <jobs>.stop)
cd /media/hdd/ihsuan/VisTacFusion/AlignTac
J=outputs/rss_logs/rss2_jobs_b.tsv; L=outputs/rss_logs; CONDA=/home/shared/miniconda3/bin/conda
while [ ! -f $L/rss2_watchdog.stop ]; do
  A=$(ps -u $(id -u) -o args)
  if ! echo "$A" | grep -q "rss2_queue.py --jobs $J" && [ ! -f $J.stop ]; then
    echo "$(date '+%m-%d %H:%M') queue not running: restarting" >> $L/rss2_watchdog.log
    setsid nohup $CONDA run --no-capture-output -n vistacfusion python -u ablation/pilot_robosoft/rss2_queue.py --jobs $J --gpus 0,1,2,3 --per-gpu 4 --min-free 7500 >> $L/rss2_queue_b.log 2>&1 &
  fi
  if ! echo "$A" | grep -q "rss2_finisher.sh"; then
    echo "$(date '+%m-%d %H:%M') finisher not running: restarting" >> $L/rss2_watchdog.log
    setsid nohup bash -c "while true; do bash ablation/pilot_robosoft/rss2_finisher.sh 1 >> $L/rss2_finisher.log 2>&1; sleep 600; done" > /dev/null 2>&1 &
  fi
  sleep 120
done
