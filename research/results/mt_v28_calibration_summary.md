# MT28 Hull-Boundary Decision Calibration & Conformal Abstention Results

We evaluate split-conformal isotonic calibration on WBM test predictions (n=256,963).

| Model | Cov 1.0 Prec | Cov 0.7 Cal Prec | Cov 0.7 Margin Prec | 95% CI of Difference | Beats Margin Baseline? |
|---|---:|---:|---:|---|:---:|
| orb | 0.9013 | 0.9699 | 0.9656 | (0.0004, 0.0082) | True |
| mace | 0.8261 | 0.9776 | 0.9518 | (0.0106, 0.0388) | True |
| chgnet | 0.5152 | 0.9168 | 0.7037 | (0.2053, 0.2210) | True |
| m3gnet | 0.4448 | 0.8197 | 0.5824 | (0.2221, 0.2497) | True |
