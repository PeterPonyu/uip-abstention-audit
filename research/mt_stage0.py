#!/usr/bin/env python
"""MT1+MT2 Stage-0 — Matbench Discovery: low regression error != reliable stability decision.

Uses ONLY registration-free CSVs (no pymatgen): WBM summary (true e_form + true e_above_hull) + per-model
formation-energy predictions. Predicted hull distance = true_hull + (e_form_pred - e_form_true) (the
standard matbench-discovery each_pred; convex hull held at MP2020-corrected).

Falsifiable checks:
  MT1 (classification vs regression mismatch / "triangle of peril"): a model with LOWER formation-energy
       MAE can have WORSE stability-classification F1 (decision near the 0 eV/atom hull boundary).
  MT1 (calibrated abstention): abstaining on |pred hull dist| < margin (the uncertain band) RAISES
       stability precision at fixed coverage.
  MT2 (OOD degradation): classification F1 / MAE degrade across WBM substitution steps 1->5 (more OOD).
Bootstrap 95% CIs throughout. Pandas/sklearn only.
"""
import os, glob, json, math, re
import numpy as np, pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score
RNG = np.random.default_rng(0)
DATA = os.path.expanduser('~/mt_stage0/data')
E_FORM_TRUE = 'e_form_per_atom_mp2020_corrected'
E_HULL_TRUE = 'e_above_hull_mp2020_corrected_ppd_mp'
MODELS = {  # display -> filename glob
    'CGCNN':      '*cgcnn-ens*IS2RE*.csv.gz',
    'CGCNN+P':    '*cgcnn-perturb*IS2RE*.csv.gz',
    'ALIGNN-FF':  '*alignn-ff*IS2RE*.csv.gz',
    'MEGNet':     '*megnet*IS2RE*.csv.gz',
}

def load_summary():
    f = glob.glob(os.path.join(DATA, '*wbm-summary*.csv.gz'))[0]
    df = pd.read_csv(f, usecols=lambda c: c in ('material_id', E_FORM_TRUE, E_HULL_TRUE))
    df = df.dropna(subset=[E_FORM_TRUE, E_HULL_TRUE])
    df['step'] = df['material_id'].str.extract(r'wbm-(\d+)-').astype(float)
    return df

def model_pred(fileglob, summ):
    fs = glob.glob(os.path.join(DATA, fileglob))
    if not fs: return None
    df = pd.read_csv(fs[0])
    pred_cols = [c for c in df.columns if c != 'material_id' and 'ale' not in c.lower()]
    if not pred_cols: return None
    df['e_form_pred'] = df[pred_cols].mean(axis=1)
    m = summ.merge(df[['material_id', 'e_form_pred']], on='material_id', how='inner').dropna(subset=['e_form_pred'])
    m['hull_pred'] = m[E_HULL_TRUE] + (m['e_form_pred'] - m[E_FORM_TRUE])
    return m

def clf_metrics(true_hull, pred_hull):
    yt = (true_hull < 0).astype(int); yp = (pred_hull < 0).astype(int)
    if yt.sum() == 0 or yt.sum() == len(yt):
        return dict(F1=float('nan'), precision=float('nan'), recall=float('nan'), FPR=float('nan'), acc=float('nan'))
    tn = int(((yt==0)&(yp==0)).sum()); fp = int(((yt==0)&(yp==1)).sum())
    return dict(F1=round(f1_score(yt,yp),4), precision=round(precision_score(yt,yp,zero_division=0),4),
                recall=round(recall_score(yt,yp,zero_division=0),4),
                FPR=round(fp/(fp+tn) if (fp+tn) else float('nan'),4),
                acc=round(float((yt==yp).mean()),4))

def boot_ci(fn, *arrs, n=1000):
    vals=[]; L=len(arrs[0])
    for _ in range(n):
        idx=RNG.integers(0,L,L); v=fn(*[a[idx] for a in arrs])
        if v==v: vals.append(v)
    return [round(float(np.percentile(vals,2.5)),4), round(float(np.percentile(vals,97.5)),4)] if vals else [float('nan')]*2

def f1_of(true_hull, pred_hull):
    yt=(true_hull<0).astype(int); yp=(pred_hull<0).astype(int)
    return f1_score(yt,yp,zero_division=0) if 0<yt.sum()<len(yt) else float('nan')

def main():
    summ = load_summary()
    print(f'WBM test rows: {len(summ)} | stable(true e_hull<0): {int((summ[E_HULL_TRUE]<0).sum())}', flush=True)
    rows=[]
    for name, g in MODELS.items():
        m = model_pred(g, summ)
        if m is None or len(m) < 1000:
            print(f'  {name}: SKIP (no data)', flush=True); continue
        mae_form = float(np.abs(m['e_form_pred']-m[E_FORM_TRUE]).mean())
        mae_hull = float(np.abs(m['hull_pred']-m[E_HULL_TRUE]).mean())
        cm = clf_metrics(m[E_HULL_TRUE].values, m['hull_pred'].values)
        f1ci = boot_ci(f1_of, m[E_HULL_TRUE].values, m['hull_pred'].values)
        # calibrated abstention near boundary: abstain |hull_pred| < margin; precision on remainder
        prec_full = cm['precision']
        prec_cov = {}
        for margin in (0.0, 0.02, 0.05, 0.1):
            keep = np.abs(m['hull_pred'].values) >= margin
            cov = float(keep.mean())
            if keep.sum() > 50:
                yt=(m[E_HULL_TRUE].values[keep]<0).astype(int); yp=(m['hull_pred'].values[keep]<0).astype(int)
                pr = precision_score(yt,yp,zero_division=0) if 0<yt.sum() else float('nan')
                prec_cov[f'm{margin}'] = {'coverage':round(cov,3),'precision':round(float(pr),4)}
        # OOD by WBM step
        steps={}
        for s in sorted(m['step'].dropna().unique()):
            ms=m[m['step']==s]
            if len(ms)>500:
                steps[int(s)]={'n':len(ms),'mae_form':round(float(np.abs(ms['e_form_pred']-ms[E_FORM_TRUE]).mean()),4),
                               'clf_F1':round(float(f1_of(ms[E_HULL_TRUE].values,ms['hull_pred'].values)),4)}
        rows.append({'model':name,'n':len(m),'MAE_form':round(mae_form,4),'MAE_hull':round(mae_hull,4),
                     'clf':cm,'clf_F1_CI':f1ci,'abstain_precision':prec_cov,'ood_by_step':steps})
        print(f"  {name}: MAE_form {mae_form:.4f} | clf F1 {cm['F1']} (CI {f1ci}) prec {cm['precision']} FPR {cm['FPR']} | "
              f"abstain prec {prec_full}->{prec_cov.get('m0.05',{}).get('precision')}@cov{prec_cov.get('m0.05',{}).get('coverage')}", flush=True)
    # triangle of peril: CGCNN vs CGCNN+P
    tri=None
    d={r['model']:r for r in rows}
    if 'CGCNN' in d and 'CGCNN+P' in d:
        a,b=d['CGCNN'],d['CGCNN+P']
        tri={'CGCNN_MAE_form':a['MAE_form'],'CGCNN+P_MAE_form':b['MAE_form'],
             'CGCNN_clf_F1':a['clf']['F1'],'CGCNN+P_clf_F1':b['clf']['F1'],
             'perturb_lowers_MAE':bool(b['MAE_form']<a['MAE_form']),
             'perturb_worsens_clf':bool(b['clf']['F1']<a['clf']['F1']),
             'triangle_of_peril_reproduced':bool(b['MAE_form']<=a['MAE_form'] and b['clf']['F1']<a['clf']['F1'])}
        print('\nTRIANGLE OF PERIL:', json.dumps(tri), flush=True)
    out={'experiment':'MT1_MT2_stage0','n_models':len(rows),'triangle_of_peril':tri,'models':rows}
    json.dump(out, open(os.path.expanduser('~/mt_stage0/mt_results.json'),'w'), indent=2, default=str)
    # md
    L=['# MT1+MT2 Stage-0 — Matbench Discovery: regression vs stability-decision reliability','',
       'Predicted hull dist = true_hull + (e_form_pred - e_form_true); stable = e_above_hull < 0.','',
       '| model | n | MAE_form(eV) | clf F1 | F1 CI | precision | FPR | prec@cov0.05(margin abstain) |',
       '|---|--:|--:|--:|---|--:|--:|---|']
    for r in rows:
        ab=r['abstain_precision'].get('m0.05',{})
        L.append(f"| {r['model']} | {r['n']} | {r['MAE_form']} | {r['clf']['F1']} | ({r['clf_F1_CI'][0]},{r['clf_F1_CI'][1]}) "
                 f"| {r['clf']['precision']} | {r['clf']['FPR']} | {ab.get('precision')}@{ab.get('coverage')} |")
    if tri:
        L+=['', '## Triangle of peril (CGCNN vs CGCNN+P)',
            f"- CGCNN MAE_form {tri['CGCNN_MAE_form']} → clf F1 {tri['CGCNN_clf_F1']}",
            f"- CGCNN+P MAE_form {tri['CGCNN+P_MAE_form']} → clf F1 {tri['CGCNN+P_clf_F1']}",
            f"- perturb lowers MAE: {tri['perturb_lowers_MAE']} · perturb worsens classification: {tri['perturb_worsens_clf']}",
            f"- **triangle-of-peril reproduced: {tri['triangle_of_peril_reproduced']}** (lower/equal MAE yet worse stability F1)"]
    L+=['', '## OOD degradation by WBM substitution step (1=near-MP → 5=most OOD)']
    for r in rows:
        seq=' · '.join(f"step{k}: F1 {v['clf_F1']}, MAE {v['mae_form']}" for k,v in sorted(r['ood_by_step'].items()))
        L.append(f"- **{r['model']}**: {seq}")
    open(os.path.expanduser('~/mt_stage0/mt_summary.md'),'w').write('\n'.join(L)+'\n')
    print('\n'.join(L))

if __name__=='__main__': main()
