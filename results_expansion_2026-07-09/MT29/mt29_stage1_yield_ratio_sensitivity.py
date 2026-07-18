#!/usr/bin/env python
"""MT29 Stage-1 SENSITIVITY — Y_tight/Y_loose ratio sweep for the corrected matched-yield
stratified-abstention interaction.

mt29_stage1_matched_yield_fix.py fixes Y_tight = Y_loose // 2 (ratio 0.5) once, post hoc, with
no sensitivity sweep reported. This script reruns the IDENTICAL matched-yield machinery
(same cached WBM summary + UIP prediction CSVs, same seed, same 1000-boot CIs) for a small
grid of alternative tight/loose ratios --- 1/3, 0.4, 0.5 (baseline), 0.6 --- and reports
whether the headline 48/60 CI-excludes-0 interaction count and the specific CHGNet
oxide-vs-halide interaction survive.

No new data or training: reads the same on-disk cached Matbench-Discovery predictions as
mt29_stage1_matched_yield_fix.py.

Seed 20260621, 1000-boot percentile CIs.
"""
import os, json
import numpy as np
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mt29_stage1_chem_yield import load, MODELS, SEED, N_BOOT, OUT_DIR, ci95, excl0, sha256, DATA, UIP

FAM_ORDER = ['oxide', 'intermetallic', 'chalcogenide', 'halide', 'pnictide', 'other']
OUT_JSON = os.path.join(OUT_DIR, 'mt29_stage1_yield_ratio_sensitivity_result.json')
RATIOS = [1.0 / 3.0, 0.4, 0.5, 0.6]


def daf_top_y(conf_cs, st_cs, target_y, base_rate):
    n = len(conf_cs)
    if n == 0 or target_y <= 0:
        return np.nan
    y = min(int(target_y), n)
    order = np.argsort(-conf_cs)[:y]
    prec = float(st_cs[order].sum() / y)
    return prec / base_rate if base_rate > 0 else np.nan


def boot_yield_gain(rng, conf_cs, st_cs, base_rate, y_tight, y_loose, shuffle=False):
    n = len(conf_cs)
    out = np.empty(N_BOOT)
    for b in range(N_BOOT):
        bs = rng.integers(0, n, n)
        c = conf_cs[bs].copy()
        s = st_cs[bs]
        if shuffle:
            rng.shuffle(c)
        out[b] = daf_top_y(c, s, y_tight, base_rate) - daf_top_y(c, s, y_loose, base_rate)
    return out[~np.isnan(out)]


def run_one_ratio(base, ratio):
    """Same matched-yield interaction as mt29_stage1_matched_yield_fix.py, but with
    y_tight = max(1, round(y_loose * ratio)) instead of the hardcoded y_loose // 2."""
    # fresh RNG per ratio, same seed, so each ratio's bootstrap draws are independently
    # reproducible and comparable to the baseline script's own RNG stream.
    rng = np.random.default_rng(SEED)
    eft = base['e_form_per_atom_mp2020_corrected'].values
    ht = base['e_above_hull_mp2020_corrected_ppd_mp'].values
    true_stable = ht < 0.0
    fams = FAM_ORDER
    fam_idx = {f: np.where(base['family'].values == f)[0] for f in fams}

    pred_hull = {m: ht + (base[f'eform_{m}'].values - eft) for m in MODELS}
    conf = {m: np.abs(pred_hull[m]) for m in MODELS}
    pred_stable = {m: pred_hull[m] < 0.0 for m in MODELS}

    per_model = {}
    inter_real = []
    inter_shuf = []
    n_real = 0
    n_shuf = 0
    for m in MODELS:
        cs_conf = {}; cs_st = {}; br = {}; total_cs = {}
        for f in fams:
            idx = fam_idx[f]
            sp = pred_stable[m][idx]
            cs = np.where(sp)[0]
            cs_conf[f] = conf[m][idx][cs]
            cs_st[f] = true_stable[idx][cs]
            br[f] = float(true_stable[idx].mean())
            total_cs[f] = len(cs)
        y_loose = min(total_cs.values())
        y_tight = max(1, int(round(y_loose * ratio)))
        per_model[m] = {'y_loose': int(y_loose), 'y_tight': int(y_tight), 'ratio': ratio}
        gains = {f: boot_yield_gain(rng, cs_conf[f], cs_st[f], br[f], y_tight, y_loose, False) for f in fams}
        gains_sh = {f: boot_yield_gain(rng, cs_conf[f], cs_st[f], br[f], y_tight, y_loose, True) for f in fams}
        per_model[m]['gain_median'] = {f: round(float(np.median(gains[f])), 5) for f in fams}
        for i in range(len(fams)):
            for j in range(i + 1, len(fams)):
                a, b = fams[i], fams[j]
                L = min(len(gains[a]), len(gains[b]))
                if L < 100:
                    continue
                d = gains[a][:L] - gains[b][:L]
                ci = ci95(d); e = excl0(ci); n_real += int(e)
                rec = dict(model=m, stratumA=a, stratumB=b,
                           gainA_med=round(float(np.median(gains[a])), 5),
                           gainB_med=round(float(np.median(gains[b])), 5),
                           interaction_med=round(float(np.median(d)), 5),
                           interaction_ci95=[round(ci[0], 5), round(ci[1], 5)],
                           excludes_0=e)
                inter_real.append(rec)
                Ls = min(len(gains_sh[a]), len(gains_sh[b]))
                if Ls >= 100:
                    ds = gains_sh[a][:Ls] - gains_sh[b][:Ls]
                    cis = ci95(ds); es = excl0(cis); n_shuf += int(es)
                    inter_shuf.append(dict(model=m, stratumA=a, stratumB=b,
                                           interaction_med=round(float(np.median(ds)), 5),
                                           interaction_ci95=[round(cis[0], 5), round(cis[1], 5)],
                                           excludes_0=es))

    shuffle_clean = n_shuf <= max(1, int(0.05 * max(1, len(inter_shuf))))
    # pull out the specific CHGNet oxide-vs-halide cell called out in the manuscript
    chgnet_ox_hal = next((x for x in inter_real if x['model'] == 'chgnet'
                          and {x['stratumA'], x['stratumB']} == {'oxide', 'halide'}), None)
    return {
        'ratio': ratio,
        'per_model_budgets': per_model,
        'n_pairs': len(inter_real),
        'matched_yield_excl0': f'{n_real}/{len(inter_real)}',
        'matched_yield_SHUFFLE_excl0': f'{n_shuf}/{len(inter_shuf)}',
        'shuffle_null_clean': bool(shuffle_clean),
        'chgnet_oxide_vs_halide': chgnet_ox_hal,
        'interactions_matched_yield': inter_real,
        'interactions_matched_yield_SHUFFLE': inter_shuf,
    }


def main():
    base = load()
    results = {'meta': {
        'story': 'G007-s1-materials-mt29-yield-ratio-sensitivity',
        'stage': 'Stage-1 supplementary robustness: Y_tight/Y_loose ratio sweep',
        'seed': SEED, 'n_boot': N_BOOT, 'models': MODELS, 'strata': FAM_ORDER,
        'ratios_tested': RATIOS,
        'baseline_ratio': 0.5,
        'note': ('mt29_stage1_matched_yield_fix.py fixes Y_tight = Y_loose // 2 (ratio 0.5) once, '
                 'post hoc, with no sensitivity sweep. This script reruns the identical matched-yield '
                 'machinery for Y_tight = round(Y_loose * ratio) at ratio in {1/3, 0.4, 0.5, 0.6} on '
                 'the same cached WBM predictions to test whether the headline interaction and the '
                 'CHGNet oxide-vs-halide cell survive the choice of ratio.'),
    }}

    by_ratio = {}
    for ratio in RATIOS:
        print(f"=== ratio={ratio:.4f} ===", flush=True)
        res = run_one_ratio(base, ratio)
        by_ratio[f'{ratio:.4f}'] = res
        print(f"  matched-yield excl0: {res['matched_yield_excl0']}  shuffle: "
              f"{res['matched_yield_SHUFFLE_excl0']}  clean={res['shuffle_null_clean']}", flush=True)
        ox_hal = res['chgnet_oxide_vs_halide']
        if ox_hal:
            print(f"  chgnet oxide-vs-halide: int={ox_hal['interaction_med']:+.4f} "
                  f"CI={ox_hal['interaction_ci95']} excludes_0={ox_hal['excludes_0']}", flush=True)
    results['by_ratio'] = by_ratio

    excl0_counts = {r: by_ratio[r]['matched_yield_excl0'] for r in by_ratio}
    ox_hal_survives = {r: bool(by_ratio[r]['chgnet_oxide_vs_halide']
                                and by_ratio[r]['chgnet_oxide_vs_halide']['excludes_0'])
                       for r in by_ratio}
    shuffle_clean_all = all(by_ratio[r]['shuffle_null_clean'] for r in by_ratio)
    results['summary'] = {
        'excl0_by_ratio': excl0_counts,
        'chgnet_oxide_vs_halide_excludes_0_by_ratio': ox_hal_survives,
        'interaction_survives_all_ratios': all(ox_hal_survives.values()),
        'shuffle_clean_all_ratios': shuffle_clean_all,
    }

    print("\n=== SENSITIVITY SUMMARY ===")
    for r in by_ratio:
        print(f"  ratio={r}: excl0={excl0_counts[r]}  chgnet_ox_vs_halide_excl0={ox_hal_survives[r]}")

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_JSON, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nWrote {OUT_JSON}")

    import platform, subprocess
    try:
        git_sha = subprocess.check_output(
            ['git', '-C', '/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research', 'rev-parse', 'HEAD'],
            text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        git_sha = None
    import numpy as _np, pandas as _pd
    manifest = {
        'cmd': f'python3 {os.path.basename(__file__)}',
        'script_sha256': sha256(os.path.abspath(__file__)),
        'git_head': git_sha, 'seed': SEED, 'n_boot': N_BOOT, 'ratios_tested': RATIOS,
        'inputs': {os.path.basename(DATA): sha256(DATA),
                   **{f'{m}_pred.csv': sha256(os.path.join(UIP, f'{m}_pred.csv')) for m in MODELS}},
        'output_sha256': sha256(OUT_JSON),
        'versions': {'python': platform.python_version(), 'numpy': _np.__version__,
                     'pandas': _pd.__version__},
        'platform': platform.platform(),
    }
    manifest_path = os.path.join(OUT_DIR, 'mt29_stage1_yield_ratio_sensitivity_manifest.json')
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote {manifest_path}")


if __name__ == '__main__':
    main()
