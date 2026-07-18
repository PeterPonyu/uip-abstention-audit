#!/usr/bin/env python
"""
P2-01 Independent Red-Team: Calibration attack experiments
- Attack A (primary): Multi-seed split variance for the 70% coverage precision gain (calibrated vs margin).
- Reports: gain distribution (mean, median, 95% range), fraction of seeds where CI excludes 0.
- This quantifies whether the MT28 headline ("calibration adds value beyond |hull margin|") is robust to different random cal/eval splits.

Run (local or via dispatch):
  python research/scripts/run_calib_redteam.py --n-seeds 20 --coverage 0.7

Output goes to research/redteam/calib_redteam_multi_seed_YYYYMMDD.json + .md
"""
import argparse
import os
import glob
import json
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import train_test_split

DATA = os.path.expanduser('~/mt_stage0/data')
UIP = os.path.expanduser('~/mt_uip')
E_FORM_TRUE = 'e_form_per_atom_mp2020_corrected'
E_HULL_TRUE = 'e_above_hull_mp2020_corrected_ppd_mp'
MODELS = ['orb', 'mace', 'chgnet', 'm3gnet']

def load_data():
    f = glob.glob(os.path.join(DATA, '*wbm-summary*.csv.gz'))[0]
    summ = pd.read_csv(f, usecols=lambda c: c in ('material_id', E_FORM_TRUE, E_HULL_TRUE))
    summ = summ.dropna(subset=[E_FORM_TRUE, E_HULL_TRUE]).rename(columns={E_FORM_TRUE:'eft', E_HULL_TRUE:'hull_true'})
    for m in MODELS:
        p = pd.read_csv(os.path.join(UIP, f'{m}_pred.csv'))[['material_id','e_form_pred']].rename(columns={'e_form_pred':m})
        summ = summ.merge(p, on='material_id', how='inner')
    return summ.dropna()

def evaluate_abstention(score, yp, yt, cov):
    n = len(score)
    k = max(1, int(cov * n))
    idx = np.argsort(score)[::-1][:k]
    sp = yp[idx]
    st = yt[idx]
    tp = ((sp == 1) & (st == 1)).sum()
    fp = ((sp == 1) & (st == 0)).sum()
    return tp / (tp + fp) if (tp + fp) > 0 else 0.0

def run_one_seed(df, seed, coverage=0.7, model='orb'):
    rng = np.random.default_rng(seed)
    n = len(df)
    indices = np.arange(n)
    rng.shuffle(indices)
    half = n // 2
    cal_idx, test_idx = indices[:half], indices[half:]

    hp_cal = df['hull_true'].values[cal_idx] + (df[model].values[cal_idx] - df['eft'].values[cal_idx])
    yt_cal = (df['hull_true'].values[cal_idx] < 0).astype(int)
    hp_test = df['hull_true'].values[test_idx] + (df[model].values[test_idx] - df['eft'].values[test_idx])
    yt_test = (df['hull_true'].values[test_idx] < 0).astype(int)
    yp_test = (hp_test < 0).astype(int)

    # Isotonic
    iso = IsotonicRegression(out_of_bounds='clip')
    iso.fit(-hp_cal, yt_cal)
    p_test = iso.predict(-hp_test)
    conf_test = np.maximum(p_test, 1 - p_test)

    margin_test = np.abs(hp_test)

    prec_margin = evaluate_abstention(margin_test, yp_test, yt_test, coverage)
    prec_cal = evaluate_abstention(conf_test, yp_test, yt_test, coverage)
    gain = prec_cal - prec_margin

    # Bootstrap CI on this seed's gain (500 resamples)
    boot_gains = []
    n_test = len(yt_test)
    for _ in range(500):
        b = rng.integers(0, n_test, n_test)
        bm = margin_test[b]
        bc = conf_test[b]
        byp = yp_test[b]
        byt = yt_test[b]
        bp_m = evaluate_abstention(bm, byp, byt, coverage)
        bp_c = evaluate_abstention(bc, byp, byt, coverage)
        boot_gains.append(bp_c - bp_m)
    ci = [float(np.percentile(boot_gains, 2.5)), float(np.percentile(boot_gains, 97.5))]
    return gain, ci, prec_margin, prec_cal

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--n-seeds', type=int, default=12)
    parser.add_argument('--coverage', type=float, default=0.7)
    parser.add_argument('--model', default='orb')
    args = parser.parse_args()

    print(f"MT28 Red-Team Attack A: Multi-seed calibration split variance (model={args.model}, cov={args.coverage})")
    df = load_data()
    print(f"Loaded N={len(df)}")

    gains = []
    cis = []
    for s in range(args.n_seeds):
        g, ci, pm, pc = run_one_seed(df, seed=20260616 + s*17, coverage=args.coverage, model=args.model)
        gains.append(g)
        cis.append(ci)
        print(f"seed {s}: gain={g:.5f}  CI=[{ci[0]:.5f},{ci[1]:.5f}]  margin_prec={pm:.4f} cal_prec={pc:.4f}")

    gains = np.array(gains)
    lower = np.array([c[0] for c in cis])
    median_gain = float(np.median(gains))
    mean_gain = float(np.mean(gains))
    p_positive = float((lower > 0).mean())
    frac_excludes_zero = float(np.mean([c[0] > 0 for c in cis]))

    report = {
        'timestamp': datetime.now().isoformat(),
        'model': args.model,
        'coverage': args.coverage,
        'n_seeds': args.n_seeds,
        'gain_mean': mean_gain,
        'gain_median': median_gain,
        'gain_range_approx': [float(gains.min()), float(gains.max())],
        'fraction_seeds_CI_excludes_zero': frac_excludes_zero,
        'p_gain_positive_lower': p_positive,
        'note': 'If frac_excludes_zero remains high across seeds, the calibration advantage is robust to split choice.'
    }

    os.makedirs('research/redteam', exist_ok=True)
    tag = f"calib_redteam_multiseed_{args.model}_cov{int(args.coverage*100)}_{args.n_seeds}seeds"
    with open(f'research/redteam/{tag}.json', 'w') as f:
        json.dump(report, f, indent=2)

    print("\n=== Red-Team Summary ===")
    print(json.dumps(report, indent=2))
    print(f"Saved to research/redteam/{tag}.json")

if __name__ == "__main__":
    main()
