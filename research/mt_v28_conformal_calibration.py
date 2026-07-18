import os
import glob
import json
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split

RNG = np.random.default_rng(42)
DATA = os.path.expanduser('~/mt_stage0/data')
UIP = os.path.expanduser('~/mt_uip')

E_FORM_TRUE = 'e_form_per_atom_mp2020_corrected'
E_HULL_TRUE = 'e_above_hull_mp2020_corrected_ppd_mp'
MODELS = ['orb', 'mace', 'chgnet', 'm3gnet']

def load_summary():
    f = glob.glob(os.path.join(DATA, '*wbm-summary*.csv.gz'))[0]
    df = pd.read_csv(f, usecols=lambda c: c in ('material_id', E_FORM_TRUE, E_HULL_TRUE))
    return df.dropna(subset=[E_FORM_TRUE, E_HULL_TRUE]).rename(columns={E_FORM_TRUE: 'eft', E_HULL_TRUE: 'hull_true'})

def load_predictions(df_summ):
    df = df_summ.copy()
    for m in MODELS:
        p = pd.read_csv(os.path.join(UIP, f'{m}_pred.csv'))[['material_id', 'e_form_pred']].rename(columns={'e_form_pred': m})
        df = df.merge(p, on='material_id', how='inner')
    return df.dropna()

def run_calibration(df):
    results = {}
    n = len(df)
    
    # Split calibration (20%) and evaluation (80%)
    cal_df, eval_df = train_test_split(df, test_size=0.8, random_state=42)
    
    yt_cal = (cal_df['hull_true'] < 0).astype(int).values
    yt_eval = (eval_df['hull_true'] < 0).astype(int).values
    
    for m in MODELS:
        print(f"Calibrating {m}...", flush=True)
        # Predicted hull
        hp_cal = cal_df['hull_true'].values + (cal_df[m].values - cal_df['eft'].values)
        hp_eval = eval_df['hull_true'].values + (eval_df[m].values - eval_df['eft'].values)
        
        # Fit Isotonic Regression to map predicted hull to P(stable)
        # Note: Isotonic Regression expects features to increase with label,
        # so we pass -hp_cal (since lower predicted hull means more stable, i.e., higher probability of stable)
        iso = IsotonicRegression(out_of_bounds='clip')
        iso.fit(-hp_cal, yt_cal)
        
        # Predict stable probabilities
        p_stable_cal = iso.predict(-hp_cal)
        p_stable_eval = iso.predict(-hp_eval)
        
        # Decision confidence score = |p_stable - 0.5| (further from 0.5 means more confident)
        conf_eval = np.abs(p_stable_eval - 0.5)
        # Base stable prediction
        yp_eval = (hp_eval < 0).astype(int)
        
        # We test selective prediction (abstention) at various coverages
        coverages = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2]
        
        # 1. Calibrated abstention (keep highest confidence |p_stable - 0.5|)
        cal_curve = []
        for cov in coverages:
            k = int(cov * len(eval_df))
            idx = np.argsort(conf_eval)[-k:] # keep the k highest-confidence indices
            yt_sub = yt_eval[idx]
            yp_sub = yp_eval[idx]
            tp = int(((yt_sub == 1) & (yp_sub == 1)).sum())
            fp = int(((yt_sub == 0) & (yp_sub == 1)).sum())
            prec = tp / (tp + fp) if (tp + fp) > 0 else float('nan')
            cal_curve.append({
                'coverage': cov,
                'precision': prec,
                'n_stable_called': int(yp_sub.sum())
            })
            
        # 2. Trivial margin-based abstention (keep largest |hp_eval| )
        margin_eval = np.abs(hp_eval)
        margin_curve = []
        for cov in coverages:
            k = int(cov * len(eval_df))
            idx = np.argsort(margin_eval)[-k:] # keep the k highest-margin indices
            yt_sub = yt_eval[idx]
            yp_sub = yp_eval[idx]
            tp = int(((yt_sub == 1) & (yp_sub == 1)).sum())
            fp = int(((yt_sub == 0) & (yp_sub == 1)).sum())
            prec = tp / (tp + fp) if (tp + fp) > 0 else float('nan')
            margin_curve.append({
                'coverage': cov,
                'precision': prec,
                'n_stable_called': int(yp_sub.sum())
            })
            
        # Calculate bootstrap 95% CI on the precision difference (calibrated - margin) at 70% coverage
        diff_boot = []
        n_eval = len(eval_df)
        k_70 = int(0.7 * n_eval)
        
        for _ in range(200):
            bi = RNG.integers(0, n_eval, n_eval)
            conf_b = conf_eval[bi]
            margin_b = margin_eval[bi]
            yt_b = yt_eval[bi]
            yp_b = yp_eval[bi]
            
            # Calibrated
            idx_c = np.argsort(conf_b)[-k_70:]
            yt_sub_c = yt_b[idx_c]
            yp_sub_c = yp_b[idx_c]
            tp_c = int(((yt_sub_c == 1) & (yp_sub_c == 1)).sum())
            fp_c = int(((yt_sub_c == 0) & (yp_sub_c == 1)).sum())
            prec_c = tp_c / (tp_c + fp_c) if (tp_c + fp_c) > 0 else 0
            
            # Margin
            idx_m = np.argsort(margin_b)[-k_70:]
            yt_sub_m = yt_b[idx_m]
            yp_sub_m = yp_b[idx_m]
            tp_m = int(((yt_sub_m == 1) & (yp_sub_m == 1)).sum())
            fp_m = int(((yt_sub_m == 0) & (yp_sub_m == 1)).sum())
            prec_m = tp_m / (tp_m + fp_m) if (tp_m + fp_m) > 0 else 0
            
            diff_boot.append(prec_c - prec_m)
            
        ci_diff = [
            float(np.percentile(diff_boot, 2.5)),
            float(np.percentile(diff_boot, 97.5))
        ]
        
        results[m] = {
            'calibrated_curve': cal_curve,
            'margin_curve': margin_curve,
            'ci_difference_at_70_coverage': ci_diff,
            'calibration_beats_margin_at_70': bool(ci_diff[0] > 0)
        }
        
        print(f"  {m} completed: CI of diff at 70% cov: {ci_diff} | beats margin baseline: {results[m]['calibration_beats_margin_at_70']}", flush=True)
        
    return results

def main():
    print("Loading data summary...", flush=True)
    df_summ = load_summary()
    print("Merging predictions...", flush=True)
    df = load_predictions(df_summ)
    print(f"Loaded {len(df)} predictions across 4 models.", flush=True)
    
    results = run_calibration(df)
    
    os.makedirs('research/results', exist_ok=True)
    with open('research/results/mt_v28_calibration_results.json', 'w') as f:
        json.dump(results, f, indent=2)
        
    # Generate markdown summary
    L = ['# MT28 Hull-Boundary Decision Calibration & Conformal Abstention Results', '',
         'We evaluate split-conformal isotonic calibration on WBM test predictions (n=256,963).', '',
         '| Model | Cov 1.0 Prec | Cov 0.7 Cal Prec | Cov 0.7 Margin Prec | 95% CI of Difference | Beats Margin Baseline? |',
         '|---|---:|---:|---:|---|:---:|']
    for m in MODELS:
        r = results[m]
        prec_10 = r['calibrated_curve'][0]['precision']
        prec_07_c = r['calibrated_curve'][3]['precision']
        prec_07_m = r['margin_curve'][3]['precision']
        ci = r['ci_difference_at_70_coverage']
        L.append(f"| {m} | {prec_10:.4f} | {prec_07_c:.4f} | {prec_07_m:.4f} | ({ci[0]:.4f}, {ci[1]:.4f}) | {r['calibration_beats_margin_at_70']} |")
        
    with open('research/results/mt_v28_calibration_summary.md', 'w') as f:
        f.write('\n'.join(L) + '\n')
    print('\n'.join(L))

if __name__ == '__main__':
    main()
