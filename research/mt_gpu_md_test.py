import time
import numpy as np
import torch
import ase
from ase.build import bulk
from ase.md.velocitydistribution import MaxwellBoltzmannDistribution
from ase.md import VelocityVerlet
from ase import units

def run_md(name, calc, steps=50):
    print(f"\n=== Running MD with {name} ===")
    atoms = bulk('Si', 'diamond', a=5.43, cubic=True)
    atoms = atoms * (2, 2, 2) # 64 atoms
    atoms.calc = calc
    
    # Set temperature
    MaxwellBoltzmannDistribution(atoms, temperature_K=300)
    
    # Initialize dynamical system
    dyn = VelocityVerlet(atoms, timestep=1.0 * units.fs)
    
    energies = []
    times = []
    
    # Start VRAM measurement
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
        vram_start = torch.cuda.max_memory_allocated() / (1024**2)
    else:
        vram_start = 0.0
        
    t_start = time.time()
    
    # Run MD steps
    for i in range(steps):
        dyn.run(steps=1)
        pe = atoms.get_potential_energy()
        ke = atoms.get_kinetic_energy()
        tot = pe + ke
        energies.append(tot)
        times.append(i)
        
    t_end = time.time()
    
    if torch.cuda.is_available():
        vram_peak = torch.cuda.max_memory_allocated() / (1024**2)
    else:
        vram_peak = 0.0
        
    energies = np.array(energies)
    drift = (energies[-1] - energies[0]) / steps
    std_energy = np.std(energies)
    
    print(f"{name} MD completed: {steps} steps in {t_end - t_start:.2f}s ({1000*(t_end - t_start)/steps:.1f} ms/step)")
    print(f"Peak VRAM: {vram_peak:.1f} MB (Start: {vram_start:.1f} MB)")
    print(f"Initial Energy: {energies[0]:.6f} eV, Final Energy: {energies[-1]:.6f} eV")
    print(f"Drift per step: {drift:.6e} eV, Stdev of Total Energy: {std_energy:.6e} eV")
    
    return {
        'name': name,
        'vram_peak_mb': vram_peak,
        'time_per_step_ms': 1000 * (t_end - t_start) / steps,
        'drift_per_step': drift,
        'std_energy': std_energy,
        'energies': list(energies)
    }

def main():
    print("CUDA available:", torch.cuda.is_available())
    results = {}
    
    # 1. CHGNet
    try:
        from chgnet.model.dynamics import CHGNetCalculator
        chg_calc = CHGNetCalculator(use_device="cuda")
        results['CHGNet'] = run_md('CHGNet', chg_calc)
    except Exception as e:
        print("CHGNet failed:", e)
        import traceback
        traceback.print_exc()
        
    # 2. MACE
    try:
        from mace.calculators import mace_mp
        mace_calc = mace_mp(model="medium", device="cuda", default_dtype="float32")
        results['MACE'] = run_md('MACE', mace_calc)
    except Exception as e:
        print("MACE failed:", e)
        import traceback
        traceback.print_exc()
        
    # 3. ORB
    try:
        from orb_models.forcefield import pretrained
        from orb_models.forcefield.inference.calculator import ORBCalculator
        orb_model, orb_adapter = pretrained.orb_v2(device="cuda")
        orb_calc = ORBCalculator(orb_model, orb_adapter, device="cuda")
        results['ORB'] = run_md('ORB', orb_calc)
    except Exception as e:
        print("ORB failed:", e)
        import traceback
        traceback.print_exc()

    import json
    import os
    os.makedirs('research/results', exist_ok=True)
    with open('research/results/mt_gpu_md_results.json', 'w') as f:
        json.dump(results, f, indent=2)

if __name__ == '__main__':
    main()
