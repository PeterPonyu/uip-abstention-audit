#!/usr/bin/env python
"""MT29 M1 · E1 — COMMITTEE-VARIANCE fork of mt29_stage1_matched_yield_fix.py.

Replaces the SINGLE-MODEL abstention signal (|hull_pred_m|, one model's margin) with the
COMMITTEE VARIANCE: the std across the 4 UIPs (chgnet/m3gnet/mace/orb) of the reconstructed
predicted hull. Low committee variance = high confidence (kept first); high variance = abstain.
Consensus stable call = committee MEAN predicted hull < 0.

Everything else is held IDENTICAL to the single-model matched-yield fix:
  - common ABSOLUTE matched yield Y across strata (Y_loose = min over strata of committee
    called-stable; Y_tight = Y_loose // 2),
  - DAF(top Y) = precision(top-Y most-agreed committee-called-stable) / per-stratum base rate,
  - matched-yield interaction = DAF(top Y_tight) - DAF(top Y_loose); interaction = gain_A - gain_B,
  - 1000-boot percentile 95% CIs, seed 20260621, within-stratum resampling,
  - shuffle-null: permute the committee variance within each stratum's called-stable set.

Because there is ONE committee (not 4 models), we get 15 stratum-pair interactions.

Two-branch gate is defined in research/results/MT29/M1_PREREG.md (written & committed before this
ran). This script computes both branch verdicts against the single-model reference JSON.

Point estimates use np.median of the bootstrap distribution (same convention as the single-model
fix: fields *_med / gain_median), NOT the bootstrap mean.
"""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mt29_stage1_chem_yield import load, MODELS, SEED, N_BOOT, OUT_DIR, ci95, excl0

RNG = np.random.default_rng(SEED)
FAM_ORDER = ['oxide', 'intermetallic', 'chalcogenide', 'halide', 'pnictide', 'other']
OUT_JSON = os.path.join(OUT_DIR, 'mt29_committee_variance.json')
SINGLE_JSON = os.path.join(OUT_DIR, 'mt29_stage1_matched_yield_result.json')


def daf_top_y(conf_cs, st_cs, target_y, base_rate):
    """conf_cs = confidence (HIGHER = keep first) over committee-called-stable structures of a
    stratum; st_cs = truth. Take the top target_y by confidence; DAF = precision / base_rate.
    For committee variance, confidence = -std, so 'top by confidence' = lowest-variance / most
    agreed structures."""
    n = len(conf_cs)
    if n == 0 or target_y <= 0:
        return np.nan
    y = min(int(target_y), n)
    order = np.argsort(-conf_cs)[:y]
    prec = float(st_cs[order].sum() / y)
    return prec / base_rate if base_rate > 0 else np.nan


def boot_yield_gain(conf_cs, st_cs, base_rate, y_tight, y_loose, shuffle=False):
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


def load_single_reference():
    """Per-pair single-model reference sign map + consensus significance from the existing
    single-model matched-yield JSON (pre-existing data referenced in the prereg)."""
    r = json.load(open(SINGLE_JSON))
    iy = r['interactions_matched_yield']
    from collections import defaultdict
    pairs = defaultdict(list)
    for x in iy:
        pairs[(x['stratumA'], x['stratumB'])].append(x)
    ref = {}
    for p, xs in pairs.items():
        sig = [x for x in xs if x['excludes_0']]
        signs = set(int(np.sign(x['interaction_med'])) for x in sig)
        s_single = signs.pop() if len(signs) == 1 else None  # defined iff sign-consistent
        nsig = len(sig)
        ref[p] = {'S_single': s_single, 'n_models_sig': nsig,
                  'excl0_single_consensus': bool(nsig >= 2)}
    dom = np.median([x['interaction_med'] for x in iy if x['excludes_0']])
    return ref, int(np.sign(dom))


def main():
    base = load()
    eft = base['e_form_per_atom_mp2020_corrected'].values
    ht = base['e_above_hull_mp2020_corrected_ppd_mp'].values
    true_stable = ht < 0.0
    fams = FAM_ORDER
    fam_idx = {f: np.where(base['family'].values == f)[0] for f in fams}

    # reconstructed predicted hull per model, then committee mean + variance (std)
    pred_hull = np.stack([ht + (base[f'eform_{m}'].values - eft) for m in MODELS], axis=1)  # (n,4)
    committee_mean = pred_hull.mean(axis=1)
    committee_std = pred_hull.std(axis=1, ddof=0)          # disagreement / abstention signal
    conf = -committee_std                                   # HIGHER conf = lower variance = keep first
    committee_stable = committee_mean < 0.0                 # consensus stable call

    ref_signmap, single_dom_sign = load_single_reference()

    results = {'meta': {
        'story': 'G007-s1-materials-mt29-committee-variance',
        'stage': 'M1/E1 committee-variance robustness of the matched-yield interaction',
        'seed': SEED, 'n_boot': N_BOOT, 'models_in_committee': MODELS, 'strata': fams,
        'abstention_signal': 'COMMITTEE VARIANCE: std across the 4 UIP reconstructed predicted '
                             'hulls; confidence = -std (low variance kept first).',
        'consensus_call': 'committee MEAN predicted hull < 0',
        'control': 'COMMON ABSOLUTE committee-called-stable yield Y across strata; '
                   'DAF(top Y_tight) - DAF(top Y_loose), Y identical across strata.',
        'budget_rule': 'Y_loose = min over strata of committee-called-stable; Y_tight = Y_loose//2.',
        'point_estimate_statistic': 'np.median of the within-stratum bootstrap distribution '
                                    '(same as single-model fix); NOT the bootstrap mean.',
        'single_model_reference': os.path.basename(SINGLE_JSON),
    }}

    # per-stratum committee-called-stable confidence/truth + base rate + budgets
    cs_conf = {}; cs_st = {}; br = {}; total_cs = {}
    for f in fams:
        idx = fam_idx[f]
        sp = committee_stable[idx]
        cs = np.where(sp)[0]
        cs_conf[f] = conf[idx][cs]
        cs_st[f] = true_stable[idx][cs]
        br[f] = float(true_stable[idx].mean())
        total_cs[f] = len(cs)
    y_loose = min(total_cs.values())
    y_tight = max(1, y_loose // 2)

    results['committee_budgets'] = {
        'y_loose': int(y_loose), 'y_tight': int(y_tight),
        'total_committee_called_stable': {f: int(total_cs[f]) for f in fams},
        'base_rate_stable': {f: round(br[f], 5) for f in fams},
        'daf_top_y_tight': {f: round(float(daf_top_y(cs_conf[f], cs_st[f], y_tight, br[f])), 5) for f in fams},
        'daf_top_y_loose': {f: round(float(daf_top_y(cs_conf[f], cs_st[f], y_loose, br[f])), 5) for f in fams},
    }

    gains = {f: boot_yield_gain(cs_conf[f], cs_st[f], br[f], y_tight, y_loose, False) for f in fams}
    gains_sh = {f: boot_yield_gain(cs_conf[f], cs_st[f], br[f], y_tight, y_loose, True) for f in fams}
    results['committee_gain_median'] = {f: round(float(np.median(gains[f])), 5) for f in fams}

    inter_real = []; inter_shuf = []; n_real = 0; n_shuf = 0
    for i in range(len(fams)):
        for j in range(i + 1, len(fams)):
            a, b = fams[i], fams[j]
            L = min(len(gains[a]), len(gains[b]))
            if L < 100:
                continue
            d = gains[a][:L] - gains[b][:L]
            ci = ci95(d); e = excl0(ci); n_real += int(e)
            inter_real.append(dict(stratumA=a, stratumB=b,
                                   gainA_med=round(float(np.median(gains[a])), 5),
                                   gainB_med=round(float(np.median(gains[b])), 5),
                                   interaction_med=round(float(np.median(d)), 5),
                                   interaction_ci95=[round(ci[0], 5), round(ci[1], 5)],
                                   excludes_0=e))
            Ls = min(len(gains_sh[a]), len(gains_sh[b]))
            if Ls >= 100:
                ds = gains_sh[a][:Ls] - gains_sh[b][:Ls]
                cis = ci95(ds); es = excl0(cis); n_shuf += int(es)
                inter_shuf.append(dict(stratumA=a, stratumB=b,
                                       interaction_med=round(float(np.median(ds)), 5),
                                       interaction_ci95=[round(cis[0], 5), round(cis[1], 5)],
                                       excludes_0=es))

    results['interactions_committee_variance'] = inter_real
    results['interactions_committee_variance_SHUFFLE'] = inter_shuf

    shuffle_clean = n_shuf <= max(1, int(0.05 * max(1, len(inter_shuf))))

    # -------- pre-registered two-branch gate (definitions frozen in M1_PREREG.md) --------
    # Branch A: robustness (committee reproduces the sign)
    sign_matches = 0; sign_eval = 0; per_pair = []
    for x in inter_real:
        p = (x['stratumA'], x['stratumB'])
        rr = ref_signmap.get(p, {})
        s_single = rr.get('S_single')
        sign_c = int(np.sign(x['interaction_med']))
        agree = None
        if x['excludes_0'] and s_single is not None:
            sign_eval += 1
            agree = (sign_c == s_single)
            sign_matches += int(agree)
        # Branch B per-pair: committee excl0 vs single-model consensus excl0
        b_diff = bool(x['excludes_0'] != rr.get('excl0_single_consensus', False))
        per_pair.append({**{k: x[k] for k in ('stratumA', 'stratumB', 'interaction_med',
                                              'interaction_ci95', 'excludes_0')},
                         'S_single': s_single, 'sign_committee': sign_c,
                         'sign_agrees': agree,
                         'single_consensus_excl0': rr.get('excl0_single_consensus', False),
                         'sign_or_sig_differs_from_single': b_diff})

    committee_dom_sign = int(np.sign(np.median([x['interaction_med'] for x in inter_real if x['excludes_0']]))) if n_real else 0
    branchA_pass = bool(n_real >= 1 and sign_eval >= 1 and sign_matches > sign_eval / 2.0)
    # Branch B: contrast — any pair where committee sig-decision differs from single consensus,
    # OR any committee-significant pair whose sign disagrees with the single-model reference sign.
    any_sig_diff = any(pp['sign_or_sig_differs_from_single'] for pp in per_pair)
    any_sign_disagree = any(pp['excludes_0'] and pp['sign_agrees'] is False for pp in per_pair)
    branchB_pass = bool(any_sig_diff or any_sign_disagree)

    results['gate'] = {
        'shuffle_null_clean': bool(shuffle_clean),
        'committee_excl0': f'{n_real}/{len(inter_real)}',
        'committee_SHUFFLE_excl0': f'{n_shuf}/{len(inter_shuf)}',
        'single_model_dominant_sign': single_dom_sign,
        'committee_dominant_sign': committee_dom_sign,
        'branchA_robustness': {
            'rule': '>=1 committee pair CI-excludes-0 AND committee sign matches single-model '
                    'reference sign for strict majority of jointly-defined pairs',
            'sign_agree_pairs': f'{sign_matches}/{sign_eval}',
            'committee_dominant_sign_matches_single': bool(committee_dom_sign == single_dom_sign),
            'PASS': branchA_pass,
        },
        'branchB_contrast': {
            'rule': '>=1 pair where committee sig-decision differs from single-model consensus, '
                    'OR >=1 committee-significant pair with sign disagreeing from single reference',
            'n_pairs_sig_or_sign_differ': int(sum(pp['sign_or_sig_differs_from_single'] for pp in per_pair)),
            'any_committee_significant_sign_disagreement': bool(any_sign_disagree),
            'PASS': branchB_pass,
        },
        'per_pair': per_pair,
    }
    results['summary'] = {
        'n_pairs': len(inter_real),
        'committee_excl0': f'{n_real}/{len(inter_real)}',
        'committee_SHUFFLE_excl0': f'{n_shuf}/{len(inter_shuf)}',
        'shuffle_null_clean': bool(shuffle_clean),
        'branchA_robustness_PASS': branchA_pass,
        'branchB_contrast_PASS': branchB_pass,
        'gate_verdict': ('PASS-BOTH' if (branchA_pass and branchB_pass and shuffle_clean)
                         else 'PASS-A-only' if (branchA_pass and shuffle_clean)
                         else 'PASS-B-only' if (branchB_pass and shuffle_clean)
                         else 'FAIL'),
    }

    print('=== MT29 M1/E1 committee-variance matched-yield interaction ===')
    print(f"  Y_tight={y_tight} Y_loose={y_loose}")
    print(f"  committee_gain_median={results['committee_gain_median']}")
    print(f"  committee interaction: {n_real}/{len(inter_real)} CI-exclude-0")
    print(f"  committee SHUFFLE-null: {n_shuf}/{len(inter_shuf)} (want ~0)  clean={shuffle_clean}")
    print(f"  single dom sign={single_dom_sign}  committee dom sign={committee_dom_sign}")
    print(f"  Branch A robustness sign-agree={sign_matches}/{sign_eval} PASS={branchA_pass}")
    print(f"  Branch B contrast PASS={branchB_pass}")
    print(f"  GATE VERDICT: {results['summary']['gate_verdict']}")
    print('  Top committee interactions:')
    for x in sorted([z for z in inter_real if z['excludes_0']], key=lambda z: -abs(z['interaction_med']))[:12]:
        print(f"    {x['stratumA']:13s} vs {x['stratumB']:13s}: int={x['interaction_med']:+.4f} CI{x['interaction_ci95']}")

    with open(OUT_JSON, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nWrote {OUT_JSON}")


if __name__ == '__main__':
    main()
