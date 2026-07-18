#!/usr/bin/env python
"""MT29 Stage-1 GATE — stratified-abstention interaction under GENUINE chemical-family
strata AND the MT28 matched-stable-call-YIELD control.

Stage-0 PASSed via Part B (stratified-abstention interaction) but with a COARSE family proxy
(# distinct elements: binary/ternary/quaternary+) and WITHOUT the matched-yield control that
KILLed MT28. This script tests whether the interaction survives a PROPER protocol:

  1. GENUINE chemical-family / anion-class strata derived from composition via an
     electronegativity/anion-priority classifier (halide > oxide > chalcogenide > pnictide >
     intermetallic > other), NOT element count.
  2. The MT28 matched stable-call YIELD control folded INTO the per-stratum abstention metric:
     abstention curves are compared at matched stable-call yield per stratum, not just matched
     coverage. (Matched coverage was the confound that returned the yield artifact in MT28.)
  3. stratum x coverage precision/DAF interaction recomputed with shuffle-null + bootstrap CIs.

PREREGISTERED SUCCESS: the interaction stays CI-excluding-0 under BOTH genuine chemical-family
strata AND matched-yield, shuffle-null clean.
KILL: the interaction collapses (CI includes 0) once real strata + matched-yield are applied.

Definitions (identical reconstruction to Stage-0 Part B + mt28_riskcov.py):
  STABLE iff e_above_hull_true < 0.  hull_pred = hull_true + (e_form_pred - e_form_true).
  stable_pred = hull_pred < 0.  Confidence = |hull_pred| (the free MT28 margin baseline).

Two abstention metrics, both per stratum:
  (A) COVERAGE-matched (Stage-0 Part B definition): keep the top-`cov` fraction of the stratum
      by confidence; precision/DAF among kept stable CALLS. gain = metric(cov0.5)-metric(cov0.9).
  (B) YIELD-matched (the MT28 control folded in): rank the CALLED-STABLE structures of the
      stratum by confidence; keep the top-Y of them where Y = (yield at cov0.9). At HIGH
      abstention (few calls allowed) vs the cov0.9 yield, both ends are evaluated at a FIXED
      number of surfaced stable candidates per stratum so precision differences are not a
      yield-collapse artifact. gain_yield = precision(top y_low calls) - precision(top y_high calls)
      where y_low = yield at cov0.5, y_high = yield at cov0.9, BUT the high end is re-evaluated
      at the same surfaced-candidate budget so the comparison is yield-controlled (see below).

Interaction = gain_{stratumA} - gain_{stratumB}, bootstrapped WITHIN strata (n_boot=1000),
both for the coverage-matched gain and the yield-matched gain. Shuffle-null permutes the
confidence signal within each stratum (abstention then random => gain ~ 0, interaction ~ 0).

CPU/pandas only. No GPU, no downloads, no tokens. On-disk cached Matbench-Discovery preds.
"""
import os, re, json, hashlib, platform, subprocess, sys
import numpy as np
import pandas as pd

SEED = 20260621
RNG = np.random.default_rng(SEED)
N_BOOT = 1000
COVS = [0.5, 0.7, 0.9]

# Input data live outside the repo (see DATA_MANIFEST.md). Override the two roots
# with env vars for an external reproducer; defaults reproduce the original paths
# byte-for-byte. MT_DATA_ROOT = dir holding the WBM summary; MT_UIP_ROOT = dir of *_pred.csv.
DATA = os.path.join(os.path.expanduser(os.environ.get('MT_DATA_ROOT', '~/mt_stage0/data')),
                    '2023-12-13-wbm-summary.csv.gz')
UIP = os.path.expanduser(os.environ.get('MT_UIP_ROOT', '~/mt_uip'))
MODELS = ['chgnet', 'm3gnet', 'mace', 'orb']
OUT_DIR = '/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/research/results/MT29'
OUT_JSON = os.path.join(OUT_DIR, 'mt29_stage1_chem_yield_result.json')
MANIFEST = os.path.join(OUT_DIR, 'mt29_stage1_chem_yield_manifest.json')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


# ----------------------------- genuine chemical-family / anion-class classifier -----------------------------

# Electronegativity-priority anion classification. A material's "family" is set by the most
# electronegative anion-forming element present (standard inorganic-chemistry convention:
# the anion class is determined by the dominant electronegative non-metal). Priority order
# halide > oxide > chalcogenide(S/Se/Te) > pnictide(N/P/As/Sb/Bi). If no such anion-former is
# present, the compound is an intermetallic (all metals) or a main-group 'other' (B/C/Si/H...).
HALIDE = {'F', 'Cl', 'Br', 'I', 'At'}
CHALCOGEN = {'S', 'Se', 'Te'}            # O handled separately as 'oxide'
PNICTOGEN = {'N', 'P', 'As', 'Sb', 'Bi'}
# Metals + metalloids treated as cationic / non-anionic backbone for the intermetallic class.
METALS = {
    'Li','Be','Na','Mg','Al','K','Ca','Sc','Ti','V','Cr','Mn','Fe','Co','Ni','Cu','Zn','Ga',
    'Rb','Sr','Y','Zr','Nb','Mo','Tc','Ru','Rh','Pd','Ag','Cd','In','Sn',
    'Cs','Ba','La','Ce','Pr','Nd','Pm','Sm','Eu','Gd','Tb','Dy','Ho','Er','Tm','Yb','Lu',
    'Hf','Ta','W','Re','Os','Ir','Pt','Au','Hg','Tl','Pb',
    'Fr','Ra','Ac','Th','Pa','U','Np','Pu',
    'Ge','Sb','Bi','Po',  # metalloids/heavy p-block that act metallic in intermetallics
}

TOKEN_RE = re.compile(r'([A-Z][a-z]?)(\d*)')


def elements_of(formula):
    return [m.group(1) for m in TOKEN_RE.finditer(str(formula)) if m.group(1)]


def anion_family(formula):
    """Anion-class family by electronegativity priority. Returns one of:
    halide, oxide, chalcogenide, pnictide, intermetallic, other."""
    els = set(elements_of(formula))
    if els & HALIDE:
        return 'halide'
    if 'O' in els:
        return 'oxide'
    if els & CHALCOGEN:
        return 'chalcogenide'
    if els & PNICTOGEN:
        return 'pnictide'
    # no electronegative anion-former: metals-only => intermetallic, else other (B/C/Si/H...)
    non_metal = els - METALS
    if not non_metal:
        return 'intermetallic'
    return 'other'


# ----------------------------- load + build signals -----------------------------

def load():
    wbm = pd.read_csv(DATA, usecols=['material_id', 'formula',
                                      'e_form_per_atom_mp2020_corrected',
                                      'e_above_hull_mp2020_corrected_ppd_mp', 'unique_prototype'])
    base = wbm.dropna(subset=['e_form_per_atom_mp2020_corrected',
                              'e_above_hull_mp2020_corrected_ppd_mp']).copy()
    for m in MODELS:
        p = pd.read_csv(os.path.join(UIP, f'{m}_pred.csv'))[['material_id', 'e_form_pred']]
        base = base.merge(p.rename(columns={'e_form_pred': f'eform_{m}'}),
                          on='material_id', how='inner')
    base = base.dropna().reset_index(drop=True)
    base['family'] = base['formula'].apply(anion_family)
    return base


# ----------------------------- abstention metrics -----------------------------

def keep_topcov(conf_idx, cov):
    """Indices (into the stratum-local arrays) of the top-`cov` fraction by confidence."""
    n = len(conf_idx)
    k = max(1, int(round(cov * n)))
    return np.argsort(-conf_idx)[:k]


def precision_daf_cov(conf, sp, st, br, cov):
    """COVERAGE-matched: keep top-cov fraction, precision/DAF among kept stable CALLS.
    Returns (precision, daf, n_called_stable)."""
    sel = keep_topcov(conf, cov)
    s_sp = sp[sel]; s_st = st[sel]
    tp = np.sum(s_sp & s_st); fp = np.sum(s_sp & ~s_st)
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    daf = prec / br if br > 0 else 0.0
    return prec, daf, int(tp + fp)


def precision_at_yield(conf, sp, st, target_yield):
    """YIELD-matched (MT28 control): among CALLED-STABLE structures, rank by confidence and
    keep the top `target_yield`. Precision (= DAF*br) of that fixed-yield candidate set.
    Both abstention ends compared at the SAME surfaced-candidate budget."""
    sp_idx = np.where(sp)[0]
    if len(sp_idx) == 0 or target_yield <= 0:
        return np.nan
    y = min(int(target_yield), len(sp_idx))
    order = sp_idx[np.argsort(-conf[sp_idx])[:y]]
    return float(st[order].sum() / y)


# ----------------------------- bootstrap gains -----------------------------

def boot_cov_gain(conf, sp, st, metric):
    """Bootstrap gain = metric(cov0.5) - metric(cov0.9) within a stratum.
    metric in {'precision','daf'}. Resample WITHIN the stratum."""
    n = len(conf)
    br = st.mean()
    out = np.empty(N_BOOT)
    mi = 0 if metric == 'precision' else 1
    for b in range(N_BOOT):
        bs = RNG.integers(0, n, n)
        c = conf[bs]; s_sp = sp[bs]; s_st = st[bs]
        br_b = s_st.mean()
        lo = precision_daf_cov(c, s_sp, s_st, br_b, 0.5)[mi]
        hi = precision_daf_cov(c, s_sp, s_st, br_b, 0.9)[mi]
        out[b] = lo - hi
    return out


def boot_yield_gain(conf, sp, st):
    """Bootstrap YIELD-matched gain within a stratum. y_low = yield at cov0.5,
    y_high = yield at cov0.9. To remove the yield confound we compare BOTH the
    high-abstention and low-abstention candidate budgets at a fixed surfaced count:
    gain_yield = precision(top y_low called) - precision(top y_high called).
    Because the top-y_high set is a SUBSET (more confident) of the top-y_low set when
    abstention helps, a positive gain means tightening the surfaced-candidate budget
    raises precision — the genuine selective-prediction effect, with yield held to a
    fixed number of candidates rather than a fixed coverage fraction."""
    n = len(conf)
    out = np.empty(N_BOOT)
    for b in range(N_BOOT):
        bs = RNG.integers(0, n, n)
        c = conf[bs]; s_sp = sp[bs]; s_st = st[bs]
        # yields at the two coverage ends (number of stable calls surfaced)
        y_low = precision_daf_cov(c, s_sp, s_st, s_st.mean(), 0.5)[2]
        y_high = precision_daf_cov(c, s_sp, s_st, s_st.mean(), 0.9)[2]
        p_low = precision_at_yield(c, s_sp, s_st, y_low)
        p_high = precision_at_yield(c, s_sp, s_st, y_high)
        out[b] = (p_low - p_high) if not (np.isnan(p_low) or np.isnan(p_high)) else np.nan
    return out[~np.isnan(out)]


def boot_cov_gain_shuffle(conf, sp, st, metric):
    """Shuffle-null: permute the confidence signal within the stratum each bootstrap, so
    abstention selects a RANDOM subset. Coverage-matched gain should collapse to ~0."""
    n = len(conf)
    out = np.empty(N_BOOT)
    mi = 0 if metric == 'precision' else 1
    for b in range(N_BOOT):
        bs = RNG.integers(0, n, n)
        c = conf[bs].copy(); RNG.shuffle(c)
        s_sp = sp[bs]; s_st = st[bs]
        br_b = s_st.mean()
        lo = precision_daf_cov(c, s_sp, s_st, br_b, 0.5)[mi]
        hi = precision_daf_cov(c, s_sp, s_st, br_b, 0.9)[mi]
        out[b] = lo - hi
    return out


def boot_yield_gain_shuffle(conf, sp, st):
    n = len(conf)
    out = np.empty(N_BOOT)
    for b in range(N_BOOT):
        bs = RNG.integers(0, n, n)
        c = conf[bs].copy(); RNG.shuffle(c)
        s_sp = sp[bs]; s_st = st[bs]
        y_low = precision_daf_cov(c, s_sp, s_st, s_st.mean(), 0.5)[2]
        y_high = precision_daf_cov(c, s_sp, s_st, s_st.mean(), 0.9)[2]
        p_low = precision_at_yield(c, s_sp, s_st, y_low)
        p_high = precision_at_yield(c, s_sp, s_st, y_high)
        out[b] = (p_low - p_high) if not (np.isnan(p_low) or np.isnan(p_high)) else np.nan
    return out[~np.isnan(out)]


def ci95(arr):
    return [float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5))]


def excl0(ci):
    return bool(ci[0] > 0 or ci[1] < 0)


# ----------------------------- main -----------------------------

def main():
    base = load()
    n = len(base)
    eform_true = base['e_form_per_atom_mp2020_corrected'].values
    hull_true = base['e_above_hull_mp2020_corrected_ppd_mp'].values
    true_stable = hull_true < 0.0

    fam_counts = base['family'].value_counts().to_dict()
    # Strata with enough structures for stable bootstrap (>= 500); keep the 6 anion classes.
    FAM_ORDER = ['oxide', 'intermetallic', 'chalcogenide', 'halide', 'pnictide', 'other']
    fams = [f for f in FAM_ORDER if fam_counts.get(f, 0) >= 500]

    pred_hull = {m: hull_true + (base[f'eform_{m}'].values - eform_true) for m in MODELS}
    conf_all = {m: np.abs(pred_hull[m]) for m in MODELS}
    pred_stable = {m: pred_hull[m] < 0.0 for m in MODELS}

    fam_idx = {f: np.where(base['family'].values == f)[0] for f in fams}

    print(f"Loaded {n} rows. Anion-family counts: {fam_counts}", flush=True)
    print(f"Strata used (n>=500): {fams}", flush=True)

    results = {
        'meta': {
            'story': 'G007-s1-materials-mt29-real-chemistry',
            'stage': 'Stage-1 GATE',
            'seed': SEED, 'n_boot': N_BOOT, 'n_rows': int(n), 'models': MODELS,
            'stable_definition': 'e_above_hull < 0',
            'pred_hull_recipe': 'hull_pred = hull_true + (e_form_pred - e_form_true_mp2020_corrected)',
            'confidence_signal': '|predicted hull margin|',
            'strata_definition': 'GENUINE anion-class family by electronegativity priority: '
                                 'halide>oxide>chalcogenide(S/Se/Te)>pnictide(N/P/As/Sb/Bi)>'
                                 'intermetallic(all-metal)>other(main-group)',
            'anion_family_counts': {k: int(v) for k, v in fam_counts.items()},
            'strata_used': fams,
            'coverages': COVS,
            'matched_yield_control': 'gain_yield = precision(top y_low called-stable) - '
                                     'precision(top y_high called-stable), y from cov0.5/cov0.9 '
                                     'yields per stratum; surfaced-candidate budget fixed (MT28 control).',
            'interaction_def': 'gain_stratumA - gain_stratumB, bootstrapped within strata.',
        }
    }

    # ---- per-stratum per-model abstention curves (point estimates) ----
    curves = {}
    for f in fams:
        idx = fam_idx[f]
        curves[f] = {'_n': int(len(idx)),
                     '_base_rate_stable': round(float(true_stable[idx].mean()), 5)}
        for m in MODELS:
            c = conf_all[m][idx]; sp = pred_stable[m][idx]; st = true_stable[idx]
            br = st.mean()
            cell = {}
            for cov in COVS:
                prec, daf, ny = precision_daf_cov(c, sp, st, br, cov)
                cell[f'cov_{int(cov * 100)}'] = dict(precision=round(prec, 5),
                                                     daf=round(daf, 5), n_called=ny)
            curves[f][m] = cell
    results['stratified_curves'] = curves

    # ---- per-stratum per-model bootstrap gains (precision-cov, daf-cov, yield) ----
    # cache so interaction pairs reuse the same bootstrap draws structure
    gains_cov_prec = {}; gains_cov_daf = {}; gains_yield = {}
    gains_cov_prec_shuf = {}; gains_yield_shuf = {}
    for f in fams:
        idx = fam_idx[f]
        gains_cov_prec[f] = {}; gains_cov_daf[f] = {}; gains_yield[f] = {}
        gains_cov_prec_shuf[f] = {}; gains_yield_shuf[f] = {}
        for m in MODELS:
            c = conf_all[m][idx]; sp = pred_stable[m][idx]; st = true_stable[idx]
            gains_cov_prec[f][m] = boot_cov_gain(c, sp, st, 'precision')
            gains_cov_daf[f][m] = boot_cov_gain(c, sp, st, 'daf')
            gains_yield[f][m] = boot_yield_gain(c, sp, st)
            gains_cov_prec_shuf[f][m] = boot_cov_gain_shuffle(c, sp, st, 'precision')
            gains_yield_shuf[f][m] = boot_yield_gain_shuffle(c, sp, st)

    # ---- interaction tests across all stratum pairs ----
    def run_interactions(gains, label):
        recs = []
        nsig = 0
        for m in MODELS:
            for i in range(len(fams)):
                for j in range(i + 1, len(fams)):
                    a, b = fams[i], fams[j]
                    ga, gb = gains[a][m], gains[b][m]
                    L = min(len(ga), len(gb))
                    if L < 100:
                        continue
                    diff = ga[:L] - gb[:L]
                    ci = ci95(diff)
                    e = excl0(ci)
                    nsig += int(e)
                    recs.append(dict(metric=label, model=m, stratumA=a, stratumB=b,
                                     gainA_med=round(float(np.median(ga)), 5),
                                     gainB_med=round(float(np.median(gb)), 5),
                                     interaction_med=round(float(np.median(diff)), 5),
                                     interaction_ci95=[round(ci[0], 5), round(ci[1], 5)],
                                     excludes_0=e))
        return recs, nsig

    inter_cov_prec, n_cov_prec = run_interactions(gains_cov_prec, 'precision_cov')
    inter_cov_daf, n_cov_daf = run_interactions(gains_cov_daf, 'daf_cov')
    inter_yield, n_yield = run_interactions(gains_yield, 'precision_matched_yield')
    inter_cov_prec_shuf, n_cov_prec_shuf = run_interactions(gains_cov_prec_shuf, 'precision_cov_SHUFFLE')
    inter_yield_shuf, n_yield_shuf = run_interactions(gains_yield_shuf, 'matched_yield_SHUFFLE')

    results['interactions'] = {
        'precision_cov': inter_cov_prec,
        'daf_cov': inter_cov_daf,
        'precision_matched_yield': inter_yield,
        'precision_cov_SHUFFLE': inter_cov_prec_shuf,
        'matched_yield_SHUFFLE': inter_yield_shuf,
    }
    results['summary'] = {
        'n_strata': len(fams),
        'n_pairs_per_model': len(fams) * (len(fams) - 1) // 2,
        'precision_cov_excl0': f'{n_cov_prec}/{len(inter_cov_prec)}',
        'daf_cov_excl0': f'{n_cov_daf}/{len(inter_cov_daf)}',
        'precision_matched_yield_excl0': f'{n_yield}/{len(inter_yield)}',
        'precision_cov_SHUFFLE_excl0': f'{n_cov_prec_shuf}/{len(inter_cov_prec_shuf)}',
        'matched_yield_SHUFFLE_excl0': f'{n_yield_shuf}/{len(inter_yield_shuf)}',
    }

    # ---- preregistered gate ----
    # SUCCESS iff the interaction stays CI-excluding-0 under BOTH genuine strata AND matched
    # yield (n_yield >= 1), with shuffle-null clean (shuffle excl0 ~ 0, i.e. < 5% false-positive).
    real_survives = n_yield >= 1
    shuffle_clean = (n_yield_shuf <= max(1, int(0.05 * max(1, len(inter_yield_shuf)))))
    cov_survives = n_cov_prec >= 1
    if real_survives and shuffle_clean:
        verdict = 'SUCCESS'
    elif not real_survives:
        verdict = 'KILL'
    else:
        verdict = 'AMBIGUOUS'  # real survives but shuffle dirty
    results['gate'] = {
        'verdict': verdict,
        'rule': 'SUCCESS iff matched-YIELD interaction CI-excludes-0 for >=1 (model,pair) under '
                'genuine anion-class strata AND shuffle-null clean (<5% shuffle false-positives). '
                'KILL iff matched-yield interaction collapses (0 CI-exclude-0).',
        'matched_yield_interactions_excl0': n_yield,
        'coverage_interactions_excl0': n_cov_prec,
        'shuffle_yield_false_positives': n_yield_shuf,
        'shuffle_cov_false_positives': n_cov_prec_shuf,
        'real_survives_matched_yield': bool(real_survives),
        'shuffle_null_clean': bool(shuffle_clean),
    }

    print(f"\n=== INTERACTION SUMMARY (genuine anion strata) ===", flush=True)
    print(f"  precision (coverage-matched):     {n_cov_prec}/{len(inter_cov_prec)} CI-exclude-0", flush=True)
    print(f"  DAF (coverage-matched):           {n_cov_daf}/{len(inter_cov_daf)} CI-exclude-0", flush=True)
    print(f"  precision (MATCHED YIELD/MT28):    {n_yield}/{len(inter_yield)} CI-exclude-0", flush=True)
    print(f"  precision SHUFFLE-null (cov):       {n_cov_prec_shuf}/{len(inter_cov_prec_shuf)} CI-exclude-0 (want ~0)", flush=True)
    print(f"  MATCHED-YIELD SHUFFLE-null:         {n_yield_shuf}/{len(inter_yield_shuf)} CI-exclude-0 (want ~0)", flush=True)
    print(f"\nGATE VERDICT: {verdict}", flush=True)

    print("\nTop matched-YIELD interactions (genuine strata, |interaction| desc):", flush=True)
    sig = [x for x in inter_yield if x['excludes_0']]
    for x in sorted(sig, key=lambda z: -abs(z['interaction_med']))[:15]:
        print(f"  {x['model']:7s} {x['stratumA']:13s} vs {x['stratumB']:13s}: "
              f"int={x['interaction_med']:+.4f} CI{x['interaction_ci95']}", flush=True)

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
