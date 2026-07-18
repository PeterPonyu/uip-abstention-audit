import os
import time
import json
import numpy as np
import torch
import ase
from ase.build import bulk
from ase.md.velocitydistribution import MaxwellBoltzmannDistribution
from ase.md import VelocityVerlet
from ase import units

def get_perturbed_structures():
    elements = [
        ('Si', 'diamond', 5.43),
        ('Cu', 'fcc', 3.61),
        ('Fe', 'bcc', 2.87),
        ('Al', 'fcc', 4.05),
        ('Pt', 'fcc', 3.92)
    ]
    structures = []
    
    for symbol, lattice, a_param in elements:
        # Generate 10 strained structures (volume compression/expansion)
        for i, scale in enumerate(np.linspace(0.85, 1.15, 10)):
            atoms = bulk(symbol, lattice, a=a_param * scale, cubic=True)
            atoms = atoms * (2, 2, 2)
            structures.append({
                'id': f'{symbol}_strain_{i}',
                'symbol': symbol,
                'type': 'strain',
                'param': float(scale),
                'atoms': atoms.copy()
            })
            
        # Generate 10 rattled structures (atomic displacements)
        for i, stdev in enumerate(np.linspace(0.02, 0.25, 10)):
            atoms = bulk(symbol, lattice, a=a_param, cubic=True)
            atoms = atoms * (2, 2, 2)
            atoms.rattle(stdev=stdev, seed=i)
            structures.append({
                'id': f'{symbol}_rattle_{i}',
                'symbol': symbol,
                'type': 'rattle',
                'param': float(stdev),
                'atoms': atoms.copy()
            })
            
    return structures

def run_md(name, calc, base_atoms, steps=200):
    atoms = base_atoms.copy()
    atoms.calc = calc
    
    # Initialize temperature
    MaxwellBoltzmannDistribution(atoms, temperature_K=300)
    
    # NVE integrator
    dyn = VelocityVerlet(atoms, timestep=1.0 * units.fs)
    
    energies = []
    
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
        
    t_start = time.time()
    
    try:
        for _ in range(steps):
            dyn.run(steps=1)
            pe = atoms.get_potential_energy()
            ke = atoms.get_kinetic_energy()
            energies.append(float(pe + ke))
    except Exception as e:
        print(f"  {name} failed during MD run: {e}")
        return None
        
    t_end = time.time()
    
    if torch.cuda.is_available():
        vram_peak = torch.cuda.max_memory_allocated() / (1024**2)
    else:
        vram_peak = 0.0
        
    energies = np.array(energies)
    drift = (energies[-1] - energies[0]) / steps
    std_energy = np.std(energies)
    
    return {
        'vram_peak_mb': float(vram_peak),
        'time_per_step_ms': float(1000 * (t_end - t_start) / len(energies)),
        'drift_per_step': float(drift),
        'std_energy': float(std_energy),
        'initial_energy': float(energies[0]),
        'final_energy': float(energies[-1])
    }

def main():
    print("Initializing calculators...", flush=True)
    
    # 1. CHGNet
    from chgnet.model.dynamics import CHGNetCalculator
    chg_calc = CHGNetCalculator(use_device="cuda")
    
    # 2. MACE
    from mace.calculators import mace_mp
    mace_calc = mace_mp(model="medium", device="cuda", default_dtype="float32")
    
    # 3. ORB
    from orb_models.forcefield import pretrained
    from orb_models.forcefield.inference.calculator import ORBCalculator
    orb_model, orb_adapter = pretrained.orb_v2(device="cuda")
    orb_calc = ORBCalculator(orb_model, orb_adapter, device="cuda")
    
    print("Generating perturbed structures...", flush=True)
    structures = get_perturbed_structures()
    print(f"Generated {len(structures)} structures.", flush=True)
    
    results = []
    
    for idx, struct in enumerate(structures):
        print(f"[{idx+1}/{len(structures)}] Running structure {struct['id']} ({struct['type']}={struct['param']:.3f})...", flush=True)
        
        atoms = struct['atoms']
        
        # Calculate initial energies and disagreement
        try:
            atoms.calc = chg_calc
            e_chg = float(atoms.get_potential_energy() / len(atoms))
            
            atoms.calc = mace_calc
            e_mace = float(atoms.get_potential_energy() / len(atoms))
            
            atoms.calc = orb_calc
            e_orb = float(atoms.get_potential_energy() / len(atoms))
            
            disagreement = float(np.std([e_chg, e_mace, e_orb]))
        except Exception as e:
            print(f"  Failed initial energy computation: {e}")
            continue
            
        struct_res = {
            'id': struct['id'],
            'symbol': struct['symbol'],
            'type': struct['type'],
            'param': struct['param'],
            'e_chg_init': e_chg,
            'e_mace_init': e_mace,
            'e_orb_init': e_orb,
            'disagreement': disagreement,
            'md_results': {}
        }
        
        # Run MACE MD
        res_mace = run_md('MACE', mace_calc, atoms, steps=200)
        if res_mace:
            struct_res['md_results']['MACE'] = res_mace
            
        # Run CHGNet MD
        res_chg = run_md('CHGNet', chg_calc, atoms, steps=200)
        if res_chg:
            struct_res['md_results']['CHGNet'] = res_chg
            
        # Run ORB MD
        res_orb = run_md('ORB', orb_calc, atoms, steps=200)
        if res_orb:
            struct_res['md_results']['ORB'] = res_orb
            
        results.append(struct_res)
        
        # Save intermediate results every 5 structures
        if (idx + 1) % 5 == 0:
            os.makedirs('research/results', exist_ok=True)
            with open('research/results/mt_gpu_batch_md_results.json', 'w') as f:
                json.dump(results, f, indent=2)
                
    # Save final results
    os.makedirs('research/results', exist_ok=True)
    with open('research/results/mt_gpu_batch_md_results.json', 'w') as f:
        json.dump(results, f, indent=2)
        
    print("\nBatch MD run completed successfully!", flush=True)

if __name__ == '__main__':
    main()
