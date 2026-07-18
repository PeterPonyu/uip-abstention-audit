#!/usr/bin/env python
"""MT29 Stage-1 — matched-yield stratified-abstention interaction under ALTERNATIVE stratum
definitions (robustness of the chemistry-dependence beyond the single anion-priority rule).

Clone of mt29_stage1_matched_yield_fix.py with the `family` column construction PARAMETERIZED
by --stratifier; every statistic, seed (20260621), and the matched-yield discipline are held
IDENTICAL to that script. Only the strata change:

  electronegativity_q5 : composition-weighted mean Pauling electronegativity
                         (mean_EN = sum_i n_i*X(el_i) / sum_i n_i, X = pymatgen Element().X),
                         quintiles q1..q5 (q5 = highest mean-EN = most oxide-like). Rows with any
                         element of undefined Pauling X (noble gases) are dropped and reported.
  metal_fraction       : amount-weighted metal fraction (metal iff pymatgen Element().is_metal;
                         metalloids B/Si/Ge/As/Sb/Te/Po/At count as NON-metal — a rule deliberately
                         distinct from the anion-priority METALS set). Fixed bins mf1=[0,1/3),
                         mf2=[1/3,1/2), mf3=[1/2,2/3), mf4=[2/3,1.0), mf5={1.0} (mf1 = most oxide-like).

Strata are ordered MOST-OXIDE-LIKE -> LEAST; the interaction of each pair (A,B), A more oxide-like,
is gain_A - gain_B. "Same direction as the anion result" (oxide = highest abstention benefit) =
interaction CI entirely ABOVE 0.

Matched-yield control (identical to the anion Stage-1 fix): fix a COMMON ABSOLUTE yield budget Y
across strata; DAF(top Y_tight) - DAF(top Y_loose), Y_loose = min over usable strata of total
called-stable (per model), Y_tight = Y_loose // 2. DAF = precision / stratum stable base-rate.

CIs / medians / excl0 at N_BOOT=1000 (percentile 95%); two-sided bootstrap sign p-values at
N_BOOT_HIRES=10000 (so Holm within a <=40-cell family is not resolution-limited: floor 2/(B+1) =
2.0e-4 < 0.05/40). Shuffle-null permutes confidence within each stratum's called-stable set.

Prereg: research/results/MT29/PREREG-altstrat-2026-07-02.md (committed ex ante).
CPU only, on-disk cached preds, no downloads.
Usage: python3 mt29_stage1_altstrat.py --stratifier {electronegativity_q5|metal_fraction}
"""
import os, sys, json, argparse, platform, warnings
import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')  # pymatgen noble-gas X UserWarnings are handled explicitly
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, '/home/zeyufu/Desktop/ml-reliability-research/reliability-commons')

from mt29_stage1_chem_yield import (load, MODELS, SEED, N_BOOT, OUT_DIR, ci95, excl0,
                                    sha256, DATA, UIP, TOKEN_RE)
from relmetrics.provenance import stamp_result

from pymatgen.core import Element

N_BOOT_HIRES = 10000
MIN_STRATUM = 500
MIN_CALLED_STABLE = 40

# strata ordered MOST-oxide-like -> LEAST (so pair (A,B) i<j has A the more oxide-like stratum)
STRATA_ORDER = {
    'electronegativity_q5': ['q5', 'q4', 'q3', 'q2', 'q1'],
    'metal_fraction': ['mf1', 'mf2', 'mf3', 'mf4', 'mf5'],
}

# element-property caches (pymatgen)
_X = {}
_METAL = {}


def elem_X(sym):
    if sym not in _X:
        try:
            v = Element(sym).X
        except Exception:
            v = float('nan')
        _X[sym] = float(v)
    return _X[sym]


def elem_is_metal(sym):
    if sym not in _METAL:
        try:
            _METAL[sym] = bool(Element(sym).is_metal)
        except Exception:
            _METAL[sym] = False
    return _METAL[sym]


def composition(formula):
    """Parse the WBM formula (space-separated integer counts, e.g. 'Ac6 U2') into {el: amount}."""
    out = {}
    for m in TOKEN_RE.finditer(str(formula)):
        el = m.group(1)
        if not el:
            continue
        c = m.group(2)
        out[el] = out.get(el, 0.0) + (float(c) if c else 1.0)
    return out


def mean_electronegativity(formula):
    comp = composition(formula)
    tot = sum(comp.values())
    if tot <= 0:
        return float('nan')
    xs = [elem_X(e) for e in comp]
    if any(np.isnan(x) for x in xs):
        return float('nan')  # undefined Pauling X (noble gas) -> row dropped downstream
    return sum(comp[e] * elem_X(e) for e in comp) / tot


def metal_fraction(formula):
    comp = composition(formula)
    tot = sum(comp.values())
    if tot <= 0:
        return float('nan')
    return sum(v for e, v in comp.items() if elem_is_metal(e)) / tot


def build_family(base, stratifier):
    """Return (base_kept, meta) with base_kept['family'] set to the alt-stratifier labels."""
    b = base.copy()
    meta = {}
    if stratifier == 'electronegativity_q5':
        b['mean_EN'] = b['formula'].apply(mean_electronegativity)
        n_before = len(b)
        b = b[~b['mean_EN'].isna()].reset_index(drop=True)
        n_dropped = n_before - len(b)
        edges = np.quantile(b['mean_EN'].values, [0, .2, .4, .6, .8, 1.0])
        # q1..q5 by ascending mean_EN; digitize on interior edges, right=False, clamp last bin
        lab = np.digitize(b['mean_EN'].values, edges[1:-1], right=False)  # 0..4
        lab = np.clip(lab, 0, 4)
        b['family'] = ['q%d' % (i + 1) for i in lab]
        meta = {'undefined_EN_rows_dropped': int(n_dropped),
                'quintile_edges_mean_EN': [round(float(e), 5) for e in edges],
                'averaging_rule': 'amount-weighted mean of pymatgen Element().X (Pauling)'}
    elif stratifier == 'metal_fraction':
        b['metal_frac'] = b['formula'].apply(metal_fraction)
        n_before = len(b)
        b = b[~b['metal_frac'].isna()].reset_index(drop=True)
        meta['undefined_metalfrac_rows_dropped'] = int(n_before - len(b))
        edges = [1.0 / 3.0, 1.0 / 2.0, 2.0 / 3.0, 1.0]  # interior breaks; mf5 is the ==1.0 bin
        mf = b['metal_frac'].values
        lab = np.digitize(mf, edges, right=False)  # 0..4 ; ==1.0 -> 4 (only exact 1.0 reaches bin4)
        b['family'] = ['mf%d' % (i + 1) for i in lab]
        meta['bin_edges'] = 'mf1=[0,1/3) mf2=[1/3,1/2) mf3=[1/2,2/3) mf4=[2/3,1.0) mf5={1.0}'
        meta['metal_rule'] = 'element is metal iff pymatgen Element().is_metal (metalloids -> non-metal)'
    else:
        raise SystemExit('unknown stratifier: %s' % stratifier)
    return b, meta


# ----------------------------- matched-yield machinery (identical to Stage-1 fix) -----------------------------

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


def pval_two_sided(d):
    L = len(d)
    if L == 0:
        return 1.0
    p_le = (1 + int(np.sum(d <= 0))) / (L + 1)
    p_ge = (1 + int(np.sum(d >= 0))) / (L + 1)
    return min(1.0, 2.0 * min(p_le, p_ge))


def per_model_cells(base, fams, n_boot, rng, want_p=False):
    """Compute (per model x usable stratum-pair) matched-yield interaction cells + shuffle cells,
    in the fixed model x stratum order (identical discipline to mt29_stage1_matched_yield_fix)."""
    eft = base['e_form_per_atom_mp2020_corrected'].values
    ht = base['e_above_hull_mp2020_corrected_ppd_mp'].values
    true_stable = ht < 0.0
    fam_vals = base['family'].values
    fam_idx = {f: np.where(fam_vals == f)[0] for f in fams}
    pred_hull = {m: ht + (base[f'eform_{m}'].values - eft) for m in MODELS}
    conf = {m: np.abs(pred_hull[m]) for m in MODELS}
    pred_stable = {m: pred_hull[m] < 0.0 for m in MODELS}

    real, shuf = [], []
    budgets = {}
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
            total_cs[f] = int(len(cs))
            if len(cs) >= MIN_CALLED_STABLE and br[f] > 0:
                usable.append(f)
        if len(usable) < 2:
            budgets[m] = {'usable_strata': usable, 'skipped': 'fewer than 2 usable strata'}
            continue
        y_loose = min(total_cs[f] for f in usable)
        y_tight = max(1, y_loose // 2)
        budgets[m] = {'usable_strata': usable, 'y_loose': int(y_loose), 'y_tight': int(y_tight),
                      'total_called_stable': {f: total_cs[f] for f in fams},
                      'base_rate_stable': {f: round(br[f], 5) for f in fams}}
        gains = {f: boot_yield_gain(rng, n_boot, cs_conf[f], cs_st[f], br[f], y_tight, y_loose, False)
                 for f in usable}
        gains_sh = {f: boot_yield_gain(rng, n_boot, cs_conf[f], cs_st[f], br[f], y_tight, y_loose, True)
                    for f in usable}
        for i in range(len(usable)):
            for j in range(i + 1, len(usable)):
                a, b = usable[i], usable[j]  # a is more oxide-like (fams is ordered so)
                L = min(len(gains[a]), len(gains[b]))
                if L < 100:
                    continue
                d = gains[a][:L] - gains[b][:L]
                ci = ci95(d)
                rec = dict(model=m, stratumA=a, stratumB=b,
                           gainA_med=round(float(np.median(gains[a])), 5),
                           gainB_med=round(float(np.median(gains[b])), 5),
                           interaction_med=round(float(np.median(d)), 5),
                           interaction_ci95=[round(ci[0], 5), round(ci[1], 5)],
                           excludes_0=excl0(ci),
                           ci_above_0=bool(ci[0] > 0))
                if want_p:
                    rec['p_raw'] = pval_two_sided(d)
                real.append(rec)
                Ls = min(len(gains_sh[a]), len(gains_sh[b]))
                if Ls >= 100:
                    ds = gains_sh[a][:Ls] - gains_sh[b][:Ls]
                    cis = ci95(ds)
                    srec = dict(model=m, stratumA=a, stratumB=b,
                                interaction_med=round(float(np.median(ds)), 5),
                                interaction_ci95=[round(cis[0], 5), round(cis[1], 5)],
                                excludes_0=excl0(cis), ci_above_0=bool(cis[0] > 0))
                    if want_p:
                        srec['p_raw'] = pval_two_sided(ds)
                    shuf.append(srec)
    return real, shuf, budgets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stratifier', required=True,
                    choices=['electronegativity_q5', 'metal_fraction'])
    args = ap.parse_args()
    strat = args.stratifier

    base0 = load()
    base, strat_meta = build_family(base0, strat)
    order = STRATA_ORDER[strat]
    fam_counts = base['family'].value_counts().to_dict()
    fams = [f for f in order if fam_counts.get(f, 0) >= MIN_STRATUM]
    dropped_small = [f for f in order if fam_counts.get(f, 0) < MIN_STRATUM]

    print(f"=== ALT-STRATIFIER: {strat} ===", flush=True)
    print(f"rows used: {len(base)}  strata sizes: "
          f"{ {f: int(fam_counts.get(f, 0)) for f in order} }", flush=True)
    print(f"strata >= MIN_STRATUM({MIN_STRATUM}): {fams}"
          f"{'  (dropped small: %s)' % dropped_small if dropped_small else ''}", flush=True)
    if len(fams) < 2:
        raise SystemExit('UNINFORMATIVE: fewer than 2 strata above MIN_STRATUM.')

    results = {'meta': {
        'story': f'G007-mt29-altstrat-{strat}',
        'stage': 'Stage-1 alt-stratification robustness (matched-yield interaction)',
        'prereg': 'research/results/MT29/PREREG-altstrat-2026-07-02.md',
        'stratifier': strat,
        'stratifier_definition': strat_meta,
        'strata_order_most_to_least_oxide_like': order,
        'strata_used': fams,
        'strata_sizes': {f: int(fam_counts.get(f, 0)) for f in order},
        'seed': SEED, 'n_boot': N_BOOT, 'n_boot_hires': N_BOOT_HIRES,
        'models': MODELS, 'min_stratum': MIN_STRATUM, 'min_called_stable': MIN_CALLED_STABLE,
        'stable_definition': 'e_above_hull_true < 0',
        'pred_hull_recipe': 'hull_pred = hull_true + (e_form_pred - e_form_true_mp2020_corrected)',
        'confidence_signal': '|predicted hull margin|',
        'matched_yield_control': 'common absolute Y across strata; DAF(top Y_tight) - DAF(top Y_loose), '
                                 'Y_loose = min over usable strata of total called-stable (per model), '
                                 'Y_tight = Y_loose // 2; DAF = precision / stratum stable base-rate.',
        'interaction_def': 'gain_A - gain_B, A the more-oxide-like stratum; bootstrapped within strata.',
        'direction_rule': 'same direction as anion result (oxide highest benefit) == CI entirely above 0.',
        'pvalue_def': 'two-sided bootstrap sign p on paired gain diff d, floor 2/(B+1); computed at '
                      'N_BOOT_HIRES so Holm within family is not resolution-limited.',
    }}

    # ---- B=1000 pass: CIs, medians, excl0, shuffle-null (fresh RNG seeded to SEED) ----
    rng = np.random.default_rng(SEED)
    real, shuf, budgets = per_model_cells(base, fams, N_BOOT, rng, want_p=False)
    # ---- B=10000 pass: hires p-values for the real cells (fresh RNG re-seeded to SEED) ----
    rng_h = np.random.default_rng(SEED)
    real_h, shuf_h, _ = per_model_cells(base, fams, N_BOOT_HIRES, rng_h, want_p=True)

    # attach hires p_raw onto the B=1000 real/shuffle cells by cell key
    def key(c):
        return (c['model'], c['stratumA'], c['stratumB'])
    ph_real = {key(c): c['p_raw'] for c in real_h}
    ph_shuf = {key(c): c['p_raw'] for c in shuf_h}
    for c in real:
        c['p_raw_hires'] = ph_real.get(key(c))
    for c in shuf:
        c['p_raw_hires'] = ph_shuf.get(key(c))

    n_cells = len(real)
    n_excl0 = sum(c['excludes_0'] for c in real)
    n_above0 = sum(c['ci_above_0'] for c in real)
    n_shuf = len(shuf)
    n_shuf_excl0 = sum(c['excludes_0'] for c in shuf)
    shuffle_clean = n_shuf_excl0 <= max(1, int(0.05 * max(1, n_shuf)))

    results['budgets'] = budgets
    results['cells'] = real
    results['cells_SHUFFLE'] = shuf
    results['summary'] = {
        'n_cells': n_cells,
        'ci_excl0': f'{n_excl0}/{n_cells}',
        'ci_above0_correct_direction': f'{n_above0}/{n_cells}',
        'shuffle_ci_excl0': f'{n_shuf_excl0}/{n_shuf}',
        'shuffle_null_clean': bool(shuffle_clean),
        'note': 'Holm/BH multiplicity + final SUCCESS/KILL verdict computed in '
                'mt29_altstrat_multiplicity.py per the prereg (Holm within family, BH across families).',
    }

    print(f"\n  cells: {n_cells}  CI-excl-0: {n_excl0}  CI-above-0 (correct dir): {n_above0}", flush=True)
    print(f"  shuffle-null CI-excl-0: {n_shuf_excl0}/{n_shuf}  clean={shuffle_clean}", flush=True)
    print(f"\n  Top correct-direction cells (CI above 0), |interaction| desc:", flush=True)
    sig = [c for c in real if c['ci_above_0']]
    for c in sorted(sig, key=lambda z: -abs(z['interaction_med']))[:12]:
        print(f"    {c['model']:7s} {c['stratumA']:4s} vs {c['stratumB']:4s}: "
              f"int={c['interaction_med']:+.4f} CI{c['interaction_ci95']} "
              f"p_hires={c['p_raw_hires']:.2e}", flush=True)

    stamp_result(results, __file__, seeds=[SEED])
    out_json = os.path.join(OUT_DIR, f'mt29_stage1_altstrat_{strat}_result.json')
    manifest_path = os.path.join(OUT_DIR, f'mt29_stage1_altstrat_{strat}_manifest.json')
    if os.path.exists(out_json):
        raise SystemExit(f'REFUSING to overwrite existing {out_json}')
    with open(out_json, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nWrote {out_json}", flush=True)

    manifest = {
        'cmd': ' '.join([sys.executable] + sys.argv),
        'script_sha256': sha256(os.path.abspath(__file__)),
        'git_head': results['provenance'].get('git_sha'),
        'seed': SEED, 'n_boot': N_BOOT, 'n_boot_hires': N_BOOT_HIRES,
        'stratifier': strat,
        'inputs': {os.path.basename(DATA): sha256(DATA),
                   **{f'{m}_pred.csv': sha256(os.path.join(UIP, f'{m}_pred.csv')) for m in MODELS}},
        'output_sha256': sha256(out_json),
        'versions': {'python': platform.python_version(), 'numpy': np.__version__,
                     'pandas': pd.__version__,
                     'pymatgen': __import__('importlib.metadata', fromlist=['version']).version('pymatgen')},
        'platform': platform.platform(),
    }
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote {manifest_path}", flush=True)


if __name__ == '__main__':
    main()
