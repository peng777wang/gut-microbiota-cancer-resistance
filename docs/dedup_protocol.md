# Deduplication: rule, audit trail and what is (and is not) verified

## Rule applied

The WoSCC and Scopus exports were stacked and deduplicated with a deterministic two-stage
rule, implemented in `code/01_deduplication.R`:

1. exact match on the DOI;
2. for records without a usable DOI, match on the normalised title (case-folded, punctuation
   and whitespace removed).

Where the two sources described the same publication but disagreed on bibliographic
detail, the WoSCC record was retained. The rule removed 682 duplicates - 681 pairs matched
on DOI and one pair on normalised title - leaving 1,532 unique records (978 WoSCC + 1,236
Scopus).

## Audit trail

Every decision is recorded at record level, so the outcome of the rule can be audited
without re-running the databases:

| File | Content |
| --- | --- |
| `data_derived/dedup_decisions_retained_1532.csv` | the records kept, with source and match rule |
| `data_derived/dedup_decisions_removed_682.csv` | the records discarded, with the record they were matched to and the rule applied |

## Verification status

The duplicate decisions are fully documented by the two audit files above and can be
re-derived from them mechanically. An independent blinded verification of a random sample
of the matched and discarded pairs was set up but is **not** reported in this version of
the package: no second-assessor judgements are included here. The manuscript therefore
makes no claim of a completed second-assessor check for the deduplication step; the
evidence offered is the record-level decision table, which is complete for all 2,214
retrieved records.
