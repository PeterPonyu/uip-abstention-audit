#!/usr/bin/env python
"""MT29 Stage-2 — ROBUSTNESS of the corrected matched-yield stratified-abstention interaction.

Stage-1 SUCCESS: the stratum x coverage selective-abstention interaction (oxide highest
abstention-benefit, halide/intermetallic lowest) survives genuine anion-class strata AND the
MT28 matched-stable-call-YIELD control (common absolute yield budget Y across strata) with a
clean shuffle-null (48/60 CI-excl-0; shuffle 0/60). See mt29_stage1_matched_yield_fix.py.

Stage-2 GATE asks whether that interaction is ROBUST or driven by a few dominant element
families / a single WBM acquisition round:

  GATE 1 — LEAVE-ONE-ELEMENT-OUT (LOEO): for each dominant element E in turn (O, plus the most
    common cations + the anion-formers that DEFINE the strata), DROP every WBM structure whose
    formula contains E, then recompute the corrected matched-yield interaction on the surviving
    rows. If the oxide-vs-intermetallic (and the other) abstention-benefit gaps were an artifact
    of a handful of element families, removing one collapses the interaction (CI includes 0 for
    most cells). Removing O is the strongest test: it removes the entire oxide stratum's
    defining anion, so we additionally hold out O and confirm the NON-oxide interaction structure
    (intermetallic-vs-halide etc.) still fires.

  GATE 2 — WBM-ROUND (time-like) cross-split: WBM was acquired in 5 sequential rounds
    (material_id = wbm-{round}-{n}); later rounds are substitutions on earlier discoveries, so
    rounds are a genuine temporal / distribution-shift axis. Recompute the interaction WITHIN
    each round 1..5 separately. Temporal robustness = the interaction keeps firing in the
    majority of rounds, not just pooled.

Same controls as Stage-1: COMMON ABSOLUTE matched-yield budget across strata (per model, per
split), shuffle-null (permute confidence within each stratum's called-stable set), 1000-boot
percentile CIs.

PREREGISTERED SUCCESS: the stratum x coverage interaction stays CI-excluding-0 for the MAJORITY
of (model x stratum-pair) cells under BOTH the LOEO splits AND the WBM-round splits, with
shuffle-null clean (<5% false-positive). KILL: the interaction collapses (CI includes 0 for most
cells) once a dominant element is removed OR across rounds.

CPU/pandas only. No GPU, no downloads, no tokens. On-disk cached Matbench-Discovery preds.
Seed 20260621, 1000-boot CIs.
"""
import os, re, json, hashlib, platform, subprocess, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mt29_stage1_chem_yield import (
    load, MODELS, SEED, N_BOOT, OUT_DIR, ci95, excl0, elements_of, anion_family, DATA, UIP, sha256,
)

RNG = np.random.default_rng(SEED)
FAM_ORDER = ['oxide', 'intermetallic', 'chalcogenide', 'halide', 'pnictide', 'other']
MIN_STRATUM = 500            # min rows in a stratum within a split to test it
MIN_CALLED_STABLE = 40       # min called-stable in a stratum so a yield budget is meaningful
OUT_JSON = os.path.join(OUT_DIR, 'mt29_stage2_robustness_result.json')
MANIFEST = os.path.join(OUT_DIR, 'mt29_stage2_robustness_manifest.json')


# ----------------------------- corrected matched-yield machinery (same as Stage-1 fix) -----------------------------

def daf_top_y(conf_cs, st_cs, target_y, base_rate):
    """conf_cs/st_cs: confidence & truth over the CALLED-STABLE structures of a stratum.
    Take the top target_y by confidence; DAF = precision / base_rate."""
    n = len(conf_cs)
    if n == 0 or target_y <= 0:
        return np.nan
    y = min(int(target_y), n)
    order = np.argsort(-conf_cs)[:y]
    prec = float(st_cs[order].sum() / y)
    return prec / base_rate if base_rate > 0 else np.nan


def boot_yield_gain(conf_cs, st_cs, base_rate, y_tight, y_loose, shuffle=False):
    """Bootstrap matched-yield abstention gain = DAF(top y_tight) - DAF(top y_loose),
    resampling WITHIN the called-stable set. y_tight/y_loose are ABSOLUTE counts common
    across strata."""
    n = len(conf_cs)
    if n == 0:
        return np.array([])
    out = np.empty(N_BOOT)
    for b in range(N_BOOT):
        bs = RNG.integers(0, n, n)
        c = conf_cs[bs].copy()
        s = st_cs[bs]
        if shuffle:
            RNG.shuffle(c)
        out[b] = daf_top_y(c, s, y_tight, base_rate) - daf_top_y(c, s, y_loose, base_rate)
    return out[~np.isnan(out)]


def interaction_on_subset(base, mask, split_label):
    """Run the corrected matched-yield interaction (real + shuffle) on the rows of `base`
    selected by boolean `mask`. Returns a dict with the per-model budgets, the interaction
    records, the shuffle records, and the excl0 counts. Strata with too few rows / too few
    called-stable in this subset are skipped (reported in 'strata_used')."""
    sub = base[mask].reset_index(drop=True)
    eft = sub['e_form_per_atom_mp2020_corrected'].values
    ht = sub['e_above_hull_mp2020_corrected_ppd_mp'].values
    true_stable = ht < 0.0
    fam_vals = sub['family'].values

    # strata with enough rows in this subset
    fam_counts = {f: int((fam_vals == f).sum()) for f in FAM_ORDER}
    fams = [f for f in FAM_ORDER if fam_counts[f] >= MIN_STRATUM]
    fam_idx = {f: np.where(fam_vals == f)[0] for f in fams}

    pred_hull = {m: ht + (sub[f'eform_{m}'].values - eft) for m in MODELS}
    conf = {m: np.abs(pred_hull[m]) for m in MODELS}
    pred_stable = {m: pred_hull[m] < 0.0 for m in MODELS}

    per_model = {}
    inter_real = []
    inter_shuf = []
    n_real = 0
    n_shuf = 0
    n_cells = 0

    for m in MODELS:
        cs_conf = {}; cs_st = {}; br = {}; total_cs = {}
        usable = []
        for f in fams:
            idx = fam_idx[f]
            sp = pred_stable[m][idx]
            cs = np.where(sp)[0]
            cs_conf[f] = conf[m][idx][cs]
            cs_st[f] = true_stable[idx][cs]
            br[f] = float(true_stable[idx].mean())
            total_cs[f] = len(cs)
            if len(cs) >= MIN_CALLED_STABLE and br[f] > 0:
                usable.append(f)
        if len(usable) < 2:
            per_model[m] = {'note': 'fewer than 2 usable strata in this split',
                            'total_called_stable': {f: int(total_cs[f]) for f in fams}}
            continue
        # common absolute yield budget across the USABLE strata of this split
        y_loose = min(total_cs[f] for f in usable)
        y_tight = max(1, y_loose // 2)
        per_model[m] = {
            'y_loose': int(y_loose), 'y_tight': int(y_tight),
            'usable_strata': usable,
            'total_called_stable': {f: int(total_cs[f]) for f in fams},
            'base_rate_stable': {f: round(br[f], 5) for f in fams},
        }
        gains = {f: boot_yield_gain(cs_conf[f], cs_st[f], br[f], y_tight, y_loose, False) for f in usable}
        gains_sh = {f: boot_yield_gain(cs_conf[f], cs_st[f], br[f], y_tight, y_loose, True) for f in usable}
        per_model[m]['gain_median'] = {f: round(float(np.median(gains[f])), 5) for f in usable
                                       if len(gains[f]) > 0}
        for i in range(len(usable)):
            for j in range(i + 1, len(usable)):
                a, b = usable[i], usable[j]
                L = min(len(gains[a]), len(gains[b]))
                if L < 100:
                    continue
                n_cells += 1
                d = gains[a][:L] - gains[b][:L]
                ci = ci95(d); e = excl0(ci); n_real += int(e)
                inter_real.append(dict(split=split_label, model=m, stratumA=a, stratumB=b,
                                       gainA_med=round(float(np.median(gains[a])), 5),
                                       gainB_med=round(float(np.median(gains[b])), 5),
                                       interaction_med=round(float(np.median(d)), 5),
                                       interaction_ci95=[round(ci[0], 5), round(ci[1], 5)],
                                       excludes_0=e))
                Ls = min(len(gains_sh[a]), len(gains_sh[b]))
                if Ls >= 100:
                    ds = gains_sh[a][:Ls] - gains_sh[b][:Ls]
                    cis = ci95(ds); es = excl0(cis); n_shuf += int(es)
                    inter_shuf.append(dict(split=split_label, model=m, stratumA=a, stratumB=b,
                                           interaction_med=round(float(np.median(ds)), 5),
                                           interaction_ci95=[round(cis[0], 5), round(cis[1], 5)],
                                           excludes_0=es))

    return {
        'split': split_label,
        'n_rows': int(mask.sum()),
        'strata_used': fams,
        'fam_counts': fam_counts,
        'per_model_budgets': per_model,
        'interactions': inter_real,
        'interactions_SHUFFLE': inter_shuf,
        'n_cells': n_cells,
        'n_excl0': n_real,
        'n_shuffle_excl0': n_shuf,
        'majority_excl0': bool(n_cells > 0 and n_real > n_cells / 2),
        'shuffle_clean': bool(n_shuf <= max(1, int(0.05 * max(1, len(inter_shuf))))),
    }


# ----------------------------- main -----------------------------

def dominant_elements(base, top_n=8):
    """Most common elements across all formulas (the families whose removal would most plausibly
    collapse an element-driven interaction). Always includes the anion-formers that define the
    strata so the LOEO directly probes the strata-defining chemistry."""
    from collections import Counter
    cnt = Counter()
    for f in base['formula'].values:
        cnt.update(set(elements_of(f)))
    common = [e for e, _ in cnt.most_common(top_n)]
    must = ['O', 'F', 'S', 'N', 'P']   # oxide/halide/chalcogenide/pnictide anion-formers
    for e in must:
        if e not in common:
            common.append(e)
    return common, dict(cnt.most_common(20))


def main():
    base = load()
    # WBM round from material_id (wbm-{round}-{n})
    base['wbm_round'] = base['material_id'].str.extract(r'wbm-(\d+)-')[0].astype(int)

    print(f"Loaded {len(base)} rows.", flush=True)
    print(f"Anion-family counts: {base['family'].value_counts().to_dict()}", flush=True)
    print(f"WBM round counts: {base['wbm_round'].value_counts().sort_index().to_dict()}", flush=True)

    results = {'meta': {
        'story': 'G003-s2-materials-mt29-loeo',
        'stage': 'Stage-2 robustness (LOEO + WBM-round) of corrected matched-yield interaction',
        'seed': SEED, 'n_boot': N_BOOT, 'models': MODELS, 'strata_order': FAM_ORDER,
        'n_rows_total': int(len(base)),
        'control': 'COMMON ABSOLUTE matched-yield budget Y across strata within EACH split '
                   '(per model). DAF(top Y_tight) - DAF(top Y_loose), Y identical across strata; '
                   'Y_loose = min over usable strata of total called-stable, Y_tight = Y_loose//2.',
        'min_stratum_rows': MIN_STRATUM, 'min_called_stable': MIN_CALLED_STABLE,
        'loeo_rule': 'drop every structure whose formula contains element E, recompute interaction.',
        'round_rule': 'restrict to WBM round r (material_id wbm-r-n), recompute interaction.',
        'success_rule': 'interaction CI-excludes-0 for MAJORITY of (model x stratum-pair) cells '
                        'under BOTH LOEO and WBM-round splits, shuffle-null clean (<5% FP).',
    }}

    # ---------------- GATE 1: leave-one-element-out ----------------
    elems, elem_freq = dominant_elements(base, top_n=8)
    results['meta']['dominant_elements_tested'] = elems
    results['meta']['element_frequency_top20'] = {k: int(v) for k, v in elem_freq.items()}
    print(f"\n=== GATE 1: LEAVE-ONE-ELEMENT-OUT ({elems}) ===", flush=True)

    has_elem = {e: base['formula'].apply(lambda fo, e=e: e in set(elements_of(fo))).values
                for e in elems}

    loeo = {}
    for e in elems:
        mask = ~has_elem[e]
        res = interaction_on_subset(base, mask, f'LOEO_drop_{e}')
        loeo[e] = res
        print(f"  drop {e:2s}: n={res['n_rows']:6d} strata={res['strata_used']}  "
              f"excl0={res['n_excl0']}/{res['n_cells']}  shuffle={res['n_shuffle_excl0']}/"
              f"{len(res['interactions_SHUFFLE'])}  majority={res['majority_excl0']}", flush=True)
    results['gate1_loeo'] = loeo

    # ---------------- GATE 2: WBM-round cross-split ----------------
    print(f"\n=== GATE 2: WBM-ROUND cross-split (rounds 1..5) ===", flush=True)
    rounds = {}
    for r in sorted(base['wbm_round'].unique()):
        mask = (base['wbm_round'] == r).values
        res = interaction_on_subset(base, mask, f'round_{r}')
        rounds[int(r)] = res
        print(f"  round {r}: n={res['n_rows']:6d} strata={res['strata_used']}  "
              f"excl0={res['n_excl0']}/{res['n_cells']}  shuffle={res['n_shuffle_excl0']}/"
              f"{len(res['interactions_SHUFFLE'])}  majority={res['majority_excl0']}", flush=True)
    results['gate2_rounds'] = rounds

    # ---------------- aggregate gate verdict ----------------
    loeo_pass = sum(1 for e in elems if loeo[e]['majority_excl0'] and loeo[e]['shuffle_clean'])
    loeo_total = len(elems)
    round_pass = sum(1 for r in rounds if rounds[r]['majority_excl0'] and rounds[r]['shuffle_clean'])
    round_total = len(rounds)

    loeo_excl0_total = sum(loeo[e]['n_excl0'] for e in elems)
    loeo_cells_total = sum(loeo[e]['n_cells'] for e in elems)
    loeo_shuf_total = sum(loeo[e]['n_shuffle_excl0'] for e in elems)
    loeo_shuf_cells = sum(len(loeo[e]['interactions_SHUFFLE']) for e in elems)
    round_excl0_total = sum(rounds[r]['n_excl0'] for r in rounds)
    round_cells_total = sum(rounds[r]['n_cells'] for r in rounds)
    round_shuf_total = sum(rounds[r]['n_shuffle_excl0'] for r in rounds)
    round_shuf_cells = sum(len(rounds[r]['interactions_SHUFFLE']) for r in rounds)

    # GATE: majority of LOEO splits keep a majority interaction (robust to element removal)
    #       AND majority of rounds keep a majority interaction (temporally robust),
    #       shuffle clean throughout.
    loeo_robust = loeo_pass > loeo_total / 2
    round_robust = round_pass > round_total / 2
    shuffle_clean_all = (loeo_shuf_total <= max(1, int(0.05 * max(1, loeo_shuf_cells)))
                         and round_shuf_total <= max(1, int(0.05 * max(1, round_shuf_cells))))

    if loeo_robust and round_robust and shuffle_clean_all:
        verdict = 'SUCCESS'
    elif (not loeo_robust) or (not round_robust):
        verdict = 'KILL'
    else:
        verdict = 'AMBIGUOUS'   # robust but shuffle dirty

    results['summary'] = {
        'verdict': verdict,
        'loeo_splits_passing': f'{loeo_pass}/{loeo_total}',
        'loeo_interaction_excl0': f'{loeo_excl0_total}/{loeo_cells_total}',
        'loeo_shuffle_excl0': f'{loeo_shuf_total}/{loeo_shuf_cells}',
        'round_splits_passing': f'{round_pass}/{round_total}',
        'round_interaction_excl0': f'{round_excl0_total}/{round_cells_total}',
        'round_shuffle_excl0': f'{round_shuf_total}/{round_shuf_cells}',
        'loeo_robust_majority_of_splits': bool(loeo_robust),
        'round_robust_majority_of_rounds': bool(round_robust),
        'shuffle_null_clean': bool(shuffle_clean_all),
    }

    print(f"\n=== STAGE-2 ROBUSTNESS SUMMARY ===", flush=True)
    print(f"  LOEO splits passing (majority-excl0 + clean shuffle): {loeo_pass}/{loeo_total}", flush=True)
    print(f"  LOEO interaction excl0 (pooled cells):                {loeo_excl0_total}/{loeo_cells_total}", flush=True)
    print(f"  LOEO shuffle excl0:                                   {loeo_shuf_total}/{loeo_shuf_cells}", flush=True)
    print(f"  WBM-round splits passing:                             {round_pass}/{round_total}", flush=True)
    print(f"  WBM-round interaction excl0 (pooled cells):           {round_excl0_total}/{round_cells_total}", flush=True)
    print(f"  WBM-round shuffle excl0:                              {round_shuf_total}/{round_shuf_cells}", flush=True)
    print(f"  VERDICT: {verdict}", flush=True)

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_JSON, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nWrote {OUT_JSON}", flush=True)

    try:
        git_sha = subprocess.check_output(
            ['git', '-C', '/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research', 'rev-parse', 'HEAD'],
            text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        git_sha = None
    manifest = {
        'cmd': ' '.join([sys.executable] + sys.argv),
        'script_sha256': sha256(os.path.abspath(__file__)),
        'git_head': git_sha, 'seed': SEED, 'n_boot': N_BOOT,
        'inputs': {os.path.basename(DATA): sha256(DATA),
                   **{f'{m}_pred.csv': sha256(os.path.join(UIP, f'{m}_pred.csv')) for m in MODELS}},
        'output_sha256': sha256(OUT_JSON),
        'versions': {'python': platform.python_version(), 'numpy': np.__version__,
                     'pandas': pd.__version__},
        'platform': platform.platform(),
    }
    with open(MANIFEST, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote {MANIFEST}", flush=True)


if __name__ == '__main__':
    main()
