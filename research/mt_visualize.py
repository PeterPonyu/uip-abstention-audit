import os
import json
import matplotlib.pyplot as plt
import numpy as np

# Set style
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
fig_dir = 'research/figures'
os.makedirs(fig_dir, exist_ok=True)

# 1. Plot MT28 Calibration Curves
cal_res_path = 'research/results/mt_v28_calibration_results.json'
if os.path.exists(cal_res_path):
    with open(cal_res_path, 'r') as f:
        cal_data = json.load(f)
        
    fig, axes = plt.subplots(2, 2, figsize=(12, 10), sharex=True, sharey=False)
    axes = axes.flatten()
    models = ['orb', 'mace', 'chgnet', 'm3gnet']
    colors = {'orb': '#1f77b4', 'mace': '#ff7f0e', 'chgnet': '#2ca02c', 'm3gnet': '#d62728'}
    
    for idx, m in enumerate(models):
        if m not in cal_data:
            continue
        ax = axes[idx]
        c_curve = cal_data[m]['calibrated_curve']
        m_curve = cal_data[m]['margin_curve']
        
        covs = [x['coverage'] for x in c_curve]
        c_precs = [x['precision'] for x in c_curve]
        m_precs = [x['precision'] for x in m_curve]
        
        ax.plot(covs, c_precs, label='Calibrated (Split-Conformal)', color=colors[m], marker='o', linewidth=2)
        ax.plot(covs, m_precs, label='Baseline (Predicted Margin)', color='gray', linestyle='--', marker='x', linewidth=1.5)
        
        ax.set_title(f'{m.upper()} Stability Screening', fontsize=14, fontweight='bold')
        ax.set_xlabel('Coverage (fraction of structures kept)', fontsize=12)
        ax.set_ylabel('Stable Call Precision', fontsize=12)
        ax.set_xlim(1.05, 0.15) # Inverted x-axis from full coverage to low coverage
        ax.legend(loc='lower left', frameon=True)
        ax.tick_params(labelsize=10)
        
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, 'mt28_calibration_curves.png'), dpi=300)
    plt.close()
    print("Saved mt28_calibration_curves.png", flush=True)

# 2. Plot MT4 MD Energy Trajectories
md_res_path = 'research/results/mt_gpu_md_results.json'
if os.path.exists(md_res_path):
    with open(md_res_path, 'r') as f:
        md_data = json.load(f)
        
    plt.figure(figsize=(10, 6))
    
    # We want to plot total energy deviation from the initial step (E(t) - E(0))
    for m in ['MACE', 'CHGNet', 'ORB']:
        if m not in md_data:
            continue
        energies = np.array(md_data[m]['energies'])
        steps = np.arange(len(energies))
        dev = energies - energies[0]
        
        if m == 'ORB':
            plt.plot(steps, dev, label=f'{m} (Direct Force)', color='#d62728', linewidth=2.5)
        else:
            plt.plot(steps, dev, label=f'{m} (Gradient-based)', linewidth=2)
            
    plt.title('NVE MD Total Energy Drift Case Study (Bulk Si)', fontsize=16, fontweight='bold')
    plt.xlabel('MD Step (1 step = 1 fs)', fontsize=14)
    plt.ylabel('Energy Deviation $E_t - E_0$ (eV)', fontsize=14)
    plt.legend(fontsize=12, loc='upper left')
    plt.tick_params(labelsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, 'mt4_energy_trajectories.png'), dpi=300)
    plt.close()
    print("Saved mt4_energy_trajectories.png", flush=True)
