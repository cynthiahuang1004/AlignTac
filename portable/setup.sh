#!/bin/bash
# Make a machine (Colab, WSL2 or Linux) look like the server for the AlignTac code.
# usage: bash setup.sh <dir with the *.tar.zst archives> <extract dir> [archives ...]     (default archives: 01_code 02_real_core 03_sim_subset)
# All configs, dataset manifests and ~600k symlinks use absolute paths under /media/hdd/ihsuan, so the bundle is extracted to
# <extract dir> and /media/hdd/ihsuan is made a symlink to it (needs root: Colab is root; locally the script calls sudo once).
set -e
SRC=$1; DST=$2; shift 2; ARCH=${@:-01_code 02_real_core 03_sim_subset}
command -v zstd >/dev/null || { (apt-get -qq update && apt-get -qq install -y zstd) || sudo apt-get install -y zstd; }
mkdir -p $DST
for a in $ARCH; do
  if [ -f $DST/.done_$a ]; then echo "$a already extracted"; continue; fi
  echo "extracting $a ..."; cat $SRC/$a.tar.zst* | zstd -dc -T0 | tar -x -C $DST && touch $DST/.done_$a
done
SUDO=""; [ "$(id -u)" = 0 ] || SUDO=sudo
if [ "$(readlink -f /media/hdd/ihsuan 2>/dev/null)" != "$(readlink -f $DST)" ]; then
  [ -e /media/hdd/ihsuan ] && [ ! -L /media/hdd/ihsuan ] && { echo "/media/hdd/ihsuan exists and is not a symlink: refusing to touch it"; exit 1; }
  $SUDO mkdir -p /media/hdd && $SUDO ln -sfn $(readlink -f $DST) /media/hdd/ihsuan
fi
python -c "import timm, trimesh, omegaconf, cv2, skimage" 2>/dev/null || pip -q install -r /media/hdd/ihsuan/VisTacFusion/AlignTac/portable/requirements.txt
mkdir -p /media/hdd/ihsuan/VisTacFusion/AlignTac/runs /media/hdd/ihsuan/VisTacFusion/AlignTac/outputs/rss_logs
echo "ready: /media/hdd/ihsuan -> $(readlink -f /media/hdd/ihsuan);  cd /media/hdd/ihsuan/VisTacFusion/AlignTac"
