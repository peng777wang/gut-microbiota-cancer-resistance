# =============================================================================
# Figure 6A - MCA conceptual structure map (biblioshiny / bibliometrix)
#
# Verified on 2026-09-14 with bibliometrix 5.5.0 under R 4.5.2: this script
# reproduces the published panel exactly (Dim1 = 73.06%, Dim2 = 19.51%, the
# same 26 terms and the same four clusters).
#
# Two details of the biblioshiny interface are reproduced here explicitly:
#   1. "Number of Terms" in the interface is NOT a term count passed to
#      bibliometrix. biblioshiny converts it into minDegree, the frequency of
#      the term at that rank: minDegree <- as.numeric(tableTag(...)[n]).
#      Ranks 25 and 26 both occur 97 times, so a request of 25 or 26 both give
#      minDegree = 97 and retain 26 terms.
#   2. The label size entered in the interface (6) is halved before being
#      passed to conceptualStructure (labelsize = CSlabelsize / 2).
# =============================================================================

suppressPackageStartupMessages(library(bibliometrix))  # 5.5.0

corpus_file <- "C:/Users/19565/Documents/Codex/2026-09-06/x20/outputs/Merged_corpus_strict_FINAL.txt"
stop_file   <- "C:/Users/19565/Documents/Codex/2026-09-06/x20/outputs/Stopwords_22_lines.txt"
out_dir     <- "C:/Users/19565/Documents/Codex/2026-09-14/codex-threads-01a08a08-4cad-7640-a664-3/outputs"

# --- data -------------------------------------------------------------------
M <- convert2df(corpus_file, dbsource = "wos", format = "plaintext")
stopwords <- trimws(readLines(stop_file))
stopwords <- stopwords[nchar(stopwords) > 0]           # 22 generic terms

# --- interface conversion: "Number of Terms" -> minDegree -------------------
tab <- tableTag(
  M[!duplicated(M$SR), ],
  Tag = "KW_Merged", sep = ";", ngrams = 1, remove.terms = stopwords
)
number_of_terms <- 26                                  # 25 gives the same result
min_degree <- as.numeric(tab[number_of_terms])         # -> 97

# --- conceptual structure map ----------------------------------------------
CS <- conceptualStructure(
  M,
  method      = "MCA",            # interface: Method
  field       = "KW_Merged",      # interface: Field = All Keywords
  minDegree   = min_degree,       # 97
  clust       = "4",              # interface: N. of Clusters
  k.max       = 8,                # fixed by biblioshiny
  stemming    = FALSE,
  labelsize   = 6 / 2,            # interface: Label Size 6
  documents   = 5,                # interface: Num. of Documents
  graph       = FALSE,
  remove.terms = stopwords,       # interface: stopword file
  synonyms    = NULL              # interface: synonyms not loaded
)

CS$res$eigCorr$perc[1:2]                               # 73.06 19.51

# --- terms by cluster -------------------------------------------------------
dc  <- CS$km.res$data.clust
grp <- dc[[ncol(dc)]]
words <- data.frame(word = rownames(dc), cluster = grp)
words <- words[order(words$cluster, words$word), ]
print(table(words$cluster))

write.csv(
  words,
  file.path(out_dir, "Figure6A_MCA_words_by_cluster.csv"),
  row.names = FALSE
)
