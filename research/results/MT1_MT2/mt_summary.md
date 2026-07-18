# MT1+MT2 Stage-0 — Matbench Discovery: regression vs stability-decision reliability

Predicted hull dist = true_hull + (e_form_pred - e_form_true); stable = e_above_hull < 0.

| model | n | MAE_form(eV) | clf F1 | F1 CI | precision | FPR | prec@cov0.05(margin abstain) |
|---|--:|--:|--:|---|--:|--:|---|
| CGCNN | 256961 | 0.135 | 0.5089 | (0.5054,0.5124) | 0.4455 | 0.1477 | 0.5851@0.696 |
| CGCNN+P | 256961 | 0.1083 | 0.5083 | (0.5049,0.5117) | 0.4069 | 0.1973 | 0.5753@0.558 |
| ALIGNN-FF | 256963 | 0.1404 | 0.4914 | (0.488,0.4947) | 0.374 | 0.2398 | 0.3963@0.691 |
| MEGNet | 256963 | 0.1282 | 0.5105 | (0.5069,0.5141) | 0.4562 | 0.1381 | 0.4971@0.754 |

## Triangle of peril (CGCNN vs CGCNN+P)
- CGCNN MAE_form 0.135 → clf F1 0.5089
- CGCNN+P MAE_form 0.1083 → clf F1 0.5083
- perturb lowers MAE: True · perturb worsens classification: True
- **triangle-of-peril reproduced: True** (lower/equal MAE yet worse stability F1)

## OOD degradation by WBM substitution step (1=near-MP → 5=most OOD)
- **CGCNN**: step1: F1 0.4782, MAE 0.1393 · step2: F1 0.537, MAE 0.1291 · step3: F1 0.4847, MAE 0.1255 · step4: F1 0.535, MAE 0.1374 · step5: F1 0.5335, MAE 0.1652
- **CGCNN+P**: step1: F1 0.5101, MAE 0.0982 · step2: F1 0.5466, MAE 0.1035 · step3: F1 0.466, MAE 0.1108 · step4: F1 0.5194, MAE 0.1099 · step5: F1 0.5197, MAE 0.135
- **ALIGNN-FF**: step1: F1 0.4541, MAE 0.134 · step2: F1 0.5214, MAE 0.1425 · step3: F1 0.4565, MAE 0.1496 · step4: F1 0.5303, MAE 0.1274 · step5: F1 0.5553, MAE 0.1435
- **MEGNet**: step1: F1 0.4669, MAE 0.1345 · step2: F1 0.5366, MAE 0.1267 · step3: F1 0.4872, MAE 0.121 · step4: F1 0.55, MAE 0.1247 · step5: F1 0.5491, MAE 0.1457
