#!/usr/bin/env python
"""V6 (MT) — is cross-model DISAGREEMENT a decision-grade uncertainty signal for stability classification?
The materials analogue of "the model's own uncertainty is a decision variable" (cf. V3 AD-predicts-error, V7
ensemble spread). No single model knows its own error; but 4 independent modern UIPs (MACE/CHGNet/M3GNet/ORB)
disagree more where they are wrong. We test, on the full leakage-removed WBM (256,963 structures):
  1. Does inter-model disagreement (std of e_form_pred across the 4 UIPs) predict the consensus error? [Spearman]
  2. Does abstaining on the most-disagreeing structures raise stability-classification precision? [coverage-risk]
  3. Shuffle control: permuted disagreement -> no precision gain.
  4. Are decision flips (wrong stable/unstable call) concentrated in the high-disagreement quartile?
Predicted hull = true_hull + (mean e_form_pred - e_form_true); stable = e_above_hull < 0. pandas+scipy, CPU.
"""
import os, glob, json, numpy as np, pandas as pd
from scipy.stats import spearmanr
RNG=np.random.default_rng(0)
DATA=os.path.expanduser('~/mt_stage0/data'); UIP=os.path.expanduser('~/mt_uip')
E_FORM_TRUE='e_form_per_atom_mp2020_corrected'; E_HULL_TRUE='e_above_hull_mp2020_corrected_ppd_mp'
MODELS=['mace','chgnet','m3gnet','orb']

def load():
    s=glob.glob(os.path.join(DATA,'*wbm-summary*.csv.gz'))[0]
    summ=pd.read_csv(s, usecols=lambda c: c in ('material_id',E_FORM_TRUE,E_HULL_TRUE)).dropna()
    df=summ.rename(columns={E_FORM_TRUE:'eft',E_HULL_TRUE:'hull_true'})
    for m in MODELS:
        p=pd.read_csv(os.path.join(UIP,f'{m}_pred.csv'))[['material_id','e_form_pred']].rename(columns={'e_form_pred':m})
        df=df.merge(p,on='material_id',how='inner')
    return df.dropna()

def precision_at_coverage(score, stable_pred, stable_true, cov):
    """keep the (1-? ) lowest-score (lowest-disagreement) fraction = cov; precision of 'stable' calls there."""
    n=len(score); k=int(cov*n); idx=np.argsort(score)[:k]
    sp=stable_pred[idx]; st=stable_true[idx]
    tp=int((sp&st).sum()); fp=int((sp&~st).sum())
    prec=tp/(tp+fp) if (tp+fp)>0 else float('nan')
    f1=(2*tp)/(2*tp+fp+int((~sp&st).sum())) if tp+fp>0 else float('nan')
    return prec, f1, int(sp.sum())

def main():
    df=load(); n=len(df)
    P=df[MODELS].values                              # (n,4) e_form_pred
    eft=df['eft'].values; hull_true=df['hull_true'].values
    disagree=P.std(axis=1)                            # cross-model std of e_form_pred == std of predicted hull
    ens=P.mean(axis=1)
    hull_pred=hull_true+(ens-eft)
    err=np.abs(hull_pred-hull_true)                  # = |ens e_form err|
    stable_true=hull_true<0; stable_pred=hull_pred<0
    # 1. disagreement predicts error?
    rho_e=float(spearmanr(disagree,err).correlation)
    # per-model: disagreement vs mean |per-model hull err|
    permerr=np.abs((hull_true[:,None]+(P-eft[:,None]))-hull_true[:,None]).mean(1)
    rho_pm=float(spearmanr(disagree,permerr).correlation)
    # 2. coverage-risk: precision of stable calls vs coverage (abstain on high disagreement)
    covs=[1.0,0.9,0.8,0.7,0.6,0.5]
    cr=[]
    for c in covs:
        pr,f1,ns=precision_at_coverage(disagree,stable_pred,stable_true,c)
        cr.append({'coverage':c,'precision':round(pr,4),'f1':round(f1,4),'n_called_stable':ns})
    base=cr[0]['precision']
    # 3. shuffle control at cov 0.7
    sh=disagree.copy(); RNG.shuffle(sh)
    pr_sh,_,_=precision_at_coverage(sh,stable_pred,stable_true,0.7)
    # bootstrap CI on precision gain (cov0.7 - full)
    boot=[]
    for _ in range(500):
        bi=RNG.integers(0,n,n)
        p07,_,_=precision_at_coverage(disagree[bi],stable_pred[bi],stable_true[bi],0.7)
        pfull,_,_=precision_at_coverage(disagree[bi],stable_pred[bi],stable_true[bi],1.0)
        boot.append(p07-pfull)
    gain_ci=[round(float(np.percentile(boot,2.5)),4),round(float(np.percentile(boot,97.5)),4)]
    # 4. decision flips by disagreement quartile
    flip=(stable_pred!=stable_true)
    fp=(stable_pred&~stable_true); fn=(~stable_pred&stable_true)   # false-stable / false-unstable
    q=np.quantile(disagree,[0.25,0.5,0.75])
    qidx=np.digitize(disagree,q)
    flip_by_q=[round(float(flip[qidx==i].mean()),4) for i in range(4)]
    fp_by_q=[round(float(fp[qidx==i].mean()),4) for i in range(4)]
    fn_by_q=[round(float(fn[qidx==i].mean()),4) for i in range(4)]
    out={'experiment':'V6_crossmodel_disagreement_reliability','n':n,'models':MODELS,
         'spearman_disagree_enserr':round(rho_e,4),'spearman_disagree_permodelerr':round(rho_pm,4),
         'coverage_risk':cr,'precision_full':base,'precision_cov0.7':cr[3]['precision'],
         'precision_cov0.7_shuffled':round(pr_sh,4),'precision_gain_cov0.7_CI':gain_ci,
         'flip_rate_by_disagreement_quartile':flip_by_q,
         'false_stable_FP_by_quartile':fp_by_q,'false_unstable_FN_by_quartile':fn_by_q}
    json.dump(out,open(os.path.join(UIP,'v6_result.json'),'w'),indent=2,default=str)
    L=['# V6 (MT) — cross-model disagreement as a stability-decision uncertainty signal','',
       f'4 modern UIPs (MACE/CHGNet/M3GNet/ORB) on full WBM (n={n}). Disagreement = std of e_form_pred across models.','',
       f"**Disagreement predicts consensus error:** Spearman(disagree, |err|) = **{rho_e:.3f}** "
       f"(per-model-mean err {rho_pm:.3f}).",'',
       '| coverage (keep lowest-disagreement) | stability precision | F1 | n called stable |','|--:|--:|--:|--:|']
    for r in cr: L.append(f"| {r['coverage']} | {r['precision']} | {r['f1']} | {r['n_called_stable']} |")
    L+=['',f"Precision gain abstaining on top-30% disagreement: {base} -> {cr[3]['precision']} "
        f"(bootstrap 95% CI on gain {gain_ci}); shuffled-disagreement control: {pr_sh:.4f} (≈no gain).",
        '',f"Decision-flip (mis-stable OR mis-unstable) rate by disagreement quartile "
        f"(Q1 low -> Q4 high): {flip_by_q}. NOTE: disagreement gates stable-call PRECISION (it filters "
        f"false-positive 'stable' calls), but does NOT track overall misclassification rate -- see findings.",
        f"  false-STABLE (FP) by quartile: {fp_by_q}  |  false-UNSTABLE (FN) by quartile: {fn_by_q}" ]
    open(os.path.join(UIP,'v6_result.md'),'w').write('\n'.join(L)+'\n'); print('\n'.join(L))

if __name__=='__main__': main()
