# ============================================================================
# Cubic growth-curve fits and panel C of Figure 2
#
# Original analysis script (file name on the author's workstation: 代码V1.R,
# figure folder "3.拟合图"), included verbatim apart from this header so that
# the fitted curves and the R2 values printed in Figure 2C of the manuscript
# can be regenerated.
#
# The three annual series below are identical to
# data_derived/annual_output_by_database.csv.
#
# Note on the figure: the three annotated equations are drawn in the colour of
# the series they belong to (Total = #0E3E87, SCOPUS = #346CAC,
# WOSCC = #DEEAEA), so the annotated order is Total, SCOPUS, WOSCC while the
# legend order is WOSCC, SCOPUS, WOSCC+SCOPUS.
#
# Requires: tidyverse (ggplot2, dplyr, tidyr).
# ============================================================================

library(tidyverse)

# ========== 1. 数据 ==========
df <- data.frame(
  Year = 2016:2025,
  WOSCC = c(18, 18, 39, 46, 72, 94, 123, 137, 145, 286),
  SCOPUS = c(33, 28, 49, 66, 110, 115, 149, 172, 200, 314),
  Total = c(40, 38, 63, 84, 133, 154, 185, 210, 235, 390)
)

df_long <- df %>%
  pivot_longer(cols = c(WOSCC, SCOPUS, Total),
               names_to = "Database", 
               values_to = "Publications")

df_long$Database <- factor(df_long$Database, 
                           levels = c("WOSCC", "SCOPUS", "Total"),
                           labels = c("WOSCC", "SCOPUS", "WOSCC+SCOPUS"))

# ========== 2. 拟合（年份中心化，避免NA） ==========
get_poly3_stats <- function(x, y) {
  x0 <- x - min(x)  # 2016年设为0，数值稳定
  fit <- lm(y ~ poly(x0, 3, raw = TRUE))
  r2 <- summary(fit)$r.squared
  cf <- coef(fit)
  # 公式字符串（x代表Year-2016）
  formula_str <- sprintf("y = %.4fx³ + %.4fx² + %.2fx + %.2f\nR² = %.4f",
                         cf[4], cf[3], cf[2], cf[1], r2)
  return(list(formula = formula_str))
}

stats_wos <- get_poly3_stats(df$Year, df$WOSCC)
stats_sco <- get_poly3_stats(df$Year, df$SCOPUS)
stats_tot <- get_poly3_stats(df$Year, df$Total)

cat("WOSCC:", stats_wos$formula, "\n\n")
cat("SCOPUS:", stats_sco$formula, "\n\n")
cat("Total:", stats_tot$formula, "\n\n")

# ========== 3. 画图（无背景网格，无上下右边框） ==========
p <- ggplot(df_long, aes(x = Year, y = Publications, color = Database)) +
  
  # 实线 + 空心圆点
  geom_line(linewidth = 1.2) +
  geom_point(size = 3, shape = 21, fill = "white", stroke = 1.2) +
  
  # 虚线拟合
  geom_smooth(data = subset(df_long, Database == "WOSCC"),
              method = "lm", formula = y ~ I(x-2016) + I((x-2016)^2) + I((x-2016)^3),
              se = FALSE, linetype = "dashed", linewidth = 0.8, color = "#DEEAEA") +
  geom_smooth(data = subset(df_long, Database == "SCOPUS"),
              method = "lm", formula = y ~ I(x-2016) + I((x-2016)^2) + I((x-2016)^3),
              se = FALSE, linetype = "dashed", linewidth = 0.8, color = "#346CAC") +
  geom_smooth(data = subset(df_long, Database == "WOSCC+SCOPUS"),
              method = "lm", formula = y ~ I(x-2016) + I((x-2016)^2) + I((x-2016)^3),
              se = FALSE, linetype = "dashed", linewidth = 0.8, color = "#0E3E87") +
  
  # 坐标轴
  scale_x_continuous(breaks = 2016:2025, expand = c(0.02, 0.02)) +
  scale_y_continuous(limits = c(0, 500), breaks = seq(0, 500, 50),
                     expand = c(0, 0)) +
  
  scale_color_manual(values = c("WOSCC" = "#DEEAEA", 
                                "SCOPUS" = "#346CAC", 
                                "WOSCC+SCOPUS" = "#0E3E87")) +
  
  # 主题：去掉背景横线/竖线，去掉上下右边框，只保留左下L形轴
  theme_classic(base_size = 14) +
  theme(
    panel.grid.major = element_blank(),      # 去掉背景横线
    panel.grid.minor = element_blank(),      # 去掉背景细线
    panel.border = element_blank(),          # 去掉四周边框
    axis.line = element_line(color = "black", linewidth = 0.5),  # 左下轴线
    axis.line.y.right = element_blank(),     # 去掉右边竖杠
    axis.line.x.top = element_blank(),       # 去掉上面横杠
    axis.ticks = element_line(color = "black"),
    legend.position = c(0.22, 0.82),
    legend.background = element_blank(),
    legend.title = element_blank(),
    legend.text = element_text(size = 11),
    axis.title.x = element_text(size = 13, face = "bold"),
    axis.title.y = element_text(size = 13, face = "bold"),
    plot.margin = margin(20, 60, 20, 20)
  ) +
  
  labs(x = "Year", y = "Publications") +
  
  # 公式文本（位置可根据实际显示微调）
  annotate("text", x = 2020.3, y = 460, 
           label = stats_tot$formula, 
           color = "#0E3E87", size = 3.3, hjust = 0) +
  annotate("text", x = 2020.3, y = 410, 
           label = stats_sco$formula, 
           color = "#346CAC", size = 3.3, hjust = 0) +
  annotate("text", x = 2020.3, y = 360, 
           label = stats_wos$formula, 
           color = "#DEEAEA", size = 3.3, hjust = 0)

print(p)

# ========== 4. 保存 ==========
ggsave("Figure2A_Clean.png", p, 
       width = 10, height = 7, dpi = 300, bg = "white")

ggsave("Figure2A_Clean.tiff", p, 
       width = 10, height = 7, dpi = 300, bg = "white", compression = "lzw")
