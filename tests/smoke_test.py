#!/usr/bin/env python3
"""Fast (<2 min, no external data) smoke test for the MT29 reproducibility package.

Checks three things without touching the multi-GB external prediction CSVs:

  1. Core dependencies import (numpy, pandas, scikit-learn, scipy, matplotlib) and
     the local `relmetrics` sibling package is importable.
  2. The canonical analysis module (mt29_stage1_chem_yield) imports data-free and
     its core pure-Python helpers run correctly on a tiny in-memory fixture; the
     BH-FDR / Holm multiplicity routines run on toy p-values.
  3. The frozen headline result JSONs parse and contain the expected top-level keys.

Exit code 0 = pass, non-zero = fail. Run via ../smoke_test.sh.
"""
import os
import sys
import json

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MT29 = os.path.join(REPO, 'research', 'results', 'MT29')
# Hermetic: load `relmetrics` from the repo-contained vendor copy (see
# relmetrics/VENDORED_FROM.md). The upstream sibling checkout at
# `../reliability-commons` is intentionally NOT consulted -- the public
# release must not depend on a sibling repository being present.
sys.path.insert(0, REPO)
sys.path.insert(0, MT29)

failures = []


def check(name, fn):
    try:
        fn()
        print(f"  PASS  {name}")
    except Exception as e:  # noqa: BLE001 - smoke test reports any failure
        failures.append((name, repr(e)))
        print(f"  FAIL  {name}: {e!r}")


# ---------------------------------------------------------------------------
# 1. Core dependency imports
# ---------------------------------------------------------------------------
print("[1] dependency imports")


def _imports():
    import numpy  # noqa: F401
    import pandas  # noqa: F401
    import sklearn  # noqa: F401
    import scipy  # noqa: F401
    import matplotlib  # noqa: F401


def _relmetrics():
    import relmetrics
    from relmetrics.multiplicity import benjamini_hochberg, holm_bonferroni  # noqa: F401
    from relmetrics.provenance import stamp_result  # noqa: F401
    # Hermetic guard: the package MUST resolve from inside this repo (the
    # vendored copy under <repo>/relmetrics/), NOT from a sibling checkout or
    # an editable pip install. This is the public-release hermeticity contract
    # -- if this fails, the release is silently broken.
    assert relmetrics.__file__ is not None
    real = os.path.realpath(relmetrics.__file__)
    assert real.startswith(REPO + os.sep), (
        f"relmetrics resolved from outside the repo: {real!r} "
        f"(expected under {REPO!r}); the public release must not depend on a "
        f"sibling checkout or editable pip install."
    )
    # Vendored copy must carry the +mt29vendored version stamp.
    assert "mt29vendored" in relmetrics.__version__, relmetrics.__version__


check("core scientific stack imports", _imports)
check("relmetrics (local sibling) imports", _relmetrics)


# ---------------------------------------------------------------------------
# 2. Analysis module imports data-free; helpers run on a tiny fixture
# ---------------------------------------------------------------------------
print("[2] analysis code runs on a tiny slice")


def _import_analysis():
    import mt29_stage1_chem_yield as s
    assert s.MODELS == ['chgnet', 'm3gnet', 'mace', 'orb']
    assert s.SEED == 20260621


def _anion_family():
    import mt29_stage1_chem_yield as s
    cases = {'NaCl': 'halide', 'SiO2': 'oxide', 'Fe3Al': 'intermetallic'}
    for formula, expected in cases.items():
        got = s.anion_family(formula)
        assert got == expected, f"anion_family({formula!r})={got!r} != {expected!r}"


def _ci_helpers():
    import numpy as np
    import mt29_stage1_chem_yield as s
    ci = s.ci95(np.arange(1, 101))
    assert ci[0] < ci[1], ci
    assert s.excl0([0.77, 1.04]) is True
    assert s.excl0([-0.1, 0.2]) is False


def _abstention_metric():
    import numpy as np
    import mt29_stage1_chem_yield as s
    # tiny fixture: 6 rows, confidence perfectly ranks true-stable to the top
    conf = np.array([0.9, 0.8, 0.7, 0.3, 0.2, 0.1])
    sp = np.array([True, True, True, True, True, True])   # all called stable
    st = np.array([True, True, True, False, False, False])  # top-3 truly stable
    prec, daf, n = s.precision_daf_cov(conf, sp, st, st.mean(), 0.5)
    assert 0.0 <= prec <= 1.0 and n >= 1, (prec, daf, n)


def _multiplicity():
    from relmetrics.multiplicity import benjamini_hochberg, holm_bonferroni
    pvals = [0.001, 0.02, 0.5, 0.9]
    bh = benjamini_hochberg(pvals)
    holm = holm_bonferroni(pvals)
    for res in (bh, holm):
        assert 'adjusted_p' in res and 'reject' in res
        assert len(res['adjusted_p']) == len(pvals)
    assert bool(bh['reject'][0]) is True  # smallest p should survive


check("mt29_stage1_chem_yield imports data-free", _import_analysis)
check("anion_family classifier", _anion_family)
check("ci95 / excl0 helpers", _ci_helpers)
check("precision_daf_cov abstention metric", _abstention_metric)
check("relmetrics BH-FDR / Holm multiplicity", _multiplicity)


# ---------------------------------------------------------------------------
# 3. Frozen result JSONs parse with expected top-level keys
# ---------------------------------------------------------------------------
print("[3] frozen result JSONs parse with expected keys")

EXPECTED = {
    'mt29_stage1_matched_yield_result.json':
        ['meta', 'interactions_matched_yield', 'summary'],
    'mt29_stage2_robustness_result.json':
        ['meta', 'gate1_loeo', 'gate2_rounds', 'summary'],
    'mt29_stage1_chem_yield_result.json':
        ['meta', 'stratified_curves', 'interactions', 'summary', 'gate'],
}


def _make_json_check(fname, keys):
    def _fn():
        path = os.path.join(MT29, fname)
        assert os.path.exists(path), f"missing {path}"
        with open(path) as fh:
            d = json.load(fh)
        for k in keys:
            assert k in d, f"{fname} missing top-level key {k!r}"
    return _fn


for fname, keys in EXPECTED.items():
    check(f"{fname} parses + keys {keys}", _make_json_check(fname, keys))


# ---------------------------------------------------------------------------
print()
if failures:
    print(f"SMOKE TEST FAILED: {len(failures)} check(s) failed")
    for name, err in failures:
        print(f"  - {name}: {err}")
    sys.exit(1)
print("SMOKE TEST PASSED")
sys.exit(0)
