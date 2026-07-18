# MT28 — Hull-boundary decision calibration audit findings

Date: 2026-06-16

This audit evaluates whether post-hoc calibrated confidence (Logistic/Isotonic Regression) mapping predicted hull distance to true stability improves stability-decision precision at 70% and 90% coverage relative to the raw absolute predicted hull-margin (`|hull_pred|`) baseline.

## Quantitative Table (Coverage 70% and 90%)

| Model | Coverage | Margin Precision | Isotonic Precision | Iso Gain [95% CI] | Log Precision | Log Gain [95% CI] | Cal Beats Margin? |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| chgnet | 70% | 0.70283 | 0.92387 | 0.22105 [0.21073, 0.23085] | 0.92555 | 0.22272 [0.21205, 0.23221] | YES |
| chgnet | 90% | 0.57435 | 0.54149 | -0.03285 [-0.03938, -0.02689] | 0.48270 | -0.09164 [-0.09752, -0.08583] | NO |
| m3gnet | 70% | 0.58755 | 0.39038 | -0.19716 [-0.28735, -0.10635] | 0.82331 | 0.23576 [0.22031, 0.24965] | NO |
| m3gnet | 90% | 0.49149 | 0.42314 | -0.06835 [-0.07332, -0.06417] | 0.38087 | -0.11062 [-0.11474, -0.10628] | NO |
| mace | 70% | 0.95094 | 0.94485 | -0.00609 [-0.03614, 0.01931] | 0.95291 | 0.00197 [-0.00092, 0.00480] | NO |
| mace | 90% | 0.91169 | 0.92406 | 0.01237 [0.01032, 0.01449] | 0.94259 | 0.03090 [0.02734, 0.03426] | YES |
| orb | 70% | 0.96646 | 0.99013 | 0.02367 [0.01573, 0.03086] | 0.96822 | 0.00176 [-0.00035, 0.00383] | YES |
| orb | 90% | 0.95695 | 0.94933 | -0.00762 [-0.00941, -0.00599] | 0.96199 | 0.00504 [0.00330, 0.00676] | NO |

## Adjudication & Implications
- **Trivial Margin Baseline Dominance**: If the Isotonic Gain CI includes 0 or is negative, it confirms that raw `|hull_pred|` is already the optimal decision variable for selective stability-prediction (abstention), and post-hoc calibration does not improve upon it near the hull boundary.
- **Kill Threshold**: If the gain CI includes 0 for all models, the calibration story is falsified, confirming that absolute hull distance is a sufficient uncertainty signal.
