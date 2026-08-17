---
layout: base.njk
permalink: /
---

<p class="status-chip">{{ site.status }}</p>

<h1>{{ site.title }}</h1>
<p class="byline">{{ site.author }}. <a href="{{ site.orcid }}">ORCID 0009-0001-8329-0108</a>. {{ site.affiliation }}.</p>

<p>Universal machine-learning interatomic potentials (UIPs) surface false stability candidates most in oxide chemistries: against the MP2020-corrected density-functional-theory (DFT) labels used in Matbench Discovery, oxides have the lowest stable base rate (12.4%) of any anion class while UIPs call them stable at six times that rate. The audit does not validate DFT labels. Scoping: the oxide-highest ordering does not transfer temporally, a stratum-aware allocator is falsified, and within oxides the benefit does not localize to correction-sensitive cation classes.</p>

<section class="routes" aria-label="Three scientific routes">
  <p class="route-links">
    Routes:
    <a href="{{ '/potentials/' | url }}">potentials</a> ·
    <a href="{{ '/error/' | url }}">error</a> ·
    <a href="{{ '/mechanism/' | url }}">mechanism</a>.
  </p>
  <article class="route">
    <h2>Potentials</h2>
    <p>Four canonical UIPs (CHGNet, M3GNet, MACE, ORB) and a 32-UIP roster. The oxide-highest DAF interaction is not a single-model quirk.</p>
    <p>Across six anion-class strata the prototype-blocked interaction excludes zero in 45 of 60 cells.</p>
    <img src="{{ '/assets/web/w2_daf.svg' | url }}" alt="CHGNet matched-yield DAF gain is largest in oxides.">
  </article>
  <article class="route">
    <h2>Error</h2>
    <p>This is a decision mismatch, not an RMSE ranking. Under every tail-robust estimator oxides are not the highest formation-energy-error stratum.</p>
    <p>The raw RMSE gap is 99.7% due to one implausible published prediction.</p>
    <img src="{{ '/assets/web/w4_error.svg' | url }}" alt="Oxide over rest error ratio exceeds one only for raw RMSE.">
  </article>
  <article class="route">
    <h2>Mechanism</h2>
    <p>Oxide reference energetics, including missing Hubbard-U treatment, and fitting difficulty co-locate with the abstention signal.</p>
    <p>Charge-balance-resolved oxidation states localize the benefit to high formal valence. It is not reducible to MP2020 corrections.</p>
    <img src="{{ '/assets/web/w8_mechanism.svg' | url }}" alt="Model-averaged blocked gain is largest in the very-high valence bin.">
  </article>
</section>

{% include "scope-strip.njk" %}

<section class="protocol-strip" aria-label="Protocol">
  <h2>Protocol</h2>
  <ol class="protocol-steps">
    <li>Records</li>
    <li>SELECT (<em>Y</em> matched)</li>
    <li>Stage 1</li>
    <li>Stage 2</li>
    <li>Verdict</li>
  </ol>
  <p><em>n</em> = {{ site.nJoined }} WBM structures after inner join. CPU-only; no model is trained; no DFT is run. Confidence is the absolute predicted hull margin. <a href="{{ '/protocol/' | url }}">Matched-yield protocol</a>.</p>
</section>

{% include "cite-box.njk" %}
