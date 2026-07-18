"""V6b (materials) — is cross-model disagreement a PER-MODEL error flag and a MODEL-ROUTING signal? Reuses the
V6 data (4 modern UIPs on full WBM). For each UIP: Spearman(disagreement, |that model's e_form error|). Routing:
can disagreement-weighted model selection (pick, per structure, the model closest to the consensus) beat the
single best model's MAE? graph/base env, pandas+scipy, CPU.
"""
import os, glob, json, numpy as np, pandas as pd
from scipy.stats import spearmanr
DATA=os.path.expanduser('~/mt_stage0/data'); UIP=os.path.expanduser('~/mt_uip')
E_FORM_TRUE='e_form_per_atom_mp2020_corrected'; E_HULL_TRUE='e_above_hull_mp2020_corrected_ppd_mp'
MODELS=['mace','chgnet','m3gnet','orb']
s=glob.glob(os.path.join(DATA,'*wbm-summary*.csv.gz'))[0]
df=pd.read_csv(s, usecols=lambda c: c in ('material_id',E_FORM_TRUE,E_HULL_TRUE)).dropna().rename(columns={E_FORM_TRUE:'eft'})
for m in MODELS:
    p=pd.read_csv(os.path.join(UIP,f'{m}_pred.csv'))[['material_id','e_form_pred']].rename(columns={'e_form_pred':m})
    df=df.merge(p,on='material_id',how='inner')
df=df.dropna(); P=df[MODELS].values; eft=df['eft'].values; n=len(df)
disagree=P.std(axis=1); errs={m:np.abs(P[:,i]-eft) for i,m in enumerate(MODELS)}
rows=[{'model':m,'MAE':round(float(errs[m].mean()),4),'spearman_disagree_err':round(float(spearmanr(disagree,errs[m]).correlation),4)} for i,m in enumerate(MODELS)]
# routing: per structure, the consensus-closest model (oracle-free: closest to the 4-model mean)
ens=P.mean(1); dist=np.abs(P-ens[:,None]); pick=dist.argmin(1)
routed_pred=P[np.arange(n),pick]; routed_mae=float(np.abs(routed_pred-eft).mean())
best_single=min(rows,key=lambda r:r['MAE']); ens_mae=float(np.abs(ens-eft).mean())
out={'experiment':'V6b_per_model_disagreement_and_routing','n':n,'per_model':rows,
     'best_single_MAE':best_single['MAE'],'ensemble_mean_MAE':round(ens_mae,4),
     'consensus_closest_routing_MAE':round(routed_mae,4),
     'routing_beats_best_single':bool(routed_mae<best_single['MAE']),
     'routing_beats_ensemble_mean':bool(routed_mae<ens_mae)}
json.dump(out,open(os.path.join(UIP,'v6b_result.json'),'w'),indent=2,default=str)
L=['# V6b (materials) — disagreement as a per-model error flag + model routing (WBM, 4 UIPs)','',
   f'n={n}. Disagreement = std of e_form_pred across MACE/CHGNet/M3GNet/ORB.','',
   '| model | MAE (eV) | Spearman(disagreement, |error|) |','|---|--:|--:|']
for r in rows: L.append(f"| {r['model']} | {r['MAE']} | {r['spearman_disagree_err']} |")
L+=['',f"Best single model MAE: {best_single['model']} {best_single['MAE']}. Ensemble-mean MAE: {ens_mae:.4f}.",
    f"Consensus-closest routing MAE: {routed_mae:.4f} (beats best single: {out['routing_beats_best_single']}; beats ensemble-mean: {out['routing_beats_ensemble_mean']}).",
    '','Per-model Spearman>0 = disagreement flags each per-model error; routing tests if disagreement enables label-free model selection.']
open(os.path.join(UIP,'v6b_result.md'),'w').write('\n'.join(L)+'\n'); print('\n'.join(L))
print('[v6b-done]')
