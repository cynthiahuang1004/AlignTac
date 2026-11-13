#!/bin/bash
# New-object study, second held-out fold (same pipeline as fold 1 = chain_loo3.sh + rss2_loo3_obsf_roots.sh, other objects).
# usage: rss2_fold.sh <A|B> [ignored marker args]      (queue job; CUDA_VISIBLE_DEVICES is set by rss2_queue.py; every step is skipped if done)
#   A: bg-conditioned renderer without the held-out objects -> sim renderings -> teacher -> teacher labels -> aligned labels (9-object
#      aligner from chain B) -> mesh-only onboarded aligner -> observability-aware fusion -> label roots, merged roots, configs -> students queued
#   B: plain renderer without the held-out objects -> 9-object aligner -> lower-bound student (Labeled only, 9 objects)
# Split roots and the teacher / lower-bound configs come from rss2_make_fold.py (run once, before queuing).
F=f2; HELD="pattern_01_2_lines_angle_1_2 pattern_32 pattern_35"; C=$1
cd /media/hdd/ihsuan/VisTacFusion/AlignTac; export PYTHONPATH=/media/hdd/ihsuan/VisTacFusion/AlignTac PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
G=/media/hdd/ihsuan/gs_blender; L=outputs/rss_logs; P=ablation/pilot_robosoft; S=scripts/tactile_render; J=$L/rss2_jobs_b.tsv
PY="conda run --no-capture-output -n vistacfusion python -u"
step() { echo "$(date '+%m-%d %H:%M') [$F chain $C] $*" >> $L/rss2_${F}_chain.log; }
fail() { step "FAILED: $*"; exit 1; }
exec 9> $L/rss2_${F}_chain$C.lock; flock -n 9 || { step "another instance is running, leaving"; exit 0; }
X="--k 0 --gan outputs/tactile_gan_loo_$F --exclude-objects $HELD --device cuda:0"
rc() { $PY $S/pseudo_label_rc.py --src-root $G/real_pseudo_${F}_ng --real-root $G/real_$F --run A_${F}_teacher --prefix rss2_ --gan outputs/tactile_gan_loo_$F \
         --keep-frac 1.0 --pose-all --eval-gt "$@"; }
merge() {  # merge <variant> <root holding the held-out objects>: seen objects from real_filtered + held-out objects from $2; config for the student
  local M=$G/real_${F}_merge_$1
  if [ ! -d $M ]; then for o in $G/real_filtered/pattern_*; do n=$(basename $o); mkdir -p $M/$n
      src=$o; case " $HELD " in *" $n "*) src=$2/$n;; esac
      for s in $src/session_*; do [ -d "$s" ] && ln -s $s $M/$n/$(basename $s); done; done; fi
  [ -f $P/data_A_${F}_$1.yaml ] || $PY - "$1" "$F" <<'PYEOF'
import sys, yaml
v, F = sys.argv[1], sys.argv[2]; P = "ablation/pilot_robosoft"
c = yaml.safe_load(open(f"{P}/data_A_{F}_teacher.yaml"))
c["real"].pop("test_objects", None)
c["real"]["root"] = f"/media/hdd/ihsuan/gs_blender/real_{F}_merge_{v}"
c["real"]["exclude_frames"] = f"{P}/{F}_test_frames.json"
yaml.safe_dump(c, open(f"{P}/data_A_{F}_{v}.yaml", "w"), sort_keys=False)
PYEOF
  step "merged root + config: $1 ($(find -L $M -name '*_gt.npy' | wc -l) label files)"
}

case $C in
B)
  if [ ! -f outputs/tactile_gan_loo_$F/G_final.pt ]; then step "renderer without the held-out objects"
    $PY $S/train_tactile_gan.py --out outputs/tactile_gan_loo_$F --device cuda:0 --epochs 250 --exclude-objects $HELD > $L/gan_loo_$F.log 2>&1 || fail "renderer"; fi
  if [ ! -f outputs/aligner_${F}_loo9/aligner.pt ]; then step "aligner on the 9 seen objects"
    $PY $S/train_aligner.py $X --out outputs/aligner_${F}_loo9 > $L/aligner_${F}_loo9.log 2>&1 || fail "aligner"; fi
  step "lower-bound student (Labeled only, 9 objects)"
  TRAIN_YAML=$P/train_pilot_e150.yaml bash $P/rss2_train.sh rss2_ A_${F}_realonly $F >> $L/rss2_train.log 2>&1 || fail "lower-bound student"
  ;;
A)
  if [ ! -f outputs/tactile_gan_bgcond_loo_$F/G_final.pt ]; then step "bg-conditioned renderer without the held-out objects"
    $PY $S/train_tactile_gan.py --bg-cond --out outputs/tactile_gan_bgcond_loo_$F --device cuda:0 --epochs 250 --exclude-objects $HELD > $L/gan_bgcond_loo_$F.log 2>&1 || fail "bg-cond renderer"; fi
  if ! grep -q '^done' $L/gen_bc_loo_$F.log 2>/dev/null; then step "sim renderings samples_bc_loo_$F"
    OBJS=$($PY -c "import yaml;print(' '.join(yaml.safe_load(open('$P/data_A_${F}_teacher.yaml'))['sim']['include_objects']))")
    $PY $S/generate_tactile.py --bg-cond --ckpt outputs/tactile_gan_bgcond_loo_$F/G_final.pt --device cuda:0 --out-subdir samples_bc_loo_$F --objects $OBJS > $L/gen_bc_loo_$F.log 2>&1 || fail "sim renderings"; fi
  step "teacher"
  TRAIN_YAML=$P/train_pilot_e150.yaml bash $P/rss2_train.sh rss2_ A_${F}_teacher $F >> $L/rss2_train.log 2>&1 || fail "teacher"
  if [ ! -f $G/real_pseudo_${F}_ng/pseudo_manifest.json ]; then step "teacher labels"
    $PY $S/pseudo_label.py --run A_${F}_teacher --prefix rss2_ --k 25 --real-root $G/real_$F --out-root $G/real_pseudo_${F}_ng --device cuda:0 --pose --unlabeled-only --iou-thr 0 \
       > $L/pseudo_${F}_ng.log 2>&1 || fail "teacher labels"; fi
  for i in $(seq 360); do [ -f outputs/aligner_${F}_loo9/aligner.pt ] && break; sleep 60; done; [ -f outputs/aligner_${F}_loo9/aligner.pt ] || fail "9-object aligner missing (chain B)"
  if [ ! -f $G/real_pseudo_${F}_al/pseudo_manifest.json ]; then step "aligned mesh labels (9-object aligner)"
    rc --aligner outputs/aligner_${F}_loo9/aligner.pt --out-root $G/real_pseudo_${F}_al --device cuda:0 > $L/pseudo_${F}_al.log 2>&1 || fail "rc al"; fi
  if [ ! -f $G/real_pseudo_${F}_tp/pseudo_manifest.json ]; then step "mesh at the teacher pose (control)"
    rc --aligner outputs/aligner_${F}_loo9/aligner.pt --aligner-iters 0 --out-root $G/real_pseudo_${F}_tp --device cuda:0 > $L/pseudo_${F}_tp.log 2>&1 || fail "rc tp"; fi
  if [ ! -f outputs/aligner_${F}_syn3_r2/aligner.pt ]; then step "onboarding: pose ranges from the teacher's predictions, aligner with synthetic frames of the new meshes (2x range)"
    $PY - "$F" <<'PYEOF' >> $L/aligner_${F}_syn3_r2.ranges.log 2>&1 || fail "pose ranges"
import collections, json, math, os, sys
import numpy as np
F = sys.argv[1]; G = '/media/hdd/ihsuan/gs_blender'; f = json.load(open(f'{G}/real_pseudo_{F}_al/rc_fits.json')); src = f'{G}/real_pseudo_{F}_ng'
by = collections.defaultdict(list)
for tac, v in f.items():      # teacher pose (tp) and teacher depth only: no label of the new objects
    unit = os.path.dirname(os.path.dirname(tac)); idx = os.path.basename(tac)[:4]; obj = unit.split('/')[-3]
    dep = os.path.join(unit.replace(f'{G}/real_{F}', src), 'raw_data', idx + '_gt.npy')
    by[obj].append(list(v['tp']) + [float(np.clip(np.load(dep).max() * 1000, 0.3, 1.6))])
out = {}
for o, v in by.items():
    v = np.array(v); m = np.array([math.radians(10), 1.0, 1.0, 0.05])
    lo = np.percentile(v, 2, axis=0) - m; hi = np.percentile(v, 98, axis=0) + m; out[o] = [lo.tolist(), hi.tolist()]
    print(o, len(v), 'theta deg [%.0f, %.0f] x [%.1f, %.1f] y [%.1f, %.1f] p [%.2f, %.2f]' % (math.degrees(lo[0]), math.degrees(hi[0]), lo[1], hi[1], lo[2], hi[2], lo[3], hi[3]))
os.makedirs(f'outputs/aligner_{F}_syn3_r2', exist_ok=True); json.dump(out, open(f'outputs/aligner_{F}_syn3_r2/synth_ranges.json', 'w'), indent=1)
PYEOF
    $PY $S/train_aligner.py $X --synth-ranges outputs/aligner_${F}_syn3_r2/synth_ranges.json --synth-weight 3 --range-scale 2.0 --out outputs/aligner_${F}_syn3_r2 \
       > $L/aligner_${F}_syn3_r2.log 2>&1 || fail "onboarded aligner"; fi
  mkdir -p outputs/rss2_fits/$F
  if [ ! -f outputs/rss2_fits/$F/fits_obsf_loo9.json ]; then step "observability-aware fusion, 9-object aligner"
    $PY $P/rss2_obs_fusion.py --al-root $G/real_pseudo_${F}_al --real-root $G/real_$F --workers 12 --device cpu --n-touches 5,10,20 \
       --write-fits outputs/rss2_fits/$F/fits_obsf_loo9.json --out $P/rss2_obsfusion_${F}_loo9.json > $L/rss2_obsfusion_${F}_loo9.log 2>&1 || fail "fusion loo9"; fi
  if [ ! -f outputs/rss2_fits/$F/fits_obsf_syn3_r2.json ]; then step "observability-aware fusion, onboarded aligner"
    $PY $P/rss2_obs_fusion.py --al-root $G/real_pseudo_${F}_al --real-root $G/real_$F --workers 12 --device cpu --n-touches 5,10,20 --aligner outputs/aligner_${F}_syn3_r2/aligner.pt --range-scale 2.0 \
       --write-fits outputs/rss2_fits/$F/fits_obsf_syn3_r2.json --out $P/rss2_obsfusion_${F}_syn3_r2.json > $L/rss2_obsfusion_${F}_syn3_r2.log 2>&1 || fail "fusion syn3_r2"; fi
  for a in obsf=fits_obsf_syn3_r2.json obsf9=fits_obsf_loo9.json syn=fits_obsf_syn3_r2_pertouch.json; do v=${a%%=*}; f=outputs/rss2_fits/$F/${a#*=}
    [ -f $G/real_pseudo_${F}_$v/pseudo_manifest.json ] || rc --fits $f --out-root $G/real_pseudo_${F}_$v --device cpu > $L/pseudo_${F}_$v.log 2>&1 || fail "root $v"
  done
  for v in al tp syn obsf9 obsf; do merge $v $G/real_pseudo_${F}_$v; done
  merge oracle $G/real_filtered
  for v in al tp syn obsf9 obsf; do step "labels $v: $(grep -v Warn $L/pseudo_${F}_$v.log | grep '^mesh (kept)')"; done
  if ! grep -q "^rss2_A_${F}_obsf	" $J; then
    for r in obsf syn al oracle tp obsf9 obsf_seed1 obsf_seed2 syn_seed1 syn_seed2 al_seed1 al_seed2 oracle_seed1 oracle_seed2; do
      printf 'rss2_A_%s_%s\tbash ablation/pilot_robosoft/rss2_train.sh rss2_ A_%s_%s %s >> outputs/rss_logs/rss2_train.log 2>&1\n' $F $r $F $r $F; done >> $J
    step "14 students appended to $J"; fi
  ;;
esac
step "done"; echo "$(date '+%m-%d %H:%M') [rss2_${F}_chain$C] done" >> $L/rss2_train.log
