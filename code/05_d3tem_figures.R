# =============================================================================
# Figure 10 panels (D3TEM) drawn from the tables written by
# Figure10_D3TEM_pipeline.py
#   Output: one PDF and one TIF per panel, Times New Roman, no composition
#
# Usage
#   Rscript Figure10_plots_TimesNewRoman.R <input_dir> <output_dir>
# =============================================================================

args <- commandArgs(trailingOnly = TRUE)
input_dir <- if (length(args) >= 1) args[1] else "C:/72.wxjlx-1/Figure10_output"
output_dir <- if (length(args) >= 2) args[2] else file.path(input_dir, "figures")
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

suppressPackageStartupMessages({
  library(ggplot2)
  library(patchwork)
  library(RColorBrewer)
  library(ggrepel)
})

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
  for (attempt in seq_len(attempts)) {
    ok <- tryCatch({
      writer(target)
      TRUE
    }, error = function(e) {
      if (attempt == attempts) {
        fallback <- sub("\\.(pdf|tif)$", paste0("_new.\\1"), target)
        message("could not write ", basename(target), " (", conditionMessage(e),
                "), writing ", basename(fallback), " instead")
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
  df <- read.csv(path, check.names = FALSE, encoding = "UTF-8")
  names(df) <- sub("^\uFEFF", "", names(df))
  df
}

palette_for <- function(n) {
  base <- brewer.pal(8, "Dark2")
  if (n <= length(base)) base[seq_len(n)] else colorRampPalette(base)(n)
}

# ------------------------------------------------------------------ panel A
a <- read_table("Figure10A_source_data.csv")
a$Topic <- factor(a$Topic, levels = a$Topic[order(a$Meta_cluster, a$Topic)])
meta_levels <- paste0("Meta-cluster ", sort(unique(a$Meta_cluster)))
a$Meta <- factor(paste0("Meta-cluster ", a$Meta_cluster), levels = meta_levels)

p_a <- ggplot(a, aes(PC1, PC2)) +
  geom_point(aes(colour = Meta, size = Documents), alpha = 0.85) +
  geom_text_repel(aes(label = paste0("T", as.character(Topic))), family = FONT,
                  size = 2.6, box.padding = 0.35, point.padding = 0.25,
                  min.segment.length = 0, segment.size = 0.2, seed = 42) +
  scale_colour_manual(values = palette_for(length(meta_levels)), name = NULL) +
  scale_size_continuous(name = "Documents", range = c(2, 8)) +
  labs(x = "PC1", y = "PC2",
       title = "Meta-clusters of topics (Ward, k = 6)") +
  theme_paper()
save_panel(p_a, "Figure10A_meta_clusters", 7.4, 5.6)

# ------------------------------------------------------------------ panel B
drift_u <- read_table("Figure10B_drift_uniform.csv")
drift_s <- read_table("Figure10B_drift_semantic.csv")
events <- read_table("Figure10B_birth_death_uniform.csv")

drift_long <- rbind(
  data.frame(order = seq_len(nrow(drift_u)), transition = drift_u$transition,
             drift = drift_u$drift_index, cost = "Uniform cost (as published)"),
  data.frame(order = seq_len(nrow(drift_s)), transition = drift_s$transition,
             drift = drift_s$drift_index, cost = "Semantic cost")
)
drift_long$transition <- factor(drift_long$transition,
                                levels = unique(drift_u$transition))

p_b1 <- ggplot(drift_long, aes(order, drift, colour = cost)) +
  geom_line(linewidth = 0.5) +
  geom_point(size = 1.4) +
  scale_colour_manual(values = c("#08519C", "#D94801"), name = NULL) +
  scale_x_continuous(breaks = seq_len(nrow(drift_u)),
                     labels = drift_u$transition, expand = c(0.02, 0.02)) +
  labs(x = NULL, y = "Drift index", title = "Drift index across time bins") +
  theme_paper() +
  theme(axis.text.x = element_text(angle = 40, hjust = 1, size = 6.5),
        legend.position = "top",
        plot.margin = margin(5.5, 14, 5.5, 14))

if (nrow(events) > 0) {
  events$transition <- factor(paste(events$from_label, "to", events$to_label),
                              levels = unique(drift_u$transition))
  events$topic_label <- paste0("T", events$topic)
  p_b2 <- ggplot(events, aes(transition, topic_label, colour = event)) +
    geom_point(shape = 124, size = 4) +
    scale_colour_manual(values = c(birth = "#238B45", death = "#CB181D"),
                        name = NULL) +
    labs(x = "Time bin transition", y = "Topic",
         title = "Topic birth and death events") +
    theme_paper() +
    theme(axis.text.x = element_text(angle = 40, hjust = 1, size = 6.5),
          legend.position = "top",
          plot.margin = margin(5.5, 14, 5.5, 14))
} else {
  p_b2 <- ggplot() + theme_void() +
    labs(title = "No birth or death events at this threshold")
}

# Panels B1 and B2 are written as separate files so that the drift index and the
# lifecycle map can be placed independently.
save_panel(p_b1, "Figure10B1_drift_index", 8.2, 4.6)
save_panel(p_b2, "Figure10B2_birth_death", 8.2, 4.8)

# ------------------------------------------------------------------ panel C
c_df <- read_table("Figure10C_source_data.csv")
c_df$Significant <- as.character(c_df$Significant) == "True"
c_df$topic_label <- factor(paste0("T", c_df$Topic),
                           levels = paste0("T", c_df$Topic[order(c_df$Slope)]))
p_c <- ggplot(c_df, aes(Slope, topic_label, fill = Significant)) +
  geom_col(width = 0.65) +
  scale_fill_manual(values = c(`TRUE` = "#D94801", `FALSE` = "#BDBDBD"),
                    labels = c(`TRUE` = "Significant increase (P < 0.05)",
                               `FALSE` = "Not significant"),
                    name = NULL) +
  labs(x = "Annual slope (documents per year)", y = "Topic",
       title = "Annual trends of the valid topics") +
  theme_paper() +
  theme(legend.position = "top")
save_panel(p_c, "Figure10C_annual_slopes", 7.0, 5.2)

# ------------------------------------------------------------- panels D to G
dg <- read_table("Figure10DG_coupling_matrices.csv")
transitions <- unique(dg$transition)
chosen <- transitions[c(1, 4, length(transitions) - 1, length(transitions))]
chosen <- unique(chosen)
letters_dg <- c("D", "E", "F", "G")

for (i in seq_along(chosen)) {
  block <- dg[dg$transition == chosen[i], ]
  topics <- sort(unique(block$topic_from))
  block$from <- factor(paste0("T", block$topic_from), levels = rev(paste0("T", topics)))
  block$to <- factor(paste0("T", block$topic_to), levels = paste0("T", topics))
  diagonal <- sum(block$transport[block$topic_from == block$topic_to])
  p <- ggplot(block, aes(to, from, fill = transport)) +
    geom_tile(colour = "white", linewidth = 0.15) +
    scale_fill_gradientn(colours = c("#FFFFE5", "#C7E9B4", "#41B6C4", "#225EA8"),
                         name = "Transport") +
    labs(x = "Topic in the later bin", y = "Topic in the earlier bin",
         title = sprintf("Coupling matrix, %s (diagonal mass %.2f)",
                         chosen[i], diagonal)) +
    theme_paper() +
    theme(axis.text.x = element_text(angle = 90, hjust = 1, vjust = 0.5, size = 6),
          axis.text.y = element_text(size = 6))
  save_panel(p, paste0("Figure10", letters_dg[i], "_coupling_matrix"),
             6.4, 5.8)
}

# ------------------------------------------------------------------ panel H
h <- read_table("Figure10H_breakpoints.csv")
freq <- read_table("Figure10B_bin_frequencies.csv")
core <- h$topic

series <- do.call(rbind, lapply(core, function(topic) {
  column <- paste0("T", topic)
  if (!column %in% names(freq)) return(NULL)
  data.frame(Topic = paste0("T", topic),
             order = seq_len(nrow(freq)),
             value = freq[[column]] / mean(freq[[column]]))
}))
breaks <- data.frame(Topic = paste0("T", h$topic),
                     order = match(h$bai_perron_break_midpoint,
                                   freq$midpoint, nomatch = NA))

p_h <- ggplot(series, aes(order, value)) +
  geom_line(colour = "#08519C", linewidth = 0.5) +
  geom_point(colour = "#08519C", size = 1.1) +
  geom_vline(data = breaks, aes(xintercept = order), linetype = "dashed",
             colour = "#CB181D", linewidth = 0.4, na.rm = TRUE) +
  facet_wrap(~Topic, nrow = 1, scales = "free_y") +
  scale_x_continuous(breaks = seq_len(nrow(freq))) +
  labs(x = "Time bin", y = "Relative frequency",
       title = "Breakpoint tests for the five core topics (dashed line, Bai-Perron break)") +
  theme_paper() +
  theme(axis.text.x = element_text(size = 6),
        strip.text = element_text(face = "bold", family = FONT))
save_panel(p_h, "Figure10H_breakpoints", 9.0, 3.8)

message("all Figure 10 panels written to ", output_dir)
