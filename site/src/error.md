---
layout: base.njk
title: Error
permalink: /error/
---

# Decision error versus residual error

Oxides have the lowest stable base rate (12.4%). UIPs call them stable at six times that rate. That is a decision mismatch against the MP2020-corrected labels. It is not an error-magnitude ranking.

<figure class="figure">
  <img src="{{ '/assets/web/w4_error.svg' | url }}" alt="Four bars comparing oxide to non-oxide error; only raw RMSE ranks oxide highest.">
  <figcaption>Oxide divided by mean non-oxide formation-energy error. Vermillion marks the one estimator for which oxide is highest (raw RMSE). Tail-robust estimators do not.</figcaption>
</figure>

<figure class="figure">
  <img src="{{ '/assets/web/w_baserate.svg' | url }}" alt="Stable base rates by anion class; oxide is the lowest at 12.4 percent.">
  <figcaption>Stable base rate by anion class. Oxide is 12.4%; halide is 27.8%. DAF divides precision by this denominator, which is why the +0.90 headline is an amplification of a +7.7 precision-point contrast.</figcaption>
</figure>

The raw RMSE gap suggesting otherwise is 99.7% due to one implausible published prediction. Dropping that row collapses the RMSE contrast; the abstention interaction does not travel with it.

<p><a href="{{ '/potentials/' | url }}">Potentials</a> · <a href="{{ '/mechanism/' | url }}">Mechanism</a></p>
