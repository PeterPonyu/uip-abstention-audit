#!/usr/bin/env Rscript
# ==========================================================================
# F3_robustness_panel.R -- paper Fig. 3: fraction of (model x stratum-pair)
# cells whose 95% CI excludes zero, per robustness split.
# Left: leave-one-element-out (12 splits). Right: WBM acquisition round (5).
# Cell counts annotated; dashed line = majority threshold (0.5).
#
# REGENERATE-ONLY-FROM-JSON RULE: reads EXCLUSIVELY the frozen result JSON
# below; never hardcode arrays, never hand-edit the JSON.
#
# Input : ../research/results/MT29/mt29_stage2_robustness_result.json
#         (gate1_loeo[elem]$n_excl0/$n_cells, gate2_rounds[r]$n_excl0/...)
# Output: figures/F3_robustness_panel.pdf and .png
# ==========================================================================

suppressPackageStartupMessages({
  library(jsonlite)
  library(ggplot2)
  library(patchwork)
})

# Serif family (JCIM/ACS Times-like), set at theme + device + geom defaults so
# every embedded glyph stays in one serif family with no sans/CJK fallback
# fonts. Panel identity is carried by (a)/(b) tags (this is a two-panel
# composite, plain weight per the no-decorative-bold typography rule); the
# per-split success counts live in the caption, not in-plot.
ff <- "TeX Gyre Termes"
update_geom_defaults("text", list(family = ff))
update_geom_defaults("label", list(family = ff))

input_json <- "../research/results/MT29/mt29_stage2_robustness_result.json"
out_stem <- "figures/F3_robustness_panel"

if (!file.exists(input_json)) {
  stop(sprintf(
    "Result JSON not found: %s\nFigures regenerate ONLY from on-disk result JSONs; run the analysis first.",
    input_json
  ))
}

res <- fromJSON(input_json)

# ---- left: LOEO -----------------------------------------------------------
loeo <- res$gate1_loeo
loeo_df <- do.call(rbind, lapply(names(loeo), function(e) {
  data.frame(
    element = e,
    n_excl0 = loeo[[e]]$n_excl0,
    n_cells = loeo[[e]]$n_cells,
    n_rows = loeo[[e]]$n_rows
  )
}))
loeo_df$frac <- loeo_df$n_excl0 / loeo_df$n_cells
loeo_df$element <- factor(loeo_df$element, levels = names(loeo))
loeo_df$is_O <- loeo_df$element == "O"

n_pass_loeo <- sum(loeo_df$frac > 0.5)

# Label-clearance rule: a label placed just above its bar can visually collide
# with the dashed 0.5 threshold line whenever the bar top sits close to 0.5
# (from either side). Widen the label's offset from the bar in that case so
# it never sits on the line, instead of a fixed vjust that assumes the bar is
# always well clear of 0.5. Purely a layout rule -- computed from frac, no
# hardcoded per-category values.
loeo_df$label_y <- loeo_df$frac + ifelse(abs(loeo_df$frac - 0.5) < 0.08, 0.09, 0.035)

p_left <- ggplot(loeo_df, aes(x = element, y = frac, fill = is_O)) +
  geom_col(width = 0.7, colour = "grey30", linewidth = 0.3) +
  geom_hline(yintercept = 0.5, linetype = "dashed", colour = "black", linewidth = 0.5) +
  geom_text(aes(y = label_y, label = sprintf("%d/%d", n_excl0, n_cells)),
            vjust = 0, size = 3.0) +
  scale_fill_manual(values = c(`FALSE` = "#56B4E9", `TRUE` = "#E69F00"), guide = "none") +
  scale_y_continuous(limits = c(0, 1.05), expand = expansion(mult = c(0, 0.02))) +
  labs(
    x = "held-out element (drop all formulas containing it)",
    y = "fraction of cells CI-excl-0"
  ) +
  theme_minimal(base_size = 10, base_family = ff) +
  theme(
    panel.grid.minor = element_blank(), panel.grid.major.x = element_blank()
  )

# ---- right: WBM rounds ------------------------------------------------------
rnds <- res$gate2_rounds
rnd_df <- do.call(rbind, lapply(names(rnds), function(r) {
  data.frame(
    round = r,
    n_excl0 = rnds[[r]]$n_excl0,
    n_cells = rnds[[r]]$n_cells,
    n_rows = rnds[[r]]$n_rows
  )
}))
rnd_df$frac <- rnd_df$n_excl0 / rnd_df$n_cells
rnd_df$round <- factor(rnd_df$round, levels = sort(names(rnds)))

n_pass_rnd <- sum(rnd_df$frac > 0.5)

# Same label-clearance rule as the left panel (see above): widen the offset
# from the bar top whenever it sits close to the 0.5 dashed line, so the
# count label never overlaps the line.
rnd_df$label_y <- rnd_df$frac + ifelse(abs(rnd_df$frac - 0.5) < 0.08, 0.09, 0.035)

p_right <- ggplot(rnd_df, aes(x = round, y = frac)) +
  geom_col(width = 0.62, fill = "#009E73", colour = "grey30", linewidth = 0.3) +
  geom_hline(yintercept = 0.5, linetype = "dashed", colour = "black", linewidth = 0.5) +
  geom_text(aes(y = label_y, label = sprintf("%d/%d", n_excl0, n_cells)),
            vjust = 0, size = 3.0) +
  geom_text(aes(y = 0.02, label = sprintf("n=%dk", round(n_rows / 1000))),
            vjust = 0, size = 3.0, colour = "white") +
  scale_y_continuous(limits = c(0, 1.05), expand = expansion(mult = c(0, 0.02))) +
  labs(
    x = "WBM acquisition round (time-like)",
    y = NULL
  ) +
  theme_minimal(base_size = 10, base_family = ff) +
  theme(
    panel.grid.minor = element_blank(), panel.grid.major.x = element_blank()
  )

p <- (p_left + p_right + plot_layout(widths = c(3, 2))) +
  plot_annotation(tag_levels = "a", tag_prefix = "(", tag_suffix = ")") &
  theme(plot.tag = element_text(size = 10, family = ff))

# Canvas sized so the included width (\textwidth, ~6.5in) scales base_size=10
# to ~8.5pt effective (typography audit 2026-07-16: the previous 10.5x3.6in
# canvas rendered at ~6.2pt effective).
ggsave(paste0(out_stem, ".pdf"), p, width = 7.65, height = 2.62, device = cairo_pdf, family = ff)
ggsave(paste0(out_stem, ".png"), p, width = 7.65, height = 2.62, dpi = 300,
       device = ragg::agg_png)

cat(sprintf("Wrote %s.pdf and %s.png from %s\n", out_stem, out_stem, input_json))
