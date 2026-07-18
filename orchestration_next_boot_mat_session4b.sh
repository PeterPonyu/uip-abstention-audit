#!/bin/bash
# Materials session #4b — roster repair pass (2026-07-10). Session 4 outcomes:
# data audit OK (json.bz2 loader), but ROSTER_mace-mp-0_FAILED (GitHub
# checkpoint download truncated without network_turbo -> corrupt torch zip)
# and ROSTER_orb-v3_FAILED (orb-models not importable in its venv — the
# VENV_orb_OK marker had trusted pip's exit code, not an import probe).
# This pass: network_turbo ON throughout; purge the corrupt MACE cache;
# reinstall orb-models gated on a REAL import; re-run only the missing
# roster models; then force-re-run oam+hull so Arm 1b's *_pred.csv
# auto-discovery sees the full roster.
set -uo pipefail
RELIABILITY_COMMONS="${RELIABILITY_COMMONS:-/root/reliability-commons}"
if [ -f "${RELIABILITY_COMMONS}/tools/boxkit/chain_lib.sh" ]; then
  # shellcheck disable=SC1091
  source "${RELIABILITY_COMMONS}/tools/boxkit/chain_lib.sh"
else
  chain_prologue() { :; }
  chain_epilogue() {
    echo "$2" >> "${CHAIN_LOG:-${L:-/root/chain.log}}"
    [ -f /root/NO_AUTOSHUTDOWN ] || shutdown -h now
  }
fi
source /root/miniconda3/etc/profile.d/conda.sh && conda activate base
export HF_HOME="${HF_HOME:-/root/autodl-tmp/hf-cache}"
source /etc/network_turbo >/dev/null 2>&1 || true
cd /root/materials-mlip-research
L="${MAT_LOG:-/root/mat_session4b.log}"
export CHAIN_LOG="$L"
chain_prologue
MT29="research/results/MT29"
export MT_DATA_ROOT="${MT_DATA_ROOT:-/root/mt_stage0/data}"
REFS="${OAM_REF_ENERGIES_JSON:-/root/autodl-tmp/ref_energies.json}"
export OAM_REF_ENERGIES_JSON="$REFS"
MIN_ROWS="${ROSTER_MIN_PREDICTIONS:-1000}"
PIP_IDX="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"

echo "[$(date)] MAT4B: purge-corrupt -> reinstall-orb -> roster gaps -> oam -> hull" >> "$L"

# --- 1. purge the corrupt MACE checkpoint cache (truncated zip) ---------------
find /root/.cache -path "*mace*" -name "*.model" -size -76M -print -delete >> "$L" 2>&1 || true
echo "MACE_CACHE_PURGED" >> "$L"

# --- 2. orb venv repair, gated on a REAL import (not pip exit code) -----------
if ! /root/venvs/orb/bin/python -c "import orb_models" >> "$L" 2>&1; then
  /root/venvs/orb/bin/pip install -q -i "$PIP_IDX" --force-reinstall orb-models >> "$L" 2>&1 || true
fi
if /root/venvs/orb/bin/python -c "import orb_models" >> "$L" 2>&1; then
  echo "ORB_IMPORT_OK" >> "$L"
else
  echo "ORB_IMPORT_FAILED (will be disclosed as roster gap)" >> "$L"
fi

# --- 3. roster gaps only (existing *_pred.csv are skipped) --------------------
declare -A MPY=( [mace-mp-0]="/root/venvs/mace/bin/python" [orb-v3]="/root/venvs/orb/bin/python" [mattersim]="/root/venvs/mattersim/bin/python" )
ROSTER_FAIL=0
for MODEL in mace-mp-0 orb-v3 mattersim; do
  OUT_CSV="${MT_UIP_ROOT:-$HOME/mt_uip}/$(echo "$MODEL" | tr '-' '_')_pred.csv"
  if [ ! -f "$OUT_CSV" ]; then
    "${MPY[$MODEL]}" "$MT29/mt29_uip_inference.py" --model "$MODEL" \
      --wbm-root "$MT_DATA_ROOT" --ref-energies-json "$REFS" >> "$L" 2>&1
  fi
  if [ -f "$OUT_CSV" ]; then
    N=$(python3 -c "import pandas as pd; print(len(pd.read_csv('$OUT_CSV')))" 2>/dev/null || echo 0)
  else
    N=0
  fi
  if [ "$N" -gt "$MIN_ROWS" ]; then
    echo "ROSTER_${MODEL}_OK rows=$N" >> "$L"
  else
    echo "ROSTER_${MODEL}_FAILED rows=$N" >> "$L"; ROSTER_FAIL=1
  fi
done
[ "$ROSTER_FAIL" -eq 0 ] && echo "ROSTER_ALL_OK" >> "$L" || echo "ROSTER_PARTIAL" >> "$L"

# --- 4. force oam+hull re-run so Arm 1b discovers the FULL pred roster --------
export OAM_MODEL="${OAM_MODEL:-sevennet-mf-ompa}"
rm -f "$MT29/mt29_stage1_oam_arm_result.json" "$MT29/mt29_hull_recompute_validation_result.json"
bash run_all_arms.sh oam >> "$L" 2>&1 && echo "OAM_OK" >> "$L" || echo "OAM_FAILED" >> "$L"
bash run_all_arms.sh hull >> "$L" 2>&1 && echo "HULL_OK" >> "$L" || echo "HULL_FAILED" >> "$L"

echo "MAT_SESSION4B_DONE" >> "$L"
chain_epilogue "$MT29 /root/mt_uip /root/mat_session4*.log" "MAT_SESSION4B_ALL_DONE" "mat_session4b"
