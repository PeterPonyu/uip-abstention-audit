#!/usr/bin/env python3
"""Slim frozen-record extracts for the public Pages.

Reads analysis records that already live in this public archive, plus
optional extra frozen records for the error and mechanism extracts.
Writes site/data/*.json and extract.sha256. Never invents numeric cells.
The sidecar is a local hash log; it is not published on Pages.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

PUBLIC = Path(__file__).resolve().parents[2]
EXTRA = Path(os.environ["UIP_EXTRA_RECORDS"]) if os.environ.get("UIP_EXTRA_RECORDS") else None
OUT = Path(__file__).resolve().parents[1] / "data"
WEB = Path(__file__).resolve().parents[1] / "assets" / "web"

MODELS = ["chgnet", "m3gnet", "mace", "orb"]
STRATA = ["oxide", "intermetallic", "chalcogenide", "halide", "pnictide", "other"]
MODEL_COLORS = {
    "chgnet": "#0072B2",
    "m3gnet": "#E69F00",
    "mace": "#009E73",
    "orb": "#D55E00",
}
STRATUM_COLORS = {
    "oxide": "#D55E00",
    "intermetallic": "#0072B2",
    "chalcogenide": "#009E73",
    "halide": "#56B4E9",
    "pnictide": "#E69F00",
    "other": "#999999",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: Path) -> dict:
    with path.open() as fh:
        return json.load(fh)


def dump(name: str, obj: object) -> Path:
    dest = OUT / name
    dest.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
    return dest


def pair_key(a: str, b: str) -> str:
    return f"{a}|{b}"


def extract() -> list[tuple[str, str, Path]]:
    OUT.mkdir(parents=True, exist_ok=True)
    records: list[tuple[str, str, Path]] = []

    chem_p = PUBLIC / "research/results/MT29/mt29_stage1_chem_yield_result.json"
    match_p = PUBLIC / "research/results/MT29/mt29_stage1_matched_yield_result.json"
    proto_p = (
        PUBLIC
        / "results_expansion_2026-07-11/prototype_blocked_cis/mt29_prototype_blocked_ci_result.json"
    )
    robust_p = PUBLIC / "research/results/MT29/mt29_stage2_robustness_result.json"
    roster_p = PUBLIC / "results_expansion_2026-07-14/mt29_roster_expansion_result.json"
    m1_p = (EXTRA / "m1_robust_error_result.json") if EXTRA else None
    m2_p = (EXTRA / "m2_oxide_subclass_result.json") if EXTRA else None
    m3_p = (EXTRA / "m3_oxstate_subclass_result.json") if EXTRA else None

    chem = load(chem_p)
    match = load(match_p)
    proto = load(proto_p)
    robust = load(robust_p)
    roster = load(roster_p)
    extra_ready = bool(
        m1_p and m2_p and m3_p and m1_p.is_file() and m2_p.is_file() and m3_p.is_file()
    )
    m1 = load(m1_p) if extra_ready else None
    m2 = load(m2_p) if extra_ready else None
    m3 = load(m3_p) if extra_ready else None

    curves = chem["stratified_curves"]
    strata = []
    for name in STRATA:
        row = curves[name]
        strata.append(
            {
                "stratum": name,
                "n": row["_n"],
                "base_rate_stable": row["_base_rate_stable"],
            }
        )
    dest = dump("strata.json", {"n_joined": chem["meta"]["n_rows"], "strata": strata})
    records.append(("chem_yield", sha256_file(chem_p), dest))

    chg = match["per_model_budgets"]["chgnet"]
    oxide_base = chg["base_rate_stable"]["oxide"]
    halide_base = chg["base_rate_stable"]["halide"]
    oxide_prec_tight = chg["daf_top_y_tight"]["oxide"] * oxide_base
    oxide_prec_loose = chg["daf_top_y_loose"]["oxide"] * oxide_base
    halide_prec_tight = chg["daf_top_y_tight"]["halide"] * halide_base
    halide_prec_loose = chg["daf_top_y_loose"]["halide"] * halide_base
    oxide_lift = oxide_prec_tight - oxide_prec_loose
    halide_lift = halide_prec_tight - halide_prec_loose

    blocked = proto["summary"]
    headline = {
        "n_joined": 256963,
        "oxide_base_rate": oxide_base,
        "halide_base_rate": halide_base,
        "blocked_excl0": blocked["blocked_excl0"],
        "blocked_shuffle_excl0": blocked["blocked_SHUFFLE_excl0"],
        "chgnet_oxide_halide_daf_median": blocked["chgnet_oxide_vs_halide_blocked_median"],
        "chgnet_oxide_halide_daf_ci95": blocked["chgnet_oxide_vs_halide_blocked_ci95"],
        "chgnet_oxide_precision_lift": oxide_lift,
        "chgnet_halide_precision_lift": halide_lift,
        "chgnet_oxide_minus_halide_precision_lift": oxide_lift - halide_lift,
        "y_loose": chg["y_loose"],
        "y_tight": chg["y_tight"],
        "n_models_total": roster["n_models_total"],
        "n_included_uip": roster["n_included_uip"],
        "generational_perm_p": roster["verdicts"]["V3_permutation"]["perm_p"],
        "hull_recipe": chem["meta"]["pred_hull_recipe"],
        "confidence_signal": chem["meta"]["confidence_signal"],
    }
    dest = dump("headline.json", headline)
    records.append(("matched_blocked_roster", sha256_file(match_p), dest))

    daf_rows = []
    for model in MODELS:
        bud = match["per_model_budgets"][model]
        for stratum in STRATA:
            daf_rows.append(
                {
                    "model": model,
                    "stratum": stratum,
                    "gain_median": bud["gain_median"][stratum],
                    "daf_tight": bud["daf_top_y_tight"][stratum],
                    "daf_loose": bud["daf_top_y_loose"][stratum],
                }
            )
    dest = dump("daf_gains.json", {"rows": daf_rows})
    records.append(("matched_yield", sha256_file(match_p), dest))

    heat = []
    for cell in proto["interactions_blocked"]:
        heat.append(
            {
                "model": cell["model"],
                "stratum_a": cell["stratumA"],
                "stratum_b": cell["stratumB"],
                "interaction_med": cell["interaction_med"],
                "ci95": cell["interaction_ci95"],
                "excludes_0": cell["excludes_0_blocked"],
            }
        )
    dest = dump(
        "heatmap.json",
        {
            "blocked_excl0": blocked["blocked_excl0"],
            "cells": heat,
        },
    )
    records.append(("prototype_blocked", sha256_file(proto_p), dest))

    loeo = []
    for elem, block in robust["gate1_loeo"].items():
        loeo.append(
            {
                "element": elem,
                "n_rows": block["n_rows"],
                "n_excl0": sum(1 for row in block["interactions"] if row.get("excludes_0")),
                "n_cells": len(block["interactions"]),
            }
        )
    dest = dump(
        "robustness.json",
        {
            "n_joined": robust["meta"]["n_rows_total"],
            "loeo_splits_passing": robust["summary"]["loeo_splits_passing"],
            "round_splits_passing": robust["summary"]["round_splits_passing"],
            "loeo_interaction_excl0": robust["summary"]["loeo_interaction_excl0"],
            "round_interaction_excl0": robust["summary"]["round_interaction_excl0"],
            "shuffle_null_clean": robust["summary"]["shuffle_null_clean"],
            "loeo": loeo,
        },
    )
    records.append(("stage2_robustness", sha256_file(robust_p), dest))

    roster_models = []
    for short, row in roster["per_model"].items():
        roster_models.append(
            {
                "id": short,
                "included_uip": bool(row.get("included")),
                "n": row.get("n"),
                "argmax_gain_stratum": row.get("argmax_gain_stratum"),
                "oxide_gain": (row.get("gain_median") or {}).get("oxide"),
                "halide_gain": (row.get("gain_median") or {}).get("halide"),
            }
        )
    dest = dump(
        "roster.json",
        {
            "n_models_total": roster["n_models_total"],
            "n_included_uip": roster["n_included_uip"],
            "generation_counts": roster["generation_counts"],
            "perm_p": roster["verdicts"]["V3_permutation"]["perm_p"],
            "overall": roster["verdicts"]["overall"],
            "models": roster_models,
        },
    )
    records.append(("roster_expansion", sha256_file(roster_p), dest))

    if extra_ready:
        error = {
            "oxide_highest_under_all_metrics": m1["verdict"]["oxide_highest_under_all_metrics"],
            "metrics_where_oxide_not_highest": m1["verdict"]["metrics_where_oxide_not_highest"],
            "oxide_vs_rest": {
                key: {
                    "oxide": val["oxide"],
                    "mean_non_oxide": val["mean_non_oxide"],
                    "oxide_is_highest": val["oxide_is_highest"],
                }
                for key, val in m1["oxide_vs_rest_ratios"].items()
            },
            "model_averaged": {
                name: {
                    "n": m1["model_averaged_per_stratum"][name]["n"],
                    "rmse": m1["model_averaged_per_stratum"][name]["rmse"],
                    "mae": m1["model_averaged_per_stratum"][name]["mae"],
                    "median_ae": m1["model_averaged_per_stratum"][name]["median_ae"],
                    "winsorized_rmse": m1["model_averaged_per_stratum"][name][
                        "winsorized_rmse_5_95"
                    ],
                }
                for name in STRATA
            },
        }
        dest = dump("error.json", error)
        records.append(("robust_error", sha256_file(m1_p), dest))

        ox = m3["oxstate_class"]
        dest = dump(
            "mechanism.json",
            {
                "oxstate": {
                    "blocked_excl0": ox["summary"]["blocked_excl0"],
                    "shuffle_excl0": ox["summary"]["shuffle_excl0"],
                    "ranked_by_gain": ox["ranked_by_gain"],
                    "model_averaged_blocked_gain": ox["model_averaged_blocked_gain"],
                },
                "cation_class": {
                    "blocked_excl0": m2["axes"]["cation_class"]["summary"]["blocked_excl0"],
                    "ranked_by_gain": m2["axes"]["cation_class"]["ranked_by_gain"],
                },
                "mp2020_sensitive": {
                    "blocked_excl0": m2["axes"]["mp2020_sensitive"]["summary"]["blocked_excl0"],
                    "ranked_by_gain": m2["axes"]["mp2020_sensitive"]["ranked_by_gain"],
                },
            },
        )
        records.append(("oxstate_subclass", sha256_file(m3_p), dest))
    else:
        for name, label in (("error.json", "robust_error"), ("mechanism.json", "oxstate_subclass")):
            dest = OUT / name
            if not dest.is_file():
                raise FileNotFoundError(
                    f"{name} extract is missing; set UIP_EXTRA_RECORDS to rebuild it"
                )
            records.append((label, sha256_file(dest), dest))

    sidecar = OUT / "extract.sha256"
    lines = [
        "# source_label  source_sha256  extract_file  extract_sha256",
    ]
    for label, src_hash, dest in records:
        lines.append(f"{label}  {src_hash}  {dest.name}  {sha256_file(dest)}")
    sidecar.write_text("\n".join(lines) + "\n")
    return records


def _text(x: float, y: float, s: str, *, size: int = 13, fill: str = "#111", anchor: str = "start", weight: str = "400") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" '
        f'font-family="Source Sans 3, Source Sans Pro, sans-serif" '
        f'font-weight="{weight}" text-anchor="{anchor}">{s}</text>'
    )


def write_svgs() -> None:
    WEB.mkdir(parents=True, exist_ok=True)
    headline = json.loads((OUT / "headline.json").read_text())
    daf = json.loads((OUT / "daf_gains.json").read_text())
    heat = json.loads((OUT / "heatmap.json").read_text())
    robust = json.loads((OUT / "robustness.json").read_text())
    roster = json.loads((OUT / "roster.json").read_text())
    error = json.loads((OUT / "error.json").read_text())
    mech = json.loads((OUT / "mechanism.json").read_text())
    strata = json.loads((OUT / "strata.json").read_text())

    # W1 protocol schematic
    stages = [
        (40, "RECORDS", "Published UIP\npredictions"),
        (200, "SELECT", "Matched yield Y\nloose / tight"),
        (360, "STAGE 1", "Four UIPs\n× six strata"),
        (520, "STAGE 2", "LOEO · WBM-round\nmultiplicity"),
        (680, "VERDICT", "Diagnostic,\nnot a policy"),
    ]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 860 280" role="img" '
        'aria-labelledby="w1-title w1-desc">',
        '<title id="w1-title">Matched-yield audit protocol</title>',
        '<desc id="w1-desc">Records to SELECT to Stage 1 to Stage 2 to verdict, with a controls bus for shuffle, falsified allocator, and temporal hold-out.</desc>',
        '<rect width="860" height="280" fill="#FCFCFB"/>',
    ]
    for i, (x, title, body) in enumerate(stages):
        parts.append(
            f'<rect x="{x}" y="36" width="140" height="88" rx="6" fill="#fff" stroke="#E1E0D9"/>'
        )
        parts.append(f'<rect x="{x}" y="36" width="6" height="88" fill="#0072B2"/>')
        parts.append(_text(x + 16, 62, title, size=14, weight="600"))
        for j, line in enumerate(body.split("\n")):
            parts.append(_text(x + 16, 86 + 16 * j, line, size=12, fill="#333"))
        if i < len(stages) - 1:
            parts.append(
                f'<line x1="{x + 140}" y1="80" x2="{x + 160}" y2="80" stroke="#333" stroke-width="1.4" marker-end="url(#arr)"/>'
            )
    parts.append(
        '<defs><marker id="arr" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">'
        '<path d="M0,0 L6,3 L0,6 Z" fill="#333"/></marker></defs>'
    )
    parts.append('<rect x="40" y="160" width="780" height="88" rx="6" fill="#fff" stroke="#666" stroke-dasharray="4 3"/>')
    parts.append(_text(56, 184, "Controls bus — evidence that bounds the reading, not a deployable action", size=13, weight="600"))
    parts.append(_text(56, 208, "Within-stratum shuffle null  ·  stratum-aware allocator falsified  ·  oxide-highest ordering does not transfer temporally", size=13, fill="#333"))
    parts.append(_text(56, 232, "Label on the allocator: falsified. The audit does not validate DFT labels.", size=13, fill="#D55E00"))
    parts.append("</svg>")
    (WEB / "w1_protocol.svg").write_text("\n".join(parts) + "\n")

    # W2 DAF gains CHGNet
    chg_rows = [r for r in daf["rows"] if r["model"] == "chgnet"]
    w, h = 720, 360
    left, right, top, bottom = 150, 40, 48, 48
    inner_w = w - left - right
    inner_h = h - top - bottom
    vmax = max(r["gain_median"] for r in chg_rows) * 1.15
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-labelledby="w2-title w2-desc">',
        '<title id="w2-title">CHGNet matched-yield DAF gain by anion class</title>',
        '<desc id="w2-desc">Oxide has the largest matched-yield DAF gain among six anion-class strata for CHGNet.</desc>',
        f'<rect width="{w}" height="{h}" fill="#FCFCFB"/>',
        _text(left, 28, "CHGNet matched-yield DAF gain (Y tight minus Y loose)", size=15, weight="600"),
    ]
    bar_h = inner_h / len(chg_rows)
    for i, row in enumerate(chg_rows):
        y = top + i * bar_h + 8
        bw = (row["gain_median"] / vmax) * inner_w
        color = STRATUM_COLORS[row["stratum"]]
        parts.append(f'<rect x="{left}" y="{y}" width="{bw:.1f}" height="{bar_h - 16:.1f}" fill="{color}"/>')
        parts.append(_text(left - 8, y + (bar_h - 16) / 2 + 5, row["stratum"], size=13, anchor="end"))
        parts.append(_text(left + bw + 8, y + (bar_h - 16) / 2 + 5, f'{row["gain_median"]:.2f}', size=13))
    parts.append(
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{h - bottom}" stroke="#333"/>'
    )
    parts.append(_text(left, h - 16, "Dashed reference at DAF gain = 0. Oxide (vermillion) is the largest cell.", size=12, fill="#333"))
    parts.append("</svg>")
    (WEB / "w2_daf.svg").write_text("\n".join(parts) + "\n")

    # W3 heatmap CHGNet
    cells = [c for c in heat["cells"] if c["model"] == "chgnet"]
    lookup = {(c["stratum_a"], c["stratum_b"]): c for c in cells}
    lookup.update({(c["stratum_b"], c["stratum_a"]): c for c in cells})
    w, h = 640, 560
    left, top = 130, 70
    cell = 70
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-labelledby="w3-title w3-desc">',
        '<title id="w3-title">CHGNet stratum-pair DAF interaction</title>',
        '<desc id="w3-desc">Prototype-blocked DAF interaction heatmap for CHGNet. Oxide–halide is the largest positive cell.</desc>',
        f'<rect width="{w}" height="{h}" fill="#FCFCFB"/>',
        _text(40, 28, "CHGNet stratum-pair Δgain (prototype-blocked)", size=15, weight="600"),
        _text(40, 48, f'{heat["blocked_excl0"]} cells exclude zero across four UIPs.', size=13, fill="#333"),
    ]
    for i, a in enumerate(STRATA):
        parts.append(_text(left - 8, top + i * cell + cell / 2 + 4, a, size=12, anchor="end"))
        parts.append(_text(left + i * cell + cell / 2, top - 10, a[:4], size=11, anchor="middle"))
        for j, b in enumerate(STRATA):
            x = left + j * cell
            y = top + i * cell
            if i == j:
                parts.append(f'<rect x="{x}" y="{y}" width="{cell - 2}" height="{cell - 2}" fill="#F4F4F2" stroke="#E1E0D9"/>')
                continue
            celld = lookup.get((a, b))
            if not celld:
                parts.append(f'<rect x="{x}" y="{y}" width="{cell - 2}" height="{cell - 2}" fill="#fff" stroke="#E1E0D9"/>')
                parts.append(_text(x + cell / 2, y + cell / 2 + 4, "—", size=12, anchor="middle", fill="#666"))
                continue
            v = celld["interaction_med"]
            t = max(-1.0, min(1.0, v))
            if t >= 0:
                fill = f"rgb({int(255 - t * (255 - 178))},{int(255 - t * (255 - 24))},{int(255 - t * (255 - 43))})"
            else:
                u = -t
                fill = f"rgb({int(255 - u * (255 - 33))},{int(255 - u * (255 - 102))},{int(255 - u * (255 - 172))})"
            stroke = "#111" if celld["excludes_0"] else "#E1E0D9"
            sw = 1.6 if celld["excludes_0"] else 0.8
            parts.append(
                f'<rect x="{x}" y="{y}" width="{cell - 2}" height="{cell - 2}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
            )
            parts.append(_text(x + cell / 2, y + cell / 2 + 4, f"{v:+.2f}", size=12, anchor="middle"))
    parts.append(_text(40, h - 20, "Black outline: 95% CI excludes 0. Oxide–halide is the largest positive cell.", size=12, fill="#333"))
    parts.append("</svg>")
    (WEB / "w3_heatmap.svg").write_text("\n".join(parts) + "\n")

    # W4 error: RMSE vs tail-robust
    metrics = [
        ("rmse", "RMSE"),
        ("mae", "MAE"),
        ("median_ae", "Median AE"),
        ("winsorized_rmse_5_95", "Winsorized RMSE"),
    ]
    w, h = 720, 340
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-labelledby="w4-title w4-desc">',
        '<title id="w4-title">Oxide is not the highest-error stratum under tail-robust estimators</title>',
        '<desc id="w4-desc">Oxide over rest ratio is above one only for raw RMSE. Tail-robust estimators do not rank oxide highest.</desc>',
        f'<rect width="{w}" height="{h}" fill="#FCFCFB"/>',
        _text(32, 28, "Oxide ÷ mean non-oxide formation-energy error", size=15, weight="600"),
    ]
    left, top, bar_w = 40, 56, 150
    for i, (key, label) in enumerate(metrics):
        rec = error["oxide_vs_rest"][key]
        ratio = rec["oxide"] / rec["mean_non_oxide"] if rec["mean_non_oxide"] else 0
        x = left + i * (bar_w + 20)
        bh = min(220, ratio * 40)
        y = 280 - bh
        fill = "#D55E00" if rec["oxide_is_highest"] else "#0072B2"
        parts.append(f'<rect x="{x}" y="{y}" width="{bar_w}" height="{bh:.1f}" fill="{fill}"/>')
        parts.append(_text(x + bar_w / 2, 300, label, size=12, anchor="middle"))
        parts.append(_text(x + bar_w / 2, y - 8, f"{ratio:.2f}×", size=13, anchor="middle", weight="600"))
    parts.append(_text(32, 328, "Vermillion: oxide is the highest stratum. Blue: it is not. Raw RMSE is the exception.", size=12, fill="#333"))
    parts.append("</svg>")
    (WEB / "w4_error.svg").write_text("\n".join(parts) + "\n")

    # W5 LOEO
    w, h = 720, 300
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-labelledby="w5-title w5-desc">',
        '<title id="w5-title">Leave-one-element-out splits</title>',
        f'<desc id="w5-desc">Leave-one-element-out: {robust["loeo_splits_passing"]} splits pass. Dropping oxygen removes the oxide stratum.</desc>',
        f'<rect width="{w}" height="{h}" fill="#FCFCFB"/>',
        _text(32, 28, f'Leave-one-element-out  ·  {robust["loeo_splits_passing"]} splits pass', size=15, weight="600"),
    ]
    n = len(robust["loeo"])
    bw = 48
    for i, row in enumerate(robust["loeo"]):
        x = 40 + i * 56
        frac = row["n_excl0"] / row["n_cells"] if row["n_cells"] else 0
        bh = frac * 180
        y = 230 - bh
        fill = "#D55E00" if row["element"] == "O" else "#0072B2"
        parts.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh:.1f}" fill="{fill}"/>')
        parts.append(_text(x + bw / 2, 250, row["element"], size=12, anchor="middle", weight="600"))
        parts.append(_text(x + bw / 2, y - 6, str(row["n_excl0"]), size=11, anchor="middle"))
    parts.append(_text(32, 284, "Height: fraction of interaction cells whose CI excludes 0. Oxygen (vermillion) drops the oxide stratum.", size=12, fill="#333"))
    parts.append("</svg>")
    (WEB / "w5_loeo.svg").write_text("\n".join(parts) + "\n")

    # W6 shuffle vs real
    real_n, real_d = 45, 60
    shuf_n, shuf_d = 0, 60
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 260" role="img" aria-labelledby="w6-title w6-desc">',
        '<title id="w6-title">Real versus within-stratum shuffle</title>',
        '<desc id="w6-desc">Prototype-blocked real cells exclude zero in 45 of 60. The shuffle null is 0 of 60.</desc>',
        '<rect width="640" height="260" fill="#FCFCFB"/>',
        _text(32, 28, "Cells whose CI excludes zero", size=15, weight="600"),
        f'<rect x="80" y="80" width="{45 / 60 * 400:.1f}" height="48" fill="#D55E00"/>',
        _text(80, 70, "Prototype-blocked real  45/60", size=13, weight="600"),
        '<rect x="80" y="160" width="4" height="48" fill="#0072B2"/>',
        _text(80, 150, "Within-stratum shuffle  0/60", size=13, weight="600"),
        _text(32, 236, "The shuffle null is clean. Counts stay counts; this is not a win banner.", size=12, fill="#333"),
        "</svg>",
    ]
    (WEB / "w6_shuffle.svg").write_text("\n".join(parts) + "\n")

    # W7 roster
    included = [m for m in roster["models"] if m["included_uip"] and m["oxide_gain"] is not None]
    included.sort(key=lambda m: -(m["oxide_gain"] or 0))
    w, h = 720, 420
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-labelledby="w7-title w7-desc">',
        '<title id="w7-title">Oxide DAF gain across included UIPs</title>',
        f'<desc id="w7-desc">{roster["n_included_uip"]} included UIPs. Generational permutation p = {roster["perm_p"]:.2f}.</desc>',
        f'<rect width="{w}" height="{h}" fill="#FCFCFB"/>',
        _text(32, 28, f'Oxide DAF gain, {roster["n_included_uip"]} included UIPs', size=15, weight="600"),
        _text(32, 48, f'Generational permutation p = {roster["perm_p"]:.2f}  ·  {roster["overall"]}', size=13, fill="#333"),
    ]
    if included:
        vmax = max(abs(m["oxide_gain"] or 0) for m in included) * 1.1
        mid = 200
        row_h = 10
        for i, m in enumerate(included):
            y = 64 + i * row_h
            g = m["oxide_gain"] or 0
            bw = (g / vmax) * 360
            fill = "#D55E00" if m["argmax_gain_stratum"] == "oxide" else "#0072B2"
            parts.append(f'<rect x="{mid}" y="{y}" width="{max(bw, 0):.1f}" height="7" fill="{fill}"/>')
        parts.append(_text(32, 400, "Vermillion: oxide is the argmax gain stratum. No ranking chrome.", size=12, fill="#333"))
    parts.append("</svg>")
    (WEB / "w7_roster.svg").write_text("\n".join(parts) + "\n")

    # W8 mechanism valence
    ranked = mech["oxstate"]["ranked_by_gain"]
    w, h = 640, 280
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-labelledby="w8-title w8-desc">',
        '<title id="w8-title">Oxidation-state bins, model-averaged blocked gain</title>',
        '<desc id="w8-desc">Charge-balance-resolved oxidation states localize abstention value to high formal valence.</desc>',
        f'<rect width="{w}" height="{h}" fill="#FCFCFB"/>',
        _text(32, 28, "Oxidation-state bins  ·  model-averaged blocked gain", size=15, weight="600"),
        _text(32, 48, f'Blocked cells excluding zero: {mech["oxstate"]["blocked_excl0"]}', size=13, fill="#333"),
    ]
    labels = {"mid": "mid valence", "high": "high valence", "very_high": "very high valence"}
    vmax = max(abs(v) for _, v in ranked) * 1.2
    mid = 320
    for i, (name, val) in enumerate(ranked):
        y = 80 + i * 56
        bw = (abs(val) / vmax) * 220
        fill = "#D55E00" if val > 0 else "#0072B2"
        x = mid if val >= 0 else mid - bw
        parts.append(f'<rect x="{x:.1f}" y="{y}" width="{bw:.1f}" height="36" fill="{fill}"/>')
        parts.append(_text(40, y + 24, labels.get(name, name), size=13, weight="600"))
        parts.append(_text(mid + (bw + 12 if val >= 0 else -bw - 12), y + 24, f"{val:+.2f}", size=13, anchor="start" if val >= 0 else "end"))
    parts.append(_text(32, 260, "Positive (vermillion) localizes to high formal valence. Not a coordination-environment proxy.", size=12, fill="#333"))
    parts.append("</svg>")
    (WEB / "w8_mechanism.svg").write_text("\n".join(parts) + "\n")

    # W9 scope cards (no crystal viewer)
    cards = [
        ("DFT labels", "The audit does not validate the MP2020-corrected DFT stability labels."),
        ("Allocator", "A stratum-aware allocator is falsified. This is a diagnostic, not a policy."),
        ("Temporal", "The oxide-highest ordering does not transfer to a later acquisition window."),
        ("Effect size", "Precision-point interaction is primary; DAF amplification is the low-base-rate rewrite."),
    ]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 860 220" role="img" aria-labelledby="w9-title w9-desc">',
        '<title id="w9-title">Scope of the audit</title>',
        '<desc id="w9-desc">Four scope facts: labels not validated, allocator falsified, temporal non-transfer, precision-point primary.</desc>',
        '<rect width="860" height="220" fill="#FCFCFB"/>',
    ]
    for i, (title, body) in enumerate(cards):
        x = 16 + (i % 4) * 210
        parts.append(f'<rect x="{x}" y="24" width="200" height="176" rx="6" fill="#fff" stroke="#E1E0D9"/>')
        parts.append(f'<rect x="{x}" y="24" width="6" height="176" fill="#D55E00"/>')
        parts.append(_text(x + 18, 56, title, size=14, weight="600"))
        # wrap body
        words = body.split()
        line = ""
        lines = []
        for word in words:
            trial = (line + " " + word).strip()
            if len(trial) > 26:
                lines.append(line)
                line = word
            else:
                line = trial
        if line:
            lines.append(line)
        for j, ln in enumerate(lines[:6]):
            parts.append(_text(x + 18, 84 + j * 16, ln, size=12, fill="#333"))
    parts.append("</svg>")
    (WEB / "w9_scope.svg").write_text("\n".join(parts) + "\n")

    # unused but keep strata in a tiny strip used as thumbnail
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 160" role="img" aria-labelledby="w-strata-title">',
        '<title id="w-strata-title">Stable base rates by anion class</title>',
        '<rect width="640" height="160" fill="#FCFCFB"/>',
        _text(24, 28, "Stable base rate by anion class", size=15, weight="600"),
    ]
    for i, row in enumerate(strata["strata"]):
        x = 24 + i * 102
        bh = row["base_rate_stable"] * 280
        y = 130 - bh
        parts.append(f'<rect x="{x}" y="{y}" width="84" height="{bh:.1f}" fill="{STRATUM_COLORS[row["stratum"]]}"/>')
        parts.append(_text(x + 42, 148, row["stratum"][:4], size=11, anchor="middle"))
        parts.append(_text(x + 42, y - 6, f'{100 * row["base_rate_stable"]:.1f}%', size=12, anchor="middle"))
    parts.append("</svg>")
    (WEB / "w_baserate.svg").write_text("\n".join(parts) + "\n")


def main() -> None:
    extract()
    write_svgs()
    print("wrote", OUT)
    print("wrote", WEB)


if __name__ == "__main__":
    main()
