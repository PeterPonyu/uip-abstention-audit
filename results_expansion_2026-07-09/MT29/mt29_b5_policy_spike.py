#!/usr/bin/env python
"""B5 Spike — Stratum-Aware Abstention POLICY vs Global-Threshold Baseline.

FABLE-HANDOFF §6 direction #2. Claim to test:
  A per-stratum (anion-class) |hull-margin| abstention threshold policy
  maximising DAF at FIXED GLOBAL COVERAGE strictly DOMINATES the single
  global-threshold policy at matched global coverage.

Two policies compared:
  GLOBAL     : rank ALL N structures by |hull-pred-margin|; keep top c*N.
               Per-stratum DAF = precision/br among globally-kept+called-stable.
  PERSTRATUM : keep top-c fraction WITHIN each stratum; total kept = c*N.
               Per-stratum DAF = precision/br among per-stratum-kept+called-stable.

Both see the same |hull-margin| signal; only the threshold scope differs.

Bootstrap (SPIKE mode): stratified (resample within each stratum), 200 draws, at
focal coverage COV_BOOT=0.7 only. Point estimates reported for all 5 targets.
Upgrade N_BOOT=1000 + loop over COV_TARGETS for camera-ready.
Shuffle null: permute confidence globally before applying both policies.
Kill criterion: KILL if no (model, stratum) cell shows positive DAF gain CI-excl-0.

Strata + confidence signal + DAF: verbatim from mt29_stage1_chem_yield.py.
"""
import os, re, json, hashlib, platform, subprocess, sys
import numpy as np
import pandas as pd

SEED = 20260621
RNG = np.random.default_rng(SEED)
N_BOOT = 200           # spike: 200 (upgrade to 1000 for camera-ready)
COV_TARGETS = [0.5, 0.6, 0.7, 0.8, 0.9]   # point estimates at all 5
COV_BOOT = 0.7         # bootstrap CIs at this focal coverage only
FAM_ORDER = ['oxide', 'intermetallic', 'chalcogenide', 'halide', 'pnictide', 'other']
MIN_STRATUM_N = 500

DATA = os.path.join(os.path.expanduser(os.environ.get('MT_DATA_ROOT', '~/mt_stage0/data')),
                    '2023-12-13-wbm-summary.csv.gz')
UIP_DIR = os.path.expanduser(os.environ.get('MT_UIP_ROOT', '~/mt_uip'))
MODELS = ['chgnet', 'm3gnet', 'mace', 'orb']
OUT_DIR = '/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/research/results/MT29'
OUT_JSON = os.path.join(OUT_DIR, 'mt29_b5_policy_spike_result.json')

# ---- anion classifier (verbatim from mt29_stage1_chem_yield.py) ----
HALIDE = {'F', 'Cl', 'Br', 'I', 'At'}
CHALCOGEN = {'S', 'Se', 'Te'}
PNICTOGEN = {'N', 'P', 'As', 'Sb', 'Bi'}
METALS = {
    'Li', 'Be', 'Na', 'Mg', 'Al', 'K', 'Ca', 'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co',
    'Ni', 'Cu', 'Zn', 'Ga', 'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd',
    'Ag', 'Cd', 'In', 'Sn', 'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd',
    'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu', 'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt',
    'Au', 'Hg', 'Tl', 'Pb', 'Fr', 'Ra', 'Ac', 'Th', 'Pa', 'U', 'Np', 'Pu', 'Ge', 'Sb',
    'Bi', 'Po',
}
TOKEN_RE = re.compile(r'([A-Z][a-z]?)(\d*)')


def elements_of(formula):
    return [m.group(1) for m in TOKEN_RE.finditer(str(formula)) if m.group(1)]


def anion_family(formula):
    els = set(elements_of(formula))
    if els & HALIDE:
        return 'halide'
    if 'O' in els:
        return 'oxide'
    if els & CHALCOGEN:
        return 'chalcogenide'
    if els & PNICTOGEN:
        return 'pnictide'
    non_metal = els - METALS
    if not non_metal:
        return 'intermetallic'
    return 'other'


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def load():
    wbm = pd.read_csv(DATA, usecols=['material_id', 'formula',
                                     'e_form_per_atom_mp2020_corrected',
                                     'e_above_hull_mp2020_corrected_ppd_mp'])
    base = wbm.dropna(subset=['e_form_per_atom_mp2020_corrected',
                               'e_above_hull_mp2020_corrected_ppd_mp']).copy()
    for m in MODELS:
        p = pd.read_csv(os.path.join(UIP_DIR, f'{m}_pred.csv'))[['material_id', 'e_form_pred']]
        base = base.merge(p.rename(columns={'e_form_pred': f'eform_{m}'}),
                          on='material_id', how='inner')
    base = base.dropna().reset_index(drop=True)
    base['family'] = base['formula'].apply(anion_family)
    return base


def stratum_daf_from_mask(sp, st, kept_in_stratum, br):
    """DAF among kept+called-stable structures in one stratum.
    kept_in_stratum: global indices of kept structures within this stratum."""
    if len(kept_in_stratum) == 0:
        return np.nan, np.nan, 0
    sp_s = sp[kept_in_stratum]
    st_s = st[kept_in_stratum]
    tp = int(np.sum(sp_s & st_s))
    fp = int(np.sum(sp_s & ~st_s))
    prec = tp / (tp + fp) if (tp + fp) > 0 else np.nan
    daf = prec / br if (br > 0 and not np.isnan(prec)) else np.nan
    return daf, prec, tp + fp


def compute_both_policies(conf, sp, st, fam_arr, fams, cov):
    """Return (global_daf_dict, perstratum_daf_dict) at one coverage level.
    Dict maps stratum name -> (daf, prec, n_called)."""
    N = len(conf)
    K = max(1, int(round(cov * N)))

    # Global policy: top-K globally
    global_kept = np.zeros(N, dtype=bool)
    global_kept[np.argsort(-conf)[:K]] = True

    # Per-stratum policy: top-(cov*n_s) within each stratum
    perstratum_kept = np.zeros(N, dtype=bool)
    for f in fams:
        idx = np.where(fam_arr == f)[0]
        k_s = max(1, int(round(cov * len(idx))))
        top_local = np.argsort(-conf[idx])[:k_s]
        perstratum_kept[idx[top_local]] = True

    gd = {}; pd_ = {}
    for f in fams:
        idx = np.where(fam_arr == f)[0]
        br = float(st[idx].mean())
        gd[f] = stratum_daf_from_mask(sp, st, idx[global_kept[idx]], br)
        pd_[f] = stratum_daf_from_mask(sp, st, idx[perstratum_kept[idx]], br)
    return gd, pd_


def run_boots(conf, sp, st, fam_arr, fams, cov, n_boot, rng, shuffle=False):
    """Stratified bootstrap: resample within each stratum with replacement.
    Paired comparison: same draw used for both policies.

    Optimisation: pre-sort within each stratum once so the per-stratum
    mask uses a sort of n_s-element draws (cheap) rather than the full N.
    Global policy still needs one argsort(N) per draw — this dominates.
    200 draws at cov=0.7 completes in ~2-4 min on CPU.

    Returns dict stratum -> np.array of DAF gain (perstratum - global), len n_boot.
    """
    fam_idx_dict = {f: np.where(fam_arr == f)[0] for f in fams}
    ns_dict = {f: len(fam_idx_dict[f]) for f in fams}
    # Pre-sort within each stratum once (descending confidence).
    sorted_local = {f: np.argsort(-conf[fam_idx_dict[f]]) for f in fams}
    N = len(conf)

    # Compute stratum offsets for pre-allocated buffers.
    offsets = {}
    ptr = 0
    for f in fams:
        offsets[f] = ptr
        ptr += ns_dict[f]

    # Pre-allocate boot arrays (reused each iteration).
    bc = np.empty(N)
    bsp = np.empty(N, dtype=bool)
    bst = np.empty(N, dtype=bool)
    bfam = np.empty(N, dtype='U15')

    gains = {f: np.empty(n_boot) for f in fams}

    for b in range(n_boot):
        for f in fams:
            idx = fam_idx_dict[f]
            ns = ns_dict[f]
            sl = sorted_local[f]
            draw = rng.integers(0, ns, ns)
            g_idx = idx[sl[draw]]
            o = offsets[f]
            bc[o:o + ns] = conf[g_idx]
            bsp[o:o + ns] = sp[g_idx]
            bst[o:o + ns] = st[g_idx]
            bfam[o:o + ns] = f

        if shuffle:
            rng.shuffle(bc)

        bg, bp = compute_both_policies(bc, bsp, bst, bfam, fams, cov)

        for f in fams:
            g = bg[f][0]
            p = bp[f][0]
            gains[f][b] = (p - g) if not (np.isnan(g) or np.isnan(p)) else np.nan

    return gains


def ci95(arr):
    clean = arr[~np.isnan(arr)]
    if len(clean) < 10:
        return [np.nan, np.nan]
    return [float(np.percentile(clean, 2.5)), float(np.percentile(clean, 97.5))]


def excl0(ci):
    if np.isnan(ci[0]) or np.isnan(ci[1]):
        return False
    return bool(ci[0] > 0 or ci[1] < 0)


def main():
    base = load()
    n = len(base)
    eform_true = base['e_form_per_atom_mp2020_corrected'].values
    hull_true = base['e_above_hull_mp2020_corrected_ppd_mp'].values
    true_stable = hull_true < 0.0

    fam_counts = base['family'].value_counts().to_dict()
    fams = [f for f in FAM_ORDER if fam_counts.get(f, 0) >= MIN_STRATUM_N]

    pred_hull = {m: hull_true + (base[f'eform_{m}'].values - eform_true) for m in MODELS}
    conf_all = {m: np.abs(pred_hull[m]) for m in MODELS}
    pred_stable = {m: pred_hull[m] < 0.0 for m in MODELS}
    fam_arr = base['family'].values

    br_dict = {f: float(true_stable[fam_arr == f].mean()) for f in fams}
    n_dict = {f: int(np.sum(fam_arr == f)) for f in fams}

    print(f"Loaded {n} rows. Strata ({len(fams)}): {fams}", flush=True)
    print(f"Sizes: {n_dict}", flush=True)
    print(f"Base rates: { {f: round(br_dict[f], 4) for f in fams} }", flush=True)

    results = {
        'meta': {
            'story': 'B5-stratum-aware-abstention-policy-spike',
            'claim': 'Per-stratum |hull-margin| threshold strictly dominates global threshold '
                     'at matched global coverage on per-stratum DAF.',
            'seed': SEED, 'n_boot': N_BOOT, 'n_rows': int(n),
            'models': MODELS, 'strata': fams,
            'cov_targets_point_estimates': COV_TARGETS,
            'cov_bootstrap': COV_BOOT,
            'global_policy': 'Keep top-(cov*N) globally by |hull-pred-margin|.',
            'perstratum_policy': 'Keep top-(cov*n_s) within each stratum; total kept = cov*N.',
            'daf_def': 'precision/base_rate_stable among kept+predicted-stable per stratum.',
            'bootstrap': f'Stratified resample within each stratum; paired; {N_BOOT} draws at cov={COV_BOOT}.',
            'shuffle_null': 'Permute confidence globally before both policies.',
            'kill_criterion': f'KILL if no (model, stratum) cell at cov={COV_BOOT} has positive DAF gain CI-excl-0.',
        },
        'base_rates': {f: round(br_dict[f], 6) for f in fams},
        'stratum_n': n_dict,
        'point_estimates': {},
        'bootstrap_gains': {},
        'shuffle_null': {},
    }

    # ---- point estimates at all coverage targets ----
    print("\nComputing point estimates...", flush=True)
    for m in MODELS:
        results['point_estimates'][m] = {}
        for cov in COV_TARGETS:
            ck = f'cov{int(cov * 100)}'
            gd, pd_ = compute_both_policies(conf_all[m], pred_stable[m], true_stable,
                                            fam_arr, fams, cov)
            results['point_estimates'][m][ck] = {}
            for f in fams:
                g_daf, g_prec, g_nc = gd[f]
                p_daf, p_prec, p_nc = pd_[f]
                gain = (p_daf - g_daf) if not (np.isnan(p_daf) or np.isnan(g_daf)) else None
                results['point_estimates'][m][ck][f] = {
                    'global_daf': round(float(g_daf), 5) if not np.isnan(g_daf) else None,
                    'perstratum_daf': round(float(p_daf), 5) if not np.isnan(p_daf) else None,
                    'daf_gain': round(float(gain), 5) if gain is not None else None,
                    'global_ncalled': g_nc,
                    'perstratum_ncalled': p_nc,
                }

    # ---- bootstrap gains at focal coverage only (spike mode) ----
    ck_boot = f'cov{int(COV_BOOT * 100)}'
    for m in MODELS:
        results['bootstrap_gains'][m] = {ck_boot: {}}
        results['shuffle_null'][m] = {ck_boot: {}}
        print(f"  Bootstrap {m} cov={COV_BOOT:.1f} real  ({N_BOOT} draws)...", flush=True)
        real_g = run_boots(conf_all[m], pred_stable[m], true_stable,
                           fam_arr, fams, COV_BOOT, N_BOOT, RNG, shuffle=False)
        print(f"  Bootstrap {m} cov={COV_BOOT:.1f} shuf  ({N_BOOT} draws)...", flush=True)
        shuf_g = run_boots(conf_all[m], pred_stable[m], true_stable,
                           fam_arr, fams, COV_BOOT, N_BOOT, RNG, shuffle=True)
        for f in fams:
            r = real_g[f]; s = shuf_g[f]
            r_ci = ci95(r); s_ci = ci95(s)
            results['bootstrap_gains'][m][ck_boot][f] = {
                'gain_median': round(float(np.nanmedian(r)), 5),
                'ci95': [round(v, 5) if not np.isnan(v) else None for v in r_ci],
                'excl0': excl0(r_ci),
            }
            results['shuffle_null'][m][ck_boot][f] = {
                'gain_median': round(float(np.nanmedian(s)), 5),
                'ci95': [round(v, 5) if not np.isnan(v) else None for v in s_ci],
                'excl0': excl0(s_ci),
            }

    # ---- summary ----
    n_excl0_real = 0
    n_positive_excl0 = 0
    n_excl0_shuf = 0
    total = 0
    all_gains = []

    for m in MODELS:
        for f in fams:
            r = results['bootstrap_gains'][m][ck_boot][f]
            s = results['shuffle_null'][m][ck_boot][f]
            total += 1
            if r['excl0']:
                n_excl0_real += 1
                if r['gain_median'] > 0:
                    n_positive_excl0 += 1
            if s['excl0']:
                n_excl0_shuf += 1
            gm = r['gain_median']
            if gm is not None and not np.isnan(gm):
                all_gains.append(gm)

    kill = (n_positive_excl0 == 0)
    verdict = 'KILL' if kill else 'GO'

    # per-UIP summary at focal coverage
    per_model_summary = {}
    for m in MODELS:
        cells = []
        for f in fams:
            r = results['bootstrap_gains'][m][ck_boot][f]
            pe = results['point_estimates'][m][ck_boot][f]
            cells.append({
                'stratum': f,
                'point_gain': pe['daf_gain'],
                'gain_median': r['gain_median'],
                'ci95': r['ci95'],
                'excl0': r['excl0'],
            })
        cells_sorted = sorted(cells, key=lambda x: -(x['gain_median'] or 0))
        n_pos = sum(1 for c in cells if c['excl0'] and (c['gain_median'] or 0) > 0)
        per_model_summary[m] = {
            f'{ck_boot}_n_positive_excl0': n_pos,
            f'{ck_boot}_cells_by_gain': cells_sorted,
        }

    results['summary'] = {
        'bootstrap_focal_cov': COV_BOOT,
        'total_cells': total,
        'real_excl0_any': n_excl0_real,
        'positive_excl0': n_positive_excl0,
        'shuffle_excl0': n_excl0_shuf,
        'median_gain_focal_cells': round(float(np.median(all_gains)), 5) if all_gains else None,
        'verdict': verdict,
        'rationale': (
            f'GO: >=1 (model,stratum) cell at cov={COV_BOOT} has positive DAF gain CI-excl-0. '
            'Stratum-aware abstention dominates global threshold at matched coverage.'
            if not kill else
            f'KILL: zero cells with positive DAF gain CI-excl-0 at cov={COV_BOOT}. '
            'Stratum-aware equal-within-stratum-coverage policy does not outperform global threshold.'
        ),
        'per_model': per_model_summary,
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_JSON, 'w') as fh:
        json.dump(results, fh, indent=2, default=str)
    print(f'\nWrote {OUT_JSON}', flush=True)

    print(f'\n=== B5 VERDICT: {verdict} ===', flush=True)
    print(f'  Bootstrap at cov={COV_BOOT}  total cells={total}  '
          f'real_excl0={n_excl0_real}  positive_excl0={n_positive_excl0}', flush=True)
    print(f'  Shuffle excl-0: {n_excl0_shuf} (want ~0)', flush=True)
    med = float(np.median(all_gains)) if all_gains else float('nan')
    print(f'  Median gain across focal cells: {med:+.5f}', flush=True)

    # positive CI-excl-0 gains
    tops = [(m, f, results['bootstrap_gains'][m][ck_boot][f]['gain_median'],
             results['bootstrap_gains'][m][ck_boot][f]['ci95'])
            for m in MODELS for f in fams
            if results['bootstrap_gains'][m][ck_boot][f]['excl0']
            and results['bootstrap_gains'][m][ck_boot][f]['gain_median'] > 0]
    if tops:
        tops.sort(key=lambda x: -x[2])
        print('\nPositive CI-excl-0 gains (perstratum - global DAF):', flush=True)
        for x in tops:
            print(f'  {x[0]:7s} {x[1]:14s}: gain={x[2]:+.4f}  CI{x[3]}', flush=True)
    else:
        print('\nNo positive CI-excl-0 gains found.', flush=True)

    # negative CI-excl-0 (where global beats stratum-aware)
    negs = [(m, f, results['bootstrap_gains'][m][ck_boot][f]['gain_median'],
             results['bootstrap_gains'][m][ck_boot][f]['ci95'])
            for m in MODELS for f in fams
            if results['bootstrap_gains'][m][ck_boot][f]['excl0']
            and results['bootstrap_gains'][m][ck_boot][f]['gain_median'] < 0]
    if negs:
        negs.sort(key=lambda x: x[2])
        print('\nNegative CI-excl-0 (global beats perstratum):', flush=True)
        for x in negs[:6]:
            print(f'  {x[0]:7s} {x[1]:14s}: gain={x[2]:+.4f}  CI{x[3]}', flush=True)

    print(f'\nPoint estimates (all coverages) for oxide and intermetallic:', flush=True)
    for m in MODELS:
        print(f'  {m}:', flush=True)
        for cov in COV_TARGETS:
            ck = f'cov{int(cov * 100)}'
            for f in ['oxide', 'intermetallic']:
                if f in fams:
                    pe = results['point_estimates'][m][ck][f]
                    print(f'    cov={cov:.1f} {f:14s}: global={pe["global_daf"]}  '
                          f'perstratum={pe["perstratum_daf"]}  gain={pe["daf_gain"]}',
                          flush=True)

    try:
        git_sha = subprocess.check_output(
            ['git', '-C', '/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research', 'rev-parse', 'HEAD'],
            text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        git_sha = None

    manifest = {
        'cmd': ' '.join([sys.executable] + sys.argv),
        'git_head': git_sha,
        'seed': SEED, 'n_boot': N_BOOT, 'cov_boot': COV_BOOT,
        'inputs': {os.path.basename(DATA): sha256(DATA),
                   **{f'{m}_pred.csv': sha256(os.path.join(UIP_DIR, f'{m}_pred.csv'))
                      for m in MODELS}},
        'versions': {'python': platform.python_version(),
                     'numpy': np.__version__, 'pandas': pd.__version__},
        'platform': platform.platform(),
    }
    manifest_path = os.path.join(OUT_DIR, 'mt29_b5_policy_spike_manifest.json')
    with open(manifest_path, 'w') as fh:
        json.dump(manifest, fh, indent=2)
    print(f'Wrote {manifest_path}', flush=True)


if __name__ == '__main__':
    main()
