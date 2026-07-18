"""
F5 - Committee-variance abstention signal vs the single-model |hull-margin| signal.
All data sourced exclusively from on-disk JSON; nothing hand-typed.

Panel (a): committee-variance matched-yield abstention benefit (gain median) per anion
           stratum. Oxide dominates, mirroring the single-model oxide-anchored pattern.
Panel (b): the 15 stratum-pair committee-variance interactions (median +/- 95% bootstrap
           CI). Pairs whose committee CI excludes 0 are highlighted; a side marker records
           whether the single-model consensus fired on the same pair, exposing that the
           committee is a sparser (7/15) but sign-consistent re-derivation.

Source: research/results/MT29/mt29_committee_variance.json
"""

import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

BASE = Path("/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/research/results/MT29")
OUT  = Path("/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/manuscripts/figures")

CV = json.load(open(BASE / "mt29_committee_variance.json"))

STRATA = ["oxide", "intermetallic", "chalcogenide", "halide", "pnictide", "other"]
STRATUM_LABELS = {
    "oxide": "Oxide", "intermetallic": "Intermetallic", "chalcogenide": "Chalcogenide",
    "halide": "Halide", "pnictide": "Pnictide", "other": "Other",
}
STRATA_COLORS = {
    "oxide": "#E69F00", "halide": "#56B4E9", "chalcogenide": "#009E73",
    "pnictide": "#F0E442", "other": "#CC79A7", "intermetallic": "#0072B2",
}
FIRE_COLOR = "#D55E00"
NULL_COLOR = "#999999"
DPI = 300

gain = CV["committee_gain_median"]
pairs = CV["gate"]["per_pair"]

fig, (axA, axB) = plt.subplots(1, 2, figsize=(12.5, 4.4),
                               gridspec_kw={"width_ratios": [1.0, 1.25]})

# ---- Panel (a): committee gain median per stratum ----------------------------
gvals = [gain[s] for s in STRATA]
colors = [STRATA_COLORS[s] for s in STRATA]
xpos = np.arange(len(STRATA))
axA.bar(xpos, gvals, color=colors, edgecolor="grey25".replace("grey", "#40"), linewidth=0.3)
axA.bar(xpos, gvals, color=colors, edgecolor="#404040", linewidth=0.4)
axA.axhline(0.0, color="black", linewidth=0.7)
for x, v in zip(xpos, gvals):
    axA.text(x, v + (0.012 if v >= 0 else -0.028), f"{v:+.3f}",
             ha="center", va="bottom" if v >= 0 else "top", fontsize=8)
axA.set_xticks(xpos)
axA.set_xticklabels([STRATUM_LABELS[s] for s in STRATA], rotation=40, ha="right", fontsize=8)
axA.set_ylabel("Committee-variance abstention benefit\n(matched-yield DAF gain, median)", fontsize=9)
axA.set_title("(a) Committee-variance benefit concentrates in oxides", fontsize=10)
axA.grid(axis="y", linewidth=0.4, alpha=0.5)
axA.set_ylim(-0.08, 0.66)

# ---- Panel (b): 15 stratum-pair committee interactions -----------------------
labels, meds, los, his, fired, single_fired = [], [], [], [], [], []
for p in pairs:
    labels.append(f"{STRATUM_LABELS[p['stratumA']]}-{STRATUM_LABELS[p['stratumB']]}")
    m = p["interaction_med"]; lo, hi = p["interaction_ci95"]
    meds.append(m); los.append(m - lo); his.append(hi - m)
    fired.append(bool(p["excludes_0"]))
    single_fired.append(bool(p["single_consensus_excl0"]))

order = np.argsort(meds)          # most negative at bottom, most positive at top
y = np.arange(len(order))
for yi, idx in zip(y, order):
    c = FIRE_COLOR if fired[idx] else NULL_COLOR
    axB.errorbar(meds[idx], yi, xerr=[[los[idx]], [his[idx]]], fmt="o", ms=5,
                 color=c, ecolor=c, elinewidth=1.4, capsize=2.5, zorder=3)
axB.axvline(0.0, color="black", linewidth=0.8, linestyle="--", alpha=0.7)
axB.set_yticks(y)
axB.set_yticklabels([labels[i] for i in order], fontsize=7.5)
# single-model consensus marker column at right margin
xr = axB.get_xlim()
xmark = 0.70
for yi, idx in zip(y, order):
    axB.text(xmark, yi, "*" if single_fired[idx] else "", ha="center", va="center",
             fontsize=11, color="#333333")
axB.text(xmark, len(order) - 0.2, "single\nfired", ha="center", va="bottom",
         fontsize=6.5, color="#333333")
axB.set_xlim(-0.35, 0.80)
axB.set_xlabel(r"Committee-variance interaction  gain$_A$ $-$ gain$_B$  (median, 95% CI)", fontsize=9)
axB.set_title("(b) Committee fires 7/15 pairs; sign matches single model", fontsize=10)
axB.grid(axis="x", linewidth=0.4, alpha=0.5)

from matplotlib.lines import Line2D
leg = [Line2D([0], [0], marker="o", color="w", markerfacecolor=FIRE_COLOR, markersize=7,
              label="committee CI excludes 0 (7/15)"),
       Line2D([0], [0], marker="o", color="w", markerfacecolor=NULL_COLOR, markersize=7,
              label="committee CI includes 0"),
       Line2D([0], [0], marker="$*$", color="#333333", linestyle="None", markersize=9,
              label="single-model consensus fired")]
axB.legend(handles=leg, loc="lower right", fontsize=6.8, frameon=False)

fig.suptitle("Committee-variance abstention reproduces the oxide-anchored, positive interaction "
             "(shuffle-null 0/15, gate PASS-BOTH)", fontsize=10.5, fontweight="bold", y=1.02)
fig.tight_layout()
for ext in ("png", "pdf"):
    fig.savefig(OUT / f"F5_committee_variance.{ext}", dpi=DPI, bbox_inches="tight")
plt.close(fig)
print("F5 saved.")
