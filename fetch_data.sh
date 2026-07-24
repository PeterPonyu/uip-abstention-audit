#!/usr/bin/env bash
# fetch_data.sh — data pulls for the NEXT-EXPERIMENTS.md decisive arms (OAM-era UIP +
# hull recompute). Run on a machine WITH network access (the AutoDL container — see
# RUNME_CONTAINER.md). Idempotent: re-running skips files already present with the
# expected size, so it is safe to re-invoke after a partial failure.
#
# Sources (registration-free; see DATA_MANIFEST.md):
#   - Matbench Discovery (Nature MI 2025, Apache/MIT) Figshare mirror, auto-cached by
#     the `matbench-discovery` PyPI package under ~/.cache/matbench-discovery.
#     https://matbench-discovery.materialsproject.org/
#
# What this fetches that is NOT already in DATA_MANIFEST.md:
#   1. WBM initial (unrelaxed) structures, needed to run frozen inference for the
#      OAM-era arm (Arm 1). NOTE: the existing repo-adjacent copy at
#      ~/.cache/matbench-discovery/wbm/2024-08-04-wbm-initial-atoms.extxyz.zip is a
#      confirmed 0-BYTE aborted download (DATA_MANIFEST.md Sec.3) — this script
#      re-downloads it for real.
#   2. MP computed structure entries (the reference-entry set for convex-hull
#      recompute, Arm 2), ~1-2 GB.
#
# Both are fetched via the matbench-discovery package's own DataFiles accessors,
# which handle the exact Figshare URLs/versioning internally — do NOT hardcode a raw
# Figshare URL here (they are versioned and have moved before). VERIFY the exact
# attribute names below against your installed matbench-discovery version first:
#   python -c "from matbench_discovery.data import DataFiles; print([d.name for d in DataFiles])"
# and adjust the two `DataFiles.<name>` references below if they differ.
set -euo pipefail

echo "=== fetch_data.sh: WBM initial structures + MP reference entries ==="

python3 - <<'PY'
import sys
try:
    from matbench_discovery.data import DataFiles
except ImportError:
    sys.exit(
        "ERROR: matbench-discovery not installed. Run the pip installs in "
        "RUNME_CONTAINER.md step 1 first (pip install matbench-discovery)."
    )

# Triggers the package's own download-if-missing + checksum logic; each .path access
# is idempotent (no-op if already cached under ~/.cache/matbench-discovery).
print("Fetching WBM initial (unrelaxed) structures ...")
p1 = DataFiles.wbm_initial_structures.path
print(f"  -> {p1}")

print("Fetching MP computed structure entries (hull reference set) ...")
p2 = DataFiles.mp_computed_structure_entries.path
print(f"  -> {p2}")

print("OK. Point mt29_uip_inference.py --wbm-root and "
      "mt29_hull_recompute_validation.py --mp-entries at the directories above "
      "(or export MT_DATA_ROOT / MT_MP_ENTRIES).")
PY

echo "=== fetch_data.sh done ==="
echo "Reminder: the WBM SUMMARY csv (2023-12-13-wbm-summary.csv.gz, ground truth) is"
echo "already documented in DATA_MANIFEST.md and is expected to already be present at"
echo "\$MT_DATA_ROOT (default ~/mt_stage0/data) — this script does not re-fetch it."
