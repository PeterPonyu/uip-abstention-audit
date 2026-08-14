---
layout: base.njk
title: Reproduce
permalink: /reproduce/
---

# Reproduce

The audit is CPU-only. No model is trained and no DFT is run. Inputs are the public Matbench Discovery prediction and summary tables. Frozen analysis records live on Zenodo.

## What to obtain

1. The public code archive for this audit.
2. The software version DOI and the manuscript Data-availability DOI (labeled separately on <a href="{{ '/cite/' | url }}">Cite</a>).
3. The listed prediction and WBM summary files from the upstream Matbench Discovery distribution. Checksums travel with the public archive.

## What is checked

The public archive includes a CPU-only check that the frozen analysis records are present and that the loader joins the four canonical UIPs to the WBM labels. It does not download Matbench at runtime from this site.

## What this site does not do

No live download. Numbers on these pages come from slim extracts of the frozen records. If a key is missing, the page would say “not in frozen record” rather than impute.

<p><a href="{{ '/cite/' | url }}">Cite</a> · <a href="{{ site.codeUrl }}">Public code</a></p>
