#!/usr/bin/env python3
"""pytest tests for research/results/MT29/mt29_hull_recompute_validation.py (Arm 2b —
hull-recompute validation-subset script). CPU-only, no network, no pymatgen, no real
MP/WBM data. Run: python -m pytest tests/test_hull_recompute_validation.py -v
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

import mt29_hull_recompute_validation as hrv  # noqa: E402


# ---------------------------------------------------------------------------
# stratified_sample
# ---------------------------------------------------------------------------

def test_stratified_sample_respects_per_family_cap():
    base_df = pd.DataFrame({'family': ['oxide'] * 100 + ['halide'] * 100, 'v': range(200)})
    sample = hrv.stratified_sample(base_df, fams=['oxide', 'halide'], n_total=20, seed=0)
    counts = sample['family'].value_counts().to_dict()
    assert counts['oxide'] == 10
    assert counts['halide'] == 10


def test_stratified_sample_handles_small_family():
    base_df = pd.DataFrame({'family': ['oxide'] * 3 + ['halide'] * 100, 'v': range(103)})
    sample = hrv.stratified_sample(base_df, fams=['oxide', 'halide'], n_total=20, seed=0)
    counts = sample['family'].value_counts().to_dict()
    assert counts['oxide'] == 3  # capped by availability, not the per-family target
    assert counts['halide'] == 10


def test_stratified_sample_skips_absent_family():
    base_df = pd.DataFrame({'family': ['oxide'] * 20, 'v': range(20)})
    sample = hrv.stratified_sample(base_df, fams=['oxide', 'halide'], n_total=20, seed=0)
    assert set(sample['family']) == {'oxide'}


def test_stratified_sample_deterministic_given_seed():
    base_df = pd.DataFrame({'family': ['oxide'] * 50, 'v': range(50)})
    s1 = hrv.stratified_sample(base_df, fams=['oxide'], n_total=10, seed=42)
    s2 = hrv.stratified_sample(base_df, fams=['oxide'], n_total=10, seed=42)
    assert s1['v'].tolist() == s2['v'].tolist()


# ---------------------------------------------------------------------------
# evaluate_structure — hand-checkable binary A-B toy system (same as test_hull_math.py)
# ---------------------------------------------------------------------------

def test_evaluate_structure_stable_compound_recompute():
    elements = ('A', 'B')
    ref_symbols_list = [['A'], ['B'], ['A', 'B']]
    ref_energies = [0.0, 0.0, -1.0]
    ev = hrv.evaluate_structure(elements, ref_symbols_list, ref_energies,
                                ['A', 'B'], e_form_true=-1.0,
                                e_form_pred_by_model={'m1': -0.8, 'm2': -1.0})
    assert ev['hull_energy_at_query'] == pytest.approx(-1.0, abs=1e-6)
    # true energy IS the hull point -> e_above_hull_true_recomputed == 0
    assert ev['e_above_hull_true_recomputed'] == pytest.approx(0.0, abs=1e-6)
    # m1 predicted worse (higher) energy -> positive e_above_hull (correctly above hull)
    assert ev['e_above_hull_pred_recomputed']['m1'] == pytest.approx(0.2, abs=1e-6)
    # m2 predicted exactly the hull energy -> zero
    assert ev['e_above_hull_pred_recomputed']['m2'] == pytest.approx(0.0, abs=1e-6)


def test_evaluate_structure_pure_element_query():
    elements = ('A', 'B')
    ref_symbols_list = [['A'], ['B'], ['A', 'B']]
    ref_energies = [0.0, 0.0, -1.0]
    ev = hrv.evaluate_structure(elements, ref_symbols_list, ref_energies,
                                ['A'], e_form_true=0.02,
                                e_form_pred_by_model={'m1': -0.01})
    assert ev['hull_energy_at_query'] == pytest.approx(0.0, abs=1e-6)
    assert ev['e_above_hull_true_recomputed'] == pytest.approx(0.02, abs=1e-6)
    assert ev['e_above_hull_pred_recomputed']['m1'] == pytest.approx(-0.01, abs=1e-6)


# ---------------------------------------------------------------------------
# summarize_deltas
# ---------------------------------------------------------------------------

def test_summarize_deltas_zero_when_fixed_equals_recomputed():
    rows = [
        {'family': 'oxide', 'hull_pred_fixed': {'m1': 0.1}, 'hull_pred_recomputed': {'m1': 0.1}},
        {'family': 'oxide', 'hull_pred_fixed': {'m1': -0.2}, 'hull_pred_recomputed': {'m1': -0.2}},
    ]
    out = hrv.summarize_deltas(rows, ['m1'])
    assert out['oxide']['n'] == 2
    assert out['oxide']['per_model']['m1']['delta_mean'] == pytest.approx(0.0)
    assert out['oxide']['per_model']['m1']['n_flips'] == 0


def test_summarize_deltas_detects_stable_call_flip():
    # fixed says stable (-0.01 < 0), recomputed says unstable (+0.02 > 0) -> a flip.
    rows = [
        {'family': 'halide', 'hull_pred_fixed': {'m1': -0.01}, 'hull_pred_recomputed': {'m1': 0.02}},
        {'family': 'halide', 'hull_pred_fixed': {'m1': 0.5}, 'hull_pred_recomputed': {'m1': 0.5}},
    ]
    out = hrv.summarize_deltas(rows, ['m1'])
    assert out['halide']['per_model']['m1']['n_flips'] == 1
    assert out['halide']['per_model']['m1']['flip_rate'] == pytest.approx(0.5)


def test_summarize_deltas_separates_strata():
    rows = [
        {'family': 'oxide', 'hull_pred_fixed': {'m1': 0.1}, 'hull_pred_recomputed': {'m1': 0.05}},
        {'family': 'halide', 'hull_pred_fixed': {'m1': -0.1}, 'hull_pred_recomputed': {'m1': -0.2}},
    ]
    out = hrv.summarize_deltas(rows, ['m1'])
    assert set(out.keys()) == {'oxide', 'halide'}
    assert out['oxide']['per_model']['m1']['delta_mean'] == pytest.approx(0.05, abs=1e-6)
    assert out['halide']['per_model']['m1']['delta_mean'] == pytest.approx(0.1, abs=1e-6)


# ---------------------------------------------------------------------------
# load_mp_reference_entries: pymatgen-gated, must fail clearly when pymatgen absent
# ---------------------------------------------------------------------------

def test_load_mp_reference_entries_raises_clear_error_without_pymatgen():
    try:
        import pymatgen  # noqa: F401
        pytest.skip('pymatgen is installed in this environment; guard-path not exercised')
    except ImportError:
        pass
    with pytest.raises(RuntimeError, match='pymatgen'):
        hrv.load_mp_reference_entries('/nonexistent/path.pkl')


# ---------------------------------------------------------------------------
# smoke / CLI
# ---------------------------------------------------------------------------

def test_main_smoke_returns_zero():
    assert hrv.main(['--smoke']) == 0


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-v']))
