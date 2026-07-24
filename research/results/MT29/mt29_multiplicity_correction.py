#!/usr/bin/env python
"""MT29 — formal multiple-comparison correction (BH-FDR + Holm) for the matched-yield
stratified-abstention interaction cell families.

WHY
---
The manuscript's evidence summaries use a majority-of-cells heuristic (48/60 Stage-1 cells
CI-excl-0; 548/700 LOEO; 157/300 WBM-round) with no formal multiplicity control. The
2026-07-02 portfolio review flags this: "Add formal multiple-comparison correction
(FDR/Bonferroni) across the 60/700/300 cell families rather than the majority-of-cells
heuristic."

WHAT
----
Re-runs the IDENTICAL matched-yield machinery (same seed 20260621, same RNG-stream order,
same cached WBM summary + UIP prediction CSVs) as:
  * part stage1: mt29_stage1_matched_yield_fix.py  (60-cell family), and additionally a
    high-resolution pass at N_BOOT=10000 so per-cell bootstrap p-values can resolve below
    the Holm rank-1 threshold 0.05/60 = 8.3e-4 (at B=1000 the attainable two-sided floor is
    2/(B+1) ~ 2.0e-3, which mechanically zeroes Holm for m >= 25 regardless of effect size).
  * part stage2: mt29_stage2_robustness.py  (700-cell LOEO family + 300-cell WBM-round
    family), at the original N_BOOT=1000.

For every (model x stratum-pair [x split]) cell it computes, alongside the original
percentile CI, a two-sided bootstrap sign p-value on the paired gain difference d:
    p = min(1, 2 * min[(1 + #{d<=0})/(L+1), (1 + #{d>=0})/(L+1)])
then applies Benjamini-Hochberg (FDR q=0.05) and Holm-Bonferroni (FWER alpha=0.05) WITHIN
each cell family via relmetrics.multiplicity. Shuffle-null families get the same treatment
(expected: 0 BH rejections).

REPRODUCTION CHECK: for the N_BOOT=1000 passes, every reproduced cell's interaction_med,
interaction_ci95 and excludes_0 must match the frozen result JSONs EXACTLY (same RNG stream);
the script raises otherwise. Numbers are never copied from the frozen files — they are
recomputed and then asserted equal.

CPU/pandas only, on-disk cached predictions, no downloads.
Usage: python3 mt29_multiplicity_correction.py {stage1|stage2}
"""
import os, json, sys, platform
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, REPO_ROOT)

from mt29_stage1_chem_yield import (load, MODELS, SEED, N_BOOT, OUT_DIR, ci95, excl0,
                                    sha256, DATA, UIP, elements_of)
from mt29_stage2_robustness import dominant_elements, MIN_STRATUM, MIN_CALLED_STABLE
from relmetrics.multiplicity import benjamini_hochberg, holm_bonferroni
from relmetrics.provenance import stamp_result

FAM_ORDER = ['oxide', 'intermetallic', 'chalcogenide', 'halide', 'pnictide', 'other']
FROZEN_STAGE1 = os.path.join(OUT_DIR, 'mt29_stage1_matched_yield_result.json')
FROZEN_STAGE2 = os.path.join(OUT_DIR, 'mt29_stage2_robustness_result.json')
N_BOOT_HIRES = 10000


def pval_two_sided(d):
    """Two-sided bootstrap sign p-value with the +1 finite-sample correction.
    Floor = 2/(L+1); consistent with (but finer than) 95% percentile-CI exclusion."""
    L = len(d)
    p_le = (1 + int(np.sum(d <= 0))) / (L + 1)
    p_ge = (1 + int(np.sum(d >= 0))) / (L + 1)
    return min(1.0, 2.0 * min(p_le, p_ge))


def daf_top_y(conf_cs, st_cs, target_y, base_rate):
    n = len(conf_cs)
    if n == 0 or target_y <= 0:
        return np.nan
    y = min(int(target_y), n)
    order = np.argsort(-conf_cs)[:y]
    prec = float(st_cs[order].sum() / y)
    return prec / base_rate if base_rate > 0 else np.nan


def boot_yield_gain(rng, n_boot, conf_cs, st_cs, base_rate, y_tight, y_loose, shuffle=False):
    n = len(conf_cs)
    if n == 0:
        return np.array([])
    out = np.empty(n_boot)
    for b in range(n_boot):
        bs = rng.integers(0, n, n)
        c = conf_cs[bs].copy()
        s = st_cs[bs]
        if shuffle:
            rng.shuffle(c)
        out[b] = daf_top_y(c, s, y_tight, base_rate) - daf_top_y(c, s, y_loose, base_rate)
    return out[~np.isnan(out)]


# --------------------------- stage-1 family (mt29_stage1_matched_yield_fix.py flow) ---------------------------

def stage1_cells(base, n_boot, rng):
    """Identical flow/RNG order to mt29_stage1_matched_yield_fix.py main(), plus p-values."""
    eft = base['e_form_per_atom_mp2020_corrected'].values
    ht = base['e_above_hull_mp2020_corrected_ppd_mp'].values
    true_stable = ht < 0.0
    fams = FAM_ORDER
    fam_idx = {f: np.where(base['family'].values == f)[0] for f in fams}
    pred_hull = {m: ht + (base[f'eform_{m}'].values - eft) for m in MODELS}
    conf = {m: np.abs(pred_hull[m]) for m in MODELS}
    pred_stable = {m: pred_hull[m] < 0.0 for m in MODELS}

    real, shuf = [], []
    for m in MODELS:
        cs_conf = {}; cs_st = {}; br = {}; total_cs = {}
        for f in fams:
            idx = fam_idx[f]
            sp = pred_stable[m][idx]
            cs = np.where(sp)[0]
            cs_conf[f] = conf[m][idx][cs]
            cs_st[f] = true_stable[idx][cs]
            br[f] = float(true_stable[idx].mean())
            total_cs[f] = len(cs)
        y_loose = min(total_cs.values())
        y_tight = max(1, y_loose // 2)
        gains = {f: boot_yield_gain(rng, n_boot, cs_conf[f], cs_st[f], br[f], y_tight, y_loose, False) for f in fams}
        gains_sh = {f: boot_yield_gain(rng, n_boot, cs_conf[f], cs_st[f], br[f], y_tight, y_loose, True) for f in fams}
        for i in range(len(fams)):
            for j in range(i + 1, len(fams)):
                a, b = fams[i], fams[j]
                L = min(len(gains[a]), len(gains[b]))
                if L < 100:
                    continue
                d = gains[a][:L] - gains[b][:L]
                ci = ci95(d)
                real.append(dict(model=m, stratumA=a, stratumB=b,
                                 interaction_med=round(float(np.median(d)), 5),
                                 interaction_ci95=[round(ci[0], 5), round(ci[1], 5)],
                                 excludes_0=excl0(ci), p_raw=pval_two_sided(d)))
                Ls = min(len(gains_sh[a]), len(gains_sh[b]))
                if Ls >= 100:
                    ds = gains_sh[a][:Ls] - gains_sh[b][:Ls]
                    cis = ci95(ds)
                    shuf.append(dict(model=m, stratumA=a, stratumB=b,
                                     interaction_med=round(float(np.median(ds)), 5),
                                     interaction_ci95=[round(cis[0], 5), round(cis[1], 5)],
                                     excludes_0=excl0(cis), p_raw=pval_two_sided(ds)))
    return real, shuf


# --------------------------- stage-2 families (mt29_stage2_robustness.py flow) ---------------------------

def interaction_on_subset_p(base, mask, split_label, rng):
    """Identical flow/RNG order to mt29_stage2_robustness.interaction_on_subset, plus p-values."""
    sub = base[mask].reset_index(drop=True)
    eft = sub['e_form_per_atom_mp2020_corrected'].values
    ht = sub['e_above_hull_mp2020_corrected_ppd_mp'].values
    true_stable = ht < 0.0
    fam_vals = sub['family'].values
    fam_counts = {f: int((fam_vals == f).sum()) for f in FAM_ORDER}
    fams = [f for f in FAM_ORDER if fam_counts[f] >= MIN_STRATUM]
    fam_idx = {f: np.where(fam_vals == f)[0] for f in fams}
    pred_hull = {m: ht + (sub[f'eform_{m}'].values - eft) for m in MODELS}
    conf = {m: np.abs(pred_hull[m]) for m in MODELS}
    pred_stable = {m: pred_hull[m] < 0.0 for m in MODELS}

    real, shuf = [], []
    for m in MODELS:
        cs_conf = {}; cs_st = {}; br = {}; total_cs = {}
        usable = []
        for f in fams:
            idx = fam_idx[f]
            sp = pred_stable[m][idx]
            cs = np.where(sp)[0]
            cs_conf[f] = conf[m][idx][cs]
            cs_st[f] = true_stable[idx][cs]
            br[f] = float(true_stable[idx].mean())
            total_cs[f] = len(cs)
            if len(cs) >= MIN_CALLED_STABLE and br[f] > 0:
                usable.append(f)
        if len(usable) < 2:
            continue
        y_loose = min(total_cs[f] for f in usable)
        y_tight = max(1, y_loose // 2)
        gains = {f: boot_yield_gain(rng, N_BOOT, cs_conf[f], cs_st[f], br[f], y_tight, y_loose, False) for f in usable}
        gains_sh = {f: boot_yield_gain(rng, N_BOOT, cs_conf[f], cs_st[f], br[f], y_tight, y_loose, True) for f in usable}
        for i in range(len(usable)):
            for j in range(i + 1, len(usable)):
                a, b = usable[i], usable[j]
                L = min(len(gains[a]), len(gains[b]))
                if L < 100:
                    continue
                d = gains[a][:L] - gains[b][:L]
                ci = ci95(d)
                real.append(dict(split=split_label, model=m, stratumA=a, stratumB=b,
                                 interaction_med=round(float(np.median(d)), 5),
                                 interaction_ci95=[round(ci[0], 5), round(ci[1], 5)],
                                 excludes_0=excl0(ci), p_raw=pval_two_sided(d)))
                Ls = min(len(gains_sh[a]), len(gains_sh[b]))
                if Ls >= 100:
                    ds = gains_sh[a][:Ls] - gains_sh[b][:Ls]
                    cis = ci95(ds)
                    shuf.append(dict(split=split_label, model=m, stratumA=a, stratumB=b,
                                     interaction_med=round(float(np.median(ds)), 5),
                                     interaction_ci95=[round(cis[0], 5), round(cis[1], 5)],
                                     excludes_0=excl0(cis), p_raw=pval_two_sided(ds)))
    return real, shuf


# --------------------------- verification against frozen JSONs ---------------------------

def cell_key(c):
    return (c.get('split', ''), c['model'], c['stratumA'], c['stratumB'])


def assert_reproduces(cells, frozen_cells, label):
    frozen = {cell_key(c): c for c in frozen_cells}
    if len(cells) != len(frozen_cells):
        raise AssertionError(f'{label}: cell count {len(cells)} != frozen {len(frozen_cells)}')
    n_bad = 0
    for c in cells:
        f = frozen.get(cell_key(c))
        if f is None or c['interaction_med'] != f['interaction_med'] \
                or c['interaction_ci95'] != f['interaction_ci95'] \
                or bool(c['excludes_0']) != bool(f['excludes_0']):
            n_bad += 1
    if n_bad:
        raise AssertionError(f'{label}: {n_bad}/{len(cells)} reproduced cells mismatch frozen JSON')
    print(f'  [OK] {label}: all {len(cells)} reproduced cells match frozen JSON exactly', flush=True)


# --------------------------- multiplicity report ---------------------------

def family_report(cells, label, n_boot):
    p = [c['p_raw'] for c in cells]
    bh = benjamini_hochberg(p, alpha=0.05)
    holm = holm_bonferroni(p, alpha=0.05)
    for c, pb, rb, ph, rh in zip(cells, bh['adjusted_p'], bh['reject'],
                                 holm['adjusted_p'], holm['reject']):
        c['p_bh_adjusted'] = round(float(pb), 6)
        c['reject_bh_q05'] = bool(rb)
        c['p_holm_adjusted'] = round(float(ph), 6)
        c['reject_holm_a05'] = bool(rh)
    m = len(cells)
    floor = 2.0 / (n_boot + 1)
    rep = {
        'family': label, 'n_cells': m, 'n_boot': n_boot,
        'pvalue_floor_two_sided': round(floor, 6),
        'n_excl0_unadjusted_ci': int(sum(c['excludes_0'] for c in cells)),
        'n_reject_bh_fdr_q05': int(bh['reject'].sum()),
        'n_reject_holm_fwer_a05': int(holm['reject'].sum()),
        'holm_resolution_limited': bool(floor > 0.05 / m),
        'holm_note': ('Holm rank-1 threshold 0.05/m = %.2e; attainable p floor = %.2e — Holm '
                      'counts are resolution-limited at this bootstrap size, use BH-FDR.'
                      % (0.05 / m, floor)) if floor > 0.05 / m else None,
    }
    print(f"  {label}: m={m} | CI-excl-0 {rep['n_excl0_unadjusted_ci']} | "
          f"BH-FDR(q=.05) {rep['n_reject_bh_fdr_q05']} | Holm(a=.05) {rep['n_reject_holm_fwer_a05']}"
          f"{' [Holm resolution-limited]' if rep['holm_resolution_limited'] else ''}", flush=True)
    return rep


def write_out(results, out_json, manifest_path):
    stamp_result(results, __file__, seeds=[SEED])
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(out_json, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f'\nWrote {out_json}', flush=True)
    import pandas as _pd
    manifest = {
        'cmd': ' '.join([sys.executable] + sys.argv),
        'script_sha256': sha256(os.path.abspath(__file__)),
        'git_head': results['provenance'].get('git_sha'),
        'seed': SEED,
        'inputs': {os.path.basename(DATA): sha256(DATA),
                   **{f'{m}_pred.csv': sha256(os.path.join(UIP, f'{m}_pred.csv')) for m in MODELS}},
        'output_sha256': sha256(out_json),
        'versions': {'python': platform.python_version(), 'numpy': np.__version__,
                     'pandas': _pd.__version__},
        'platform': platform.platform(),
    }
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f'Wrote {manifest_path}', flush=True)


def main_stage1():
    base = load()
    results = {'meta': {
        'story': 'G007-mt29-multiplicity-correction-stage1',
        'seed': SEED,
        'pvalue_def': 'two-sided bootstrap sign p on the paired gain difference d: '
                      'p = min(1, 2*min[(1+#{d<=0})/(L+1), (1+#{d>=0})/(L+1)])',
        'procedures': 'Benjamini-Hochberg FDR q=0.05; Holm-Bonferroni FWER alpha=0.05 '
                      '(relmetrics.multiplicity), applied WITHIN each cell family.',
        'reproduction': 'N_BOOT=1000 pass replicates the exact RNG stream of '
                        'mt29_stage1_matched_yield_fix.py and is asserted cell-by-cell '
                        'identical (median, CI, excl0) to the frozen result JSON.',
    }}
    print(f'=== stage-1 family, N_BOOT={N_BOOT} (reproduction + p-values) ===', flush=True)
    rng = np.random.default_rng(SEED)
    real, shuf = stage1_cells(base, N_BOOT, rng)
    with open(FROZEN_STAGE1) as f:
        frozen = json.load(f)
    assert_reproduces(real, frozen['interactions_matched_yield'], 'stage1 real (B=1000)')
    assert_reproduces(shuf, frozen['interactions_matched_yield_SHUFFLE'], 'stage1 shuffle (B=1000)')
    reports = [family_report(real, 'stage1_matched_yield_B1000', N_BOOT),
               family_report(shuf, 'stage1_matched_yield_SHUFFLE_B1000', N_BOOT)]
    results['stage1_B1000'] = {'cells': real, 'cells_SHUFFLE': shuf}

    print(f'\n=== stage-1 family, N_BOOT={N_BOOT_HIRES} (high-resolution p-values) ===', flush=True)
    rng_h = np.random.default_rng(SEED)
    real_h, shuf_h = stage1_cells(base, N_BOOT_HIRES, rng_h)
    reports += [family_report(real_h, f'stage1_matched_yield_B{N_BOOT_HIRES}', N_BOOT_HIRES),
                family_report(shuf_h, f'stage1_matched_yield_SHUFFLE_B{N_BOOT_HIRES}', N_BOOT_HIRES)]
    results['stage1_hires'] = {'n_boot': N_BOOT_HIRES, 'cells': real_h, 'cells_SHUFFLE': shuf_h}

    hi_excl = sum(c['excludes_0'] for c in real_h)
    ox_hal = next((c for c in real_h if c['model'] == 'chgnet'
                   and {c['stratumA'], c['stratumB']} == {'oxide', 'halide'}), None)
    results['family_reports'] = reports
    results['summary'] = {
        'B1000_ci_excl0': f"{sum(c['excludes_0'] for c in real)}/{len(real)}",
        'B1000_bh_fdr_q05': f"{reports[0]['n_reject_bh_fdr_q05']}/{len(real)}",
        'B1000_shuffle_bh_fdr_q05': f"{reports[1]['n_reject_bh_fdr_q05']}/{len(shuf)}",
        'hires_ci_excl0': f'{hi_excl}/{len(real_h)}',
        'hires_bh_fdr_q05': f"{reports[2]['n_reject_bh_fdr_q05']}/{len(real_h)}",
        'hires_holm_fwer_a05': f"{reports[2]['n_reject_holm_fwer_a05']}/{len(real_h)}",
        'hires_shuffle_bh_fdr_q05': f"{reports[3]['n_reject_bh_fdr_q05']}/{len(shuf_h)}",
        'chgnet_oxide_vs_halide_hires': ox_hal,
    }
    print('\n=== SUMMARY ===', flush=True)
    print(json.dumps(results['summary'], indent=2, default=str), flush=True)
    write_out(results, os.path.join(OUT_DIR, 'mt29_multiplicity_stage1_result.json'),
              os.path.join(OUT_DIR, 'mt29_multiplicity_stage1_manifest.json'))


def main_stage2():
    base = load()
    base['wbm_round'] = base['material_id'].str.extract(r'wbm-(\d+)-')[0].astype(int)
    results = {'meta': {
        'story': 'G003-mt29-multiplicity-correction-stage2',
        'seed': SEED, 'n_boot': N_BOOT,
        'pvalue_def': 'two-sided bootstrap sign p on the paired gain difference d: '
                      'p = min(1, 2*min[(1+#{d<=0})/(L+1), (1+#{d>=0})/(L+1)])',
        'procedures': 'Benjamini-Hochberg FDR q=0.05; Holm-Bonferroni FWER alpha=0.05 '
                      '(relmetrics.multiplicity), applied WITHIN the LOEO (700-cell) and '
                      'WBM-round (300-cell) families.',
        'reproduction': 'Replicates the exact RNG stream of mt29_stage2_robustness.py and is '
                        'asserted cell-by-cell identical to the frozen result JSON.',
    }}
    rng = np.random.default_rng(SEED)
    elems, _ = dominant_elements(base, top_n=8)
    print(f'=== stage-2 LOEO family ({elems}) ===', flush=True)
    loeo_real, loeo_shuf = [], []
    for e in elems:
        mask = ~base['formula'].apply(lambda fo, e=e: e in set(elements_of(fo))).values
        r, s = interaction_on_subset_p(base, mask, f'LOEO_drop_{e}', rng)
        print(f'  drop {e:2s}: cells={len(r)} excl0={sum(c["excludes_0"] for c in r)}', flush=True)
        loeo_real += r; loeo_shuf += s
    print(f'=== stage-2 WBM-round family ===', flush=True)
    round_real, round_shuf = [], []
    for rd in sorted(base['wbm_round'].unique()):
        mask = (base['wbm_round'] == rd).values
        r, s = interaction_on_subset_p(base, mask, f'round_{rd}', rng)
        print(f'  round {rd}: cells={len(r)} excl0={sum(c["excludes_0"] for c in r)}', flush=True)
        round_real += r; round_shuf += s

    with open(FROZEN_STAGE2) as f:
        frozen = json.load(f)
    froz_loeo = [c for e in frozen['gate1_loeo'] for c in frozen['gate1_loeo'][e]['interactions']]
    froz_loeo_sh = [c for e in frozen['gate1_loeo'] for c in frozen['gate1_loeo'][e]['interactions_SHUFFLE']]
    froz_rnd = [c for r in frozen['gate2_rounds'] for c in frozen['gate2_rounds'][r]['interactions']]
    froz_rnd_sh = [c for r in frozen['gate2_rounds'] for c in frozen['gate2_rounds'][r]['interactions_SHUFFLE']]
    assert_reproduces(loeo_real, froz_loeo, 'stage2 LOEO real')
    assert_reproduces(loeo_shuf, froz_loeo_sh, 'stage2 LOEO shuffle')
    assert_reproduces(round_real, froz_rnd, 'stage2 round real')
    assert_reproduces(round_shuf, froz_rnd_sh, 'stage2 round shuffle')

    reports = [family_report(loeo_real, 'stage2_loeo', N_BOOT),
               family_report(loeo_shuf, 'stage2_loeo_SHUFFLE', N_BOOT),
               family_report(round_real, 'stage2_rounds', N_BOOT),
               family_report(round_shuf, 'stage2_rounds_SHUFFLE', N_BOOT)]
    results['loeo'] = {'cells': loeo_real, 'cells_SHUFFLE': loeo_shuf}
    results['rounds'] = {'cells': round_real, 'cells_SHUFFLE': round_shuf}
    results['family_reports'] = reports
    results['summary'] = {
        'loeo_ci_excl0': f"{sum(c['excludes_0'] for c in loeo_real)}/{len(loeo_real)}",
        'loeo_bh_fdr_q05': f"{reports[0]['n_reject_bh_fdr_q05']}/{len(loeo_real)}",
        'loeo_shuffle_bh_fdr_q05': f"{reports[1]['n_reject_bh_fdr_q05']}/{len(loeo_shuf)}",
        'rounds_ci_excl0': f"{sum(c['excludes_0'] for c in round_real)}/{len(round_real)}",
        'rounds_bh_fdr_q05': f"{reports[2]['n_reject_bh_fdr_q05']}/{len(round_real)}",
        'rounds_shuffle_bh_fdr_q05': f"{reports[3]['n_reject_bh_fdr_q05']}/{len(round_shuf)}",
        'holm_note': 'Holm at m=700/300 requires p below 7.1e-5 / 1.7e-4; the attainable '
                     'floor at B=1000 is 2.0e-3, so Holm is resolution-limited here — '
                     'BH-FDR is the reported formal correction for these families.',
    }
    print('\n=== SUMMARY ===', flush=True)
    print(json.dumps(results['summary'], indent=2, default=str), flush=True)
    write_out(results, os.path.join(OUT_DIR, 'mt29_multiplicity_stage2_result.json'),
              os.path.join(OUT_DIR, 'mt29_multiplicity_stage2_manifest.json'))


if __name__ == '__main__':
    part = sys.argv[1] if len(sys.argv) > 1 else 'stage1'
    if part == 'stage1':
        main_stage1()
    elif part == 'stage2':
        main_stage2()
    else:
        raise SystemExit('usage: mt29_multiplicity_correction.py {stage1|stage2}')
