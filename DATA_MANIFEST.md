# DATA_MANIFEST — external input data (not tracked in this repo)

Written 2026-07-02 as part of the provenance sweep (pre-push baseline).

All experiment input data for this direction lives **outside the repository** in
hardcoded home-directory paths (a known infra gap — no `DATA_ROOT` abstraction yet).
No data directory inside the repo is gitignored; the repo itself is ~8 MB of
scripts, result JSONs, manifests, figures, and manuscript sources.

SHA-256 values below were computed with `sha256sum` on 2026-07-02. Where a hash is
also recorded as an input in a frozen run manifest under
`research/results/MT29/*_manifest.json`, the values were verified to match
(noted per file).

## 1. `~/mt_uip/` — modern UIP predictions on WBM (21 MB total)

Frozen Matbench-Discovery model prediction files (2023–24 generation UIPs), one row
per WBM structure (n = 256,963). Source per `FABLE-HANDOFF.md` §5: "free/no-auth
Figshare-cached" Matbench Discovery prediction data
(https://matbench-discovery.materialsproject.org/). The exact download command is
**not recorded** in repo docs — labeled not-recorded, do not invent.

| File | Size (bytes) | SHA-256 | Matches run manifests |
|---|---:|---|---|
| `~/mt_uip/chgnet_pred.csv` | 5,285,535 | `d84578eb02843a3f468760d01320671433867b35e969b5aa0f2b98d3293b444e` | yes (MT29 stage-1/2 manifests) |
| `~/mt_uip/m3gnet_pred.csv` | 5,287,172 | `8c4e136bf1b8e577973ba05dccafabda47dbc3b448b13ed6874484b25e028737` | yes |
| `~/mt_uip/mace_pred.csv` | 5,283,536 | `d37eed9ec6a5ee0e9993de2009ee177e3bacffffb7f1dd922fc7d786a38753d2` | yes |
| `~/mt_uip/orb_pred.csv` | 5,280,422 | `9df863e74a88cd89e234ab1f5bec02d3b226fb908f92278c7d8eb423ca53ac76` | yes |

`~/mt_uip/` also contains earlier V2/V6 scripts and result files
(`mt_v2_modern_uip.py`, `mt_v2_result.{json,md}`, `v6_disagreement_reliability.py`,
`v6_result.{json,md}`, `v6b_result.{json,md}`, `v2_run.log`, `v6_run.log`) — those
correspond to already-committed V2/V6 findings (commits `d31adf1`, `33e6517`,
`9b7306b`).

## 2. `~/mt_stage0/data/` — 2020-era model predictions + WBM ground truth (40 MB total)

Matbench Discovery Figshare-hosted prediction/summary CSVs (filenames are the
upstream canonical names). Same source note as above.

| File | Size (bytes) | SHA-256 | Notes |
|---|---:|---|---|
| `2022-11-18-megnet-wbm-IS2RE.csv.gz` | 1,336,038 | `99d55d75f9f4f357253ba84ff685e8fe4fe75197a7b78ec177a2c8f1e0f1cfc1` | MEGNet preds |
| `2023-01-26-cgcnn-ens=10-wbm-IS2RE.csv.gz` | 13,127,994 | `9fba78430e76e7443436d143d2af9ad1d7e54ef84e73443abe9058e41e4d7ebb` | CGCNN ensemble preds |
| `2023-02-05-cgcnn-perturb=5-wbm-IS2RE.csv.gz` | 12,810,481 | `d893a03e87be0982566bdd26633264ee2fe8e1b4162953308beb2ba8c3751419` | CGCNN+P preds |
| `2023-07-11-alignn-ff-wbm-IS2RE.csv.gz` | 1,323,048 | `dc75be97f3bce3ce724680065abf11a19bdc6a3928fdd77ccb42d3f62a02e593` | ALIGNN-FF preds |
| `2023-12-13-wbm-summary.csv.gz` | 12,745,623 | `adbdd8b24086d4888195d8894c77f6d5fb29ce33bbb5d7d3898b4d79e964dc54` | WBM summary = ground truth (hull, formula, rounds); **matches MT29 manifests** |

## 3. `~/.cache/matbench-discovery/wbm/` — matbench-discovery package cache (13 MB)

| File | Size (bytes) | SHA-256 | Notes |
|---|---:|---|---|
| `2023-12-13-wbm-summary.csv.gz` | 12,745,623 | `adbdd8b24086d4888195d8894c77f6d5fb29ce33bbb5d7d3898b4d79e964dc54` | byte-identical mirror of the `~/mt_stage0/data` copy |
| `2024-08-04-wbm-initial-atoms.extxyz.zip` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | **empty file** (0 bytes; hash is the SHA-256 of empty input) — aborted/never-completed download, not usable data |

## Verification chain

Every headline result JSON in `research/results/MT29/` has a sibling
`*_manifest.json` recording `script_sha256`, input SHA-256s, output SHA-256, seed
(20260621), n_boot (1000), and pinned library versions. The input hashes above were
cross-checked against `mt29_stage1_matched_yield_manifest.json` and match exactly,
so the on-disk data is byte-identical to what produced the frozen results
(independent byte-identical re-run recorded 2026-07-01 in that manifest's
`reproduction_note`).
