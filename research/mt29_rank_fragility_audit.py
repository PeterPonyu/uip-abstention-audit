#!/usr/bin/env python
"""MT29 — Leaderboard rank fragility under unique-prototype split.

This script implements:
1. Loading the WBM summary and model predictions (MACE, CHGNet, M3GNet, ORB, CGCNN, CGCNN+P, MEGNet, ALIGNN-FF).
2. Merging datasets and calculating predicted hull distances.
3. Evaluating performance (MAE and F1) on:
   - Full dataset
   - Unique prototype subset (unique_prototype == True)
4. Ranking the models based on F1 score and MAE under both splits.
5. Computing Kendall-tau and Spearman correlations between full and unique-prototype rankings.
6. Computing bootstrap 95% CIs for rank displacement (rank on full - rank on unique-prototype).
7. Outputting the results to JSON and a Markdown findings file.
"""
import os
import json
import glob
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score
from scipy.stats import kendalltau, spearmanr
import warnings

warnings.filterwarnings('ignore')
RNG = np.random.default_rng(20260616)

DATA = os.path.expanduser('~/mt_stage0/data')
UIP = os.path.expanduser('~/mt_uip')
E_FORM_TRUE = 'e_form_per_atom_mp2020_corrected'
E_HULL_TRUE = 'e_above_hull_mp2020_corrected_ppd_mp'
OUT_JSON = '/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/research/results/MT29/mt29_rank_fragility_result.json'
OUT_MD = '/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/research/findings-MT29-rank-fragility.md'

def load_summary():
    f = glob.glob(os.path.join(DATA, '*wbm-summary*.csv.gz'))[0]
    df = pd.read_csv(f, usecols=lambda c: c in ('material_id', E_FORM_TRUE, E_HULL_TRUE, 'unique_prototype'))
    return df.dropna(subset=[E_FORM_TRUE, E_HULL_TRUE, 'unique_prototype'])

def model_preds():
    for f in sorted(glob.glob(os.path.join(UIP, '*_pred.csv'))):
        name = os.path.basename(f).replace('_pred.csv', '')
        df = pd.read_csv(f)
        yield name, df[['material_id', 'e_form_pred']].dropna()
    for name, glb in [('CGCNN', '*cgcnn-ens*IS2RE*.csv.gz'), ('CGCNN+P', '*cgcnn-perturb*IS2RE*.csv.gz'),
                     ('MEGNet', '*megnet*IS2RE*.csv.gz'), ('ALIGNN-FF', '*alignn-ff*IS2RE*.csv.gz')]:
        fs = glob.glob(os.path.join(DATA, glb))
        if not fs:
            continue
        df = pd.read_csv(fs[0])
        pc = [c for c in df.columns if c != 'material_id' and 'ale' not in c.lower()]
        if not pc:
            continue
        df['e_form_pred'] = df[pc].mean(axis=1)
        yield name, df[['material_id', 'e_form_pred']].dropna()

def compute_metrics(m, unique_only=None):
    if unique_only is not None:
        sub = m[m['unique_prototype'] == unique_only]
    else:
        sub = m
        
    mae = float(np.abs(sub['e_form_pred'] - sub[E_FORM_TRUE]).mean())
    yt = (sub[E_HULL_TRUE].values < 0).astype(int)
    yp = (sub['hull_pred'].values < 0).astype(int)
    f1 = float(f1_score(yt, yp, zero_division=0))
    return mae, f1

def get_ranks(metrics_dict, rank_by='f1'):
    # Sort models by metric. For f1: higher is better (descending). For mae: lower is better (ascending).
    models = list(metrics_dict.keys())
    if rank_by == 'f1':
        sorted_models = sorted(models, key=lambda m: metrics_dict[m]['f1'], reverse=True)
    else:
        sorted_models = sorted(models, key=lambda m: metrics_dict[m]['mae'])
        
    return {model: rank + 1 for rank, model in enumerate(sorted_models)}

def bootstrap_ranks(merged_dfs, n_boot=500):
    # Store bootstrap rank lists
    boot_ranks_full_f1 = {m: [] for m in merged_dfs}
    boot_ranks_uniq_f1 = {m: [] for m in merged_dfs}
    boot_ranks_full_mae = {m: [] for m in merged_dfs}
    boot_ranks_uniq_mae = {m: [] for m in merged_dfs}
    
    n = len(next(iter(merged_dfs.values())))
    
    for _ in range(n_boot):
        boot_idx = RNG.integers(0, n, n)
        
        # Temp metrics
        f1_full = {}
        f1_uniq = {}
        mae_full = {}
        mae_uniq = {}
        
        for name, m in merged_dfs.items():
            bm = m.iloc[boot_idx]
            
            # Full metrics
            mae_f, f1_f = compute_metrics(bm)
            f1_full[name] = {'f1': f1_f, 'mae': mae_f}
            mae_full[name] = {'f1': f1_f, 'mae': mae_f}
            
            # Unique metrics
            mae_u, f1_u = compute_metrics(bm, unique_only=True)
            f1_uniq[name] = {'f1': f1_u, 'mae': mae_u}
            mae_uniq[name] = {'f1': f1_u, 'mae': mae_u}
            
        # Ranks
        r_f1_full = get_ranks(f1_full, 'f1')
        r_f1_uniq = get_ranks(f1_uniq, 'f1')
        r_mae_full = get_ranks(mae_full, 'mae')
        r_mae_uniq = get_ranks(mae_uniq, 'mae')
        
        for name in merged_dfs:
            boot_ranks_full_f1[name].append(r_f1_full[name])
            boot_ranks_uniq_f1[name].append(r_f1_uniq[name])
            boot_ranks_full_mae[name].append(r_mae_full[name])
            boot_ranks_uniq_mae[name].append(r_mae_uniq[name])
            
    # Calculate CIs for displacements
    displacements_f1 = {}
    displacements_mae = {}
    
    for name in merged_dfs:
        disp_f1 = np.array(boot_ranks_full_f1[name]) - np.array(boot_ranks_uniq_f1[name])
        disp_mae = np.array(boot_ranks_full_mae[name]) - np.array(boot_ranks_uniq_mae[name])
        
        displacements_f1[name] = [float(np.percentile(disp_f1, 2.5)), float(np.percentile(disp_f1, 97.5))]
        displacements_mae[name] = [float(np.percentile(disp_mae, 2.5)), float(np.percentile(disp_mae, 97.5))]
        
    return displacements_f1, displacements_mae

def main():
    summ = load_summary()
    print(f"Loaded summary: {len(summ)} rows", flush=True)
    
    merged_dfs = {}
    metrics_full = {}
    metrics_uniq = {}
    
    # First, load all predictions and find common material_ids
    raw_dfs = {}
    for name, dfp in model_preds():
        m = summ.merge(dfp, on='material_id', how='inner').dropna(subset=['e_form_pred'])
        if len(m) < 5000:
            continue
        m['hull_pred'] = m[E_HULL_TRUE] + (m['e_form_pred'] - m[E_FORM_TRUE])
        raw_dfs[name] = m
        
    common_ids = None
    for name, m in raw_dfs.items():
        ids = set(m['material_id'].values)
        if common_ids is None:
            common_ids = ids
        else:
            common_ids = common_ids.intersection(ids)
            
    print(f"Intersection of material_ids size: {len(common_ids)}", flush=True)
    
    for name, m in raw_dfs.items():
        m_aligned = m[m['material_id'].isin(common_ids)].sort_values('material_id').reset_index(drop=True)
        merged_dfs[name] = m_aligned
        
        # Calculate scores
        mae_full, f1_full = compute_metrics(m_aligned)
        mae_uniq, f1_uniq = compute_metrics(m_aligned, unique_only=True)
        
        metrics_full[name] = {'mae': mae_full, 'f1': f1_full}
        metrics_uniq[name] = {'mae': mae_uniq, 'f1': f1_uniq}
        
    # Standard rankings
    ranks_f1_full = get_ranks(metrics_full, 'f1')
    ranks_f1_uniq = get_ranks(metrics_uniq, 'f1')
    ranks_mae_full = get_ranks(metrics_full, 'mae')
    ranks_mae_uniq = get_ranks(metrics_uniq, 'mae')
    
    # Sort rankings for comparison
    models = list(merged_dfs.keys())
    ranking_list_f1_full = [ranks_f1_full[m] for m in models]
    ranking_list_f1_uniq = [ranks_f1_uniq[m] for m in models]
    ranking_list_mae_full = [ranks_mae_full[m] for m in models]
    ranking_list_mae_uniq = [ranks_mae_uniq[m] for m in models]
    
    # Kendall-tau and Spearman correlations
    kt_f1 = kendalltau(ranking_list_f1_full, ranking_list_f1_uniq).statistic
    sp_f1 = spearmanr(ranking_list_f1_full, ranking_list_f1_uniq).statistic
    kt_mae = kendalltau(ranking_list_mae_full, ranking_list_mae_uniq).statistic
    sp_mae = spearmanr(ranking_list_mae_full, ranking_list_mae_uniq).statistic
    
    print(f"F1 Ranking correlation: Kendall-tau = {kt_f1:.4f}, Spearman = {sp_f1:.4f}", flush=True)
    print(f"MAE Ranking correlation: Kendall-tau = {kt_mae:.4f}, Spearman = {sp_mae:.4f}", flush=True)
    
    # Run bootstrap for CIs of displacements
    print("Running bootstrap resampling...", flush=True)
    disp_f1_ci, disp_mae_ci = bootstrap_ranks(merged_dfs)
    
    # Package JSON output
    model_output = []
    for m in models:
        model_output.append({
            'model': m,
            'f1_full': metrics_full[m]['f1'],
            'f1_uniq': metrics_uniq[m]['f1'],
            'rank_f1_full': ranks_f1_full[m],
            'rank_f1_uniq': ranks_f1_uniq[m],
            'displacement_f1': ranks_f1_full[m] - ranks_f1_uniq[m],
            'displacement_f1_ci95': disp_f1_ci[m],
            'mae_full': metrics_full[m]['mae'],
            'mae_uniq': metrics_uniq[m]['mae'],
            'rank_mae_full': ranks_mae_full[m],
            'rank_mae_uniq': ranks_mae_uniq[m],
            'displacement_mae': ranks_mae_full[m] - ranks_mae_uniq[m],
            'displacement_mae_ci95': disp_mae_ci[m]
        })
        
    out = {
        'experiment': 'MT29_rank_fragility_prototype_split',
        'metrics_f1': {
            'kendall_tau': round(float(kt_f1), 4),
            'spearman': round(float(sp_f1), 4)
        },
        'metrics_mae': {
            'kendall_tau': round(float(kt_mae), 4),
            'spearman': round(float(sp_mae), 4)
        },
        'models': model_output
    }
    
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"Results written to {OUT_JSON}", flush=True)
    
    # Write Markdown findings file
    lines = [
        f"# MT29 — Leaderboard rank fragility under unique-prototype split findings",
        f"",
        f"Date: 2026-06-16",
        f"",
        f"This audit evaluates whether model rankings remain stable when Matbench Discovery-style metrics are recomputed under the unique-prototype split (`unique_prototype == True`) versus the full dataset.",
        f"",
        f"## Rank Correlation Summary",
        f"- **F1 Stability-Classification Ranking**: Kendall-τ = **`{kt_f1:.4f}`** | Spearman = **`{sp_f1:.4f}`**",
        f"- **MAE Formation-Energy Regressor Ranking**: Kendall-τ = **`{kt_mae:.4f}`** | Spearman = **`{sp_mae:.4f}`**",
        f"",
        f"## Detailed Model Ranks and Displacements",
        f"",
        f"### 1. F1 Stability-Classification Ranks",
        f"",
        f"| Model | F1 Full | F1 Uniq | Rank Full | Rank Uniq | Rank Displacement [95% CI] |",
        f"| :--- | :---: | :---: | :---: | :---: | :---: |"
    ]
    
    # Sort models by Full F1 Rank
    sorted_f1 = sorted(model_output, key=lambda x: x['rank_f1_full'])
    for r in sorted_f1:
        ci_str = f"{r['displacement_f1']} [{r['displacement_f1_ci95'][0]:.1f}, {r['displacement_f1_ci95'][1]:.1f}]"
        lines.append(f"| {r['model']} | {r['f1_full']:.4f} | {r['f1_uniq']:.4f} | {r['rank_f1_full']} | {r['rank_f1_uniq']} | {ci_str} |")
        
    lines.extend([
        f"",
        f"### 2. MAE Formation-Energy Ranks",
        f"",
        f"| Model | MAE Full | MAE Uniq | Rank Full | Rank Uniq | Rank Displacement [95% CI] |",
        f"| :--- | :---: | :---: | :---: | :---: | :---: |"
    ])
    
    # Sort models by Full MAE Rank
    sorted_mae = sorted(model_output, key=lambda x: x['rank_mae_full'])
    for r in sorted_mae:
        ci_str = f"{r['displacement_mae']} [{r['displacement_mae_ci95'][0]:.1f}, {r['displacement_mae_ci95'][1]:.1f}]"
        lines.append(f"| {r['model']} | {r['mae_full']:.4f} | {r['mae_uniq']:.4f} | {r['rank_mae_full']} | {r['rank_mae_uniq']} | {ci_str} |")
        
    # Adjudication
    f1_fragile = kt_f1 < 0.9 or any(abs(r['displacement_f1']) > 1 for r in sorted_f1)
    mae_fragile = kt_mae < 0.9 or any(abs(r['displacement_mae']) > 1 for r in sorted_mae)
    
    lines.extend([
        f"",
        f"## Adjudication & Implications",
        f"- **F1 Ranking Fragility**: **`{str(f1_fragile).upper()}`** (Any model rank displacement > 1 or Kendall-τ < 0.9)",
        f"- **MAE Ranking Fragility**: **`{str(mae_fragile).upper()}`** (Any model rank displacement > 1 or Kendall-τ < 0.9)",
        f"- **Scientific Implications**: These findings show whether universal interatomic potential benchmarks are robust to structurally duplicate structures (prototypes) or if rank re-ordering occurs when structurally redundant information is removed from evaluation."
    ])
    
    with open(OUT_MD, 'w') as f:
        f.write("\n".join(lines) + "\n")
    print(f"Findings written to {OUT_MD}", flush=True)

if __name__ == '__main__':
    main()
