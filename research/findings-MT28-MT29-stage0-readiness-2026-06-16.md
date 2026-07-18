# MT28/MT29 actual Stage-0 publication-readiness findings

Date: 2026-06-16

## 结论

- MT28: PASS — mean precision gain under margin abstention = 0.133; V6 disagreement 70% coverage gain = 0.033 with CI [0.0312, 0.0349].
- MT28 rescue wording: publish decision calibration / abstention, not the old universal triangle-of-peril.
- MT29: DATA_GATE_BLOCKED — prototype/time rank-fragility requires metadata absent from local cached outputs.

## Source artifacts

- `materials-mlip-research/research/results/MT28/mt28_calibration_result.json` — sha256 `bb40c4b9896aad409ee818c4d9648f017153511b30c0ee17ff6b7c7fa223e625`, bytes `2559`
- `materials-mlip-research/research/results/MT_V2/mt_v2_result.json` — sha256 `bd4bb585f0e653bd0e80ec6117505d6846b1daca98783660e16c43273226c527`, bytes `2686`
- `materials-mlip-research/research/results/V6/v6_result.json` — sha256 `d09bfacf837210783029b33377a672bae007155a6f5520c3867aab1d414d965f`, bytes `1353`
- `materials-mlip-research/research/results/V6b/v6b_result.json` — sha256 `36d4cf3bf03edea440d280111ab8dfd3bc4f64742166a4061ca1778fed5767d3`, bytes `658`

## 机器可读摘要

```json
{
  "MT28": {
    "abstention_coverage_median_all_models": 0.6635,
    "abstention_precision_gain_mean_all_models": 0.13269999999999998,
    "abstention_precision_gain_median_all_models": 0.13289999999999996,
    "abstention_precision_gain_range_all_models": [
      0.022299999999999986,
      0.2694
    ],
    "best_f1_model": "orb",
    "best_mae_model": "orb",
    "claim_scope": "materials_decision_calibration",
    "disagreement_gain_beats_shuffle": true,
    "disagreement_precision_gain_CI": [
      0.0312,
      0.0349
    ],
    "disagreement_precision_gain_at_70cov": 0.03320000000000001,
    "gate_state": "PASS",
    "modern_model_precision_gain_mean": 0.17259999999999998,
    "n_structures": 256963,
    "next_required_inputs": [],
    "per_model": [
      {
        "abstention_coverage": 0.567,
        "f1": 0.6099,
        "mae_form": 0.0611,
        "model": "chgnet",
        "n": 256963,
        "precision_abstain_margin_0p05": 0.7845,
        "precision_full": 0.5151,
        "precision_gain": 0.2694
      },
      {
        "abstention_coverage": 0.531,
        "f1": 0.5734,
        "mae_form": 0.0726,
        "model": "m3gnet",
        "n": 256963,
        "precision_abstain_margin_0p05": 0.6742,
        "precision_full": 0.4442,
        "precision_gain": 0.23000000000000004
      },
      {
        "abstention_coverage": 0.651,
        "f1": 0.8339,
        "mae_form": 0.0292,
        "model": "mace",
        "n": 256963,
        "precision_abstain_margin_0p05": 0.9531,
        "precision_full": 0.8269,
        "precision_gain": 0.12619999999999998
      },
      {
        "abstention_coverage": 0.676,
        "f1": 0.8596,
        "mae_form": 0.0285,
        "model": "orb",
        "n": 256963,
        "precision_abstain_margin_0p05": 0.9671,
        "precision_full": 0.9023,
        "precision_gain": 0.06479999999999997
      },
      {
        "abstention_coverage": 0.696,
        "f1": 0.5089,
        "mae_form": 0.135,
        "model": "CGCNN",
        "n": 256961,
        "precision_abstain_margin_0p05": 0.5851,
        "precision_full": 0.4455,
        "precision_gain": 0.13959999999999995
      },
      {
        "abstention_coverage": 0.558,
        "f1": 0.5083,
        "mae_form": 0.1083,
        "model": "CGCNN+P",
        "n": 256961,
        "precision_abstain_margin_0p05": 0.5753,
        "precision_full": 0.4069,
        "precision_gain": 0.16840000000000005
      },
      {
        "abstention_coverage": 0.754,
        "f1": 0.5105,
        "mae_form": 0.1282,
        "model": "MEGNet",
        "n": 256963,
        "precision_abstain_margin_0p05": 0.4971,
        "precision_full": 0.4562,
        "precision_gain": 0.04089999999999999
      },
      {
        "abstention_coverage": 0.691,
        "f1": 0.4914,
        "mae_form": 0.1404,
        "model": "ALIGNN-FF",
        "n": 256963,
        "precision_abstain_margin_0p05": 0.3963,
        "precision_full": 0.374,
        "precision_gain": 0.022299999999999986
      }
    ],
    "publication_gate": "Proceed with full decision-calibration and selective stability-prediction manuscript; calibration beats predicted hull margin near the boundary.",
    "scientific_result": "Hull-margin / disagreement abstention improves stable-material precision on cached WBM/UIP predictions; calibration audit completed showing that post-hoc calibrated confidence (Logistic/Isotonic Regression) improves stability precision (e.g. ORB Isotonic gain = 0.0237, CI [0.0157, 0.0309] at 70% coverage) relative to predicted hull-margin.",
    "source_artifacts": [
      {
        "bytes": 2686,
        "path": "materials-mlip-research/research/results/MT_V2/mt_v2_result.json",
        "sha256": "bd4bb585f0e653bd0e80ec6117505d6846b1daca98783660e16c43273226c527"
      },
      {
        "bytes": 1353,
        "path": "materials-mlip-research/research/results/V6/v6_result.json",
        "sha256": "d09bfacf837210783029b33377a672bae007155a6f5520c3867aab1d414d965f"
      },
      {
        "bytes": 658,
        "path": "materials-mlip-research/research/results/V6b/v6b_result.json",
        "sha256": "36d4cf3bf03edea440d280111ab8dfd3bc4f64742166a4061ca1778fed5767d3"
      },
      {
        "bytes": 2559,
        "path": "materials-mlip-research/research/results/MT28/mt28_calibration_result.json",
        "sha256": "bb40c4b9896aad409ee818c4d9648f017153511b30c0ee17ff6b7c7fa223e625"
      }
    ],
    "spearman_mae_vs_f1": -0.929,
    "status": "PASS",
    "triangle_persists": false,
    "v6_spearman_disagreement_ensemble_error": 0.7142,
    "v6b_model_routing_beats_best_single": false,
    "v6b_model_routing_beats_ensemble_mean": false
  },
  "MT29": {
    "claim_scope": "materials_leaderboard_fragility",
    "gate_state": "DATA_GATE",
    "local_evidence_checked": [
      "materials-mlip-research/research/results/MT_V2/mt_v2_result.json",
      "materials-mlip-research/research/results/V6/v6_result.json",
      "materials-mlip-research/research/results/V6b/v6b_result.json"
    ],
    "missing_required_inputs": [
      "per-structure prototype/family labels",
      "train/test year or release-time metadata",
      "leaderboard predictions keyed by prototype/time split"
    ],
    "next_required_inputs": [
      "per-structure prototype/family labels",
      "train/test year or release-time metadata",
      "leaderboard predictions keyed by prototype/time split"
    ],
    "publication_gate": "Do not claim MT29 result yet; next run must materialize prototype/time metadata and compute Kendall-tau rank shifts.",
    "scientific_result": "Prototype/time leaderboard-fragility spike could not be run from local artifacts because prototype/time metadata are absent from the cached result JSONs.",
    "source_artifacts": [
      {
        "bytes": 2686,
        "path": "materials-mlip-research/research/results/MT_V2/mt_v2_result.json",
        "sha256": "bd4bb585f0e653bd0e80ec6117505d6846b1daca98783660e16c43273226c527"
      },
      {
        "bytes": 1353,
        "path": "materials-mlip-research/research/results/V6/v6_result.json",
        "sha256": "d09bfacf837210783029b33377a672bae007155a6f5520c3867aab1d414d965f"
      },
      {
        "bytes": 658,
        "path": "materials-mlip-research/research/results/V6b/v6b_result.json",
        "sha256": "36d4cf3bf03edea440d280111ab8dfd3bc4f64742166a4061ca1778fed5767d3"
      },
      {
        "bytes": 2559,
        "path": "materials-mlip-research/research/results/MT28/mt28_calibration_result.json",
        "sha256": "bb40c4b9896aad409ee818c4d9648f017153511b30c0ee17ff6b7c7fa223e625"
      }
    ],
    "status": "DATA_GATE_BLOCKED"
  },
  "domain": "materials-mlip"
}
```
