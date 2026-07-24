"""relmetrics (vendored): reliability-metric helpers used by this paper.

The :mod:`relmetrics.multiplicity` module provides BH-FDR and Holm-Bonferroni
helpers; :mod:`relmetrics.provenance` provides :func:`stamp_result` that
embeds git SHA / timestamp / seeds into result dicts.

Vendored from the sibling ``reliability-commons`` repository at the
``v0.2.0.dev0`` source revision (same author, MIT license -- see
``relmetrics/LICENSE`` and ``relmetrics/VENDORED_FROM.md``) so the public
release of this paper is hermetic: ``relmetrics`` resolves from the repo
root via :mod:`sys.path` insertion in ``tests/smoke_test.py`` and the
analysis scripts that need it; no ``pip install -e ../...`` step is
required. Only the two modules actually consumed by this paper's
analysis code are vendored (multiplicity, provenance); other modules in
upstream ``reliability-commons`` (``aurc``, ``bootstrap``, ``conformal``,
``nulls``) are NOT vendored and importing them will fail by design --
that is the boundary of the hermetic surface area for this paper.
"""
from relmetrics import multiplicity, provenance  # noqa: F401

__version__ = "0.2.0.dev0+mt29vendored"

__all__ = [
    "multiplicity",
    "provenance",
    "__version__",
]