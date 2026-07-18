# MT23 Stage-0 — photonics inverse-crime: low-res optimization exploits discretization (SUPPORTED)

Date: 2026-06-15 · Workspace: `materials-mlip-research` · Compute: `dl4080`, **isolated conda env
`photonics` (pymeep)** — built specifically to avoid polluting the shared base env (see
[[pip-pollutes-shared-4080-env]]). Script: `mt23_meep_invcrime.py` · Raw: `results/MT23/`.

## Question (pre-registered, falsifiable)
Does *optimizing a photonic design at a coarse numerical discretization exploit that discretization* —
i.e. is the "optimal" geometry found at low resolution actually good, or a numerical artifact that
collapses at high resolution? 1D Fabry-Perot etalon (index-3.5 slab in air); "optimize" the slab length L
to MAXIMIZE transmission at the target frequency at low resolution, then evaluate that L at high resolution.
**KILL** if the optimum is stable across resolutions (gap ~0 AND argmax shift ≤ 1 grid step) → no exploitation.

## Result — SUPPORTED ✅

| quantity | value |
|---|---|
| res_low / res_high | 20 / 120 |
| L*_low (argmax T at low res) | 0.68 |
| **T at L*_low, low res** | **0.9994** (near-perfect) |
| **T at L*_low, high res** | **0.4528** |
| **inverse-crime gap** | **0.547** |
| L*_high (true optimum) | 0.72 |
| argmax shift | 0.04 = **2 grid steps** |
| exploitation detected | **True** |
| runtime | 4.8 s |

**Interpretation:** the slab length the optimizer picks at low resolution (L=0.68) gives apparently
*perfect* transmission (T≈0.999) — but that is a numerical-dispersion artifact: at high resolution the
*same* design transmits only **0.45**, and the true resonant length has shifted to L=0.72. A "great" result
obtained at the discretization you optimized on is **not** a reliable design — the materials/photonics
analogue of the workspace's "good score ≠ reliable decision" thesis (here: "good FOM at the training
discretization ≠ reliable physics"). This is the classic *inverse crime* (inverting/optimizing with the
same discretization that generated the figure-of-merit).

## Honest caveats
1. **Single-solver resolution-convergence proxy.** The gate's ideal MT23 cross-checks an FDTDX/JAX optimum
   on an *independent* solver (Meep). Here both the low- and high-res evaluations are Meep, so this tests
   *resolution* exploitation (numerical dispersion), not *solver-formulation* exploitation. The
   cross-solver (FDTDX→Meep) check is the stronger follow-up; it needs FDTDX in the same isolated env.
2. **1D etalon** is a deliberately clean, sharp-resonance system where the effect is large by construction;
   a 2D inverse-designed device (meep.adjoint) is the realistic next step and would quantify how badly
   real adjoint optimization exploits its grid.
3. Physics simulation, benchmark-only; no device-fabrication claim.

## Conclusion
MT23 is **supported**: a low-resolution optimum can be a discretization artifact (T 0.999 → 0.45 at high
res; gap 0.55; optimum shifts 2 grid steps), so any ML/optimization result on a photonic simulator must be
validated at finer discretization (or an independent solver) before it is trusted. A "validate-at-higher-
fidelity-before-trusting" gate is the decision-grade artifact. Ran in an isolated env (no shared-env risk).

## Source
"Inverse crime" methodology (Colton & Kress; Wirgin 2004); Meep FDTD (Oskooi et al. 2010). Gate ref:
MT23 row, `sim-first-research/research/audits/gating-thirdwave-20260615.md`.
