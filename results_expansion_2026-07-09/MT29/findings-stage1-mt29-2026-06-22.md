# MT29 Stage-1 — stratified-abstention interaction survives proper protocol → SUCCESS (2026-06-22)

Ultragoal Stage-1 story G007-s1-materials-mt29-real-chemistry. **VERDICT: SUCCESS.** The interaction survives
BOTH genuine chemical-family strata AND the matched-yield control that KILLed MT28 — not a proxy/yield artifact.

## What was done (and a self-caught bug)
1. Replaced the element-count proxy with **genuine anion-class strata** (electronegativity-priority:
   halide > oxide > chalcogenide > pnictide > intermetallic > other), per-formula. 6 strata, all ≥23K rows,
   genuinely varying stable base rate (oxide 12.4% → halide 27.8%).
2. Folded in the **MT28 matched-stable-call-yield control**. First attempt was VACUOUS (caught + flagged by the
   executor): per-stratum coverage-yields are nested in the same |margin| order → identical to coverage
   (mean |cov_int − yield_int| = 0.0005). **Corrected** to a COMMON ABSOLUTE yield budget across strata
   (DAF(top Y_tight) − DAF(top Y_loose), Y identical across strata) — the genuine MT28 semantics lifted to strata.
3. Shuffle-null (permute confidence within stratum) + 1000-boot CIs.

## Result — survives both controls
| Test | interaction CI-exclude-0 |
|---|---|
| coverage-matched, genuine anion strata | precision **47/60**, DAF **47/60** |
| **corrected matched-yield (MT28 control)** | **48/60** (all 4 models fire: chgnet 13/15, mace 13/15, m3gnet 11/15, orb 11/15) |
| shuffle-null (both) | **0/60** (clean; shuffle interaction max 0.0047) |

- Real interaction |median| 0.267, max +0.90 (chgnet oxide-vs-halide CI [0.774, 1.042]).
- **Physically coherent**: oxide is the highest abstention-benefit stratum for 3/4 models; halide/intermetallic
  lowest — consistent with UIP oxide-formation-energy miscalibration being where confidence-abstention buys most.

## Significance
This is the cleanest surviving materials result: a stratified selective-abstention interaction that holds under
real chemistry strata + the exact matched-yield control that sank the MT28 hull-margin wedge, with a clean
shuffle-null. The rank-reordering framing stays dead (Stage-0); this stratified-abstention protocol is the paper.

## Next step
Leave-one-element-out / WBM-round cross-split robustness on the corrected matched-yield interaction (confirm the
oxide-vs-intermetallic gap isn't driven by a few dominant element families) → Digital Discovery / NeurIPS D&B.

Files (research/results/MT29/): `mt29_stage1_result.json`, `mt29_stage1_matched_yield_result.json` (headline),
`mt29_stage1_chem_yield_result.json`, scripts + `mt29_stage1_chem_yield_manifest.json`.
