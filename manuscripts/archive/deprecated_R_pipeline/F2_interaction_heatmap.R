# F2: stratum x stratum-pair x model matched-yield interaction heatmap.
# Source: mt29_stage1_matched_yield_result.json (interactions_matched_yield).
# Cell = interaction_med (gain_A - gain_B) for each (model, stratumA-stratumB) pair;
# CI-excludes-0 cells are outlined. Nothing hand-typed.
source("/home/zeyufu/Desktop/Orchestration-files/manuscript-template/ggtheme.R")
suppressMessages(library(dplyr))

res <- "/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/research/results/MT29/mt29_stage1_matched_yield_result.json"
d <- read_result(res)
ints <- d$interactions_matched_yield

df <- bind_rows(lapply(ints, function(x) data.frame(
  model     = x$model,
  pair      = paste(x$stratumA, "-", x$stratumB),
  stratumA  = x$stratumA,
  inter     = x$interaction_med,
  excl0     = isTRUE(x$excludes_0)
)))

# order pairs by oxide-anchored first (the hypothesised high-benefit stratum), then the rest
strata <- c("oxide", "intermetallic", "chalcogenide", "halide", "pnictide", "other")
pair_levels <- unique(df$pair[order(match(df$stratumA, strata), df$pair)])
df$pair  <- factor(df$pair, levels = rev(pair_levels))
df$model <- factor(df$model, levels = c("chgnet", "m3gnet", "mace", "orb"),
                   labels = c("CHGNet", "M3GNet", "MACE", "ORB"))

p <- ggplot(df, aes(x = model, y = pair, fill = inter)) +
  geom_tile(colour = "grey85", linewidth = 0.3) +
  geom_tile(data = subset(df, excl0), colour = "black", linewidth = 0.7, fill = NA) +
  scale_fill_gradient2(low = "#D55E00", mid = "white", high = "#0072B2",
                       midpoint = 0, name = "interaction\n(gain_A - gain_B)") +
  labs(
    x = NULL, y = "stratum pair (A - B)",
    title = "Stratum x coverage interaction: oxide-anchored pairs fire positive",
    caption = "Outlined cells = 95% bootstrap CI excludes 0. Source: mt29_stage1_matched_yield_result.json"
  ) +
  theme_paper() +
  theme(axis.text.y = element_text(size = 7),
        legend.key.width = unit(1.2, "cm"))

save_fig(p, "/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/manuscripts/figures/F2_interaction_heatmap",
         w = 7.0, h = 6.5)
cat("F2 done\n")
