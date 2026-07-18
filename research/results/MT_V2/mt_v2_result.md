# MT V2 — triangle-of-peril for modern UIPs vs 2020 anchors

Predicted hull = true_hull + (e_form_pred - e_form_true); stable = e_above_hull<0. Lower MAE better regressor; higher F1 better decision.

| model | n | MAE_form (eV) | F1 | F1 CI | FPR | precision | abstain prec@0.05 |
|---|--:|--:|--:|---|--:|--:|--:|
| orb | 256963 | 0.0285 | 0.8596 | (0.8568,0.8622) | 0.0178 | 0.9023 | 0.9671 |
| mace | 256963 | 0.0292 | 0.8339 | (0.8313,0.8365) | 0.0352 | 0.8269 | 0.9531 |
| chgnet | 256963 | 0.0611 | 0.6099 | (0.6064,0.6133) | 0.1408 | 0.5151 | 0.7845 |
| m3gnet | 256963 | 0.0726 | 0.5734 | (0.5698,0.5767) | 0.2023 | 0.4442 | 0.6742 |
| CGCNN+P | 256961 | 0.1083 | 0.5083 | (0.5047,0.5121) | 0.1973 | 0.4069 | 0.5753 |
| MEGNet | 256963 | 0.1282 | 0.5105 | (0.5066,0.5141) | 0.1381 | 0.4562 | 0.4971 |
| CGCNN | 256961 | 0.135 | 0.5089 | (0.5052,0.5129) | 0.1477 | 0.4455 | 0.5851 |
| ALIGNN-FF | 256963 | 0.1404 | 0.4914 | (0.488,0.4945) | 0.2398 | 0.374 | 0.3963 |

Spearman(MAE, F1) = -0.929 (target -1 if regression predicts decision; >=0 = regression misleads).
Best-MAE model: orb (MAE 0.0285, F1 0.8596); best-F1 model: orb (F1 0.8596, MAE 0.0285).
**Triangle of peril persists (best regressor != best decider): False**
