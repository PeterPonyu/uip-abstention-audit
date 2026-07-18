#!/usr/bin/env python3
"""pytest tests for research/results/MT29/mt29_stage1_oam_arm.py (Arm 1b — OAM-era UIP
analysis hookup). CPU-only, no real WBM/UIP files, no network. Run:
python -m pytest tests/test_stage1_oam_arm.py -v
"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MT29 = os.path.join(REPO, 'research', 'results', 'MT29')
COMMONS = os.path.abspath(os.path.join(REPO, '..', 'reliability-commons'))
sys.path.insert(0, MT29)
sys.path.insert(0, COMMONS)

import mt29_stage1_oam_arm as arm  # noqa: E402


# ---------------------------------------------------------------------------
# discover_oam_models
# ---------------------------------------------------------------------------

def test_discover_oam_models_finds_extra_pred_csv(tmp_path):
    for name in ['chgnet', 'm3gnet', 'mace', 'orb', 'sevennet_mf_ompa']:
        (tmp_path / f'{name}_pred.csv').write_text('material_id,e_form_pred\nwbm-1,0.1\n')
    found = arm.discover_oam_models(str(tmp_path))
    assert found == ['sevennet_mf_ompa']


def test_discover_oam_models_empty_when_only_base_four(tmp_path):
    for name in arm.BASE_MODELS:
        (tmp_path / f'{name}_pred.csv').write_text('material_id,e_form_pred\nwbm-1,0.1\n')
    assert arm.discover_oam_models(str(tmp_path)) == []


def test_discover_oam_models_empty_dir(tmp_path):
    assert arm.discover_oam_models(str(tmp_path)) == []


# ---------------------------------------------------------------------------
# load_extended — synthetic tiny WBM summary + pred CSVs
# ---------------------------------------------------------------------------

def test_load_extended_merges_and_tags_family(tmp_path):
    wbm = pd.DataFrame({
        'material_id': ['wbm-1', 'wbm-2', 'wbm-3'],
        'formula': ['NaCl', 'SiO2', 'Fe3Al'],
        'e_form_per_atom_mp2020_corrected': [-1.0, -2.0, -0.5],
        'e_above_hull_mp2020_corrected_ppd_mp': [0.01, -0.02, 0.03],
        'unique_prototype': [True, True, True],
    })
    wbm_path = tmp_path / 'wbm-summary.csv.gz'
    wbm.to_csv(wbm_path, index=False, compression='gzip')

    for m in arm.BASE_MODELS + ['oam_toy']:
        preds = pd.DataFrame({'material_id': ['wbm-1', 'wbm-2', 'wbm-3'],
                              'e_form_pred': [-1.01, -1.99, -0.48]})
        preds.to_csv(tmp_path / f'{m}_pred.csv', index=False)

    df = arm.load_extended(str(wbm_path), str(tmp_path), arm.BASE_MODELS + ['oam_toy'])
    assert len(df) == 3
    assert set(df['family']) == {'halide', 'oxide', 'intermetallic'}
    for m in arm.BASE_MODELS + ['oam_toy']:
        assert f'eform_{m}' in df.columns


# ---------------------------------------------------------------------------
# run_matched_yield_arm — hand-checkable synthetic fixture
# ---------------------------------------------------------------------------

def _perfectly_ranked_family(n, seed):
    """Confidence perfectly ranks true-stable structures to the top -- the
    matched-yield gain for this family/model should be clearly non-negative (tight
    budget outperforms or matches loose budget)."""
    rng = np.random.default_rng(seed)
    half = n // 2
    true_stable = np.array([True] * half + [False] * (n - half))
    # hull_pred < 0 for ALL rows (all called stable) but |hull_pred| (confidence) is
    # highest for the truly-stable half.
    hull_pred = np.where(true_stable, -rng.uniform(0.5, 1.0, n), -rng.uniform(0.0, 0.05, n))
    eform_true = rng.normal(-2.0, 0.3, n)
    hull_true = np.where(true_stable, -rng.uniform(0.01, 0.05, n), rng.uniform(0.01, 0.05, n))
    eform_pred = eform_true + (hull_pred - hull_true)
    return eform_true, hull_true, eform_pred


def test_run_matched_yield_arm_runs_on_synthetic_fixture_with_oam_model():
    rows = []
    for fam, seed in [('oxide', 1), ('halide', 2)]:
        eft, ht, efp = _perfectly_ranked_family(200, seed)
        for i in range(200):
            row = {'material_id': f'{fam}-{i}', 'formula': 'X', 'family': fam,
                  'e_form_per_atom_mp2020_corrected': eft[i],
                  'e_above_hull_mp2020_corrected_ppd_mp': ht[i]}
            for m in arm.BASE_MODELS + ['oam_toy']:
                row[f'eform_{m}'] = efp[i]
            rows.append(row)
    base_df = pd.DataFrame(rows)

    per_model = arm.run_matched_yield_arm(base_df, arm.BASE_MODELS + ['oam_toy'],
                                          fams=['oxide', 'halide'])
    assert 'oam_toy' in per_model
    pm = per_model['oam_toy']
    assert not pm.get('skipped', False)
    assert 'gain_median' in pm
    assert set(pm['gain_median'].keys()) == {'oxide', 'halide'}
    # confidence perfectly ranks true-stable to the top -> tight-budget precision
    # should be >= loose-budget precision -> gain >= 0 (allow float noise).
    for fam, gain in pm['gain_median'].items():
        assert gain is not None
        assert gain >= -1e-6, (fam, gain)


def test_run_matched_yield_arm_skips_when_no_called_stable():
    # a model that never calls anything stable -> that stratum has 0 called-stable ->
    # this model should be marked skipped, not crash.
    n = 20
    base_df = pd.DataFrame({
        'material_id': [f'x{i}' for i in range(n)],
        'formula': ['X'] * n, 'family': ['oxide'] * n,
        'e_form_per_atom_mp2020_corrected': [-1.0] * n,
        'e_above_hull_mp2020_corrected_ppd_mp': [0.5] * n,  # all unstable
        'eform_dead_model': [10.0] * n,  # always predicts high hull dist -> never stable
    })
    per_model = arm.run_matched_yield_arm(base_df, ['dead_model'], fams=['oxide'])
    assert per_model['dead_model'].get('skipped') is True


# ---------------------------------------------------------------------------
# interactions_from_gains
# ---------------------------------------------------------------------------

def test_interactions_from_gains_pairs_all_strata():
    per_model = {
        'm1': {'gain_median': {'oxide': 0.3, 'halide': 0.1, 'chalcogenide': 0.2}},
    }
    inter = arm.interactions_from_gains(per_model, ['m1'])
    assert len(inter) == 3  # C(3,2)
    pairs = {(r['stratumA'], r['stratumB']) for r in inter}
    assert ('oxide', 'halide') in pairs


def test_interactions_from_gains_skips_missing_model():
    per_model = {'m1': {'skipped': True}}
    inter = arm.interactions_from_gains(per_model, ['m1'])
    assert inter == []


# ---------------------------------------------------------------------------
# smoke / CLI
# ---------------------------------------------------------------------------

def test_main_smoke_returns_zero():
    assert arm.main(['--smoke']) == 0


def test_synthetic_fixture_has_expected_shape():
    df = arm._synthetic_fixture()
    assert len(df) == 120
    assert set(df['family']) == {'oxide', 'halide'}
    assert 'eform_oam_toy' in df.columns


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-v']))
