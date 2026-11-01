#!/bin/bash
# New-object labeling chain (held-out objects pattern_04_3_lines_angle_2, pattern_31_rod, pattern_33):
#   teacher labels (pseudo_label.py, already running/finished) -> aligned mesh labels with the 9-object aligner
#   -> mesh at the teacher pose (control) -> merged training roots + data configs.   usage: chain_loo3.sh <gpu>
GPU=${1:-0}; cd /media/hdd2/ihsuan/VisTacFusion/AlignTac
export CUDA_VISIBLE_DEVICES=$GPU PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
G=/media/hdd2/ihsuan/gs_blender; L=outputs/rss_logs; PY="conda run --no-capture-output -n vistacfusion python"; P=ablation/pilot_robosoft
HELD="pattern_04_3_lines_angle_2 pattern_31_rod pattern_33"
step() { echo "$(date '+%m-%d %H:%M') [loo3] $*"; }
until grep -q '"val_links"\|"iou_median"' $L/pseudo_loo3_ng.log 2>/dev/null; do sleep 30; done
until [ -f outputs/aligner_loo9/aligner.pt ]; do sleep 30; done
step "aligned mesh labels (aligner_loo9)"
$PY scripts/tactile_render/pseudo_label_rc.py --src-root $G/real_pseudo_loo3_ng --real-root $G/real_loo3 --run A_bgcondloo --prefix pilot150_ \
   --gan outputs/tactile_gan_loo --aligner outputs/aligner_loo9/aligner.pt --out-root $G/real_pseudo_loo3_al --keep-frac 1.0 --pose-all --eval-gt \
   --device cuda:0 > $L/pseudo_loo3_al.log 2>&1 || { step "rc al FAILED"; tail -3 $L/pseudo_loo3_al.log; exit 1; }
grep -A6 "^labels" $L/pseudo_loo3_al.log
step "mesh at the teacher pose (control)"
$PY scripts/tactile_render/pseudo_label_rc.py --src-root $G/real_pseudo_loo3_ng --real-root $G/real_loo3 --run A_bgcondloo --prefix pilot150_ \
   --gan outputs/tactile_gan_loo --aligner outputs/aligner_loo9/aligner.pt --aligner-iters 0 --out-root $G/real_pseudo_loo3_tp --keep-frac 1.0 --pose-all --eval-gt \
   --device cuda:0 > $L/pseudo_loo3_tp.log 2>&1 || { step "rc tp FAILED"; tail -3 $L/pseudo_loo3_tp.log; exit 1; }
grep -A6 "^labels" $L/pseudo_loo3_tp.log
merge() {  # merge <held-out root> <out root>: 9 seen objects from real_filtered + 3 held-out objects from $1
  rm -rf $2; for o in $G/real_filtered/pattern_*; do n=$(basename $o); mkdir -p $2/$n
    src=$o; case " $HELD " in *" $n "*) src=$1/$n;; esac
    for s in $src/session_*; do [ -d "$s" ] && ln -s $s $2/$n/$(basename $s); done; done; }
merge $G/real_pseudo_loo3_al $G/real_loo3_merge_al
merge $G/real_pseudo_loo3_tp $G/real_loo3_merge_tp
merge $G/real_filtered       $G/real_loo3_merge_oracle
for v in al tp oracle; do
  $PY - "$v" <<'PYEOF'
import sys, yaml
v = sys.argv[1]; P = "ablation/pilot_robosoft"
c = yaml.safe_load(open(f"{P}/data_A_bgcondloo.yaml"))
c["real"].pop("test_objects", None)
c["real"]["root"] = f"/media/hdd2/ihsuan/gs_blender/real_loo3_merge_{v}"
c["real"]["exclude_frames"] = f"{P}/loo3_test_frames.json"
yaml.safe_dump(c, open(f"{P}/data_A_loo3_{v}.yaml", "w"), sort_keys=False)
print("wrote", f"{P}/data_A_loo3_{v}.yaml")
PYEOF
done
step "roots and configs ready"
