# This directory's roster-expansion result is CONTAMINATED — superseded 2026-07-14

**Do not cite `mt29_roster_expansion_result.json` or `RESULTS-ROSTER-EXPANSION.md` in this
directory.** They double-count one model. See
`../results_expansion_2026-07-14/mt29_roster_expansion_result.json` for the corrected run.

## What was wrong

`~/mt_uip_roster25/orb_v2_omat_pred.csv` — the "OMat-generation" Orb-v2 roster member — is
numerically identical (max |Δe_form| = 0 over 256,963 WBM rows) to the frozen 'orb' headline
anchor (`~/mt_uip/orb_pred.csv`, an "MP-generation" anchor in this analysis). Both files trace
to the same published Figshare checkpoint (article 28187990, file 51607307,
"orbff-v2-20241011.csv.gz", md5 `d00f381dac27d367133452a24f17a4e5`) — the frozen anchor,
originally labelled "Orb-v2 MPtrj-only," is actually this general Orb-v2 checkpoint, not the
true MPtrj-only file (Figshare 51607310).

Consequently this directory's `n_included_uip=33` (17 OMat-gen) counts `orb_v2_omat` as an
independent OMat-generation model when it is a duplicate of an MP-generation-labelled anchor
already in the roster. This is a labelling/duplication error, not a corrupt or fabricated file
(the md5 gate on the raw source passes — see `verify_roster_md5.py` in the 2026-07-14 dir,
44/44 OK). Full forensics: `../results_expansion_2026-07-14/mt29_roster_expansion_result.json`
`.remediation` block, and `~/mt_uip_roster25/CONTAMINATED-NOTE.md`.

## Corrected numbers (2026-07-14 rerun, orb_v2_omat dropped)

| quantity | this dir (contaminated) | corrected (2026-07-14) |
|---|---|---|
| n_included_uip | 33 (16 MP, 17 OMat) | 32 (16 MP, 16 OMat) |
| positive-anchored | 33/33 | 32/32 |
| argmax-oxide | 30/33 | 29/32 |
| V3 permutation gap (MP−OMat mean I) | −0.01935 | −0.03708 |
| V3 permutation p | 0.82862 | 0.68153 |
| V3 gap 95% CI | [−0.18323, 0.14301] | [−0.2083, 0.13303] |
| multiplicity full family (n cells) | 495 | 480 |
| multiplicity full family CI-excl0 | 388 | 378 |
| multiplicity full family BH q=.05 | 379 | 369 |
| multiplicity full family Holm α=.05 | 0 (resolution-limited) | 0 (resolution-limited) |
| oxide-halide subfamily | 33/33 | 32/32 |
| shuffle-null | 0/495 | 0/480 |
| overall verdict | NO-GENERATIONAL-EFFECT (honest null) | NO-GENERATIONAL-EFFECT (honest null) — unchanged qualitatively |

The verdict does not change (still an honest null), and every other model's per-model I value
is bit-for-bit unchanged (independent per-model bootstrap streams) — only the duplicate row and
the arm-level aggregates that summed over it are affected.

This directory's files (`mt29_roster_expansion_result.json`, `ROSTER25_DATA_MANIFEST.json`,
`RESULTS-ROSTER-EXPANSION.md`, `DATA-SANITY-OUTLIERS.json`) are retained unmodified for
provenance/audit purposes and MUST NOT be overwritten.
