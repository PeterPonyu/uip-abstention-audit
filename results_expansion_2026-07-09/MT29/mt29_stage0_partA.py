import os
import pandas as pd, numpy as np, re, json, itertools
from collections import defaultdict
rng = np.random.default_rng(20260621)
N_BOOT = 1000

# Data roots overridable via env (see DATA_MANIFEST.md); defaults reproduce originals.
_DATA_ROOT = os.path.expanduser(os.environ.get('MT_DATA_ROOT', '~/mt_stage0/data'))
_UIP_ROOT = os.path.expanduser(os.environ.get('MT_UIP_ROOT', '~/mt_uip'))

# ---------- load ----------
wbm = pd.read_csv(os.path.join(_DATA_ROOT, "2023-12-13-wbm-summary.csv.gz"))
keep = ['material_id','formula','e_form_per_atom_mp2020_corrected',
        'e_above_hull_mp2020_corrected_ppd_mp','unique_prototype','protostructure_spglib']
base = wbm[keep].copy()
base['round'] = base['material_id'].astype(str).str.extract(r'wbm-(\d+)-')[0].astype(int)

MODELS = ['chgnet','m3gnet','mace','orb']
for m in MODELS:
    p = pd.read_csv(os.path.join(_UIP_ROOT, f"{m}_pred.csv")).rename(columns={'e_form_pred':f'eform_{m}'})
    base = base.merge(p, on='material_id', how='inner')

eform_true = base['e_form_per_atom_mp2020_corrected'].values
hull_true  = base['e_above_hull_mp2020_corrected_ppd_mp'].values
true_stable = hull_true < 0.0
# predicted hull per model (MBD recipe)
pred_hull = {}
pred_stable = {}
for m in MODELS:
    ph = hull_true + (base[f'eform_{m}'].values - eform_true)
    pred_hull[m] = ph
    pred_stable[m] = ph < 0.0

# ---------- chemistry family from formula (number of distinct elements) ----------
def n_elements(formula):
    return len(re.findall(r'[A-Z][a-z]?', str(formula)))
nel = base['formula'].apply(n_elements).values
family = np.where(nel<=1,'unary', np.where(nel==2,'binary', np.where(nel==3,'ternary','quaternary+')))
base['family'] = family

print("Family counts:", pd.Series(family).value_counts().to_dict())
print("unique_prototype True/False:", base['unique_prototype'].value_counts().to_dict())
print("round counts:", base['round'].value_counts().sort_index().to_dict())

# ---------- discovery-decision metrics per model on a row-subset ----------
def metrics_on(idx, m):
    ts = true_stable[idx]; ps = pred_stable[m][idx]
    tp = np.sum(ps & ts); fp = np.sum(ps & ~ts); fn = np.sum(~ps & ts)
    prec = tp/(tp+fp) if (tp+fp)>0 else 0.0
    rec  = tp/(tp+fn) if (tp+fn)>0 else 0.0
    f1 = 2*prec*rec/(prec+rec) if (prec+rec)>0 else 0.0
    base_rate = ts.mean() if len(ts)>0 else 0.0
    daf = prec/base_rate if base_rate>0 else 0.0   # discovery acceleration factor
    return dict(precision=prec, recall=rec, f1=f1, daf=daf, base_rate=base_rate,
                n_called_stable=int(tp+fp), n=len(idx))

# ---------- define splits ----------
all_idx = np.arange(len(base))
splits = {}
splits['FULL'] = all_idx
splits['unique_prototype'] = np.where(base['unique_prototype'].values)[0]
for r in sorted(base['round'].unique()):
    splits[f'round_{r}'] = np.where(base['round'].values==r)[0]
# chemistry-family splits as separate "split universes" too
for fam in ['binary','ternary','quaternary+']:
    splits[f'family_{fam}'] = np.where(base['family'].values==fam)[0]

# ---------- (A) RANK-REORDERING under each split ----------
# Primary discovery-decision metric for ranking: F1 (matches MBD leaderboard headline).
# Also compute DAF ranking as secondary.
def rank_models(idx, metric='f1'):
    vals = {m: metrics_on(idx, m)[metric] for m in MODELS}
    # rank 1 = best (highest)
    order = sorted(MODELS, key=lambda m: -vals[m])
    rank = {m: order.index(m)+1 for m in MODELS}
    return vals, rank

def bootstrap_ranks(idx, metric='f1', n_boot=N_BOOT):
    n = len(idx)
    rank_samples = {m: [] for m in MODELS}
    metric_samples = {m: [] for m in MODELS}
    for _ in range(n_boot):
        bs = idx[rng.integers(0, n, n)]
        vals = {m: metrics_on(bs, m)[metric] for m in MODELS}
        order = sorted(MODELS, key=lambda m: -vals[m])
        for m in MODELS:
            rank_samples[m].append(order.index(m)+1)
            metric_samples[m].append(vals[m])
    out = {}
    for m in MODELS:
        rs = np.array(rank_samples[m]); ms = np.array(metric_samples[m])
        out[m] = dict(
            rank_median=float(np.median(rs)),
            rank_ci95=[float(np.percentile(rs,2.5)), float(np.percentile(rs,97.5))],
            metric_median=float(np.median(ms)),
            metric_ci95=[float(np.percentile(ms,2.5)), float(np.percentile(ms,97.5))],
        )
    return out

def kendall_tau(rank_a, rank_b):
    ms = MODELS
    n=len(ms); conc=disc=0
    for i in range(n):
        for j in range(i+1,n):
            a = np.sign(rank_a[ms[i]]-rank_a[ms[j]])
            b = np.sign(rank_b[ms[i]]-rank_b[ms[j]])
            if a*b>0: conc+=1
            elif a*b<0: disc+=1
    denom = n*(n-1)/2
    return (conc-disc)/denom if denom>0 else 1.0

results = {'meta':{'seed':20260621,'n_boot':N_BOOT,'n_rows':len(base),
                   'stable_definition':'e_above_hull < 0','models':MODELS,
                   'ranking_metric_primary':'f1','ranking_metric_secondary':'daf'}}

rankmap = {}
for metric in ['f1','daf']:
    rankmap[metric] = {}
    full_vals, full_rank = rank_models(splits['FULL'], metric)
    for sname, idx in splits.items():
        vals, rank = rank_models(idx, metric)
        boot = bootstrap_ranks(idx, metric)
        tau_vs_full = kendall_tau(full_rank, rank)
        rankmap[metric][sname] = dict(
            point_values={m: round(vals[m],5) for m in MODELS},
            point_rank=rank,
            bootstrap=boot,
            kendall_tau_vs_full=round(tau_vs_full,4),
            n=len(idx),
        )
results['rank_reordering'] = rankmap

# ---------- detect CI-supported rank changes vs FULL ----------
reorder_findings = []
for metric in ['f1','daf']:
    full_rank = rankmap[metric]['FULL']['point_rank']
    full_boot = rankmap[metric]['FULL']['bootstrap']
    for sname, sd in rankmap[metric].items():
        if sname=='FULL': continue
        for m in MODELS:
            r_full = full_rank[m]
            r_split = sd['point_rank'][m]
            ci_full = full_boot[m]['rank_ci95']
            ci_split = sd['bootstrap'][m]['rank_ci95']
            moved = abs(r_split - r_full) >= 1
            # non-overlapping rank CI between FULL and split for this model
            nonoverlap = (ci_split[0] > ci_full[1]) or (ci_split[1] < ci_full[0])
            if moved and nonoverlap:
                reorder_findings.append(dict(metric=metric, split=sname, model=m,
                    rank_full=r_full, rank_split=r_split,
                    ci_full=ci_full, ci_split=ci_split,
                    metric_full=round(full_boot[m]['metric_median'],4),
                    metric_split=round(sd['bootstrap'][m]['metric_median'],4)))
results['reorder_findings_ci_supported'] = reorder_findings

# kendall tau summary
tau_summary = {}
for metric in ['f1','daf']:
    tau_summary[metric] = {s: rankmap[metric][s]['kendall_tau_vs_full']
                           for s in rankmap[metric] if s!='FULL'}
results['kendall_tau_summary'] = tau_summary

print("\n=== RANK POINT (F1) ===")
for s in splits:
    print(s, rankmap['f1'][s]['point_rank'], "tau", rankmap['f1'][s]['kendall_tau_vs_full'])
print("\n=== RANK POINT (DAF) ===")
for s in splits:
    print(s, rankmap['daf'][s]['point_rank'], "tau", rankmap['daf'][s]['kendall_tau_vs_full'])
print("\nCI-supported reorderings:", len(reorder_findings))
for f in reorder_findings:
    print(f)

with open('/tmp/mt29_partA.json','w') as fh:
    json.dump(results, fh, indent=2)
print("\nwrote /tmp/mt29_partA.json")
