#!/usr/bin/env python
"""MT28 — Hull-boundary stability-decision calibration audit.

This script implements:
1. Loading the WBM summary and model predictions (MACE, CHGNet, M3GNet, ORB).
2. Setting up a calibration split and a test split (50/50).
3. Fitting calibrators (Logistic Regression, Isotonic Regression) mapping predicted hull distance to true stability.
4. Evaluating selective prediction (abstention) at 70% and 90% coverage:
   - Calibration confidence: max(p_stable, 1 - p_stable)
   - Margin baseline: |hull_pred|
5. Computing the precision of stable calls for both methods.
6. Running 500 bootstrap resamples to compute the 95% CI of the precision gain (Calibrated - Margin).
7. Outputting the results to a JSON file and a markdown findings file.
"""
import os
import json
import glob
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import precision_score
import warnings

warnings.filterwarnings('ignore')
RNG = np.random.default_rng(20260616)

DATA = os.path.expanduser('~/mt_stage0/data')
UIP = os.path.expanduser('~/mt_uip')
E_FORM_TRUE = 'e_form_per_atom_mp2020_corrected'
E_HULL_TRUE = 'e_above_hull_mp2020_corrected_ppd_mp'
OUT_JSON = '/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/research/results/MT28/mt28_calibration_result.json'
OUT_MD = '/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/research/findings-MT28-calibration-audit.md'

def load_summary():
    f = glob.glob(os.path.join(DATA, '*wbm-summary*.csv.gz'))[0]
    df = pd.read_csv(f, usecols=lambda c: c in ('material_id', E_FORM_TRUE, E_HULL_TRUE))
    return df.dropna(subset=[E_FORM_TRUE, E_HULL_TRUE])

def model_preds():
    for f in sorted(glob.glob(os.path.join(UIP, '*_pred.csv'))):
        name = os.path.basename(f).replace('_pred.csv', '')
        df = pd.read_csv(f)
        yield name, df[['material_id', 'e_form_pred']].dropna()

def evaluate_abstention(score, stable_pred, stable_true, cov):
    n = len(score)
    k = max(1, int(cov * n))
    idx = np.argsort(score)[::-1][:k] # Highest score first
    sp = stable_pred[idx]
    st = stable_true[idx]
    tp = (sp & st).sum()
    fp = (sp & ~st).sum()
    return tp / (tp + fp) if (tp + fp) > 0 else 0.0

def run_audit(name, m):
    # Predicted hull distance
    m['hull_pred'] = m[E_HULL_TRUE] + (m['e_form_pred'] - m[E_FORM_TRUE])
    
    X_hull = m['hull_pred'].values
    y_true = (m[E_HULL_TRUE].values < 0).astype(int)
    y_pred = (X_hull < 0).astype(int)
    
    n = len(m)
    half = n // 2
    
    # Shuffle indices for train/test split
    indices = np.arange(n)
    RNG.shuffle(indices)
    cal_idx, test_idx = indices[:half], indices[half:]
    
    X_cal, y_cal = X_hull[cal_idx], y_true[cal_idx]
    X_test, y_test = X_hull[test_idx], y_true[test_idx]
    y_pred_test = y_pred[test_idx]
    
    # 1. Fit Calibrators on Calibration split
    # Isotonic Regression mapping predicted hull to probability of being stable
    # Note: predicted hull < 0 means stable, so higher predicted hull means LESS stable.
    # Isotonic regression expects x and y to have monotonic relationship.
    # Since higher hull_pred -> lower p_stable, we fit on -hull_pred
    iso = IsotonicRegression(out_of_bounds='clip')
    iso.fit(-X_cal, y_cal)
    
    # Logistic Regression as fallback/comparison
    log_reg = LogisticRegression()
    log_reg.fit(X_cal.reshape(-1, 1), y_cal)
    
    # 2. Predict probabilities on Test split
    p_iso = iso.predict(-X_test)
    p_log = log_reg.predict_proba(X_test.reshape(-1, 1))[:, 1]
    
    # Calibrated confidence scores
    conf_iso = np.maximum(p_iso, 1 - p_iso)
    conf_log = np.maximum(p_log, 1 - p_log)
    
    # Margin baseline on test split: absolute predicted hull margin (higher means more certain)
    margin_score = np.abs(X_test)
    
    results = {}
    
    for cov in [0.7, 0.9]:
        prec_margin = evaluate_abstention(margin_score, y_pred_test, y_test, cov)
        prec_iso = evaluate_abstention(conf_iso, y_pred_test, y_test, cov)
        prec_log = evaluate_abstention(conf_log, y_pred_test, y_test, cov)
        
        # Bootstrap CI for gain (Iso - Margin) and (Log - Margin)
        iso_gains = []
        log_gains = []
        n_test = len(y_test)
        
        for _ in range(500):
            boot_idx = RNG.integers(0, n_test, n_test)
            bm = margin_score[boot_idx]
            bi = conf_iso[boot_idx]
            bl = conf_log[boot_idx]
            byp = y_pred_test[boot_idx]
            byt = y_test[boot_idx]
            
            bp_margin = evaluate_abstention(bm, byp, byt, cov)
            bp_iso = evaluate_abstention(bi, byp, byt, cov)
            bp_log = evaluate_abstention(bl, byp, byt, cov)
            
            iso_gains.append(bp_iso - bp_margin)
            log_gains.append(bp_log - bp_margin)
            
        results[f'cov_{int(cov*100)}'] = {
            'margin_precision': round(prec_margin, 5),
            'iso_precision': round(prec_iso, 5),
            'log_precision': round(prec_log, 5),
            'iso_gain': round(prec_iso - prec_margin, 5),
            'iso_gain_ci95': [round(float(np.percentile(iso_gains, 2.5)), 5), round(float(np.percentile(iso_gains, 97.5)), 5)],
            'log_gain': round(prec_log - prec_margin, 5),
            'log_gain_ci95': [round(float(np.percentile(log_gains, 2.5)), 5), round(float(np.percentile(log_gains, 97.5)), 5)]
        }
        
    return results

def main():
    summ = load_summary()
    print(f"Loaded summary: {len(summ)} rows", flush=True)
    
    results = {}
    for name, dfp in model_preds():
        m = summ.merge(dfp, on='material_id', how='inner').dropna(subset=['e_form_pred'])
        if len(m) < 5000:
            continue
        print(f"Auditing model: {name} ({len(m)} rows)", flush=True)
        results[name] = run_audit(name, m)
        
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Results written to {OUT_JSON}", flush=True)
    
    # Write Markdown findings file
    lines = [
        f"# MT28 — Hull-boundary decision calibration audit findings",
        f"",
        f"Date: 2026-06-16",
        f"",
        f"This audit evaluates whether post-hoc calibrated confidence (Logistic/Isotonic Regression) mapping predicted hull distance to true stability improves stability-decision precision at 70% and 90% coverage relative to the raw absolute predicted hull-margin (`|hull_pred|`) baseline.",
        f"",
        f"## Quantitative Table (Coverage 70% and 90%)",
        f"",
        f"| Model | Coverage | Margin Precision | Isotonic Precision | Iso Gain [95% CI] | Log Precision | Log Gain [95% CI] | Cal Beats Margin? |",
        f"| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]
    
    for name, res in results.items():
        for cov in ['cov_70', 'cov_90']:
            cdata = res[cov]
            c_pct = cov.split('_')[1] + '%'
            iso_ci = f"{cdata['iso_gain']:.5f} [{cdata['iso_gain_ci95'][0]:.5f}, {cdata['iso_gain_ci95'][1]:.5f}]"
            log_ci = f"{cdata['log_gain']:.5f} [{cdata['log_gain_ci95'][0]:.5f}, {cdata['log_gain_ci95'][1]:.5f}]"
            beats = "YES" if cdata['iso_gain'] > 0 and cdata['iso_gain_ci95'][0] > 0 else "NO"
            lines.append(f"| {name} | {c_pct} | {cdata['margin_precision']:.5f} | {cdata['iso_precision']:.5f} | {iso_ci} | {cdata['log_precision']:.5f} | {log_ci} | {beats} |")
            
    lines.extend([
        f"",
        f"## Adjudication & Implications",
        f"- **Trivial Margin Baseline Dominance**: If the Isotonic Gain CI includes 0 or is negative, it confirms that raw `|hull_pred|` is already the optimal decision variable for selective stability-prediction (abstention), and post-hoc calibration does not improve upon it near the hull boundary.",
        f"- **Kill Threshold**: If the gain CI includes 0 for all models, the calibration story is falsified, confirming that absolute hull distance is a sufficient uncertainty signal."
    ])
    
    with open(OUT_MD, 'w') as f:
        f.write("\n".join(lines) + "\n")
    print(f"Findings written to {OUT_MD}", flush=True)

if __name__ == '__main__':
    main()
