#!/bin/bash
# Materials session #4c — final roster repair (2026-07-10). Session 4b findings:
#   MACE: cached checkpoint is /root/.cache/mace/macempa0mediummodel — a
#     DOTLESS filename (so 4b's "*.model" purge missed it) truncated at exactly
#     20 MiB (proxy cut). mace_mp() never integrity-checks its cache. Fix:
#     purge the whole mace cache dir, download the checkpoint EXPLICITLY with
#     size + zip-CRC gates, pass it via --checkpoint.
#   ORB: orb-models 0.7.0 moved ORBCalculator to forcefield.inference.calculator
#     and the old adapter also hardcoded device='cpu' (days-of-compute bug).
#     Adapter now version-adaptive + cuda-auto (synced with this chain).
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
L="${MAT_LOG:-/root/mat_session4c.log}"
export CHAIN_LOG="$L"
chain_prologue
MT29="research/results/MT29"
export MT_DATA_ROOT="${MT_DATA_ROOT:-/root/mt_stage0/data}"
REFS="${OAM_REF_ENERGIES_JSON:-/root/autodl-tmp/ref_energies.json}"
export OAM_REF_ENERGIES_JSON="$REFS"
MIN_ROWS="${ROSTER_MIN_PREDICTIONS:-1000}"
MACE_CKPT_URL="${MACE_CKPT_URL:-https://github.com/ACEsuit/mace-mp/releases/download/mace_mpa_0/mace-mpa-0-medium.model}"
MACE_CKPT="${MACE_CKPT:-/root/autodl-tmp/checkpoints/mace-mpa-0-medium.model}"
MACE_CKPT_MIN_BYTES="${MACE_CKPT_MIN_BYTES:-70000000}"

echo "[$(date)] MAT4C: mace ckpt gated fetch -> roster gaps -> oam -> hull" >> "$L"

# --- 1. purge the ENTIRE mace cache dir (dotless-filename lesson) -------------
rm -rf /root/.cache/mace
echo "MACE_CACHE_DIR_PURGED" >> "$L"

# --- 2. explicit gated checkpoint fetch (3 attempts, size + zip CRC) ----------
mkdir -p "$(dirname "$MACE_CKPT")"
MACE_CKPT_OK=0
if [ -f "$MACE_CKPT" ] && [ "$(stat -c %s "$MACE_CKPT")" -ge "$MACE_CKPT_MIN_BYTES" ] \
   && python3 -m zipfile -t "$MACE_CKPT" >> "$L" 2>&1; then
  MACE_CKPT_OK=1
else
  for i in 1 2 3; do
    rm -f "$MACE_CKPT.partial"
    if curl -L --fail --connect-timeout 30 --max-time 3600 -o "$MACE_CKPT.partial" "$MACE_CKPT_URL" >> "$L" 2>&1; then
      BYTES=$(stat -c %s "$MACE_CKPT.partial")
      if [ "$BYTES" -ge "$MACE_CKPT_MIN_BYTES" ] && python3 -m zipfile -t "$MACE_CKPT.partial" >> "$L" 2>&1; then
        mv "$MACE_CKPT.partial" "$MACE_CKPT"
        MACE_CKPT_OK=1
        echo "MACE_CKPT_FETCH_OK attempt=$i bytes=$BYTES" >> "$L"
        break
      fi
      echo "MACE_CKPT_ATTEMPT_${i}_BAD bytes=${BYTES} (size/CRC gate)" >> "$L"
    else
      echo "MACE_CKPT_ATTEMPT_${i}_CURL_FAILED" >> "$L"
    fi
  done
fi
[ "$MACE_CKPT_OK" -eq 1 ] || echo "MACE_CKPT_FETCH_FAILED (mace will be a disclosed roster gap)" >> "$L"

# --- 3. roster gaps (existing *_pred.csv skipped; mattersim already OK) -------
declare -A MPY=( [mace-mp-0]="/root/venvs/mace/bin/python" [orb-v3]="/root/venvs/orb/bin/python" [mattersim]="/root/venvs/mattersim/bin/python" )
ROSTER_FAIL=0
for MODEL in mace-mp-0 orb-v3 mattersim; do
  OUT_CSV="${MT_UIP_ROOT:-$HOME/mt_uip}/$(echo "$MODEL" | tr '-' '_')_pred.csv"
  if [ ! -f "$OUT_CSV" ]; then
    EXTRA=()
    if [ "$MODEL" = "mace-mp-0" ]; then
      [ "$MACE_CKPT_OK" -eq 1 ] || { echo "ROSTER_${MODEL}_SKIPPED no valid checkpoint" >> "$L"; ROSTER_FAIL=1; continue; }
      EXTRA=(--checkpoint "$MACE_CKPT")
    fi
    "${MPY[$MODEL]}" "$MT29/mt29_uip_inference.py" --model "$MODEL" \
      --wbm-root "$MT_DATA_ROOT" --ref-energies-json "$REFS" "${EXTRA[@]}" >> "$L" 2>&1
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

# --- 4. force oam+hull re-run over the final pred roster ----------------------
export OAM_MODEL="${OAM_MODEL:-sevennet-mf-ompa}"
rm -f "$MT29/mt29_stage1_oam_arm_result.json" "$MT29/mt29_hull_recompute_validation_result.json"
bash run_all_arms.sh oam >> "$L" 2>&1 && echo "OAM_OK" >> "$L" || echo "OAM_FAILED" >> "$L"
bash run_all_arms.sh hull >> "$L" 2>&1 && echo "HULL_OK" >> "$L" || echo "HULL_FAILED" >> "$L"

echo "MAT_SESSION4C_DONE" >> "$L"
chain_epilogue "$MT29 /root/mt_uip /root/mat_session4*.log" "MAT_SESSION4C_ALL_DONE" "mat_session4c"
