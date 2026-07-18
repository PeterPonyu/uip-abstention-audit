#!/usr/bin/env python3
"""Convert the MP computed-structure-entries JSON.gz into the plain-pickle reference
table mt29_hull_recompute_validation.py expects — carrying MP2020-corrected FORMATION
energy per atom, on the SAME elemental-reference-zero convention as the WBM
`e_form_per_atom_mp2020_corrected` ground truth.

WHY THIS WAS REWRITTEN (POST-ANALYSIS-2026-07-10.md Sec.5): the frozen hull loader
`load_mp_reference_entries` reads each reference entry's ``energy_per_atom``. The earlier
version of this converter pickled the RAW pymatgen entries, whose ``energy_per_atom`` is
the TOTAL DFT energy per atom — while the hull query is compared against `e_form_true`, a
FORMATION energy. Mixing a total-energy reference surface with a formation-energy query
produced the spurious −3 to −6 eV/atom hull deltas and 11–41% "flips" the post-analysis
diagnosed. Neither the frozen hull script nor mt29_hull_math is touched; the fix lives
entirely here, by making the pickled entries carry formation energy AS their
``energy_per_atom``.

CONVERSION (per entry):
  1. hydrate the pymatgen ComputedStructureEntry (raw, uncorrected: correction==0).
  2. apply MaterialsProject2020Compatibility (the exact anion/GGA+U correction layer that
     built `e_form_per_atom_mp2020_corrected`) — uses each entry's structure + oxidation
     states, so peroxide/superoxide/ozonide discrimination is correct.
  3. e_form_per_atom = matbench_discovery.energy.get_e_form_per_atom(corrected_entry)
     against mp_elemental_ref_energies (== ref_energies.json; O=-4.9467) — the SAME helper
     and references matbench-discovery used to build the truth column.
  4. emit a plain ComputedEntry(composition, energy=e_form_per_atom*n_atoms, correction=0,
     entry_id) so the frozen loader's ``energy_per_atom`` == e_form_per_atom.

VALIDATION GATE (built in, --spot-check on by default): a handful of well-known MP oxides
(Fe2O3, Al2O3, TiO2, MgO, NaCl) must land within tolerance of their published MP2020
formation energies before the full table is written; otherwise the converter refuses.

Idempotent: skips when the output already exists (``--force`` re-writes). CPU-only; needs
pandas + pymatgen + matbench-discovery (the same env the hull step runs in). Emits the
pickle to ``--out`` (default the frozen loader's expected cache path); writes NOTHING into
research/results/MT29/.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import pickle
import sys
from pathlib import Path

# Published MP2020 formation energies (eV/atom) for the spot-check gate. Values are the
# Materials Project e_form_per_atom for the canonical ground-state polymorph; tolerance is
# loose (0.15 eV/atom) because we match against whichever polymorph is lowest in the entry
# set, not a specific mp-id.
KNOWN_EFORM = {
    'Fe2O3': -1.68, 'Al2O3': -3.44, 'TiO2': -3.50, 'MgO': -3.06, 'NaCl': -2.02,
}
SPOT_TOL = 0.15


def _hydrate_entries(src: str):
    from pymatgen.entries.computed_entries import ComputedEntry, ComputedStructureEntry

    with gzip.open(src, 'rt', encoding='utf-8') as fh:
        raw = json.load(fh)

    entry_col = None
    for col, values in raw.items():
        first = next(iter(values.values())) if isinstance(values, dict) and values else None
        if isinstance(first, dict) and '@class' in first:
            entry_col = col
            break
    if entry_col is None:
        raise RuntimeError('no column of pymatgen entry dicts found in src')

    ids = raw.get('material_id')
    entries, n_bad = [], 0
    for k, d in raw[entry_col].items():
        try:
            cls = ComputedStructureEntry if d.get('@class') == 'ComputedStructureEntry' else ComputedEntry
            e = cls.from_dict(d)
            if getattr(e, 'entry_id', None) is None and ids and k in ids:
                e.entry_id = ids[k]
            entries.append(e)
        except Exception as exc:  # noqa: BLE001 - count-and-continue, gated below
            n_bad += 1
            if n_bad <= 3:
                print(f'warning: entry {k} failed to hydrate: {exc}', file=sys.stderr)
    return entries, n_bad


def _spot_check(form_by_formula_min: dict) -> bool:
    ok = True
    print('--- spot-check: recomputed MP2020 formation energy vs published (eV/atom) ---')
    for formula, published in KNOWN_EFORM.items():
        got = form_by_formula_min.get(formula)
        if got is None:
            print(f'  {formula:8} MISSING from reference set -- cannot verify', file=sys.stderr)
            ok = False
            continue
        dev = abs(got - published)
        flag = 'PASS' if dev <= SPOT_TOL else 'FAIL'
        print(f'  {formula:8} recomputed={got:+.3f}  published={published:+.3f}  '
              f'|dev|={dev:.3f}  {flag}')
        if dev > SPOT_TOL:
            ok = False
    return ok


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--src', required=True,
                    help='2023-02-07-mp-computed-structure-entries.json.gz')
    ap.add_argument('-o', '--out', required=True, help='expected pkl path (plain pickle)')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--no-spot-check', action='store_true',
                    help='skip the known-materials formation-energy gate (NOT recommended)')
    args = ap.parse_args(argv)

    out = Path(args.out)
    if out.exists() and not args.force:
        print(f'convert_mp_entries: {out} already exists (idempotent skip)')
        return 0

    from pymatgen.entries.computed_entries import ComputedEntry
    from pymatgen.entries.compatibility import MaterialsProject2020Compatibility
    from matbench_discovery.energy import get_e_form_per_atom, mp_elemental_ref_energies

    print(f'convert_mp_entries: hydrating entries from {args.src} ...')
    entries, n_bad = _hydrate_entries(args.src)
    n_hydrated = len(entries)
    print(f'  hydrated {n_hydrated} entries ({n_bad} failed)')
    if not entries or n_bad > n_hydrated // 100:
        print(f'error: too many hydration failures ({n_bad}) -- refusing', file=sys.stderr)
        return 1

    print('convert_mp_entries: applying MaterialsProject2020Compatibility ...')
    compat = MaterialsProject2020Compatibility()
    corrected = compat.process_entries(entries, clean=True, verbose=False)
    n_corrected = len(corrected)
    print(f'  {n_corrected} entries processed ({n_hydrated - n_corrected} dropped as '
          'incompatible with MP2020)')

    print('convert_mp_entries: computing MP2020-corrected formation energy per atom ...')
    out_entries = []
    form_by_formula_min: dict = {}
    n_form_bad = 0
    for e in corrected:
        try:
            eform = float(get_e_form_per_atom(e, elemental_ref_energies=mp_elemental_ref_energies))
        except Exception:  # noqa: BLE001 - count-and-continue
            n_form_bad += 1
            continue
        comp = e.composition
        n_atoms = comp.num_atoms
        ce = ComputedEntry(composition=comp, energy=eform * n_atoms, correction=0.0,
                           entry_id=getattr(e, 'entry_id', None))
        out_entries.append(ce)
        # track lowest (most stable) formation energy per reduced formula for the spot-check
        rf = comp.reduced_formula
        if rf in KNOWN_EFORM:
            prev = form_by_formula_min.get(rf)
            if prev is None or eform < prev:
                form_by_formula_min[rf] = eform

    print(f'  produced {len(out_entries)} formation-energy reference entries '
          f'({n_form_bad} skipped in e_form step)')

    if not args.no_spot_check:
        if not _spot_check(form_by_formula_min):
            print('error: known-materials formation-energy spot-check FAILED -- refusing to '
                  'write (fix the correction/reference convention first)', file=sys.stderr)
            return 1

    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + '.tmp')
    with open(tmp, 'wb') as fh:
        pickle.dump(out_entries, fh, protocol=pickle.HIGHEST_PROTOCOL)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, out)
    print(f'convert_mp_entries: {len(out_entries)} formation-energy entries -> {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
