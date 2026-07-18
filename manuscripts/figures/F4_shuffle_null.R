#!/usr/bin/env Rscript
# ==========================================================================
# F4_shuffle_null.R -- paper Fig. 4: real vs within-stratum
# confidence-shuffled |interaction| per gate (Stage-1 / LOEO / WBM-round).
# The shuffle-null collapses to zero: 0/60, 0/700, 0/300 CI-excl-0.
#
# REGENERATE-ONLY-FROM-JSON RULE: reads EXCLUSIVELY the frozen result JSONs
# below; never hardcode arrays, never hand-edit the JSONs.
#
# Inputs: ../research/results/MT29/mt29_stage1_matched_yield_result.json
#         ../research/results/MT29/mt29_stage2_robustness_result.json
# Output: figures/F4_shuffle_null.pdf and .png
# ==========================================================================

suppressPackageStartupMessages({
  library(jsonlite)
  library(ggplot2)
})

# Serif family (JCIM/ACS Times-like), set at theme + device + geom defaults so
# every embedded glyph (incl. the em dash in the annotation and plotmath Delta)
# stays in one serif family with no sans/CJK fallback fonts.
ff <- "TeX Gyre Termes"
update_geom_defaults("text", list(family = ff))
update_geom_defaults("label", list(family = ff))

stage1_json <- "../research/results/MT29/mt29_stage1_matched_yield_result.json"
stage2_json <- "../research/results/MT29/mt29_stage2_robustness_result.json"
out_stem <- "figures/F4_shuffle_null"

for (f in c(stage1_json, stage2_json)) {
  if (!file.exists(f)) {
    stop(sprintf(
      "Result JSON not found: %s\nFigures regenerate ONLY from on-disk result JSONs; run the analysis first.",
      f
    ))
  }
}

myr <- fromJSON(stage1_json)
s2r <- fromJSON(stage2_json)

collect <- function(df, gate, kind) {
  data.frame(
    gate = gate, kind = kind,
    abs_med = abs(df$interaction_med),
    excludes_0 = df$excludes_0
  )
}

loeo_real <- do.call(rbind, lapply(s2r$gate1_loeo, `[[`, "interactions"))
loeo_shuf <- do.call(rbind, lapply(s2r$gate1_loeo, `[[`, "interactions_SHUFFLE"))
rnd_real <- do.call(rbind, lapply(s2r$gate2_rounds, `[[`, "interactions"))
rnd_shuf <- do.call(rbind, lapply(s2r$gate2_rounds, `[[`, "interactions_SHUFFLE"))

df <- rbind(
  collect(myr$interactions_matched_yield, "Stage-1", "Real"),
  collect(myr$interactions_matched_yield_SHUFFLE, "Stage-1", "Shuffle-null"),
  collect(loeo_real, "LOEO", "Real"),
  collect(loeo_shuf, "LOEO", "Shuffle-null"),
  collect(rnd_real, "WBM round", "Real"),
  collect(rnd_shuf, "WBM round", "Shuffle-null")
)

# Per-gate annotation counts (all read from the JSONs, none hand-typed)
ann <- do.call(rbind, lapply(split(df, df$gate), function(g) {
  r <- g[g$kind == "Real", ]
  s <- g[g$kind == "Shuffle-null", ]
  data.frame(
    gate = g$gate[1],
    label = sprintf(
      "CI-excl-0 — real: %d/%d\nshuffle: %d/%d",
      sum(r$excludes_0), nrow(r), sum(s$excludes_0), nrow(s)
    )
  )
}))

gate_levels <- c("Stage-1", "LOEO", "WBM round")
gate_labels <- c(
  `Stage-1` = sprintf("Stage-1 (%d cells)", sum(df$gate == "Stage-1" & df$kind == "Real")),
  LOEO = sprintf("LOEO (%d cells)", sum(df$gate == "LOEO" & df$kind == "Real")),
  `WBM round` = sprintf("WBM round (%d cells)", sum(df$gate == "WBM round" & df$kind == "Real"))
)
df$gate <- factor(df$gate, levels = gate_levels, labels = gate_labels[gate_levels])
ann$gate <- factor(gate_labels[as.character(ann$gate)], levels = gate_labels[gate_levels])

p <- ggplot(df, aes(x = abs_med, fill = kind)) +
  geom_histogram(aes(y = after_stat(density)), bins = 30, alpha = 0.75,
                 position = "identity", colour = "grey20", linewidth = 0.2) +
  geom_text(
    data = ann, aes(x = Inf, y = Inf, label = label),
    hjust = 1.05, vjust = 1.3, size = 3.0, inherit.aes = FALSE
  ) +
  facet_wrap(~gate, nrow = 1, scales = "free") +
  scale_fill_manual(values = c(Real = "#E69F00", `Shuffle-null` = "#56B4E9"), name = NULL) +
  labs(
    x = expression("|median interaction| (" * Delta * "DAF)"),
    y = "density"
  ) +
  theme_minimal(base_size = 10, base_family = ff) +
  theme(
    legend.position = "bottom",
    panel.grid.minor = element_blank(),
    strip.text = element_text(size = 9)
  )

# Canvas sized so the included width (0.82\textwidth, ~5.33in) scales
# base_size=10 to ~8.5pt effective (typography audit 2026-07-16: the previous
# 9.5x3.3in canvas rendered at ~5.6pt effective).
ggsave(paste0(out_stem, ".pdf"), p, width = 6.27, height = 2.18, device = cairo_pdf, family = ff)
ggsave(paste0(out_stem, ".png"), p, width = 6.27, height = 2.18, dpi = 300,
       device = ragg::agg_png)

cat(sprintf("Wrote %s.pdf and %s.png from %s and %s\n",
            out_stem, out_stem, stage1_json, stage2_json))
