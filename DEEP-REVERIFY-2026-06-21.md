# Deep Re-verification — materials-mlip-research (2026-06-21)

Adversarial re-verification of the MLIP reliability-audit workspace against the 2024–2026 literature
and against the on-disk assets. Scope: benchmark / reliability-audit research only — no clinical,
regulatory, deployment, wet-lab, or discovery claims. All flagship analyses are CPU/pandas over
cached Matbench-Discovery predictions; the RTX 5090 is load-bearing only for the (now scooped) MD path.

This pass independently re-confirmed the on-disk assets, fetched/verified the load-bearing competing
papers (incl. two that have since been peer-published), and adds a partial-scoop finding the prior
draft did not surface ("Proof-Carrying Materials," arXiv:2603.12183, Mar 2026).

**One-line verdict:** Reshape MT28 into a single canonical *risk-coverage selective-prediction audit
of the WBM stability decision*, with `|predicted hull margin|` as the mandatory baseline and matched
coverage + matched stable-call yield as first-class controls. That one move converts the
publication-blocking protocol contradiction into the paper's central question and is the direction
that is both feasible-today and (narrowly) unscooped.

---

## 1. 可行性 (Feasibility on this machine) — GREEN

**Verdict: GREEN for all publishable (CPU) directions. The only GPU path is scientifically scooped, so GPU is not load-bearing.**

Independently re-verified on disk (2026-06-21):

| Asset | Path | Size | Rows | Verified contents |
|---|---|---:|---:|---|
| 4 modern UIP preds | `~/mt_uip/{chgnet,m3gnet,mace,orb}_pred.csv` | ~5.3 MB each | 256,963 each | cols: `material_id`, `e_form_pred` (header confirmed) |
| 4 stage-0 (2020) preds | `~/mt_stage0/data/*.csv.gz` | 1.3–13 MB | — | CGCNN ens=10, CGCNN+P perturb=5, MEGNet IS2RE, ALIGNN-FF IS2RE |
| WBM summary (ground truth) | `~/mt_stage0/data/2023-12-13-wbm-summary.csv.gz` | ~12.7 MB | 256,963 | 18 cols incl. ground-truth hull + prototype + chemistry (see below) |
| WBM initial atoms | `~/.cache/matbench-discovery/wbm/2024-08-04-wbm-initial-atoms.extxyz.zip` | (zip) | — | structures, if MD/prototype re-derivation needed |
| WBM summary cache copy | `~/.cache/matbench-discovery/wbm/2023-12-13-wbm-summary.csv.gz` | ~13 MB total cache | — | mirror of the above |

**Disk:** `/dev/nvme0n1p2` has **593 GB free** (not "tens of GB" — the brief understated headroom).
Total working data < 0.1 GB. No Figshare bulk zip required for MT28/MT29/V2/V6.

**Compute:** All flagship analyses (risk-coverage curves, AURC, isotonic/conformal calibration, rank
correlation, 1000× bootstrap CIs, chemistry stratification) are pandas ops over <300k-row tables —
seconds-to-minutes on the 24-core CPU. The RTX 5090 24 GB is **unused** for the publishable work. The
MD path (MT4) measured 154–534 MB peak VRAM (fits trivially) but MT4 is scooped (see §2), so the GPU
is off the critical path.

**Data access confirmed public/no-auth:** Matbench Discovery v1 lives on Figshare article **22715158**
(Data Files) + **28187990** (Model Predictions), free and registration-free; the package auto-caches to
`MBD_CACHE_DIR` (default `~/.cache/matbench-discovery`). The WBM summary CSV on disk is the canonical
public file. No download is needed for the recommended directions — everything is already local.

**Verified during this re-check (corrects a stated feasibility finding):** the cached WBM summary CSV
contains, fully populated for all 256,963 rows:
`formula`, `protostructure_spglib` (**224,179 distinct prototypes**), `unique_prototype` (bool;
**215,488 True / 41,475 False**), `e_above_hull_mp2020_corrected_ppd_mp` (ground-truth hull, **0 nulls**),
`e_above_hull_wbm`, `e_form_per_atom_mp2020_corrected`, `n_sites`, `volume`, `bandgap_pbe`, spglib
symmetry strings. The WBM elemental-substitution **round (1→5) is recoverable from `material_id`**
(`wbm-<step>-…`): counts **61,466 / 52,755 / 79,160 / 40,314 / 23,268**.

> **Correction to the prior MT29 feasibility note (material).** The stage-0 readiness JSON
> (`findings-MT28-MT29-stage0-readiness-2026-06-16.md`) marks MT29 `DATA_GATE_BLOCKED`, claiming
> "per-structure prototype/family labels … and train/test year or release-time metadata" are absent.
> That is **false for prototype/family/round**: `protostructure_spglib`, `unique_prototype`, `formula`,
> and the substitution round (from `material_id`) are all already on disk. The metadata simply was
> never *joined into the per-model result JSONs*. The genuinely missing axis is real **wall-clock
> model-release-date** metadata (when each leaderboard model was published) — but the time-*like*
> axis the MT29 prereg actually proposed (WBM substitution generation) **is fully available**.
> Prototype-, family-, and round-stratified MT29 is **GREEN today**.

---

## 2. 新颖性 (Novelty vs 2024–2026 literature) — per-direction

All competing papers below were fetched or confirmed via search this pass (status/venue updated where
they have since been peer-reviewed).

| Direction | Verdict | Closest competing work (venue, year) | Surviving wedge |
|---|---|---|---|
| **MT28** risk-coverage selective prediction on the **binary stability decision**, baseline = `\|hull margin\|` | **novel-with-wedge (but newly contested)** | (a) "Flexible Uncertainty Calibration for MLIPs," arXiv:2510.00721 (Oct 2025) — learnable conformal **regression** quantiles on energy/force, never the WBM stability decision. (b) **"Proof-Carrying Materials," arXiv:2603.12183 (Mar 2026)** — *does* target the **binary stability decision** and reports a **risk model with AUC-ROC 0.938** + bootstrap CIs + Lean-4 certs on CHGNet/MACE/TensorNet; **partial scoop of the selective-prediction-for-stability framing.** (c) "A critical examination of compound stability predictions," npj Comput. Mater. 2020 (arXiv:2001.10591) — "good formation energy ≠ good stability," but **no** hull-margin selective signal. | PCM does **not** compare against the trivial `\|predicted hull margin\|` baseline, does not report **fixed-coverage risk-coverage / AURC** for the stable call, and its framing is formal certification, not "does calibration beat the free margin." The unoccupied bar = *must beat the free hull-margin signal at matched coverage **and** matched stable-call yield, with bootstrap-CI precision-gain/AURC*. Narrow but real. |
| **MT28 sub:** `\|predicted hull margin\|` as the trivial confidence baseline | **novel** | Selective-prediction / AURC methodology is mature broadly (arXiv:2508.07556 — confirmed **generic ML, not materials**; CWSA arXiv:2505.18622) but **not ported to Matbench-Discovery's stability call**. | The specific "beat the free hull-margin signal at matched coverage+yield" bar is unoccupied. |
| **Chemistry-/prototype-stratified DAF under abstention** | **novel-with-wedge** | "Proof-Carrying Materials" arXiv:2603.12183 stratifies WBM failure by chemical family but reports **AUC-ROC, not abstention-conditioned DAF / risk-coverage**. | The *interaction* (stratum × coverage) on DAF/precision is unoccupied; data is on disk (§1). |
| **V6** cross-model disagreement = uncertainty signal | **scooped (signal, now npj-published); novel only as decision application** | **Liu et al., "Heterogeneous Ensemble Enables a Universal Uncertainty Metric for Atomistic Foundation Models," arXiv:2507.21297 → now npj Comput. Mater. 2026 (s41524-025-01905-x).** Same signal (architecturally-diverse cross-uMLIP disagreement → calibration-free uncertainty), validated on diverse datasets, used for distillation. | "disagreement = uncertainty" is **no longer novel and is now peer-published.** Only the *stability-decision precision-gate at matched coverage+yield vs the free hull-margin* survives, as a citable head-to-head delta against 2507.21297. |
| **MT4** non-conservative (ORB) vs conservative NVE drift | **scooped → drop** | **Bigi/Langer/Ceriotti, "The dark side of the forces," arXiv:2412.11569 → ICML 2025 (PMLR 267).** Directly measures ORB NVE non-conservation/runaway heating, gives a diagnostic metric, proposes a multiple-time-stepping remedy. | MT4's phenomenon is the same; its drift–disagreement correlation is weak (ρ_ORB≈0.33 on the 100-structure batch, CI [0.14, 0.48]). **No defensible standalone delta.** Keep at most as a one-figure negative control. |
| **MT29** prototype/family/time rank fragility | **mostly-scooped on the leakage *premise*; the rank-reordering deliverable is still open + now data-feasible** | MLIP Arena arXiv:2509.20630 (Sep 2025) re-ranks on physics/MD tasks under the same leakage motivation; Matbench Discovery itself reports full-vs-dedup metric shifts; "Bias in Universal MLIPs and Effects on Fine-Tuning," arXiv:2603.10159 (2026) — **confirmed: about fine-tuning bias, NOT rank reordering** (not a scoop). | The unique-prototype rank-stability NULL (τ=ρ=1.0) is real but uninteresting alone. The *quantified rank-reordering map across prototype/family/round splits with bootstrap rank CIs* — the MT29 prereg deliverable — is **not** published and is now runnable on-disk (§1). Weak-but-revivable. |
| **V2** "low MAE ≠ reliable decision" triangle dissolves for modern UIPs | **novel but incremental** | Matbench Discovery, *Nat. Mach. Intell.* 2025, 10.1038/s42256-025-01055-1 names the triangle/regression-classification misalignment but does **not** test whether it dissolves for modern UIPs. | Spearman(MAE, F1) = −0.929 falsifying the universal slogan is defensible but thin. **Use as guardrail/framing, not a standalone paper.** |
| **Proper conformal stability decision** (split/Mondrian conformal classifier) | **novel** | Conformal-for-MLIP exists only for **regression** (arXiv:2208.08337; 2510.00721); PCM 2603.12183 uses Lean-4 certificates, not a conformal classifier with finite-sample coverage on the stable call. | Genuinely unoccupied; also cures the workspace's own "split-conformal" overclaim (§3). |

**Net:** drop MT4; reposition V6 strictly as a decision-precision head-to-head vs the now-npj-published
2507.21297; promote MT28 (canonicalized) as flagship but **explicitly differentiate from PCM
2603.12183**; keep chemistry/prototype-stratified-DAF and proper-conformal as complementary follow-ons;
**revive MT29 as a rank-reordering-map paper** now that the data gate is shown false; demote V2 to framing.

---

## 3. 现有资产是否鲁棒 (Asset robustness) — PARTIAL

**Verified-robust:**
- **Data pipeline is real and on disk** (independently re-confirmed today): 256,963-row WBM predictions
  for 4 modern UIPs + 4 stage-0 models + full ground-truth hull/prototype/formula columns.
- **V6 disagreement asset is the strongest single artifact.** Spearman(disagreement, |consensus error|)
  = 0.714 (per-model-mean 0.900); abstention precision 0.741→0.774 at 70% coverage, bootstrap 95% CI on
  gain [0.031, 0.035] excludes 0; **shuffle control ≈0.739 (clean null).** V6b honest negatives (routing
  fails, naive averaging hurts) raise credibility. *Caveat:* the underlying signal is now scooped/published
  (2507.21297), so the asset's value is the *decision-layer head-to-head*, not the signal.
- **Red-team audit (`research/audits/INDEPENDENT_RED_TEAM_AUDIT_2026-06-17.md`) is rigorous and
  self-consistent**; its P0/P1 findings reproduce against the JSON/CSV artifacts and are the authoritative
  current state of this workspace.
- All scoped Python compiles (`py_compile` clean per the audit's own re-run).

**Thin / unverified / broken (must fix before any claim):**
1. **P0 — MT28 calibration internally contradictory.** `findings-MT28-conformal-calibration.md` claims
   isotonic beats margin for *all four* models; `findings-MT28-calibration-audit.md` /
   `results/MT28/mt28_calibration_result.json` show **m3gnet iso_gain = −0.197 (CI [−0.287, −0.106],
   i.e. harmful)** at 70% coverage, MACE ≈0, and several sign flips between the two protocol JSONs.
   The "all models / model-agnostic" headline is **not stable across the workspace's own scripts.**
   Publication-blocking.
2. **P0 — MT4 stale numbers.** Manuscript-readiness doc cites ρ=0.90 and "1000×"; the final 100-structure
   batch is ρ_ORB=0.33 (CI [0.14, 0.48]), mean drift gap ~52.7×. Overstated.
3. **P0 — "Manuscript Ready / Gates Cleared" is false** (contradicted by the workspace's own GAP-FIX plan
   and the broken strata artifact). Defensible posture: *promising Stage-1; manuscript gate blocked.*
4. **P0 — strata/DAF supplement is a traceback.** `redteam/mt28_strata_daf_2026-06-16.md` ends in
   `KeyError: 'orb'`. Root cause per the audit: `scripts/supplement_strata_daf.py` loads the prediction
   column as `e_form_pred` but later accesses `df[model]`. **One-line fix**; not data-gated.
5. **P1 — yield collapse confound (the single most important missing control).** At 70% coverage the
   calibrated filter calls far fewer stable candidates (MACE 401 vs margin 13,867; CHGNet 5,371 vs 24,146;
   ORB 4,721 vs 11,402). Precision-only reporting overstates utility. **Missing: matched stable-call yield.**
6. **P1 — "split-conformal" is an overclaim.** `mt_v28_conformal_calibration.py` fits isotonic regression
   and selects by `|p−0.5|`; no conformal scores, no quantile threshold, no finite-sample coverage. Rename,
   or implement a real conformal procedure.
7. **P1 — MT29 status contradictory** across three docs (null vs DATA_GATE_BLOCKED vs "disproved").
   Corrected defensible statement (per §1): *unique-prototype rank is a clean NULL (τ=ρ=1.0); broader
   prototype/family/round-stratified rank reordering is **unrun but data-available on disk**, not gated.*
8. **P1 — not workspace-self-contained.** Scripts hardcode `~/mt_stage0`, `~/mt_uip`, absolute output
   paths; MD velocity init unseeded (only geometry rattle is seeded). Add a `DATA_ROOT` + result manifest
   (cmd, script SHA, input SHAs, seed, output SHA, package versions) before external review.

**Missing controls overall:** (a) `|hull margin|` baseline at matched coverage for the selective-prediction
claim; (b) matched stable-call yield; (c) per-stratum bootstrap interaction test; (d) a real conformal
coverage check; (e) reproducibility manifest; (f) explicit differentiation from PCM 2603.12183.

---

## 4. 剩余可发表方向 (Remaining publishable directions) — surviving + required wedge

1. **MT28 (canonicalized) — risk-coverage selective prediction on the stability decision.**
   *Required wedge:* one canonical metric (per-model risk-coverage curve + AURC for the binary stable
   call), abstention scored by (a) `|predicted hull margin|`, (b) split-isotonic calibrated p_stable,
   (c) cross-MLIP disagreement, all at **matched coverage AND matched stable-call yield**, reporting
   precision, recall, called-stable count, and DAF. Headline falsifiable test: *does any non-trivial
   confidence beat `|hull margin|` AURC with a 1000-bootstrap 95% CI excluding 0, at equal coverage and
   equal yield?* Must explicitly position against **PCM 2603.12183** (different lens: certificates +
   AUC-ROC, no margin baseline, no fixed-coverage curve). Resolves P0 (one protocol) and P1 (yield) at once.
   **SURVIVES.**

2. **Chemistry-/prototype-stratified DAF under abstention.** *Required wedge:* DAF-vs-coverage and
   precision-vs-coverage **stratified** by anion class / element group and (newly enabled)
   `unique_prototype` and WBM round — testing the **stratum × coverage interaction**: does abstention
   disproportionately help the near-zero-hull "triangle-of-peril" strata and no-op elsewhere? Complementary
   to PCM (AUC-ROC, no abstention/DAF). Fix the broken supplement first. **SURVIVES.**

3. **V6 repositioned — disagreement vs hull-margin head-to-head on the decision.** *Required wedge:* take
   2507.21297's (now npj-published) metric at face value and answer the question it skipped — on the WBM
   stability decision, does disagreement beat the free `|hull margin|` signal at fixed coverage AND fixed
   yield, with the shuffle null cleanly separated? Reuses V6/V6b scripts. **SURVIVES as a delta**, not a
   standalone novelty.

4. **Proper conformal stability decisions.** *Required wedge:* implement a real split-/Mondrian-conformal
   classifier (nonconformity = signed hull margin or calibrated p_stable) with distribution-free coverage,
   and ask whether the workspace's mislabeled "conformal" claim was *accidentally true*. Cures the overclaim;
   genuinely novel for classification. **SURVIVES.**

5. **MT29 revived — rank-reordering map under prototype/family/round splits.** *Required wedge:* the data
   gate is false (§1); deliver the *quantified rank-reordering map* (per-model rank displacement with
   bootstrap rank CIs) across full / unique-prototype / chemistry-family / WBM-round splits — the MT29
   prereg deliverable, distinct from Matbench's known full-vs-dedup metric shift. **CONDITIONAL SURVIVE**
   (run the round/family spike; if τ stays ≈1 everywhere it collapses to a reassuring null).

**Dropped/demoted:** MT4 (scooped by 2412.11569/ICML 2025); V2 (incremental — keep as guardrail framing).

---

## 5. 如何立项 (How to establish) — Stage-0 go/no-go

**Stage-0 spike (1–2 CPU sessions, no GPU, no downloads):**
Build one canonical script `mt28_riskcov.py` over the on-disk WBM data that, for each of the 8 models,
computes the risk-coverage curve + AURC for the binary stable call under three confidence signals —
`|predicted hull margin|`, split-isotonic p_stable, cross-MLIP disagreement — at **matched coverage AND
matched stable-call yield**, with 1000-bootstrap 95% CIs on the AURC/precision-gain *difference vs the
hull-margin baseline*. Reuse `mt28_calibration_audit.py` + `v6_disagreement_reliability.py` plumbing; add
a `DATA_ROOT` env and a result manifest (cmd, script SHA, input SHAs, seed, output SHA, package versions).

**First, fix the two cheap blockers** (both trivial): the `scripts/supplement_strata_daf.py` column-name
bug, and collapse the two contradictory MT28 protocol JSONs into one canonical protocol (archive the other
as a sensitivity analysis).

**Preregistration (commit before running the head-to-head):**
- Primary metric: AURC of the binary stable call per model per confidence signal.
- Primary hypothesis: ≥1 non-trivial signal beats `|hull margin|` AURC at matched coverage+yield.
- Secondary: precision/recall/called-stable/DAF at coverage ∈ {0.5, 0.7, 0.9}.
- Controls: matched yield; shuffle/permutation null; per-model bootstrap CI; explicit PCM 2603.12183
  positioning paragraph.
- Strata (direction 2 / MT29 spike): `unique_prototype`, anion class, binary/ternary+, WBM round; interaction test.

**Kill criteria:**
- **MT28 KILL** if, at matched coverage AND matched stable-call yield, no confidence signal beats
  `|hull margin|` AURC for ≥2 of the 8 models with a 1000-bootstrap 95% CI excluding 0. (Real risk:
  current evidence is ORB-only-robust and yield-confounded — m3gnet iso_gain is already negative.)
- **Strata KILL** if the stratum × coverage interaction CI on the gain *difference* includes 0.
- **V6-repositioned KILL** if disagreement does not beat `|hull margin|` at fixed coverage+yield with CI
  excluding 0, OR >5% of shuffles match the real gain.
- **Conformal KILL** if conformal DAF/precision at target coverage is statistically indistinguishable from
  the hull-margin threshold AND coverage validity is the only contribution.
- **MT29 KILL** if Kendall-τ stays >0.9 with no model moving >1 rank (CI excluding 0) across family/round
  splits (downgrade to a reassuring null audit).

**Target venue:** *Digital Discovery* (RSC) primary — framed as a reliability **audit of existing models,
no new model trained**; *Machine Learning: Science and Technology* (MLST) fallback for the conformal angle;
**NeurIPS 2026 Evaluations & Datasets (ED) Track** (confirmed live — explicitly treats "evaluation as a
scientific object of study," scope includes auditing/red-teaming/metrics) is the ideal home for the MT29
rank-reordering map and a credible fast lane for the V6 head-to-head.

---

## 6. 新的更好方向 (New better directions) — ranked

1. **Risk-Coverage Audit of Stability-Decision Selective Prediction on Matbench Discovery (canonicalize
   MT28).** *Wedge:* single canonical AURC/risk-coverage metric for the binary stable call, `|hull margin|`
   baseline mandatory, matched coverage + matched yield first-class, explicit differentiation from PCM
   2603.12183. *Data:* on-disk ~73 MB (8 models, n=256,963), free, no-auth. *Kill:* §5 MT28 kill.
   *Venue:* Digital Discovery (RSC) primary; MLST fallback.
   — Highest ROI: turns the publication-blocker into the central question, pre-empts the yield confound by
   design, unscooped vs 2510.00721/2507.21297, and only *partially* contested by PCM (different lens).

2. **Chemistry-/Prototype-/Round-Stratified Discovery Acceleration Under Abstention (fix + promote the
   broken strata_DAF).** *Wedge:* DAF-vs-coverage and precision-vs-coverage stratified by chemical family,
   `unique_prototype`, and WBM round; report the stratum × coverage interaction, not a global number.
   *Data:* same on-disk WBM; strata from `formula`/`protostructure_spglib`/`material_id` already present.
   *Kill:* §5 strata kill. *Venue:* Digital Discovery (RSC).
   — Complementary to PCM 2603.12183 (AUC-ROC, no abstention); one-line bug-fix unlocks it.

3. **Matbench-Discovery Rank-Reordering Map (revive MT29 now that the data gate is shown false).** *Wedge:*
   per-model rank displacement with bootstrap rank CIs across full / unique-prototype / chemistry-family /
   WBM-round splits — the deliverable Matbench's own full-vs-dedup numbers do not provide. *Data:* on-disk
   WBM summary (prototype + round metadata confirmed present). *Kill:* §5 MT29 kill. *Venue:* NeurIPS 2026
   ED Track / Digital Discovery.
   — Newly feasible this pass; positions against MLIP Arena (2509.20630) and OMat24 prototype-overlap notes.

4. **Ensemble-Disagreement vs Hull-Margin Head-to-Head Selective-Prediction Benchmark (reposition V6
   against npj 2026 / 2507.21297).** *Wedge:* port that metric to the WBM stability decision and ask the
   question it skipped — does disagreement beat the free hull-margin signal at fixed coverage+yield?
   Includes the already-prototyped shuffle null. *Data:* on-disk 4-UIP preds + hull. *Kill:* §5 V6 kill.
   *Venue:* MLST / Digital Discovery; or NeurIPS 2026 ED Track.
   — Converts a now-published scoop into a citable head-to-head.

5. **Proper Conformal Stability Decisions with Finite-Sample Coverage (retire the "conformal" overclaim by
   actually doing it).** *Wedge:* real split-/Mondrian-conformal classifier (nonconformity = signed hull
   margin / calibrated p_stable), per-chemistry coverage. *Data:* on-disk WBM; MAPIE (pip, CPU-light).
   *Kill:* §5 conformal kill. *Venue:* MLST (methods-forward); Digital Discovery fallback.
   — Cures a flagged overclaim and is genuinely novel for classification.

(Drop: MT4 standalone. Demote: V2 → guardrail framing inside direction 1.)

---

## 7. Sources

Cited competing / supporting work (verdicts in §2), all fetched or search-confirmed this pass:

- Matbench Discovery — *Nat. Mach. Intell.* 7, 836–847 (2025), DOI 10.1038/s42256-025-01055-1; leaderboard
  https://matbench-discovery.materialsproject.org/ ; package https://pypi.org/project/matbench-discovery/
- **Proof-Carrying Materials: Falsifiable Safety Certificates for MLIPs** — arXiv:2603.12183 (Mar 2026),
  https://arxiv.org/abs/2603.12183 — *partial scoop of MT28's selective-prediction-for-stability framing
  (CHGNet/MACE/TensorNet, risk model AUC-ROC 0.938, bootstrap CIs, Lean-4 certs); no `|hull margin|`
  baseline, no fixed-coverage risk-coverage curve.*
- **Heterogeneous Ensemble … Universal Uncertainty Metric for Atomistic Foundation Models** — Liu et al.,
  arXiv:2507.21297 (Jul 2025) → **npj Comput. Mater. 2026, s41524-025-01905-x**,
  https://www.nature.com/articles/s41524-025-01905-x — *scoops V6's disagreement-as-uncertainty signal.*
- **The dark side of the forces (non-conservative force models)** — Bigi/Langer/Ceriotti, arXiv:2412.11569
  (Dec 2024) → **ICML 2025, PMLR 267**, https://arxiv.org/abs/2412.11569 — *scoops MT4 (ORB NVE
  non-conservation/heating + diagnostic metric + MTS remedy).*
- Flexible Uncertainty Calibration for MLIPs — arXiv:2510.00721 (Oct 2025), https://arxiv.org/html/2510.00721
  — *regression quantiles only; not the stability decision.*
- A critical examination of compound stability predictions from ML formation energies — npj Comput. Mater.
  2020, arXiv:2001.10591, https://arxiv.org/abs/2001.10591 — *"good formation energy ≠ good stability"; no
  hull-margin selective signal (confirmed NOT prior art for the MT28 baseline).*
- Bias in Universal MLIPs and its Effects on Fine-Tuning — arXiv:2603.10159 (2026),
  https://arxiv.org/abs/2603.10159 — *about fine-tuning bias, NOT rank reordering (confirmed NOT an MT29 scoop).*
- Uncertainty-Driven Reliability: Selective Prediction … — arXiv:2508.07556 (2025) — *confirmed generic ML,
  no materials/MLIP/Matbench connection (NOT a scoop).*
- MLIP Arena — arXiv:2509.20630 (Sep 2025), https://github.com/atomind-ai/mlip-arena
- Conformal regression baselines for MLIPs — arXiv:2208.08337
- NeurIPS 2026 Evaluations & Datasets (ED) Track — https://blog.neurips.cc/2026/03/23/introducing-the-evaluations-datasets-track-at-neurips-2026/
  — *confirmed live; "evaluation as a scientific object of study," scope includes auditing/red-teaming/metrics.*
- Data: Figshare 22715158 (Data Files), Figshare 28187990 (Model Predictions); free/no-auth;
  `MBD_CACHE_DIR` default `~/.cache/matbench-discovery`.

Internal artifacts cross-checked this pass: `research/audits/INDEPENDENT_RED_TEAM_AUDIT_2026-06-17.md`,
`research/findings-MT28-calibration-audit.md`, `research/findings-MT29-rank-fragility.md`,
`research/findings-MT28-MT29-stage0-readiness-2026-06-16.md`, `research/MT28-preregistration-2026-06-16.md`,
`research/MT29-preregistration-2026-06-16.md`, `research/findings-V6-disagreement-reliability.md`,
`research/findings-V6b-disagreement-routing.md`, and the on-disk assets
(`~/mt_uip/*_pred.csv`, `~/mt_stage0/data/*.csv.gz`, `~/.cache/matbench-discovery/wbm/`; WBM summary
n=256,963 with prototype/round/chemistry columns independently verified 2026-06-21).
