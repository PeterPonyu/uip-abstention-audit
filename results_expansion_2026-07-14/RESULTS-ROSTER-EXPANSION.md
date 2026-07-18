# MT29 roster-expansion results — the generational contrast of oxide-anchored value-of-abstention

**RED-TEAM-ROUND2 remediation rerun (2026-07-14).** Supersedes `results_expansion_2026-07-13/` (contaminated — see that dir's `CONTAMINATED-2026-07-14.md`). `orb_v2_omat` is dropped: it is byte-identical to the frozen 'orb' headline anchor (both are the published Orb-v2 Figshare file 51607307), so it is a non-independent duplicate, not an additional OMat-generation model. All 44 roster raw sources pass the md5 gate (`verify_roster_md5.py`, 44/44 OK); this is the only non-independent member, leaving 43 models converted / 32 included UIPs.

**Status:** post-hoc-motivated, pre-specified analysis plan (`mt29_roster_expansion_PREREG-2026-07-13.md`, dated 2026-07-13; not git-timestamped ahead of the run, unlike the alt-stratification prereg). Frozen legacy-4 regression guard passed byte-exact before this run.
**Machinery:** inherited verbatim (prototype-blocked cluster bootstrap, common-absolute matched-yield DAF gain, two-sided bootstrap p, BH-FDR+Holm, seed 20260621, n_boot 1000). Anchors use the frozen on-disk snapshot; all other models use published Figshare v25 predictions.

## Headline verdict

- **V1 (oxide-anchoring across the MP generation):** CONFIRMED — positive-anchored in 16/16 MP-gen UIPs (frac 1.0); oxide is the highest-value abstention stratum in 13/16.
- **V2 (generational dissolution/reversal in the OMat generation):** NO-GENERATIONAL-EFFECT (honest null) — positive-anchored in 16/16 OMat-gen UIPs (frac 1.0), reversed in 0/16, null in 0/16.
- **V3 (formal between-generation permutation test):** observed gap in mean oxide-vs-halide interaction (MP − OMat) = -0.0371 (95% CI [-0.2083, 0.13303]), permutation p = 0.68153 [n_MP=16, n_OMat=16].
- **Shuffle-null hygiene:** 0/480 false positives (clean = yes).
- **OVERALL:** NO-GENERATIONAL-EFFECT (honest null)

## Multiplicity (included-UIP family)

- Full family (480 model×pair cells): CI-excl-0 378, BH-FDR(q=.05) 369, Holm(α=.05) 0 [Holm resolution-limited at n_boot=1000].
- Oxide-vs-halide subfamily (32 cells): CI-excl-0 32, BH-FDR 32, Holm 0.

## Roster

- Roster source files fetched and md5-verified: 44. Independent models analyzed: 43 (all MP-gen: 27, all OMat-gen: 16) — `orb_v2_omat` excluded as a non-independent duplicate of the frozen 'orb' anchor (see remediation note above).
- Included UIPs after inclusion rule (≥50 called-stable/stratum, ≥0.99 coverage): 32 (16 MP-gen, 16 OMat-gen).

## Per-model oxide-vs-halide matched-yield interaction (prototype-blocked CI)

| model | gen | class | incl | MAE(eV) | I(oxide−halide) | 95% CI | excl0 | argmax-gain stratum | SSCS |
|---|---|---|:--:|--:|--:|---|:--:|---|--:|
| eqv2_s_mp | MP | uip | yes | 0.03519 | +1.1561 | [+1.018, +1.293] | yes | oxide | 0.17877 |
| matris_mptrj | MP | uip | yes | 0.03544 | +1.0087 | [+0.881, +1.133] | yes | oxide | 0.17368 |
| dpa3_v2_mptrj | MP | uip | yes | 0.03775 | +0.9900 | [+0.864, +1.132] | yes | oxide | 0.18072 |
| allegro_mp | MP | uip | yes | 0.04244 | +0.9539 | [+0.802, +1.112] | yes | oxide | 0.19423 |
| grace_2l_mptrj | MP | uip | yes | 5.2783434449527464e+16 | +0.9088 | [+0.756, +1.064] | yes | oxide | 0.37719 |
| chgnet | MP | anchor | yes | 0.06113 | +0.8962 | [+0.742, +1.038] | yes | oxide | 0.21264 |
| mattersim | MP | uip | yes | 0.02365 | +0.8286 | [+0.706, +0.942] | yes | oxide | 0.16786 |
| dpa3_v1_mptrj | MP | uip | yes | 0.04031 | +0.8272 | [+0.696, +0.952] | yes | oxide | 0.18547 |
| hienet | MP | uip | yes | 0.03933 | +0.7373 | [+0.597, +0.867] | yes | oxide | 0.17477 |
| mace_mp_0 | MP | anchor | yes | 0.02918 | +0.6204 | [+0.488, +0.756] | yes | oxide | 0.32727 |
| nequip_mp | MP | uip | yes | 0.04112 | +0.5910 | [+0.450, +0.729] | yes | oxide | 0.18086 |
| matris_10m_mp | MP | uip | yes | 0.03013 | +0.5784 | [+0.467, +0.686] | yes | oxide | 0.17118 |
| m3gnet | MP | anchor | yes | 0.07264 | +0.5712 | [+0.423, +0.707] | yes | other | 0.23125 |
| eqnorm_mptrj | MP | uip | yes | 0.0379 | +0.4979 | [+0.369, +0.630] | yes | other | 0.17964 |
| alphanet_mp | MP | uip | yes | 0.03961 | +0.4883 | [+0.371, +0.609] | yes | oxide | 0.18122 |
| sevennet_0 | MP | uip | yes | 9.604978677864128e+27 | +0.4761 | [+0.338, +0.608] | yes | oxide | 0.19111 |
| orb_mptrj | MP | anchor | yes | 0.0285 | +0.4396 | [+0.324, +0.550] | yes | oxide | 0.1609 |
| nequix_mp | MP | uip | yes | 0.04247 | +0.4234 | [+0.286, +0.575] | yes | other | 0.18703 |
| sevennet_l3i5 | MP | uip | yes | 0.04215 | +0.4116 | [+0.272, +0.553] | yes | oxide | 0.18916 |
| esen_mp | MP | uip | yes | 0.0322 | +0.3846 | [+0.252, +0.517] | yes | other | 0.17628 |
| allegro_oam | OMat | uip | yes | 0.02145 | +1.3124 | [+1.188, +1.440] | yes | oxide | 0.17414 |
| dpa31_ft | OMat | uip | yes | 0.02254 | +1.1260 | [+1.001, +1.252] | yes | oxide | 0.17395 |
| dpa3_v2_openlam | OMat | uip | yes | 0.0219 | +0.9786 | [+0.859, +1.112] | yes | oxide | 0.17259 |
| grace_1l_oam | OMat | uip | yes | 0.03008 | +0.9078 | [+0.766, +1.045] | yes | oxide | 0.18816 |
| eqv2_m_omat | OMat | uip | yes | 0.01981 | +0.9011 | [+0.773, +1.026] | yes | oxide | 0.17185 |
| dpa3_v1_openlam | OMat | uip | yes | 0.02258 | +0.8283 | [+0.711, +0.957] | yes | oxide | 0.17228 |
| alphanet_oma | OMat | uip | yes | 0.02327 | +0.7037 | [+0.576, +0.824] | yes | oxide | 0.17254 |
| esen_oam | OMat | uip | yes | 0.01825 | +0.6987 | [+0.585, +0.808] | yes | oxide | 0.17031 |
| nequip_oam_xl | OMat | uip | yes | 0.01959 | +0.6657 | [+0.554, +0.771] | yes | oxide | 0.17185 |
| orb_v3 | OMat | uip | yes | 0.02278 | +0.6426 | [+0.520, +0.756] | yes | oxide | 0.17176 |
| mace_mpa | OMat | uip | yes | 0.02904 | +0.6175 | [+0.485, +0.753] | yes | oxide | 0.3272 |
| grace_3l_oam | OMat | uip | yes | 0.01754 | +0.5686 | [+0.448, +0.674] | yes | oxide | 0.17046 |
| grace_2l_oam | OMat | uip | yes | 0.02309 | +0.5525 | [+0.441, +0.677] | yes | oxide | 0.17209 |
| nequip_oam | OMat | uip | yes | 0.02151 | +0.5365 | [+0.424, +0.643] | yes | oxide | 0.17145 |
| matris_oam | OMat | uip | yes | 0.01861 | +0.5048 | [+0.403, +0.607] | yes | oxide | 0.17001 |
| grace_2l_oam_l | OMat | uip | yes | 0.02232 | +0.3104 | [+0.189, +0.422] | yes | oxide | 0.171 |

### 2020-era classical baselines (MP-trained; reported for the MAE-vs-decision spread)

| model | incl | MAE(eV) | I(oxide−halide) | 95% CI | excl0 | argmax-gain stratum |
|---|:--:|--:|--:|---|:--:|---|
| cgcnn_p | yes | 0.10833 | +0.5210 | [+0.377, +0.670] | yes | oxide |
| alignn | yes | 0.0916 | +0.4457 | [+0.307, +0.575] | yes | pnictide |
| cgcnn | yes | 0.13501 | +0.2756 | [+0.140, +0.416] | yes | other |
| megnet | yes | 0.12823 | +0.2441 | [+0.079, +0.412] | yes | oxide |
| wrenformer | yes | 0.1048 | +0.1622 | [+0.054, +0.269] | yes | intermetallic |
| bowsr_megnet | no | 0.11452 | -0.0781 | [-0.180, +0.030] | no | chalcogenide |
| voronoi_rf | yes | 0.1415 | -0.1170 | [-0.218, -0.017] | yes | intermetallic |

---

*Generated by `mt29_roster_expansion_report.py` from `mt29_roster_expansion_result.json`. Interpretation is added below by hand, keyed to these frozen numbers.*
