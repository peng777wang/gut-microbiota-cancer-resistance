# =============================================================================
# Figure 8A 复现脚本：Top 10 高被引文献气泡图
#   （数据取法 = biblioshiny 的 Documents -> Most Global Cited Documents）
#
# 为什么需要这个脚本：
#   biblioshiny 的 "Most Global Cited Documents" 只出「横条图 + 数据表」，
#   没有气泡图，也没有期刊 Impact Factor 字段。
#   气泡图（x = Total Citations，气泡大小 = Normalized TC，颜色 = IF）
#   必须拿它的表另外画。本脚本用与 biblioshiny 完全相同的算法复算后再画。
#
# biblioshiny 源码里的两行关键算法（已核对）：
#   TCperYear = round(TC / (y + 1 - PY), 1)      # y = 当前年份
#   NormalizedTC = TC / mean(TC)  按 PY 分组
# 注意：NormalizedTC 的分母是「你所用语料中同年份所有文献的平均被引」，
#       所以换一套语料，Normalized TC 的数值会全部改变。
# =============================================================================

library(bibliometrix)
library(dplyr)
library(ggplot2)

# --- 1. 读入语料（你的最终语料，1532 条，WoS 纯文本格式）---------------------
# 路径按需修改；也可换成导出的 .txt/.csv（dbsource 相应改为 "wos" / "scopus"）
M <- convert2df("C:/62.wxjlx/gjc/date/download.txt",
                dbsource = "wos", format = "plaintext")

# --- 2. 期刊 IF 对照表（必须自己准备，并注明 JCR 年度）------------------------
# CSV 两列：Journal, IF。Journal 用与 WoS 的 SO 字段一致的刊名/缩写。
# 例如：  Journal,IF
#         SCIENCE,44.7
#         CELL,45.1
if_tab <- read.csv("journal_IF.csv", stringsAsFactors = FALSE)

# --- 3. 复算 biblioshiny 的三列 -------------------------------------------------
y <- as.numeric(format(Sys.Date(), "%Y"))   # 当前年份

D <- M %>%
  mutate(PY = as.numeric(PY),
         TCperYear = round(TC / (y + 1 - PY), 1)) %>%
  group_by(PY) %>%
  mutate(NormalizedTC = TC / mean(TC)) %>%
  ungroup() %>%
  left_join(if_tab, by = c("SO" = "Journal"))

# --- 4. Figure 8A 的底表（Top 10 by TC）----------------------------------------
Fig8A <- D %>%
  arrange(desc(TC)) %>%
  head(10) %>%
  transmute(Paper = SR, Journal = SO, Year = PY, DOI = DI,
            `Total Citations` = TC,
            `TC per Year`    = TCperYear,
            `Normalized TC`  = round(NormalizedTC, 2),
            IF)

print(as.data.frame(Fig8A))
write.csv(Fig8A, "Figure8A_data.csv", row.names = FALSE, fileEncoding = "UTF-8")

# --- 5. 气泡图 ------------------------------------------------------------------
p <- ggplot(Fig8A, aes(x = `Total Citations`,
                       y = reorder(Paper, `Total Citations`))) +
  geom_point(aes(size = `Normalized TC`, colour = IF)) +
  scale_size_continuous(range = c(3, 10), name = "Normalized\nCitations") +
  scale_colour_gradient(low = "#1B7837", high = "#D73027",
                        name = "Impact Factor\n(IF)") +
  labs(x = "Total Global Citations", y = "Documents",
       title = "Top Papers by Total Global Citations and IF") +
  theme_classic(base_size = 11) +
  theme(plot.title = element_text(hjust = 0.5, face = "bold"),
        panel.grid.major.x = element_line(colour = "grey92"))

print(p)
ggsave("Figure8A.png", p, width = 9, height = 5, dpi = 600)
ggsave("Figure8A.pdf", p, width = 9, height = 5)   # 投稿用矢量图

# --- 6. 只要数据、不要图？--------------------------------------------------------
# biblioshiny 界面里点 "Report" 按钮，会把这张表写进 Excel 报告的一个
# 名为 MostGlobCitDocs 的 sheet，效果与上面 Figure8A_data.csv 相同。
