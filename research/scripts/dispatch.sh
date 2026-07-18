#!/bin/bash
# dispatch.sh — Scheduler for remote dl4080 (RTX 4080 12GB) and local 5090 (24GB)
# Usage:
#   bash research/scripts/dispatch.sh <target> <command...>
# Targets:
#   local | 5090     — run directly on this machine (current workspace)
#   remote | 4080    — ssh to dl4080, robust conda activation, optional code rsync
#   both             — run the command on both (sequential for now; background where safe)
#
# Examples for GAP-FIX plan:
#   # Extract MD cases locally (CPU)
#   bash research/scripts/dispatch.sh local 'python research/scripts/extract_md_cases.py'
#
#   # Run a small MD feasibility test on the constrained 12GB remote
#   bash research/scripts/dispatch.sh 4080 'cd ~/materials-mlip-research; python research/mt_gpu_md_test.py --n-structures 5'
#
#   # Multi-seed calibration red-team on local 5090 (fast iteration)
#   bash research/scripts/dispatch.sh 5090 'python research/scripts/run_calib_redteam.py --seeds 10'
#
#   # Rsync latest code + run analysis on remote data (for cases where remote has fresher ~/mt_uip)
#   bash research/scripts/dispatch.sh 4080 --rsync 'python -c "import pandas as pd; print(\"remote data OK\")"'
#
# Notes:
# - Remote activation tries common conda init locations + bash -l.
# - For GPU tasks (MD), remote proves the original 12GB gate; local 5090 used for larger/faster runs.
# - Always capture logs: redirect or use the wrapper.
# - Update GAP-FIX plan after runs.

set -euo pipefail

TARGET="${1:-}"
shift || true

if [[ -z "$TARGET" ]]; then
  echo "Usage: $0 <local|5090|remote|4080|both> [--rsync] <command...>"
  echo "See top of file for GAP-FIX examples."
  exit 1
fi

RSYNC_FIRST=false
if [[ "${1:-}" == "--rsync" ]]; then
  RSYNC_FIRST=true
  shift
fi

COMMAND="$*"
WORKSPACE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REMOTE_HOST="dl4080"
REMOTE_PROJECT_HINT="~/materials-mlip-research"

log() { echo "[$(date '+%H:%M:%S')] [dispatch:$TARGET] $*"; }

run_local() {
  log "Running on LOCAL 5090 (workspace: $WORKSPACE_ROOT)"
  cd "$WORKSPACE_ROOT"
  # Prefer 'dl' env if present, else current
  if command -v conda >/dev/null 2>&1; then
    conda activate dl 2>/dev/null || true
  fi
  eval "$COMMAND"
}

run_remote() {
  local cmd="$1"
  log "Running on REMOTE 4080 ($REMOTE_HOST)"

  if $RSYNC_FIRST; then
    log "Rsyncing research/ code to remote (creating project dir if needed)..."
    ssh "$REMOTE_HOST" "mkdir -p $REMOTE_PROJECT_HINT" || true
    rsync -az --delete \
      --include='research/scripts/**' \
      --include='research/*.py' \
      --include='research/redteam/**' \
      --include='research/figures/**' \
      --exclude='__pycache__' \
      --exclude='*.pyc' \
      --exclude='.git' \
      "$WORKSPACE_ROOT/research/" \
      "$REMOTE_HOST:$REMOTE_PROJECT_HINT/research/" || log "rsync warning (continuing)"
  fi

  # Robust remote activation (non-interactive ssh)
  # Try bash -l (loads profile), then explicit conda init paths.
  ssh "$REMOTE_HOST" '
    set -euo pipefail
    # Load profile / conda
    if [ -f ~/.bashrc ]; then source ~/.bashrc 2>/dev/null || true; fi
    for init in \
      "$HOME/miniconda3/etc/profile.d/conda.sh" \
      "$HOME/anaconda3/etc/profile.d/conda.sh" \
      "$HOME/.conda/etc/profile.d/conda.sh" \
      "/opt/conda/etc/profile.d/conda.sh" \
      "/opt/miniconda3/etc/profile.d/conda.sh"; do
      if [ -f "$init" ]; then
        source "$init" 2>/dev/null || true
        break
      fi
    done
    # Activate common envs
    conda activate dl 2>/dev/null || conda activate base 2>/dev/null || true

    # Go to project if it exists after rsync, else stay in ~
    if [ -d '"$REMOTE_PROJECT_HINT"' ]; then
      cd '"$REMOTE_PROJECT_HINT"'
    fi

    echo "[remote] conda env: ${CONDA_DEFAULT_ENV:-unknown}"
    echo "[remote] python: $(python -c \"import sys; print(sys.executable)\" 2>/dev/null || echo no-python)"
    python -c "
import torch, sys
if torch.cuda.is_available():
    print(\"[remote] GPU:\", torch.cuda.get_device_name(0))
    print(\"[remote] VRAM total (MiB):\", round(torch.cuda.get_device_properties(0).total_memory/1024/1024))
else:
    print(\"[remote] CUDA not available\")
" 2>/dev/null || echo "[remote] torch check failed"

    '"$cmd"'
  '
}

case "$TARGET" in
  local|5090)
    run_local
    ;;
  remote|4080)
    run_remote "$COMMAND"
    ;;
  both)
    log "=== Running on LOCAL first ==="
    run_local || true
    log "=== Running on REMOTE ==="
    run_remote "$COMMAND" || true
    log "=== both done ==="
    ;;
  *)
    echo "Unknown target: $TARGET (use local|5090|remote|4080|both)"
    exit 1
    ;;
esac
