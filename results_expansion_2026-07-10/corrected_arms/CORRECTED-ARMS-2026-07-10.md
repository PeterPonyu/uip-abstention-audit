# Corrected insurance arms — hull recompute + OAM/modern roster (2026-07-10, local CPU)

Scope: the two 2026-07-10 "insurance" arms that the on-box sessions (4c/4d) produced in a
diagnosed-broken form (POST-ANALYSIS-2026-07-10.md §4 OAM, §5 hull) are here **re-run
correctly, entirely locally on CPU** (the GPU box 18943 was off and was not needed). Both
now land. Every number below is printed by a script under this directory; no frozen script
or canonical MT29 result JSON was edited.

**Bottom line:**
- **Hull recompute: FIXED and PASSES.** The fixed-hull approximation is validated — after
  putting the MP reference surface on the same MP2020 formation-energy convention as the
  query, recomputing the convex hull reproduces the published `e_above_hull` to
  ~0.001 eV/atom and changes the stable/unstable call for only **13 / 4,998 structures
  (0.26%)** (was 4,611 / 4,998 with the total-vs-formation unit bug).
- **OAM / modern roster: FIXED; verdict MIXED (honest positive-with-a-dissenter).** After
  restoring the omitted MP2020 anion corrections, the four new-generation models call
  1,500–2,200 oxides stable (was 2–5; degeneracy gone). The paper's oxide-anchored
  matched-yield abstention structure **reproduces on 3 of the 4 modern models — mace-mp-0,
  mattersim, and the OAM-era sevennet-mf-ompa** (oxide gain > every other stratum, 5/5) —
  and **does not** reproduce on **orb-v3** (0/5; uniformly negative matched-yield gains, a
  genuine confidence-miscalibration in this task).

---

## Setup

- venv: `materials-mlip-research/.venv-local` (python 3.13.5) — pymatgen 2026.5.4,
  matbench-discovery 1.3.1, pandas 3.0.3, numpy 2.5.1, scipy 1.18.0.
- Heavy data under `~/.cache/matbench-discovery/mp/`.
- **figshare fetch gotcha (disclosed).** matbench-discovery's `DataFiles.<name>.path`
  downloader and the `figshare.com/ndownloader/files/<id>` URL return **HTTP 202 (staging)
  with an empty body** on this network; the package's `requests.get(timeout=5)` writes that
  empty response as a **0-byte cache file with no error**. Worked around per the brief via
  the **figshare API v2** + the **`ndownloader.figshare.com`** host, with **md5 gating**:
  - `mp_computed_structure_entries` = file 40344436, 179,351,659 B,
    md5 `76fc748db6b175bb80de4c276d27c235` — **verified**.
  - `mp_elemental_reference_entries` = file 40387775, md5
    `6e93b6f38d6e27d6c811d3cafb23a070` — **verified** (needed for
    `matbench_discovery.energy` to import).

---

## ARM 1 — convex-hull recompute (corrected)

### The bug and the fix
- **Bug (POST-ANALYSIS §5).** The frozen loader reads each MP reference entry's
  `energy_per_atom`. The prior converter pickled raw pymatgen entries, whose
  `energy_per_atom` is the **total DFT energy per atom**, while the query is compared
  against `e_form_true`, a **formation energy** — a total-vs-formation unit mismatch giving
  −3 to −6 eV/atom deltas and 11–41% spurious "flips".
- **Fix (editable `mt29_convert_mp_entries.py`, rewritten; frozen hull script/math
  untouched).** For each of the 154,718 MP entries: apply
  `MaterialsProject2020Compatibility` (the same anion/GGA+U correction layer that built the
  truth column; uses each entry's structure + oxidation states, so
  peroxide/superoxide/ozonide discrimination is correct), then compute
  `matbench_discovery.energy.get_e_form_per_atom(entry, mp_elemental_ref_energies)` (the
  same helper + references — O = −4.9467, matching `ref_energies.json` — that produced
  `e_form_per_atom_mp2020_corrected`). Emit a `ComputedEntry` whose `energy_per_atom` equals
  that formation energy, so the frozen loader reads the right convention. 154,718 processed,
  0 dropped.

### Validation gate — known-materials formation energy (spot-check, built into the converter)
| material | recomputed (eV/atom) | published MP2020 | \|dev\| | gate |
|---|---:|---:|---:|:---:|
| Fe2O3 | −1.708 | −1.68 | 0.028 | PASS |
| Al2O3 | −3.427 | −3.44 | 0.013 | PASS |
| TiO2  | −3.502 | −3.50 | 0.002 | PASS |
| MgO   | −3.054 | −3.06 | 0.006 | PASS |
| NaCl  | −2.110 | −2.02 | 0.090 | PASS |

(The Fe2O3/Al2O3/MgO near-perfect matches exercise the O-anion and Fe +U corrections — the
exact corrections at issue — confirming the convention. The recomputed TiO2 −3.502 was
cross-checked directly against the MP entry set: it is the anatase mp-390 / mp-554278 value;
an initial gate constant of −3.26 was a stale legacy figure, corrected to the MP2020 −3.50.)

### Result — fixed-hull vs recomputed hull, per stratum (n=4,998 evaluated)
| stratum | BEFORE delta_mean (§5) | BEFORE flip-rate | **AFTER delta_mean** | **AFTER flip-rate (per-model range)** |
|---|---:|---:|---:|---:|
| oxide | −4.99 | 11–16% | **−0.0000** | **0.0000** |
| halide | −3.34 | 27–41% | **+0.0002** | **0.0000–0.0024** |
| chalcogenide | −4.26 | 18–35% | **+0.0003** | **0.0000–0.0012** |
| pnictide | −5.59 | 17–36% | **+0.0009** | **0.0000–0.0036** |
| intermetallic | −5.31 | 11–31% | **−0.0000** | **0.0000** |
| other | −6.03 | 15–31% | **+0.0001** | **0.0000–0.0012** |
| **total flips** | **4,611 / 4,998** | | **13 / 4,998 (0.26%)** | (chgnet 5, m3gnet 6, mace 1, orb 1) |

### Verdict: **PASS.** The fixed-hull shortcut `hull_pred = hull_true + (e_form_pred −
e_form_true)` is validated as insurance: a from-scratch hull recompute off the MP phase
diagram reproduces the published `e_above_hull` to ~10⁻³ eV/atom and preserves the
stable/unstable call in 99.74% of a 5k stratified subset.

**Disclosure on "deltas differ across models".** The reported delta
`hull_fixed[m] − hull_recomputed[m]` is **model-independent by construction** — the model
term `e_form_pred[m]` cancels, leaving `published_e_above_hull − recomputed_e_above_hull`
(POST-ANALYSIS §5 point 1). That is a structural feature of the metric, not a defect: before
the fix it was model-independent **and huge** (a bug tell); after the fix it is
model-independent **and ≈ 0** (the correct answer). The genuinely per-model signal lives in
the **flip counts**, which do differ across models (5 / 6 / 1 / 1) and are what the
insurance claim rests on.

Outputs: `mt29_hull_recompute_corrected_result.json` (+ `_manifest.json`, with
`mp_entries_pickle_sha256` and all input hashes). Run via `run_hull_corrected.py`
(imports the frozen `run_real` unchanged; defaults identical to the 4d invocation —
BASE_MODELS, n_total=5000, seed=20260621, default WBM summary + legacy UIP root — only the
mp-entries pickle is corrected and the output path redirected).

---

## ARM 2 — OAM / modern-roster matched-yield arm (corrected)

### The bug and the fix
- **Bug (POST-ANALYSIS §4).** `mt29_uip_inference.py` converted the four new models' UIP
  energies to formation energies against the uncorrected elemental references but omitted
  the MP2020 anion-correction layer that the truth column and the legacy CSVs carry →
  anion-count-proportional positive bias (+0.59 oxide, +0.44 halide, ...), identical across
  four architectures (a harness artifact). New models called ~0 oxides stable → degenerate
  arm.
- **Fix (`apply_mp2020_correction_oam.py`; new post-hoc CSVs, originals untouched).** The
  WBM summary already carries `e_correction_per_atom_mp2020` for every material — computed by
  matbench-discovery **from the actual WBM relaxed structures**, so peroxide/superoxide
  discrimination is already baked in and **no structure download is needed**. The exact
  identity `e_form_corrected == e_form_uncorrected + e_correction_per_atom_mp2020` holds on
  **all 256,963 rows (max residual 1e-6)**. Corrected prediction =
  `raw_pred + e_correction_per_atom_mp2020`. Applied to the **4 new models only**; the 4
  legacy CSVs are already on the corrected convention (before-bias ≈ 0) and are passed
  through unchanged — adding the correction again would over-correct them (verified).

### Validation gate — per-stratum mean bias (pred − MP2020-corrected truth), eV/atom
| model | oxide B→A | halide B→A | chalc B→A | pnict B→A | interm B→A | other B→A |
|---|---|---|---|---|---|---|
| mace-mp-0 (new) | +0.592 → **+0.111** | +0.438 → +0.110 | +0.338 → +0.116 | +0.157 → +0.116 | +0.106 → +0.106 | +0.118 → +0.117 |
| mattersim (new) | +0.590 → **+0.110** | +0.437 → +0.108 | +0.352 → +0.131 | +0.188 → +0.147 | +0.141 → +0.141 | +0.143 → +0.142 |
| sevennet-mf-ompa (OAM) | +0.600 → **+0.119** | +0.442 → +0.113 | +0.339 → +0.117 | +0.159 → +0.118 | +0.107 → +0.107 | +0.122 → +0.120 |
| orb-v3 (new) | +0.586 → **+0.105** | +0.458 → +0.130 | +0.363 → +0.142 | +0.169 → +0.128 | +0.167 → +0.167 | +0.136 → +0.134 |
| mace (legacy, ref) | −0.023 | −0.004 | +0.004 | −0.004 | −0.009 | −0.005 |
| orb (legacy, ref) | +0.009 | +0.008 | +0.016 | +0.010 | +0.004 | +0.015 |

The anion-count-proportional structure **collapses**: after correction every new model has a
**flat ~+0.11 eV/atom** bias across all six families (identical on zero-correction
intermetallics), i.e. the family-differential harness artifact is removed. The residual flat
+0.11 is a genuine, family-independent model offset (not the harness bug) and is left in
place — it is a real property of these models on this reference.

### Degeneracy check — oxides called stable (was 2/5/2/512 pre-fix)
mace-mp-0 **1,552**, mattersim **1,718**, orb-v3 **2,194**, sevennet-mf-ompa **1,524** — all
in the legacy band (chgnet 2,696 / mace 3,268 / orb 2,965). Signal restored.

### Result — oxide-anchored matched-yield interaction (does oxide gain > other strata?)
Point-estimate `gain_median` per (model, stratum), and oxide-vs-other interaction sign:
| model | oxide gain | count oxide>other (of 5 pairs) | reproduces headline? |
|---|---:|:---:|:---:|
| chgnet (legacy) | +1.138 | 5/5 | yes |
| m3gnet (legacy) | +0.751 | 4/5 | yes |
| mace (legacy) | +0.670 | 5/5 | yes |
| orb (legacy) | +0.448 | 5/5 | yes |
| **mace-mp-0 (new)** | +0.156 | **5/5** | **yes** |
| **mattersim (new)** | +0.426 | **5/5** | **yes** |
| **sevennet-mf-ompa (OAM)** | +0.169 | **5/5** | **yes** |
| **orb-v3 (new)** | **−1.821** | **0/5** | **no (dissenter)** |

### Verdict: **MIXED / HOLDS on 3 of 4 modern models.** The oxide-anchored matched-yield
abstention structure — the paper's headline signature — **reproduces on mace-mp-0,
mattersim, and the OAM-era sevennet-mf-ompa** (oxide gain strictly greater than every other
stratum, 5/5, matching the legacy-4 pattern; magnitudes are compressed by the residual flat
offset but the sign structure is intact). It **does not reproduce on orb-v3**, whose
matched-yield gains are uniformly negative (oxide −1.82, other −1.75): its most-confident
stable calls are disproportionately false positives, a genuine confidence-miscalibration for
this abstention task. Honest read: the "holds on modern/OAM models" insurance is **largely
delivered** (3/4, incl. the OAM member) with orb-v3 as a disclosed dissenter — which is
itself a substantive reliability finding, not a failure of the analysis.

**Statistical scope.** These are the frozen OAM arm's point-estimate `gain_median` /
`interaction_med` (what `mt29_stage1_oam_arm.py` computes); they are not the full
bootstrap-CI-exclusion machinery behind the canonical legacy-4 "48/60" headline. The verdict
above is at the sign-structure / point-estimate level.

Outputs: `mace_mp_0_pred_mp2020.csv`, `mattersim_pred_mp2020.csv`,
`sevennet_mf_ompa_pred_mp2020.csv`, `orb_v3_pred_mp2020.csv` (corrected copies, 256,963 rows
each, schema `material_id,e_form_pred`); `roster_mp2020/` (arm input: 4 legacy unchanged + 4
new corrected); `oam_correction_validation.json`;
`mt29_stage1_oam_arm_corrected_result.json` (+ `_manifest.json`). Run via
`run_oam_corrected.py` (imports the frozen `mt29_stage1_oam_arm` functions unchanged; only
points `--uip-root` at the corrected roster and redirects output).

---

## Provenance / house-rules compliance
- **No frozen script or canonical MT29 JSON edited.** git confirms the frozen scripts
  (`mt29_hull_recompute_validation.py`, `mt29_hull_math.py`, `mt29_stage1_oam_arm.py`,
  `mt29_stage1_chem_yield.py`, `mt29_stage1_matched_yield_fix.py`) and all canonical result
  JSONs are unmodified. The only MT29 script touched is the untracked, brief-designated
  editable `mt29_convert_mp_entries.py`.
- **All outputs under `results_expansion_2026-07-10/corrected_arms/`**, never into
  `research/results/MT29/`. Both re-runs go through thin wrappers that import the frozen
  statistics functions and redirect only the output location (documented deviation from the
  bare 4d invocation, which writes into MT29 and refuses-to-overwrite).
- **md5 / row-count gates** on every download (figshare API md5s above) and derived table
  (correction identity max-resid 1e-6 over 256,963 rows; 4 corrected CSVs × 256,963 rows;
  hull spot-check 5/5). Manifests carry input/output sha256.

## Box 18943 redundancy
**Yes — fully redundant for the materials work; releasable.** Neither corrected arm needed
GPU or the box: the hull arm ran off the figshare MP entries (local CPU), and the OAM arm is
a **post-hoc CPU correction** of the four new-generation prediction CSVs the box already
produced (4c/4d) and that were already pulled and validated (ROSTER-MANIFEST-2026-07-10.json,
256,963 rows each). No new inference is required; the box's outputs are preserved on disk.
