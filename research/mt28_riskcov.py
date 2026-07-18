#!/usr/bin/env python
"""MT28 Stage-0 GATE — Risk-coverage selective prediction on the WBM stability decision.

Canonical Stage-0 go/no-go for the materials-mlip risk-coverage reshape (G003-t1-materials).

Question (preregistered, DEEP-REVERIFY-2026-06-21 §5/§6 direction 1):
  Does ANY non-trivial confidence signal beat the trivial `|predicted hull margin|` baseline
  at MATCHED coverage AND MATCHED stable-call yield, with a 1000-bootstrap 95% CI on the
  gain-vs-margin that excludes 0?

Binary decision: a structure is STABLE iff e_above_hull < 0 (ground-truth hull
  = e_above_hull_mp2020_corrected_ppd_mp). The model's stable CALL is hull_pred < 0,
  where hull_pred = hull_true + (e_form_pred - e_form_true)  (standard Matbench
  reconstruction; identical to mt28_calibration_audit.py and v6_disagreement_reliability.py).

Confidence signals (higher = more confident => abstain on lowest):
  (a) MARGIN  (baseline, MANDATORY): |hull_pred|.
  (b) ISO     : split-isotonic-calibrated p_stable confidence  max(p, 1-p),
                fit on a held-out calibration half (no leakage into the scored half).
  (c) DISAGREE: cross-MLIP disagreement (negated std of e_form_pred across the 4 modern
                UIPs). Only defined for the 4-UIP ensemble, so reported as an ensemble row.

Primary metric: AURC of the binary stable call (selective risk = 1 - precision of stable
  calls among kept structures, integrated over coverage). Lower AURC is better.

Two controls for the headline gain (both demanded by §3 P1):
  - MATCHED COVERAGE: precision of stable calls at coverage in {0.5,0.7,0.9} keeping the
    top-confidence fraction by each signal.
  - MATCHED STABLE-CALL YIELD: the signals call different numbers of structures "stable" at
    the same coverage (yield-collapse confound). We therefore ALSO compare each non-trivial
    signal against margin at the SAME number of called-stable structures: rank called-stable
    structures by confidence, keep the top-Y by yield, report precision/DAF of that fixed-Y set.

CI: 1000-bootstrap percentile 95% CI on the *difference vs margin* (AURC gain, matched-cov
  precision gain, matched-yield precision gain). Shuffle-permutation null on each signal.

DAF (discovery acceleration factor) = precision(kept stable calls) / base_rate(stable).

CPU/pandas only. No GPU, no downloads. Reproducibility manifest written alongside results.
"""
import os, sys, json, glob, hashlib, platform, subprocess
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
import warnings
warnings.filterwarnings('ignore')

SEED = 20260621
RNG = np.random.default_rng(SEED)
N_BOOT = 1000

DATA = os.path.expanduser(os.environ.get('MT_DATA_ROOT', '~/mt_stage0/data'))
UIP  = os.path.expanduser(os.environ.get('MT_UIP_ROOT',  '~/mt_uip'))
E_FORM_TRUE = 'e_form_per_atom_mp2020_corrected'
E_HULL_TRUE = 'e_above_hull_mp2020_corrected_ppd_mp'
MODELS = ['chgnet', 'm3gnet', 'mace', 'orb']

OUT_DIR  = '/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/research/results/MT28'
OUT_JSON = os.path.join(OUT_DIR, 'mt28_riskcov_result.json')
MANIFEST = os.path.join(OUT_DIR, 'mt28_riskcov_manifest.json')
COVERAGES = [0.5, 0.7, 0.9]


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def load():
    """Merge ground-truth hull + e_form_true with the 4 modern UIP e_form predictions."""
    s = glob.glob(os.path.join(DATA, '*wbm-summary*.csv.gz'))[0]
    summ = pd.read_csv(s, usecols=lambda c: c in ('material_id', E_FORM_TRUE, E_HULL_TRUE))
    df = summ.dropna(subset=[E_FORM_TRUE, E_HULL_TRUE]).rename(
        columns={E_FORM_TRUE: 'eft', E_HULL_TRUE: 'hull_true'})
    for m in MODELS:
        p = pd.read_csv(os.path.join(UIP, f'{m}_pred.csv'))[['material_id', 'e_form_pred']]
        df = df.merge(p.rename(columns={'e_form_pred': m}), on='material_id', how='inner')
    return df.dropna().reset_index(drop=True), s


# ----------------------------- core selective-prediction metrics -----------------------------

def precision_at_coverage(conf, stable_pred, stable_true, cov):
    """Keep the top-`cov` fraction by confidence (abstain on the lowest). Among the KEPT
    structures, precision of the stable CALLS (TP / (TP+FP)). Returns (precision, n_called_stable)."""
    n = len(conf)
    k = max(1, int(round(cov * n)))
    keep = np.argsort(conf)[::-1][:k]           # highest confidence first
    sp = stable_pred[keep]; st = stable_true[keep]
    tp = int((sp & st).sum()); fp = int((sp & ~st).sum())
    prec = tp / (tp + fp) if (tp + fp) > 0 else np.nan
    return prec, int(sp.sum())


def aurc(conf, stable_pred, stable_true, grid=None):
    """Area under the risk-coverage curve for the stable call. Risk = 1 - precision(stable calls)
    among kept structures; coverage swept by keeping top-confidence fraction. Trapezoid over grid.
    Coverage points with zero stable calls contribute risk=0 (no decision => no error)."""
    if grid is None:
        grid = np.linspace(0.05, 1.0, 20)
    order = np.argsort(conf)[::-1]
    sp = stable_pred[order]; st = stable_true[order]
    n = len(sp)
    risks = []
    for c in grid:
        k = max(1, int(round(c * n)))
        s_sp = sp[:k]; s_st = st[:k]
        tp = (s_sp & s_st).sum(); fp = (s_sp & ~s_st).sum()
        denom = tp + fp
        risk = 1.0 - (tp / denom) if denom > 0 else 0.0
        risks.append(risk)
    return float(np.trapz(risks, grid) / (grid[-1] - grid[0]))


def precision_at_matched_yield(conf, stable_pred, stable_true, target_yield):
    """Rank the CALLED-STABLE structures by confidence; keep the top `target_yield` of them.
    Precision among that fixed-yield set. Controls the yield-collapse confound: both signals
    are compared at the SAME number of stable candidates surfaced."""
    sp_idx = np.where(stable_pred)[0]
    if len(sp_idx) == 0 or target_yield <= 0:
        return np.nan
    y = min(int(target_yield), len(sp_idx))
    order = sp_idx[np.argsort(conf[sp_idx])[::-1][:y]]
    st = stable_true[order]
    return float(st.sum() / y)


def boot_ci(fn, n, n_boot=N_BOOT):
    """Percentile 95% CI over bootstrap resamples; fn(idx)->scalar gain."""
    vals = np.empty(n_boot)
    for b in range(n_boot):
        idx = RNG.integers(0, n, n)
        vals[b] = fn(idx)
    vals = vals[~np.isnan(vals)]
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)),
            float(np.mean(vals))]


# ----------------------------- per-model audit -----------------------------

def build_signals(df, model, use_disagree):
    """Return dict of confidence arrays + the stable call / truth for one model."""
    eft = df['eft'].values; hull_true = df['hull_true'].values
    e_pred = df[model].values
    hull_pred = hull_true + (e_pred - eft)
    stable_true = hull_true < 0
    stable_pred = hull_pred < 0

    n = len(df)
    half = n // 2
    perm = RNG.permutation(n)
    cal, test = perm[:half], perm[half:]      # isotonic fit on `cal`, never on `test`
    # Build full-length signal arrays, but ISO/test-restricted metrics evaluated on `test`.
    margin = np.abs(hull_pred)

    iso = IsotonicRegression(out_of_bounds='clip')
    iso.fit(-hull_pred[cal], stable_true[cal].astype(int))     # higher -hull => more stable
    p_iso = iso.predict(-hull_pred)
    conf_iso = np.maximum(p_iso, 1 - p_iso)

    sig = {'margin': margin, 'iso': conf_iso}
    if use_disagree:
        disagree_std = df[MODELS].values.std(axis=1)
        sig['disagree'] = -disagree_std                          # high std => low confidence
    return sig, stable_pred, stable_true, test


def audit_model(df, model, use_disagree=False):
    sig, stable_pred, stable_true, test = build_signals(df, model, use_disagree)
    # Evaluate everything on the held-out `test` half so ISO is leakage-free and the
    # comparison is apples-to-apples across signals.
    sp = stable_pred[test]; st = stable_true[test]
    sigs = {k: v[test] for k, v in sig.items()}
    nt = len(test)
    base_rate = float(st.mean())

    res = {'n_test': nt, 'base_rate_stable': round(base_rate, 5), 'signals': {}}

    # AURC per signal + bootstrap gain vs margin
    aurc_margin = aurc(sigs['margin'], sp, st)
    for name, conf in sigs.items():
        a = aurc(conf, sp, st)
        entry = {'aurc': round(a, 5)}
        if name != 'margin':
            # AURC gain = margin_aurc - signal_aurc  (positive => signal better, lower risk)
            def gfn(idx, c=conf):
                return aurc(sigs['margin'][idx], sp[idx], st[idx]) - aurc(c[idx], sp[idx], st[idx])
            lo, hi, mean = boot_ci(gfn, nt)
            entry['aurc_gain_vs_margin'] = round(aurc_margin - a, 5)
            entry['aurc_gain_ci95'] = [round(lo, 5), round(hi, 5)]
            entry['aurc_gain_excludes_0'] = bool(lo > 0)
        res['signals'][name] = entry

    # Matched-coverage precision + matched-yield precision, per coverage
    res['by_coverage'] = {}
    for cov in COVERAGES:
        prec_m, yield_m = precision_at_coverage(sigs['margin'], sp, st, cov)
        cov_entry = {'margin': {'precision': round(prec_m, 5),
                                'n_called_stable': yield_m,
                                'daf': round(prec_m / base_rate, 4) if base_rate > 0 else np.nan}}
        for name, conf in sigs.items():
            if name == 'margin':
                continue
            prec_s, yield_s = precision_at_coverage(conf, sp, st, cov)
            # matched COVERAGE gain
            def gcov(idx, c=conf, cv=cov):
                pm, _ = precision_at_coverage(sigs['margin'][idx], sp[idx], st[idx], cv)
                ps, _ = precision_at_coverage(c[idx], sp[idx], st[idx], cv)
                return ps - pm
            lo_c, hi_c, _ = boot_ci(gcov, nt)
            # matched YIELD: hold both to margin's called-stable count at this coverage
            prec_my = precision_at_matched_yield(conf, sp, st, yield_m)
            prec_m_my = precision_at_matched_yield(sigs['margin'], sp, st, yield_m)
            def gyield(idx, c=conf, ty=yield_m):
                pm = precision_at_matched_yield(sigs['margin'][idx], sp[idx], st[idx], ty)
                ps = precision_at_matched_yield(c[idx], sp[idx], st[idx], ty)
                if np.isnan(pm) or np.isnan(ps):
                    return np.nan
                return ps - pm
            lo_y, hi_y, _ = boot_ci(gyield, nt)
            cov_entry[name] = {
                'precision': round(prec_s, 5), 'n_called_stable': yield_s,
                'daf': round(prec_s / base_rate, 4) if base_rate > 0 else np.nan,
                'matched_cov_gain': round(prec_s - prec_m, 5),
                'matched_cov_gain_ci95': [round(lo_c, 5), round(hi_c, 5)],
                'matched_cov_excludes_0': bool(lo_c > 0),
                'matched_yield_target': yield_m,
                'matched_yield_precision_signal': round(prec_my, 5) if not np.isnan(prec_my) else None,
                'matched_yield_precision_margin': round(prec_m_my, 5) if not np.isnan(prec_m_my) else None,
                'matched_yield_gain': round(prec_my - prec_m_my, 5) if not (np.isnan(prec_my) or np.isnan(prec_m_my)) else None,
                'matched_yield_gain_ci95': [round(lo_y, 5), round(hi_y, 5)],
                'matched_yield_excludes_0': bool(lo_y > 0),
            }
        res['by_coverage'][f'cov_{int(cov*100)}'] = cov_entry

    # Shuffle null: permuted margin should give AURC ~ no-skill; report at cov 0.7
    shuf = sigs['margin'].copy(); RNG.shuffle(shuf)
    prec_shuf, _ = precision_at_coverage(shuf, sp, st, 0.7)
    res['shuffle_margin_precision_cov70'] = round(prec_shuf, 5)
    return res


def main():
    df, summ_path = load()
    print(f"Loaded merged frame: {len(df)} rows, {len(MODELS)} UIPs", flush=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    results = {'meta': {'n_merged': len(df), 'seed': SEED, 'n_boot': N_BOOT,
                        'stable_definition': 'e_above_hull < 0',
                        'models': MODELS, 'coverages': COVERAGES}}
    for m in MODELS:
        # disagree signal is the 4-UIP cross-model std => attach it to every model row
        # (the called-stable set is per-model, but the disagreement signal is shared).
        results[m] = audit_model(df, m, use_disagree=True)
        s = results[m]['signals']
        line = f"  {m}: AURC margin={s['margin']['aurc']:.4f}"
        for k in ('iso', 'disagree'):
            if k in s:
                line += f" | {k} gain={s[k]['aurc_gain_vs_margin']:+.4f} CI{s[k]['aurc_gain_ci95']} excl0={s[k]['aurc_gain_excludes_0']}"
        print(line, flush=True)

    # ------- GATE verdict -------
    # PASS if >=1 model shows a non-trivial signal beating margin at matched coverage+yield
    # with CI excluding 0 (primary: matched-yield precision gain; also report AURC gain).
    passing = []
    for m in MODELS:
        for cov, ce in results[m]['by_coverage'].items():
            for sig in ('iso', 'disagree'):
                if sig in ce:
                    e = ce[sig]
                    # require BOTH matched-coverage and matched-yield CI to exclude 0 (strict)
                    if e['matched_cov_excludes_0'] and e['matched_yield_excludes_0'] and \
                       e['matched_cov_gain'] > 0 and (e['matched_yield_gain'] or 0) > 0:
                        passing.append({'model': m, 'coverage': cov, 'signal': sig,
                                        'matched_cov_gain': e['matched_cov_gain'],
                                        'matched_cov_ci': e['matched_cov_gain_ci95'],
                                        'matched_yield_gain': e['matched_yield_gain'],
                                        'matched_yield_ci': e['matched_yield_gain_ci95']})
    verdict = 'PASS' if passing else 'KILL'
    results['gate'] = {
        'verdict': verdict,
        'rule': 'PASS iff >=1 (model,coverage,signal) beats |hull margin| at BOTH matched '
                'coverage AND matched stable-call yield with 1000-boot 95% CI excluding 0.',
        'n_passing_cells': len(passing),
        'passing_cells': passing,
    }
    print(f"\nGATE VERDICT: {verdict} ({len(passing)} passing cells)", flush=True)

    with open(OUT_JSON, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Wrote {OUT_JSON}", flush=True)

    # ------- reproducibility manifest -------
    try:
        git_sha = subprocess.check_output(
            ['git', '-C', '/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research', 'rev-parse', 'HEAD'],
            text=True).strip()
    except Exception:
        git_sha = None
    import sklearn, scipy
    manifest = {
        'cmd': ' '.join([sys.executable] + sys.argv),
        'script_sha256': sha256(os.path.abspath(__file__)),
        'git_head': git_sha,
        'seed': SEED, 'n_boot': N_BOOT,
        'inputs': {os.path.basename(summ_path): sha256(summ_path),
                   **{f'{m}_pred.csv': sha256(os.path.join(UIP, f'{m}_pred.csv')) for m in MODELS}},
        'output_sha256': sha256(OUT_JSON),
        'versions': {'python': platform.python_version(), 'numpy': np.__version__,
                     'pandas': pd.__version__, 'sklearn': sklearn.__version__,
                     'scipy': scipy.__version__},
        'platform': platform.platform(),
    }
    with open(MANIFEST, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote {MANIFEST}", flush=True)


if __name__ == '__main__':
    main()
