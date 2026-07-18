#!/usr/bin/env python
"""MT29 — Arm 1a (NEXT-EXPERIMENTS.md item 1; roster extended per
EXPANSION-PLAN-2026-07-09.md Sec.2.4): frozen-inference harness for current-gen
(2024-26) universal interatomic potentials over the WBM test-set structures — a
5-entry MODEL_REGISTRY (eSEN-30M-OAM [gated primary], SevenNet-MF-ompa [un-gated
OAM-era fallback], MACE-MP-0, ORB-v3, MatterSim [un-gated 2024-25 roster]) — producing
`<model>_pred.csv` in the SAME (material_id, e_form_pred) schema as the four cached
2023-24-generation UIPs (chgnet/m3gnet/mace/orb; see ~/mt_uip/*_pred.csv and
DATA_MANIFEST.md), so it drops straight into mt29_stage1_oam_arm.py (the analysis
hookup) without touching the frozen canonical mt29_stage1_chem_yield.py MODELS list or
its result JSON.

WHY frozen (no training): consistent with this repo's scope (AGENTS.md: "推理 + 经典 ML
基线, 不从头训练大模型" — inference + classical-ML baselines only, no training-from-
scratch). Every registry model is downloaded as a pretrained checkpoint and run as an
ASE calculator; no gradient step happens here.

GATED CHECKPOINT: eSEN-30M-OAM ships via a Hugging Face Hub checkpoint behind a
click-through license acceptance that cannot be completed headlessly. --model
esen-30m-oam without a resolvable --checkpoint fails fast with a message prefixed
REQUIRES_USER_CHECKPOINT (see RUNME_CONTAINER.md for the exact click-through steps).
SevenNet-MF-ompa (MDIL-SNU/SevenNet, MIT license) is the un-gated fallback used when no
checkpoint has been accepted.

MOCK BOUNDARY for tests (tests/test_uip_inference.py mocks exactly this): the pure
function `predict_formation_energies(calc, structures, ref_energies)` takes anything
duck-typed with a `.total_energy(structure) -> float` method plus a list of `Structure`
records, so no ase/fairchem/sevenn import is needed to exercise the numerical/schema
logic in --smoke or pytest. Only `build_calculator(...)` and `load_wbm_structures(...)`
touch the real ML libraries, and only when actually invoked (lazy imports).
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


# ----------------------------- structure record -----------------------------

@dataclass
class Structure:
    """A single crystal structure to run inference on. `positions`/`cell`/`pbc` are
    only required by the REAL ASE-backed calculators (build_calculator); the mock
    calculator used in --smoke/pytest only reads `symbols`."""
    material_id: str
    symbols: List[str]
    positions: Optional[List[List[float]]] = None
    cell: Optional[List[List[float]]] = None
    pbc: tuple = (True, True, True)


# ----------------------------- formation-energy math (pure, hand-checkable) -----------------------------

def formation_energy_per_atom(total_energy_ev: float, symbols: Iterable[str],
                               ref_energies: Dict[str, float]) -> float:
    """total_energy_ev: raw calculator total energy (eV) for the WHOLE cell. symbols:
    one element symbol per atom. ref_energies: per-atom elemental reference energies
    (eV/atom), on the SAME correction scheme as the WBM ground truth
    (e_form_per_atom_mp2020_corrected) so the OAM-era model's e_form_pred lands on the
    same energy scale as the four cached UIPs — see RUNME_CONTAINER.md for how to
    source this table for a real run. Pure arithmetic, hand-checkable: e.g. a 2-atom
    NaCl cell with total_energy=-4.0 and ref_energies={'Na':-1.0,'Cl':-1.0} gives
    (-4.0 - (-2.0)) / 2 == -1.0 eV/atom."""
    symbols = list(symbols)
    n = len(symbols)
    if n == 0:
        raise ValueError('empty structure')
    try:
        ref_total = sum(ref_energies[s] for s in symbols)
    except KeyError as e:
        raise KeyError(f'no reference energy for element {e.args[0]!r}') from e
    return (total_energy_ev - ref_total) / n


def predict_formation_energies(calc, structures: Iterable[Structure],
                                ref_energies: Dict[str, float]) -> pd.DataFrame:
    """The mockable boundary. `calc` is anything with `.total_energy(structure) ->
    float` (eV, whole-cell). Returns DataFrame[material_id, e_form_pred] — identical
    schema to the four cached *_pred.csv files."""
    rows = []
    for s in structures:
        e_tot = calc.total_energy(s)
        e_form = formation_energy_per_atom(e_tot, s.symbols, ref_energies)
        rows.append((s.material_id, e_form))
    return pd.DataFrame(rows, columns=['material_id', 'e_form_pred'])


# ----------------------------- model registry / calculators -----------------------------

MODEL_REGISTRY = {
    'esen-30m-oam': dict(
        gated=True,
        family='eSEN (fairchem/OMat24)', year=2025,
        training_data='OMat24 (~100M DFT relaxation frames, Meta FAIR) + MPtrj + Alexandria',
        hint=('eSEN-30M-OAM ships via the `fairchem` package Hugging Face Hub '
              'integration behind a one-time click-through license acceptance at '
              'huggingface.co (facebook/OMat24 family) — cannot be fetched headlessly. '
              'Accept the license in a browser, then `hf download` (or the fairchem '
              'checkpoint helper) the .pt file and pass --checkpoint /path/to/file.pt. '
              'See RUNME_CONTAINER.md "gated checkpoint" step.'),
    ),
    'sevennet-mf-ompa': dict(
        gated=False,
        family='SevenNet (MDIL-SNU)', year=2025,
        training_data='MPtrj + sAlex (multi-fidelity OMat24-aligned, "mf-ompa" checkpoint)',
        hint=('SevenNet-MF-ompa (MDIL-SNU/SevenNet, MIT) — public checkpoint zoo, no '
              'click-through; `pip install sevenn` and the checkpoint downloads '
              'automatically on first use (or pass --checkpoint to pin a local file).'),
    ),
    'mace-mp-0': dict(
        gated=False,
        family='MACE (ACEsuit, higher-order equivariant message passing)', year=2024,
        training_data='MPtrj (Materials Project relaxation trajectories, 1.6M structures, 89 elements)',
        hint=('MACE-MP-0 — `pip install mace-torch` (NOT the unrelated PyPI package '
              '"mace"); `from mace.calculators import mace_mp; mace_mp()` returns an '
              'ASE calculator directly (signature verified on mace-torch==0.3.16, '
              '2026-07-09: `mace_mp(model=None, device="", default_dtype="float32", '
              'dispersion=False, ..., return_raw_model=False, **kwargs)`; `model` '
              'accepts either a size string or a local checkpoint path/URL) and '
              'auto-downloads the default foundation-model checkpoint (medium-mpa-0 as '
              'of mace-torch>=0.3.10) from https://github.com/ACEsuit/mace-mp/releases '
              '(or mace-foundations on Hugging Face) on first use, cached under '
              '~/.cache/mace — NETWORK REQUIRED at load time unless --checkpoint pins a '
              'pre-fetched local .model file (passed as model=). Un-gated, no '
              'click-through. NOTE: mace-torch pins e3nn==0.4.4, which conflicts with '
              'mattersim<1.2.4\'s e3nn>=0.5.0 pin — see the mattersim entry\'s note; '
              'install in separate venvs/containers if both models are needed side by '
              'side. See RUNME_CONTAINER.md.'),
    ),
    'orb-v3': dict(
        gated=False,
        family='ORB (Orbital Materials, conservative/direct GNN)', year=2025,
        training_data='OMat24 + MPtrj + Alexandria (orb-v3 "conservative-inf-omat" checkpoint)',
        hint=('ORB-v3 — `pip install orb-models`; '
              '`from orb_models.forcefield import pretrained` then '
              '`pretrained.orb_v3_conservative_inf_omat(device=..., precision=...)` '
              '(signature verified on orb-models==0.5.5, 2026-07-09: `weights_path` '
              'defaults to the model\'s own S3 URL, not a local path) auto-downloads '
              'the checkpoint from an Orbital Materials S3 bucket '
              '(orbitalmaterials-public-models.s3.us-west-1.amazonaws.com) on first '
              'use, cached locally under the torch hub cache — NETWORK REQUIRED at '
              'load time unless --checkpoint pins a pre-fetched local weights file '
              '(passed as weights_path). Un-gated, no click-through. `ORBCalculator` '
              'verified importable from `orb_models.forcefield.calculator` (NOT '
              '`orb_models.forcefield.inference.calculator`, which does not exist on '
              'orb-models==0.5.5) — re-verify against whatever version pip resolves '
              'in the container — see RUNME_CONTAINER.md.'),
    ),
    'mattersim': dict(
        gated=False,
        family='MatterSim (Microsoft Research)', year=2024,
        training_data='~17M DFT structures spanning 0-5000K, 0-1000GPa (Microsoft internal + MP-derived)',
        hint=('MatterSim — `pip install mattersim`; UNLIKE the other 4 registry '
              'entries, `MatterSimCalculator.__init__` (verified on mattersim==1.2.5, '
              '2026-07-09) does NOT take a checkpoint path directly — build a '
              '`mattersim.forcefield.potential.Potential` via the classmethod '
              '`Potential.from_checkpoint(load_path=...)` first, then pass it as '
              '`MatterSimCalculator(potential=...)` (see `_MatterSimCalculator._lazy` '
              'below). Ships two checkpoints (mattersim-v1.0.0-1M.pth default, -5M.pth '
              'via load_path=); auto-downloads from '
              'raw.githubusercontent.com/microsoft/mattersim (NOT Hugging Face — '
              'confirmed by reading `potential.download_checkpoint`\'s source) to '
              '~/.local/mattersim/pretrained_models on first use — NETWORK REQUIRED '
              'at load time unless --checkpoint pins a pre-fetched local .pth file. '
              'Un-gated, no click-through, no license blocker found. NOTE: '
              'mattersim<1.2.4 pins e3nn>=0.5.0, which CONFLICTS with '
              'mace-torch\'s e3nn==0.4.4 pin in the SAME environment (mattersim>=1.2.4 '
              'resolves this but needs Python>=3.12) — install mace-torch and '
              'mattersim in separate venvs/containers if both are needed side by '
              'side. See RUNME_CONTAINER.md.'),
    ),
}


class RequiresUserCheckpoint(RuntimeError):
    """Raised when a gated model is requested without a locally-resolvable checkpoint."""


def build_calculator(model_key: str, checkpoint_path: Optional[str] = None):
    """Returns a lazy calculator object exposing `.total_energy(structure) -> float`.
    Real ML-library imports happen INSIDE the calculator's first `.total_energy()`
    call, not here — so this function itself never needs ase/fairchem/sevenn
    installed, and is exercised directly by tests/test_uip_inference.py."""
    if model_key not in MODEL_REGISTRY:
        raise ValueError(f'unknown model {model_key!r}; choices: {sorted(MODEL_REGISTRY)}')
    spec = MODEL_REGISTRY[model_key]
    if spec['gated'] and not (checkpoint_path and os.path.exists(checkpoint_path)):
        raise RequiresUserCheckpoint(
            f"REQUIRES_USER_CHECKPOINT: {model_key} needs a locally-resolvable checkpoint "
            f"(pass --checkpoint /path/to/file). {spec['hint']}"
        )
    if model_key == 'esen-30m-oam':
        return _EsenCalculator(checkpoint_path)
    if model_key == 'sevennet-mf-ompa':
        return _SevenNetCalculator(checkpoint_path)
    if model_key == 'mace-mp-0':
        return _MaceCalculator(checkpoint_path)
    if model_key == 'orb-v3':
        return _OrbCalculator(checkpoint_path)
    return _MatterSimCalculator(checkpoint_path)


class _EsenCalculator:
    """ASE-backed adapter for eSEN-30M-OAM via fairchem's OCPCalculator. Verify the
    exact class/import path against the installed fairchem-core version in the
    container (API has moved between fairchem releases) — see RUNME_CONTAINER.md."""

    def __init__(self, checkpoint_path: str):
        self.checkpoint_path = checkpoint_path
        self._ase_calc = None

    def _lazy(self):
        if self._ase_calc is None:
            try:
                from fairchem.core import OCPCalculator
            except ImportError as e:
                raise RuntimeError(
                    'fairchem-core is required for eSEN-30M-OAM inference; '
                    'pip install fairchem-core (see RUNME_CONTAINER.md).') from e
            self._ase_calc = OCPCalculator(checkpoint_path=self.checkpoint_path, cpu=False)
        return self._ase_calc

    def total_energy(self, structure: Structure) -> float:
        try:
            from ase import Atoms
        except ImportError as e:
            raise RuntimeError(
                'ase is required for real structure inference; pip install ase '
                '(see RUNME_CONTAINER.md).') from e
        atoms = Atoms(symbols=structure.symbols, positions=structure.positions,
                      cell=structure.cell, pbc=structure.pbc)
        atoms.calc = self._lazy()
        return float(atoms.get_potential_energy())


class _SevenNetCalculator:
    """ASE-backed adapter for SevenNet-MF-ompa via the `sevenn` package. Verify the
    exact class/import path against the installed sevenn version in the container —
    see RUNME_CONTAINER.md."""

    def __init__(self, checkpoint_path: Optional[str]):
        self.checkpoint_path = checkpoint_path
        self._ase_calc = None

    def _lazy(self):
        if self._ase_calc is None:
            try:
                from sevenn.calculator import SevenNetCalculator
            except ImportError as e:
                raise RuntimeError(
                    'sevenn is required for SevenNet-MF-ompa inference; pip install '
                    'sevenn (see RUNME_CONTAINER.md).') from e
            kwargs = {'model': self.checkpoint_path} if self.checkpoint_path else {'model': '7net-mf-ompa'}
            self._ase_calc = SevenNetCalculator(**kwargs)
        return self._ase_calc

    def total_energy(self, structure: Structure) -> float:
        try:
            from ase import Atoms
        except ImportError as e:
            raise RuntimeError(
                'ase is required for real structure inference; pip install ase '
                '(see RUNME_CONTAINER.md).') from e
        atoms = Atoms(symbols=structure.symbols, positions=structure.positions,
                      cell=structure.cell, pbc=structure.pbc)
        atoms.calc = self._lazy()
        return float(atoms.get_potential_energy())


class _MaceCalculator:
    """ASE-backed adapter for MACE-MP-0 via the `mace` package's `mace_mp()` foundation-
    model loader, which returns a ready-to-use ASE calculator (no separate wrapper
    class, unlike eSEN/SevenNet). Signature verified live against mace-torch==0.3.16
    (2026-07-09): `mace_mp(model=None, device='', default_dtype='float32', ...,
    **kwargs)` — `model=` doubles as the local-checkpoint-path override used here.
    Re-verify against whatever mace-torch version pip resolves in the container (the
    default model string has moved between releases — 0.3.10+ defaults to
    'medium-mpa-0') — see RUNME_CONTAINER.md."""

    def __init__(self, checkpoint_path: Optional[str] = None):
        self.checkpoint_path = checkpoint_path
        self._ase_calc = None

    def _lazy(self):
        if self._ase_calc is None:
            try:
                from mace.calculators import mace_mp
            except ImportError as e:
                raise RuntimeError(
                    'mace-torch is required for MACE-MP-0 inference; pip install '
                    'mace-torch (NOT the unrelated PyPI package "mace") — see '
                    'RUNME_CONTAINER.md.') from e
            kwargs = {'model': self.checkpoint_path} if self.checkpoint_path else {}
            self._ase_calc = mace_mp(**kwargs)
        return self._ase_calc

    def total_energy(self, structure: Structure) -> float:
        try:
            from ase import Atoms
        except ImportError as e:
            raise RuntimeError(
                'ase is required for real structure inference; pip install ase '
                '(see RUNME_CONTAINER.md).') from e
        atoms = Atoms(symbols=structure.symbols, positions=structure.positions,
                      cell=structure.cell, pbc=structure.pbc)
        atoms.calc = self._lazy()
        return float(atoms.get_potential_energy())


class _OrbCalculator:
    """ASE-backed adapter for ORB-v3 via the `orb_models` package's `pretrained` module
    + `ORBCalculator` wrapper. Signatures verified live against orb-models==0.5.5
    (2026-07-09): `pretrained.orb_v3_conservative_inf_omat(weights_path=<default S3
    URL>, device=None, precision='float32-high', ...)` returns the forcefield model
    directly (NOT a (model, atoms_adapter) tuple, despite some docs implying
    otherwise); `ORBCalculator` imports from `orb_models.forcefield.calculator` (the
    `orb_models.forcefield.inference.calculator` path some docs mention does not exist
    on this version). Re-verify against whatever orb-models version pip resolves in
    the container — see RUNME_CONTAINER.md."""

    def __init__(self, checkpoint_path: Optional[str] = None):
        self.checkpoint_path = checkpoint_path
        self._ase_calc = None

    def _lazy(self):
        if self._ase_calc is None:
            try:
                from orb_models.forcefield import pretrained
                from orb_models.forcefield.calculator import ORBCalculator
            except ImportError as e:
                raise RuntimeError(
                    'orb-models is required for ORB-v3 inference; pip install '
                    'orb-models (see RUNME_CONTAINER.md).') from e
            kwargs = {'weights_path': self.checkpoint_path} if self.checkpoint_path else {}
            orbff = pretrained.orb_v3_conservative_inf_omat(device='cpu', **kwargs)
            self._ase_calc = ORBCalculator(orbff, device='cpu')
        return self._ase_calc

    def total_energy(self, structure: Structure) -> float:
        try:
            from ase import Atoms
        except ImportError as e:
            raise RuntimeError(
                'ase is required for real structure inference; pip install ase '
                '(see RUNME_CONTAINER.md).') from e
        atoms = Atoms(symbols=structure.symbols, positions=structure.positions,
                      cell=structure.cell, pbc=structure.pbc)
        atoms.calc = self._lazy()
        return float(atoms.get_potential_energy())


class _MatterSimCalculator:
    """ASE-backed adapter for MatterSim. UNLIKE mace_mp()/SevenNetCalculator,
    `MatterSimCalculator.__init__` does NOT take a checkpoint path directly (verified
    against mattersim==1.2.5's real signature: `MatterSimCalculator(potential=None,
    device='cuda', ...)`) — the checkpoint is loaded separately via the classmethod
    `Potential.from_checkpoint(load_path=..., device=...)` and the resulting
    `Potential` is passed in as `potential=`. See RUNME_CONTAINER.md."""

    def __init__(self, checkpoint_path: Optional[str] = None):
        self.checkpoint_path = checkpoint_path
        self._ase_calc = None

    def _lazy(self):
        if self._ase_calc is None:
            try:
                from mattersim.forcefield import MatterSimCalculator
                from mattersim.forcefield.potential import Potential
            except ImportError as e:
                raise RuntimeError(
                    'mattersim is required for MatterSim inference; pip install '
                    'mattersim (see RUNME_CONTAINER.md).') from e
            kwargs = {'load_path': self.checkpoint_path} if self.checkpoint_path else {}
            potential = Potential.from_checkpoint(**kwargs)
            self._ase_calc = MatterSimCalculator(potential=potential)
        return self._ase_calc

    def total_energy(self, structure: Structure) -> float:
        try:
            from ase import Atoms
        except ImportError as e:
            raise RuntimeError(
                'ase is required for real structure inference; pip install ase '
                '(see RUNME_CONTAINER.md).') from e
        atoms = Atoms(symbols=structure.symbols, positions=structure.positions,
                      cell=structure.cell, pbc=structure.pbc)
        atoms.calc = self._lazy()
        return float(atoms.get_potential_energy())


# ----------------------------- WBM structure loading (real path only) -----------------------------

def load_wbm_structures(wbm_root: str, limit: Optional[int] = None) -> Iterable[Structure]:
    """Guarded ase import. Reads the WBM initial-structure extxyz. NOTE
    (DATA_MANIFEST.md): the in-repo-adjacent mirror
    `~/.cache/matbench-discovery/wbm/2024-08-04-wbm-initial-atoms.extxyz.zip` is a
    0-BYTE aborted download — fetch_data.sh in the container must re-download it for
    real (see RUNME_CONTAINER.md)."""
    try:
        from ase.io import iread
    except ImportError as e:
        raise RuntimeError(
            'ase is required for real WBM structure loading; pip install ase '
            '(see RUNME_CONTAINER.md).') from e
    candidates = sorted(glob.glob(os.path.join(wbm_root, '*wbm-initial-atoms*')))
    if not candidates:
        raise FileNotFoundError(
            f'no WBM initial-structure file found under {wbm_root!r}; run fetch_data.sh first.')
    path = candidates[0]
    for i, atoms in enumerate(iread(path)):
        if limit is not None and i >= limit:
            break
        mid = atoms.info.get('material_id') or atoms.info.get('wbm_id') or f'wbm-{i}'
        yield Structure(material_id=mid,
                        symbols=list(atoms.get_chemical_symbols()),
                        positions=atoms.get_positions().tolist(),
                        cell=atoms.get_cell().tolist(),
                        pbc=tuple(bool(p) for p in atoms.pbc))


# ----------------------------- smoke path (no ase/network/checkpoint) -----------------------------

class _MockCalc:
    """Deterministic stand-in for a real ASE/fairchem/sevenn calculator: total energy
    = -1.0 eV/atom * n_atoms (toy 'binding energy'), so e_form_pred is hand-checkable
    against ref_energies=0 for every element."""

    def total_energy(self, structure: Structure) -> float:
        return -1.0 * len(structure.symbols)


def _run_smoke() -> int:
    structures = [
        Structure('smoke-1', ['Na', 'Cl']),
        Structure('smoke-2', ['Fe', 'Fe', 'Al']),
        Structure('smoke-3', ['O', 'O']),
    ]
    ref_energies = {'Na': 0.0, 'Cl': 0.0, 'Fe': 0.0, 'Al': 0.0, 'O': 0.0}
    df = predict_formation_energies(_MockCalc(), structures, ref_energies)
    assert list(df.columns) == ['material_id', 'e_form_pred'], df.columns
    assert len(df) == 3, len(df)
    assert np.allclose(df['e_form_pred'].values, -1.0), df

    # also prove the CSV-write path works end-to-end, entirely outside the repo tree.
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, 'smoke_pred.csv')
        df.to_csv(out, index=False)
        reread = pd.read_csv(out)
        assert list(reread.columns) == ['material_id', 'e_form_pred']
        assert len(reread) == 3

    # also prove build_calculator's gate: the four un-gated models build without a
    # checkpoint; esen (gated) refuses with REQUIRES_USER_CHECKPOINT.
    build_calculator('sevennet-mf-ompa', None)
    build_calculator('mace-mp-0', None)
    build_calculator('orb-v3', None)
    build_calculator('mattersim', None)
    try:
        build_calculator('esen-30m-oam', None)
    except RequiresUserCheckpoint as e:
        assert 'REQUIRES_USER_CHECKPOINT' in str(e)
    else:
        raise AssertionError('expected RequiresUserCheckpoint for esen-30m-oam without a checkpoint')

    print('SMOKE OK: predict_formation_energies + CSV round-trip + checkpoint gate all pass '
          f'(CPU-only, no ase/network/checkpoint). {len(df)} rows.')
    return 0


# ----------------------------- CLI -----------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--model', choices=sorted(MODEL_REGISTRY), default='sevennet-mf-ompa')
    ap.add_argument('--checkpoint', default=None,
                    help='local checkpoint path (required for gated models, e.g. esen-30m-oam)')
    ap.add_argument('--wbm-root', default=os.path.expanduser(
        os.environ.get('MT_DATA_ROOT', '~/mt_stage0/data')))
    ap.add_argument('--ref-energies-json', default=None,
                    help='per-element reference-energy table (eV/atom); required for a real '
                         'run — see RUNME_CONTAINER.md "reference energies".')
    ap.add_argument('--out', default=None,
                    help='output CSV path; default $MT_UIP_ROOT/<model>_pred.csv')
    ap.add_argument('--limit', type=int, default=None, help='cap number of structures (debug)')
    ap.add_argument('--smoke', action='store_true',
                    help='CPU-only, no network/checkpoint/ase end-to-end check on 3 synthetic '
                         'toy structures + a mock calculator')
    args = ap.parse_args(argv)

    if args.smoke:
        return _run_smoke()

    if not args.ref_energies_json:
        print('ERROR: --ref-energies-json is required for a real run (see RUNME_CONTAINER.md '
              '"reference energies").', file=sys.stderr)
        return 2
    with open(args.ref_energies_json) as f:
        ref_energies = json.load(f)

    calc = build_calculator(args.model, args.checkpoint)  # raises RequiresUserCheckpoint clearly
    structures = list(load_wbm_structures(args.wbm_root, limit=args.limit))
    df = predict_formation_energies(calc, structures, ref_energies)

    uip_root = os.path.expanduser(os.environ.get('MT_UIP_ROOT', '~/mt_uip'))
    out = args.out or os.path.join(uip_root, f"{args.model.replace('-', '_')}_pred.csv")
    if os.path.exists(out):
        print(f'REFUSING to overwrite existing {out}', file=sys.stderr)
        return 1
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    df.to_csv(out, index=False)
    print(f'wrote {len(df)} rows -> {out}')

    manifest = {
        'cmd': ' '.join([sys.executable] + sys.argv),
        'model': args.model,
        'script_sha256': sha256(os.path.abspath(__file__)),
        'checkpoint_sha256': sha256(args.checkpoint) if args.checkpoint and os.path.exists(args.checkpoint) else None,
        'ref_energies_sha256': sha256(args.ref_energies_json),
        'n_structures': len(df),
        'output_sha256': sha256(out),
        'versions': {'python': platform.python_version(), 'numpy': np.__version__,
                     'pandas': pd.__version__},
        'platform': platform.platform(),
    }
    try:
        git_sha = subprocess.check_output(['git', '-C', REPO, 'rev-parse', 'HEAD'],
                                          text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        git_sha = None
    manifest['git_head'] = git_sha
    manifest_path = out.rsplit('.', 1)[0] + '_manifest.json'
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f'wrote {manifest_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
