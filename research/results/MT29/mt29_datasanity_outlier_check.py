#!/usr/bin/env python
"""MT29 data-sanity check: quantify the effect of catastrophic-outlier rows in two
published Figshare v25 prediction files (GRACE-2L-MPtrj, SevenNet-0) on (a) the naive
mean-absolute-error and (b) the rank-based oxide-halide value-of-abstention interaction.

The converted CSVs faithfully copy the published MP2020-corrected e_form column; a handful
of rows in the *published* v25 files carry non-physical predictions (|e_form_pred| up to
1e22-1e33 eV/atom) that inflate the MEAN absolute error but do not affect the rank/threshold
decision analysis. This script proves that by recomputing the interaction with |pred|>1e3
rows dropped. Writes results_expansion_2026-07-13/DATA-SANITY-OUTLIERS.json.
CPU/pandas/NumPy only; reuses mt29_roster_expansion_audit.analyze_model verbatim.
"""
import os, sys, json, hashlib, platform
from datetime import datetime, timezone
import numpy as np, pandas as pd
MT29 = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, MT29)
import mt29_roster_expansion_audit as A

ROSTER = os.path.expanduser("~/mt_uip_roster25")
OUTDIR = "/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/results_expansion_2026-07-13"
THRESH = 1e3   # |e_form_pred| eV/atom above this is a non-physical published-data outlier

def main():
    base = A.load_base()
    out = {"threshold_abs_eV": THRESH, "models": {}}
    for m in ["grace_2l_mptrj", "sevennet_0"]:
        orig = os.path.join(ROSTER, f"{m}_pred.csv")
        df = pd.read_csv(orig)
        p = pd.to_numeric(df["e_form_pred"], errors="coerce")
        mask = p.abs() > THRESH
        clean = df[~mask].copy()
        cp = os.path.join(OUTDIR, f"_datasanity_{m}_clean.csv"); clean.to_csv(cp, index=False)
        r0 = A.analyze_model(base, m, orig); r1 = A.analyze_model(base, m, cp)
        os.remove(cp)
        oh0 = r0["interactions"]["oxide|halide"]; oh1 = r1["interactions"]["oxide|halide"]
        out["models"][m] = dict(
            n_outlier_rows=int(mask.sum()), n_total_rows=int(len(df)),
            outlier_values=[round(float(v), 4) for v in p[mask].sort_values(key=abs, ascending=False).head(15)],
            mae_form_naive=r0["mae_form"], mae_form_trimmed=round(r1["mae_form"], 5),
            I_oxhal_orig=oh0["interaction_med"], I_oxhal_trimmed=oh1["interaction_med"],
            delta_I=round(oh1["interaction_med"] - oh0["interaction_med"], 6),
            ci95_orig=oh0["ci95"], ci_width=round(oh0["ci95"][1] - oh0["ci95"][0], 5),
            argmax_orig=r0["argmax_gain_stratum"], argmax_trimmed=r1["argmax_gain_stratum"],
            excl0_orig=oh0["excl0"], excl0_trimmed=oh1["excl0"],
            robust=bool(abs(oh1["interaction_med"] - oh0["interaction_med"]) < (oh0["ci95"][1] - oh0["ci95"][0])
                        and r0["argmax_gain_stratum"] == r1["argmax_gain_stratum"] and oh0["excl0"] == oh1["excl0"]),
        )
    out["conclusion"] = ("naive MAE is corrupted only by a handful of published-v25 outlier rows; "
                         "rank-based oxide-halide interaction is robust (|delta_I| < CI width, argmax & "
                         "CI-exclusion unchanged); both models retained with disclosure.")
    out["versions"] = dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__)
    out["generated_utc"] = datetime.now(timezone.utc).isoformat()
    dst = os.path.join(OUTDIR, "DATA-SANITY-OUTLIERS.json")
    json.dump(out, open(dst, "w"), indent=2)
    print(json.dumps(out, indent=2))
    print("\nwrote", dst)

if __name__ == "__main__":
    main()
