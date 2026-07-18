#!/bin/bash
# Materials session #4: DATA-AUDIT-FIRST (session3 lesson, 2026-07-09: arms ran
# against an empty /root/mt_stage0/data and burned a GPU boot in 50 seconds —
# ROSTER/OAM/HULL all FileNotFoundError). This chain refuses to touch the arms
# until every required data file is PRESENT and non-trivial:
#   1. AUDIT: locate WBM initial structures, WBM summary, MP entries anywhere
#      on the box (search /root/.cache/matbench-discovery, /root/autodl-tmp,
#      /root/mt_stage0) and symlink them into $MT_DATA_ROOT so every arm
#      script's default path resolves.
#   2. If a file is missing -> ONE box-side fetch attempt (network_turbo,
#      content-gated on file size, matbench-discovery's own fetcher).
#   3. Still missing -> MAT_SESSION4_DATA_MISSING marker + fast epilogue.
#      The source decision (figshare-class relay) escalates to the user per
#      the standing directive — no GPU time is spent either way.
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
cd /root/materials-mlip-research
L="${MAT_LOG:-/root/mat_session4.log}"
export CHAIN_LOG="$L"
chain_prologue
MT29="research/results/MT29"
export MT_DATA_ROOT="${MT_DATA_ROOT:-/root/mt_stage0/data}"
REFS="${OAM_REF_ENERGIES_JSON:-/root/autodl-tmp/ref_energies.json}"
MIN_ROWS="${ROSTER_MIN_PREDICTIONS:-1000}"
SEARCH_ROOTS="${DATA_SEARCH_ROOTS:-/root/.cache/matbench-discovery /root/autodl-tmp /root/mt_stage0}"

echo "[$(date)] MAT4: data audit -> (fetch) -> roster -> oam -> hull" >> "$L"
mkdir -p "$MT_DATA_ROOT"

# --- 1. data audit: locate + symlink each required file ---------------------
# name pattern -> min bytes (content gate: a truncated download must not pass)
locate_and_link() {
  local pattern="$1" min_bytes="$2" label="$3"
  local existing
  existing=$(find "$MT_DATA_ROOT" -maxdepth 1 \( -name "$pattern" \) -size +"$((min_bytes/1024))"k 2>/dev/null | head -1)
  if [ -n "$existing" ]; then echo "AUDIT_${label}_OK $existing" >> "$L"; return 0; fi
  local found
  # shellcheck disable=SC2086
  found=$(find $SEARCH_ROOTS -maxdepth 4 -name "$pattern" -size +"$((min_bytes/1024))"k 2>/dev/null | head -1)
  if [ -n "$found" ]; then
    ln -sf "$found" "$MT_DATA_ROOT/$(basename "$found")"
    echo "AUDIT_${label}_OK linked $found -> $MT_DATA_ROOT" >> "$L"
    return 0
  fi
  echo "AUDIT_${label}_MISSING (pattern=$pattern, roots=$SEARCH_ROOTS)" >> "$L"
  return 1
}

AUDIT_FAIL=0
locate_and_link "*wbm*initial*atoms*.extxyz.zip" 100000000 WBM_INITIAL || \
  locate_and_link "*wbm-init-structs*.json*" 30000000 WBM_INITIAL || AUDIT_FAIL=1
locate_and_link "*wbm-summary*.csv.gz" 10000000 WBM_SUMMARY || AUDIT_FAIL=1
locate_and_link "*mp-computed-structure-entries*.json.gz" 100000000 MP_ENTRIES || AUDIT_FAIL=1

# --- 2. one fetch attempt if anything is missing -----------------------------
if [ "$AUDIT_FAIL" -ne 0 ]; then
  echo "[$(date)] MAT4: audit incomplete -> one content-gated fetch attempt" >> "$L"
  source /etc/network_turbo >/dev/null 2>&1 || true
  bash fetch_data.sh >> "$L" 2>&1 || true
  AUDIT_FAIL=0
  locate_and_link "*wbm*initial*atoms*.extxyz.zip" 100000000 WBM_INITIAL_POSTFETCH || \
    locate_and_link "*wbm-init-structs*.json*" 30000000 WBM_INITIAL_POSTFETCH || AUDIT_FAIL=1
  locate_and_link "*wbm-summary*.csv.gz" 10000000 WBM_SUMMARY_POSTFETCH || AUDIT_FAIL=1
  locate_and_link "*mp-computed-structure-entries*.json.gz" 100000000 MP_ENTRIES_POSTFETCH || AUDIT_FAIL=1
fi

if [ "$AUDIT_FAIL" -ne 0 ]; then
  echo "MAT_SESSION4_DATA_MISSING -- arms NOT run, no GPU time spent; escalate source decision to user" >> "$L"
  chain_epilogue "/root/mat_session*.log" "MAT_SESSION4_ALL_DONE"
  exit 1
fi
echo "DATA_AUDIT_ALL_OK" >> "$L"

# --- 3. refs (skip if already derived by session3) ---------------------------
if [ ! -s "$REFS" ]; then
  echo "DERIVE_REFS_MISSING -- session3 should have written $REFS; aborting rather than re-deriving blind" >> "$L"
  chain_epilogue "/root/mat_session*.log" "MAT_SESSION4_ALL_DONE"
  exit 1
fi
export OAM_REF_ENERGIES_JSON="$REFS"
echo "REFS_PRESENT $REFS" >> "$L"

# --- 4. roster with per-model interpreters (session3 body, unchanged) --------
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

# --- 5. oam + hull (main env) -------------------------------------------------
export OAM_MODEL="${OAM_MODEL:-sevennet-mf-ompa}"
bash run_all_arms.sh oam >> "$L" 2>&1 && echo "OAM_OK" >> "$L" || echo "OAM_FAILED" >> "$L"
bash run_all_arms.sh hull >> "$L" 2>&1 && echo "HULL_OK" >> "$L" || echo "HULL_FAILED" >> "$L"

echo "MAT_SESSION4_DONE" >> "$L"
chain_epilogue "$MT29 /root/mt_uip /root/mat_session*.log" "MAT_SESSION4_ALL_DONE" "mat_session4"
