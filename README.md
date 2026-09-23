# Reproducibility package

**From describing microbes to designing interventions: a bibliometric study of gut
microbiota research in cancer therapy resistance (2016 - 2025)**
Frontiers in Immunology - revised submission

Archived on Zenodo: https://doi.org/10.5281/zenodo.22811196 (concept DOI, always resolves to
the latest version). The version accompanying the manuscript is v1.0.3, archived under its own
version DOI: https://doi.org/10.5281/zenodo.22921458.

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

## Provenance of the figures

Figures 3 to 8 were produced with graphical applications. The tool is identified panel by
panel, as it appears in the exported figures:

| Panel | Tool | Analysis |
| --- | --- | --- |
| Figure 3A-3D | biblioshiny (bibliometrix 5.5.0) | author, country and affiliation productivity over time; Lotka's law fit |
| Figure 4A | VOSviewer 1.6.20 | keyword co-occurrence network (40 keywords, minimum link strength 65) |
| Figure 4B-4D | CiteSpace 7.0.R0 | keyword burst detection, keyword clustering, timeline view |
| Figure 5A-5C | VOSviewer 1.6.20 | author, country and institution co-authorship, computed separately for WoSCC and Scopus |
| Figure 5D | CiteSpace 7.0.R0 | dual-map overlay of citing and cited journals |
| Figure 6A | biblioshiny (bibliometrix 5.5.0) | multiple correspondence analysis (Dim1 73.06%, Dim2 19.51%) |
| Figure 6B-6D | VOSviewer 1.6.20 | author, source and reference co-citation networks |
| Figure 7A-7D | biblioshiny (bibliometrix 5.5.0) | three-field plot, thematic evolution, thematic map, trend topics |
| Figure 8A | biblioshiny statistics, redrawn in R | ten most cited documents, bubble chart |
| Figure 8B | CiteSpace 7.0.R0 | reference burst detection |

Because CiteSpace requires records in Web of Science format, the Scopus export was converted
to WoS format and merged with the WoSCC export before import, so the keyword analyses
(Fig. 4B-4D) use the merged corpus of 1,532 records. The co-citation networks of
Fig. 6B-6D use the WoSCC subset of 978 records; the database behind each analysis is listed
in Supplementary Table 4. VOSviewer and biblioshiny were run on the merged corpus.

These applications do not produce a batch script, so for those panels reproducibility rests
on three things: the corpus is rebuilt exactly as above, the parameter settings are listed
in Supplementary Tables 4, 5 and 17-18, and the node and edge tables exported by the tools
are reproduced from the same corpus.

For two of those panels we additionally provide scripts that re-derive the published output
from the corpus:

- `code/07_mca_figure6a.R` reproduces Figure 6A, the multiple correspondence analysis
  (Dim1 = 73.06%, Dim2 = 19.51%, the same 26 terms and the same four clusters), including
  the two interface conventions that biblioshiny applies internally.
- `code/06_figure8a_bubble.R` reproduces the Figure 8A bubble chart using the same
  normalisation that biblioshiny uses for Normalized TC (`TC / mean(TC)` within publication
  year) and the same `TC per year = TC / (y + 1 - PY)` convention.

## Relation to the manuscript

| Manuscript item | How it was produced | Where it is documented here |
| --- | --- | --- |
| Table 1 | counts from the merged corpus | `data_derived/table1_countries.csv` |
| Table 4 | linear regression of annual topic frequency on year | `code/08_table4_topic_trends.py` -> `data_derived/table4_*.csv` |
| Figure 2A | annual output of the three series | `data_derived/annual_output_by_database.csv` |
| Figure 2B | mean citations per article and citable years | `data_derived/average_citations_per_article.csv` |
| Figure 2C, and the R2 values in Results 3.1 | cubic `lm()` fit on Year - 2016 | `code/11_growth_curve_fits.R` (original) + `code/11_growth_curve_fits_check.py` -> `data_derived/growth_curve_fits.csv` |
| Figure 2D, 2E | country and institution counts | `data_derived/table1_countries.csv`, `data_derived/figure2e_institutions.csv` |
| Figure 3 | biblioshiny (author, institution and country indicators, Lotka fit) | Supplementary Table 18 |
| Figure 4 | CiteSpace keyword co-occurrence, bursts and clustering on the WoSCC subset | Supplementary Table 5 |
| Figure 5 | VOSviewer collaboration networks, plus the CiteSpace dual-map overlay | Supplementary Table 5 |
| Figure 6A | bibliometrix MCA | `code/07_mca_figure6a.R` |
| Figure 6B-6D | biblioshiny co-citation network | Supplementary Table 18 |
| Figure 7 | biblioshiny thematic map and thematic evolution | Supplementary Table 18 |
| Figure 8A | bubble chart of the ten most cited documents | `code/06_figure8a_bubble.R` |
| Figure 8B | CiteSpace reference burst detection | Supplementary Table 5, block B |
| Figure 9 | BERTopic topic model | `code/02_bertopic_pipeline.py` + `code/03_bertopic_figures.R` |
| Figure 10 | D3TEM dynamic-evolution framework | `code/04_d3tem_pipeline.py` + `code/05_d3tem_figures.R` |
| Table 5 and Section 4.4 | PubMed clinical trial search | `code/S1_Search_Strategy.docx`; screening recorded in Table 5 |
| Supplementary Tables 6-9 | BERTopic supplement | `code/10_bertopic_supplement.py` |
| Supplementary Tables 10-13 | D3TEM supplement | `code/09_d3tem_supplement.py` |
| Supplementary Tables 14-16 | quality and relevance assessment | `docs/quality_relevance_*`, `code/12_inter_rater_reliability.py` |
| Supplementary Tables 1-5, 17, 18 | search strings and tool parameters | `code/S1_Search_Strategy.docx`, `data_derived/stopwords_22.txt` |
| Methods 2.1 deduplication | DOI then normalised title, WoSCC precedence | `code/01_deduplication.R` + `data_derived/dedup_decisions_*.csv` + `docs/dedup_protocol.md` |

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

`v1.0.3` accompanies the revised manuscript. It adds a software version report generated
inside the analysis environment actually used for the topic model and the D3TEM analysis
(hdbscan 0.8.44, POT 0.9.7.post1, statsmodels 0.15.0), an updated D3TEM supplementary methods
document, and the correspondingly updated checksum manifest, and it updates the repository
title. `v1.0.2` was identical in content to `v1.0.1` and only triggered archiving. `v1.0.1`
corrected the bin labels in the D3TEM drift and coupling tables, cleaned the Unicode escapes
in the deduplication audit tables, and added the document-type breakdown and the full citation
ranking of the corpus. Every change is recorded in the release notes; please cite the version
DOI.

## Licence

Code: MIT (`LICENSE`). Derived data, metadata and documentation: CC BY 4.0. Raw database
records are not redistributed.

## Contact

Corresponding authors: Jianlei An and Guogui Sun (see the manuscript for e-mail addresses).
