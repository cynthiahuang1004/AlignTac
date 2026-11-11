#!/bin/bash
# One-time setup on a local machine: Ubuntu, or Windows through WSL2 (Ubuntu inside Windows).  Native Windows is not supported:
# the data set is ~600k symlinks with absolute Linux paths and the job scripts are bash.
# usage: bash setup_local.sh <dir with the *.tar.zst archives> [extract dir, default ~/aligntac]
# It (1) checks the GPU and the archives, (2) creates a conda env "aligntac" identical to the server's (python 3.11, torch 2.5.1+cu121),
# (3) extracts 01_code, 02_real_core, 03_sim_subset and points /media/hdd/ihsuan at them (asks for the sudo password once).
# Safe to re-run: finished steps are skipped.
set -e
[ -n "$1" ] || { echo "usage: bash setup_local.sh <dir with the archives> [extract dir]"; exit 1; }
SRC=$(readlink -f "$1"); DST=$(readlink -m "${2:-$HOME/aligntac}")
case "$DST/" in /mnt/[a-z]/*) echo "The extract dir must be inside the Linux file system (for example ~/aligntac), not a Windows drive (/mnt/c ...):"; echo "Windows drives do not keep the symlinks and are several times slower."; exit 1;; esac
for a in 01_code 02_real_core 03_sim_subset; do [ -f "$SRC/$a.tar.zst" ] || { echo "missing $SRC/$a.tar.zst"; exit 1; }; done
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || { echo "nvidia-smi does not work.  On Windows: install the current NVIDIA driver in Windows (not inside WSL), then run 'wsl --update' and 'wsl --shutdown' in PowerShell."; exit 1; }
need=75; free=$(df -BG --output=avail "$(dirname "$DST")" | tail -1 | tr -dc 0-9)
[ "$free" -ge $need ] || { echo "only ${free} GB free at $(dirname "$DST"); about ${need} GB are needed (60 GB data, 7 GB environment, 2 GB of checkpoints per student)"; exit 1; }
if [ -f "$SRC/SHA256SUMS" ] && [ ! -f "$SRC/.sha_ok" ]; then
  echo "checking the archives (a few minutes) ..."; (cd "$SRC" && grep -E " (01_code|02_real_core|03_sim_subset)\.tar\.zst$" SHA256SUMS | sha256sum -c -) && touch "$SRC/.sha_ok" 2>/dev/null || { echo "an archive is damaged or incomplete: copy it again"; exit 1; }
fi
command -v zstd >/dev/null || sudo apt-get install -y zstd
if ! command -v conda >/dev/null; then
  if [ ! -x "$HOME/miniforge3/bin/conda" ]; then
    echo "installing Miniforge to ~/miniforge3 ..."; wget -q -O /tmp/miniforge.sh "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh"; bash /tmp/miniforge.sh -b -p "$HOME/miniforge3"; "$HOME/miniforge3/bin/conda" init bash >/dev/null
  fi
  export PATH="$HOME/miniforge3/bin:$PATH"
fi
source "$(conda info --base)/etc/profile.d/conda.sh"
conda env list | grep -q "^aligntac " || conda create -y -q -n aligntac python=3.11
conda activate aligntac
python -c "import torch, torchvision; assert torch.__version__.startswith('2.5.1')" 2>/dev/null || pip install -q torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121
HERE=$(dirname "$(readlink -f "$0")")
pip install -q -r "$HERE/requirements_local.txt"      # pinned to the server versions, before setup.sh so that it finds them installed
bash "$HERE/setup.sh" "$SRC" "$DST"
python -c "import torch; assert torch.cuda.is_available(), 'torch does not see the GPU'; print('GPU:', torch.cuda.get_device_name(0), '| torch', torch.__version__)"
cat <<EOF

Setup finished.  Every new terminal:
  conda activate aligntac && cd /media/hdd/ihsuan/VisTacFusion/AlignTac
Then:
  python portable/verify_data.py                      # prints BUNDLE OK (about 5 min)
  python portable/run_jobs.py --bench                 # 3 min: speed, GPU memory, hours per student
  nohup python portable/run_jobs.py --jobs portable/jobs_local.tsv --parallel 1 --workers 6 > ~/aligntac_jobs.log 2>&1 &
  tail -f ~/aligntac_jobs.log outputs/rss_logs/rss2_A_loo3_syn_seed1.log
The archives in $SRC are no longer needed and can be deleted.
EOF
