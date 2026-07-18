# F3: robustness panel - interaction-CI-excl-0 counts under LOEO (12/12 splits) and
# WBM-round (3/5 rounds) splits. Source: mt29_stage2_robustness_result.json
#   gate1_loeo[E]   : n_excl0 / n_cells  (held-out element E)
#   gate2_rounds[r] : n_excl0 / n_cells  (WBM round r)
# Bars coloured by whether the split is majority-firing. Nothing hand-typed.
source("/home/zeyufu/Desktop/Orchestration-files/manuscript-template/ggtheme.R")
suppressMessages(library(dplyr))

res <- "/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/research/results/MT29/mt29_stage2_robustness_result.json"
d <- read_result(res)

loeo <- bind_rows(lapply(names(d$gate1_loeo), function(e) {
  v <- d$gate1_loeo[[e]]
  data.frame(gate = "Leave-one-element-out", split = e,
             n_excl0 = v$n_excl0, n_cells = v$n_cells,
             majority = isTRUE(v$majority_excl0))
}))
rounds <- bind_rows(lapply(names(d$gate2_rounds), function(r) {
  v <- d$gate2_rounds[[r]]
  data.frame(gate = "WBM round", split = paste0("R", r),
             n_excl0 = v$n_excl0, n_cells = v$n_cells,
             majority = isTRUE(v$majority_excl0))
}))
df <- bind_rows(loeo, rounds)
df$frac <- df$n_excl0 / df$n_cells
# order LOEO bars by held-out element as listed; rounds R1..R5
df$split <- factor(df$split, levels = c(names(d$gate1_loeo), paste0("R", names(d$gate2_rounds))))
df$majority <- factor(ifelse(df$majority, "majority-firing", "below majority"),
                      levels = c("majority-firing", "below majority"))

p <- ggplot(df, aes(x = split, y = frac, fill = majority)) +
  geom_col(width = 0.74, colour = "grey25", linewidth = 0.2) +
  geom_hline(yintercept = 0.5, linetype = "dashed", colour = "grey30") +
  geom_text(aes(label = paste0(n_excl0, "/", n_cells)),
            vjust = -0.35, size = 2.6) +
  facet_grid(~gate, scales = "free_x", space = "free_x") +
  scale_fill_manual(values = c("majority-firing" = "#0072B2",
                               "below majority"   = "#D55E00"), name = NULL) +
  scale_y_continuous(limits = c(0, 1.0), expand = expansion(mult = c(0, 0.08))) +
  labs(
    x = "robustness split (held-out element / WBM round)",
    y = "fraction of cells with CI excluding 0",
    title = "Interaction survives 12/12 LOEO and 3/5 WBM-round splits",
    caption = "Dashed line = majority (0.5). Source: mt29_stage2_robustness_result.json"
  ) +
  theme_paper() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1, size = 8))

save_fig(p, "/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/manuscripts/figures/F3_robustness_panel",
         w = 9.0, h = 4.0)
cat("F3 done\n")
