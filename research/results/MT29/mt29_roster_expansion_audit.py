#!/usr/bin/env python
"""MT29 roster-expansion audit — the generational contrast of oxide-anchored value-of-abstention.

Governed by `mt29_roster_expansion_PREREG-2026-07-13.md`. INHERITS the frozen statistical
machinery verbatim and invents no estimator:
  * prototype-blocked (cluster) bootstrap  -> boot_gain_cluster        (mt29_prototype_blocked_ci)
  * common-absolute matched-yield DAF gain -> daf_top_y                (mt29_stage1_matched_yield_fix)
  * two-sided bootstrap sign p-value       -> pval_two_sided           (mt29_multiplicity_correction)
  * BH-FDR + Holm-Bonferroni               -> relmetrics.multiplicity
  * anion strata / hull recipe / seed / n_boot -> mt29_stage1_chem_yield
The only new objects are the roster, the model->generation map, and the two-arm aggregation.

Each model is loaded INDEPENDENTLY (WBM ground truth inner-joined with that model's own preds),
not force-intersected across the whole roster, so per-model results equal what the model would
score standalone and coverage differences do not collapse the shared row set.

CPU/pandas/NumPy only. Reads converted preds from ~/mt_uip_roster25/ (anchors = frozen on-disk;
all other models = published Figshare v25). No GPU, no self-inference, no downloads here.
"""
import os, sys, json, hashlib, platform
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from scipy.stats import norm

MT29 = "/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/research/results/MT29"
RC = "/home/zeyufu/Desktop/ml-reliability-research/reliability-commons"
PROTO_DIR = ("/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/"
             "results_expansion_2026-07-11/prototype_blocked_cis")
sys.path.insert(0, MT29)
sys.path.insert(0, RC)
sys.path.insert(0, PROTO_DIR)
from mt29_stage1_chem_yield import anion_family, ci95, excl0, SEED, N_BOOT, sha256
from mt29_stage1_matched_yield_fix import daf_top_y, FAM_ORDER
from mt29_prototype_blocked_ci import boot_gain_cluster
from mt29_multiplicity_correction import pval_two_sided
from relmetrics.multiplicity import benjamini_hochberg, holm_bonferroni

WBM = os.path.expanduser("~/mt_stage0/data/2023-12-13-wbm-summary.csv.gz")
ROSTER_DIR = os.path.expanduser("~/mt_uip_roster25")
OUTDIR = "/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/results_expansion_2026-07-13"
DATA_MANIFEST = os.path.join(OUTDIR, "ROSTER25_DATA_MANIFEST.json")
OUT_JSON = os.path.join(OUTDIR, "mt29_roster_expansion_result.json")
OUT_MANIFEST = os.path.join(OUTDIR, "mt29_roster_expansion_manifest.json")

N_WBM = 256963
MIN_CS = 50            # min called-stable per stratum for inclusion (prereg §3)
MIN_COV = 0.99         # min WBM coverage for inclusion
PERM = 10000           # permutation reps for V3
PERM_SEED = 20260713
OXHAL = ("oxide", "halide")   # frozen headline pair (FAM_ORDER: oxide idx0 < halide idx3)


def load_base():
    cols = ["material_id", "formula", "e_form_per_atom_mp2020_corrected",
            "e_above_hull_mp2020_corrected_ppd_mp", "protostructure_spglib"]
    wbm = pd.read_csv(WBM, usecols=cols)
    base = wbm.dropna(subset=["e_form_per_atom_mp2020_corrected",
                              "e_above_hull_mp2020_corrected_ppd_mp"]).reset_index(drop=True)
    base["family"] = base["formula"].apply(anion_family)
    return base


def sscs_native(pred_hull, true_stable, fam, fams, seed=20260629):
    """Descriptive per-model SSCS (M1_PREREG E3): p_native = Phi(-hull_pred/sigma),
    sigma = RMSE(hull error) on a calibration half; per-stratum gap = mean(p_native) -
    empirical stable rate on the test half; SSCS = max_stratum |gap|."""
    n = len(pred_hull)
    rng = np.random.default_rng(seed)
    perm = rng.permutation(n)
    calib, test = perm[: n // 2], perm[n // 2:]
    err = pred_hull  # hull error vs 0-boundary proxy; sigma from calibration spread of pred_hull
    sigma = float(np.sqrt(np.mean((pred_hull[calib] - pred_hull[calib].mean()) ** 2))) or 1.0
    p_native = norm.cdf(-pred_hull / sigma)
    gaps = {}
    for f in fams:
        m = (fam == f)
        ti = np.intersect1d(test, np.where(m)[0], assume_unique=False)
        if len(ti) < 50:
            continue
        gaps[f] = float(p_native[ti].mean() - true_stable[ti].mean())
    sscs = max((abs(v) for v in gaps.values()), default=float("nan"))
    return dict(sscs_max_abs_gap=round(sscs, 5), per_stratum_gap={k: round(v, 5) for k, v in gaps.items()})


def analyze_model(base, short, pred_path):
    p = pd.read_csv(pred_path)[["material_id", "e_form_pred"]]
    df = base.merge(p, on="material_id", how="inner").dropna(subset=["e_form_pred"]).reset_index(drop=True)
    eft = df["e_form_per_atom_mp2020_corrected"].values
    ht = df["e_above_hull_mp2020_corrected_ppd_mp"].values
    true_stable = ht < 0.0
    pred_hull = ht + (df["e_form_pred"].values - eft)
    conf = np.abs(pred_hull)
    pred_stable = pred_hull < 0.0
    protos = df["protostructure_spglib"].values
    fam = df["family"].values
    fams = FAM_ORDER
    fam_idx = {f: np.where(fam == f)[0] for f in fams}

    cs_conf = {}; cs_st = {}; cs_groups = {}; br = {}; total_cs = {}
    for f in fams:
        idx = fam_idx[f]
        cs = np.where(pred_stable[idx])[0]
        gi = idx[cs]
        cs_conf[f] = conf[gi]; cs_st[f] = true_stable[gi]
        br[f] = float(true_stable[idx].mean()); total_cs[f] = int(len(cs))
        if len(gi):
            uniq, inv = np.unique(protos[gi], return_inverse=True)
            cs_groups[f] = [np.where(inv == k)[0] for k in range(len(uniq))]
        else:
            cs_groups[f] = []

    coverage = len(df) / N_WBM
    included = bool(coverage >= MIN_COV and all(total_cs[f] >= MIN_CS and br[f] > 0 for f in fams))
    y_loose = min(total_cs.values())
    y_tight = max(1, y_loose // 2)

    # per-model FRESH bootstrap stream (seed 20260621): the first-processed anchor (chgnet) thereby
    # reproduces the frozen prototype-blocked cell exactly; all models share one reproducible stream.
    gains = {}; gains_sh = {}
    if y_loose > 0:
        rng = np.random.default_rng(SEED)
        for f in fams:
            if total_cs[f] > 0 and br[f] > 0:
                gains[f] = boot_gain_cluster(cs_conf[f], cs_st[f], cs_groups[f], br[f], y_tight, y_loose, rng, False)
            else:
                gains[f] = np.array([])
        for f in fams:
            if total_cs[f] > 0 and br[f] > 0:
                gains_sh[f] = boot_gain_cluster(cs_conf[f], cs_st[f], cs_groups[f], br[f], y_tight, y_loose, rng, True)
            else:
                gains_sh[f] = np.array([])
    else:
        gains = {f: np.array([]) for f in fams}
        gains_sh = {f: np.array([]) for f in fams}

    gain_med = {f: (round(float(np.median(gains[f])), 5) if len(gains[f]) else None) for f in fams}
    valid = [f for f in fams if gain_med[f] is not None]
    argmax_stratum = max(valid, key=lambda f: gain_med[f]) if valid else None

    inter = {}; inter_sh = {}
    for i in range(len(fams)):
        for j in range(i + 1, len(fams)):
            a, b = fams[i], fams[j]
            L = min(len(gains[a]), len(gains[b]))
            if L < 100:
                continue
            d = gains[a][:L] - gains[b][:L]
            ci = ci95(d)
            inter[f"{a}|{b}"] = dict(interaction_med=round(float(np.median(d)), 5),
                                     ci95=[round(ci[0], 5), round(ci[1], 5)],
                                     excl0=excl0(ci), p_raw=pval_two_sided(d))
            Ls = min(len(gains_sh[a]), len(gains_sh[b]))
            if Ls >= 100:
                ds = gains_sh[a][:Ls] - gains_sh[b][:Ls]
                cis = ci95(ds)
                inter_sh[f"{a}|{b}"] = dict(excl0=excl0(cis), p_raw=pval_two_sided(ds))

    sscs = sscs_native(pred_hull, true_stable, fam, fams)
    mae = float(np.abs(df["e_form_pred"].values - eft).mean())
    return dict(short=short, n=len(df), coverage=round(coverage, 6), included=included,
                mae_form=round(mae, 5), total_called_stable=total_cs,
                base_rate_stable={f: round(br[f], 5) for f in fams},
                y_tight=int(y_tight), y_loose=int(y_loose),
                gain_median=gain_med, argmax_gain_stratum=argmax_stratum,
                interactions=inter, interactions_SHUFFLE=inter_sh, sscs=sscs)


def frac(cnt, tot):
    return round(cnt / tot, 4) if tot else None


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    manifest = json.load(open(DATA_MANIFEST))
    models_meta = manifest["models"]           # short -> dict(generation, klass, ...)
    base = load_base()
    print(f"WBM base rows {len(base)}; roster models {len(models_meta)}", flush=True)

    per_model = {}
    for short in sorted(models_meta):
        pred_path = os.path.join(ROSTER_DIR, f"{short}_pred.csv")
        if not os.path.exists(pred_path):
            print(f"  skip {short}: no pred csv", flush=True)
            continue
        r = analyze_model(base, short, pred_path)
        r["generation"] = models_meta[short]["generation"]
        r["klass"] = models_meta[short]["klass"]
        oh = r["interactions"].get("oxide|halide")
        per_model[short] = r
        ohs = (f"I(ox-hal)={oh['interaction_med']:+.4f} CI{oh['ci95']} excl0={oh['excl0']}"
               if oh else "I(ox-hal)=NA")
        print(f"  {short:16s} [{r['generation']:7s}/{r['klass']:9s}] incl={int(r['included'])} "
              f"MAE={r['mae_form']:.3f} argmax={r['argmax_gain_stratum']} {ohs}", flush=True)

    # ---------- assemble the generational contrast over INCLUDED UIPs ----------
    def get_I(short):
        oh = per_model[short]["interactions"].get("oxide|halide")
        return oh

    incl_uip = [s for s, r in per_model.items() if r["included"] and r["klass"] == "uip"]
    mp = [s for s in incl_uip if per_model[s]["generation"] == "MP"]
    om = [s for s in incl_uip if per_model[s]["generation"] == "OMat"]

    def arm_stats(arm):
        rows = []
        for s in arm:
            oh = get_I(s)
            if oh is None:
                continue
            I = oh["interaction_med"]; e = oh["excl0"]
            rows.append(dict(model=s, I=I, excl0=e,
                             positive_anchored=bool(I > 0 and e),
                             reversed=bool(I < 0 and e),
                             null=bool(not e),
                             argmax_oxide=bool(per_model[s]["argmax_gain_stratum"] == "oxide")))
        n = len(rows)
        return dict(
            n=n, models=[r["model"] for r in rows],
            I_values={r["model"]: r["I"] for r in rows},
            n_positive_anchored=sum(r["positive_anchored"] for r in rows),
            n_reversed=sum(r["reversed"] for r in rows),
            n_null=sum(r["null"] for r in rows),
            n_argmax_oxide=sum(r["argmax_oxide"] for r in rows),
            frac_positive_anchored=frac(sum(r["positive_anchored"] for r in rows), n),
            frac_reversed=frac(sum(r["reversed"] for r in rows), n),
            frac_argmax_oxide=frac(sum(r["argmax_oxide"] for r in rows), n),
            mean_I=round(float(np.mean([r["I"] for r in rows])), 5) if n else None,
            median_I=round(float(np.median([r["I"] for r in rows])), 5) if n else None,
            rows=rows,
        )

    mp_stats = arm_stats(mp)
    om_stats = arm_stats(om)

    # V3 permutation test on mean(I) difference between generations (included UIPs)
    v3 = None
    if mp_stats["n"] >= 2 and om_stats["n"] >= 2:
        I_mp = np.array([get_I(s)["interaction_med"] for s in mp if get_I(s)])
        I_om = np.array([get_I(s)["interaction_med"] for s in om if get_I(s)])
        obs = float(I_mp.mean() - I_om.mean())
        pool = np.concatenate([I_mp, I_om]); nmp = len(I_mp)
        rng = np.random.default_rng(PERM_SEED)
        cnt = 0
        for _ in range(PERM):
            rng.shuffle(pool)
            if abs(pool[:nmp].mean() - pool[nmp:].mean()) >= abs(obs) - 1e-12:
                cnt += 1
        # bootstrap CI of the gap
        bs = []
        for _ in range(2000):
            a = I_mp[rng.integers(0, len(I_mp), len(I_mp))]
            b = I_om[rng.integers(0, len(I_om), len(I_om))]
            bs.append(a.mean() - b.mean())
        v3 = dict(observed_gap_meanI=round(obs, 5), perm_p=round((cnt + 1) / (PERM + 1), 5),
                  gap_ci95=[round(float(np.percentile(bs, 2.5)), 5), round(float(np.percentile(bs, 97.5)), 5)],
                  n_mp=int(nmp), n_omat=int(len(I_om)))

    # ---------- multiplicity over the included-UIP family (all 15 pairs) ----------
    fam_cells = []
    for s in incl_uip:
        for pair, cell in per_model[s]["interactions"].items():
            fam_cells.append(dict(model=s, generation=per_model[s]["generation"], pair=pair,
                                  interaction_med=cell["interaction_med"], excl0=cell["excl0"],
                                  p_raw=cell["p_raw"]))
    def multiplicity(cells):
        if not cells:
            return dict(n=0)
        p = [c["p_raw"] for c in cells]
        bh = benjamini_hochberg(p, alpha=0.05); holm = holm_bonferroni(p, alpha=0.05)
        for c, rb, rh, pb, ph in zip(cells, bh["reject"], holm["reject"], bh["adjusted_p"], holm["adjusted_p"]):
            c["reject_bh_q05"] = bool(rb); c["reject_holm_a05"] = bool(rh)
            c["p_bh"] = round(float(pb), 6); c["p_holm"] = round(float(ph), 6)
        floor = 2.0 / (N_BOOT + 1)
        return dict(n=len(cells), n_ci_excl0=int(sum(c["excl0"] for c in cells)),
                    n_bh_q05=int(bh["reject"].sum()), n_holm_a05=int(holm["reject"].sum()),
                    pvalue_floor=round(floor, 6), holm_resolution_limited=bool(floor > 0.05 / len(cells)))
    mult_full = multiplicity(fam_cells)
    oh_cells = [c for c in fam_cells if c["pair"] == "oxide|halide"]
    mult_oxhal = multiplicity([dict(c) for c in oh_cells])

    # ---------- shuffle-null hygiene over the included-UIP family ----------
    sh_total = 0; sh_excl0 = 0
    for s in incl_uip:
        for pair, cell in per_model[s]["interactions_SHUFFLE"].items():
            sh_total += 1; sh_excl0 += int(cell["excl0"])
    shuffle_clean = sh_excl0 <= max(1, int(0.05 * max(1, sh_total)))

    # ---------- V1 / V2 verdicts (prereg §5) ----------
    fp_mp = mp_stats["frac_positive_anchored"] or 0.0
    fp_om = om_stats["frac_positive_anchored"] or 0.0
    fr_om = om_stats["frac_reversed"] or 0.0
    fa_mp = mp_stats["frac_argmax_oxide"] or 0.0

    if om_stats["n"] < 5:
        v_overall = "UNDERPOWERED (N_OMat<5)"
        v1 = v2 = "N/A"
    else:
        v1 = ("CONFIRMED" if fp_mp >= 0.60 else "WEAKENED" if fp_mp >= 0.30 else "FAILED")
        mp_anchored = fp_mp >= 0.60
        if abs(fp_mp - fp_om) < 0.20:
            v2 = "NO-GENERATIONAL-EFFECT (honest null)"
        elif mp_anchored and fp_om <= 0.40 and fr_om >= 0.40:
            v2 = "CONFIRMED-REVERSAL"
        elif mp_anchored and fp_om <= 0.40:
            v2 = "CONFIRMED-DISSOLUTION"
        elif fp_om > 0.60:
            v2 = "IDIOSYNCRATIC-DISSENTER"
        else:
            v2 = "PARTIAL / INCONCLUSIVE"
        v_overall = v2

    verdicts = dict(
        V1_distributional_MP=dict(verdict=v1, frac_positive_anchored_MP=fp_mp,
                                  frac_argmax_oxide_MP=fa_mp),
        V2_generational=dict(verdict=v2, frac_positive_anchored_MP=fp_mp,
                             frac_positive_anchored_OMat=fp_om, frac_reversed_OMat=fr_om),
        V3_permutation=v3,
        shuffle_null_clean=bool(shuffle_clean),
        overall=v_overall,
    )

    result = dict(
        analysis="MT29 roster-expansion generational contrast of oxide-anchored value-of-abstention",
        prereg="research/results/MT29/mt29_roster_expansion_PREREG-2026-07-13.md",
        seed=SEED, n_boot=N_BOOT, perm_reps=PERM, perm_seed=PERM_SEED,
        inclusion_rule=dict(min_called_stable_per_stratum=MIN_CS, min_coverage=MIN_COV),
        headline_pair="oxide|halide",
        strata=FAM_ORDER,
        n_models_total=len(per_model),
        n_included_uip=len(incl_uip),
        generation_counts=dict(
            included_uip_MP=mp_stats["n"], included_uip_OMat=om_stats["n"],
            all_MP=sum(1 for r in per_model.values() if r["generation"] == "MP"),
            all_OMat=sum(1 for r in per_model.values() if r["generation"] == "OMat")),
        MP_arm=mp_stats, OMat_arm=om_stats,
        verdicts=verdicts,
        multiplicity_full_family=mult_full,
        multiplicity_oxide_halide=mult_oxhal,
        shuffle_null=dict(n_cells=sh_total, n_excl0=sh_excl0, clean=bool(shuffle_clean)),
        per_model=per_model,
        provenance=dict(timestamp_utc=datetime.now(timezone.utc).isoformat(),
                        wbm_sha256=sha256(WBM),
                        python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__),
    )
    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)

    # manifest with input sha256s
    inputs = {"2023-12-13-wbm-summary.csv.gz": sha256(WBM)}
    for s in per_model:
        pp = os.path.join(ROSTER_DIR, f"{s}_pred.csv")
        if os.path.exists(pp):
            inputs[f"{s}_pred.csv"] = sha256(pp)
    man = dict(cmd=" ".join([sys.executable] + sys.argv),
               script_sha256=sha256(os.path.abspath(__file__)),
               seed=SEED, n_boot=N_BOOT, inputs=inputs, output_sha256=sha256(OUT_JSON),
               versions=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__),
               platform=platform.platform())
    with open(OUT_MANIFEST, "w") as f:
        json.dump(man, f, indent=2)

    # console digest
    print("\n=== GENERATIONAL CONTRAST (included UIPs) ===", flush=True)
    print(f"  MP-gen UIPs   n={mp_stats['n']}: positive-anchored {mp_stats['n_positive_anchored']}/{mp_stats['n']} "
          f"(frac {fp_mp}), argmax-oxide {mp_stats['n_argmax_oxide']}/{mp_stats['n']}, mean I={mp_stats['mean_I']}", flush=True)
    print(f"  OMat-gen UIPs n={om_stats['n']}: positive-anchored {om_stats['n_positive_anchored']}/{om_stats['n']} "
          f"(frac {fp_om}), reversed {om_stats['n_reversed']}/{om_stats['n']}, null {om_stats['n_null']}, mean I={om_stats['mean_I']}", flush=True)
    if v3:
        print(f"  V3 permutation: gap(meanI MP-OMat)={v3['observed_gap_meanI']} p={v3['perm_p']} CI{v3['gap_ci95']}", flush=True)
    print(f"  multiplicity (UIP family {mult_full['n']} cells): CI-excl0 {mult_full['n_ci_excl0']}, "
          f"BH-FDR {mult_full['n_bh_q05']}, Holm {mult_full['n_holm_a05']}"
          f"{' [Holm res-limited]' if mult_full['holm_resolution_limited'] else ''}", flush=True)
    print(f"  shuffle-null: {sh_excl0}/{sh_total} excl0 (clean={shuffle_clean})", flush=True)
    print(f"\n  V1 (MP distributional): {v1}", flush=True)
    print(f"  V2 (generational):      {v2}", flush=True)
    print(f"  OVERALL:                {v_overall}", flush=True)
    print(f"\nWrote {OUT_JSON}\nWrote {OUT_MANIFEST}", flush=True)


if __name__ == "__main__":
    main()
