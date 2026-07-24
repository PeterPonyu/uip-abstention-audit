#!/usr/bin/env Rscript
# ==========================================================================
# F2_interaction_heatmap.R -- paper Fig. 2: the stratum x coverage
# interaction (median gain_A - gain_B) for every (model, stratum-pair) cell;
# cells outlined in black have a 95% bootstrap CI excluding zero (48/60).
#
# REGENERATE-ONLY-FROM-JSON RULE: reads EXCLUSIVELY the frozen result JSON
# below; never hardcode arrays, never hand-edit the JSON.
#
# Input : ../research/results/MT29/mt29_stage1_matched_yield_result.json
#         (interactions_matched_yield: model, stratumA, stratumB,
#          interaction_med, excludes_0)
# Output: figures/F2_interaction_heatmap.pdf and .png
# ==========================================================================

suppressPackageStartupMessages({
  library(jsonlite)
  library(ggplot2)
})

# Serif family (JCIM/ACS Times-like), set at theme + device + geom defaults so
# every embedded glyph (incl. the Unicode minus in pair labels and plotmath
# Delta) stays in one serif family with no sans/CJK fallback fonts.
ff <- "TeX Gyre Termes"
update_geom_defaults("text", list(family = ff))
update_geom_defaults("label", list(family = ff))

input_json <- "../../research/results/MT29/mt29_stage1_matched_yield_result.json"
out_stem <- "F2_interaction_heatmap"

if (!file.exists(input_json)) {
  stop(sprintf(
    "Result JSON not found: %s\nFigures regenerate ONLY from on-disk result JSONs; run the analysis first.",
    input_json
  ))
}

res <- fromJSON(input_json)
ints <- res$interactions_matched_yield # data.frame (60 rows)

model_labels <- c(chgnet = "CHGNet", m3gnet = "M3GNet", mace = "MACE", orb = "ORB")
stratum_labels <- c(
  oxide = "Oxide", intermetallic = "Interm.", chalcogenide = "Chalc.",
  halide = "Halide", pnictide = "Pnict.", other = "Other"
)

ints$model_lab <- factor(model_labels[ints$model], levels = unname(model_labels))
ints$pair <- paste0(
  stratum_labels[ints$stratumA], " − ", stratum_labels[ints$stratumB]
)

# Order pairs by their mean interaction across models (data-driven, from JSON)
pair_order <- names(sort(tapply(ints$interaction_med, ints$pair, mean)))
ints$pair <- factor(ints$pair, levels = pair_order)

n_excl <- sum(ints$excludes_0)
n_tot <- nrow(ints)
cat(sprintf("F2: %d/%d cells CI-exclude-0 (from JSON)\n", n_excl, n_tot))

fill_min <- min(ints$interaction_med)
fill_max <- max(ints$interaction_med)
label_cut <- 0.55 * max(abs(c(fill_min, fill_max)))
ints$label_colour <- ifelse(abs(ints$interaction_med) >= label_cut, "white", "black")
legend_breaks <- c(fill_min, 0, fill_max)

p <- ggplot(ints, aes(x = model_lab, y = pair, fill = interaction_med)) +
  geom_tile(colour = "white", linewidth = 0.2) +
  geom_tile(
    data = subset(ints, excludes_0),
    fill = NA, colour = "black", linewidth = 0.5
  ) +
  geom_text(
    aes(label = sprintf("%+.2f", interaction_med), colour = label_colour),
    size = 3.8, show.legend = FALSE
  ) +
  scale_colour_identity() +
  scale_fill_gradient2(
    low = "#2166AC", mid = "white", high = "#B2182B",
    midpoint = 0, limits = c(fill_min, fill_max), breaks = legend_breaks,
    labels = function(x) sprintf("%+.2f", x),
    name = expression(atop("interaction  ", Delta * "gain  (DAF)"))
  ) +
  labs(
    x = NULL, y = NULL,
    caption = "Black outline: i.i.d. 95% bootstrap CI excludes 0"
  ) +
  # coord_fixed removed: was forcing 15x4 cells into square aspect, crushing the heatmap (Fable audit 2026-07-20)
  theme_minimal(base_size = 12, base_family = ff) +
  theme(
    panel.grid = element_blank(),
    legend.position = "right",
    legend.title = element_text(size = 10),
    legend.text  = element_text(size = 9),
    plot.caption = element_text(size = 8.5, hjust = 0),
    axis.text.x  = element_text(size = 9, angle = 30, hjust = 1, vjust = 1, margin = margin(t = 6, r = 0, b = 0, l = 0)),
    axis.text.y  = element_text(size = 9)
  )

# Canvas sized so the included width (0.82\textwidth, ~5.33in) scales
# base_size=10 to ~8.5pt effective (typography audit 2026-07-16: the previous
# 7.2x5.6in canvas rendered at ~7.4pt effective, with smaller elements below
# the 7pt floor).
ggsave(paste0(out_stem, ".pdf"), p, width = 6.27, height = 4.0, device = cairo_pdf, family = ff)
ggsave(paste0(out_stem, ".png"), p, width = 6.27, height = 4.0, dpi = 300,
       device = ragg::agg_png)

cat(sprintf("Wrote %s.pdf and %s.png from %s\n", out_stem, out_stem, input_json))
