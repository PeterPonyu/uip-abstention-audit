#!/usr/bin/env python
"""MT29 — Arm 1b (NEXT-EXPERIMENTS.md item 1): hooks OAM-era UIP predictions (produced
by mt29_uip_inference.py, e.g. ~/mt_uip/sevennet_mf_ompa_pred.csv) into the EXISTING
matched-yield stratified-abstention verdict pipeline, WITHOUT touching the frozen
canonical mt29_stage1_chem_yield.py / mt29_stage1_matched_yield_fix.py or their result
JSONs (portfolio rule: results only change by re-running analysis code; never
hand-edit/overwrite an existing result JSON — new experiments emit NEW
provenance-stamped JSONs).

Reuses (imports, does not re-architect):
  - mt29_stage1_chem_yield: anion_family classifier, DATA/UIP roots, sha256, SEED, N_BOOT
  - mt29_stage1_matched_yield_fix: FAM_ORDER, daf_top_y, boot_yield_gain — the CORRECTED
    matched-yield control (see that file's docstring for why the naive yield control in
    mt29_stage1_chem_yield.py was superseded; this arm always uses the corrected one).

Writes a NEW output: mt29_stage1_oam_arm_result.json (+ manifest). Never
mt29_stage1_matched_yield_result.json.

Model set = the 4 frozen 2023-24 UIPs (chgnet/m3gnet/mace/orb) + any OAM-era prediction
CSVs found in $MT_UIP_ROOT beyond those four (auto-discovered; override with
--oam-models). An empty OAM set is not an error — the script still runs (as a
base-4-only pipeline-verification pass) but records oam_models_found: [] in the output
so a stub run can never be mistaken for the real arm result.

Usage (real, once mt29_uip_inference.py has produced a new *_pred.csv):
  python3 mt29_stage1_oam_arm.py
Usage (CPU-only, no real WBM/UIP files, no network):
  python3 mt29_stage1_oam_arm.py --smoke
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import platform
import subprocess
import sys
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, '/home/zeyufu/Desktop/ml-reliability-research/reliability-commons')

from mt29_stage1_chem_yield import anion_family, DATA as DEFAULT_WBM_SUMMARY  # noqa: E402
from mt29_stage1_chem_yield import UIP as DEFAULT_UIP_ROOT, sha256, SEED, N_BOOT  # noqa: E402
from mt29_stage1_matched_yield_fix import FAM_ORDER, daf_top_y, boot_yield_gain  # noqa: E402

try:
    from relmetrics.provenance import stamp_result
except ImportError:  # pragma: no cover - relmetrics is a hard dep elsewhere, but keep
    stamp_result = None  # this script importable in a minimal test environment.

BASE_MODELS = ['chgnet', 'm3gnet', 'mace', 'orb']
OUT_DIR = HERE
OUT_JSON = os.path.join(OUT_DIR, 'mt29_stage1_oam_arm_result.json')
MANIFEST = os.path.join(OUT_DIR, 'mt29_stage1_oam_arm_manifest.json')


# ----------------------------- model discovery / data loading -----------------------------

def discover_oam_models(uip_root: str, base_models: List[str] = BASE_MODELS) -> List[str]:
    """Any `*_pred.csv` in `uip_root` whose stem is not one of the base 4 is treated as
    an OAM-era (or otherwise new) arm."""
    found = []
    for f in sorted(glob.glob(os.path.join(uip_root, '*_pred.csv'))):
        name = os.path.basename(f).replace('_pred.csv', '')
        if name not in base_models:
            found.append(name)
    return found


def load_extended(wbm_summary_path: str, uip_root: str, models: List[str]) -> pd.DataFrame:
    """Same merge/family-tag recipe as mt29_stage1_chem_yield.load(), parameterized
    over an arbitrary model list (base + OAM) instead of the hardcoded canonical four."""
    wbm = pd.read_csv(wbm_summary_path, usecols=['material_id', 'formula',
                                                  'e_form_per_atom_mp2020_corrected',
                                                  'e_above_hull_mp2020_corrected_ppd_mp',
                                                  'unique_prototype'])
    base = wbm.dropna(subset=['e_form_per_atom_mp2020_corrected',
                              'e_above_hull_mp2020_corrected_ppd_mp']).copy()
    for m in models:
        p = pd.read_csv(os.path.join(uip_root, f'{m}_pred.csv'))[['material_id', 'e_form_pred']]
        base = base.merge(p.rename(columns={'e_form_pred': f'eform_{m}'}),
                          on='material_id', how='inner')
    base = base.dropna().reset_index(drop=True)
    base['family'] = base['formula'].apply(anion_family)
    return base


# ----------------------------- matched-yield arm (the tested/mockable core) -----------------------------

def run_matched_yield_arm(base_df: pd.DataFrame, models: List[str],
                          fams: Optional[List[str]] = None) -> Dict:
    """Corrected matched-yield-control gain per (model, stratum), IDENTICAL math to
    mt29_stage1_matched_yield_fix.main() but generalized over `models`/a supplied
    dataframe so it can run on the full WBM merge OR a tiny synthetic fixture — this is
    the function pytest and --smoke exercise directly, with no file I/O."""
    fams = fams if fams is not None else FAM_ORDER
    eft = base_df['e_form_per_atom_mp2020_corrected'].values
    ht = base_df['e_above_hull_mp2020_corrected_ppd_mp'].values
    true_stable = ht < 0.0
    fam_idx = {f: np.where(base_df['family'].values == f)[0] for f in fams}
    fam_idx = {f: idx for f, idx in fam_idx.items() if len(idx) > 0}

    pred_hull = {m: ht + (base_df[f'eform_{m}'].values - eft) for m in models}
    conf = {m: np.abs(pred_hull[m]) for m in models}
    pred_stable = {m: pred_hull[m] < 0.0 for m in models}

    per_model = {}
    for m in models:
        cs_conf, cs_st, br, total_cs = {}, {}, {}, {}
        for f, idx in fam_idx.items():
            sp = pred_stable[m][idx]
            cs = np.where(sp)[0]
            cs_conf[f] = conf[m][idx][cs]
            cs_st[f] = true_stable[idx][cs]
            br[f] = float(true_stable[idx].mean())
            total_cs[f] = len(cs)
        if not total_cs or min(total_cs.values()) == 0:
            per_model[m] = {'skipped': True,
                            'reason': 'a stratum has zero called-stable structures for this model/fixture'}
            continue
        y_loose = min(total_cs.values())
        y_tight = max(1, y_loose // 2)
        gains = {f: boot_yield_gain(cs_conf[f], cs_st[f], br[f], y_tight, y_loose, False)
                for f in fam_idx}
        per_model[m] = {
            'y_loose': int(y_loose), 'y_tight': int(y_tight),
            'total_called_stable': {f: int(total_cs[f]) for f in fam_idx},
            'base_rate_stable': {f: round(br[f], 5) for f in fam_idx},
            'gain_median': {f: (round(float(np.median(gains[f])), 5) if len(gains[f]) else None)
                           for f in fam_idx},
        }
    return per_model


def interactions_from_gains(per_model: Dict, models: List[str]) -> Dict:
    """Pairwise stratum interactions (gain_A - gain_B) from the point-estimate
    gain_median table (a lightweight companion to run_matched_yield_arm's bootstrap
    output, sufficient for the arm-verification report)."""
    inter = []
    for m in models:
        pm = per_model.get(m, {})
        gm = pm.get('gain_median')
        if not gm:
            continue
        fams = list(gm.keys())
        for i in range(len(fams)):
            for j in range(i + 1, len(fams)):
                a, b = fams[i], fams[j]
                if gm[a] is None or gm[b] is None:
                    continue
                inter.append({'model': m, 'stratumA': a, 'stratumB': b,
                              'interaction_med': round(gm[a] - gm[b], 5)})
    return inter


# ----------------------------- smoke path (no real WBM/UIP files) -----------------------------

def _synthetic_fixture(seed: int = 0) -> pd.DataFrame:
    """Tiny hand-constructed fixture: 2 families x 60 rows, base-4 models + 1 synthetic
    'oam_toy' model whose predicted formation energy is a small perturbation of the
    truth (so the matched-yield-gain math has non-degenerate signal to run on, without
    touching real WBM/UIP files or the network)."""
    rng = np.random.default_rng(seed)
    rows = []
    for fam, n in [('oxide', 60), ('halide', 60)]:
        eform_true = rng.normal(-2.0, 0.5, n)
        hull_true = rng.normal(0.0, 0.05, n)
        for i in range(n):
            row = {'material_id': f'{fam}-{i}', 'formula': 'NaO' if fam == 'oxide' else 'NaCl',
                  'e_form_per_atom_mp2020_corrected': eform_true[i],
                  'e_above_hull_mp2020_corrected_ppd_mp': hull_true[i], 'family': fam}
            for m in BASE_MODELS + ['oam_toy']:
                row[f'eform_{m}'] = eform_true[i] + rng.normal(0, 0.02)
            rows.append(row)
    return pd.DataFrame(rows)


def _run_smoke() -> int:
    base_df = _synthetic_fixture()
    models = BASE_MODELS + ['oam_toy']
    per_model = run_matched_yield_arm(base_df, models, fams=['oxide', 'halide'])
    assert 'oam_toy' in per_model, per_model
    assert set(BASE_MODELS).issubset(per_model.keys())
    inter = interactions_from_gains(per_model, models)
    payload = {'per_model_budgets': per_model, 'interactions': inter}
    json.dumps(payload, default=str)  # prove JSON-serializable, no disk write in smoke
    print('SMOKE OK: matched-yield arm ran on a synthetic 2-family/5-model fixture '
          f'(oam_toy included). {len(inter)} pairwise interaction cells computed.')
    return 0


# ----------------------------- CLI -----------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--wbm-summary', default=DEFAULT_WBM_SUMMARY)
    ap.add_argument('--uip-root', default=DEFAULT_UIP_ROOT)
    ap.add_argument('--oam-models', default=None,
                    help='comma-separated OAM model keys (pred-CSV stems); default: '
                         'auto-discover in --uip-root beyond the base 4')
    ap.add_argument('--smoke', action='store_true',
                    help='CPU-only, no real WBM/UIP files, no network')
    args = ap.parse_args(argv)

    if args.smoke:
        return _run_smoke()

    oam_models = args.oam_models.split(',') if args.oam_models else discover_oam_models(args.uip_root)
    models = BASE_MODELS + oam_models
    if not oam_models:
        print('WARNING: no OAM-era prediction CSVs found beyond the base 4 in '
              f'{args.uip_root!r} -- run mt29_uip_inference.py first (see '
              'RUNME_CONTAINER.md). Continuing with base-4-only for pipeline '
              'verification; result JSON records oam_models_found: [] so this run is '
              'never mistaken for the real arm.')

    base_df = load_extended(args.wbm_summary, args.uip_root, models)
    per_model = run_matched_yield_arm(base_df, models)
    inter = interactions_from_gains(per_model, models)

    results = {
        'meta': {
            'story': 'G007-s1-materials-mt29-oam-arm',
            'stage': 'NEXT-EXPERIMENTS.md item 1 (OAM-era UIP refresh)',
            'seed': SEED, 'n_boot': N_BOOT, 'base_models': BASE_MODELS,
            'oam_models_found': oam_models, 'models': models, 'strata': FAM_ORDER,
            'n_rows': int(len(base_df)),
            'control': 'identical corrected matched-yield control as '
                       'mt29_stage1_matched_yield_fix.py, generalized over an '
                       'OAM-extended model list; frozen canonical result JSONs untouched.',
        },
        'per_model_budgets': per_model,
        'interactions': inter,
    }
    if stamp_result is not None:
        stamp_result(results, __file__, seeds=[SEED])

    if os.path.exists(OUT_JSON):
        print(f'REFUSING to overwrite existing {OUT_JSON}', file=sys.stderr)
        return 1
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_JSON, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f'Wrote {OUT_JSON}')

    try:
        git_sha = subprocess.check_output(
            ['git', '-C', '/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research',
             'rev-parse', 'HEAD'], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        git_sha = None
    manifest = {
        'cmd': ' '.join([sys.executable] + sys.argv),
        'script_sha256': sha256(os.path.abspath(__file__)),
        'git_head': git_sha, 'seed': SEED, 'n_boot': N_BOOT,
        'models': models, 'oam_models_found': oam_models,
        'inputs': {os.path.basename(args.wbm_summary): sha256(args.wbm_summary),
                  **{f'{m}_pred.csv': sha256(os.path.join(args.uip_root, f'{m}_pred.csv'))
                     for m in models}},
        'output_sha256': sha256(OUT_JSON),
        'versions': {'python': platform.python_version(), 'numpy': np.__version__,
                    'pandas': pd.__version__},
        'platform': platform.platform(),
    }
    with open(MANIFEST, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f'Wrote {MANIFEST}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
