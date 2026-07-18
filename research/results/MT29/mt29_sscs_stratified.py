#!/usr/bin/env python
"""MT29 M1 · E3 — SSCS-style per-stratum conditional-coverage on the native-Gaussian p_stable.

Reuses the zero-free-parameter native-Gaussian probability from
mt29_crossgen_reliability_exec_2026_06_29.py:
    err = e_form_pred - e_form_true;  hull_pred = hull_true + err
    sigma = RMSE(err) on the 50/50 CALIBRATION half (seed 20260629)
    p_native = Phi(-hull_pred / sigma)   scored on the TEST half
and stratifies by the genuine anion-class family (from mt29_stage1_chem_yield.anion_family).

Per anion-family stratum on the TEST half we report the conditional-coverage /
calibration-in-the-large gap:
    gap = mean(p_native) - empirical_stable_rate      (stable_true = e_above_hull < 0)
with a 1000-boot percentile 95% CI (resample within stratum). Aggregate, size-stratified-coverage
style:  SSCS = max_stratum |gap|   (worst-slab calibration deviation), with its own bootstrap CI.

Descriptive / defensive only — no gate. CPU/pandas, on-disk cached preds, seed 20260629.
"""
import os, sys, json
import numpy as np
from scipy.stats import norm
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mt29_stage1_chem_yield import load, MODELS, OUT_DIR, anion_family  # noqa

SEED = 20260629                     # match the crossgen native-Gaussian run
RNG = np.random.default_rng(SEED)
N_BOOT = 1000
FAM_ORDER = ['oxide', 'intermetallic', 'chalcogenide', 'halide', 'pnictide', 'other']
MIN_STRATUM = 200                   # need enough test-half rows for a stable per-stratum CI
OUT_JSON = os.path.join(OUT_DIR, 'mt29_sscs_stratified.json')


def native_p_stable(eform_pred, eft, hull_true):
    """Exact crossgen recipe: sigma = RMSE(err) on cal half, p = Phi(-hull_pred/sigma) on test."""
    err = eform_pred - eft
    hull_pred = hull_true + err
    n = len(err)
    half = n // 2
    perm = RNG.permutation(n)
    cal, test = perm[:half], perm[half:]
    sigma = float(np.sqrt(np.mean(err[cal] ** 2)))
    p_native = norm.cdf(-hull_pred / sigma)
    return p_native, test, sigma


def boot_gap_ci(p, y):
    """1000-boot percentile 95% CI of gap = mean(p) - mean(y), resampled within the stratum."""
    n = len(p)
    vals = np.empty(N_BOOT)
    for b in range(N_BOOT):
        idx = RNG.integers(0, n, n)
        vals[b] = p[idx].mean() - y[idx].mean()
    return [round(float(np.percentile(vals, 2.5)), 5), round(float(np.percentile(vals, 97.5)), 5)]


def main():
    base = load()
    eft = base['e_form_per_atom_mp2020_corrected'].values
    hull_true = base['e_above_hull_mp2020_corrected_ppd_mp'].values
    stable_true = (hull_true < 0.0).astype(float)
    family = base['family'].values

    out = {'meta': {
        'story': 'G007-s1-materials-mt29-sscs-stratified',
        'stage': 'M1/E3 SSCS-style per-stratum conditional coverage (native-Gaussian p_stable)',
        'seed': SEED, 'n_boot': N_BOOT, 'models': MODELS, 'min_stratum_test': MIN_STRATUM,
        'probability_model': 'native Gaussian p_stable = Phi(-hull_pred/sigma), sigma=RMSE(err) on '
                             'cal half, scored on test half (reused from crossgen exec 2026-06-29).',
        'conditional_coverage_def': 'per anion-family stratum on TEST half: gap = mean(p_native) - '
                                    'empirical_stable_rate (calibration-in-the-large per stratum).',
        'SSCS_def': 'max_stratum |gap| = worst-slab calibration deviation (size-stratified-coverage '
                    'style); reported per model with a within-model bootstrap CI.',
        'stable_definition': 'e_above_hull_mp2020_corrected_ppd_mp < 0',
    }}

    per_model = {}
    sscs_vals = []
    for m in MODELS:
        p_native, test, sigma = native_p_stable(base[f'eform_{m}'].values, eft, hull_true)
        pt = p_native[test]; yt = stable_true[test]; famt = family[test]
        strata = {}
        gaps_for_sscs = {}
        for f in FAM_ORDER:
            sel = np.where(famt == f)[0]
            n_f = len(sel)
            if n_f < MIN_STRATUM:
                strata[f] = {'n_test': int(n_f), 'skipped_small': True}
                continue
            pf = pt[sel]; yf = yt[sel]
            gap = float(pf.mean() - yf.mean())
            ci = boot_gap_ci(pf, yf)
            strata[f] = {'n_test': int(n_f),
                         'empirical_stable_rate': round(float(yf.mean()), 5),
                         'mean_p_native': round(float(pf.mean()), 5),
                         'coverage_gap': round(gap, 5),
                         'coverage_gap_ci95': ci,
                         'gap_excludes_0': bool(ci[0] > 0 or ci[1] < 0)}
            gaps_for_sscs[f] = abs(gap)

        # SSCS = worst-slab |gap|; bootstrap CI on the max|gap| across strata (paired resample)
        used = [f for f in FAM_ORDER if f in gaps_for_sscs]
        worst_f = max(used, key=lambda f: gaps_for_sscs[f])
        sscs = gaps_for_sscs[worst_f]
        # bootstrap the whole SSCS statistic: per draw, recompute |gap| for every used stratum, take max
        boot_sscs = np.empty(N_BOOT)
        cache = {f: (pt[np.where(famt == f)[0]], yt[np.where(famt == f)[0]]) for f in used}
        for b in range(N_BOOT):
            mx = 0.0
            for f in used:
                pf, yf = cache[f]
                idx = RNG.integers(0, len(pf), len(pf))
                mx = max(mx, abs(pf[idx].mean() - yf[idx].mean()))
            boot_sscs[b] = mx
        sscs_ci = [round(float(np.percentile(boot_sscs, 2.5)), 5),
                   round(float(np.percentile(boot_sscs, 97.5)), 5)]
        per_model[m] = {'sigma_rmse_cal': round(sigma, 5), 'n_test': int(len(test)),
                        'strata': strata, 'strata_used': used,
                        'SSCS_worst_slab_absgap': round(sscs, 5),
                        'SSCS_worst_stratum': worst_f, 'SSCS_ci95': sscs_ci}
        sscs_vals.append(sscs)
        print(f"  {m:7s} sigma={sigma:.4f} SSCS(max|gap|)={sscs:.4f} @ {worst_f} CI{sscs_ci}")
        for f in used:
            s = strata[f]
            print(f"      {f:13s} n={s['n_test']:6d} rate={s['empirical_stable_rate']:.4f} "
                  f"p={s['mean_p_native']:.4f} gap={s['coverage_gap']:+.4f} CI{s['coverage_gap_ci95']} "
                  f"excl0={s['gap_excludes_0']}")

    out['per_model'] = per_model
    out['summary'] = {
        'mean_SSCS_over_models': round(float(np.mean(sscs_vals)), 5),
        'max_SSCS_over_models': round(float(np.max(sscs_vals)), 5),
        'per_model_SSCS': {m: per_model[m]['SSCS_worst_slab_absgap'] for m in MODELS},
        'per_model_worst_stratum': {m: per_model[m]['SSCS_worst_stratum'] for m in MODELS},
    }
    print('\nSSCS summary:', json.dumps(out['summary'], indent=1))

    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2, default=str)
    print(f"Wrote {OUT_JSON}")


if __name__ == '__main__':
    main()
