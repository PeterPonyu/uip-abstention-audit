#!/usr/bin/env python
"""MT29 alt-stratification — multiplicity correction + preregistered SUCCESS/KILL verdict.

Loads the two per-stratifier result JSONs written by mt29_stage1_altstrat.py and applies the
PREREG-altstrat-2026-07-02.md multiplicity plan:

  PRIMARY (gating):  Holm-Bonferroni WITHIN each stratifier family (alpha=0.05, m = that family's
                     cell count), on the hires (N_BOOT=10000) two-sided bootstrap p-values.
  SECONDARY (reported, non-gating): Benjamini-Hochberg FDR (q=0.05) ACROSS the pooled two families
                     (m = sum of both families' cells).

Per-stratifier verdict (prereg):
  SUCCESS      : >=1 cell with CI entirely above 0 (anion-consistent direction) AND surviving Holm
                 within-stratifier, AND shuffle-null clean (<=5% shuffle cells CI-exclude-0).
  KILL         : 0 cells with CI entirely above 0 in the correct direction.
  UNINFORMATIVE: cells fire in the correct direction but none survive Holm, OR shuffle dirty,
                 OR < 1 usable cell.

Shuffle-null families get the identical Holm+BH treatment (expected: 0 rejections).
CPU only, reads on-disk result JSONs; no re-run of the bootstrap.
Usage: python3 mt29_altstrat_multiplicity.py
"""
import os, sys, json, platform
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, '/home/zeyufu/Desktop/ml-reliability-research/reliability-commons')

from mt29_stage1_chem_yield import SEED, OUT_DIR, sha256
from relmetrics.multiplicity import benjamini_hochberg, holm_bonferroni
from relmetrics.provenance import stamp_result

STRATIFIERS = ['electronegativity_q5', 'metal_fraction']
RESULT = {s: os.path.join(OUT_DIR, f'mt29_stage1_altstrat_{s}_result.json') for s in STRATIFIERS}
OUT_JSON = os.path.join(OUT_DIR, 'mt29_altstrat_multiplicity_result.json')
MANIFEST = os.path.join(OUT_DIR, 'mt29_altstrat_multiplicity_manifest.json')


def holm_within(cells):
    """Holm-Bonferroni within a family on hires p-values; annotates cells in place, returns m."""
    p = [c['p_raw_hires'] for c in cells]
    if not p:
        return 0
    holm = holm_bonferroni(p, alpha=0.05)
    for c, ph, rh in zip(cells, holm['adjusted_p'], holm['reject']):
        c['p_holm_adjusted'] = round(float(ph), 8)
        c['reject_holm_a05'] = bool(rh)
    return len(cells)


def main():
    # verify both per-stratifier results exist
    for s in STRATIFIERS:
        if not os.path.exists(RESULT[s]):
            raise SystemExit(f'missing {RESULT[s]} — run mt29_stage1_altstrat.py --stratifier {s} first')

    loaded = {s: json.load(open(RESULT[s])) for s in STRATIFIERS}
    out = {'meta': {
        'story': 'G007-mt29-altstrat-multiplicity',
        'prereg': 'research/results/MT29/PREREG-altstrat-2026-07-02.md',
        'seed': SEED,
        'multiplicity_plan': 'PRIMARY Holm-Bonferroni within each stratifier family (alpha=0.05, '
                             'hires p); SECONDARY BH-FDR (q=0.05) pooled across both families.',
        'direction_rule': 'a cell counts toward SUCCESS only if CI entirely above 0 (anion-'
                          'consistent: more-oxide-like stratum higher matched-yield abstention gain).',
        'stratifiers': STRATIFIERS,
        'source_results': {s: os.path.basename(RESULT[s]) for s in STRATIFIERS},
    }}

    per_strat = {}
    pooled_real = []           # for BH across families
    pooled_real_owner = []     # parallel list of stratifier names
    for s in STRATIFIERS:
        cells = loaded[s]['cells']
        shuf = loaded[s]['cells_SHUFFLE']
        m_real = holm_within(cells)
        m_shuf = holm_within(shuf)

        n_above0 = sum(c['ci_above_0'] for c in cells)
        # correct-direction Holm survivors: Holm reject AND CI above 0
        holm_dir = [c for c in cells if c.get('reject_holm_a05') and c['ci_above_0']]
        n_holm_dir = len(holm_dir)
        n_shuf_excl0 = sum(c['excludes_0'] for c in shuf)
        shuffle_clean = n_shuf_excl0 <= max(1, int(0.05 * max(1, len(shuf))))

        if n_above0 == 0:
            verdict = 'KILL'
        elif n_holm_dir >= 1 and shuffle_clean:
            verdict = 'SUCCESS'
        else:
            verdict = 'UNINFORMATIVE'

        top = sorted(holm_dir, key=lambda z: -abs(z['interaction_med']))[:8]
        per_strat[s] = {
            'stratifier_definition': loaded[s]['meta']['stratifier_definition'],
            'strata_used': loaded[s]['meta']['strata_used'],
            'strata_sizes': loaded[s]['meta']['strata_sizes'],
            'n_cells': m_real,
            'n_ci_above0_correct_direction': n_above0,
            'n_holm_reject_a05': int(sum(c.get('reject_holm_a05', False) for c in cells)),
            'n_holm_reject_correct_direction': n_holm_dir,
            'shuffle_n_cells': m_shuf,
            'shuffle_ci_excl0': n_shuf_excl0,
            'shuffle_holm_reject_a05': int(sum(c.get('reject_holm_a05', False) for c in shuf)),
            'shuffle_null_clean': bool(shuffle_clean),
            'verdict': verdict,
            'top_correct_direction_holm_cells': [
                {'model': c['model'], 'stratumA': c['stratumA'], 'stratumB': c['stratumB'],
                 'interaction_med': c['interaction_med'], 'interaction_ci95': c['interaction_ci95'],
                 'p_raw_hires': c['p_raw_hires'], 'p_holm_adjusted': c['p_holm_adjusted']}
                for c in top],
        }
        for c in cells:
            pooled_real.append(c['p_raw_hires'])
            pooled_real_owner.append((s, c['model'], c['stratumA'], c['stratumB'], c['ci_above_0']))

    # SECONDARY: BH-FDR across the pooled two families
    bh = benjamini_hochberg(pooled_real, alpha=0.05)
    bh_reject = bh['reject']
    bh_adj = bh['adjusted_p']
    pooled_records = []
    for (owner, ph, rj, adj) in zip(pooled_real_owner, pooled_real, bh_reject, bh_adj):
        s, model, a, b, above0 = owner
        pooled_records.append({'stratifier': s, 'model': model, 'stratumA': a, 'stratumB': b,
                               'ci_above_0': above0, 'p_raw_hires': ph,
                               'p_bh_adjusted': round(float(adj), 8), 'reject_bh_q05': bool(rj)})
    n_bh_dir = sum(r['reject_bh_q05'] and r['ci_above_0'] for r in pooled_records)

    out['per_stratifier'] = per_strat
    out['bh_across_families'] = {
        'm_pooled_cells': len(pooled_real),
        'n_reject_bh_q05': int(bh_reject.sum()),
        'n_reject_bh_q05_correct_direction': int(n_bh_dir),
        'per_cell': pooled_records,
    }
    verdicts = {s: per_strat[s]['verdict'] for s in STRATIFIERS}
    n_success = sum(v == 'SUCCESS' for v in verdicts.values())
    overall = ('BOTH_ROBUST' if n_success == 2 else
               'PARTIAL' if n_success == 1 else
               'ANION_SPECIFIC')
    out['summary'] = {
        'per_stratifier_verdict': verdicts,
        'n_stratifiers_success': n_success,
        'overall': overall,
        'bh_across_families_correct_direction': f"{n_bh_dir}/{len(pooled_real)}",
    }

    print('=== ALT-STRATIFICATION MULTIPLICITY / VERDICT ===', flush=True)
    for s in STRATIFIERS:
        d = per_strat[s]
        print(f"\n[{s}] strata={d['strata_used']}  cells={d['n_cells']}", flush=True)
        print(f"  CI-above-0 (correct dir): {d['n_ci_above0_correct_direction']}  "
              f"Holm-reject(correct dir): {d['n_holm_reject_correct_direction']}  "
              f"shuffle CI-excl0: {d['shuffle_ci_excl0']}/{d['shuffle_n_cells']} clean={d['shuffle_null_clean']}",
              flush=True)
        print(f"  VERDICT: {d['verdict']}", flush=True)
        for c in d['top_correct_direction_holm_cells'][:5]:
            print(f"    {c['model']:7s} {c['stratumA']:4s} vs {c['stratumB']:4s}: "
                  f"int={c['interaction_med']:+.4f} CI{c['interaction_ci95']} "
                  f"p_holm={c['p_holm_adjusted']:.2e}", flush=True)
    print(f"\nBH-FDR across families (correct dir): {n_bh_dir}/{len(pooled_real)}", flush=True)
    print(f"OVERALL: {overall}  ({verdicts})", flush=True)

    stamp_result(out, __file__, seeds=[SEED])
    if os.path.exists(OUT_JSON):
        raise SystemExit(f'REFUSING to overwrite existing {OUT_JSON}')
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nWrote {OUT_JSON}", flush=True)

    manifest = {
        'cmd': ' '.join([sys.executable] + sys.argv),
        'script_sha256': sha256(os.path.abspath(__file__)),
        'git_head': out['provenance'].get('git_sha'),
        'seed': SEED,
        'inputs': {os.path.basename(RESULT[s]): sha256(RESULT[s]) for s in STRATIFIERS},
        'output_sha256': sha256(OUT_JSON),
        'versions': {'python': platform.python_version(), 'numpy': np.__version__},
        'platform': platform.platform(),
    }
    with open(MANIFEST, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote {MANIFEST}", flush=True)


if __name__ == '__main__':
    main()
