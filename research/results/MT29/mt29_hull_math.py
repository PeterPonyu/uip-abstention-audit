#!/usr/bin/env python
"""MT29 — Arm 2a (NEXT-EXPERIMENTS.md item 2): pure convex-hull-recompute math.

Independent of pymatgen/matbench-discovery (numpy + scipy only, both already hard deps
— see requirements.txt), so it is directly unit-testable on hand-checkable toy systems
without network access or the ~1-2 GB MP reference-entry download the real recompute
needs (tests/test_hull_math.py exercises exactly this module).

Construction (mathematically equivalent to what pymatgen's PhaseDiagram does under the
hood for a FIXED chemical system): a chemical system with k elements has compositions
living on the (k-1)-simplex (fractions sum to 1, so one coordinate is dependent). Lift
each reference entry (composition fractions, energy per atom) to a point in R^k by
keeping k-1 composition coordinates + 1 energy coordinate, take the convex hull of that
point set, and keep only the LOWER envelope (facets whose outward normal points in the
-energy direction — the boundary you would see looking up from below, i.e. the
thermodynamically stable boundary since lower energy = more stable). The hull energy at
an arbitrary query composition is the minimum energy achievable by mixing lower-hull
reference entries at that composition — solved directly as a small linear program
(equivalent to, but simpler to implement than, explicit lower-hull facet search), which
also handles compositions that fall on a hull vertex/edge cleanly.

Used by mt29_hull_recompute_validation.py to recompute e_above_hull_pred per model on a
stratified WBM validation subset, instead of the fixed-hull shortcut
`hull_pred = hull_true + (e_form_pred - e_form_true)` used everywhere else in MT29
(see the fixed-hull limitation in README.md).
"""
from __future__ import annotations

import re
from typing import Iterable, Sequence

import numpy as np
from scipy.optimize import linprog
from scipy.spatial import ConvexHull
from scipy.spatial import QhullError

TOKEN_RE = re.compile(r'([A-Z][a-z]?)(\d*)')

__all__ = [
    'formula_to_symbols', 'composition_fractions', 'lower_hull_mask',
    'hull_energy_at', 'e_above_hull',
]


def formula_to_symbols(formula: str) -> list:
    """'Fe3Al' -> ['Fe','Fe','Fe','Al']; 'NaCl' -> ['Na','Cl']. Multi-digit counts
    supported ('O12' -> twelve 'O'). Hand-checkable: formula_to_symbols('Fe3Al') has
    length 4 (3 Fe + 1 Al)."""
    symbols = []
    for m in TOKEN_RE.finditer(str(formula)):
        el, cnt = m.group(1), m.group(2)
        if not el:
            continue
        symbols.extend([el] * (int(cnt) if cnt else 1))
    return symbols


def composition_fractions(symbols: Sequence[str], elements: Sequence[str]) -> np.ndarray:
    """symbols: atom multiset of a structure/formula (e.g. ['Na','Cl']). elements:
    ordered list of element symbols spanning the chemical system (superset of the
    symbols actually present). Returns an array of fractions (sums to 1), aligned to
    `elements`, zero for elements absent from `symbols`."""
    n = len(symbols)
    if n == 0:
        raise ValueError('empty composition')
    counts = {e: 0 for e in elements}
    for s in symbols:
        if s not in counts:
            raise ValueError(f'element {s!r} not in system {list(elements)}')
        counts[s] += 1
    return np.array([counts[e] / n for e in elements], dtype=float)


def lower_hull_mask(comp_fracs: np.ndarray, energies: np.ndarray, tol: float = 1e-8) -> np.ndarray:
    """comp_fracs: (n, k) fractions, each row summing to 1. energies: (n,) per-atom
    energies. Returns a boolean mask of which reference rows lie ON the lower convex
    hull (the candidate thermodynamically-stable phases for this system)."""
    comp_fracs = np.asarray(comp_fracs, dtype=float)
    energies = np.asarray(energies, dtype=float)
    n, k = comp_fracs.shape
    if k == 1:
        # unary system: the hull is just the minimum-energy entry/entries.
        return energies <= energies.min() + tol
    # drop the last (linearly dependent) composition coordinate -> point in R^k
    pts = np.column_stack([comp_fracs[:, :-1], energies])
    if n <= pts.shape[1]:
        # not enough points to define a hull in this dimension; every point is
        # (trivially) on its own lower boundary.
        return energies <= energies.min() + tol
    try:
        hull = ConvexHull(pts, qhull_options='QJ')
    except QhullError:
        return energies <= energies.min() + tol
    lower_vertices = set()
    for eq, simplex in zip(hull.equations, hull.simplices):
        # eq = [n_1, ..., n_k, offset]; the energy axis is the LAST composition
        # coordinate we kept, i.e. index k-1 -> eq[-2]. A facet faces "down" in
        # energy (is on the stable lower envelope) iff its outward normal has a
        # negative energy component.
        if eq[-2] < -tol:
            lower_vertices.update(int(v) for v in simplex)
    if not lower_vertices:
        return energies <= energies.min() + tol
    mask = np.zeros(n, dtype=bool)
    mask[list(lower_vertices)] = True
    return mask


def hull_energy_at(query_comp: np.ndarray, comp_fracs: np.ndarray, energies: np.ndarray,
                    tol: float = 1e-8) -> float:
    """Lowest energy achievable at `query_comp` by mixing lower-hull reference
    entries (comp_fracs/energies) — the recomputed hull energy at that composition.
    query_comp: (k,) fractions summing to 1, SAME element ordering as comp_fracs.
    Solved as a linear program: minimize sum(w_i * E_i) subject to sum(w_i * comp_i)
    == query_comp, sum(w_i) == 1, w_i >= 0, over the lower-hull reference entries only
    — equivalent to interpolating within whichever lower-hull simplex contains
    query_comp, without needing to explicitly search for that simplex."""
    comp_fracs = np.asarray(comp_fracs, dtype=float)
    energies = np.asarray(energies, dtype=float)
    query_comp = np.asarray(query_comp, dtype=float)
    mask = lower_hull_mask(comp_fracs, energies, tol=tol)
    hull_comps = comp_fracs[mask]
    hull_energies = energies[mask]
    n_hull = len(hull_energies)
    if n_hull == 1:
        if not np.allclose(hull_comps[0], query_comp, atol=1e-6):
            raise RuntimeError(
                f'single-entry hull composition {hull_comps[0]} cannot span query {query_comp}')
        return float(hull_energies[0])
    A_eq = np.vstack([hull_comps.T, np.ones(n_hull)])
    b_eq = np.concatenate([query_comp, [1.0]])
    res = linprog(c=hull_energies, A_eq=A_eq, b_eq=b_eq, bounds=(0, 1), method='highs')
    if not res.success:
        raise RuntimeError(
            f'hull interpolation infeasible for composition {query_comp}: {res.message}')
    return float(res.fun)


def e_above_hull(query_comp: np.ndarray, query_energy: float,
                  comp_fracs: np.ndarray, energies: np.ndarray, tol: float = 1e-8) -> float:
    """Recomputed e_above_hull for a query entry: query_energy - hull_energy_at(comp).
    Negative/zero => on/below hull (predicted stable); positive => above hull
    (predicted unstable). This is the direct replacement for the fixed-hull shortcut
    `hull_pred = hull_true + (e_form_pred - e_form_true)`."""
    he = hull_energy_at(query_comp, comp_fracs, energies, tol=tol)
    return float(query_energy) - he
