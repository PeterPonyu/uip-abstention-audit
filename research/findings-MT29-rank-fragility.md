# MT29 — Leaderboard rank fragility under unique-prototype split findings

Date: 2026-06-16

This audit evaluates whether model rankings remain stable when Matbench Discovery-style metrics are recomputed under the unique-prototype split (`unique_prototype == True`) versus the full dataset.

## Rank Correlation Summary
- **F1 Stability-Classification Ranking**: Kendall-τ = **`1.0000`** | Spearman = **`1.0000`**
- **MAE Formation-Energy Regressor Ranking**: Kendall-τ = **`1.0000`** | Spearman = **`1.0000`**

## Detailed Model Ranks and Displacements

### 1. F1 Stability-Classification Ranks

| Model | F1 Full | F1 Uniq | Rank Full | Rank Uniq | Rank Displacement [95% CI] |
| :--- | :---: | :---: | :---: | :---: | :---: |
| orb | 0.8596 | 0.8802 | 1 | 1 | 0 [0.0, 0.0] |
| mace | 0.8339 | 0.8505 | 2 | 2 | 0 [0.0, 0.0] |
| chgnet | 0.6099 | 0.6111 | 3 | 3 | 0 [0.0, 0.0] |
| m3gnet | 0.5734 | 0.5680 | 4 | 4 | 0 [0.0, 0.0] |
| MEGNet | 0.5105 | 0.5091 | 5 | 5 | 0 [0.0, 2.0] |
| CGCNN | 0.5089 | 0.5062 | 6 | 6 | 0 [-1.0, 1.0] |
| CGCNN+P | 0.5083 | 0.4995 | 7 | 7 | 0 [-2.0, 0.0] |
| ALIGNN-FF | 0.4914 | 0.4879 | 8 | 8 | 0 [0.0, 0.0] |

### 2. MAE Formation-Energy Ranks

| Model | MAE Full | MAE Uniq | Rank Full | Rank Uniq | Rank Displacement [95% CI] |
| :--- | :---: | :---: | :---: | :---: | :---: |
| orb | 0.0285 | 0.0282 | 1 | 1 | 0 [0.0, 1.0] |
| mace | 0.0292 | 0.0300 | 2 | 2 | 0 [-1.0, 0.0] |
| chgnet | 0.0611 | 0.0635 | 3 | 3 | 0 [0.0, 0.0] |
| m3gnet | 0.0726 | 0.0761 | 4 | 4 | 0 [0.0, 0.0] |
| CGCNN+P | 0.1083 | 0.1133 | 5 | 5 | 0 [0.0, 0.0] |
| MEGNet | 0.1282 | 0.1301 | 6 | 6 | 0 [0.0, 0.0] |
| CGCNN | 0.1350 | 0.1385 | 7 | 7 | 0 [0.0, 0.0] |
| ALIGNN-FF | 0.1404 | 0.1421 | 8 | 8 | 0 [0.0, 0.0] |

## Adjudication & Implications
- **F1 Ranking Fragility**: **`FALSE`** (Any model rank displacement > 1 or Kendall-τ < 0.9)
- **MAE Ranking Fragility**: **`FALSE`** (Any model rank displacement > 1 or Kendall-τ < 0.9)
- **Scientific Implications**: These findings show whether universal interatomic potential benchmarks are robust to structurally duplicate structures (prototypes) or if rank re-ordering occurs when structurally redundant information is removed from evaluation.
