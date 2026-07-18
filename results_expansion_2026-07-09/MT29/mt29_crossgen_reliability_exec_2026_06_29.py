#!/usr/bin/env python
"""MT29 — Cross-GENERATIONAL reliability table on Matbench-Discovery WBM.

First measurement that puts BOTH MLIP generations on the SAME reliability axes:
  - 2020-era (Matbench Discovery v1 anchors): CGCNN (ens=10), CGCNN+P (perturb=5),
    MEGNet, ALIGNN-FF.
  - 2023-24 universal interatomic potentials: CHGNet, M3GNet, MACE, ORB.

FRAMING (preregistered direction, confirm-or-refute):
  This is a MEASUREMENT, not an advocacy of "newer models calibrate worse." V2 found
  Spearman(MAE, F1) = -0.929 across these 8 models -> stability-decision quality tracks
  regression accuracy outside the near-chance regime. The directional hypothesis
  "newer => worse-calibrated (higher ECE/Brier)" is therefore EXPECTED to be REFUTED.
  We report whichever way it lands. The defensible novelty is that ECE / Brier / NLL is a
  DISTINCT reliability axis (probabilistic calibration of the stability call) that has not
  been measured cross-generationally on this arena, alongside AURC (selective-risk ranking).

AXES (per model):
  (1) MAE_form  : mean |e_form_pred - e_form_true|  (regression accuracy; full merged set).
  (2) F1        : F1 of the binary stable call stable_pred=(hull_pred<0) vs
                  stable_true=(hull_true<0).  (full merged set).
  (3) AURC      : area under risk-coverage curve, confidence = |hull_pred| (margin),
                  selective risk = 1 - precision(stable calls among kept). Lower=better.
                  Evaluated on the held-out TEST half. Uniform protocol for all 8.
  (4) ECE/Brier/NLL : probabilistic calibration of the stability call. Probability built
                  with a ZERO-free-parameter native Gaussian error model:
                      p_stable = Phi( -hull_pred / sigma ),   sigma = RMSE of hull-pred error
                  where sigma (= the model's own global formation-energy error scale) is
                  estimated on the CALIBRATION half and metrics scored on the TEST half.
                  This is "the model trusts its own accuracy": no per-model classifier is
                  fit, so the axis is fully comparable and reproducible across all 8.
                  (Secondary, reported too: Platt-scaled p_stable refit on the cal half.)

hull_pred = hull_true + (e_form_pred - e_form_true)   (standard Matbench reconstruction;
  identical to mt28_riskcov.py / mt28_calibration_audit.py / mt_v2_modern_uip.py).
stable_true = e_above_hull_mp2020_corrected_ppd_mp < 0.

CIs: 1000-bootstrap percentile 95% on every TEST-half metric. Shuffle null (labels permuted
  vs probabilities) for ECE/Brier/NLL. CPU/pandas only. New output files (-exec-2026-06-29).
"""
import os, sys, json, glob, hashlib, platform, subprocess
import numpy as np
import pandas as pd
from scipy.stats import norm, spearmanr
from sklearn.metrics import f1_score, precision_score, recall_score
from sklearn.linear_model import LogisticRegression
import warnings
warnings.filterwarnings('ignore')

SEED = 20260629
RNG = np.random.default_rng(SEED)
N_BOOT = 1000
N_SHUFFLE = 200
ECE_BINS = 15

DATA = os.path.expanduser(os.environ.get('MT_DATA_ROOT', '~/mt_stage0/data'))
UIP  = os.path.expanduser(os.environ.get('MT_UIP_ROOT',  '~/mt_uip'))
E_FORM_TRUE = 'e_form_per_atom_mp2020_corrected'
E_HULL_TRUE = 'e_above_hull_mp2020_corrected_ppd_mp'

OUT_DIR  = '/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/research/results/MT29'
OUT_JSON = os.path.join(OUT_DIR, 'mt29_crossgen_reliability_result-exec-2026-06-29.json')
MANIFEST = os.path.join(OUT_DIR, 'mt29_crossgen_reliability_manifest-exec-2026-06-29.json')

COVERAGES = [0.5, 0.7, 0.9]

# (display_name, generation, loader_tag). Modern UIPs loaded from ~/mt_uip; 2020 from ~/mt_stage0.
MODERN = ['chgnet', 'm3gnet', 'mace', 'orb']                       # gen 2023-24
STAGE0 = [  # (name, glob, ensemble-prediction column)
    ('CGCNN',     '*cgcnn-ens*IS2RE*.csv.gz',     'e_form_per_atom_mp2020_corrected_pred_ens'),
    ('CGCNN+P',   '*cgcnn-perturb*IS2RE*.csv.gz', 'e_form_per_atom_cgcnn_pred_ens'),
    ('MEGNet',    '*megnet*IS2RE*.csv.gz',        'e_form_per_atom_megnet'),
    ('ALIGNN-FF', '*alignn-ff*IS2RE*.csv.gz',     'e_form_per_atom_alignn_ff'),
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def load_summary():
    f = glob.glob(os.path.join(DATA, '*wbm-summary*.csv.gz'))[0]
    df = pd.read_csv(f, usecols=lambda c: c in ('material_id', E_FORM_TRUE, E_HULL_TRUE))
    return df.dropna(subset=[E_FORM_TRUE, E_HULL_TRUE]), f


def model_frames(summ):
    """Yield (name, gen, merged_df with cols eft, hull_true, e_form_pred)."""
    for m in MODERN:
        p = pd.read_csv(os.path.join(UIP, f'{m}_pred.csv'))[['material_id', 'e_form_pred']].dropna()
        df = summ.merge(p, on='material_id', how='inner').rename(
            columns={E_FORM_TRUE: 'eft', E_HULL_TRUE: 'hull_true'})
        yield m, '2023-24', df.dropna().reset_index(drop=True)
    for name, glb, col in STAGE0:
        fs = glob.glob(os.path.join(DATA, glb))
        if not fs:
            continue
        raw = pd.read_csv(fs[0])
        if col not in raw.columns:
            raise RuntimeError(f'{name}: missing column {col}; have {list(raw.columns)[:5]}...')
        p = raw[['material_id', col]].rename(columns={col: 'e_form_pred'}).dropna()
        df = summ.merge(p, on='material_id', how='inner').rename(
            columns={E_FORM_TRUE: 'eft', E_HULL_TRUE: 'hull_true'})
        yield name, '2020', df.dropna().reset_index(drop=True)


# ----------------------------- metric primitives -----------------------------

def aurc_margin(margin, stable_pred, stable_true, grid=None):
    """Area under risk-coverage curve; confidence = margin (|hull_pred|). Identical
    definition to mt28_riskcov.py: risk = 1 - precision(stable calls among kept)."""
    if grid is None:
        grid = np.linspace(0.05, 1.0, 20)
    order = np.argsort(margin)[::-1]
    sp = stable_pred[order]; st = stable_true[order]
    n = len(sp)
    risks = []
    for c in grid:
        k = max(1, int(round(c * n)))
        s_sp = sp[:k]; s_st = st[:k]
        tp = (s_sp & s_st).sum(); fp = (s_sp & ~s_st).sum()
        denom = tp + fp
        risks.append(1.0 - (tp / denom) if denom > 0 else 0.0)
    _trap = getattr(np, 'trapezoid', getattr(np, 'trapz', None))
    return float(_trap(risks, grid) / (grid[-1] - grid[0]))


def ece(p, y, n_bins=ECE_BINS):
    """Expected calibration error, equal-width bins on [0,1]."""
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    n = len(p)
    e = 0.0
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        m = (p > lo) & (p <= hi) if i > 0 else (p >= lo) & (p <= hi)
        if m.sum() == 0:
            continue
        e += (m.sum() / n) * abs(y[m].mean() - p[m].mean())
    return float(e)


def brier(p, y):
    return float(np.mean((p - y) ** 2))


def nll(p, y, eps=1e-12):
    p = np.clip(p, eps, 1 - eps)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def boot_ci(metric_fn, n, *arrays):
    """1000-boot percentile 95% CI of metric_fn(*resampled arrays)."""
    vals = np.empty(N_BOOT)
    for b in range(N_BOOT):
        idx = RNG.integers(0, n, n)
        vals[b] = metric_fn(*[a[idx] for a in arrays])
    vals = vals[~np.isnan(vals)]
    return [round(float(np.percentile(vals, 2.5)), 5),
            round(float(np.percentile(vals, 97.5)), 5),
            round(float(np.mean(vals)), 5)]


# ----------------------------- per-model audit -----------------------------

def audit(name, gen, df):
    eft = df['eft'].values; hull_true = df['hull_true'].values
    e_pred = df['e_form_pred'].values
    err = e_pred - eft                       # formation-energy error (= hull_pred error)
    hull_pred = hull_true + err
    stable_true = (hull_true < 0)
    stable_pred = (hull_pred < 0)
    n = len(df)

    # --- accuracy axes on full set (matches V2) ---
    mae = float(np.mean(np.abs(err)))
    yt_full = stable_true.astype(int); yp_full = stable_pred.astype(int)
    f1_full = float(f1_score(yt_full, yp_full, zero_division=0))
    prec_full = float(precision_score(yt_full, yp_full, zero_division=0))
    rec_full = float(recall_score(yt_full, yp_full, zero_division=0))

    # --- 50/50 split: fit sigma / Platt on cal, score on test ---
    half = n // 2
    perm = RNG.permutation(n)
    cal, test = perm[:half], perm[half:]
    sigma = float(np.sqrt(np.mean(err[cal] ** 2)))   # RMSE of hull-pred error on cal half

    # native Gaussian error-model probability of stability (zero free params besides sigma)
    p_native = norm.cdf(-hull_pred / sigma)

    # secondary: Platt-scaled logistic on -hull_pred fit on cal
    lr = LogisticRegression()
    lr.fit((-hull_pred[cal]).reshape(-1, 1), stable_true[cal].astype(int))
    p_platt = lr.predict_proba((-hull_pred).reshape(-1, 1))[:, 1]

    # restrict to test half
    spt = stable_pred[test]; stt = stable_true[test]
    yt = stt.astype(int)
    margin_t = np.abs(hull_pred[test])
    pn_t = p_native[test]; pp_t = p_platt[test]
    nt = len(test)
    base_rate = float(stt.mean())

    res = {
        'model': name, 'gen': gen, 'n_full': n, 'n_test': nt,
        'base_rate_stable': round(base_rate, 5), 'sigma_rmse_cal': round(sigma, 5),
        'MAE_form': round(mae, 5), 'F1': round(f1_full, 5),
        'precision': round(prec_full, 5), 'recall': round(rec_full, 5),
    }

    # AURC (margin) on test + CI
    a = aurc_margin(margin_t, spt, stt)
    res['AURC_margin'] = round(a, 5)
    res['AURC_margin_ci95'] = boot_ci(lambda mg, sp, st: aurc_margin(mg, sp, st),
                                      nt, margin_t, spt, stt)[:2]

    # calibration metrics (native + platt) on test + CI
    for tag, p in (('native', pn_t), ('platt', pp_t)):
        e_v = ece(p, yt); b_v = brier(p, yt); n_v = nll(p, yt)
        res[f'ECE_{tag}'] = round(e_v, 5)
        res[f'ECE_{tag}_ci95'] = boot_ci(lambda pp, yy: ece(pp, yy), nt, p, yt)[:2]
        res[f'Brier_{tag}'] = round(b_v, 5)
        res[f'Brier_{tag}_ci95'] = boot_ci(lambda pp, yy: brier(pp, yy), nt, p, yt)[:2]
        res[f'NLL_{tag}'] = round(n_v, 5)
        res[f'NLL_{tag}_ci95'] = boot_ci(lambda pp, yy: nll(pp, yy), nt, p, yt)[:2]

    # shuffle null on the PRIMARY (native) probability: permute labels vs p
    null_ece, null_brier, null_nll = [], [], []
    for _ in range(N_SHUFFLE):
        ys = yt[RNG.permutation(nt)]
        null_ece.append(ece(pn_t, ys)); null_brier.append(brier(pn_t, ys)); null_nll.append(nll(pn_t, ys))
    res['shuffle_null_native'] = {
        'ECE_mean': round(float(np.mean(null_ece)), 5),
        'ECE_p95': round(float(np.percentile(null_ece, 95)), 5),
        'Brier_mean': round(float(np.mean(null_brier)), 5),
        'NLL_mean': round(float(np.mean(null_nll)), 5),
        'ECE_native_below_null_p05': bool(res['ECE_native'] < np.percentile(null_ece, 5)),
        'Brier_native_below_null_p05': bool(res['Brier_native'] < np.percentile(null_brier, 5)),
    }
    return res


def main():
    summ, summ_path = load_summary()
    print(f'WBM summary rows {len(summ)}  stable {int((summ[E_HULL_TRUE] < 0).sum())}', flush=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    rows = []
    for name, gen, df in model_frames(summ):
        if len(df) < 5000:
            print(f'  SKIP {name}: only {len(df)} rows', flush=True)
            continue
        r = audit(name, gen, df)
        rows.append(r)
        print(f"  {r['model']:10s} [{r['gen']}] n={r['n_full']} MAE={r['MAE_form']:.4f} F1={r['F1']:.4f} "
              f"AURC={r['AURC_margin']:.4f} ECE_nat={r['ECE_native']:.4f} Brier_nat={r['Brier_native']:.4f} "
              f"NLL_nat={r['NLL_native']:.4f} (null Brier {r['shuffle_null_native']['Brier_mean']:.4f})", flush=True)

    # ---- cross-generational correlations (the measurement) ----
    def col(k):
        return np.array([r[k] for r in rows], float)
    mae = col('MAE_form'); f1 = col('F1')
    aurc = col('AURC_margin'); ece_n = col('ECE_native'); brier_n = col('Brier_native'); nll_n = col('NLL_native')

    def sp(a, b):
        c = spearmanr(a, b)
        return [round(float(c.correlation), 4), round(float(c.pvalue), 5)]

    corr = {
        'spearman_MAE_vs_ECEnative': sp(mae, ece_n),
        'spearman_MAE_vs_Briernative': sp(mae, brier_n),
        'spearman_MAE_vs_NLLnative': sp(mae, nll_n),
        'spearman_MAE_vs_AURC': sp(mae, aurc),
        'spearman_F1_vs_ECEnative': sp(f1, ece_n),
        'spearman_F1_vs_Briernative': sp(f1, brier_n),
        'spearman_F1_vs_AURC': sp(f1, aurc),
        'note': 'positive MAE-vs-ECE/Brier => less accurate models are less reliable '
                '(reliability tracks accuracy). negative F1-vs-Brier => same direction.',
    }

    # ---- directional hypothesis: "newer (2023-24) calibrate WORSE" ----
    g2020 = [r for r in rows if r['gen'] == '2020']
    g2324 = [r for r in rows if r['gen'] == '2023-24']
    def mean(group, k):
        return round(float(np.mean([r[k] for r in group])), 5)
    hyp = {
        'hypothesis': 'newer 2023-24 UIPs have HIGHER ECE/Brier (worse calibration) than 2020-era models',
        'mean_ECEnative_2020': mean(g2020, 'ECE_native'), 'mean_ECEnative_2023_24': mean(g2324, 'ECE_native'),
        'mean_Briernative_2020': mean(g2020, 'Brier_native'), 'mean_Briernative_2023_24': mean(g2324, 'Brier_native'),
        'mean_NLLnative_2020': mean(g2020, 'NLL_native'), 'mean_NLLnative_2023_24': mean(g2324, 'NLL_native'),
        'mean_AURC_2020': mean(g2020, 'AURC_margin'), 'mean_AURC_2023_24': mean(g2324, 'AURC_margin'),
        'mean_MAE_2020': mean(g2020, 'MAE_form'), 'mean_MAE_2023_24': mean(g2324, 'MAE_form'),
    }
    # verdict per Brier (primary scoring rule): is newer worse?
    newer_worse_brier = hyp['mean_Briernative_2023_24'] > hyp['mean_Briernative_2020']
    newer_worse_ece = hyp['mean_ECEnative_2023_24'] > hyp['mean_ECEnative_2020']
    hyp['newer_worse_by_Brier'] = bool(newer_worse_brier)
    hyp['newer_worse_by_ECE'] = bool(newer_worse_ece)
    hyp['directional_verdict'] = (
        'CONFIRMED (newer worse)' if (newer_worse_brier and newer_worse_ece)
        else 'REFUTED (newer better or equal)' if (not newer_worse_brier and not newer_worse_ece)
        else 'MIXED (Brier and ECE disagree)')

    out = {
        'experiment': 'MT29_cross_generational_reliability',
        'date': '2026-06-29',
        'meta': {'seed': SEED, 'n_boot': N_BOOT, 'n_shuffle': N_SHUFFLE, 'ece_bins': ECE_BINS,
                 'stable_definition': 'e_above_hull_mp2020_corrected_ppd_mp < 0',
                 'hull_reconstruction': 'hull_true + (e_form_pred - e_form_true)',
                 'probability_model_primary': 'native Gaussian: p_stable=Phi(-hull_pred/sigma), '
                 'sigma=RMSE(err) on cal half, scored on test half',
                 'probability_model_secondary': 'Platt logistic on -hull_pred, fit cal half',
                 'coverages': COVERAGES},
        'models': rows,
        'cross_gen_correlations': corr,
        'directional_hypothesis': hyp,
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2, default=str)
    print(f'\nWrote {OUT_JSON}', flush=True)
    print('CORRS', json.dumps(corr, indent=2), flush=True)
    print('HYP', json.dumps(hyp, indent=2), flush=True)

    # manifest
    try:
        git_sha = subprocess.check_output(
            ['git', '-C', '/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research', 'rev-parse', 'HEAD'],
            text=True).strip()
    except Exception:
        git_sha = None
    import sklearn, scipy
    inputs = {os.path.basename(summ_path): sha256(summ_path)}
    for m in MODERN:
        inputs[f'{m}_pred.csv'] = sha256(os.path.join(UIP, f'{m}_pred.csv'))
    for name, glb, col_ in STAGE0:
        fs = glob.glob(os.path.join(DATA, glb))
        if fs:
            inputs[os.path.basename(fs[0])] = sha256(fs[0])
    manifest = {
        'cmd': ' '.join([sys.executable] + sys.argv),
        'script_sha256': sha256(os.path.abspath(__file__)),
        'git_head': git_sha, 'seed': SEED, 'n_boot': N_BOOT,
        'inputs': inputs, 'output_sha256': sha256(OUT_JSON),
        'versions': {'python': platform.python_version(), 'numpy': np.__version__,
                     'pandas': pd.__version__, 'sklearn': sklearn.__version__,
                     'scipy': scipy.__version__},
        'platform': platform.platform(),
    }
    with open(MANIFEST, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f'Wrote {MANIFEST}', flush=True)


if __name__ == '__main__':
    main()
