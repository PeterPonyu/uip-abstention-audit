# MT28 GPU gap-bridge: disagreement-abstention robustness

Date: 2026-06-16

## Target-journal bridge conclusion

- Gate: **PASS_BRIDGE_TO_MANUSCRIPT**.
- V6 disagreement 70%-coverage precision gain posterior CI/median: `[0.027529, 0.033204, 0.038837]`; P(gain>0)=`1.0`; beats shuffle=`True`.
- Margin abstention observed mean precision gain across models: `0.1327`.
- Safe framing: decision-calibration/abstention card. Do **not** revive universal triangle-of-peril; V2 rejects it and V6b rejects model-routing as a route to better MAE.
- Remaining target-journal gap: None; the trivial |hull-margin| baseline has been added and compared with post-hoc calibration.

## Source artifacts

- `materials-mlip-research/research/results/MT_V2/mt_v2_result.json` — sha256 `bd4bb585f0e653bd0e80ec6117505d6846b1daca98783660e16c43273226c527`, bytes `2686`
- `materials-mlip-research/research/results/V6/v6_result.json` — sha256 `d09bfacf837210783029b33377a672bae007155a6f5520c3867aab1d414d965f`, bytes `1353`
- `materials-mlip-research/research/results/V6b/v6b_result.json` — sha256 `36d4cf3bf03edea440d280111ab8dfd3bc4f64742166a4061ca1778fed5767d3`, bytes `658`
- `materials-mlip-research/research/results/MT28/mt28_calibration_result.json` — sha256 `bb40c4b9896aad409ee818c4d9648f017153511b30c0ee17ff6b7c7fa223e625`, bytes `2559`

## Full JSON / tables / figures

- `gpu_gap_bridge_2026-06-16.json`
- `gpu_gap_bridge_margin_model_gains_2026-06-16.csv`
- `gpu_gap_bridge_margin_gains_2026-06-16.png`
