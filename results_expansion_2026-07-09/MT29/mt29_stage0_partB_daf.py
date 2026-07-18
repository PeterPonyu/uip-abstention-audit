import os
import pandas as pd, numpy as np, re, json
rng = np.random.default_rng(20260621)
N_BOOT = 1000
# Data roots overridable via env (see DATA_MANIFEST.md); defaults reproduce originals.
_DATA_ROOT = os.path.expanduser(os.environ.get('MT_DATA_ROOT', '~/mt_stage0/data'))
_UIP_ROOT = os.path.expanduser(os.environ.get('MT_UIP_ROOT', '~/mt_uip'))
wbm = pd.read_csv(os.path.join(_DATA_ROOT, "2023-12-13-wbm-summary.csv.gz"))
keep=['material_id','formula','e_form_per_atom_mp2020_corrected','e_above_hull_mp2020_corrected_ppd_mp','unique_prototype']
base=wbm[keep].copy(); base['round']=base['material_id'].astype(str).str.extract(r'wbm-(\d+)-')[0].astype(int)
MODELS=['chgnet','m3gnet','mace','orb']
for m in MODELS:
    p=pd.read_csv(os.path.join(_UIP_ROOT, f"{m}_pred.csv")).rename(columns={'e_form_pred':f'eform_{m}'}); base=base.merge(p,on='material_id',how='inner')
eform_true=base['e_form_per_atom_mp2020_corrected'].values; hull_true=base['e_above_hull_mp2020_corrected_ppd_mp'].values
true_stable=hull_true<0.0
def nel(f): return len(re.findall(r'[A-Z][a-z]?',str(f)))
fam=base['formula'].apply(nel).values
base['family']=np.where(fam<=1,'unary',np.where(fam==2,'binary',np.where(fam==3,'ternary','quaternary+')))
pred_hull={m: hull_true+(base[f'eform_{m}'].values-eform_true) for m in MODELS}
conf={m: np.abs(pred_hull[m]) for m in MODELS}; pred_stable={m: pred_hull[m]<0.0 for m in MODELS}

def daf_at_cov(idx,m,cov,shuffle=False):
    c=conf[m][idx]
    if shuffle: c=c[rng.permutation(len(c))]
    k=max(1,int(round(cov*len(idx)))); sel=idx[np.argsort(-c)[:k]]
    ts=true_stable[sel]; ps=pred_stable[m][sel]
    tp=np.sum(ps&ts); fp=np.sum(ps&~ts)
    prec=tp/(tp+fp) if (tp+fp)>0 else 0.0
    br=true_stable[idx].mean(); return prec/br if br>0 else 0.0

def strat(by):
    out={}
    if by=='family':
        for f in ['binary','ternary','quaternary+']: out[f]=np.where(base['family'].values==f)[0]
    elif by=='unique_prototype':
        out['unique=True']=np.where(base['unique_prototype'].values)[0]; out['unique=False']=np.where(~base['unique_prototype'].values)[0]
    return out

# DAF-based interaction (cov0.5 - cov0.9), real vs shuffle null
def boot_daf_gain(idx,m,shuffle=False):
    n=len(idx); s=[]
    for _ in range(N_BOOT):
        bs=idx[rng.integers(0,n,n)]
        s.append(daf_at_cov(bs,m,0.5,shuffle)-daf_at_cov(bs,m,0.9,shuffle))
    return np.array(s)

print("=== DAF interaction (cov0.5-cov0.9), real signal ===")
sig=0; tot=0; out={}
for by in ['family','unique_prototype']:
    si=strat(by); names=list(si.keys()); out[by]=[]
    for m in MODELS:
        g={s:boot_daf_gain(si[s],m) for s in names}
        for i in range(len(names)):
            for j in range(i+1,len(names)):
                a,b=names[i],names[j]; d=g[a]-g[b]
                ci=[float(np.percentile(d,2.5)),float(np.percentile(d,97.5))]; e=(ci[0]>0)or(ci[1]<0)
                tot+=1; sig+= 1 if e else 0
                rec=dict(model=m,A=a,B=b,med=round(float(np.median(d)),4),ci=[round(ci[0],4),round(ci[1],4)],excl0=bool(e))
                out[by].append(rec)
                if e and by=='family': print(f"  family {m:7s} {a} vs {b}: {rec['med']:+.4f} CI{rec['ci']}")
print(f"DAF interaction: {sig}/{tot} exclude 0")

# Shuffle null: under permuted confidence, abstention should give DAF~base => gain~0, interaction~0
print("\n=== Shuffle-null check (family, precision-gain interaction should collapse) ===")
import itertools
def boot_prec_gain(idx,m,shuffle):
    n=len(idx); s=[]
    for _ in range(N_BOOT):
        bs=idx[rng.integers(0,n,n)]
        def pr(cov):
            c=conf[m][bs].copy()
            if shuffle: c=c[rng.permutation(len(c))]
            k=max(1,int(round(cov*len(bs)))); sel=bs[np.argsort(-c)[:k]]
            ts=true_stable[sel]; ps=pred_stable[m][sel]; tp=np.sum(ps&ts); fp=np.sum(ps&~ts)
            return tp/(tp+fp) if (tp+fp)>0 else 0.0
        s.append(pr(0.5)-pr(0.9))
    return np.array(s)
si=strat('family'); 
for m in ['chgnet','m3gnet']:
    greal={s:boot_prec_gain(si[s],m,False) for s in si}
    gshuf={s:boot_prec_gain(si[s],m,True) for s in si}
    a,b='ternary','quaternary+'
    dr=greal[a]-greal[b]; ds=gshuf[a]-gshuf[b]
    print(f"  {m} {a}vs{b}: REAL int={np.median(dr):+.4f} CI[{np.percentile(dr,2.5):.4f},{np.percentile(dr,97.5):.4f}] | "
          f"SHUFFLE int={np.median(ds):+.4f} CI[{np.percentile(ds,2.5):.4f},{np.percentile(ds,97.5):.4f}]")

json.dump({'daf_interactions':out,'n_sig':sig,'n_tot':tot},open('/tmp/mt29_partB_daf.json','w'),indent=2)
print("\nwrote /tmp/mt29_partB_daf.json")
