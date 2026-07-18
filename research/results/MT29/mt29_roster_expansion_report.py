#!/usr/bin/env python
"""Render results_expansion_2026-07-13/RESULTS-ROSTER-EXPANSION.md from the audit JSON.
Numbers are read from mt29_roster_expansion_result.json — never hand-typed."""
import json, os

OUTDIR = "/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/results_expansion_2026-07-13"
R = json.load(open(os.path.join(OUTDIR, "mt29_roster_expansion_result.json")))
MD = os.path.join(OUTDIR, "RESULTS-ROSTER-EXPANSION.md")

pm = R["per_model"]
v = R["verdicts"]
mp = R["MP_arm"]; om = R["OMat_arm"]


def yn(b):
    return "yes" if b else "no"


def sci(x):
    return "NA" if x is None else f"{x:+.4f}"


L = []
L.append("# MT29 roster-expansion results — the generational contrast of oxide-anchored value-of-abstention")
L.append("")
L.append("**Status:** post-hoc-motivated, PRE-REGISTERED (`mt29_roster_expansion_PREREG-2026-07-13.md`), "
         "pending user sign-off. Frozen legacy-4 regression guard passed byte-exact before this run.")
L.append("**Machinery:** inherited verbatim (prototype-blocked cluster bootstrap, common-absolute matched-yield "
         "DAF gain, two-sided bootstrap p, BH-FDR+Holm, seed 20260621, n_boot 1000). Anchors use the frozen "
         "on-disk snapshot; all other models use published Figshare v25 predictions.")
L.append("")

# ---- headline verdict block ----
L.append("## Headline verdict")
L.append("")
L.append(f"- **V1 (oxide-anchoring across the MP generation):** {v['V1_distributional_MP']['verdict']} "
         f"— positive-anchored in {mp['n_positive_anchored']}/{mp['n']} MP-gen UIPs "
         f"(frac {v['V1_distributional_MP']['frac_positive_anchored_MP']}); "
         f"oxide is the highest-value abstention stratum in {mp['n_argmax_oxide']}/{mp['n']}.")
L.append(f"- **V2 (generational dissolution/reversal in the OMat generation):** {v['V2_generational']['verdict']} "
         f"— positive-anchored in {om['n_positive_anchored']}/{om['n']} OMat-gen UIPs "
         f"(frac {v['V2_generational']['frac_positive_anchored_OMat']}), "
         f"reversed in {om['n_reversed']}/{om['n']}, null in {om['n_null']}/{om['n']}.")
if v.get("V3_permutation"):
    v3 = v["V3_permutation"]
    L.append(f"- **V3 (formal between-generation permutation test):** observed gap in mean oxide-vs-halide "
             f"interaction (MP − OMat) = {v3['observed_gap_meanI']:+.4f} "
             f"(95% CI {v3['gap_ci95']}), permutation p = {v3['perm_p']} "
             f"[n_MP={v3['n_mp']}, n_OMat={v3['n_omat']}].")
L.append(f"- **Shuffle-null hygiene:** {R['shuffle_null']['n_excl0']}/{R['shuffle_null']['n_cells']} "
         f"false positives (clean = {yn(v['shuffle_null_clean'])}).")
L.append(f"- **OVERALL:** {v['overall']}")
L.append("")

# ---- multiplicity ----
mf = R["multiplicity_full_family"]; mo = R["multiplicity_oxide_halide"]
L.append("## Multiplicity (included-UIP family)")
L.append("")
L.append(f"- Full family ({mf['n']} model×pair cells): CI-excl-0 {mf['n_ci_excl0']}, "
         f"BH-FDR(q=.05) {mf['n_bh_q05']}, Holm(α=.05) {mf['n_holm_a05']}"
         f"{' [Holm resolution-limited at n_boot=1000]' if mf['holm_resolution_limited'] else ''}.")
L.append(f"- Oxide-vs-halide subfamily ({mo['n']} cells): CI-excl-0 {mo['n_ci_excl0']}, "
         f"BH-FDR {mo['n_bh_q05']}, Holm {mo['n_holm_a05']}.")
L.append("")

# ---- counts ----
gc = R["generation_counts"]
L.append("## Roster")
L.append("")
L.append(f"- Models converted: {R['n_models_total']} (all MP-gen: {gc['all_MP']}, all OMat-gen: {gc['all_OMat']}).")
L.append(f"- Included UIPs after inclusion rule (≥{R['inclusion_rule']['min_called_stable_per_stratum']} "
         f"called-stable/stratum, ≥{R['inclusion_rule']['min_coverage']} coverage): "
         f"{R['n_included_uip']} ({gc['included_uip_MP']} MP-gen, {gc['included_uip_OMat']} OMat-gen).")
L.append("")

# ---- per-model table (UIPs, by generation then interaction) ----
def model_rows(klass_filter):
    rows = []
    for s, r in pm.items():
        if r["klass"] not in klass_filter:
            continue
        oh = r["interactions"].get("oxide|halide", {})
        rows.append((s, r["generation"], r["klass"], r["included"], r.get("mae_form"),
                     oh.get("interaction_med"), oh.get("ci95"), oh.get("excl0"),
                     r.get("argmax_gain_stratum"), r["sscs"].get("sscs_max_abs_gap")))
    # sort: generation (MP first), then interaction desc
    order = {"MP": 0, "OMat": 1, "special": 2}
    rows.sort(key=lambda x: (order.get(x[1], 3), -(x[5] if x[5] is not None else -9)))
    return rows

L.append("## Per-model oxide-vs-halide matched-yield interaction (prototype-blocked CI)")
L.append("")
L.append("| model | gen | class | incl | MAE(eV) | I(oxide−halide) | 95% CI | excl0 | argmax-gain stratum | SSCS |")
L.append("|---|---|---|:--:|--:|--:|---|:--:|---|--:|")
for s, gen, kl, inc, mae, I, ci, e, amx, sscs in model_rows({"uip", "anchor"}):
    ci_s = f"[{ci[0]:+.3f}, {ci[1]:+.3f}]" if ci else "NA"
    L.append(f"| {s} | {gen} | {kl} | {yn(inc)} | {mae if mae is not None else 'NA'} | "
             f"{sci(I)} | {ci_s} | {yn(e) if e is not None else 'NA'} | {amx or 'NA'} | "
             f"{sscs if sscs is not None else 'NA'} |")
L.append("")
L.append("### 2020-era classical baselines (MP-trained; reported for the MAE-vs-decision spread)")
L.append("")
L.append("| model | incl | MAE(eV) | I(oxide−halide) | 95% CI | excl0 | argmax-gain stratum |")
L.append("|---|:--:|--:|--:|---|:--:|---|")
for s, gen, kl, inc, mae, I, ci, e, amx, sscs in model_rows({"classical"}):
    ci_s = f"[{ci[0]:+.3f}, {ci[1]:+.3f}]" if ci else "NA"
    L.append(f"| {s} | {yn(inc)} | {mae if mae is not None else 'NA'} | {sci(I)} | {ci_s} | "
             f"{yn(e) if e is not None else 'NA'} | {amx or 'NA'} |")
L.append("")
L.append("---")
L.append("")
L.append("*Generated by `mt29_roster_expansion_report.py` from `mt29_roster_expansion_result.json`. "
         "Interpretation is added below by hand, keyed to these frozen numbers.*")

with open(MD, "w") as f:
    f.write("\n".join(L) + "\n")
print("wrote", MD, "(", len(L), "lines )")
