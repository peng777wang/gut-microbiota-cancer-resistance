#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Independent check of the cubic growth-curve fits behind Figure 2C.

The fits were produced by `11_growth_curve_fits.R` (R lm() on a cubic polynomial
of Year - 2016). This script recomputes the same least-squares estimates from
`data_derived/annual_output_by_database.csv` with numpy, so that the reported
coefficients and R2 values can be verified without an R installation.

Input   data_derived/annual_output_by_database.csv
Output  data_derived/growth_curve_fits.csv

Expected values (as printed in Figure 2C of the manuscript):
  WoSCC           y = 0.6599x^3 - 5.8666x^2 + 27.55x + 7.38    R2 = 0.9396
  Scopus          y = 0.4771x^3 - 3.5163x^2 + 23.57x + 21.16   R2 = 0.9697
  WoSCC + Scopus  y = 0.6632x^3 - 5.5513x^2 + 33.83x + 24.91   R2 = 0.9593
"""

import csv
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data_derived")
IN_CSV = os.path.join(DATA, "annual_output_by_database.csv")
OUT_CSV = os.path.join(DATA, "growth_curve_fits.csv")

EXPECTED = {
    "WoSCC": (0.6599, -5.8666, 27.55, 7.38, 0.9396),
    "Scopus": (0.4771, -3.5163, 23.57, 21.16, 0.9697),
    "WoSCC_plus_Scopus": (0.6632, -5.5513, 33.83, 24.91, 0.9593),
}


def r_squared(y, y_hat):
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    return 1.0 - ss_res / ss_tot


def main():
    with open(IN_CSV, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    years = np.array([int(r["year"]) for r in rows], dtype=float)
    x = years - 2016.0                      # centering, as in the R script

    out_rows = []
    print("%-18s %9s %9s %9s %9s %9s   expected R2" % (
        "series", "a3", "a2", "a1", "a0", "R2"))
    for series, exp in EXPECTED.items():
        y = np.array([float(r[series]) for r in rows])
        coef = np.polyfit(x, y, 3)          # highest order first
        a3, a2, a1, a0 = coef
        y_hat = np.polyval(coef, x)
        r2 = r_squared(y, y_hat)
        print("%-18s %9.4f %9.4f %9.4f %9.4f %9.4f   %9.4f" % (
            series, a3, a2, a1, a0, r2, exp[4]))
        if abs(r2 - exp[4]) > 5e-4:
            raise SystemExit(
                "R2 for %s (%.4f) does not reproduce the reported value (%.4f)"
                % (series, r2, exp[4]))
        out_rows.append({
            "series": series,
            "cubic": round(a3, 4), "quadratic": round(a2, 4),
            "linear": round(a1, 4), "intercept": round(a0, 4),
            "R2": round(r2, 4),
            "n_documents": int(np.sum(y)),
        })

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    print("\nall three R2 values reproduce the values printed in Figure 2C")
    print("written:", os.path.normpath(OUT_CSV))


if __name__ == "__main__":
    main()
