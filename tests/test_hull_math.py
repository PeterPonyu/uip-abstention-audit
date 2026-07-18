#!/usr/bin/env python3
"""pytest tests for research/results/MT29/mt29_hull_math.py (Arm 2a — convex-hull
recompute math). Hand-checkable toy systems only: numpy/scipy, no pymatgen, no
network, no real WBM/MP data. Run: python -m pytest tests/test_hull_math.py -v
"""
import os
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MT29 = os.path.join(REPO, 'research', 'results', 'MT29')
sys.path.insert(0, MT29)

from mt29_hull_math import (  # noqa: E402
    composition_fractions, e_above_hull, formula_to_symbols, hull_energy_at,
    lower_hull_mask,
)


# ---------------------------------------------------------------------------
# formula_to_symbols
# ---------------------------------------------------------------------------

def test_formula_to_symbols_multi_element():
    assert formula_to_symbols('Fe3Al') == ['Fe', 'Fe', 'Fe', 'Al']


def test_formula_to_symbols_no_counts():
    assert formula_to_symbols('NaCl') == ['Na', 'Cl']


def test_formula_to_symbols_multidigit_count():
    assert formula_to_symbols('O12') == ['O'] * 12


# ---------------------------------------------------------------------------
# composition_fractions
# ---------------------------------------------------------------------------

def test_composition_fractions_binary():
    frac = composition_fractions(['Na', 'Cl'], ['Na', 'Cl'])
    assert np.allclose(frac, [0.5, 0.5])
    assert np.isclose(frac.sum(), 1.0)


def test_composition_fractions_pure_element():
    frac = composition_fractions(['Fe', 'Fe', 'Fe'], ['Fe', 'Al'])
    assert np.allclose(frac, [1.0, 0.0])


def test_composition_fractions_empty_raises():
    with pytest.raises(ValueError):
        composition_fractions([], ['Fe', 'Al'])


def test_composition_fractions_unknown_element_raises():
    with pytest.raises(ValueError):
        composition_fractions(['Xx'], ['Fe', 'Al'])


# ---------------------------------------------------------------------------
# lower_hull_mask / hull_energy_at / e_above_hull — hand-checkable binary A-B system
#
# Toy system: pure A (comp [1,0], E=0.0), pure B (comp [0,1], E=0.0), and an AB
# compound at comp [0.5, 0.5]. Two variants:
#   (a) STABLE compound: E(AB) = -1.0 (below the A-B tie line at 0.0) -> all three
#       points on the lower hull; hull energy at [0.5,0.5] is -1.0.
#   (b) UNSTABLE compound: E(AB) = +0.3 (above the tie line) -> only pure A/B on the
#       lower hull; hull energy at [0.5,0.5] interpolates to 0.0 (the tie line).
# ---------------------------------------------------------------------------

ELEMENTS_AB = ['A', 'B']


def _binary_system(compound_energy):
    comp_fracs = np.array([[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]])
    energies = np.array([0.0, 0.0, compound_energy])
    return comp_fracs, energies


def test_lower_hull_mask_stable_compound_all_on_hull():
    comp_fracs, energies = _binary_system(-1.0)
    mask = lower_hull_mask(comp_fracs, energies)
    assert mask.tolist() == [True, True, True]


def test_lower_hull_mask_unstable_compound_excluded():
    comp_fracs, energies = _binary_system(0.3)
    mask = lower_hull_mask(comp_fracs, energies)
    # pure A and pure B are on the hull; the above-tie-line compound is not.
    assert mask.tolist() == [True, True, False]


def test_hull_energy_at_stable_compound_composition():
    comp_fracs, energies = _binary_system(-1.0)
    he = hull_energy_at(np.array([0.5, 0.5]), comp_fracs, energies)
    assert he == pytest.approx(-1.0, abs=1e-6)


def test_hull_energy_at_unstable_compound_composition_interpolates_tie_line():
    comp_fracs, energies = _binary_system(0.3)
    he = hull_energy_at(np.array([0.5, 0.5]), comp_fracs, energies)
    # tie line between (0,0.0) and (1,0.0) at x=0.5 is 0.0, NOT the compound's own
    # (excluded, above-hull) energy of 0.3.
    assert he == pytest.approx(0.0, abs=1e-6)


def test_hull_energy_at_pure_element_composition():
    comp_fracs, energies = _binary_system(-1.0)
    he_a = hull_energy_at(np.array([1.0, 0.0]), comp_fracs, energies)
    he_b = hull_energy_at(np.array([0.0, 1.0]), comp_fracs, energies)
    assert he_a == pytest.approx(0.0, abs=1e-6)
    assert he_b == pytest.approx(0.0, abs=1e-6)


def test_e_above_hull_stable_query_is_negative():
    comp_fracs, energies = _binary_system(-1.0)
    # a hypothetical query at the compound composition, predicted BELOW the hull's
    # own defining point (-1.0) -> e_above_hull negative (would redefine the hull,
    # but relative to the CURRENT reference hull it reads as negative/on-hull).
    e_ah = e_above_hull(np.array([0.5, 0.5]), -1.2, comp_fracs, energies)
    assert e_ah == pytest.approx(-0.2, abs=1e-6)


def test_e_above_hull_unstable_query_is_positive_and_hand_checkable():
    comp_fracs, energies = _binary_system(-1.0)
    # query at the compound composition with a WORSE (higher) predicted energy than
    # the true hull point -> e_above_hull = query_energy - hull_energy = -0.5 - (-1.0)
    e_ah = e_above_hull(np.array([0.5, 0.5]), -0.5, comp_fracs, energies)
    assert e_ah == pytest.approx(0.5, abs=1e-6)


def test_e_above_hull_pure_element_hand_checkable():
    comp_fracs, energies = _binary_system(-1.0)
    # pure-A query 0.05 eV/atom above the pure-A reference point (hull energy 0.0)
    e_ah = e_above_hull(np.array([1.0, 0.0]), 0.05, comp_fracs, energies)
    assert e_ah == pytest.approx(0.05, abs=1e-6)


# ---------------------------------------------------------------------------
# Ternary sanity check: A-B-C system, a stable ternary compound at the centroid.
# ---------------------------------------------------------------------------

def test_ternary_stable_centroid_compound_on_hull():
    comp_fracs = np.array([
        [1.0, 0.0, 0.0],   # pure A
        [0.0, 1.0, 0.0],   # pure B
        [0.0, 0.0, 1.0],   # pure C
        [1 / 3, 1 / 3, 1 / 3],  # ABC ternary compound, well below the ABC facet
    ])
    energies = np.array([0.0, 0.0, 0.0, -2.0])
    mask = lower_hull_mask(comp_fracs, energies)
    assert mask.tolist() == [True, True, True, True]
    he = hull_energy_at(np.array([1 / 3, 1 / 3, 1 / 3]), comp_fracs, energies)
    assert he == pytest.approx(-2.0, abs=1e-6)
    # a query at the same composition but a worse energy is above-hull.
    e_ah = e_above_hull(np.array([1 / 3, 1 / 3, 1 / 3]), -1.0, comp_fracs, energies)
    assert e_ah == pytest.approx(1.0, abs=1e-6)


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-v']))
