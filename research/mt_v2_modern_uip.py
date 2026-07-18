#!/usr/bin/env python
"""V2 — does the MT1 'triangle of peril' (low regression MAE != reliable stability decision) hold for
MODERN universal interatomic potentials (MACE / CHGNet / M3GNet / ORB), or do 2024 SOTA models close it?

Reuses Matbench Discovery WBM (registration-free): true e_form + e_above_hull (summary) + each model's
predicted formation energy. Modern-UIP preds = compact (material_id, e_form_pred) parsed from Figshare
geo-opt jsonl. 2020 anchors (CGCNN, CGCNN+P) re-scored from their repo CSVs. Predicted hull dist =
true_hull + (e_form_pred - e_form_true) (each_pred). Bootstrap 95% CIs. pandas+sklearn, CPU.
"""
import os, glob, json, math, re
import numpy as np, pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score
RNG=np.random.default_rng(0)
DATA=os.path.expanduser('~/mt_stage0/data')              # WBM summary + 2020 model csvs
UIP=os.path.expanduser('~/mt_uip')                        # modern-UIP *_pred.csv
E_FORM_TRUE='e_form_per_atom_mp2020_corrected'
E_HULL_TRUE='e_above_hull_mp2020_corrected_ppd_mp'

def load_summary():
    f=glob.glob(os.path.join(DATA,'*wbm-summary*.csv.gz'))[0]
    df=pd.read_csv(f, usecols=lambda c: c in ('material_id',E_FORM_TRUE,E_HULL_TRUE))
    return df.dropna(subset=[E_FORM_TRUE,E_HULL_TRUE])

def model_preds():
    """yield (name, df[material_id,e_form_pred]) for modern UIPs (compact) + 2020 anchors (ensemble mean)."""
    for f in sorted(glob.glob(os.path.join(UIP,'*_pred.csv'))):
        name=os.path.basename(f).replace('_pred.csv','')
        df=pd.read_csv(f); yield name, df[['material_id','e_form_pred']].dropna()
    for name,glb in [('CGCNN','*cgcnn-ens*IS2RE*.csv.gz'),('CGCNN+P','*cgcnn-perturb*IS2RE*.csv.gz'),
                     ('MEGNet','*megnet*IS2RE*.csv.gz'),('ALIGNN-FF','*alignn-ff*IS2RE*.csv.gz')]:
        fs=glob.glob(os.path.join(DATA,glb))
        if not fs: continue
        df=pd.read_csv(fs[0]); pc=[c for c in df.columns if c!='material_id' and 'ale' not in c.lower()]
        if not pc: continue
        df['e_form_pred']=df[pc].mean(axis=1); yield name, df[['material_id','e_form_pred']].dropna()

def boot_f1_ci(yt,yp,n=1000):
    v=[]
    for _ in range(n):
        i=RNG.integers(0,len(yt),len(yt))
        if 0<yt[i].sum()<len(i): v.append(f1_score(yt[i],yp[i],zero_division=0))
    return [round(float(np.percentile(v,2.5)),4),round(float(np.percentile(v,97.5)),4)] if v else [float('nan')]*2

def score(summ, name, dfp):
    m=summ.merge(dfp,on='material_id',how='inner').dropna(subset=['e_form_pred'])
    if len(m)<5000: return None
    m['hull_pred']=m[E_HULL_TRUE]+(m['e_form_pred']-m[E_FORM_TRUE])
    mae=float(np.abs(m['e_form_pred']-m[E_FORM_TRUE]).mean())
    yt=(m[E_HULL_TRUE]<0).astype(int).values; yp=(m['hull_pred']<0).astype(int).values
    tn=int(((yt==0)&(yp==0)).sum()); fp=int(((yt==0)&(yp==1)).sum())
    f1=f1_score(yt,yp,zero_division=0); prec=precision_score(yt,yp,zero_division=0); rec=recall_score(yt,yp,zero_division=0)
    fpr=fp/(fp+tn) if (fp+tn) else float('nan')
    # boundary abstention precision @ |hull_pred|>=0.05
    keep=np.abs(m['hull_pred'].values)>=0.05
    pa=precision_score(yt[keep],yp[keep],zero_division=0) if keep.sum()>50 and 0<yt[keep].sum() else float('nan')
    return {'model':name,'n':int(len(m)),'MAE_form':round(mae,4),'F1':round(float(f1),4),
            'F1_CI':boot_f1_ci(yt,yp),'precision':round(float(prec),4),'recall':round(float(rec),4),
            'FPR':round(float(fpr),4),'precision_abstain@0.05':round(float(pa),4),'abstain_cov':round(float(keep.mean()),3)}

def main():
    summ=load_summary(); print('WBM rows',len(summ),'stable',int((summ[E_HULL_TRUE]<0).sum()),flush=True)
    rows=[]
    for name,dfp in model_preds():
        r=score(summ,name,dfp)
        if r: rows.append(r); print(f"{name:10s} MAE {r['MAE_form']:.4f} | F1 {r['F1']} | FPR {r['FPR']} | prec {r['precision']} -> abstain {r['precision_abstain@0.05']}@{r['abstain_cov']}",flush=True)
    # triangle of peril: MAE rank vs F1 rank (Spearman) — if low MAE != high F1, regression misleads decision
    from scipy.stats import spearmanr
    maes=np.array([r['MAE_form'] for r in rows]); f1s=np.array([r['F1'] for r in rows])
    rho=float(spearmanr(maes,f1s).correlation) if len(rows)>=3 else float('nan')
    # do MODERN UIPs (lowest MAE) still misclassify near hull? compare best-MAE vs best-F1 model
    by_mae=sorted(rows,key=lambda r:r['MAE_form']); by_f1=sorted(rows,key=lambda r:-r['F1'])
    out={'experiment':'MT_V2_modern_UIP_triangle','spearman_MAE_vs_F1':round(rho,3),
         'note':'rho should be -1 (low MAE -> high F1) if regression predicts decision quality; rho>=0 = triangle persists',
         'best_MAE_model':by_mae[0]['model'],'best_F1_model':by_f1[0]['model'],
         'triangle_persists':bool(by_mae[0]['model']!=by_f1[0]['model']),'models':rows}
    json.dump(out,open(os.path.expanduser('~/mt_uip/mt_v2_result.json'),'w'),indent=2,default=str)
    L=['# MT V2 — triangle-of-peril for modern UIPs vs 2020 anchors','',
       'Predicted hull = true_hull + (e_form_pred - e_form_true); stable = e_above_hull<0. Lower MAE better regressor; higher F1 better decision.','',
       '| model | n | MAE_form (eV) | F1 | F1 CI | FPR | precision | abstain prec@0.05 |','|---|--:|--:|--:|---|--:|--:|--:|']
    for r in sorted(rows,key=lambda r:r['MAE_form']):
        L.append(f"| {r['model']} | {r['n']} | {r['MAE_form']} | {r['F1']} | ({r['F1_CI'][0]},{r['F1_CI'][1]}) | {r['FPR']} | {r['precision']} | {r['precision_abstain@0.05']} |")
    L+=['',f"Spearman(MAE, F1) = {round(rho,3)} (target -1 if regression predicts decision; >=0 = regression misleads).",
        f"Best-MAE model: {by_mae[0]['model']} (MAE {by_mae[0]['MAE_form']}, F1 {by_mae[0]['F1']}); best-F1 model: {by_f1[0]['model']} (F1 {by_f1[0]['F1']}, MAE {by_f1[0]['MAE_form']}).",
        f"**Triangle of peril persists (best regressor != best decider): {out['triangle_persists']}**"]
    open(os.path.expanduser('~/mt_uip/mt_v2_result.md'),'w').write('\n'.join(L)+'\n'); print('\n'.join(L))

if __name__=='__main__': main()
