#!/usr/bin/env Rscript
# ==========================================================================
# F1_daf_coverage.R -- paper Fig. 1: matched-yield DAF at the looser
# (Y_loose) vs tighter (Y_tight, abstaining) yield budgets, per anion-class
# stratum and per UIP model.
#
# REGENERATE-ONLY-FROM-JSON RULE (portfolio honest-audit culture):
#   Reads EXCLUSIVELY the frozen result JSON below; never hardcode arrays,
#   never hand-edit the JSON. Rebuild with `make figures` from manuscripts/.
#
# Input : ../research/results/MT29/mt29_stage1_matched_yield_result.json
#         (per_model_budgets[model]$daf_top_y_loose / $daf_top_y_tight)
# Output: figures/F1_daf_coverage.pdf and figures/F1_daf_coverage.png
# ==========================================================================

suppressPackageStartupMessages({
  library(jsonlite)
  library(ggplot2)
})

# Serif family (JCIM/ACS Times-like). Set at BOTH the theme and the device so
# geom_text() and plotmath (which do not inherit the theme base_family) also
# render in serif; keeps every embedded glyph in one serif family with no
# sans/CJK fallback fonts (see figures README / pdffonts acceptance).
ff <- "TeX Gyre Termes"
update_geom_defaults("text", list(family = ff))
update_geom_defaults("label", list(family = ff))

input_json <- "../research/results/MT29/mt29_stage1_matched_yield_result.json"
out_stem <- "figures/F1_daf_coverage"

if (!file.exists(input_json)) {
  stop(sprintf(
    "Result JSON not found: %s\nFigures regenerate ONLY from on-disk result JSONs; run the analysis first.",
    input_json
  ))
}

res <- fromJSON(input_json)

models <- c("chgnet", "m3gnet", "mace", "orb")
model_labels <- c(chgnet = "CHGNet", m3gnet = "M3GNet", mace = "MACE", orb = "ORB")
strata <- c("oxide", "intermetallic", "chalcogenide", "halide", "pnictide", "other")
stratum_labels <- c(
  oxide = "Oxide", intermetallic = "Intermetallic", chalcogenide = "Chalcogenide",
  halide = "Halide", pnictide = "Pnictide", other = "Other"
)

rows <- list()
for (m in models) {
  b <- res$per_model_budgets[[m]]
  for (s in strata) {
    rows[[length(rows) + 1]] <- data.frame(
      model = model_labels[[m]], stratum = s,
      budget = "looser yield (Y_loose)", daf = b$daf_top_y_loose[[s]]
    )
    rows[[length(rows) + 1]] <- data.frame(
      model = model_labels[[m]], stratum = s,
      budget = "abstaining (Y_tight)", daf = b$daf_top_y_tight[[s]]
    )
  }
}
df <- do.call(rbind, rows)
df$model <- factor(df$model, levels = unname(model_labels))
df$stratum <- factor(df$stratum, levels = strata, labels = stratum_labels[strata])
df$budget <- factor(df$budget,
  levels = c("looser yield (Y_loose)", "abstaining (Y_tight)")
)

p <- ggplot(df, aes(x = stratum, y = daf, fill = budget)) +
  geom_col(position = position_dodge(width = 0.72), width = 0.66,
           colour = "grey40", linewidth = 0.25) +
  geom_hline(yintercept = 1.0, linetype = "dashed", linewidth = 0.4,
             colour = "black", alpha = 0.6) +
  facet_wrap(~model, nrow = 1, scales = "free_y") +
  scale_fill_manual(
    values = c("#999999", "#E69F00"),
    labels = c(
      expression("looser yield (" * Y[loose] * ")"),
      expression("abstaining (" * Y[tight] * ")")
    )
  ) +
  labs(x = NULL, y = "discovery acceleration\nfactor (DAF)", fill = NULL) +
  theme_minimal(base_size = 10, base_family = ff) +
  theme(
    axis.text.x = element_text(angle = 40, hjust = 1, size = 8.5),
    legend.position = "bottom",
    panel.grid.minor = element_blank(),
    panel.grid.major.x = element_blank(),
    strip.text = element_text(size = 9)
  )

# Canvas sized so the included width (\textwidth in the paper, ~6.5in) scales
# base_size=10 to ~8.5pt effective on the printed page (typography audit
# 2026-07-16: the previous 10.5x3.4in canvas rendered at ~6.2pt effective).
ggsave(paste0(out_stem, ".pdf"), p, width = 7.65, height = 2.48, device = cairo_pdf, family = ff)
ggsave(paste0(out_stem, ".png"), p, width = 7.65, height = 2.48, dpi = 300,
       device = ragg::agg_png)

cat(sprintf("Wrote %s.pdf and %s.png from %s\n", out_stem, out_stem, input_json))
