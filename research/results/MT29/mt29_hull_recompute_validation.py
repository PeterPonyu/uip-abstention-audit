#!/usr/bin/env python
"""MT29 — Arm 2b (NEXT-EXPERIMENTS.md item 2): convex-hull recompute on a validation
subset, to bound the fixed-hull approximation used everywhere else in MT29
(see the fixed-hull limitation in README.md).

For a stratified random sample of WBM test structures (default 5,000, stratified
across the 6 anion families used throughout MT29 — mt29_stage1_chem_yield.anion_family),
rebuilds each structure's chemical-system hull from MP reference entries and recomputes
e_above_hull_pred from each cached UIP's predicted formation energy via
mt29_hull_math.hull_energy_at / e_above_hull, instead of the fixed-hull shortcut.
Reports the distribution of (fixed_hull_pred - recomputed_hull_pred) per stratum per
model, and whether any structure's STABLE/UNSTABLE call (sign of hull_pred) flips
between the two methods.

DATA (network + ~1-2 GB, NOT fetched here — see RUNME_CONTAINER.md / fetch_data.sh): MP
reference entries via `matbench_discovery.data.DataFiles.mp_computed_structure_entries`
(guarded import; requires `pip install matbench-discovery pymatgen`). pymatgen is used
ONLY by `load_mp_reference_entries` to flatten each `ComputedStructureEntry` into plain
(elements, symbols, energy_per_atom) — the hull GEOMETRY itself (mt29_hull_math) is pure
numpy/scipy with no pymatgen dependency, so the math and this script's sampling/
recompute logic are unit-tested (tests/test_hull_math.py,
tests/test_hull_recompute_validation.py) WITHOUT pymatgen or matbench-discovery
installed.

Writes a NEW result JSON (mt29_hull_recompute_validation_result.json + manifest); never
touches the frozen mt29_stage0/mt29_stage1 result JSONs (this is a bounding/validation
study of the existing fixed-hull approximation, not a replacement for it).
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import platform
import subprocess
import sys
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, REPO_ROOT)

from mt29_hull_math import composition_fractions, formula_to_symbols, hull_energy_at  # noqa: E402
from mt29_stage1_chem_yield import anion_family, DATA as DEFAULT_WBM_SUMMARY  # noqa: E402
from mt29_stage1_chem_yield import UIP as DEFAULT_UIP_ROOT, sha256, SEED  # noqa: E402
from mt29_stage1_matched_yield_fix import FAM_ORDER  # noqa: E402

try:
    from relmetrics.provenance import stamp_result
except ImportError:  # pragma: no cover
    stamp_result = None

BASE_MODELS = ['chgnet', 'm3gnet', 'mace', 'orb']
OUT_DIR = HERE
OUT_JSON = os.path.join(OUT_DIR, 'mt29_hull_recompute_validation_result.json')
MANIFEST = os.path.join(OUT_DIR, 'mt29_hull_recompute_validation_manifest.json')
N_TOTAL_DEFAULT = 5000


# ----------------------------- stratified sampling (data-independent, tested) -----------------------------

def stratified_sample(base_df: pd.DataFrame, fams: Sequence[str] = FAM_ORDER,
                      n_total: int = N_TOTAL_DEFAULT, seed: int = SEED) -> pd.DataFrame:
    """Stratified random sample across `fams`, up to `n_total // len(fams)` rows per
    family (fewer if a family has fewer rows than that). Deterministic given `seed`."""
    rng = np.random.default_rng(seed)
    per_fam = max(1, n_total // len(fams))
    parts = []
    for f in fams:
        sub = base_df[base_df['family'] == f]
        k = min(per_fam, len(sub))
        if k == 0:
            continue
        idx = rng.choice(sub.index.values, size=k, replace=False)
        parts.append(base_df.loc[idx])
    if not parts:
        return base_df.iloc[0:0]
    return pd.concat(parts).reset_index(drop=True)


# ----------------------------- per-structure recompute (data-independent, tested) -----------------------------

def evaluate_structure(elements: Sequence[str], ref_symbols_list: List[List[str]],
                       ref_energies: Sequence[float], symbols: Sequence[str],
                       e_form_true: float, e_form_pred_by_model: Dict[str, float]) -> Dict:
    """Single query structure. `elements`: sorted tuple of element symbols spanning its
    chemical system. `ref_symbols_list`/`ref_energies`: MP reference entries for that
    system (elements subset-of `elements` convention; energies are per-atom formation
    energies on the SAME elemental-reference-zero convention as `e_form_true`).
    `symbols`: the query structure's own atom multiset. Returns the recomputed hull
    energy at the query composition plus the recomputed e_above_hull for the true
    formation energy and each model's predicted one."""
    ref_comps = np.stack([composition_fractions(s, elements) for s in ref_symbols_list])
    qc = composition_fractions(symbols, elements)
    he = hull_energy_at(qc, ref_comps, np.asarray(ref_energies, dtype=float))
    return {
        'hull_energy_at_query': he,
        'e_above_hull_true_recomputed': float(e_form_true) - he,
        'e_above_hull_pred_recomputed': {m: float(e) - he for m, e in e_form_pred_by_model.items()},
    }


def summarize_deltas(rows: List[Dict], models: List[str]) -> Dict:
    """rows: list of dicts each with 'family', 'hull_pred_fixed' (dict per model) and
    'hull_pred_recomputed' (dict per model). Returns per-stratum per-model delta
    distribution (fixed - recomputed) and stable/unstable call-flip counts."""
    out = {}
    fams = sorted({r['family'] for r in rows})
    for f in fams:
        frows = [r for r in rows if r['family'] == f]
        out[f] = {'n': len(frows), 'per_model': {}}
        for m in models:
            deltas = np.array([r['hull_pred_fixed'][m] - r['hull_pred_recomputed'][m] for r in frows])
            fixed_stable = np.array([r['hull_pred_fixed'][m] < 0 for r in frows])
            recomp_stable = np.array([r['hull_pred_recomputed'][m] < 0 for r in frows])
            n_flips = int(np.sum(fixed_stable != recomp_stable))
            out[f]['per_model'][m] = {
                'delta_mean': round(float(deltas.mean()), 6) if len(deltas) else None,
                'delta_median': round(float(np.median(deltas)), 6) if len(deltas) else None,
                'delta_std': round(float(deltas.std()), 6) if len(deltas) else None,
                'n_flips': n_flips,
                'flip_rate': round(n_flips / len(frows), 5) if frows else None,
            }
    return out


# ----------------------------- real-data path (guarded imports; not exercised by tests) -----------------------------

def load_mp_reference_entries(mp_entries_path: str) -> pd.DataFrame:
    """Guarded import: needs pymatgen + a local MP entries cache produced by
    fetch_data.sh (`matbench_discovery.data.DataFiles.mp_computed_structure_entries`).
    Flattens each `ComputedStructureEntry` -> plain (material_id, elements frozenset,
    symbols, e_per_atom) so downstream code never touches pymatgen objects — this
    function is the ONLY part of the real path pymatgen-gated; mt29_hull_math and
    evaluate_structure/summarize_deltas above are pymatgen-free and unit-tested."""
    try:
        from pymatgen.entries.computed_entries import ComputedEntry  # noqa: F401
    except ImportError as e:
        raise RuntimeError(
            'pymatgen is required to read MP reference entries for the real hull '
            'recompute; pip install pymatgen matbench-discovery (see RUNME_CONTAINER.md).'
        ) from e
    with open(mp_entries_path, 'rb') as f:
        entries = pickle.load(f)
    rows = []
    for e in entries:
        comp = e.composition.element_composition.as_dict()
        symbols = []
        for el, amt in comp.items():
            symbols.extend([el] * int(round(amt)))
        rows.append({
            'material_id': getattr(e, 'entry_id', None),
            'elements': frozenset(comp.keys()),
            'symbols': symbols,
            'e_per_atom': float(e.energy_per_atom),
        })
    return pd.DataFrame(rows)


def run_real(wbm_summary_path: str, uip_root: str, mp_entries_path: str,
            models: List[str], n_total: int, seed: int) -> Dict:
    wbm = pd.read_csv(wbm_summary_path, usecols=['material_id', 'formula',
                                                  'e_form_per_atom_mp2020_corrected',
                                                  'e_above_hull_mp2020_corrected_ppd_mp'])
    base = wbm.dropna().copy()
    for m in models:
        p = pd.read_csv(os.path.join(uip_root, f'{m}_pred.csv'))[['material_id', 'e_form_pred']]
        base = base.merge(p.rename(columns={'e_form_pred': f'eform_{m}'}), on='material_id', how='inner')
    base = base.dropna().reset_index(drop=True)
    base['family'] = base['formula'].apply(anion_family)

    sample = stratified_sample(base, n_total=n_total, seed=seed)
    mp_entries = load_mp_reference_entries(mp_entries_path)

    rows = []
    for _, r in sample.iterrows():
        symbols = formula_to_symbols(r['formula'])
        elements = tuple(sorted(set(symbols)))
        ref_slice = mp_entries[mp_entries['elements'].apply(lambda es: es.issubset(set(elements)))]
        if len(ref_slice) < 2:
            continue  # not enough reference entries to build a hull for this system
        e_form_true = r['e_form_per_atom_mp2020_corrected']
        hull_true_fixed = r['e_above_hull_mp2020_corrected_ppd_mp']
        e_form_pred_by_model = {m: r[f'eform_{m}'] for m in models}
        hull_pred_fixed = {m: hull_true_fixed + (e_form_pred_by_model[m] - e_form_true) for m in models}
        try:
            ev = evaluate_structure(elements, ref_slice['symbols'].tolist(),
                                    ref_slice['e_per_atom'].tolist(), symbols,
                                    e_form_true, e_form_pred_by_model)
        except (ValueError, RuntimeError):
            continue
        rows.append({
            'material_id': r['material_id'], 'family': r['family'],
            'hull_pred_fixed': hull_pred_fixed,
            'hull_pred_recomputed': ev['e_above_hull_pred_recomputed'],
        })

    per_stratum = summarize_deltas(rows, models)
    total_flips = sum(v['per_model'][m]['n_flips'] for v in per_stratum.values() for m in models)
    return {
        'meta': {'n_requested': n_total, 'n_evaluated': len(rows), 'models': models,
                'seed': seed, 'strata': FAM_ORDER},
        'per_stratum': per_stratum,
        'summary': {'total_flips': total_flips, 'any_flips': bool(total_flips > 0)},
    }


# ----------------------------- smoke path (toy in-script data, no network/pymatgen) -----------------------------

def _toy_reference_entries():
    """Small hand-built 'MP reference entries' for a binary A-B system, matching the
    hand-checkable toy in tests/test_hull_math.py: pure A, pure B (both 0.0), and a
    stable AB compound at -1.0 eV/atom."""
    return dict(
        elements=('A', 'B'),
        ref_symbols_list=[['A'], ['B'], ['A', 'B']],
        ref_energies=[0.0, 0.0, -1.0],
    )


def _run_smoke() -> int:
    toy = _toy_reference_entries()
    # 4 synthetic "WBM-like" query rows at the AB composition, 2 per toy family, each
    # with a true formation energy and 2 models' predictions (one accurate, one biased).
    rows = []
    rng = np.random.default_rng(0)
    for fam, n in [('oxide', 6), ('halide', 6)]:
        for i in range(n):
            e_true = -1.0 + rng.normal(0, 0.02)
            e_pred_good = e_true + rng.normal(0, 0.01)
            e_pred_biased = e_true + 0.15  # a model that's systematically optimistic
            hull_true_fixed = 0.0  # on-hull ground truth by construction
            e_form_pred_by_model = {'good': e_pred_good, 'biased': e_pred_biased}
            hull_pred_fixed = {m: hull_true_fixed + (e_form_pred_by_model[m] - e_true)
                               for m in e_form_pred_by_model}
            ev = evaluate_structure(toy['elements'], toy['ref_symbols_list'], toy['ref_energies'],
                                    ['A', 'B'], e_true, e_form_pred_by_model)
            rows.append({'material_id': f'{fam}-{i}', 'family': fam,
                        'hull_pred_fixed': hull_pred_fixed,
                        'hull_pred_recomputed': ev['e_above_hull_pred_recomputed']})

    per_stratum = summarize_deltas(rows, ['good', 'biased'])
    assert set(per_stratum.keys()) == {'oxide', 'halide'}
    for f in per_stratum:
        assert 'good' in per_stratum[f]['per_model'] and 'biased' in per_stratum[f]['per_model']

    # sample-fraction sanity: stratified_sample on a synthetic base_df pulls from both
    # families and respects the per-family cap.
    base_df = pd.DataFrame({
        'family': ['oxide'] * 50 + ['halide'] * 30,
        'val': list(range(80)),
    })
    sample = stratified_sample(base_df, fams=['oxide', 'halide'], n_total=20, seed=0)
    assert set(sample['family']) == {'oxide', 'halide'}
    assert len(sample) <= 20

    payload = {'per_stratum': per_stratum, 'sample_n': len(sample)}
    json.dumps(payload, default=str)  # prove JSON-serializable, no disk write in smoke
    print('SMOKE OK: toy binary-system recompute + stratified_sample + delta summary '
          f'all ran (CPU-only, no network/pymatgen). {len(rows)} toy query rows evaluated.')
    return 0


# ----------------------------- CLI -----------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--wbm-summary', default=DEFAULT_WBM_SUMMARY)
    ap.add_argument('--uip-root', default=DEFAULT_UIP_ROOT)
    ap.add_argument('--mp-entries', default=os.path.expanduser(
        os.environ.get('MT_MP_ENTRIES', '~/.cache/matbench-discovery/mp/mp_computed_structure_entries.pkl.gz')))
    ap.add_argument('--models', default=','.join(BASE_MODELS))
    ap.add_argument('--n-total', type=int, default=N_TOTAL_DEFAULT)
    ap.add_argument('--seed', type=int, default=SEED)
    ap.add_argument('--smoke', action='store_true',
                    help='CPU-only, no network/pymatgen; toy binary-system fixture')
    args = ap.parse_args(argv)

    if args.smoke:
        return _run_smoke()

    models = args.models.split(',')
    results = run_real(args.wbm_summary, args.uip_root, args.mp_entries, models,
                       args.n_total, args.seed)
    if stamp_result is not None:
        stamp_result(results, __file__, seeds=[args.seed])

    if os.path.exists(OUT_JSON):
        print(f'REFUSING to overwrite existing {OUT_JSON}', file=sys.stderr)
        return 1
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_JSON, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f'Wrote {OUT_JSON}')

    try:
        git_sha = subprocess.check_output(
            ['git', '-C', REPO_ROOT, 'rev-parse', 'HEAD'], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        git_sha = None
    manifest = {
        'cmd': ' '.join([sys.executable] + sys.argv),
        'script_sha256': sha256(os.path.abspath(__file__)),
        'git_head': git_sha, 'seed': args.seed, 'n_total': args.n_total, 'models': models,
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
