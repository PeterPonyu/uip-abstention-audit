#!/usr/bin/env python
"""MAJOR-4 remediation: prototype-BLOCKED (cluster) bootstrap for the Stage-1
matched-yield stratified-abstention interaction.

The frozen Stage-1 CIs (mt29_stage1_matched_yield_fix.py, boot_yield_gain) resample
CALLED-STABLE STRUCTURES i.i.d. within each stratum. WBM is elemental-substitution-
generated, so structures sharing a parent prototype (protostructure_spglib) are
correlated; an i.i.d.-structure bootstrap underestimates variance and can inflate the
count of CI-exclusions. This script re-runs the IDENTICAL matched-yield machinery but
resamples PROTOTYPE CLUSTERS with replacement (block/cluster bootstrap, block =
protostructure_spglib) within each stratum's called-stable set.

Everything except the resampling unit is unchanged and imported from the frozen scripts:
same data load, same strata, same fixed absolute budgets Y_tight/Y_loose, same base
rates, same daf_top_y, same ci95/excl0, same seed, same N_BOOT, same index-paired
interaction difference. A deterministic reproduction check asserts the per-model budgets
and DAF points match the frozen result byte-for-byte before any CI is recomputed.

No massaging: survivors are survivors. Writes result JSON + provenance in this dir.
Run:  MT_DATA_ROOT=~/mt_stage0/data MT_UIP_ROOT=~/mt_uip python3 mt29_prototype_blocked_ci.py
"""
import os, sys, json, hashlib, platform
from datetime import datetime, timezone
import numpy as np
import pandas as pd

os.environ.setdefault('MT_DATA_ROOT', os.path.expanduser('~/mt_stage0/data'))
os.environ.setdefault('MT_UIP_ROOT', os.path.expanduser('~/mt_uip'))
HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
MT29 = os.path.join(REPO_ROOT, 'research', 'results', 'MT29')
sys.path.insert(0, MT29)
from mt29_stage1_chem_yield import load, MODELS, SEED, N_BOOT, ci95, excl0, DATA  # frozen pipeline
from mt29_stage1_matched_yield_fix import daf_top_y, FAM_ORDER                     # frozen DAF

HERE = os.path.dirname(os.path.abspath(__file__))
FROZEN = os.path.join(MT29, 'mt29_stage1_matched_yield_result.json')


def boot_gain_cluster(conf, st, groups, base_rate, y_tight, y_loose, rng, shuffle=False):
    """Cluster bootstrap: resample the ncl prototype groups WITH REPLACEMENT, concat
    their members, take top-Y by confidence, DAF gain = DAF(top y_tight)-DAF(top y_loose)."""
    ncl = len(groups)
    out = np.empty(N_BOOT)
    for b in range(N_BOOT):
        pick = rng.integers(0, ncl, ncl)
        idx = np.concatenate([groups[g] for g in pick])
        c = conf[idx].copy(); s = st[idx]
        if shuffle:
            rng.shuffle(c)
        out[b] = daf_top_y(c, s, y_tight, base_rate) - daf_top_y(c, s, y_loose, base_rate)
    return out[~np.isnan(out)]


def main():
    base = load()
    # attach the prototype label aligned to base rows (merge by material_id, order preserved)
    proto = pd.read_csv(DATA, usecols=['material_id', 'protostructure_spglib'])
    base = base.merge(proto, on='material_id', how='left')
    assert base['protostructure_spglib'].notna().all(), "missing protostructure labels"

    eft = base['e_form_per_atom_mp2020_corrected'].values
    ht = base['e_above_hull_mp2020_corrected_ppd_mp'].values
    true_stable = ht < 0.0
    protos = base['protostructure_spglib'].values
    fams = FAM_ORDER
    fam_idx = {f: np.where(base['family'].values == f)[0] for f in fams}

    pred_hull = {m: ht + (base[f'eform_{m}'].values - eft) for m in MODELS}
    conf = {m: np.abs(pred_hull[m]) for m in MODELS}
    pred_stable = {m: pred_hull[m] < 0.0 for m in MODELS}

    frozen = json.load(open(FROZEN))
    frozen_budgets = frozen['per_model_budgets']
    frozen_inter = {(x['model'], x['stratumA'], x['stratumB']): x
                    for x in frozen['interactions_matched_yield']}

    rng = np.random.default_rng(SEED)
    per_model = {}
    inter = []
    inter_shuf = []
    n_real = 0
    n_shuf = 0
    repro_ok = True
    cluster_diag = {}

    for m in MODELS:
        cs_conf = {}; cs_st = {}; cs_groups = {}; br = {}; total_cs = {}
        ndistinct = {}; maxclu = {}
        for f in fams:
            idx = fam_idx[f]
            sp = pred_stable[m][idx]
            cs = np.where(sp)[0]
            gi = idx[cs]                       # global indices of called-stable structs
            cs_conf[f] = conf[m][gi]
            cs_st[f] = true_stable[gi]
            br[f] = float(true_stable[idx].mean())
            total_cs[f] = len(cs)
            # prototype groups within this called-stable set
            p = protos[gi]
            uniq, inv = np.unique(p, return_inverse=True)
            cs_groups[f] = [np.where(inv == k)[0] for k in range(len(uniq))]
            ndistinct[f] = int(len(uniq))
            maxclu[f] = int(max((len(g) for g in cs_groups[f]), default=0))
        y_loose = min(total_cs.values())
        y_tight = max(1, y_loose // 2)

        # --- deterministic reproduction check vs frozen budgets ---
        fb = frozen_budgets[m]
        chk = {
            'y_loose': int(y_loose) == fb['y_loose'],
            'y_tight': int(y_tight) == fb['y_tight'],
            'base_rate': all(round(br[f], 5) == fb['base_rate_stable'][f] for f in fams),
            'daf_tight': all(round(float(daf_top_y(cs_conf[f], cs_st[f], y_tight, br[f])), 5)
                             == fb['daf_top_y_tight'][f] for f in fams),
            'daf_loose': all(round(float(daf_top_y(cs_conf[f], cs_st[f], y_loose, br[f])), 5)
                             == fb['daf_top_y_loose'][f] for f in fams),
        }
        repro_ok = repro_ok and all(chk.values())

        cluster_diag[m] = {f: {'n_called_stable': total_cs[f], 'n_distinct_proto': ndistinct[f],
                               'mean_structs_per_proto': round(total_cs[f] / ndistinct[f], 3) if ndistinct[f] else None,
                               'max_cluster_size': maxclu[f]} for f in fams}

        gains = {f: boot_gain_cluster(cs_conf[f], cs_st[f], cs_groups[f], br[f], y_tight, y_loose, rng, False) for f in fams}
        gains_sh = {f: boot_gain_cluster(cs_conf[f], cs_st[f], cs_groups[f], br[f], y_tight, y_loose, rng, True) for f in fams}
        per_model[m] = {'y_loose': int(y_loose), 'y_tight': int(y_tight),
                        'repro_check_vs_frozen': chk,
                        'gain_median': {f: round(float(np.median(gains[f])), 5) for f in fams}}

        for i in range(len(fams)):
            for j in range(i + 1, len(fams)):
                a, b = fams[i], fams[j]
                L = min(len(gains[a]), len(gains[b]))
                if L < 100:
                    continue
                d = gains[a][:L] - gains[b][:L]
                ci = ci95(d); e = excl0(ci); n_real += int(e)
                fr = frozen_inter.get((m, a, b), {})
                inter.append(dict(model=m, stratumA=a, stratumB=b,
                                  interaction_med=round(float(np.median(d)), 5),
                                  interaction_ci95=[round(ci[0], 5), round(ci[1], 5)],
                                  excludes_0_blocked=e,
                                  excludes_0_frozen_iid=fr.get('excludes_0'),
                                  frozen_iid_ci95=fr.get('interaction_ci95')))
                Ls = min(len(gains_sh[a]), len(gains_sh[b]))
                if Ls >= 100:
                    ds = gains_sh[a][:Ls] - gains_sh[b][:Ls]
                    cis = ci95(ds); es = excl0(cis); n_shuf += int(es)
                    inter_shuf.append(dict(model=m, stratumA=a, stratumB=b, excludes_0=es))

    # headline cell + flip accounting
    flips_to_null = [x for x in inter if x['excludes_0_frozen_iid'] and not x['excludes_0_blocked']]
    gained = [x for x in inter if (not x['excludes_0_frozen_iid']) and x['excludes_0_blocked']]
    chg_oxhal = next((x for x in inter if x['model'] == 'chgnet' and
                      {x['stratumA'], x['stratumB']} == {'oxide', 'halide'}), None)

    result = {
        'analysis': 'MAJOR-4 prototype-blocked (cluster) bootstrap of Stage-1 matched-yield interaction',
        'block_unit': 'protostructure_spglib (WBM AFLOW prototype label)',
        'seed': SEED, 'n_boot': N_BOOT, 'models': MODELS, 'strata': fams,
        'deterministic_repro_vs_frozen_budgets': bool(repro_ok),
        'summary': {
            'blocked_excl0': f'{n_real}/{len(inter)}',
            'frozen_iid_excl0': frozen['summary']['matched_yield_excl0'],
            'blocked_SHUFFLE_excl0': f'{n_shuf}/{len(inter_shuf)}',
            'n_frozen_cells_lost_under_blocking': len(flips_to_null),
            'n_cells_gained_under_blocking': len(gained),
            'chgnet_oxide_vs_halide_blocked_excl0': (chg_oxhal or {}).get('excludes_0_blocked'),
            'chgnet_oxide_vs_halide_blocked_ci95': (chg_oxhal or {}).get('interaction_ci95'),
            'chgnet_oxide_vs_halide_blocked_median': (chg_oxhal or {}).get('interaction_med'),
        },
        'cells_lost_under_blocking': flips_to_null,
        'cells_gained_under_blocking': gained,
        'per_model': per_model,
        'cluster_diagnostics': cluster_diag,
        'interactions_blocked': inter,
        'provenance': {
            'script': 'results_expansion_2026-07-11/prototype_blocked_cis/mt29_prototype_blocked_ci.py',
            'frozen_compared': 'research/results/MT29/mt29_stage1_matched_yield_result.json',
            'wbm_summary_sha256_head': hashlib.sha256(open(DATA, 'rb').read()).hexdigest()[:16],
            'timestamp_utc': datetime.now(timezone.utc).isoformat(),
            'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__,
        },
    }
    outp = os.path.join(HERE, 'mt29_prototype_blocked_ci_result.json')
    with open(outp, 'w') as f:
        json.dump(result, f, indent=2, default=str)

    # console digest
    print("deterministic repro vs frozen budgets:", repro_ok)
    print(f"blocked excl0: {n_real}/{len(inter)}   (frozen i.i.d.: {frozen['summary']['matched_yield_excl0']})")
    print(f"blocked SHUFFLE excl0: {n_shuf}/{len(inter_shuf)} (want ~0)")
    print(f"cells lost under blocking: {len(flips_to_null)} | gained: {len(gained)}")
    if chg_oxhal:
        print(f"CHGNet oxide-vs-halide: blocked excl0={chg_oxhal['excludes_0_blocked']} "
              f"median={chg_oxhal['interaction_med']} CI{chg_oxhal['interaction_ci95']} "
              f"(frozen i.i.d. CI {chg_oxhal['frozen_iid_ci95']})")
    print("\noxide-stratum clustering (called-stable):")
    for m in MODELS:
        d = cluster_diag[m]['oxide']
        print(f"  {m}: n_cs={d['n_called_stable']} n_proto={d['n_distinct_proto']} "
              f"mean/proto={d['mean_structs_per_proto']} max_cluster={d['max_cluster_size']}")
    print("wrote", outp)


if __name__ == '__main__':
    main()
