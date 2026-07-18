# Sampled exemplar papers — presentation patterns borrowed for MT28/MT29

Purpose: ground MT28/MT29's *presentation* (structure, claim-scoping, hedging, novelty framing, limitations) in real comparable papers, and define how each scientific conclusion must be shown. DOIs verified vs CrossRef (2026-06-16).

## Exemplars and what each contributes

| Paper | DOI | Target venue | Presentation pattern borrowed |
| :--- | :--- | :--- | :--- |
| Riebesell et al., *Matbench Discovery* (*npj Comput Mater* 2024) | 10.1038/s41524-024-01261-z | **Digital Discovery** / **npj Comput Mater** | **Framework & benchmark structure**: Establishes the evaluation of universal interatomic potentials (UIPs) on WBM. MT28/MT29 reuses its predictions as raw inputs and audits decision calibration and rank robustness. |
| Sivaraman et al., Active learning of interatomic potentials (*npj Comput Mater* 2020) | 10.1038/s41524-020-00367-7 | **ML Science & Technology (MLST)** | **Uncertainty-driven decision framing**: Uses model disagreement to guide simulations. MT28 adapts this to design post-hoc boundary-abstention and calibration layers. |
| Batatia et al., MACE (*NeurIPS* 2022) | 10.48550/arXiv.2206.07697 | **Digital Discovery** / **MLST** | **UIP architecture & error baseline**: Describes message-passing neural network potentials. MT28/MT29 uses MACE as a primary state-of-the-art model. |

## How each conclusion must be presented (appropriateness checklist)

Every conclusion in the manuscript must carry, explicitly: **scope** (the universal interatomic potentials on WBM, not all materials models), an **uncertainty interval** (95% bootstrap CI), the **control** (predicted hull margin baseline), and the **honest "we do not claim"**. Mapping:

| Conclusion | Required presentation | Required caveat / "not claimed" |
| :--- | :--- | :--- |
| **MT28: Calibration gain** | Isotonic gain of **`0.0237`** [0.0157, 0.0309] at 70% coverage for ORB. | Scoped to thermodynamic stability; does not guarantee improvements in dynamic molecular simulation properties. |
| **MT28: Disagreement correlation** | Spearman correlation $\rho = 0.7142$ between ensemble disagreement and error. | Disagreement acts as a proxy for prediction error but is not a physical error bound. |
| **MT29: Rank robustness** | Kendall-τ = **`1.0000`** under unique-prototype split compared to full WBM. | Falsifies the "rank fragility" hypothesis on the Matbench Discovery dataset; rankings are structurally robust. |
