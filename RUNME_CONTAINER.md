# RUNME_CONTAINER.md — fresh AutoDL 4090D container runbook

Target: a fresh AutoDL 4090D container (24 GB VRAM), conda `base` env with `torch`
cu128 preinstalled. Goal: run the two decisive arms deferred in `NEXT-EXPERIMENTS.md`
(items 1 and 2) end-to-end, feeding new provenance-stamped result JSONs into
`research/results/MT29/` without touching any existing frozen result.

This machine (the CPU depth-pass sandbox) has **no GPU, no network, and none of the
UIP/pymatgen libraries installed** — everything below is implemented and unit-tested
against synthetic/toy data (`python -m pytest`, `bash run_all_arms.sh smoke`) but has
**not been run for real**. Treat the exact library API names (fairchem's
`OCPCalculator`, sevenn's `SevenNetCalculator`, matbench-discovery's `DataFiles`
attribute names) as best-effort scaffolding to be verified against whatever versions
`pip` resolves in the container — they may have moved since this was written.

## 0. Clone / sync the repo onto the container

This repo is not pushed to a remote yet (`NEXT-EXPERIMENTS.md` item 3) — copy it onto
the container by whatever out-of-band means you're already using (rsync/scp), together
with the sibling `reliability-commons` directory (needed for `relmetrics`):

```
materials-mlip-research/          # this repo
reliability-commons/              # sibling, same parent dir
```

## 1. pip installs

The base env already has numpy/pandas/scikit-learn/scipy/matplotlib + torch (cu128).
Install the UIP-specific and hull-recompute-specific libraries:

```bash
cd materials-mlip-research
pip install -r requirements.txt
pip install -e ../reliability-commons

# Arm 1 (OAM-era UIP inference) -- eSEN / SevenNet (2025, primary + un-gated fallback):
pip install ase                       # structure I/O + Calculator interface
pip install fairchem-core              # eSEN-30M-OAM (Meta FAIR OMat24 family)
pip install sevenn                     # SevenNet-MF-ompa (MDIL-SNU, un-gated fallback)

# Roster (EXPANSION-PLAN-2026-07-09.md Sec.2.4) -- 3 more current-gen (2024-25) UIPs,
# all un-gated, no click-through, but each auto-downloads its checkpoint over the
# network on first use unless --checkpoint pins a pre-fetched local file.
# *** mace-torch and mattersim CANNOT coexist in one env (verified 2026-07-09): ***
# *** mace-torch pins e3nn==0.4.4, mattersim<1.2.4 pins e3nn>=0.5.0, and           ***
# *** mattersim>=1.2.4 needs Python>=3.12. Use separate venvs if the container's  ***
# *** Python is <3.12 (each --model run is a separate process anyway).           ***
pip install mace-torch                 # MACE-MP-0 (ACEsuit, 2024) -- NOT the unrelated
                                        # PyPI package "mace"; checkpoint auto-fetches
                                        # from github.com/ACEsuit/mace-mp/releases (or
                                        # mace-foundations on HF) to ~/.cache/mace
pip install orb-models                 # ORB-v3 (Orbital Materials, 2025); checkpoint
                                        # auto-fetches from an Orbital Materials S3
                                        # bucket (orbitalmaterials-public-models.s3...)
                                        # -- NOT Hugging Face, verified 2026-07-09
pip install mattersim                  # MatterSim (Microsoft Research, 2024); ships
                                        # mattersim-v1.0.0-1M.pth (default) / -5M.pth,
                                        # auto-fetched from raw.githubusercontent.com/
                                        # microsoft/mattersim -- NOT Hugging Face,
                                        # verified 2026-07-09; needs a SEPARATE venv
                                        # from mace-torch (see note above)

# Arm 2 (hull recompute validation):
pip install pymatgen matbench-discovery
```

Verify the exact class/import paths this repo's code assumes still hold (see the
"verify against installed version" comments in `mt29_uip_inference.py` and
`fetch_data.sh`):

```bash
python -c "from fairchem.core import OCPCalculator" 2>&1 | tail -5
python -c "from sevenn.calculator import SevenNetCalculator" 2>&1 | tail -5
python -c "from mace.calculators import mace_mp" 2>&1 | tail -5
python -c "from orb_models.forcefield import pretrained; from orb_models.forcefield.calculator import ORBCalculator" 2>&1 | tail -5
python -c "from mattersim.forcefield import MatterSimCalculator; from mattersim.forcefield.potential import Potential" 2>&1 | tail -5
python -c "from matbench_discovery.data import DataFiles; print([d.name for d in DataFiles])"
```

If any of these fail, adjust the corresponding `_lazy()` import in
`research/results/MT29/mt29_uip_inference.py` (one calculator class per model — see
`MODEL_REGISTRY` and the `_EsenCalculator` / `_SevenNetCalculator` / `_MaceCalculator`
/ `_OrbCalculator` / `_MatterSimCalculator` classes) or the two `DataFiles.<name>`
references in `fetch_data.sh` to match the installed package's current API, then
re-run `bash run_all_arms.sh smoke` to confirm the rest of the pipeline is undisturbed
(the smoke path never imports these libraries, so it stays green regardless). The ORB
import path in particular has moved between releases
(`orb_models.forcefield.calculator` vs `orb_models.forcefield.inference.calculator`) —
verify against the installed version first.

## 2. Smoke-test first (CPU, seconds, no data)

Before spending any GPU time or bandwidth, confirm the code paths work:

```bash
python -m pytest                 # 60 tests, all CPU/toy-data, should be green
bash run_all_arms.sh smoke       # --smoke on all three new scripts
```

## 3. Fetch data

```bash
bash fetch_data.sh
```

Fetches (via the `matbench-discovery` package's own cache-aware `DataFiles`
accessors — see the script for exact source notes):
- WBM initial (unrelaxed) structures — needed for Arm 1 inference. **Note:** the
  existing repo-adjacent copy is a confirmed 0-byte aborted download
  (`DATA_MANIFEST.md` Sec.3); this re-fetches it for real.
- MP computed structure entries — the reference-entry set for Arm 2's hull recompute
  (~1-2 GB).

The WBM **summary** CSV (ground truth, `2023-12-13-wbm-summary.csv.gz`) and the four
cached 2023-24 UIP prediction CSVs are expected to already be present per
`DATA_MANIFEST.md` (`$MT_DATA_ROOT`, default `~/mt_stage0/data`; `$MT_UIP_ROOT`,
default `~/mt_uip`) — copy them onto the container too if this is a fresh machine.

## 4. Gated checkpoint (eSEN-30M-OAM) — READ THIS BEFORE ARM 1

`eSEN-30M-OAM` is the **primary** OAM-era model target (F1 0.925, per
`FABLE-HANDOFF.md` Sec.5) but its checkpoint sits behind a Hugging Face Hub
click-through license that **cannot be completed headlessly**:

1. On a machine with a browser, log into (or create) a Hugging Face account and visit
   the `facebook/OMat24`-family model page; accept the license.
2. Generate an HF access token (Settings -> Access Tokens) if you don't already
   have one, and run `huggingface-cli login` (or `hf auth login`) on the container.
3. Download the eSEN-30M-OAM checkpoint file (`hf download <repo> <file>` or the
   fairchem checkpoint helper — check current fairchem docs, this has moved before).
4. Pass the resulting local path as `--checkpoint /path/to/esen-30m-oam.pt` (or
   `OAM_CHECKPOINT=/path/to/esen-30m-oam.pt` for `run_all_arms.sh`).

**If step 1 cannot be completed** (no one available to click through the license):
fall back to `sevennet-mf-ompa` (F1 0.901, un-gated, MIT license, downloads
automatically) — set `OAM_MODEL=sevennet-mf-ompa` (the `run_all_arms.sh` default).
Running `mt29_uip_inference.py --model esen-30m-oam` without a resolved checkpoint
fails fast with a message prefixed `REQUIRES_USER_CHECKPOINT:` rather than hanging or
silently falling back — this is intentional (see that script's docstring).

### 4b. Roster models (mace-mp-0 / orb-v3 / mattersim) — none are gated

Unlike eSEN, none of the three roster models (EXPANSION-PLAN-2026-07-09.md Sec.2.4)
sit behind a click-through license — no browser step needed. Each still needs NETWORK
ACCESS at first `.total_energy()` call to auto-download its checkpoint. **Sources
below were verified live** (pip-installed into a local CPU-only venv on 2026-07-09,
`import`/`inspect.signature` only — no checkpoint downloads, no real inference run
locally; see the "package/API surprises" note at the end of this section):

| Model key | Package (verified version) | Checkpoint source | Gated? |
|---|---|---|---|
| `mace-mp-0` | `mace-torch==0.3.16` | `github.com/ACEsuit/mace-mp/releases` (or `mace-foundations` on HF); cached at `~/.cache/mace` (override via `XDG_CACHE_HOME`) | No |
| `orb-v3` | `orb-models==0.5.5` | An Orbital Materials **S3 bucket** (`orbitalmaterials-public-models.s3.us-west-1.amazonaws.com/forcefields/orb-v3/...`) — **NOT Hugging Face**, contrary to some third-party docs; this is the literal default value of `pretrained.orb_v3_conservative_inf_omat`'s `weights_path` parameter | No |
| `mattersim` | `mattersim==1.2.5` | `raw.githubusercontent.com/microsoft/mattersim/main/pretrained_models/<file>.pth` — **NOT Hugging Face**; downloaded to `~/.local/mattersim/pretrained_models` on first use (confirmed by reading `mattersim.forcefield.potential.download_checkpoint`'s source) | No |

If the box has no outbound network at GPU-session time, pre-fetch each checkpoint
during the no-card staging window and pass it via `--checkpoint /path/to/file`
(same flag eSEN/SevenNet use).

**Package/API surprises found during live verification (2026-07-09, CPU-only venv,
not in this repo's requirements.txt):**
- **`MatterSimCalculator` does NOT accept a checkpoint path directly.** Its real
  `__init__` is `MatterSimCalculator(potential=None, device='cuda', ...)` — you must
  first build a `Potential` via the classmethod
  `mattersim.forcefield.potential.Potential.from_checkpoint(load_path=..., device=...)`
  and pass that in as `potential=`. `mt29_uip_inference.py`'s `_MatterSimCalculator`
  already does this correctly (fixed during this verification pass — an earlier draft
  incorrectly assumed a `load_path=` kwarg on the calculator itself).
- **`mace-torch` and `mattersim` cannot be pip-installed into the SAME environment.**
  `mace-torch` pins `e3nn==0.4.4`; `mattersim<1.2.4` pins `e3nn>=0.5.0`; `mattersim
  >=1.2.4` (which relaxes this) requires `Python>=3.12`. If the container's Python is
  <3.12, install mace-torch and mattersim in **separate venvs** (or containers) and
  run their arms in separate `mt29_uip_inference.py --model ...` invocations — this
  repo's harness already does this naturally (one `--model` per process), so it only
  matters if you try to `pip install -r requirements.txt`-style everything into one
  env. `orb-models` conflicts with neither.
- ORB-v3's `pretrained.orb_v3_conservative_inf_omat(...)` returns the forcefield model
  object directly, not a `(model, atoms_adapter)` tuple as some third-party docs
  suggest — `ORBCalculator(orbff, device=...)` (as coded) is correct as-is.

## 5. Reference energies

`mt29_uip_inference.py --ref-energies-json` needs a per-element reference-energy table
(eV/atom) on the SAME correction convention as the WBM ground truth
(`e_form_per_atom_mp2020_corrected`), so the new model's `e_form_pred` lands on the
same energy scale as the four cached UIPs. Source this from whatever the installed
`matbench-discovery` version exposes for MP2020-corrected elemental references (check
`matbench_discovery.energy` or the package's docs for the current helper name — this
has not been verified in this sandbox, no network available). Write it out as JSON,
e.g.:

```bash
python - <<'PY'
import json
# TODO(container): replace with the actual matbench_discovery reference-energy source
# once verified against the installed package version.
ref_energies = {...}  # {"Na": -1.31, "Cl": -1.85, ...}
json.dump(ref_energies, open("ref_energies.json", "w"))
PY
```

## 6. Run the arms, in order

```bash
export OAM_MODEL=sevennet-mf-ompa            # or esen-30m-oam if checkpoint accepted
export OAM_CHECKPOINT=/path/to/checkpoint.pt  # only if using esen-30m-oam
export OAM_REF_ENERGIES_JSON=/path/to/ref_energies.json

bash run_all_arms.sh all
```

Equivalently, step by step (each step is idempotent — safe to re-run). **Run `roster`
BEFORE `oam`** — `oam`'s Arm 1b call auto-discovers every `*_pred.csv` beyond the base
4 that exists on disk AT THAT MOMENT, so the roster models must already be written for
the one combined result JSON to include all 5 current-gen UIPs:

```bash
bash run_all_arms.sh fetch    # Sec.3 above
bash run_all_arms.sh roster   # mace-mp-0 / orb-v3 / mattersim inference (content-gated
                               # per-model: each *_pred.csv must exist AND have >
                               # $ROSTER_MIN_PREDICTIONS rows, default 1000 -- never a
                               # bare exit-code check)
bash run_all_arms.sh oam      # Arm 1a (eSEN/SevenNet) inference -> Arm 1b analysis
                               # hookup (auto-discovers roster CSVs too)
bash run_all_arms.sh hull     # Arm 2 hull-recompute validation
```

(`bash run_all_arms.sh all` runs `smoke, fetch, roster, oam, hull` in that order.)

Arm 1a (`mt29_uip_inference.py`) writes `$MT_UIP_ROOT/<model>_pred.csv` (+ a sidecar
`_manifest.json`) for each model, whether run via `oam` (single model) or `roster`
(mace-mp-0/orb-v3/mattersim, looped, each content-gated on row count); Arm 1b
(`mt29_stage1_oam_arm.py`) auto-discovers ALL of them and writes ONE
`research/results/MT29/mt29_stage1_oam_arm_result.json` (+ manifest) covering every
current-gen UIP found beyond the frozen base 4 (`chgnet`/`m3gnet`/`mace`/`orb`) — the
multi-UIP verdict-replication table for JCIM reviewer-proofing. Arm 2
(`mt29_hull_recompute_validation.py`) writes
`research/results/MT29/mt29_hull_recompute_validation_result.json` (+ manifest). None
of these overwrite an existing frozen result JSON — each script refuses
(`REFUSING to overwrite existing ...`) if its output already exists; delete the file
first if you intend a genuine re-run.

## 7. What's optional / not wired here

- `mt29_stage2_robustness.py` (LOEO / WBM-round gates) and
  `mt29_multiplicity_correction.py` (BH-FDR/Holm) were not extended to the OAM-era
  model list in this pass (kept out of scope to stay a minimal diff for the container
  work). If you want them, follow the same pattern as
  `research/results/MT29/mt29_stage1_oam_arm.py`: import the base script's helper
  functions, override the model list locally, and write a NEW output filename — never
  edit `MODELS` in the frozen canonical scripts in place.
- Convex-hull recompute (Arm 2) currently samples 5,000 structures by default
  (`--n-total`); increase/decrease per the ~1-3 h CPU budget noted in
  `NEXT-EXPERIMENTS.md` item 2.
