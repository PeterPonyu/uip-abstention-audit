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
source /root/miniconda3/etc/profile.d/conda.sh && conda activate base
export HF_HOME=/root/autodl-tmp/hf-cache
source /etc/network_turbo >/dev/null 2>&1 || true
export HF_ENDPOINT=https://hf-mirror.com
export HF_HUB_DISABLE_XET=1
cd /root/materials-mlip-research
L="${MAT_LOG:-/root/mat_session2.log}"
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

# --- 2. reference energies via pymatgen ---
python3 - << 'PYEOF' >> "$L" 2>&1
import gzip, json
from pathlib import Path
from pymatgen.entries.computed_entries import ComputedStructureEntry
src = Path.home() / ".cache/matbench-discovery/mp/2023-02-07-mp-computed-structure-entries.json.gz"
raw = json.load(gzip.open(src, "rt"))
items = list(raw.values()) if isinstance(raw, dict) else raw
print("schema probe: container", type(raw).__name__, "n=", len(items),
      "first keys:", sorted(list(items[0].keys()))[:8] if items and isinstance(items[0], dict) else "?")
refs, n_elem = {}, 0
for d in items:
    try:
        ent = ComputedStructureEntry.from_dict(d)
    except Exception:
        continue
    comp = ent.composition
    if len(comp.elements) != 1:
        continue
    n_elem += 1
    el = comp.elements[0].symbol
    epa = ent.energy / comp.num_atoms  # correction-inclusive in pymatgen
    if el not in refs or epa < refs[el]:
        refs[el] = epa
out = Path("/root/autodl-tmp/ref_energies.json")
out.write_text(json.dumps(refs, indent=1))
print(f"REFS_DERIVED elements={len(refs)} from {n_elem} elemental entries")
assert len(refs) >= 60, f"too few elements: {len(refs)}"
print("REFS_OK")
PYEOF
grep -q "REFS_OK" "$L" && echo "DERIVE_REFS_OK" >> "$L" || { echo "DERIVE_REFS_FAILED" >> "$L"; echo "MAT_SESSION2_DONE" >> "$L"; exit 1; }
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

echo "MAT_SESSION2_DONE" >> "$L"
