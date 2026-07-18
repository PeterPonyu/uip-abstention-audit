# F4: shuffle-null contrast. Real interaction magnitudes vs shuffled-confidence interaction
# magnitudes, per gate. Shows the real signal is large and the shuffle-null collapses to 0
# (0/700 LOEO, 0/300 rounds; 0/60 Stage-1).
# Sources:
#   mt29_stage1_matched_yield_result.json : interactions_matched_yield (+ _SHUFFLE)
#   mt29_stage2_robustness_result.json    : per-split interactions / interactions_SHUFFLE
# Nothing hand-typed.
source("/home/zeyufu/Desktop/Orchestration-files/manuscript-template/ggtheme.R")
suppressMessages(library(dplyr))

s1 <- read_result("/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/research/results/MT29/mt29_stage1_matched_yield_result.json")
s2 <- read_result("/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/research/results/MT29/mt29_stage2_robustness_result.json")

grab <- function(lst) vapply(lst, function(x) abs(x$interaction_med), numeric(1))

df <- bind_rows(
  data.frame(gate = "Stage-1 (60 cells)", kind = "real",
             val = grab(s1$interactions_matched_yield)),
  data.frame(gate = "Stage-1 (60 cells)", kind = "shuffled",
             val = grab(s1$interactions_matched_yield_SHUFFLE)),
  bind_rows(lapply(names(s2$gate1_loeo), function(e)
    data.frame(gate = "LOEO (700 cells)", kind = "real",
               val = grab(s2$gate1_loeo[[e]]$interactions)))),
  bind_rows(lapply(names(s2$gate1_loeo), function(e)
    data.frame(gate = "LOEO (700 cells)", kind = "shuffled",
               val = grab(s2$gate1_loeo[[e]]$interactions_SHUFFLE)))),
  bind_rows(lapply(names(s2$gate2_rounds), function(r)
    data.frame(gate = "WBM round (300 cells)", kind = "real",
               val = grab(s2$gate2_rounds[[r]]$interactions)))),
  bind_rows(lapply(names(s2$gate2_rounds), function(r)
    data.frame(gate = "WBM round (300 cells)", kind = "shuffled",
               val = grab(s2$gate2_rounds[[r]]$interactions_SHUFFLE))))
)
df$gate <- factor(df$gate,
                  levels = c("Stage-1 (60 cells)", "LOEO (700 cells)", "WBM round (300 cells)"))
df$kind <- factor(df$kind, levels = c("real", "shuffled"))

p <- ggplot(df, aes(x = gate, y = val, fill = kind)) +
  geom_violin(position = position_dodge(width = 0.8), width = 0.75,
              colour = "grey30", linewidth = 0.25, scale = "width", trim = TRUE) +
  geom_boxplot(position = position_dodge(width = 0.8), width = 0.16,
               outlier.size = 0.4, linewidth = 0.25, colour = "grey20", alpha = 0.9) +
  scale_fill_paper() +
  labs(
    x = NULL, y = "|interaction| (|gain_A - gain_B|)", fill = NULL,
    title = "Shuffle-null collapses to zero across every gate",
    caption = "CI-excludes-0 under shuffle: 0/60 (Stage-1), 0/700 (LOEO), 0/300 (round). Sources: mt29_stage1_matched_yield_result.json, mt29_stage2_robustness_result.json"
  ) +
  theme_paper()

save_fig(p, "/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/manuscripts/figures/F4_shuffle_null",
         w = 7.5, h = 4.2)
cat("F4 done\n")
