import os
import pandas as pd, numpy as np, re, json
rng = np.random.default_rng(20260621)
N_BOOT = 1000

# Data roots overridable via env (see DATA_MANIFEST.md); defaults reproduce originals.
_DATA_ROOT = os.path.expanduser(os.environ.get('MT_DATA_ROOT', '~/mt_stage0/data'))
_UIP_ROOT = os.path.expanduser(os.environ.get('MT_UIP_ROOT', '~/mt_uip'))

wbm = pd.read_csv(os.path.join(_DATA_ROOT, "2023-12-13-wbm-summary.csv.gz"))
keep = ['material_id','formula','e_form_per_atom_mp2020_corrected',
        'e_above_hull_mp2020_corrected_ppd_mp','unique_prototype']
base = wbm[keep].copy()
base['round'] = base['material_id'].astype(str).str.extract(r'wbm-(\d+)-')[0].astype(int)
MODELS=['chgnet','m3gnet','mace','orb']
for m in MODELS:
    p=pd.read_csv(os.path.join(_UIP_ROOT, f"{m}_pred.csv")).rename(columns={'e_form_pred':f'eform_{m}'})
    base=base.merge(p,on='material_id',how='inner')
eform_true=base['e_form_per_atom_mp2020_corrected'].values
hull_true=base['e_above_hull_mp2020_corrected_ppd_mp'].values
true_stable=hull_true<0.0
def nel(f): return len(re.findall(r'[A-Z][a-z]?',str(f)))
fam=base['formula'].apply(nel).values
base['family']=np.where(fam<=1,'unary',np.where(fam==2,'binary',np.where(fam==3,'ternary','quaternary+')))

# predicted hull + |margin| confidence per model
pred_hull={m: hull_true+(base[f'eform_{m}'].values-eform_true) for m in MODELS}
conf={m: np.abs(pred_hull[m]) for m in MODELS}   # |predicted hull margin| -> larger=more confident
pred_stable={m: pred_hull[m]<0.0 for m in MODELS}

COVS=[0.5,0.7,0.9]
def precision_daf_at_cov(idx, m, cov):
    # keep most-confident `cov` fraction within this stratum (abstention)
    c=conf[m][idx]
    k=max(1,int(round(cov*len(idx))))
    thr_order=np.argsort(-c)          # most confident first
    sel=idx[thr_order[:k]]
    ts=true_stable[sel]; ps=pred_stable[m][sel]
    tp=np.sum(ps&ts); fp=np.sum(ps&~ts)
    prec=tp/(tp+fp) if (tp+fp)>0 else 0.0
    br=true_stable[idx].mean()        # stratum base rate
    daf=prec/br if br>0 else 0.0
    return prec, daf, int(tp+fp)

# Interaction: does the precision-GAIN from abstention (cov=0.5 vs cov=0.9) differ by stratum?
# gain_s = metric(cov_low=0.5) - metric(cov_high=0.9) within stratum s.
# interaction = gain_{stratumA} - gain_{stratumB}, bootstrapped within strata.
def stratum_indices(by):
    out={}
    if by=='unique_prototype':
        out['unique=True']=np.where(base['unique_prototype'].values)[0]
        out['unique=False']=np.where(~base['unique_prototype'].values)[0]
    elif by=='family':
        for f in ['binary','ternary','quaternary+']:
            out[f]=np.where(base['family'].values==f)[0]
    elif by=='round':
        for r in sorted(base['round'].unique()):
            out[f'round_{r}']=np.where(base['round'].values==r)[0]
    return out

def boot_gain(idx, m, metric_idx=0):
    # metric_idx: 0=precision,1=daf ; gain = cov0.5 - cov0.9
    n=len(idx); samples=[]
    for _ in range(N_BOOT):
        bs=idx[rng.integers(0,n,n)]
        lo=precision_daf_at_cov(bs,m,0.5)[metric_idx]
        hi=precision_daf_at_cov(bs,m,0.9)[metric_idx]
        samples.append(lo-hi)
    return np.array(samples)

results={'meta':{'seed':20260621,'n_boot':N_BOOT,'confidence_signal':'|predicted hull margin|',
                 'coverages':COVS,'models':MODELS,
                 'interaction_def':'precision_gain(cov0.5 - cov0.9) difference between strata, bootstrapped'}}

# point estimates: precision & DAF vs coverage per stratum per model
strat_curves={}
for by in ['unique_prototype','family','round']:
    strat_curves[by]={}
    for sname,idx in stratum_indices(by).items():
        strat_curves[by][sname]={}
        for m in MODELS:
            strat_curves[by][sname][m]={f'cov_{int(c*100)}':dict(
                precision=round(precision_daf_at_cov(idx,m,c)[0],5),
                daf=round(precision_daf_at_cov(idx,m,c)[1],5),
                n_called=precision_daf_at_cov(idx,m,c)[2]) for c in COVS}
        strat_curves[by][sname]['_base_rate_stable']=round(float(true_stable[idx].mean()),5)
        strat_curves[by][sname]['_n']=len(idx)
results['stratified_curves']=strat_curves

# interaction tests: for each stratification axis & each model, test all stratum pairs
interactions=[]
for by in ['unique_prototype','family','round']:
    si=stratum_indices(by)
    snames=list(si.keys())
    for m in MODELS:
        # precompute per-stratum bootstrap gain samples (precision)
        gains={s: boot_gain(si[s], m, 0) for s in snames}
        for i in range(len(snames)):
            for j in range(i+1,len(snames)):
                a,b=snames[i],snames[j]
                diff=gains[a]-gains[b]
                ci=[float(np.percentile(diff,2.5)),float(np.percentile(diff,97.5))]
                excl0 = (ci[0]>0) or (ci[1]<0)
                interactions.append(dict(axis=by,model=m,stratumA=a,stratumB=b,
                    gainA_median=round(float(np.median(gains[a])),5),
                    gainB_median=round(float(np.median(gains[b])),5),
                    interaction_median=round(float(np.median(diff)),5),
                    interaction_ci95=[round(ci[0],5),round(ci[1],5)],
                    excludes_0=bool(excl0)))
results['interactions']=interactions

n_sig=sum(1 for x in interactions if x['excludes_0'])
results['n_interactions_total']=len(interactions)
results['n_interactions_excl0']=n_sig

print("Total interaction tests:",len(interactions)," CI-excludes-0:",n_sig)
print("\nSample significant interactions (precision gain cov0.5 - cov0.9):")
sigs=[x for x in interactions if x['excludes_0']]
for x in sorted(sigs,key=lambda z:-abs(z['interaction_median']))[:15]:
    print(f"{x['axis']:18s} {x['model']:7s} {x['stratumA']} vs {x['stratumB']}: "
          f"int={x['interaction_median']:+.4f} CI{x['interaction_ci95']}")

# Does the best-coverage policy differ by stratum? Report argmax-coverage per stratum/model for DAF
print("\n=== Best-coverage policy by stratum (DAF-maximizing coverage) ===")
bestcov={}
for by in ['unique_prototype','family','round']:
    bestcov[by]={}
    for sname,idx in stratum_indices(by).items():
        row={}
        for m in MODELS:
            dafs={c:precision_daf_at_cov(idx,m,c)[1] for c in COVS}
            row[m]=max(dafs,key=dafs.get)
        bestcov[by][sname]=row
    print(by, bestcov[by])
results['best_coverage_policy_daf']=bestcov

json.dump(results,open('/tmp/mt29_partB.json','w'),indent=2)
print("\nwrote /tmp/mt29_partB.json")
