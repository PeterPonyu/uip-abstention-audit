#!/usr/bin/env python3
"""Run the FROZEN mt29_hull_recompute_validation on the CORRECTED MP reference table
(MP2020 formation-energy-per-atom entries produced by the rewritten
mt29_convert_mp_entries.py), writing the result under
results_expansion_2026-07-10/corrected_arms/ (NOT into research/results/MT29/).

This wrapper imports mt29_hull_recompute_validation.run_real UNCHANGED — the exact frozen
sampling / hull-recompute / delta-summary logic the 4d chain invoked
(`python3 mt29_hull_recompute_validation.py` with all defaults: BASE_MODELS, n_total=5000,
seed=SEED, default WBM summary + legacy UIP root) — and only (a) points --mp-entries at the
corrected pickle and (b) redirects the output JSON location. No frozen script is edited; no
canonical MT29 JSON is touched. CPU-only, no network.
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

from mt29_hull_recompute_validation import run_real, BASE_MODELS, N_TOTAL_DEFAULT  # noqa: E402
from mt29_stage1_chem_yield import DATA as DEFAULT_WBM_SUMMARY, UIP as DEFAULT_UIP_ROOT  # noqa: E402
from mt29_stage1_chem_yield import sha256, SEED  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--wbm-summary', default=DEFAULT_WBM_SUMMARY)
    ap.add_argument('--uip-root', default=DEFAULT_UIP_ROOT)
    ap.add_argument('--mp-entries', default=os.path.expanduser(
        '~/.cache/matbench-discovery/mp/mp_computed_structure_entries.pkl.gz'))
    ap.add_argument('--models', default=','.join(BASE_MODELS))
    ap.add_argument('--n-total', type=int, default=N_TOTAL_DEFAULT)
    ap.add_argument('--seed', type=int, default=SEED)
    ap.add_argument('--out-json', default=os.path.join(HERE, 'mt29_hull_recompute_corrected_result.json'))
    args = ap.parse_args(argv)

    models = args.models.split(',')
    print(f'[hull] mp_entries={args.mp_entries}')
    print(f'[hull] models={models} n_total={args.n_total} seed={args.seed}')
    results = run_real(args.wbm_summary, args.uip_root, args.mp_entries, models,
                       args.n_total, args.seed)

    with open(args.out_json, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f'[write] {args.out_json}')

    # ---- headline read-out ----------------------------------------------------------
    meta = results['meta']
    summ = results['summary']
    print(f"\n=== hull recompute (corrected reference) : n_evaluated={meta['n_evaluated']} "
          f"of {meta['n_requested']} requested ===")
    print(f"total stable/unstable call flips (fixed-hull vs recomputed): "
          f"{summ['total_flips']}  any_flips={summ['any_flips']}")
    print('\nper-stratum delta_mean (fixed - recomputed, eV/atom) and flip_rate range over models:')
    for fam, v in results['per_stratum'].items():
        dms = [v['per_model'][m]['delta_mean'] for m in models if v['per_model'][m]['delta_mean'] is not None]
        frs = [v['per_model'][m]['flip_rate'] for m in models if v['per_model'][m]['flip_rate'] is not None]
        dmean = float(np.mean(dms)) if dms else float('nan')
        print(f"  {fam:14} n={v['n']:5}  delta_mean~{dmean:+.4f}  "
              f"flip_rate {min(frs):.4f}-{max(frs):.4f}")

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
        'frozen_hull_script_sha256': sha256(os.path.join(MT29, 'mt29_hull_recompute_validation.py')),
        'converter_sha256': sha256(os.path.join(MT29, 'mt29_convert_mp_entries.py')),
        'git_head': git_sha, 'seed': args.seed, 'n_total': args.n_total, 'models': models,
        'mp_entries_pickle_sha256': sha256(args.mp_entries),
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
