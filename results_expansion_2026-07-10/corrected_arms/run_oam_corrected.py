#!/usr/bin/env python3
"""Run the FROZEN mt29_stage1_oam_arm statistics against the MP2020-CORRECTED modern
roster, writing the result under results_expansion_2026-07-10/corrected_arms/ (NOT into
research/results/MT29/).

This wrapper imports mt29_stage1_oam_arm's functions UNCHANGED (load_extended,
discover_oam_models, run_matched_yield_arm, interactions_from_gains) — identical matched-
yield-control math to mt29_stage1_matched_yield_fix.py — and only redirects the output
location and points --uip-root at the corrected roster
(corrected_arms/roster_mp2020/, which holds the 4 legacy CSVs unchanged + the 4 new
models with e_correction_per_atom_mp2020 added). No frozen script is edited; no canonical
MT29 JSON is touched. CPU-only, no network.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
MT29 = '/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/research/results/MT29'
sys.path.insert(0, MT29)

from mt29_stage1_oam_arm import (  # noqa: E402  (frozen functions, imported not edited)
    BASE_MODELS, discover_oam_models, load_extended, run_matched_yield_arm,
    interactions_from_gains,
)
from mt29_stage1_chem_yield import sha256, SEED, N_BOOT  # noqa: E402
from mt29_stage1_matched_yield_fix import FAM_ORDER  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--wbm-summary',
                    default=os.environ.get('MT_WBM_SUMMARY',
                                           os.path.expanduser('~/mt_stage0/data/2023-12-13-wbm-summary.csv.gz')))
    ap.add_argument('--uip-root', default=os.path.join(HERE, 'roster_mp2020'))
    ap.add_argument('--out-json', default=os.path.join(HERE, 'mt29_stage1_oam_arm_corrected_result.json'))
    args = ap.parse_args(argv)

    oam_models = discover_oam_models(args.uip_root)
    models = BASE_MODELS + oam_models
    print(f'[roster] base={BASE_MODELS} oam_discovered={oam_models}')
    assert oam_models, 'no OAM models discovered in roster; aborting'

    base_df = load_extended(args.wbm_summary, args.uip_root, models)
    per_model = run_matched_yield_arm(base_df, models)
    inter = interactions_from_gains(per_model, models)

    results = {
        'meta': {
            'story': 'G007-s1-materials-mt29-oam-arm-CORRECTED',
            'stage': 'corrected_arms 2026-07-10: MP2020-corrected modern roster',
            'seed': SEED, 'n_boot': N_BOOT, 'base_models': BASE_MODELS,
            'oam_models_found': oam_models, 'models': models, 'strata': FAM_ORDER,
            'n_rows': int(len(base_df)),
            'roster_note': ('4 legacy CSVs (chgnet/m3gnet/mace/orb) UNCHANGED; 4 new models '
                            '(mace_mp_0/mattersim/sevennet_mf_ompa/orb_v3) = raw prediction + '
                            'e_correction_per_atom_mp2020 (matbench-discovery per-material '
                            'MP2020 correction). See oam_correction_validation.json.'),
            'control': ('identical corrected matched-yield control as '
                        'mt29_stage1_matched_yield_fix.py, generalized over the OAM-extended '
                        'roster; frozen canonical result JSONs untouched.'),
        },
        'per_model_budgets': per_model,
        'interactions': inter,
    }

    with open(args.out_json, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f'[write] {args.out_json}')

    # ---- headline read-out: total_called_stable per model (degeneracy check) --------
    print('\n=== total_called_stable (oxide) per model — degeneracy check ===')
    for m in models:
        pm = per_model.get(m, {})
        if pm.get('skipped'):
            print(f'  {m:20} SKIPPED: {pm.get("reason")}')
        else:
            tcs = pm.get('total_called_stable', {})
            print(f'  {m:20} oxide={tcs.get("oxide")} halide={tcs.get("halide")} '
                  f'y_loose={pm.get("y_loose")}')

    # manifest
    try:
        git_sha = subprocess.check_output(
            ['git', '-C', '/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research',
             'rev-parse', 'HEAD'], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        git_sha = None
    manifest = {
        'cmd': ' '.join([sys.executable] + sys.argv),
        'wrapper_sha256': sha256(os.path.abspath(__file__)),
        'frozen_oam_arm_sha256': sha256(os.path.join(MT29, 'mt29_stage1_oam_arm.py')),
        'git_head': git_sha, 'seed': SEED, 'n_boot': N_BOOT,
        'models': models, 'oam_models_found': oam_models,
        'inputs': {os.path.basename(args.wbm_summary): sha256(args.wbm_summary),
                   **{f'{m}_pred.csv': sha256(os.path.join(args.uip_root, f'{m}_pred.csv'))
                      for m in models}},
        'output_sha256': sha256(args.out_json),
        'versions': {'python': platform.python_version(), 'numpy': np.__version__,
                     'pandas': pd.__version__},
        'platform': platform.platform(),
    }
    man_path = args.out_json.replace('_result.json', '_manifest.json')
    with open(man_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f'[write] {man_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
