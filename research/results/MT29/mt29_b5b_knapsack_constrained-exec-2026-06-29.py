#!/usr/bin/env python
"""B5b EXEC (2026-06-29) — CONSTRAINED KNAPSACK abstention allocator vs global threshold.

Context: B5 spike (mt29_b5_policy_spike.py) tested a NAIVE per-stratum equalizer
(each stratum keeps top-(cov*n_s) -> uniform per-stratum coverage). Result: only
8/24 cells positive CI-excl-0, intermetallic/chalcogenide NEGATIVE. The "unified
optimal allocation" seam was FALSIFIED in that naive form.

This script tests whether a PROPERLY CONSTRAINED optimizer rescues per-stratum
dominance over the global threshold at MATCHED total coverage (0.7).

ALLOCATOR (greedy marginal knapsack):
  Total keep-budget B = round(cov*N) (matched to global EXACTLY). Start keeping
  ALL N structures; greedily DROP (N-B) structures, each step removing the
  lowest-confidence kept structure from the stratum whose drop yields the largest
  marginal increase in the objective = sum_s DAF_s(k_s) (equal-stratum-weight mean
  DAF). i.e. abstention budget flows ONLY to strata with the largest positive
  marginal DAF-gain. Per-stratum kept set is always a confidence-prefix (top-k_s).

  DAF_s(k) = precision/base_rate among the top-k (by |hull-margin|) kept &
  predicted-stable structures in stratum s. (verbatim DAF def from B5.)

CONSERVATION NOTE (pre-registered expectation): For BOTH the global threshold and
ANY reallocation at matched total coverage, the within-stratum kept set is the
top-k_s confidence prefix, so DAF_s is a function of k_s ALONE and identical
across policies. Global already spends exactly B; any reallocation that lowers
k_s in one stratum (raising its DAF) must raise k_t in another (lowering its DAF).
Hence per-stratum Pareto dominance over global is mathematically impossible unless
the knapsack reproduces the global allocation. We MEASURE the +/- cell counts and
the aggregate (mean) DAF to quantify this.

Bootstrap: stratified resample within each stratum (paired), N_BOOT=1000 at cov=0.7.
Shuffle null: permute confidence globally before both policies.
Dominance test: count (model,stratum) cells with knapsack-minus-global DAF gain
CI-excl-0 positive vs negative. CLEAN dominance = >=1 positive AND 0 negative.
"""
import os, re, json, hashlib, platform, subprocess, sys, heapq
import numpy as np
import pandas as pd

SEED = 20260629
RNG = np.random.default_rng(SEED)
N_BOOT = 1000
COV = 0.7
FAM_ORDER = ['oxide', 'intermetallic', 'chalcogenide', 'halide', 'pnictide', 'other']
MIN_STRATUM_N = 500

DATA = os.path.join(os.path.expanduser(os.environ.get('MT_DATA_ROOT', '~/mt_stage0/data')),
                    '2023-12-13-wbm-summary.csv.gz')
UIP_DIR = os.path.expanduser(os.environ.get('MT_UIP_ROOT', '~/mt_uip'))
MODELS = ['chgnet', 'm3gnet', 'mace', 'orb']
OUT_DIR = '/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/research/results/MT29'
OUT_JSON = os.path.join(OUT_DIR, 'mt29_b5b_knapsack_constrained-exec-2026-06-29.json')

HALIDE = {'F', 'Cl', 'Br', 'I', 'At'}
CHALCOGEN = {'S', 'Se', 'Te'}
PNICTOGEN = {'N', 'P', 'As', 'Sb', 'Bi'}
METALS = {
    'Li','Be','Na','Mg','Al','K','Ca','Sc','Ti','V','Cr','Mn','Fe','Co','Ni','Cu','Zn',
    'Ga','Rb','Sr','Y','Zr','Nb','Mo','Tc','Ru','Rh','Pd','Ag','Cd','In','Sn','Cs','Ba',
    'La','Ce','Pr','Nd','Pm','Sm','Eu','Gd','Tb','Dy','Ho','Er','Tm','Yb','Lu','Hf','Ta',
    'W','Re','Os','Ir','Pt','Au','Hg','Tl','Pb','Fr','Ra','Ac','Th','Pa','U','Np','Pu',
    'Ge','Sb','Bi','Po',
}
TOKEN_RE = re.compile(r'([A-Z][a-z]?)(\d*)')


def elements_of(formula):
    return [m.group(1) for m in TOKEN_RE.finditer(str(formula)) if m.group(1)]


def anion_family(formula):
    els = set(elements_of(formula))
    if els & HALIDE: return 'halide'
    if 'O' in els: return 'oxide'
    if els & CHALCOGEN: return 'chalcogenide'
    if els & PNICTOGEN: return 'pnictide'
    non_metal = els - METALS
    if not non_metal: return 'intermetallic'
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


def daf_curve(conf_s, ps_s, ts_s, br):
    """Return DAF_s(k) array for k=0..n_s (kept top-k by confidence desc).
    DAF_s(k) = (TP/predicted-positive among top-k)/br ; 0 if no predicted-pos kept."""
    order = np.argsort(-conf_s, kind='stable')
    ps = ps_s[order].astype(np.int64)
    ts = ts_s[order].astype(np.int64)
    cum_pp = np.concatenate(([0], np.cumsum(ps)))          # predicted-positive among top-k
    cum_tp = np.concatenate(([0], np.cumsum(ps & ts)))     # true-pos among predicted-pos top-k
    daf = np.zeros(len(cum_pp))
    nz = cum_pp > 0
    daf[nz] = (cum_tp[nz] / cum_pp[nz]) / br if br > 0 else 0.0
    return daf  # length n_s+1, index = k


def global_k(conf, fam_arr, fams, B):
    """k_s for the global threshold = #stratum-s structures in global top-B by conf."""
    N = len(conf)
    kept = np.zeros(N, dtype=bool)
    kept[np.argpartition(-conf, B - 1)[:B]] = True
    return {f: int(np.sum(kept[fam_arr == f])) for f in fams}


def knapsack_k(daf_curves, ns_dict, fams, B):
    """Greedy marginal allocator: start k_s=n_s, drop (N-B) structures, each from the
    stratum with the largest marginal objective gain = DAF_s(k-1)-DAF_s(k)."""
    N = sum(ns_dict.values())
    D = N - B
    k = {f: ns_dict[f] for f in fams}
    # max-heap on marginal gain of dropping from current k to k-1
    heap = []
    for f in fams:
        kk = k[f]
        g = daf_curves[f][kk - 1] - daf_curves[f][kk]
        heapq.heappush(heap, (-g, f))
    for _ in range(D):
        negg, f = heapq.heappop(heap)
        k[f] -= 1
        if k[f] >= 1:
            kk = k[f]
            g = daf_curves[f][kk - 1] - daf_curves[f][kk]
            heapq.heappush(heap, (-g, f))
        # if k[f]==0 we no longer offer drops for f (cannot keep <0)
    return k


def policies_for_draw(conf, ps, ts, fam_arr, fams, br_dict, ns_dict, B):
    """Return per-stratum (global_daf, knap_daf) for one (resampled) dataset."""
    curves = {}
    for f in fams:
        idx = np.where(fam_arr == f)[0]
        curves[f] = daf_curve(conf[idx], ps[idx], ts[idx], br_dict[f])
    gk = global_k(conf, fam_arr, fams, B)
    kk = knapsack_k(curves, ns_dict, fams, B)
    gd = {f: float(curves[f][gk[f]]) for f in fams}
    kd = {f: float(curves[f][kk[f]]) for f in fams}
    return gd, kd, gk, kk


def ci95(arr):
    clean = arr[~np.isnan(arr)]
    if len(clean) < 10:
        return [np.nan, np.nan]
    return [float(np.percentile(clean, 2.5)), float(np.percentile(clean, 97.5))]


def excl0(ci):
    if ci[0] is None or ci[1] is None or np.isnan(ci[0]) or np.isnan(ci[1]):
        return False
    return bool(ci[0] > 0 or ci[1] < 0)


def main():
    base = load()
    n = len(base)
    eform_true = base['e_form_per_atom_mp2020_corrected'].values
    hull_true = base['e_above_hull_mp2020_corrected_ppd_mp'].values
    true_stable = hull_true < 0.0
    fam_arr = base['family'].values

    fam_counts = base['family'].value_counts().to_dict()
    fams = [f for f in FAM_ORDER if fam_counts.get(f, 0) >= MIN_STRATUM_N]
    ns_dict = {f: int(np.sum(fam_arr == f)) for f in fams}
    br_dict = {f: float(true_stable[fam_arr == f].mean()) for f in fams}
    N = n
    B = int(round(COV * N))

    pred_hull = {m: hull_true + (base[f'eform_{m}'].values - eform_true) for m in MODELS}
    conf_all = {m: np.abs(pred_hull[m]) for m in MODELS}
    pred_stable = {m: pred_hull[m] < 0.0 for m in MODELS}

    print(f"Loaded {n} rows. Strata ({len(fams)}): {fams}", flush=True)
    print(f"Sizes: {ns_dict}", flush=True)
    print(f"B (keep-budget at cov={COV}) = {B}  ({B/N:.4f})", flush=True)

    results = {
        'meta': {
            'story': 'B5b-constrained-knapsack-allocator-exec-2026-06-29',
            'claim': 'A constrained (greedy marginal-DAF) knapsack allocator at matched total '
                     'coverage CI-dominates the global threshold on per-stratum DAF.',
            'allocator': 'Greedy drop maximizing sum_s DAF_s(k_s); abstention budget -> largest '
                         'positive marginal-DAF strata; within-stratum kept = top-k confidence prefix.',
            'objective': 'equal-stratum-weight mean DAF',
            'seed': SEED, 'n_boot': N_BOOT, 'n_rows': int(n), 'cov': COV, 'keep_budget_B': B,
            'models': MODELS, 'strata': fams,
            'conservation_note': ('At matched total coverage, DAF_s depends only on k_s and is '
                                  'identical for global & knapsack; reallocation is zero-sum, so '
                                  'per-stratum Pareto dominance over global is impossible unless '
                                  'knapsack == global.'),
            'dominance_test': 'CLEAN dominance = >=1 cell knapsack-minus-global gain CI-excl-0 positive AND 0 negative.',
        },
        'base_rates': {f: round(br_dict[f], 6) for f in fams},
        'stratum_n': ns_dict,
        'point_estimates': {},
        'bootstrap_gains': {},
        'shuffle_null': {},
        'aggregate': {},
    }

    # ---- point estimates ----
    print("\nPoint estimates (real data, cov=0.7)...", flush=True)
    for m in MODELS:
        gd, kd, gk, kk = policies_for_draw(conf_all[m], pred_stable[m], true_stable,
                                           fam_arr, fams, br_dict, ns_dict, B)
        results['point_estimates'][m] = {}
        for f in fams:
            results['point_estimates'][m][f] = {
                'global_daf': round(gd[f], 5), 'knap_daf': round(kd[f], 5),
                'daf_gain': round(kd[f] - gd[f], 5),
                'global_k': gk[f], 'knap_k': kk[f],
                'global_cov_s': round(gk[f] / ns_dict[f], 4),
                'knap_cov_s': round(kk[f] / ns_dict[f], 4),
            }
        # aggregate (equal-weight mean DAF + population-weighted mean DAF)
        mean_g = float(np.mean([gd[f] for f in fams]))
        mean_k = float(np.mean([kd[f] for f in fams]))
        wsum = sum(ns_dict[f] for f in fams)
        wmean_g = float(np.sum([gd[f] * ns_dict[f] for f in fams]) / wsum)
        wmean_k = float(np.sum([kd[f] * ns_dict[f] for f in fams]) / wsum)
        results['aggregate'][m] = {
            'mean_daf_global': round(mean_g, 5), 'mean_daf_knap': round(mean_k, 5),
            'mean_daf_gain': round(mean_k - mean_g, 5),
            'wmean_daf_global': round(wmean_g, 5), 'wmean_daf_knap': round(wmean_k, 5),
            'wmean_daf_gain': round(wmean_k - wmean_g, 5),
        }
        print(f"  {m}: mean DAF global={mean_g:.4f} knap={mean_k:.4f} gain={mean_k-mean_g:+.4f} | "
              f"wmean gain={wmean_k-wmean_g:+.4f}", flush=True)

    # ---- bootstrap (stratified within stratum, paired) ----
    fam_idx = {f: np.where(fam_arr == f)[0] for f in fams}
    for m in MODELS:
        conf = conf_all[m]; ps = pred_stable[m]; ts = true_stable
        for tag, shuffle in [('bootstrap_gains', False), ('shuffle_null', True)]:
            print(f"  {tag} {m} ({N_BOOT} draws)...", flush=True)
            gains = {f: np.empty(N_BOOT) for f in fams}
            mean_gain = np.empty(N_BOOT)
            wmean_gain = np.empty(N_BOOT)
            wsum = sum(ns_dict[f] for f in fams)
            bconf = np.empty(N); bps = np.empty(N, dtype=bool); bts = np.empty(N, dtype=bool)
            bfam = np.empty(N, dtype='U15')
            off = {}; ptr = 0
            for f in fams:
                off[f] = ptr; ptr += ns_dict[f]
            for b in range(N_BOOT):
                for f in fams:
                    idx = fam_idx[f]; ns = ns_dict[f]
                    draw = RNG.integers(0, ns, ns)
                    g = idx[draw]
                    o = off[f]
                    bconf[o:o+ns] = conf[g]; bps[o:o+ns] = ps[g]
                    bts[o:o+ns] = ts[g]; bfam[o:o+ns] = f
                if shuffle:
                    RNG.shuffle(bconf)
                gd, kd, _, _ = policies_for_draw(bconf, bps, bts, bfam, fams, br_dict, ns_dict, B)
                for f in fams:
                    gains[f][b] = kd[f] - gd[f]
                mg = [kd[f] - gd[f] for f in fams]
                mean_gain[b] = float(np.mean(mg))
                wmean_gain[b] = float(np.sum([(kd[f]-gd[f]) * ns_dict[f] for f in fams]) / wsum)
            results[tag][m] = {}
            for f in fams:
                c = ci95(gains[f])
                results[tag][m][f] = {
                    'gain_median': round(float(np.nanmedian(gains[f])), 5),
                    'ci95': [round(v, 5) if not np.isnan(v) else None for v in c],
                    'excl0': excl0(c),
                }
            mc = ci95(mean_gain); wc = ci95(wmean_gain)
            results[tag][m]['_mean_daf_gain'] = {
                'gain_median': round(float(np.nanmedian(mean_gain)), 5),
                'ci95': [round(v, 5) for v in mc], 'excl0': excl0(mc)}
            results[tag][m]['_wmean_daf_gain'] = {
                'gain_median': round(float(np.nanmedian(wmean_gain)), 5),
                'ci95': [round(v, 5) for v in wc], 'excl0': excl0(wc)}

    # ---- summary ----
    total = 0; pos = 0; neg = 0; shuf_excl = 0
    for m in MODELS:
        for f in fams:
            r = results['bootstrap_gains'][m][f]
            s = results['shuffle_null'][m][f]
            total += 1
            if r['excl0']:
                if r['gain_median'] > 0: pos += 1
                else: neg += 1
            if s['excl0']: shuf_excl += 1
    # mean-DAF aggregate dominance count
    mean_pos = sum(1 for m in MODELS
                   if results['bootstrap_gains'][m]['_mean_daf_gain']['excl0']
                   and results['bootstrap_gains'][m]['_mean_daf_gain']['gain_median'] > 0)
    clean_dominance = (pos >= 1 and neg == 0)
    verdict = 'GO-DOMINANCE' if clean_dominance else 'FALSIFIED-NO-DOMINANCE'
    results['summary'] = {
        'cov': COV, 'total_cells': total,
        'positive_excl0': pos, 'negative_excl0': neg, 'shuffle_excl0': shuf_excl,
        'mean_daf_aggregate_positive_excl0_models': mean_pos,
        'clean_per_stratum_dominance': clean_dominance,
        'verdict': verdict,
        'rationale': (
            f'Per-stratum dominance test: {pos} cells CI-excl-0 POSITIVE, {neg} cells CI-excl-0 '
            f'NEGATIVE (of {total}). CLEAN dominance requires >=1 positive AND 0 negative -> '
            f'{clean_dominance}. Aggregate mean-DAF improved with CI-excl-0 in {mean_pos}/{len(MODELS)} '
            f'models (knapsack optimizes the equal-weight mean objective), but at matched total '
            f'coverage the reallocation is zero-sum across strata, so per-stratum Pareto dominance '
            f'over the global threshold is not achieved.'
        ),
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_JSON, 'w') as fh:
        json.dump(results, fh, indent=2, default=str)
    print(f"\nWrote {OUT_JSON}", flush=True)
    print(f"\n=== B5b VERDICT: {verdict} ===", flush=True)
    print(f"  cells: total={total} positive_excl0={pos} negative_excl0={neg} shuffle_excl0={shuf_excl}", flush=True)
    print(f"  mean-DAF aggregate positive_excl0 in {mean_pos}/{len(MODELS)} models", flush=True)

    try:
        git_sha = subprocess.check_output(
            ['git', '-C', '/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research', 'rev-parse', 'HEAD'],
            text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        git_sha = None
    manifest = {
        'cmd': ' '.join([sys.executable] + sys.argv), 'git_head': git_sha,
        'seed': SEED, 'n_boot': N_BOOT, 'cov': COV, 'keep_budget_B': B,
        'inputs': {os.path.basename(DATA): sha256(DATA),
                   **{f'{m}_pred.csv': sha256(os.path.join(UIP_DIR, f'{m}_pred.csv')) for m in MODELS}},
        'versions': {'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__},
        'platform': platform.platform(),
    }
    with open(os.path.join(OUT_DIR, 'mt29_b5b_knapsack_constrained-exec-2026-06-29_manifest.json'), 'w') as fh:
        json.dump(manifest, fh, indent=2)


if __name__ == '__main__':
    main()
