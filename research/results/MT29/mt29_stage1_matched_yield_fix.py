#!/usr/bin/env python
"""MT29 Stage-1 — CORRECTED matched-stable-call-YIELD control for the stratified-abstention
interaction (supersedes the vacuous yield control in mt29_stage1_chem_yield.py).

WHY a fix was needed
--------------------
The first Stage-1 pass defined the yield gain as precision(top y_low called) - precision(top
y_high called) where y_low/y_high were the per-stratum yields at cov0.5/cov0.9. Because the
confidence signal IS |margin| and the top-cov fraction is nested in the same confidence order
as the top-Y called-stable set, that gain came out numerically identical to the coverage gain
(mean |cov_int - yield_int| = 0.0005 over 60 pairs; 0 excl0-status flips). It did NOT control
the confound that killed MT28: different strata surface DIFFERENT ABSOLUTE NUMBERS of stable
calls, and a precision/DAF gain can be a yield-count artifact.

CORRECT matched-yield control (MT28 `precision_at_matched_yield` semantics, lifted to strata):
  Fix a COMMON ABSOLUTE yield budget Y (same integer count of surfaced stable candidates in
  EVERY stratum). For each stratum, rank its CALLED-STABLE structures by confidence and take the
  top-Y; precision/DAF of that fixed-count candidate set. Sweep a tight budget Y_tight and a
  loose budget Y_loose (Y_tight < Y_loose), both identical across strata. The matched-yield
  abstention gain = DAF(top Y_tight) - DAF(top Y_loose); the interaction = gain_A - gain_B
  across strata. Now BOTH the surfaced-candidate count AND its change are held identical across
  strata, so any surviving interaction is the abstention-quality-by-chemistry effect, not yield.

Budgets: Y_loose = floor of the min across strata of total called-stable (so every stratum can
supply it); Y_tight = Y_loose // 2. Per model (yields differ by model). DAF uses the per-stratum
stable base rate (precision/base_rate), so it is directly comparable across strata.

Shuffle-null: permute confidence within each stratum's called-stable set => top-Y is a random
Y-subset => gain ~ 0, interaction ~ 0.

CPU/pandas, on-disk cached preds, seed 20260621, 1000-boot percentile CIs.
"""
import os, json
import numpy as np
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mt29_stage1_chem_yield import (load, MODELS, SEED, N_BOOT, OUT_DIR, ci95, excl0)

RNG = np.random.default_rng(SEED)
FAM_ORDER = ['oxide', 'intermetallic', 'chalcogenide', 'halide', 'pnictide', 'other']
OUT_JSON = os.path.join(OUT_DIR, 'mt29_stage1_matched_yield_result.json')


def daf_top_y(conf_cs, st_cs, target_y, base_rate):
    """conf_cs/st_cs are confidence & truth arrays over the CALLED-STABLE structures of a
    stratum. Take the top target_y by confidence; DAF = precision / base_rate."""
    n = len(conf_cs)
    if n == 0 or target_y <= 0:
        return np.nan
    y = min(int(target_y), n)
    order = np.argsort(-conf_cs)[:y]
    prec = float(st_cs[order].sum() / y)
    return prec / base_rate if base_rate > 0 else np.nan


def boot_yield_gain(conf_cs, st_cs, base_rate, y_tight, y_loose, shuffle=False):
    """Bootstrap matched-yield abstention gain = DAF(top y_tight) - DAF(top y_loose),
    resampling WITHIN the called-stable set of the stratum. y_tight/y_loose are ABSOLUTE
    counts common across strata."""
    n = len(conf_cs)
    out = np.empty(N_BOOT)
    for b in range(N_BOOT):
        bs = RNG.integers(0, n, n)
        c = conf_cs[bs].copy()
        s = st_cs[bs]
        if shuffle:
            RNG.shuffle(c)
        out[b] = daf_top_y(c, s, y_tight, base_rate) - daf_top_y(c, s, y_loose, base_rate)
    return out[~np.isnan(out)]


def main():
    base = load()
    eft = base['e_form_per_atom_mp2020_corrected'].values
    ht = base['e_above_hull_mp2020_corrected_ppd_mp'].values
    true_stable = ht < 0.0
    fams = FAM_ORDER
    fam_idx = {f: np.where(base['family'].values == f)[0] for f in fams}

    pred_hull = {m: ht + (base[f'eform_{m}'].values - eft) for m in MODELS}
    conf = {m: np.abs(pred_hull[m]) for m in MODELS}
    pred_stable = {m: pred_hull[m] < 0.0 for m in MODELS}

    results = {'meta': {
        'story': 'G007-s1-materials-mt29-real-chemistry',
        'stage': 'Stage-1 GATE (corrected matched-yield)',
        'seed': SEED, 'n_boot': N_BOOT, 'models': MODELS, 'strata': fams,
        'control': 'COMMON ABSOLUTE stable-call yield Y across strata; DAF(top Y_tight) - '
                   'DAF(top Y_loose), Y identical across strata (genuine MT28 yield control).',
        'budget_rule': 'Y_loose = min over strata of total called-stable (per model); '
                       'Y_tight = Y_loose // 2.',
    }}

    per_model = {}
    inter_real = []
    inter_shuf = []
    n_real = 0
    n_shuf = 0
    for m in MODELS:
        # per-stratum called-stable confidence/truth + base rate + budgets
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
        per_model[m] = {'y_loose': int(y_loose), 'y_tight': int(y_tight),
                        'total_called_stable': {f: int(total_cs[f]) for f in fams},
                        'base_rate_stable': {f: round(br[f], 5) for f in fams},
                        'daf_top_y_tight': {f: round(float(daf_top_y(cs_conf[f], cs_st[f], y_tight, br[f])), 5) for f in fams},
                        'daf_top_y_loose': {f: round(float(daf_top_y(cs_conf[f], cs_st[f], y_loose, br[f])), 5) for f in fams}}
        # bootstrap gains
        gains = {f: boot_yield_gain(cs_conf[f], cs_st[f], br[f], y_tight, y_loose, False) for f in fams}
        gains_sh = {f: boot_yield_gain(cs_conf[f], cs_st[f], br[f], y_tight, y_loose, True) for f in fams}
        per_model[m]['gain_median'] = {f: round(float(np.median(gains[f])), 5) for f in fams}
        for i in range(len(fams)):
            for j in range(i + 1, len(fams)):
                a, b = fams[i], fams[j]
                L = min(len(gains[a]), len(gains[b]))
                if L < 100:
                    continue
                d = gains[a][:L] - gains[b][:L]
                ci = ci95(d); e = excl0(ci); n_real += int(e)
                inter_real.append(dict(model=m, stratumA=a, stratumB=b,
                                       gainA_med=round(float(np.median(gains[a])), 5),
                                       gainB_med=round(float(np.median(gains[b])), 5),
                                       interaction_med=round(float(np.median(d)), 5),
                                       interaction_ci95=[round(ci[0], 5), round(ci[1], 5)],
                                       excludes_0=e))
                Ls = min(len(gains_sh[a]), len(gains_sh[b]))
                if Ls >= 100:
                    ds = gains_sh[a][:Ls] - gains_sh[b][:Ls]
                    cis = ci95(ds); es = excl0(cis); n_shuf += int(es)
                    inter_shuf.append(dict(model=m, stratumA=a, stratumB=b,
                                           interaction_med=round(float(np.median(ds)), 5),
                                           interaction_ci95=[round(cis[0], 5), round(cis[1], 5)],
                                           excludes_0=es))

    results['per_model_budgets'] = per_model
    results['interactions_matched_yield'] = inter_real
    results['interactions_matched_yield_SHUFFLE'] = inter_shuf
    shuffle_clean = n_shuf <= max(1, int(0.05 * max(1, len(inter_shuf))))
    verdict = 'SUCCESS' if (n_real >= 1 and shuffle_clean) else ('KILL' if n_real == 0 else 'AMBIGUOUS')
    results['summary'] = {
        'n_pairs': len(inter_real),
        'matched_yield_excl0': f'{n_real}/{len(inter_real)}',
        'matched_yield_SHUFFLE_excl0': f'{n_shuf}/{len(inter_shuf)}',
        'shuffle_null_clean': bool(shuffle_clean),
        'verdict': verdict,
    }

    print(f"=== CORRECTED matched-yield interaction (common absolute Y across strata) ===")
    for m in MODELS:
        pm = per_model[m]
        print(f"  {m}: Y_tight={pm['y_tight']} Y_loose={pm['y_loose']}  "
              f"gain_med={pm['gain_median']}")
    print(f"\n  matched-YIELD interaction:          {n_real}/{len(inter_real)} CI-exclude-0")
    print(f"  matched-YIELD SHUFFLE-null:         {n_shuf}/{len(inter_shuf)} CI-exclude-0 (want ~0)")
    print(f"  VERDICT: {verdict}")
    print("\n  Top matched-yield interactions:")
    sig = [x for x in inter_real if x['excludes_0']]
    for x in sorted(sig, key=lambda z: -abs(z['interaction_med']))[:12]:
        print(f"    {x['model']:7s} {x['stratumA']:13s} vs {x['stratumB']:13s}: "
              f"int={x['interaction_med']:+.4f} CI{x['interaction_ci95']}")

    with open(OUT_JSON, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nWrote {OUT_JSON}")


if __name__ == '__main__':
    main()
