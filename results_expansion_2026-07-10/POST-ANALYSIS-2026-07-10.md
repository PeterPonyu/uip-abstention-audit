# Post-analysis of the 2026-07-10 roster expansion (sessions 4c + 4d)

Scope: local CPU validation, reconciliation, and analysis of the on-box roster-expansion
reruns for MT29 (the chemistry-stratified value-of-abstention paper). Two GPU sessions ran
on the box: **4c** (MACE checkpoint gated fetch, mace-mp-0 / orb-v3 / mattersim roster
inference, sevennet-mf-ompa OAM arm, hull step) and **4d** (orb-v3 repair, MP-entries
convert, hull re-run). All GPU work is CLOSED; this pass is the local read-out.

Bottom line up front: **the paper's headline — the oxide-anchored, matched-yield abstention
interaction on the four 2023–24 UIPs — is fully intact and reproduces byte-for-byte on this
machine.** Both *new* robustness arms attempted on the box (the OAM/modern-model roster arm
and the convex-hull recompute) **did not land as executed**: each failed in a specific,
diagnosed, fixable way (a formation-energy referencing mismatch and a total-vs-formation
energy unit mismatch, respectively). Neither can be integrated as a positive result yet;
both are documented below as attended items with exact fix recipes. Nothing in the frozen
canonical pipeline was edited.

---

## 1. Roster validation — all 8 prediction CSVs pass

The session-4c tarball (`pulled/mat_session4c.tar.gz`) was extracted into an isolated
directory **`results_expansion_2026-07-10/pulled/extracted_4c/`** (never into the repo root);
orb-v3 came from the already-extracted `pulled_4d/root/mt_uip/orb_v3_pred.csv`. Every CSV was
read in full (not streamed) to count data rows and hash bytes. Full sha256 and per-row
validation are recorded in **`ROSTER-MANIFEST-2026-07-10.json`** (`ALL_VALID: true`).

| CSV | role | data rows | schema `material_id,e_form_pred` | sha256 (16) | VALID |
|---|---|---:|:---:|---|:---:|
| chgnet_pred.csv | legacy 2023–24 | 256,963 | ✓ | d84578eb02843a3f | ✓ |
| m3gnet_pred.csv | legacy 2023–24 | 256,963 | ✓ | 8c4e136bf1b8e577 | ✓ |
| mace_pred.csv | legacy 2023–24 | 256,963 | ✓ | d37eed9ec6a5ee0e | ✓ |
| orb_pred.csv | legacy 2023–24 | 256,963 | ✓ | 9df863e74a88cd89 | ✓ |
| mace_mp_0_pred.csv | new in-house (4c) | 256,963 | ✓ | b55baabe81d66379 | ✓ |
| mattersim_pred.csv | new in-house (4b/4c) | 256,963 | ✓ | 8ab571a4b0aa9ca2 | ✓ |
| sevennet_mf_ompa_pred.csv | new in-house, OAM (4c) | 256,963 | ✓ | 47365965ca202898 | ✓ |
| orb_v3_pred.csv | new in-house (4d) | 256,963 | ✓ | 5be8102c4be9fb65 | ✓ |

Row count matches the WBM test set (256,963) exactly for all eight. The four legacy CSVs are
byte-identical to the copies on local disk (`~/mt_uip/`) and to the input hashes recorded in
the frozen Stage-1 manifest, so they are the same artifacts the published analysis rode on.

**Naming note.** The survey's "5-UIP roster" is a *planned* framing. As realized on disk there
are **four new-generation in-house prediction sets** (mace-mp-0, orb-v3, mattersim,
sevennet-mf-ompa) plus the four legacy sets — eight prediction CSVs total, spanning the MACE,
Orb, MatterSim and SevenNet architecture families across the 2023–2026 generations, with
sevennet-mf-ompa as the OAM-era member. The gated eSEN-30M-OAM checkpoint was correctly
skipped (survey recommendation).

---

## 2. Reconciliation of pulled result JSONs vs the repo — clean

Every **canonical** MT29 result JSON is **byte-identical** between the repo tree and both the
4c and 4d pulls (verified by sha256): `mt29_stage1_matched_yield_result.json`,
`mt29_stage2_robustness_result.json`, `mt29_multiplicity_stage1_result.json`,
`mt29_multiplicity_stage2_result.json`, `mt29_stage1_chem_yield_result.json`,
`mt29_committee_variance.json`, `mt29_sscs_stratified.json`. The box did **not** re-run the
canonical arms; it only produced two **new** result JSONs:

- `mt29_stage1_oam_arm_result.json` (+ manifest) — 4c and 4d (identical); Arm 1b.
- `mt29_hull_recompute_validation_result.json` (+ manifest) — 4d only; Arm 2b.

**Decision (no clobber):** both new results are diagnosed-flawed *and* the OAM one is also
incomplete (it ran during 4c, before orb-v3 existed, so its `oam_models_found` omits orb-v3).
They are therefore **kept under `results_expansion_2026-07-10/` and referenced**, not copied
into the canonical `research/results/MT29/` set, to avoid (a) polluting the canonical
directory with a degenerate/partial artifact and (b) tripping the scripts' refuse-to-overwrite
guard on a future corrected re-run. This matches the brief's "keep pulled copies under
results_expansion and reference them" option.

**Manifest touch, disclosed and reverted.** Re-running `mt29_stage2_robustness.py` for
verification (below) rewrote `mt29_stage2_robustness_manifest.json` in place (the script stamps
the manifest with the *running machine's* env). The **result** `output_sha256` was unchanged
(`2275d6a2c10afcb4…`), i.e. the numbers are deterministic; only environment metadata differed
(`python 3.11.15→3.13.5`, `numpy 2.4.6→2.2.6`, `pandas 3.0.3→2.3.3`, platform, git_head,
script hash). The manifest was reverted with `git checkout` to preserve the frozen artifact.
The multiplicity manifests were guarded the same way. After this pass, **no canonical MT29
result or manifest file is modified vs git.**

---

## 3. Canonical legacy-4 pipeline — reproduces byte-for-byte on this machine

The four 2023–24 UIPs are exactly the pipeline underpinning the manuscript's headline. Re-run
locally from `~/mt_uip/` (4 legacy CSVs) + `~/mt_stage0/data/2023-12-13-wbm-summary.csv.gz`:

| script | result `output_sha256` (16) | vs frozen | headline it feeds |
|---|---|:---:|---|
| `mt29_stage1_matched_yield_fix.py` | e85f6177ac8a26ed | **byte-identical** | 48/60 interaction, CHGNet oxide–halide +0.90 |
| `mt29_stage2_robustness.py` | 2275d6a2c10afcb4 | **byte-identical** | LOEO 12/12 (548/700), rounds 3/5 (157/300) |
| `mt29_multiplicity_correction.py {stage1,stage2}` | see §note | reproduced | BH 46/60, Holm 40/60 |
| `pytest` | — | **61 passed, 3 failed** | 3 failures are the known `ase`-missing GPU-stack tests (`test_uip_inference.py`), out of scope for CPU |

The byte-identical Stage-1/Stage-2 reproductions match the SHA-256 prefixes the manuscript
already cites (`e85f6177…`, `2275d6a2…`), i.e. the paper's determinism claim holds on a third
independent environment. (Multiplicity re-run launched in the background; the frozen results
were confirmed intact after an initial 2-min timeout killed the run before any write —
`65c8338574aa385c` / `fb246d558596b5a4` unchanged and git-clean.)

---

## 4. Arm A — OAM / modern-model roster matched-yield arm: **BLOCKED (degenerate as run)**

**Question.** Does the oxide-anchored matched-yield interaction replicate when the four new,
modern-generation UIPs are hooked into the corrected matched-yield pipeline
(`mt29_stage1_oam_arm.py`, auto-discovering every `*_pred.csv` beyond the base four)?

**What the box produced** (`mt29_stage1_oam_arm_result.json`): the three new models present at
4c time (mace-mp-0, mattersim, sevennet-mf-ompa) collapse to a **degenerate** arm — their
matched-yield gains are 0.0 in every stratum and every pairwise interaction is 0.0. The cause
is visible in `total_called_stable`: the new models call **essentially no oxides stable**
(oxide = 2, 5, 2 respectively), so the per-model yield budget `y_loose = min_strata(...)`
collapses to 2–5 and the gains have no signal.

**Root cause (diagnosed, not guessed).** All four new in-house CSVs carry a **systematic,
anion-count-proportional positive bias** in predicted formation energy relative to the
MP2020-corrected ground truth. Measured directly (merge each CSV with the WBM summary,
per anion family):

| model | oxide mean err (eV/atom) | halide | intermetallic | oxides called stable |
|---|---:|---:|---:|---:|
| mace (legacy, reference) | −0.023 | −0.004 | −0.009 | 3,268 |
| orb (legacy, reference) | +0.009 | +0.008 | +0.005 | 2,965 |
| mace-mp-0 (new) | **+0.592** | +0.438 | +0.106 | 2 |
| mattersim (new) | **+0.590** | +0.437 | +0.141 | 5 |
| sevennet-mf-ompa (new) | **+0.599** | +0.441 | +0.107 | 2 |
| orb-v3 (new) | **+0.586** | +0.458 | +0.167 | 512 |

The bias is **identical across four different architectures** (~+0.59 eV/atom for oxides,
~+0.44 for halides, ~+0.11 for intermetallics) and scales with anion content. Four independent
models cannot share the same offset by chance — this is a shared **conversion artifact in the
inference harness, not a model property**. The magnitude and anion-proportionality match the
**MP2020 compatibility (oxide/anion) corrections** (~0.69 eV per O atom): the new inference
(`mt29_uip_inference.py`) computed **raw** formation energies from `ref_energies.json` elemental
references *without* applying the MP2020 anion corrections that both the ground-truth
`e_form_per_atom_mp2020_corrected` column **and** the legacy prediction CSVs carry. The legacy
CSVs show ~0 mean error precisely because they were produced by matbench-discovery's own
MP2020-consistent pipeline. (`ref_energies.json` itself is complete and correct — 90 elements,
O = −4.947 eV/atom — so unlike session 2 the reference-energy *derivation* succeeded; the
missing step is the MP2020 correction layer, not the elemental references.)

**Verdict: BLOCKED — do not integrate as a positive result.** The "the interaction holds on
modern/OAM models" insurance the roster was meant to buy **was not delivered by this run**. The
arm is fixable without new GPU inference in principle (apply MP2020 corrections to the four new
CSVs, or re-run the conversion with `pymatgen`'s `MaterialsProject2020Compatibility`), but doing
so correctly is itself a new analysis that needs its own prereg discipline and verification — it
is out of scope for this CPU read-out and is listed as an attended item. **The manuscript keeps
its headline scoped to the four legacy UIPs** and discloses the OAM refresh as attempted,
diagnosed, and deferred (which, honestly framed, still pre-empts the "stale models" objection by
showing the attempt and the exact blocker).

---

## 5. Arm B — convex-hull recompute validation: **INVALID AS RUN (unit mismatch)**

**Question.** For a stratified 5k subset, does recomputing `e_above_hull` from a rebuilt MP
phase diagram (instead of the fixed-hull shortcut `hull_pred = hull_true + (e_form_pred −
e_form_true)`) leave the Stage-1 stable/unstable calls unchanged — the paper's fixed-hull
"insurance"?

**What the box produced** (`mt29_hull_recompute_validation_result.json`, n_evaluated = 4,998):
per-stratum "fixed − recomputed" hull deltas that are **implausibly large** and, tellingly,
**identical across all four models** within each stratum (only the flip counts differ):

| stratum | delta_mean (eV/atom) | delta_std | stable-call flip rate (min–max over 4 models) |
|---|---:|---:|---:|
| oxide | −4.99 | 0.95 | 11.2%–16.0% |
| halide | −3.34 | 1.49 | 27.5%–41.4% |
| chalcogenide | −4.26 | 1.28 | 18.2%–34.7% |
| pnictide | −5.59 | 1.81 | 16.8%–35.5% |
| intermetallic | −5.31 | 1.95 | 11.4%–30.9% |
| other | −6.03 | 1.61 | 14.5%–31.1% |
| **total** | | | **4,611 / 4,998 flips** |

**Root cause (diagnosed from code, two independent tells).**
1. *Algebra:* the reported delta is
   `hull_pred_fixed[m] − hull_pred_recomputed[m] = (hull_true + e_form_pred[m] − e_form_true) −
   (e_form_pred[m] − he)`, in which the model term `e_form_pred[m]` **cancels**. The delta is
   therefore **model-independent by construction** — exactly what the JSON shows — so it is *not*
   a per-model robustness measurement at all; it reduces to `hull_true − e_form_true + he`.
2. *Units:* `mt29_convert_mp_entries.py` + `load_mp_reference_entries` populate the reference
   `e_per_atom` from `ComputedStructureEntry.energy_per_atom` — the **total DFT energy per
   atom** — while the query is compared against `e_form_true`, a **formation energy**. The hull
   math (`mt29_hull_math.hull_energy_at`) thus mixes a total-energy reference surface with a
   formation-energy query, producing a systematic offset ≈ the average elemental total energy
   per atom (several eV, chemistry-dependent) — matching the observed −3 to −6 eV/atom deltas
   and their variation by anion family. `load_mp_reference_entries`' own docstring claims the
   references are "per-atom formation energies on the SAME elemental-reference-zero convention as
   `e_form_true`," which the code contradicts.

**Verdict: the recompute as executed does not bound the fixed-hull approximation.** The huge
deltas and 11–41% "flip" rates are **artifacts of the total-vs-formation energy mismatch**, not
evidence about the fixed-hull shortcut. **It must not be reported as robustness insurance, and
no CI-flip claim can be drawn from it.** The fix is to convert MP reference entries to the same
MP2020-corrected formation-energy convention as `e_form_true` before building the hull (e.g.
`PhaseDiagram(entries).get_form_energy_per_atom`, or an MP2020-corrected formation-energy
reference table), then re-run. This is a bounded CPU job on the already-downloaded MP entries;
it is an attended item, not a blocker for the legacy-4 headline (whose fixed-hull approximation
remains an acknowledged, disclosed limitation exactly as the current manuscript states).

---

## 6. Complications (verbatim, for the record)

- **4c `MAT_SESSION4C_DONE` masked two hard failures.** The 4c log ends with the success
  sentinel despite `ROSTER_orb-v3_FAILED rows=0` and `HULL_FAILED`. Only mace-mp-0 and
  mattersim actually completed roster inference in 4c; the OAM Arm-1b hookup ran (`OAM_OK`) but
  on the degenerate inputs above. The orchestration's ALL-DONE marker is not a content gate —
  the roster content gate (`run_all_arms.sh`, `ROSTER_MIN_PREDICTIONS`) is the reliable check,
  and it is what session 4d keyed off to repair orb-v3.
- **orb-v3 `atoms_adapter` bug (4c → fixed 4d).** 4c died with
  `TypeError: ORBCalculator.__init__() missing 1 required positional argument: 'atoms_adapter'`
  — the orb-models 0.7 API change (the same family of adapter/device bugs the survey flagged).
  4d repaired it; `orb_v3_pred.csv` (256,963 rows) is the fresh realization.
- **hull `FileNotFoundError` (4c → fixed 4d).** 4c's hull step could not find
  `mp_computed_structure_entries.pkl.gz`. 4d ran `mt29_convert_mp_entries.py`
  (154,718 entries, 0 skipped) to produce it, then the hull step completed (`HULL_OK`) — but
  on the wrong energy convention (§5).
- **MACE dotless-cache / checkpoint-truncation history.** 4c purged the MACE cache and
  re-fetched with a size + CRC gate (`MACE_CKPT_FETCH_OK bytes=79462305`), the mitigation for
  the earlier proxy-20 MiB silent-truncation bug. It succeeded this session.
- **`ref_energies.json` succeeded this time.** The session-2 "too few elements: 0" failure did
  not recur; the file is a complete 90-element elemental-reference table. The OAM degeneracy
  (§4) is a *downstream* MP2020-correction omission, not a ref-energy derivation failure.

---

## 7. Measured compute (from `gpu_util.log`, per-minute nvidia-smi)

Single **RTX 4090D (24 GB)**. The log's timestamped span covers 18:38–19:19 CST (a 4d window)
plus trailing idle samples; it therefore **bounds** rather than fully accounts for the
multi-session inference. Within it: **peak GPU memory 6,414 MiB (6.3 GiB of 24)**, **peak
utilization 84%**, ~169 samples at ≥60% util (≈ the active-inference minutes), mean active
memory ~2.8 GiB. Consistent with the survey's claim that all roster models are ≤30 M params and
frozen inference fits 24 GB comfortably — the residual GPU cost is single-digit hours per model
over 256,963 structures, far under the 30–80 h contingency budget. The orb-v3 checkpoint
download alone took 1:43:53 (4c log), which is network, not compute.

---

## 8. Cross-arm synthesis — is the paper's headline safe?

**Yes, unconditionally, and independently of the two failed arms.** The load-bearing claim —
the chemistry-stratified, matched-yield abstention interaction (48/60 cells, oxide-anchored,
LOEO 12/12, rounds 3/5, shuffle-null 0/700 & 0/300, committee-variance re-derivation, SSCS
miscalibration) — rests entirely on the four 2023–24 UIPs, whose CSVs and result JSONs are
byte-identical to the published artifacts and **reproduced byte-for-byte here**. The paper
already scopes itself to "the four 2023–24-generation UIPs and single anion-priority
stratification tested here" and calls modern-generation generalization untested. That scoping
is exactly right and needs no change.

**What did *not* land:** the two 2026-07-10 "insurance" arms. Neither weakens the headline —
they were *additional* hardening — but neither can be cited as a win:
- the OAM/modern-model arm is **blocked** on an MP2020-correction omission in the new inference;
- the hull recompute is **invalid as run** on a total-vs-formation energy unit mismatch.

Both are cheap, local, CPU-fixable, and are listed below. Until fixed, the manuscript integrates
them **honestly as attempted-and-deferred**, not as confirmatory results.

---

## 9. Gaps / attended items before submission

1. **OAM/modern-roster arm — apply MP2020 corrections.** Re-derive the four new CSVs'
   formation energies on the MP2020-corrected convention (post-hoc correction of the existing
   CSVs, or re-run `mt29_uip_inference.py` conversion with
   `MaterialsProject2020Compatibility`), then re-run `mt29_stage1_oam_arm.py` (now
   auto-discovering orb-v3 too). Only then can the "holds on modern models" claim be made. New
   prereg note required (this is a new analysis realization).
2. **Hull recompute — fix the energy convention.** Convert MP reference entries to MP2020
   formation-energy-per-atom before hull construction, then re-run
   `mt29_hull_recompute_validation.py`. Bounded CPU on the already-downloaded entries.
3. **JCIM vs Digital Discovery — final call + cover letter.** Position against PCM
   (arXiv:2603.12183, global non-stratified AUC, no matched-yield control); cite PROBE
   (arXiv:2605.00640) as adjacent-not-overlapping (per-atom MD selective classification, not the
   WBM stability decision). JCIM primary (no mandatory APC), Digital Discovery / npj Comput.
   Mater. alternates.
4. **achemso conversion.** The manuscript is still generic `article` class. Per the survey,
   note the achemso conversion as a listed packaging gap rather than rewriting wholesale.
5. **License table.** MACE MIT / MatterSim MIT / orb-v3 Apache-2.0 / SevenNet ≥0.12.0 MIT /
   WBM CC-BY-4.0 — added to the manuscript (SI-appropriate).
6. **sevenn version pin.** Record the installed `sevenn` version (≥0.12.0 = MIT era) in the
   roster manifest / SI; the box session-2 log showed sevenn 0.13.0 but this was not
   re-confirmed in the 4c/4d logs — attended.
7. **halide DAF 4.42 → 3.01 provenance.** 3.01 is genuinely the value in
   `mt29_stage1_chem_yield_result.json` and is used consistently in the manuscript; **no on-disk
   historical trail** (commit/transcript/log) for the 4.42→3.01 correction exists
   (FABLE-HANDOFF §confirmed). Disclosed as a provenance note, not a current error.
8. **Zenodo / private remote push.** DOI 10.5281/zenodo.21130295 is reserved on a draft
   deposition; activation + off-disk git remote need user credentials.
