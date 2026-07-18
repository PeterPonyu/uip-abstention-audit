#!/usr/bin/env Rscript
# ==========================================================================
# F5_committee_variance.R -- paper Fig. 5: committee-variance abstention vs
# the single-model |hull-margin| signal.
# (a) matched-yield DAF gain (median) per anion stratum, committee signal;
# (b) the 15 stratum-pair committee interactions (median, 95% bootstrap CI);
#     highlighted = committee CI excludes 0 (7/15); asterisk = the
#     single-model consensus also fired on that pair.
#
# REGENERATE-ONLY-FROM-JSON RULE: reads EXCLUSIVELY the frozen result JSON
# below; never hardcode arrays, never hand-edit the JSON.
#
# Input : ../research/results/MT29/mt29_committee_variance.json
# Output: figures/F5_committee_variance.pdf and .png
# ==========================================================================

suppressPackageStartupMessages({
  library(jsonlite)
  library(ggplot2)
  library(patchwork)
})

# Serif family (JCIM/ACS Times-like), set at theme + device + geom defaults so
# every embedded glyph (incl. the Unicode minus in pair labels and plotmath
# Delta/subscripts) stays in one serif family with no sans/CJK fallback fonts.
# Panel identity is carried by (a)/(b) tags (plain weight per the
# no-decorative-bold typography rule); interpretation lives in the caption,
# not in-plot titles. All in-figure TEXT is black; colour is reserved for the
# data marks (CI-excludes-0 points/bars).
ff <- "TeX Gyre Termes"
update_geom_defaults("text", list(family = ff, colour = "black"))
update_geom_defaults("label", list(family = ff, colour = "black"))

input_json <- "../research/results/MT29/mt29_committee_variance.json"
out_stem <- "figures/F5_committee_variance"

if (!file.exists(input_json)) {
  stop(sprintf(
    "Result JSON not found: %s\nFigures regenerate ONLY from on-disk result JSONs; run the analysis first.",
    input_json
  ))
}

res <- fromJSON(input_json)

strata <- c("oxide", "intermetallic", "chalcogenide", "halide", "pnictide", "other")
stratum_labels <- c(
  oxide = "Oxide", intermetallic = "Intermetallic", chalcogenide = "Chalcogenide",
  halide = "Halide", pnictide = "Pnictide", other = "Other"
)
# ---- panel (a): committee gain median per stratum ---------------------------
# Single neutral fill: the stratum is already named on the x-axis, so a
# per-stratum colour key would be a purely decorative (guide-less, uncaptioned)
# re-encoding of position -- removed in the 2026-07-16 figure-content pass.
# Bar height alone carries the signal (oxide +0.563 dominates; rest <= +0.10).
gain <- res$committee_gain_median
df_a <- data.frame(
  stratum = factor(stratum_labels[strata], levels = stratum_labels[strata]),
  gain = vapply(strata, function(s) gain[[s]], numeric(1))
)

p_a <- ggplot(df_a, aes(x = stratum, y = gain)) +
  geom_col(width = 0.68, fill = "#999999", colour = "grey25", linewidth = 0.3) +
  geom_hline(yintercept = 0, colour = "black", linewidth = 0.4) +
  # Value labels always sit clear of the bar: above for positive, below for the
  # lone small negative (halide). Generous y-expansion (below) keeps both the
  # top "+0.563" label and the negative label inside the panel.
  geom_text(aes(label = sprintf("%+.3f", gain),
                vjust = ifelse(gain >= 0, -0.6, 1.5)), size = 3.0) +
  scale_y_continuous(expand = expansion(mult = c(0.14, 0.20))) +
  labs(
    x = NULL,
    y = "committee-variance\nabstention benefit\n(DAF gain, median)"
  ) +
  theme_minimal(base_size = 10, base_family = ff) +
  theme(
    axis.text.x = element_text(angle = 40, hjust = 1, size = 8.5),
    axis.title.y = element_text(size = 9),
    panel.grid.minor = element_blank(), panel.grid.major.x = element_blank(),
    plot.margin = margin(4, 6, 4, 4)
  )

# ---- panel (b): 15 stratum-pair committee interactions ----------------------
pp <- res$gate$per_pair # data.frame; interaction_ci95 is a list column
ci <- do.call(rbind, pp$interaction_ci95)
df_b <- data.frame(
  pair = paste0(stratum_labels[pp$stratumA], " − ", stratum_labels[pp$stratumB]),
  med = pp$interaction_med,
  lo = ci[, 1], hi = ci[, 2],
  fired = pp$excludes_0,
  single_fired = pp$single_consensus_excl0
)
df_b$pair <- factor(df_b$pair, levels = df_b$pair[order(df_b$med)])
n_fired <- sum(df_b$fired)
# Fixed x for the single-model-consensus asterisk gutter: past the widest CI
# whisker, in the right margin opened by the upper x-expansion below.
ast_x <- max(df_b$hi) + 0.085

p_b <- ggplot(df_b, aes(x = med, y = pair, colour = fired)) +
  geom_vline(xintercept = 0, linetype = "dashed", colour = "black",
             linewidth = 0.4, alpha = 0.7) +
  geom_errorbar(aes(xmin = lo, xmax = hi), orientation = "y",
                width = 0.4, linewidth = 0.7) +
  geom_point(size = 2.1) +
  geom_text(
    data = subset(df_b, single_fired),
    aes(x = ast_x, label = "*"),
    colour = "black", size = 4.6, vjust = 0.78, show.legend = FALSE
  ) +
  scale_colour_manual(
    values = c(`TRUE` = "#D55E00", `FALSE` = "#999999"),
    labels = c(
      `TRUE` = sprintf("CI excludes 0 (%d/%d)", n_fired, nrow(df_b)),
      `FALSE` = "CI includes 0"
    ),
    name = NULL
  ) +
  scale_x_continuous(expand = expansion(mult = c(0.05, 0.13))) +
  labs(
    x = expression(atop("interaction " * gain[A] - gain[B],
                         "(committee-variance; median, 95% CI)")),
    y = NULL
  ) +
  theme_minimal(base_size = 10, base_family = ff) +
  theme(
    axis.text.y = element_text(size = 8.5),
    axis.title.x = element_text(size = 9),
    legend.position = "bottom", legend.text = element_text(size = 8.5),
    panel.grid.minor = element_blank(),
    plot.margin = margin(4, 4, 4, 2)
  )

p <- (p_a + p_b + plot_layout(widths = c(1.0, 1.28))) +
  plot_annotation(tag_levels = "a", tag_prefix = "(", tag_suffix = ")") &
  theme(plot.tag = element_text(size = 10, family = ff))

# Canvas: tall enough that panel (b)'s 15 categorical rows and their pair
# labels do not collide and the single-model asterisk gutter reads as 14
# separated marks (the 2026-07-16 audit's 2.79in canvas crushed all 15 rows
# and their labels into an overlapping stack). Included at \textwidth (~6.5in)
# this scales base_size=10 to ~8.8pt effective; the ~0.20in per-row pitch on
# the page leaves clear inter-label whitespace.
ggsave(paste0(out_stem, ".pdf"), p, width = 7.4, height = 4.25, device = cairo_pdf, family = ff)
ggsave(paste0(out_stem, ".png"), p, width = 7.4, height = 4.25, dpi = 300,
       device = ragg::agg_png)

cat(sprintf("Wrote %s.pdf and %s.png from %s\n", out_stem, out_stem, input_json))
