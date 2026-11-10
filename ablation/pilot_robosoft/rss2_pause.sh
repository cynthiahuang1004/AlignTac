#!/bin/bash
# Pause / resume training jobs (SIGSTOP / SIGCONT on the trainer and its dataloader workers) to prioritize GPU time.
# usage: rss2_pause.sh pause|resume <run dir name> ...     e.g. rss2_pause.sh pause rss2_T_k25_rf_conf75
sig=STOP; [ "$1" = resume ] && sig=CONT; shift
me=$(id -un)
for r in "$@"; do
  for pid in $(ps -u $me -o pid,args | grep "engine.train" | grep -- "--output-dir runs/$r\b" | grep -v grep | awk '{print $1}'); do
    pkill -$sig -P $pid 2>/dev/null; kill -$sig $pid 2>/dev/null && echo "$sig $r ($pid)"
  done
done
