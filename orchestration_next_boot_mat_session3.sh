#!/bin/bash
# Materials session #2 (next GPU boot). Fixes from the 2026-07-09 session:
#   1. e3nn conflict (mace-torch==e3nn0.4.4 vs mattersim>=0.5, predicted by the
#      build agent, confirmed by pip ResolutionImpossible): each UIP gets its
#      own venv with --system-site-packages (torch reused), and the roster
#      loop runs each model with ITS OWN interpreter (mirroring run_all_arms'
#      per-model process design + content gates).
#   2. ref-energies derivation rewritten on pymatgen's own parser (raw-dict
#      schema guessing found 0 entries): ComputedStructureEntry.from_dict,
#      entry.energy is correction-inclusive, elemental = single-element comp.
#   3. Chain gates unchanged: nothing downstream runs on a failed step.
set -uo pipefail
RELIABILITY_COMMONS="${RELIABILITY_COMMONS:-/root/reliability-commons}"
if [ -f "${RELIABILITY_COMMONS}/tools/boxkit/chain_lib.sh" ]; then
  # shellcheck disable=SC1091
  source "${RELIABILITY_COMMONS}/tools/boxkit/chain_lib.sh"
else
  chain_prologue() { :; }
  chain_epilogue() {
    local marker_name="$2"
    echo "$marker_name" >> "${CHAIN_LOG:-${L:-/root/chain.log}}"
    [ -f /root/NO_AUTOSHUTDOWN ] || shutdown -h now
  }
fi
chain_prologue
source /etc/network_turbo >/dev/null 2>&1 || true
export HF_ENDPOINT=https://hf-mirror.com
export HF_HUB_DISABLE_XET=1
cd /root/materials-mlip-research
L="${MAT_LOG:-/root/mat_session3.log}"
MT29="research/results/MT29"
REFS="${OAM_REF_ENERGIES_JSON:-/root/autodl-tmp/ref_energies.json}"
MIN_ROWS="${ROSTER_MIN_PREDICTIONS:-1000}"
PIP_IDX="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"

echo "[$(date)] MAT2: per-model venvs -> pymatgen refs -> roster -> oam -> hull" >> "$L"

# --- 1. per-model venvs (torch shared via system-site-packages) ---
declare -A PKG=( [mace]="mace-torch" [orb]="orb-models" [mattersim]="mattersim" )
for V in mace orb mattersim; do
  if [ ! -f "/root/venvs/$V/bin/python" ]; then
    python3 -m venv --system-site-packages "/root/venvs/$V"
    "/root/venvs/$V/bin/pip" install -q -i "$PIP_IDX" "${PKG[$V]}" >> "$L" 2>&1 \
      && echo "VENV_${V}_OK" >> "$L" || echo "VENV_${V}_FAILED" >> "$L"
  else
    echo "VENV_${V}_OK (exists)" >> "$L"
  fi
done

# --- 2. reference energies (parser VALIDATED locally against the real file
#         2026-07-09: 89 elements from 790 elemental entries / 154,718 total;
#         file is pandas-orient JSON: {"material_id": {...}, "entry": {row: CSE-dict}}) ---
python3 - << 'PYEOF2' >> "$L" 2>&1
import gzip, json
from pathlib import Path
src = Path.home() / ".cache/matbench-discovery/mp/2023-02-07-mp-computed-structure-entries.json.gz"
raw = json.load(gzip.open(src, "rt"))
refs, n_elem = {}, 0
for d in raw["entry"].values():
    comp = d.get("composition") or {}
    if len(comp) != 1:
        continue
    n_elem += 1
    el = next(iter(comp))
    epa = (d["energy"] + (d.get("correction") or 0.0)) / sum(comp.values())
    if el not in refs or epa < refs[el]:
        refs[el] = epa
Path("/root/autodl-tmp/ref_energies.json").write_text(json.dumps(refs, indent=1))
print(f"REFS_DERIVED elements={len(refs)} from {n_elem} elemental entries")
assert len(refs) >= 60, f"too few elements: {len(refs)}"
print("REFS_OK")
PYEOF2
grep -q "REFS_OK" "$L" && echo "DERIVE_REFS_OK" >> "$L" || { echo "DERIVE_REFS_FAILED" >> "$L"; echo "MAT_SESSION3_DONE" >> "$L"; exit 1; }
export OAM_REF_ENERGIES_JSON="$REFS"

# --- 3. roster with per-model interpreters (mirrors run_all_arms gates) ---
declare -A MPY=( [mace-mp-0]="/root/venvs/mace/bin/python" [orb-v3]="/root/venvs/orb/bin/python" [mattersim]="/root/venvs/mattersim/bin/python" )
ROSTER_FAIL=0
for MODEL in mace-mp-0 orb-v3 mattersim; do
  OUT_CSV="${MT_UIP_ROOT:-$HOME/mt_uip}/$(echo "$MODEL" | tr '-' '_')_pred.csv"
  if [ ! -f "$OUT_CSV" ]; then
    "${MPY[$MODEL]}" "$MT29/mt29_uip_inference.py" --model "$MODEL" \
      --ref-energies-json "$REFS" >> "$L" 2>&1
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

# --- 4. oam + hull (main env; sevenn/fairchem already installed) ---
export OAM_MODEL="${OAM_MODEL:-sevennet-mf-ompa}"
bash run_all_arms.sh oam >> "$L" 2>&1 && echo "OAM_OK" >> "$L" || echo "OAM_FAILED" >> "$L"
bash run_all_arms.sh hull >> "$L" 2>&1 && echo "HULL_OK" >> "$L" || echo "HULL_FAILED" >> "$L"

echo "MAT_SESSION3_DONE" >> "$L"

chain_epilogue "$MT29 /root/mat_session*.log" "MAT_SESSION3_ALL_DONE"
