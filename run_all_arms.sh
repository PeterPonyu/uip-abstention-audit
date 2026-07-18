#!/usr/bin/env bash
# run_all_arms.sh — runs the NEXT-EXPERIMENTS.md decisive arms in order on a fresh
# AutoDL 4090D container (see RUNME_CONTAINER.md for the full walkthrough + the gated
# eSEN-30M-OAM checkpoint step). Idempotent: every step either checks for its expected
# output first or refuses to overwrite an existing result JSON, so re-running after a
# partial failure just resumes.
#
# Usage:
#   bash run_all_arms.sh smoke     # CPU-only, no data/network/GPU -- verifies the
#                                   # code paths before spending GPU time (~seconds)
#   bash run_all_arms.sh fetch     # fetch_data.sh only
#   bash run_all_arms.sh oam       # Arm 1: OAM-era UIP inference + analysis hookup
#   bash run_all_arms.sh roster    # Roster: mace-mp-0/orb-v3/mattersim frozen
#                                   # inference (EXPANSION-PLAN-2026-07-09.md Sec.2.4)
#   bash run_all_arms.sh hull      # Arm 2: hull-recompute validation
#   bash run_all_arms.sh all       # fetch + oam + roster + hull, in order (default)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MT29="${HERE}/research/results/MT29"
MODE="${1:-all}"

# Roster step's content gate: minimum row count a `<model>_pred.csv` must have to be
# accepted as real (never trust the inference script's exit code alone -- a partial
# WBM download or an early-exhausted iterator can still exit 0 with a near-empty CSV).
# Override via ROSTER_MIN_PREDICTIONS for a deliberately capped --limit smoke run.
ROSTER_MIN_PREDICTIONS="${ROSTER_MIN_PREDICTIONS:-1000}"

run_smoke() {
    echo "=== SMOKE: all new-arm scripts, CPU-only, no network/GPU/checkpoint ==="
    python3 "${MT29}/mt29_uip_inference.py" --smoke
    python3 "${MT29}/mt29_stage1_oam_arm.py" --smoke
    python3 "${MT29}/mt29_hull_recompute_validation.py" --smoke
    echo "=== SMOKE OK ==="
}

run_fetch() {
    echo "=== fetch_data.sh ==="
    bash "${HERE}/fetch_data.sh"
}

run_oam() {
    echo "=== Arm 1a: OAM-era UIP frozen inference ==="
    echo "REQUIRES either:"
    echo "  (a) eSEN-30M-OAM: a locally-resolvable checkpoint after accepting the HF"
    echo "      click-through license (see RUNME_CONTAINER.md 'gated checkpoint'), OR"
    echo "  (b) SevenNet-MF-ompa (default; un-gated, downloads automatically)."
    MODEL="${OAM_MODEL:-sevennet-mf-ompa}"
    CKPT_ARGS=()
    if [ -n "${OAM_CHECKPOINT:-}" ]; then
        CKPT_ARGS=(--checkpoint "${OAM_CHECKPOINT}")
    fi
    if [ -z "${OAM_REF_ENERGIES_JSON:-}" ]; then
        echo "ERROR: set OAM_REF_ENERGIES_JSON=/path/to/ref_energies.json (see"
        echo "RUNME_CONTAINER.md 'reference energies') before running the real arm."
        exit 2
    fi
    OUT_CSV="${MT_UIP_ROOT:-$HOME/mt_uip}/$(echo "${MODEL}" | tr '-' '_')_pred.csv"
    if [ -f "${OUT_CSV}" ]; then
        echo "SKIP: ${OUT_CSV} already exists (idempotent) -- delete it to re-run inference."
    else
        python3 "${MT29}/mt29_uip_inference.py" --model "${MODEL}" "${CKPT_ARGS[@]}" \
            --ref-energies-json "${OAM_REF_ENERGIES_JSON}"
    fi

    echo "=== Arm 1b: hook OAM-era prediction(s) into the matched-yield pipeline ==="
    if [ -f "${MT29}/mt29_stage1_oam_arm_result.json" ]; then
        echo "SKIP: mt29_stage1_oam_arm_result.json already exists (idempotent) --"
        echo "delete it (never hand-edit) to re-run."
    else
        python3 "${MT29}/mt29_stage1_oam_arm.py"
    fi
}

run_roster() {
    echo "=== Roster: current-gen (2024-25) UIP frozen inference -- mace-mp-0, orb-v3,"
    echo "mattersim (EXPANSION-PLAN-2026-07-09.md Sec.2.4; adds to the eSEN/SevenNet"
    echo "OAM-era pair already handled by 'oam', for a 5-model multi-UIP verdict table)."
    if [ -z "${OAM_REF_ENERGIES_JSON:-}" ]; then
        echo "ERROR: set OAM_REF_ENERGIES_JSON=/path/to/ref_energies.json (see"
        echo "RUNME_CONTAINER.md 'reference energies') before running the roster."
        exit 2
    fi
    for MODEL in mace-mp-0 orb-v3 mattersim; do
        OUT_CSV="${MT_UIP_ROOT:-$HOME/mt_uip}/$(echo "${MODEL}" | tr '-' '_')_pred.csv"
        if [ -f "${OUT_CSV}" ]; then
            echo "SKIP: ${OUT_CSV} already exists (idempotent) -- delete it to re-run"
            echo "inference for ${MODEL}."
        else
            python3 "${MT29}/mt29_uip_inference.py" --model "${MODEL}" \
                --ref-energies-json "${OAM_REF_ENERGIES_JSON}"
        fi

        # CONTENT GATE (never a bare exit-code check): the output CSV must exist AND
        # have more than ROSTER_MIN_PREDICTIONS data rows -- a truncated download or a
        # calculator that silently produced zero/near-zero rows must fail this step
        # loudly rather than let a downstream analysis run on a near-empty roster.
        if [ ! -f "${OUT_CSV}" ]; then
            echo "CONTENT GATE FAILED: ${OUT_CSV} does not exist after running ${MODEL}." >&2
            exit 1
        fi
        N_ROWS="$(python3 -c "import pandas as pd; print(len(pd.read_csv('${OUT_CSV}')))")"
        if [ "${N_ROWS}" -le "${ROSTER_MIN_PREDICTIONS}" ]; then
            echo "CONTENT GATE FAILED: ${OUT_CSV} has only ${N_ROWS} rows (need >" \
                 "${ROSTER_MIN_PREDICTIONS})." >&2
            exit 1
        fi
        echo "CONTENT GATE OK: ${MODEL} -> ${OUT_CSV} (${N_ROWS} predictions)"
    done
    echo "=== Roster inference done. Run (or re-run) 'oam' afterward -- its Arm 1b"
    echo "(mt29_stage1_oam_arm.py) auto-discovers ALL *_pred.csv beyond the base 4,"
    echo "so it will pick up these 3 roster models too, in the same combined"
    echo "mt29_stage1_oam_arm_result.json. ==="
}

run_hull() {
    echo "=== Arm 2: convex-hull recompute validation subset ==="
    if [ -f "${MT29}/mt29_hull_recompute_validation_result.json" ]; then
        echo "SKIP: mt29_hull_recompute_validation_result.json already exists"
        echo "(idempotent) -- delete it (never hand-edit) to re-run."
    else
        python3 "${MT29}/mt29_hull_recompute_validation.py"
    fi
}

case "${MODE}" in
    smoke)  run_smoke ;;
    fetch)  run_fetch ;;
    oam)    run_oam ;;
    roster) run_roster ;;
    hull)   run_hull ;;
    all)
        run_smoke
        run_fetch
        # roster BEFORE oam: oam's Arm 1b call auto-discovers every *_pred.csv beyond
        # the base 4, so running roster first means the one combined
        # mt29_stage1_oam_arm_result.json includes mace-mp-0/orb-v3/mattersim too.
        run_roster
        run_oam
        run_hull
        ;;
    *)
        echo "Usage: bash run_all_arms.sh {smoke|fetch|oam|roster|hull|all}" >&2
        exit 1
        ;;
esac
