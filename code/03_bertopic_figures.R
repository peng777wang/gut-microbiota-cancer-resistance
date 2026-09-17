# =============================================================================
# Figure 9 panels drawn from the BERTopic output tables.
#   Input  : folder produced by Figure9_BERTopic_pipeline.py
#   Output : one PDF and one TIF per panel, Times New Roman, no composition
#
# Usage
#   Rscript Figure9_plots_TimesNewRoman.R <input_dir> <output_dir>
# =============================================================================

args <- commandArgs(trailingOnly = TRUE)
input_dir <- if (length(args) >= 1) args[1] else "C:/72.wxjlx-1/Figure9_output"
output_dir <- if (length(args) >= 2) args[2] else file.path(input_dir, "figures")
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

suppressPackageStartupMessages({
  library(ggplot2)
})

# --- Times New Roman ---------------------------------------------------------
# The PDF is written with grDevices::cairo_pdf(), which embeds a real Times New
# Roman subset. Do not use showtext here, it converts text to vector outlines
# and the PDF then contains no embedded fonts.
FONT <- "Times New Roman"
BASE_SIZE <- 9

theme_paper <- function() {
  theme_bw(base_size = BASE_SIZE, base_family = FONT) +
    theme(
      panel.grid.minor = element_blank(),
      panel.border = element_rect(colour = "black", linewidth = 0.4),
      axis.text = element_text(colour = "black"),
      axis.title = element_text(colour = "black"),
      plot.title = element_text(hjust = 0.5, face = "bold"),
      legend.title = element_text(face = "bold"),
      legend.key.size = unit(9, "pt")
    )
}

write_with_retry <- function(target, writer, attempts = 4) {
  # a file that is open in a viewer cannot be overwritten on Windows, so retry
  # and fall back to a suffixed name instead of losing the whole run
  for (attempt in seq_len(attempts)) {
    ok <- tryCatch({
      writer(target)
      TRUE
    }, error = function(e) {
      if (attempt == attempts) {
        fallback <- sub("\\.(pdf|tif)$", paste0("_new.\\1"), target)
        message("could not write ", basename(target), " (", conditionMessage(e),
                "), writing ", basename(fallback), " instead. Close the file and rerun.")
        writer(fallback)
        return(TRUE)
      }
      Sys.sleep(1.5)
      FALSE
    })
    if (isTRUE(ok)) return(invisible(TRUE))
  }
}

save_panel <- function(plot, name, width, height) {
  pdf_file <- file.path(output_dir, paste0(name, ".pdf"))
  tif_file <- file.path(output_dir, paste0(name, ".tif"))
  write_with_retry(pdf_file, function(target) {
    grDevices::cairo_pdf(target, width = width, height = height,
                         family = FONT, bg = "white")
    print(plot)
    grDevices::dev.off()
  })
  write_with_retry(tif_file, function(target) {
    ggsave(target, plot, width = width, height = height, units = "in",
           device = "tiff", type = "cairo", dpi = 600, compression = "lzw")
  })
  message("written: ", basename(pdf_file), " and ", basename(tif_file))
}

read_table <- function(file) {
  path <- file.path(input_dir, file)
  if (!file.exists(path)) stop("missing input: ", path)
  # note: fileEncoding = "UTF-8-BOM" truncates these files in R, use encoding
  df <- read.csv(path, check.names = FALSE, encoding = "UTF-8")
  names(df) <- sub("^\uFEFF", "", names(df))   # strip a stray byte order mark
  df
}

# ------------------------------------------------------------------ panel A
a <- read_table("Figure9A_source_data.csv")
a$Topic <- as.integer(a$Topic)
message("panel A: ", nrow(a), " documents, ", length(unique(a$Topic)), " topics")
if (nrow(a) < 1000) stop("panel A input looks truncated, check the CSV reader")
doc_counts <- table(a$Topic)
centroids <- aggregate(cbind(UMAP1, UMAP2) ~ Topic, data = a, FUN = mean)
centroids$label <- ifelse(centroids$Topic == -1, "Topic -1",
                          paste0("T", centroids$Topic))

p_a <- ggplot(a, aes(UMAP1, UMAP2)) +
  geom_point(aes(colour = Topic), size = 0.35, alpha = 0.75) +
  geom_label(data = centroids, aes(label = label),
             family = FONT, size = 2.0, label.size = 0.1,
             label.padding = unit(0.08, "lines"), fill = "white", alpha = 0.85) +
  scale_colour_gradientn(
    colours = c("#08306B", "#2171B5", "#6BAED6", "#C6DBEF"),
    breaks = 0:10, labels = 0:10, name = "Topic") +
  labs(x = "UMAP 1", y = "UMAP 2",
       title = "Documents and Topics") +
  theme_paper() +
  theme(legend.position = "right")
save_panel(p_a, "Figure9A_documents_topics", 7.2, 5.6)

# ------------------------------------------------------------------ panel B
b <- read_table("Figure9B_source_data.csv")
b$Topic <- as.integer(b$Topic)
b$label <- paste0("T", b$Topic)

p_b <- ggplot(b, aes(PC1, PC2)) +
  geom_point(aes(size = Documents), shape = 21, fill = "#9ECAE1",
             colour = "black", stroke = 0.3, alpha = 0.9) +
  geom_text(aes(label = label), family = FONT, size = 2.2, vjust = -1.6) +
  scale_size_continuous(name = "Documents", range = c(1.5, 8)) +
  labs(x = "PC1", y = "PC2", title = "Intertopic Distance Map") +
  theme_paper()
save_panel(p_b, "Figure9B_intertopic_distance", 7.2, 5.6)

# ------------------------------------------------------------------ panel C
c_mat <- read_table("Figure9C_source_data.csv")
labels <- c_mat[[1]]
c_long <- data.frame(
  row = rep(labels, times = ncol(c_mat) - 1),
  col = rep(labels, each  = nrow(c_mat)),
  value = as.vector(as.matrix(c_mat[, -1]))
)
c_long$row <- factor(c_long$row, levels = rev(labels))
c_long$col <- factor(c_long$col, levels = labels)
c_long$value <- pmin(pmax(as.numeric(c_long$value), 0), 1)  # clip float overshoot
c_long$label <- ifelse(c_long$value >= 0.995,
                       sprintf("%.1f", c_long$value),
                       sprintf("%.2f", c_long$value))

p_c <- ggplot(c_long, aes(col, row, fill = value)) +
  geom_tile(colour = "white", linewidth = 0.1) +
  geom_text(aes(label = label), family = FONT, size = 1.5, colour = "black") +
  scale_fill_gradientn(colours = c("#FFFFE5", "#C7E9B4", "#41B6C4", "#225EA8"),
                       limits = c(0, 1), name = "Cosine similarity") +
  labs(x = NULL, y = NULL, title = "Similarity Matrix") +
  theme_paper() +
  theme(axis.text.x = element_text(angle = 90, hjust = 1, vjust = 0.5, size = 6),
        axis.text.y = element_text(size = 6))
save_panel(p_c, "Figure9C_similarity_matrix", 8.0, 7.0)

# ------------------------------------------------------------------ panel D
d <- read_table("Figure9D_source_data.csv")
names(d)[1] <- "Year"
d$Year <- as.integer(d$Year)
d_long <- do.call(rbind, lapply(setdiff(names(d), "Year"), function(col) {
  data.frame(Year = d$Year, Topic = as.integer(col), Frequency = d[[col]])
}))
d_long$Topic <- factor(d_long$Topic, levels = sort(unique(d_long$Topic)))
topic_levels <- levels(d_long$Topic)
topic_palette <- colorRampPalette(c("#08306B", "#2171B5", "#6BAED6",
                                    "#C6DBEF"))(length(topic_levels))
names(topic_palette) <- topic_levels

p_d <- ggplot(d_long, aes(Year, Frequency, colour = Topic, group = Topic)) +
  geom_line(linewidth = 0.4) +
  geom_point(size = 0.7) +
  scale_colour_manual(values = topic_palette, name = "Topic",
                      labels = paste0("T", topic_levels)) +
  guides(colour = guide_legend(ncol = 1, override.aes = list(linewidth = 1))) +
  scale_x_continuous(breaks = sort(unique(d_long$Year))) +
  labs(x = "Year", y = "Frequency", title = "Topics over Time") +
  theme_paper() +
  theme(legend.position = "right",
        legend.text = element_text(size = 7),
        legend.key.height = unit(9, "pt"),
        legend.spacing.y = unit(0.5, "pt"))
save_panel(p_d, "Figure9D_topics_over_time", 8.2, 5.4)

message("all panels written to ", output_dir)
