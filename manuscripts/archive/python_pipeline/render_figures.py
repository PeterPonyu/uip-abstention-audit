"""
Render 4 publication figures for the MT29 chemistry-stratified value-of-abstention paper.
All data sourced exclusively from on-disk JSON result files; no fabrication.

Figures:
  F1 — DAF-vs-coverage per anion stratum (4 panels, one per UIP model)
  F2 — Stratum x model interaction heatmap (matched-yield gain_median, CI-excl-0 annotated)
  F3 — LOEO + WBM-round robustness panel
  F4 — Shuffle-null contrast (real vs shuffled interaction distributions)
"""

import json
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

# ── paths ──────────────────────────────────────────────────────────────────────
BASE = Path("/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/research/results/MT29")
OUT  = Path("/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/manuscripts/figures")
OUT.mkdir(parents=True, exist_ok=True)

MYR  = json.load(open(BASE / "mt29_stage1_matched_yield_result.json"))   # matched-yield
CYR  = json.load(open(BASE / "mt29_stage1_chem_yield_result.json"))      # stratified curves
S2R  = json.load(open(BASE / "mt29_stage2_robustness_result.json"))      # stage-2 robustness

# ── shared constants ────────────────────────────────────────────────────────────
MODELS  = ["chgnet", "m3gnet", "mace", "orb"]
MODEL_LABELS = {"chgnet": "CHGNet", "m3gnet": "M3GNet", "mace": "MACE", "orb": "ORB"}

STRATA  = ["oxide", "halide", "chalcogenide", "pnictide", "other", "intermetallic"]
STRATUM_LABELS = {
    "oxide":         "Oxide",
    "halide":        "Halide",
    "chalcogenide":  "Chalcogenide",
    "pnictide":      "Pnictide",
    "other":         "Other",
    "intermetallic": "Intermetallic",
}

# Colourblind-safe palette for strata
STRATA_COLORS = {
    "oxide":         "#E69F00",
    "halide":        "#56B4E9",
    "chalcogenide":  "#009E73",
    "pnictide":      "#F0E442",
    "other":         "#CC79A7",
    "intermetallic": "#0072B2",
}

DPI = 300
COVERAGE_KEYS = ["cov_50", "cov_70", "cov_90"]
COV_VALS      = [50, 70, 90]   # percent coverage

# ─────────────────────────────────────────────────────────────────────────────
# F1 — DAF-vs-coverage per anion stratum, 4 model panels
# ─────────────────────────────────────────────────────────────────────────────
def make_f1():
    sc = CYR["stratified_curves"]   # sc[stratum][model][cov_key]['daf']

    fig, axes = plt.subplots(1, 4, figsize=(14, 3.8), sharey=False)
    fig.suptitle(
        "F1 — DAF vs. Coverage per Anion Stratum (Matched-Yield Control)",
        fontsize=11, fontweight="bold", y=1.01,
    )

    for ax_idx, model in enumerate(MODELS):
        ax = axes[ax_idx]
        for stratum in STRATA:
            if stratum not in sc:
                continue
            model_data = sc[stratum].get(model, {})
            if not model_data:
                continue
            daf_vals = [model_data[ck]["daf"] for ck in COVERAGE_KEYS]
            ax.plot(
                COV_VALS, daf_vals,
                marker="o", markersize=5,
                color=STRATA_COLORS[stratum],
                label=STRATUM_LABELS[stratum],
                linewidth=1.8,
            )

        # base-rate DAF=1 line
        ax.axhline(1.0, color="black", linewidth=0.7, linestyle="--", alpha=0.5)
        ax.set_title(MODEL_LABELS[model], fontsize=10)
        ax.set_xlabel("Coverage (%)", fontsize=9)
        if ax_idx == 0:
            ax.set_ylabel("DAF", fontsize=9)
        ax.set_xticks(COV_VALS)
        ax.tick_params(labelsize=8)
        ax.grid(axis="y", linewidth=0.4, alpha=0.5)

    # shared legend
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles, labels,
        loc="lower center", ncol=6, fontsize=8,
        bbox_to_anchor=(0.5, -0.08), frameon=False,
    )

    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"F1_daf_vs_coverage.{ext}", dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print("F1 saved.")


# ─────────────────────────────────────────────────────────────────────────────
# F2 — Stratum × model heatmap (matched-yield gain_median)
#       Annotate cells where the majority of pairwise interactions CI-excl-0
# ─────────────────────────────────────────────────────────────────────────────
def make_f2():
    budgets   = MYR["per_model_budgets"]   # [model]['gain_median'][stratum]
    raw_pairs = MYR["interactions_matched_yield"]  # list of {model, stratumA, stratumB, excludes_0, ...}

    # Build gain matrix (strata × models)
    gain = np.full((len(STRATA), len(MODELS)), np.nan)
    for m_idx, model in enumerate(MODELS):
        for s_idx, stratum in enumerate(STRATA):
            gain[s_idx, m_idx] = budgets[model]["gain_median"].get(stratum, np.nan)

    # Per-(stratum, model): fraction of pairings that exclude 0
    # A cell is "CI-excl-0 dominant" if >50% of its pairings exclude 0
    excl0_frac = np.zeros((len(STRATA), len(MODELS)))
    pair_counts = np.zeros((len(STRATA), len(MODELS)))
    for p in raw_pairs:
        m_idx = MODELS.index(p["model"])
        for stratum in (p["stratumA"], p["stratumB"]):
            if stratum in STRATA:
                s_idx = STRATA.index(stratum)
                pair_counts[s_idx, m_idx] += 1
                if p["excludes_0"]:
                    excl0_frac[s_idx, m_idx] += 1
    # normalise
    mask = pair_counts > 0
    excl0_frac[mask] /= pair_counts[mask]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    fig.suptitle(
        "F2 — Matched-Yield Abstention Gain (DAF) per Stratum × Model\n"
        "Cells framed in black = CI excludes 0 for >50% of pairings",
        fontsize=10, fontweight="bold",
    )

    vmax = np.nanmax(np.abs(gain))
    im = ax.imshow(gain, cmap="RdYlGn", aspect="auto",
                   vmin=-vmax * 0.5, vmax=vmax)

    ax.set_xticks(range(len(MODELS)))
    ax.set_xticklabels([MODEL_LABELS[m] for m in MODELS], fontsize=9)
    ax.set_yticks(range(len(STRATA)))
    ax.set_yticklabels([STRATUM_LABELS[s] for s in STRATA], fontsize=9)
    ax.set_xlabel("Model", fontsize=10)
    ax.set_ylabel("Anion-class Stratum", fontsize=10)

    for s_idx in range(len(STRATA)):
        for m_idx in range(len(MODELS)):
            val = gain[s_idx, m_idx]
            if np.isnan(val):
                continue
            frac = excl0_frac[s_idx, m_idx]
            # annotate value
            txt_color = "black" if abs(val) < vmax * 0.55 else "white"
            ax.text(m_idx, s_idx, f"{val:+.2f}",
                    ha="center", va="center", fontsize=8, color=txt_color, fontweight="bold")
            # frame cell if CI-excl-0 dominant
            if frac > 0.5:
                rect = mpatches.FancyBboxPatch(
                    (m_idx - 0.48, s_idx - 0.48), 0.96, 0.96,
                    boxstyle="square,pad=0", linewidth=2.0,
                    edgecolor="black", facecolor="none",
                    transform=ax.transData, zorder=5,
                )
                ax.add_patch(rect)

    cbar = fig.colorbar(im, ax=ax, shrink=0.85, pad=0.02)
    cbar.set_label("Abstention gain (ΔDAF)", fontsize=9)
    cbar.ax.tick_params(labelsize=8)

    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"F2_interaction_heatmap.{ext}", dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print("F2 saved.")


# ─────────────────────────────────────────────────────────────────────────────
# F3 — LOEO + WBM-round robustness panel
# ─────────────────────────────────────────────────────────────────────────────
def make_f3():
    loeo_data = S2R["gate1_loeo"]
    rnd_data  = S2R["gate2_rounds"]

    # Compute per-element counts
    elements = sorted(loeo_data.keys())
    elem_excl0 = []
    elem_total = []
    for elem in elements:
        ints = loeo_data[elem]["interactions"]
        elem_excl0.append(sum(1 for x in ints if x.get("excludes_0")))
        elem_total.append(len(ints))

    # Per-round counts
    rounds = ["1", "2", "3", "4", "5"]
    rnd_excl0  = []
    rnd_total  = []
    rnd_nrows  = []
    rnd_shuf   = []
    for rnd in rounds:
        r = rnd_data[rnd]
        ints = r["interactions"]
        rnd_excl0.append(sum(1 for x in ints if x.get("excludes_0")))
        rnd_total.append(len(ints))
        rnd_nrows.append(r["n_rows"])
        rnd_shuf.append(sum(1 for x in r.get("interactions_SHUFFLE", []) if x.get("excludes_0")))

    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(13, 4.5),
                                      gridspec_kw={"width_ratios": [3, 2]})
    fig.suptitle(
        "F3 — Robustness: Leave-One-Element-Out (left) and WBM-Round (right)",
        fontsize=11, fontweight="bold",
    )

    # --- left: LOEO bar chart ---
    x = np.arange(len(elements))
    bar_colors = ["#E69F00" if e == "O" else "#56B4E9" for e in elements]
    bars = ax_l.bar(x, elem_excl0, color=bar_colors, edgecolor="black", linewidth=0.7, zorder=3)
    # baseline 48/60
    ax_l.axhline(48, color="crimson", linestyle="--", linewidth=1.5,
                 label="Baseline (48/60, full cohort)", zorder=5)
    ax_l.set_xticks(x)
    ax_l.set_xticklabels([f"drop {e}" for e in elements], rotation=45, ha="right", fontsize=8)
    ax_l.set_ylabel("Cells CI-excl-0 (of total)", fontsize=9)
    ax_l.set_title("Leave-One-Element-Out (12 elements)", fontsize=10)
    ax_l.set_ylim(0, max(elem_total) + 4)
    ax_l.legend(fontsize=8, loc="lower right")
    # annotate total
    for bar_i, (bar, tot) in enumerate(zip(bars, elem_total)):
        ax_l.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                  f"/{tot}", ha="center", va="bottom", fontsize=7, color="#333333")
    ax_l.grid(axis="y", linewidth=0.4, alpha=0.5)
    # highlight O bar label
    ax_l.get_xticklabels()[elements.index("O")].set_color("#E69F00")
    ax_l.get_xticklabels()[elements.index("O")].set_fontweight("bold")

    # --- right: WBM-round trajectory ---
    rnd_x = np.arange(1, 6)
    rnd_fracs_real = [e / t for e, t in zip(rnd_excl0, rnd_total)]
    ax_r.bar(rnd_x - 0.2, rnd_excl0, width=0.38, color="#009E73", edgecolor="black",
             linewidth=0.7, label="Real interactions CI-excl-0", zorder=3)
    ax_r.bar(rnd_x + 0.2, rnd_shuf, width=0.38, color="#CC79A7", edgecolor="black",
             linewidth=0.7, label="Shuffle-null CI-excl-0", zorder=3)
    ax_r.axhline(30, color="black", linestyle=":", linewidth=1.0,
                 label="Majority threshold (30/60)")
    ax_r.set_xticks(rnd_x)
    ax_r.set_xticklabels([f"Round {r}" for r in rounds], fontsize=8)
    ax_r.set_ylabel("Cells CI-excl-0 (of 60)", fontsize=9)
    ax_r.set_title("WBM Acquisition Round (temporal)", fontsize=10)
    ax_r.set_ylim(0, 70)
    ax_r.legend(fontsize=8, loc="upper right")
    # annotate n_rows
    for ri, (nrows, excl) in enumerate(zip(rnd_nrows, rnd_excl0)):
        ax_r.text(ri + 1, excl + 1.5, f"n={nrows//1000}k",
                  ha="center", va="bottom", fontsize=7, color="#333333")
    ax_r.grid(axis="y", linewidth=0.4, alpha=0.5)

    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"F3_robustness_panel.{ext}", dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print("F3 saved.")


# ─────────────────────────────────────────────────────────────────────────────
# F4 — Shuffle-null contrast (real vs shuffled interaction distributions)
# ─────────────────────────────────────────────────────────────────────────────
def make_f4():
    real_ints   = MYR["interactions_matched_yield"]
    shuf_ints   = MYR["interactions_matched_yield_SHUFFLE"]

    # Per-model: median interaction values
    real_by_model = {m: [] for m in MODELS}
    shuf_by_model = {m: [] for m in MODELS}
    for entry in real_ints:
        real_by_model[entry["model"]].append(entry["interaction_med"])
    for entry in shuf_ints:
        shuf_by_model[entry["model"]].append(entry["interaction_med"])

    # Also aggregate all-model distributions
    all_real = [e["interaction_med"] for e in real_ints]
    all_shuf = [e["interaction_med"] for e in shuf_ints]

    fig, axes = plt.subplots(1, 5, figsize=(15, 4.0), sharey=False)
    fig.suptitle(
        "F4 — Shuffle-Null Contrast: Real vs. Shuffled Interaction (Median ΔDAF)",
        fontsize=11, fontweight="bold",
    )

    def plot_panel(ax, real_vals, shuf_vals, title):
        bins = np.linspace(
            min(min(real_vals), min(shuf_vals)) - 0.05,
            max(max(real_vals), max(shuf_vals)) + 0.05,
            25,
        )
        ax.hist(real_vals, bins=bins, color="#E69F00", alpha=0.75, label="Real", edgecolor="black", linewidth=0.5, density=True)
        ax.hist(shuf_vals, bins=bins, color="#56B4E9", alpha=0.75, label="Shuffle-null", edgecolor="black", linewidth=0.5, density=True)
        ax.axvline(0, color="black", linewidth=1.2, linestyle="--")
        ax.set_title(title, fontsize=9)
        ax.set_xlabel("Median ΔDAF", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(axis="y", linewidth=0.4, alpha=0.5)
        # count CI-excl-0
        n_real_pos = sum(1 for v in real_vals if v > 0)
        ax.text(0.97, 0.95, f"Real >0: {n_real_pos}/{len(real_vals)}",
                transform=ax.transAxes, ha="right", va="top", fontsize=7,
                color="#E69F00", fontweight="bold")

    # Per-model panels
    for ax_idx, model in enumerate(MODELS):
        plot_panel(
            axes[ax_idx],
            real_by_model[model], shuf_by_model[model],
            MODEL_LABELS[model],
        )
        if ax_idx == 0:
            axes[ax_idx].set_ylabel("Density", fontsize=8)

    # Aggregated panel
    plot_panel(axes[4], all_real, all_shuf, "All models\n(aggregated)")

    handles = [
        mpatches.Patch(facecolor="#E69F00", alpha=0.75, label="Real"),
        mpatches.Patch(facecolor="#56B4E9", alpha=0.75, label="Shuffle-null"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=2, fontsize=9,
               bbox_to_anchor=(0.5, -0.06), frameon=False)

    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"F4_shuffle_null_contrast.{ext}", dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print("F4 saved.")


# ─────────────────────────────────────────────────────────────────────────────
# F1 (paper main figure, filename F1_daf_coverage) — matched-yield DAF at the
# looser (Y_loose) vs tighter (Y_tight, abstaining) budgets, per stratum & model.
# Replaces the retired R script F1_daf_coverage.R (deprecated_R_pipeline/) whose
# external ggtheme.R dependency no longer exists on disk. Matches the paper's
# Fig. 1 caption. All values read from mt29_stage1_matched_yield_result.json.
# ─────────────────────────────────────────────────────────────────────────────
def make_f1_budget_bars():
    pmb = MYR["per_model_budgets"]   # [model]['daf_top_y_loose'/'daf_top_y_tight'][stratum]
    strata_order = ["oxide", "intermetallic", "chalcogenide", "halide", "pnictide", "other"]

    fig, axes = plt.subplots(1, 4, figsize=(14, 3.8), sharey=False)
    fig.suptitle(
        "F1 — Matched-yield DAF: looser (Y$_{loose}$) vs. abstaining (Y$_{tight}$) budget",
        fontsize=11, fontweight="bold", y=1.01,
    )
    x = np.arange(len(strata_order))
    width = 0.36
    c_loose, c_tight = "#999999", "#E69F00"
    for ax_idx, model in enumerate(MODELS):
        ax = axes[ax_idx]
        b = pmb[model]
        loose = [b["daf_top_y_loose"][s] for s in strata_order]
        tight = [b["daf_top_y_tight"][s] for s in strata_order]
        ax.bar(x - width / 2, loose, width, color=c_loose, edgecolor="grey",
               linewidth=0.4, label="looser yield (Y$_{loose}$)")
        ax.bar(x + width / 2, tight, width, color=c_tight, edgecolor="grey",
               linewidth=0.4, label="abstaining (Y$_{tight}$)")
        ax.axhline(1.0, color="black", linewidth=0.7, linestyle="--", alpha=0.5)
        ax.set_title(MODEL_LABELS[model], fontsize=10)
        ax.set_xticks(x)
        ax.set_xticklabels([STRATUM_LABELS[s] for s in strata_order],
                           rotation=40, ha="right", fontsize=8)
        if ax_idx == 0:
            ax.set_ylabel("discovery acceleration factor (DAF)", fontsize=9)
        ax.tick_params(labelsize=8)
        ax.grid(axis="y", linewidth=0.4, alpha=0.5)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, fontsize=9,
               bbox_to_anchor=(0.5, -0.10), frameon=False)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"F1_daf_coverage.{ext}", dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print("F1 (budget bars, paper Fig. 1) saved.")


# ─────────────────────────────────────────────────────────────────────────────
# F4 (paper main figure, filename F4_shuffle_null) — real vs. within-stratum
# confidence-shuffled |interaction| per gate (Stage-1 / LOEO / WBM-round).
# Replaces the retired R script F4_shuffle_null.R (deprecated_R_pipeline/).
# Matches the paper's Fig. 4 caption. All values read from
# mt29_stage1_matched_yield_result.json and mt29_stage2_robustness_result.json.
# ─────────────────────────────────────────────────────────────────────────────
def make_f4_gate_contrast():
    gates = {
        "Stage-1 (60 cells)": (
            MYR["interactions_matched_yield"],
            MYR["interactions_matched_yield_SHUFFLE"],
        ),
        "LOEO (700 cells)": (
            [c for e in S2R["gate1_loeo"].values() for c in e["interactions"]],
            [c for e in S2R["gate1_loeo"].values() for c in e["interactions_SHUFFLE"]],
        ),
        "WBM round (300 cells)": (
            [c for r in S2R["gate2_rounds"].values() for c in r["interactions"]],
            [c for r in S2R["gate2_rounds"].values() for c in r["interactions_SHUFFLE"]],
        ),
    }
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), sharey=False)
    fig.suptitle(
        "F4 — Real vs. confidence-shuffled |interaction| per gate",
        fontsize=11, fontweight="bold", y=1.01,
    )
    for ax, (title, (real_cells, shuf_cells)) in zip(axes, gates.items()):
        real_abs = np.abs([c["interaction_med"] for c in real_cells])
        shuf_abs = np.abs([c["interaction_med"] for c in shuf_cells])
        n_real_excl = sum(1 for c in real_cells if c["excludes_0"])
        n_shuf_excl = sum(1 for c in shuf_cells if c["excludes_0"])
        bins = np.linspace(0.0, max(real_abs.max(), shuf_abs.max()) * 1.05, 30)
        ax.hist(real_abs, bins=bins, color="#E69F00", alpha=0.75, density=True,
                edgecolor="black", linewidth=0.4, label="Real")
        ax.hist(shuf_abs, bins=bins, color="#56B4E9", alpha=0.75, density=True,
                edgecolor="black", linewidth=0.4, label="Shuffle-null")
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("|median interaction| (ΔDAF)", fontsize=8)
        ax.tick_params(labelsize=8)
        ax.grid(axis="y", linewidth=0.4, alpha=0.5)
        ax.text(0.97, 0.95,
                f"CI-excl-0 — real: {n_real_excl}/{len(real_cells)}\n"
                f"shuffle: {n_shuf_excl}/{len(shuf_cells)}",
                transform=ax.transAxes, ha="right", va="top", fontsize=7.5)
    axes[0].set_ylabel("Density", fontsize=9)
    handles = [
        mpatches.Patch(facecolor="#E69F00", alpha=0.75, label="Real"),
        mpatches.Patch(facecolor="#56B4E9", alpha=0.75, label="Shuffle-null"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=2, fontsize=9,
               bbox_to_anchor=(0.5, -0.08), frameon=False)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"F4_shuffle_null.{ext}", dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print("F4 (per-gate contrast, paper Fig. 4) saved.")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    make_f1()              # supplementary: DAF-vs-coverage curves (F1_daf_vs_coverage)
    make_f2()
    make_f3()
    make_f4()              # supplementary: per-model median-ΔDAF contrast (F4_shuffle_null_contrast)
    make_f1_budget_bars()  # paper Fig. 1 (F1_daf_coverage)
    make_f4_gate_contrast()# paper Fig. 4 (F4_shuffle_null)
    print("All figures rendered.")
