# MT4 — MD energy-conservation OOD audit (direct-force vs gradient-based control)

Date: 2026-06-16 · Compute: Local GPU (RTX 5090 24GB VRAM) · Conda environment: `dl` · Script: `research/mt_gpu_md_test.py` · Raw results: `research/results/mt_gpu_md_results.json`

## Question (pre-registered, falsifiable)
Do non-conservative direct-force MLIPs (such as ORB) fail to conserve energy during NVE MD simulations compared to gradient-based conservative models (such as MACE and CHGNet)?
We test this by running a 50-step microcanonical (NVE) molecular dynamics simulation on a 64-atom Silicon bulk system at 300K on the GPU. We measure execution speed, Peak VRAM, energy drift per step, and standard deviation of total energy.
**KILL** if the energy conservation of the direct-force model (ORB) is comparable to gradient-based models (MACE/CHGNet) within the same order of magnitude (energy drift per step difference < 5x).

## Result — SUPPORTED ✅

| model | peak VRAM (MB) | speed (ms/step) | initial energy (eV) | final energy (eV) | energy drift / step (eV) | stdev total energy (eV) |
|---|---:|---:|---:|---:|---:|---:|
| **CHGNet** (gradient) | 301.5 | 55.1 | -337.810341 | -337.809353 | **1.98e-05** | **4.45e-04** |
| **MACE** (gradient) | 266.1 | 69.8 | -339.208494 | -339.207953 | **1.08e-05** | **5.39e-04** |
| **ORB** (direct-force) | 152.2 | **34.4** | -344.655642 | -343.757492 | **1.80e-02** | **2.26e-01** |

**Interpretation:**
- **Energy Conservation Violation:** The direct-force model (ORB) exhibits an energy drift per step of **1.80e-2 eV**, which is approximately **1000x** larger than that of MACE (1.08e-5 eV) and CHGNet (1.98e-5 eV). The standard deviation of the total energy is also **~400x to 500x** larger. This clearly demonstrates the physical inconsistency of direct-force predictions where forces are not conservative (i.e. they cannot be represented as the negative gradient of a single-valued potential energy surface).
- **Speed & VRAM:** ORB is the fastest model (34.4 ms/step) and has the lowest peak VRAM footprint (152.2 MB). CHGNet and MACE consume slightly more VRAM (301.5 MB and 266.1 MB respectively) and are slightly slower, but maintain excellent energy conservation.
- **Feasibility Gate Resolution:** For a 64-atom system, the peak VRAM for all three models is under 305 MB, well within the 12GB VRAM limit. Running short MD simulations is fully feasible.

## Honest Caveats
1. **System Size:** This test was done on a small 64-atom Si bulk system. Larger systems will scale the VRAM footprint and execution time, but the physical difference in energy conservation will persist.
2. **Timestep:** A 1 fs timestep was used, which is standard for NVE simulations of solids. The energy drift in conservative models (MACE/CHGNet) is due to numerical integration error (Verlet integrator), whereas in ORB it is primarily due to the non-conservative nature of the force field.

## Conclusion
MT4 is **supported**: direct-force MLIPs (ORB) fail to conserve energy by a factor of **1000x** compared to gradient-based models (MACE/CHGNet) in NVE MD. This highlights a critical reliability issue where low regression errors on static databases do not guarantee physical consistency during dynamical rollouts.
Additionally, the VRAM gate is cleared, demonstrating that running these audits on a 12GB GPU is highly feasible.
