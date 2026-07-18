#!/bin/bash
# Materials session #4d — targeted repair of 4c's two failures (2026-07-10).
#   ORB: 4c made the adapter import version-adaptive but missed that
#     orb-models 0.7 pretrained loaders return (model, atoms_adapter) and the
#     inference ORBCalculator requires the adapter positionally ->
#     "ORBCalculator.__init__() missing ... 'atoms_adapter'".
#     mt29_uip_inference.py now unpacks the tuple (probed LIVE on this box:
#     ORB_PROBE_OK, NaCl rocksalt smoke, 2026-07-10). Re-run orb-v3 only.
#   HULL: mt29_hull_recompute_validation.py expects a plain-pickle
#     mp_computed_structure_entries.pkl.gz that nothing ever produced; the
#     July-9 relay artifact (2023-02-07-...json.gz) IS on the box.
#     mt29_convert_mp_entries.py bridges the formats (frozen hull script
#     untouched), then hull re-runs.
# Honest markers (4c's loose-ALL_DONE lesson): MAT_SESSION4D_ALL_DONE only
# when BOTH repairs pass their content gates; MAT_SESSION4D_PARTIAL_DONE
# otherwise. Same tar either way so partial results still get pulled.
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
L="${MAT_LOG:-/root/mat_session4d.log}"
export CHAIN_LOG="$L"
chain_prologue
MT29="research/results/MT29"
export MT_DATA_ROOT="${MT_DATA_ROOT:-/root/mt_stage0/data}"
REFS="${OAM_REF_ENERGIES_JSON:-/root/autodl-tmp/ref_energies.json}"
export OAM_REF_ENERGIES_JSON="$REFS"
MT_UIP_ROOT="${MT_UIP_ROOT:-$HOME/mt_uip}"
EXPECTED_ROWS="${MT29_EXPECTED_ROWS:-256963}"   # WBM test-set size, frozen fact
ORB_PY="${ORB_PY:-/root/venvs/orb/bin/python}"
MP_ENTRIES_SRC="${MP_ENTRIES_SRC:-/root/.cache/matbench-discovery/mp/2023-02-07-mp-computed-structure-entries.json.gz}"
MP_ENTRIES_PKL="${MP_ENTRIES_PKL:-/root/.cache/matbench-discovery/mp/mp_computed_structure_entries.pkl.gz}"
FAIL=0

echo "[$(date)] MAT4D: orb-v3 roster repair -> mp-entries convert -> hull re-run" >> "$L"

# --- 1. orb-v3 roster inference (the 0.7 tuple-unpack fix rides the repo sync)
OUT_CSV="$MT_UIP_ROOT/orb_v3_pred.csv"
csv_rows() { python3 -c "import pandas as pd; print(len(pd.read_csv('$1')))" 2>/dev/null || echo 0; }
if [ -f "$OUT_CSV" ] && [ "$(csv_rows "$OUT_CSV")" -eq "$EXPECTED_ROWS" ]; then
  echo "SKIP orb-v3: $OUT_CSV already complete" >> "$L"
else
  rm -f "$OUT_CSV"
  "$ORB_PY" "$MT29/mt29_uip_inference.py" --model orb-v3 \
    --wbm-root "$MT_DATA_ROOT" --ref-energies-json "$REFS" >> "$L" 2>&1
fi
N=$(csv_rows "$OUT_CSV")
if [ "$N" -eq "$EXPECTED_ROWS" ]; then
  echo "ROSTER_orb-v3_OK rows=$N" >> "$L"
else
  # exact-count gate (M7 discipline): delete a short/partial CSV so a resumed
  # run re-scores instead of trusting it forever
  echo "ROSTER_orb-v3_FAILED rows=$N expected=$EXPECTED_ROWS" >> "$L"
  [ "$N" -eq 0 ] || rm -f "$OUT_CSV"
  FAIL=1
fi

# --- 2. MP reference entries: json.gz -> plain pickle (idempotent) -----------
if python3 "$MT29/mt29_convert_mp_entries.py" --src "$MP_ENTRIES_SRC" -o "$MP_ENTRIES_PKL" >> "$L" 2>&1; then
  echo "MP_ENTRIES_CONVERT_OK" >> "$L"
  CONVERT_OK=1
else
  echo "MP_ENTRIES_CONVERT_FAILED" >> "$L"
  CONVERT_OK=0
  FAIL=1
fi

# --- 3. hull recompute validation (only with reference entries in place) -----
if [ "$CONVERT_OK" -eq 1 ]; then
  rm -f "$MT29/mt29_hull_recompute_validation_result.json"
  if bash run_all_arms.sh hull >> "$L" 2>&1; then
    echo "HULL_OK" >> "$L"
  else
    echo "HULL_FAILED" >> "$L"
    FAIL=1
  fi
else
  echo "HULL_SKIPPED (no reference entries)" >> "$L"
fi

# --- markers + epilogue (conditional; partial never masquerades as done) -----
if [ "$FAIL" -eq 0 ]; then
  marker="MAT_SESSION4D_ALL_DONE"
else
  marker="MAT_SESSION4D_PARTIAL_DONE"
fi
echo "$marker" >> "$L"
chain_epilogue "$MT29 $OUT_CSV /root/mat_session4d.log" "$marker" "mat_session4d"
