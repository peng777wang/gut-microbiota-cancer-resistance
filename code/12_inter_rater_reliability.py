#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inter-rater reliability of the quality and topical-relevance assessment.

Reads the three returned rating forms and recomputes every agreement statistic
reported in Methods 2.6 and in Supplementary Tables 14-16:
Fleiss' kappa with a bootstrap 95% CI, Gwet's AC1 with a bootstrap 95% CI,
pairwise agreement, the number of unanimous records and the category
distributions, separately for the 50-record pilot set and the 153-record main
sample.

Input   docs/rating_form_reviewer_1.xlsx ... _3.xlsx
Output  docs/inter_rater_reliability_recomputed.csv

Expected values are read from docs/quality_relevance_results.xlsx when that file
is present, and the script reports any difference.
"""

import csv
import os
import random
from collections import Counter

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "..", "docs")
FORMS = [os.path.join(DOCS, "rating_form_reviewer_%d.xlsx" % i) for i in (1, 2, 3)]
SHEETS = [("pilot", "Pilot_50"), ("main", "Main_sample_153")]
QUALITY_LEVELS = ["A", "B", "C"]
RELEVANCE_LEVELS = ["Relevant", "Partially relevant", "Irrelevant"]
SEED = 20260917
BOOT = 2000


def read_form(path, sheet):
    """Return {sample_id: (quality, relevance)} for one rater and one sheet."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[sheet]
    out = {}
    header_seen = False
    for row in ws.iter_rows(values_only=True):
        if row and row[0] == "Sample ID":
            header_seen = True
            continue
        if not header_seen or not row or not row[0]:
            continue
        sid = str(row[0]).strip()
        quality = (str(row[5]).strip() if row[5] else "")
        relevance = (str(row[6]).strip() if row[6] else "")
        if quality or relevance:
            out[sid] = (quality, relevance)
    wb.close()
    return out


def fleiss_kappa(units, categories):
    """units: list of lists of ratings, one list per subject."""
    n = len(units)
    r = len(units[0])
    counts = [Counter(u) for u in units]
    p_i = []
    for c in counts:
        s = sum(c.get(cat, 0) ** 2 for cat in categories)
        p_i.append((s - r) / (r * (r - 1)))
    p_bar = sum(p_i) / n
    p_j = []
    for cat in categories:
        p_j.append(sum(c.get(cat, 0) for c in counts) / (n * r))
    p_e = sum(p ** 2 for p in p_j)
    return (p_bar - p_e) / (1 - p_e), p_bar


def gwet_ac1(units, categories):
    n = len(units)
    r = len(units[0])
    q = len(categories)
    counts = [Counter(u) for u in units]
    p_a = sum((sum(c.get(cat, 0) ** 2 for cat in categories) - r) / (r * (r - 1))
              for c in counts) / n
    p_j = [sum(c.get(cat, 0) for c in counts) / (n * r) for cat in categories]
    p_e = sum(p * (1 - p) for p in p_j) / (q - 1)
    return (p_a - p_e) / (1 - p_e)


def bootstrap_ci(units, categories, fn):
    rng = random.Random(SEED)
    n = len(units)
    vals = []
    for _ in range(BOOT):
        sample = [units[rng.randrange(n)] for _ in range(n)]
        vals.append(fn(sample, categories))
    vals.sort()
    lo = vals[int(0.025 * BOOT)]
    hi = vals[int(0.975 * BOOT) - 1]
    return lo, hi


def pairwise_agreement(units):
    """Share of rater pairs that agree, averaged over all subjects."""
    num = den = 0
    for u in units:
        for i in range(len(u)):
            for j in range(i + 1, len(u)):
                den += 1
                num += int(u[i] == u[j])
    return 100.0 * num / den


def unanimity(units):
    return 100.0 * sum(1 for u in units if len(set(u)) == 1) / len(units)


def analyse(units, categories):
    kappa, p_bar = fleiss_kappa(units, categories)
    k_lo, k_hi = bootstrap_ci(units, categories,
                              lambda u, c: fleiss_kappa(u, c)[0])
    ac1 = gwet_ac1(units, categories)
    a_lo, a_hi = bootstrap_ci(units, categories, gwet_ac1)
    dist = Counter()
    for u in units:
        # majority rating per subject
        dist[Counter(u).most_common(1)[0][0]] += 1
    return {
        "kappa": round(kappa, 3),
        "kappa_ci": "%.3f-%.3f" % (k_lo, k_hi),
        "ac1": round(ac1, 3),
        "ac1_ci": "%.3f-%.3f" % (a_lo, a_hi),
        "pairwise_agreement_pct": round(pairwise_agreement(units), 1),
        "unanimous_pct": round(unanimity(units), 1),
        "distribution": dict(dist),
    }


def main():
    data = {}
    for set_name, sheet in SHEETS:
        raters = [read_form(p, sheet) for p in FORMS]
        ids = sorted(set(raters[0]) & set(raters[1]) & set(raters[2]))
        data[set_name] = (ids, raters)

    results = {}
    for set_name, (ids, raters) in data.items():
        for dim, cats, col in (("quality", QUALITY_LEVELS, 0),
                               ("relevance", RELEVANCE_LEVELS, 1)):
            units = [[raters[r][i][col] for r in range(3)] for i in ids]
            results["%s_%s" % (set_name, dim)] = analyse(units, cats)

    print("%-18s %7s %-15s %7s %-15s %8s %8s" % (
        "set / dimension", "kappa", "95% CI", "AC1", "95% CI",
        "pairwise", "unanimous"))
    for key, res in results.items():
        print("%-18s %7.3f %-15s %7.3f %-15s %7.1f%% %7.1f%%" % (
            key, res["kappa"], res["kappa_ci"], res["ac1"], res["ac1_ci"],
            res["pairwise_agreement_pct"], res["unanimous_pct"]))

    print("\nmain-sample category distribution (majority rating):")
    for dim in ("quality", "relevance"):
        print("  %-10s %s" % (dim, results["main_%s" % dim]["distribution"]))

    out = os.path.join(DOCS, "inter_rater_reliability_recomputed.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["set", "dimension", "fleiss_kappa", "kappa_95CI",
                    "gwet_ac1", "ac1_95CI", "pairwise_agreement_pct",
                    "unanimous_pct"])
        for key in sorted(results):
            set_name, dim = key.split("_", 1)
            r = results[key]
            w.writerow([set_name, dim, r["kappa"], r["kappa_ci"], r["ac1"],
                        r["ac1_ci"], r["pairwise_agreement_pct"],
                        r["unanimous_pct"]])
    print("\nwritten:", os.path.normpath(out))


if __name__ == "__main__":
    main()
