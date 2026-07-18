#!/usr/bin/env python3
"""ARM 2 (corrected OAM / modern-roster arm) — post-hoc MP2020 correction of the four
new-generation UIP prediction CSVs.

DIAGNOSIS (POST-ANALYSIS-2026-07-10.md Sec.4): mt29_uip_inference.py converted UIP total
energies to formation energies against the *uncorrected* elemental references
(ref_energies.json) but omitted the MP2020 composition/anion correction layer that the
ground-truth column `e_form_per_atom_mp2020_corrected` (and the four legacy prediction
CSVs) carry. Result: an anion-count-proportional positive bias (+0.59 eV/atom oxides,
+0.44 halides, ...) identical across the four new architectures — a harness artifact, not
a model property.

FIX (this script): add matbench-discovery's OWN precomputed per-material MP2020 correction
term to each new model's raw prediction. The WBM summary
(2023-12-13-wbm-summary.csv.gz) already carries `e_correction_per_atom_mp2020` for every
material — computed by matbench-discovery from the actual WBM relaxed structures, so
peroxide/superoxide/ozonide discrimination is already baked in and NO structure download
is needed. The exact identity holds on all 256,963 rows (verified below, gate 0):

    e_form_per_atom_mp2020_corrected == e_form_per_atom_uncorrected + e_correction_per_atom_mp2020

so the corrected prediction is simply

    e_form_pred_mp2020 = e_form_pred_raw + e_correction_per_atom_mp2020

The correction is a property of the material (its DFT-relaxed structure/composition), NOT
of the model, so adding it to any model's raw prediction is valid; it is the same term the
truth column and the legacy CSVs already include.

METHOD DISCLOSURE: the correction is applied ONLY to the four NEW models (which were
produced raw by mt29_uip_inference.py). The four legacy CSVs (chgnet/m3gnet/mace/orb) are
ALREADY on the MP2020-corrected convention (their before-correction bias vs truth is ~0),
so they are copied through UNCHANGED — adding the correction again would OVER-correct them
(verified: gate 2 before/after table shows legacy 'after' going negative).

Emits, under results_expansion_2026-07-10/corrected_arms/:
  - <model>_pred_mp2020.csv         (disclosed deliverable: corrected copy, 4 new models)
  - roster_mp2020/<model>_pred.csv  (arm input: 4 legacy unchanged + 4 new corrected)
  - oam_correction_validation.json  (gate 0 identity + before/after per-stratum bias table)

Never edits any frozen script or canonical MT29 result JSON. CPU-only, no network.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
MT29 = '/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/research/results/MT29'
sys.path.insert(0, MT29)
from mt29_stage1_chem_yield import anion_family  # noqa: E402  (frozen classifier, imported not edited)

FAM_ORDER = ['oxide', 'halide', 'chalcogenide', 'pnictide', 'intermetallic', 'other']

# The four legacy (already-MP2020-corrected) prediction CSVs and the four new-generation
# (raw / uncorrected) ones. Paths are resolved from flags/env; no hardcoded absolute
# model paths beyond the documented on-disk defaults.
LEGACY = ['chgnet', 'm3gnet', 'mace', 'orb']
NEW = ['mace_mp_0', 'mattersim', 'sevennet_mf_ompa', 'orb_v3']


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def load_pred(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)[['material_id', 'e_form_pred']]
    return df


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--wbm-summary',
                    default=os.environ.get('MT_WBM_SUMMARY',
                                           os.path.expanduser('~/mt_stage0/data/2023-12-13-wbm-summary.csv.gz')))
    ap.add_argument('--legacy-root', default=os.environ.get('MT_LEGACY_ROOT',
                                                            os.path.expanduser('~/mt_uip')),
                    help='dir holding the 4 legacy <model>_pred.csv (already MP2020-corrected)')
    ap.add_argument('--new-4c-root',
                    default=os.path.join(HERE, '..', 'pulled', 'extracted_4c', 'root', 'mt_uip'),
                    help='dir holding mace_mp_0/mattersim/sevennet_mf_ompa _pred.csv (raw)')
    ap.add_argument('--orb-v3-csv',
                    default=os.path.join(HERE, '..', 'pulled_4d', 'root', 'mt_uip', 'orb_v3_pred.csv'),
                    help='orb_v3_pred.csv (raw, produced in session 4d)')
    ap.add_argument('--out-dir', default=HERE)
    args = ap.parse_args(argv)

    roster_dir = os.path.join(args.out_dir, 'roster_mp2020')
    os.makedirs(roster_dir, exist_ok=True)

    wcols = ['material_id', 'formula', 'e_form_per_atom_uncorrected',
             'e_correction_per_atom_mp2020', 'e_form_per_atom_mp2020_corrected']
    w = pd.read_csv(args.wbm_summary, usecols=wcols)

    # ---- GATE 0: exact correction identity on all rows -------------------------------
    wv = w.dropna(subset=['e_form_per_atom_uncorrected', 'e_correction_per_atom_mp2020',
                          'e_form_per_atom_mp2020_corrected'])
    resid = (wv['e_form_per_atom_uncorrected'] + wv['e_correction_per_atom_mp2020']
             - wv['e_form_per_atom_mp2020_corrected'])
    max_resid = float(resid.abs().max())
    print(f'[gate0] identity uncorrected+correction==corrected : max|resid|={max_resid:.2e} '
          f'over n={len(wv)} rows -> {"PASS" if max_resid < 1e-5 else "FAIL"}')
    assert max_resid < 1e-5, 'MP2020 correction identity broken; aborting'

    w['family'] = w['formula'].apply(anion_family)
    corr = w[['material_id', 'family', 'e_correction_per_atom_mp2020',
              'e_form_per_atom_mp2020_corrected']]

    # ---- resolve model CSV paths -----------------------------------------------------
    new_paths = {
        'mace_mp_0': os.path.join(args.new_4c_root, 'mace_mp_0_pred.csv'),
        'mattersim': os.path.join(args.new_4c_root, 'mattersim_pred.csv'),
        'sevennet_mf_ompa': os.path.join(args.new_4c_root, 'sevennet_mf_ompa_pred.csv'),
        'orb_v3': args.orb_v3_csv,
    }
    legacy_paths = {m: os.path.join(args.legacy_root, f'{m}_pred.csv') for m in LEGACY}

    # ---- GATE 2 helper: per-stratum mean bias (pred - corrected truth) --------------
    def bias_table(pred_df: pd.DataFrame, use_corrected_pred: bool) -> dict:
        m = corr.merge(pred_df, on='material_id', how='inner').dropna(
            subset=['e_form_pred', 'e_correction_per_atom_mp2020', 'e_form_per_atom_mp2020_corrected'])
        pred = m['e_form_pred'] + (m['e_correction_per_atom_mp2020'] if use_corrected_pred else 0.0)
        m = m.assign(bias=pred - m['e_form_per_atom_mp2020_corrected'])
        g = m.groupby('family')['bias'].mean()
        return {f: (round(float(g[f]), 4) if f in g.index else None) for f in FAM_ORDER}

    validation = {'gate0_identity_max_resid': max_resid, 'n_identity_rows': int(len(wv)),
                  'method': ('e_form_pred_mp2020 = e_form_pred_raw + '
                             'e_correction_per_atom_mp2020 (matbench-discovery per-material '
                             'MP2020 correction from 2023-12-13-wbm-summary.csv.gz); applied '
                             'to the 4 NEW models only; 4 legacy CSVs already corrected -> '
                             'copied through unchanged.'),
                  'legacy_before': {}, 'legacy_after_WOULD_OVERCORRECT': {},
                  'new_before': {}, 'new_after': {}, 'outputs': {}}

    # legacy: show before (~0) and that applying correction WOULD over-correct (why we skip it)
    for m in LEGACY:
        p = load_pred(legacy_paths[m])
        validation['legacy_before'][m] = bias_table(p, use_corrected_pred=False)
        validation['legacy_after_WOULD_OVERCORRECT'][m] = bias_table(p, use_corrected_pred=True)
        # copy legacy unchanged into roster
        dst = os.path.join(roster_dir, f'{m}_pred.csv')
        shutil.copyfile(legacy_paths[m], dst)
        validation['outputs'][f'roster/{m}_pred.csv (legacy, unchanged)'] = sha256(dst)

    # new: before (biased) and after (corrected); write deliverable + roster copies
    for m in NEW:
        p = load_pred(new_paths[m])
        validation['new_before'][m] = bias_table(p, use_corrected_pred=False)
        validation['new_after'][m] = bias_table(p, use_corrected_pred=True)
        merged = corr[['material_id', 'e_correction_per_atom_mp2020']].merge(
            p, on='material_id', how='inner')
        merged['e_form_pred'] = merged['e_form_pred'] + merged['e_correction_per_atom_mp2020']
        out = merged[['material_id', 'e_form_pred']].copy()
        n_raw = len(p)
        n_out = len(out)
        deliverable = os.path.join(args.out_dir, f'{m}_pred_mp2020.csv')
        out.to_csv(deliverable, index=False)
        roster_csv = os.path.join(roster_dir, f'{m}_pred.csv')
        out.to_csv(roster_csv, index=False)
        validation['outputs'][f'{m}_pred_mp2020.csv (new, corrected)'] = {
            'sha256': sha256(deliverable), 'rows_in': int(n_raw), 'rows_out': int(n_out)}
        print(f'[write] {m}: {n_raw} raw rows -> {n_out} corrected rows '
              f'(before oxide bias {validation["new_before"][m]["oxide"]:+.3f} -> '
              f'after {validation["new_after"][m]["oxide"]:+.3f})')

    out_json = os.path.join(args.out_dir, 'oam_correction_validation.json')
    with open(out_json, 'w') as f:
        json.dump(validation, f, indent=2)
    print(f'[write] {out_json}')

    # ---- print the headline before/after table -------------------------------------
    print('\n=== per-stratum mean bias (pred - MP2020-corrected truth), eV/atom ===')
    hdr = 'model'.ljust(22) + ''.join(f.ljust(14) for f in FAM_ORDER)
    print(hdr)
    for m in NEW:
        b, a = validation['new_before'][m], validation['new_after'][m]
        print(f'{m+" BEFORE":22}' + ''.join(f'{b[f]:+.3f}'.ljust(14) for f in FAM_ORDER))
        print(f'{m+" AFTER":22}' + ''.join(f'{a[f]:+.3f}'.ljust(14) for f in FAM_ORDER))
    for m in ['mace', 'orb']:
        b = validation['legacy_before'][m]
        print(f'{m+" (legacy)":22}' + ''.join(f'{b[f]:+.3f}'.ljust(14) for f in FAM_ORDER))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
