# Quality and topical-relevance assessment: protocol and reliability

This note documents how the inter-rater reliability figures reported in Methods 2.6 and
Supplementary Tables 14-16 of the manuscript were produced. The instruments as returned
by each rater are in this folder (`rating_form_reviewer_1.xlsx` to
`rating_form_reviewer_3.xlsx`), the record list is in
`quality_relevance_sampling_key.csv`, and the computed statistics are in
`quality_relevance_results.xlsx`.

## Framework

Each record received one methodological-quality grade and one topical-relevance level,
defined operationally in `quality_relevance_framework.docx` (Supplementary Table 14):

- Quality: A (high), B (moderate), C (low)
- Relevance: relevant, partially relevant, irrelevant

## Sampling

- Sampling frame: the 1,532 deduplicated records of the final corpus.
- Design: stratified random sample of 10% of the corpus, stratified by publication year;
  n = 153 records (random seed 20260917).
- Calibration: an additional 50-record pilot set was rated first and discussed before the
  main assessment.
- Identifiers: records were handed to the raters under de-identified sample IDs
  (M001-M153 for the main sample, P01-P50 for the pilot set); the mapping back to the
  corpus is in `quality_relevance_sampling_key.csv`.

## Raters

Three researchers rated the same records independently. Each rater received the same
rubric and the same truncated record metadata, and no rater saw the other raters'
judgements or any topic-model or bibliometric output.

## Agreement

| Quantity | Value |
| --- | --- |
| Fleiss' kappa, quality (pilot, n = 50) | 0.649 |
| Fleiss' kappa, relevance (pilot, n = 50) | 0.672 |
| Fleiss' kappa, quality (main, n = 153) | 0.784 (95% CI 0.685-0.867) |
| Fleiss' kappa, relevance (main, n = 153) | 0.775 (95% CI 0.704-0.843) |
| Pairwise agreement, quality | 91.7% |
| Pairwise agreement, relevance | 88.2% |
| Unanimous records, quality | 87.6% |
| Unanimous records, relevance | 82.4% |
| Gwet's AC1, quality | 0.898 (95% CI 0.850-0.940) |
| Gwet's AC1, relevance | 0.841 (95% CI 0.783-0.896) |
| Records with any disagreement (either dimension) | 43 |

## Distribution of the ratings

| Quality level | n | % |
| --- | --- | --- |
| A | 28 | 18.3 |
| B | 117 | 76.5 |
| C | 8 | 5.2 |

| Relevance level | n | % |
| --- | --- | --- |
| Relevant | 95 | 62.1 |
| Partially relevant | 45 | 29.4 |
| Irrelevant | 13 | 8.5 |

## Handling of disagreements

All 43 records with any disagreement had a 2:1 majority in both dimensions and were
resolved by majority vote; the individual ratings for those records are listed in the
`Disagreements` sheet of `quality_relevance_results.xlsx`.

Gwet's AC1 is reported alongside Fleiss' kappa because the corpus is intentionally narrow
and most records fall into the "B" and "relevant" categories, which attenuates kappa.

## Recomputing these values

`code/12_inter_rater_reliability.py` recomputes every value in the table above from the
three returned rating forms and writes `inter_rater_reliability_recomputed.csv`. The point
estimates reproduce exactly (kappa 0.784 and 0.775; AC1 0.898 and 0.841; pairwise agreement
91.7% and 88.2%; unanimity 87.6% and 82.4%). The bootstrap confidence bounds are
resampling-dependent: the script uses 2,000 resamples with seed 20260917, and a different
seed moves the bounds by less than 0.01.
