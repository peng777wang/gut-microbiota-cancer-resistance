# Reproducibility package

**From describing microbes to designing interventions: the ten-year evolution of gut
microbiota research in cancer therapy resistance**
Frontiers in Immunology - revised submission

This repository contains the code, the derived data and the documentation needed to
reproduce the corpus, the topic model, the D3TEM dynamic-evolution analysis and the
quality/relevance assessment reported in the manuscript.

It does **not** contain the raw Web of Science Core Collection (WoSCC) or Scopus records,
because those records are subject to database licensing terms. The identifiers needed to
re-retrieve every record are provided instead (`data_derived/record_dois_1532.csv`,
`data_derived/records_without_doi.csv`) together with the verbatim search strings
(`code/S1_Search_Strategy.docx`).

## Repository layout

```
code/
  01_deduplication.R              cross-database merge and deduplication (WoSCC + Scopus)
  02_bertopic_pipeline.py         BERTopic fit, 13-configuration sensitivity grid, outlier reallocation
  03_bertopic_figures.R           Figure 9 panels
  04_d3tem_pipeline.py            D3TEM: Ward meta-clustering, entropic optimal transport, drift index, breakpoints
  05_d3tem_figures.R              Figure 10 panels
  06_figure8a_bubble.R            Figure 8A rebuild from the corpus
  07_mca_figure6a.R               Figure 6A (multiple correspondence analysis)
  08_table4_topic_trends.py       Table 4 and the annual topic-count matrix
  09_d3tem_supplement.py          Supplementary Tables 10-13 (D3TEM)
  10_bertopic_supplement.py       Supplementary Tables 6-9 (BERTopic)
  11_growth_curve_fits.R          original R script: cubic growth-curve fits and Figure 2C
  11_growth_curve_fits_check.py   R-free recomputation of the same fits (numpy)
  12_inter_rater_reliability.py   Fleiss' kappa, Gwet's AC1 and agreement rates
  S1_Search_Strategy.docx         verbatim search strings (Supplementary Table 1)

data_derived/
  record_dois_1532.csv            DOI of each of the 1,522 records that carry one
  records_without_doi.csv         the 10 records without a DOI (title, year, source)
  dedup_decisions_retained_1532.csv   per-record record of what was kept and why
  dedup_decisions_removed_682.csv     per-record record of what was discarded and on which rule
  topic_assignments_1532.csv      topic assignment of every document
  topic_info.csv                  topic sizes, c-TF-IDF top terms, representative documents
  topic_topwords.csv              ten highest-weighted terms per topic
  topic_trends.csv, table4_topic_trends.csv, table4_annual_topic_counts.csv
  bertopic_sensitivity_grid.csv, bertopic_sensitivity_topic_stability.csv
  outlier_reallocation.csv, outlier_topic_report.txt
  d3tem_meta_clusters.csv         Ward meta-cluster membership (k = 6)
  d3tem_drift_uniform.csv, d3tem_drift_semantic.csv
  d3tem_birth_death_uniform.csv, d3tem_annual_slopes.csv, d3tem_breakpoints.csv
  d3tem_sensitivity_grid.csv      the 11 D3TEM configurations
  table1_countries.csv            country output and SCP/MCP counts (Table 1)
  annual_output_by_database.csv   annual output of WoSCC, Scopus and the merged corpus (Figure 2A)
  average_citations_per_article.csv  mean citations per article and citable years (Figure 2B)
  figure2e_institutions.csv       top ten institutions by output (Figure 2E)
  growth_curve_fits.csv           cubic coefficients and R2 produced by code/11
  keyword_cooccurrence_table.csv, stopwords_22.txt
  bertopic_parameters.md, software_versions_bertopic.txt

docs/
  quality_relevance_framework.docx    the three-tier grading rubric (Supplementary Table 14)
  rating_form_reviewer_1.xlsx         the instrument as returned by each of the three raters
  rating_form_reviewer_2.xlsx
  rating_form_reviewer_3.xlsx
  quality_relevance_sampling_key.csv  the 153 sampled records and the 50 pilot records (de-identified IDs)
  quality_relevance_results.xlsx      kappa, AC1, agreement and the disagreement table
  inter_rater_reliability.md          protocol and outcome of the reliability assessment
  inter_rater_reliability_recomputed.csv  output of code/12
  dedup_protocol.md                   deduplication rule and the audit trail
  supplementary_methods_bertopic.docx supplementary Methods for the topic model
  supplementary_methods_d3tem.docx    supplementary Methods for the D3TEM framework
```

## How to reproduce

The scripts run in the order below. Scripts 02-10 were written against the original working
directories of the study, so their path constants at the top of each file (for example
`OUT_DIR`) must be pointed at your own export and output folders before they are run;
scripts 11 and 12 read straight from this repository and need no editing.

1. Re-run the searches in Web of Science Core Collection and Scopus with the verbatim
   strings in `code/S1_Search_Strategy.docx` (filters: 2016-2025, English, Article or
   Review; search date 6 September 2026). Export full records with cited references in WoS
   format and convert the Scopus export to the same format.
2. Deduplicate with `code/01_deduplication.R` (exact DOI, then normalised title; the WoSCC
   record is kept when the two sources disagree). Expected output: 1,532 unique records
   (978 WoSCC + 1,236 Scopus - 682 duplicates).
3. Fit the topic model with `code/02_bertopic_pipeline.py` on the 1,532 records. Expected
   output: 12 topics, 11 retained, 341 documents (22.3%) unassigned, 1,191 documents in
   the topic-level analyses.
4. Run `code/04_d3tem_pipeline.py` on the topic-level c-TF-IDF vectors (calendar-year bins,
   uniform and semantic cost matrices). Expected output: drift index 0.322 -> 0.106 ->
   0.152 across the nine transitions; 25 births and 13 deaths.
5. Recreate the figures and tables with `code/03_bertopic_figures.R`,
   `code/05_d3tem_figures.R`, `code/06_figure8a_bubble.R`, `code/07_mca_figure6a.R`,
   `code/08_table4_topic_trends.py`, `code/09_d3tem_supplement.py` and
   `code/10_bertopic_supplement.py`.
6. Regenerate Figure 2C with `code/11_growth_curve_fits.R` (tidyverse), which fits
   `lm(y ~ poly(Year - 2016, 3))` for each of the three series and draws the annotated
   panel. `code/11_growth_curve_fits_check.py` recomputes the same least-squares estimates
   without R and asserts them against the reported values (0.9396 WoSCC, 0.9697 Scopus,
   0.9593 merged corpus).
7. Recompute the inter-rater reliability statistics with
   `code/12_inter_rater_reliability.py` (needs `openpyxl`), or follow
   `docs/inter_rater_reliability.md`.

CiteSpace (7.0.R0) and VOSviewer (1.6.20) are graphical tools; their parameter settings
are documented in Supplementary Tables 4 and 5, and the network inputs they consume are
reproduced from the exports described above.

## Relation to the manuscript

| Manuscript item | Reproduced from |
| --- | --- |
| Table 1 | `data_derived/table1_countries.csv` |
| Table 4 | `code/08_table4_topic_trends.py` -> `data_derived/table4_*.csv` |
| Figures 2, 3, 5 | bibliometrix statistics plus the annual, per-country and per-author counts in `data_derived/` |
| Figure 4 | CiteSpace keyword analysis of the WoSCC subset (Supplementary Table 5) |
| Figure 6 | `code/07_mca_figure6a.R` |
| Figure 7 | bibliometrix thematic map and thematic evolution (Supplementary Table 18) |
| Figure 8A, 8B | `code/06_figure8a_bubble.R`; reference burst detection in CiteSpace (Supplementary Table 5, block B) |
| Figure 9 | `code/02_bertopic_pipeline.py` + `code/03_bertopic_figures.R` |
| Figure 10 | `code/04_d3tem_pipeline.py` + `code/05_d3tem_figures.R` |
| Supplementary Tables 6-9 | `code/10_bertopic_supplement.py` |
| Supplementary Tables 10-13 | `code/09_d3tem_supplement.py` |
| Supplementary Tables 14-16 | `docs/quality_relevance_*` |
| Figure 2A | `data_derived/annual_output_by_database.csv` |
| Figure 2B | `data_derived/average_citations_per_article.csv` |
| Figure 2C and the R2 values in Results 3.1 | `code/11_growth_curve_fits.R` (original) + `code/11_growth_curve_fits_check.py` -> `data_derived/growth_curve_fits.csv` |
| Methods 2.6 reliability statistics | `code/12_inter_rater_reliability.py` -> `docs/inter_rater_reliability_recomputed.csv` |
| Methods 2.1 deduplication | `code/01_deduplication.R` + `data_derived/dedup_decisions_*.csv` + `docs/dedup_protocol.md` |

## Software

- Python 3.12.10 with bertopic 0.17.4, sentence-transformers 6.0.1, transformers 5.17.0,
  umap-learn 0.5.12, hdbscan 0.8.44, scikit-learn 1.9.1, POT 0.9.7, statsmodels 0.15.0,
  numpy 2.5.3, pandas 3.0.5, scipy 1.18.1
- R 4.5.2 with bibliometrix 5.5.0, ggplot2, patchwork, RColorBrewer, ggrepel
- CiteSpace 7.0.R0 and VOSviewer 1.6.20 (graphical)
- Python scripts 11 and 12 additionally need numpy and openpyxl

Exact versions of the Python topic-modelling stack are also listed in
`data_derived/software_versions_bertopic.txt`.

## Version

`v1.0` accompanies the revised manuscript. Any later change is recorded in the release
notes; please cite the version DOI.

## Licence

Code: MIT (`LICENSE`). Derived data, metadata and documentation: CC BY 4.0. Raw database
records are not redistributed.

## Contact

Corresponding authors: Jianlei An and Guogui Sun (see the manuscript for e-mail addresses).
