#!/usr/bin/env python3
"""pytest tests for research/results/MT29/mt29_uip_inference.py (Arm 1a — OAM-era UIP
frozen-inference harness). CPU-only, no ase/torch/fairchem/sevenn, no network, no real
checkpoint. Mocks the UIP interface at its introduced boundary (`.total_energy(structure)
-> float`). Run: python -m pytest tests/test_uip_inference.py -v
"""
import os
import sys

import pandas as pd
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MT29 = os.path.join(REPO, 'research', 'results', 'MT29')
sys.path.insert(0, MT29)

import mt29_uip_inference as inf  # noqa: E402


# ---------------------------------------------------------------------------
# formation_energy_per_atom — pure arithmetic, hand-checkable
# ---------------------------------------------------------------------------

def test_formation_energy_per_atom_hand_checkable():
    # NaCl cell, total energy -4.0 eV, elemental refs -1.0 each -> (-4 - (-2))/2 = -1.0
    e = inf.formation_energy_per_atom(-4.0, ['Na', 'Cl'], {'Na': -1.0, 'Cl': -1.0})
    assert e == pytest.approx(-1.0)


def test_formation_energy_per_atom_zero_refs():
    e = inf.formation_energy_per_atom(-6.0, ['Fe', 'Fe', 'Al'], {'Fe': 0.0, 'Al': 0.0})
    assert e == pytest.approx(-2.0)


def test_formation_energy_per_atom_empty_raises():
    with pytest.raises(ValueError):
        inf.formation_energy_per_atom(0.0, [], {})


def test_formation_energy_per_atom_missing_ref_raises():
    with pytest.raises(KeyError):
        inf.formation_energy_per_atom(-1.0, ['Xx'], {'Na': 0.0})


# ---------------------------------------------------------------------------
# predict_formation_energies — the mockable UIP-interface boundary
# ---------------------------------------------------------------------------

class ConstantCalc:
    """Mock calculator: total energy is always the same constant, independent of
    structure (proves the boundary is exercised without any real ML library)."""

    def __init__(self, constant):
        self.constant = constant

    def total_energy(self, structure):
        return self.constant


class PerAtomCalc:
    """Mock calculator: total energy = -2.0 eV/atom * n_atoms."""

    def total_energy(self, structure):
        return -2.0 * len(structure.symbols)


def test_predict_formation_energies_schema_and_values():
    structures = [
        inf.Structure('m1', ['Na', 'Cl']),
        inf.Structure('m2', ['Fe', 'Al']),
    ]
    ref_energies = {'Na': 0.0, 'Cl': 0.0, 'Fe': 0.0, 'Al': 0.0}
    df = inf.predict_formation_energies(PerAtomCalc(), structures, ref_energies)
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ['material_id', 'e_form_pred']
    assert df['material_id'].tolist() == ['m1', 'm2']
    assert df['e_form_pred'].tolist() == pytest.approx([-2.0, -2.0])


def test_predict_formation_energies_known_energies_per_structure():
    # 3 known "energies" (a synthetic toy set with known formation energies), verify
    # each row independently rather than assuming a constant.
    structures = [
        inf.Structure('a', ['Na']),          # 1 atom
        inf.Structure('b', ['Na', 'Na']),    # 2 atoms
        inf.Structure('c', ['Na', 'Cl', 'Cl']),  # 3 atoms
    ]
    ref_energies = {'Na': -1.0, 'Cl': -0.5}

    class KnownCalc:
        totals = {'a': -1.5, 'b': -3.4, 'c': -3.0}

        def total_energy(self, structure):
            return self.totals[structure.material_id]

    df = inf.predict_formation_energies(KnownCalc(), structures, ref_energies)
    got = dict(zip(df['material_id'], df['e_form_pred']))
    assert got['a'] == pytest.approx((-1.5 - (-1.0)) / 1)
    assert got['b'] == pytest.approx((-3.4 - (-2.0)) / 2)
    assert got['c'] == pytest.approx((-3.0 - (-2.0)) / 3)


def test_predict_formation_energies_empty_structures():
    df = inf.predict_formation_energies(ConstantCalc(0.0), [], {})
    assert list(df.columns) == ['material_id', 'e_form_pred']
    assert len(df) == 0


# ---------------------------------------------------------------------------
# build_calculator / checkpoint gate
# ---------------------------------------------------------------------------

def test_build_calculator_unknown_model_raises():
    with pytest.raises(ValueError):
        inf.build_calculator('not-a-real-model', None)


def test_build_calculator_gated_model_without_checkpoint_raises_requires_user_checkpoint():
    with pytest.raises(inf.RequiresUserCheckpoint) as exc_info:
        inf.build_calculator('esen-30m-oam', None)
    assert 'REQUIRES_USER_CHECKPOINT' in str(exc_info.value)


def test_build_calculator_gated_model_with_nonexistent_checkpoint_path_raises():
    with pytest.raises(inf.RequiresUserCheckpoint):
        inf.build_calculator('esen-30m-oam', '/nonexistent/path/checkpoint.pt')


def test_build_calculator_gated_model_with_real_checkpoint_path_succeeds(tmp_path):
    ckpt = tmp_path / 'fake_checkpoint.pt'
    ckpt.write_bytes(b'not a real checkpoint, just proves the existence gate')
    calc = inf.build_calculator('esen-30m-oam', str(ckpt))
    assert isinstance(calc, inf._EsenCalculator)


def test_build_calculator_ungated_model_without_checkpoint_succeeds():
    calc = inf.build_calculator('sevennet-mf-ompa', None)
    assert isinstance(calc, inf._SevenNetCalculator)


# ---------------------------------------------------------------------------
# MODEL_REGISTRY — registry resolution / metadata for the three new current-gen UIPs
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('model_key,expected_class', [
    ('mace-mp-0', 'MACE'),
    ('orb-v3', 'ORB'),
    ('mattersim', 'MatterSim'),
])
def test_registry_new_models_present_ungated_with_metadata(model_key, expected_class):
    assert model_key in inf.MODEL_REGISTRY
    spec = inf.MODEL_REGISTRY[model_key]
    assert spec['gated'] is False
    assert expected_class in spec['family']
    assert spec['year'] >= 2024
    assert isinstance(spec['training_data'], str) and spec['training_data']
    assert isinstance(spec['hint'], str) and spec['hint']


def test_build_calculator_mace_mp_0_ungated_succeeds():
    calc = inf.build_calculator('mace-mp-0', None)
    assert isinstance(calc, inf._MaceCalculator)


def test_build_calculator_orb_v3_ungated_succeeds():
    calc = inf.build_calculator('orb-v3', None)
    assert isinstance(calc, inf._OrbCalculator)


def test_build_calculator_mattersim_ungated_succeeds():
    calc = inf.build_calculator('mattersim', None)
    assert isinstance(calc, inf._MatterSimCalculator)


# ---------------------------------------------------------------------------
# caller-shaped real-path regression tests: build_calculator(...) ->
# predict_formation_energies(...) through each new adapter's REAL total_energy()
# (Atoms construction + .calc wiring), with ONLY the lazy ML-library import
# (`_lazy()`) monkeypatched to a fake ase-compatible calculator -- no
# mace/orb_models/mattersim install required, but the adapter's own Atoms/pbc
# plumbing IS exercised (the "geo 8-band lesson": mock at the library boundary,
# not the adapter boundary).
# ---------------------------------------------------------------------------

class _FakeAseBackedCalc:
    """Duck-types the `.get_potential_energy(atoms)` signature ase.Atoms expects
    from a real attached Calculator (see Atoms.get_potential_energy source)."""

    def get_potential_energy(self, atoms):
        return -2.0 * len(atoms)


def test_mace_calculator_total_energy_through_predict_formation_energies():
    calc = inf.build_calculator('mace-mp-0', None)
    calc._lazy = lambda: _FakeAseBackedCalc()
    structures = [inf.Structure('m1', ['Na', 'Cl'], positions=[[0, 0, 0], [1, 1, 1]],
                                cell=[[3, 0, 0], [0, 3, 0], [0, 0, 3]])]
    df = inf.predict_formation_energies(calc, structures, {'Na': 0.0, 'Cl': 0.0})
    assert list(df.columns) == ['material_id', 'e_form_pred']
    assert df['e_form_pred'].tolist() == pytest.approx([-2.0])


def test_orb_calculator_total_energy_through_predict_formation_energies():
    calc = inf.build_calculator('orb-v3', None)
    calc._lazy = lambda: _FakeAseBackedCalc()
    structures = [inf.Structure('m1', ['Fe', 'Al'], positions=[[0, 0, 0], [1, 1, 1]],
                                cell=[[3, 0, 0], [0, 3, 0], [0, 0, 3]])]
    df = inf.predict_formation_energies(calc, structures, {'Fe': 0.0, 'Al': 0.0})
    assert list(df.columns) == ['material_id', 'e_form_pred']
    assert df['e_form_pred'].tolist() == pytest.approx([-2.0])


def test_mattersim_calculator_total_energy_through_predict_formation_energies():
    calc = inf.build_calculator('mattersim', None)
    calc._lazy = lambda: _FakeAseBackedCalc()
    structures = [inf.Structure('m1', ['O', 'O', 'O'], positions=[[0, 0, 0], [1, 1, 1], [2, 2, 2]],
                                cell=[[4, 0, 0], [0, 4, 0], [0, 0, 4]])]
    df = inf.predict_formation_energies(calc, structures, {'O': 0.0})
    assert list(df.columns) == ['material_id', 'e_form_pred']
    assert df['e_form_pred'].tolist() == pytest.approx([-2.0])


# ---------------------------------------------------------------------------
# CLI --smoke path
# ---------------------------------------------------------------------------

def test_main_smoke_returns_zero():
    assert inf.main(['--smoke']) == 0


def test_main_without_ref_energies_json_fails_fast():
    # a real (non-smoke) run without --ref-energies-json should fail cleanly, not
    # attempt any network/ase/checkpoint work.
    rc = inf.main(['--model', 'sevennet-mf-ompa'])
    assert rc == 2


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-v']))
