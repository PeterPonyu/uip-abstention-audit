# F1: matched-yield DAF at full vs abstaining coverage, per anion stratum, per model.
# Source: mt29_stage1_matched_yield_result.json (per_model_budgets:
#   daf_top_y_loose = looser yield (more candidates surfaced, lower coverage of abstention),
#   daf_top_y_tight = tighter yield (abstain harder, half the budget)).
# Every value is read from the result JSON; nothing is hand-typed.
source("/home/zeyufu/Desktop/Orchestration-files/manuscript-template/ggtheme.R")
suppressMessages(library(dplyr))

res <- "/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/research/results/MT29/mt29_stage1_matched_yield_result.json"
d <- read_result(res)
pmb <- d$per_model_budgets

strata <- c("oxide", "intermetallic", "chalcogenide", "halide", "pnictide", "other")
models <- c("chgnet", "m3gnet", "mace", "orb")

rows <- list()
for (m in models) {
  b <- pmb[[m]]
  for (s in strata) {
    rows[[length(rows) + 1]] <- data.frame(
      model    = m, stratum = s,
      coverage = c("looser yield (Y_loose)", "abstaining (Y_tight)"),
      DAF      = c(b$daf_top_y_loose[[s]], b$daf_top_y_tight[[s]])
    )
  }
}
df <- bind_rows(rows)
df$coverage <- factor(df$coverage,
                      levels = c("looser yield (Y_loose)", "abstaining (Y_tight)"))
df$stratum  <- factor(df$stratum, levels = strata)
df$model    <- factor(df$model, levels = models,
                      labels = c("CHGNet", "M3GNet", "MACE", "ORB"))

p <- ggplot(df, aes(x = stratum, y = DAF, fill = coverage)) +
  geom_col(position = position_dodge(width = 0.72), width = 0.66, colour = "grey25",
           linewidth = 0.2) +
  facet_wrap(~model, nrow = 1) +
  scale_fill_paper() +
  labs(
    x = "anion-class stratum", y = "discovery acceleration factor (DAF)",
    fill = NULL,
    title = "Matched-yield abstention lifts DAF most in oxides",
    caption = "Source: mt29_stage1_matched_yield_result.json"
  ) +
  theme_paper() +
  theme(axis.text.x = element_text(angle = 40, hjust = 1, size = 8))

save_fig(p, "/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/manuscripts/figures/F1_daf_coverage",
         w = 9.5, h = 3.6)
cat("F1 done\n")
