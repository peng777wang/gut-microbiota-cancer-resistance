# ============================================================================
# Supplementary Script 1
# Cross-database merging and deduplication of Web of Science Core Collection and
# Scopus records for the bibliometric corpus of gut microbiota research in
# cancer therapy resistance.
#
# Deduplication rule (deterministic, applied to the merged stack):
#   Stage 1  exact match on the Digital Object Identifier (DOI) after
#            normalisation to lower case and removal of any DOI prefix
#   Stage 2  for records without a usable DOI, match on the normalised title
#            (lower case, alphanumeric only)
#   WoS records are added to the registry first, so WoS wins on a duplicate.
#
# R packages required: stringdist is NOT required for this rule.
# All parsing is done with base R; data.table is used only to read the Scopus
# CSV (which contains multi-line quoted fields).
# R version of the analysis reported in the manuscript: 4.5.2.
#
# Usage:
#   Rscript Supplementary_Script_1_dedup.R [WoS_file] [Scopus_file] [output_dir]
# If no arguments are supplied the placeholder paths below are used.
# ============================================================================

suppressMessages(require(data.table, quietly = TRUE))

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
args <- commandArgs(trailingOnly = TRUE)
wos_file    <- if (length(args) >= 1) args[1] else "C:/path/to/WoS_collection.txt"
scopus_file <- if (length(args) >= 2) args[2] else "C:/path/to/Scopus.csv"
out_dir     <- if (length(args) >= 3) args[3] else "C:/path/to/output"
# ----------------------------------------------------------------------------

dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

`%||%` <- function(a, b) if (isTRUE(is.null(a)) || isTRUE(length(a) == 0) || isTRUE(is.na(a[1]))) b else a

## ---- 1. Web of Science field-tagged plain text parser -----------------------
## Each record ends with an "ER" line; field tags are two characters at the
## start of a line (e.g. "DI ", "TI ", "PY ", "AU ") and continuation lines
## start with spaces.
read_wos <- function(file) {
  lines <- readLines(file, warn = FALSE, encoding = "UTF-8")
  recs <- list(); idx <- 0L; cur <- list(); curtag <- NULL
  for (ln in lines) {
    if (grepl("^ER", ln)) {
      if (length(cur)) { idx <- idx + 1L; recs[[idx]] <- cur }
      cur <- list(); curtag <- NULL
      next
    }
    m <- regexec("^([A-Z][A-Z0-9]) (.*)$", ln)
    parts <- regmatches(ln, m)[[1]]
    if (length(parts) >= 3) {
      curtag <- parts[2]
      cur[[curtag]] <- c(cur[[curtag]], trimws(parts[3]))
    } else if (!is.null(curtag)) {
      cur[[curtag]] <- c(cur[[curtag]], trimws(ln))
    }
  }
  getf <- function(r, tag) if (!is.null(r[[tag]])) paste(r[[tag]], collapse = " ") else ""
  data.frame(ID = paste0("W_", seq_along(recs)),
             DOI = vapply(recs, getf, "", "DI"),
             TI  = vapply(recs, getf, "", "TI"),
             PY  = vapply(recs, getf, "", "PY"),
             SRC = "WoS", stringsAsFactors = FALSE)
}

## ---- 2. Scopus CSV parser ---------------------------------------------------
## data.table::fread handles the byte-order mark and multi-line quoted fields.
read_scopus <- function(file) {
  d <- as.data.frame(data.table::fread(file, data.table = FALSE, encoding = "UTF-8", showProgress = FALSE), stringsAsFactors = FALSE)
  data.frame(ID = paste0("S_", seq_len(nrow(d))),
             DOI = if ("DOI"   %in% names(d)) d$DOI   %||% "" else "",
             TI  = if ("Title" %in% names(d)) d$Title %||% "" else "",
             PY  = if ("Year"  %in% names(d)) d$Year  %||% "" else "",
             SRC = "Scopus", stringsAsFactors = FALSE)
}

## ---- 3. Load -----------------------------------------------------------------
wos <- read_wos(wos_file)
sco <- read_scopus(scopus_file)
dat <- rbind(wos, sco)                       # WoS first, so WoS wins on a tie
cat("WoS records:", nrow(wos),
    "| Scopus records:", nrow(sco),
    "| total:", nrow(dat), "\n")

## ---- 4. Normalise matching keys ----------------------------------------------
norm_title <- function(x) tolower(gsub("[^a-zA-Z0-9]", "", x))
dat$DOI     <- tolower(gsub("^https?://(dx\\.)?doi\\.org/", "", trimws(dat$DOI)))
dat$title   <- norm_title(dat$TI)
dat$doi_key <- ifelse(dat$DOI != "", dat$DOI, NA_character_)

## ---- 5. Deduplicate: DOI, then normalised title, WoS precedence -------------
seen <- new.env(parent = emptyenv())
is_dup <- logical(nrow(dat))
for (i in seq_len(nrow(dat))) {
  k <- if (!is.na(dat$doi_key[i])) dat$doi_key[i] else paste0("T:", dat$title[i])
  if (exists(k, envir = seen)) is_dup[i] <- TRUE else assign(k, i, envir = seen)
}

## ---- 6. Results ---------------------------------------------------------------
kept <- dat[!is_dup, ]
dups <- dat[is_dup, ]
cat("\nKept (merged, unique) records:", nrow(kept), "\n")
cat("Duplicate records removed:", nrow(dups), "\n")

keep_cols <- c("ID", "SRC", "DOI", "TI", "PY")
write.csv(kept[, keep_cols], file.path(out_dir, "merged_unique.csv"), row.names = FALSE)
write.csv(dups[, keep_cols], file.path(out_dir, "duplicates_removed.csv"), row.names = FALSE)
cat("Outputs written to:", out_dir, "\n")
# ----------------------------------------------------------------------------
# END
# ----------------------------------------------------------------------------
