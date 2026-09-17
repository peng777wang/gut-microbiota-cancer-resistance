#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D3TEM pipeline for Figure 10, built to answer the D3TEM-related reviewer
comments.

The published definition is reproduced exactly:
    Stage 1  BERTopic topic-level c-TF-IDF vectors
    Stage 2  Ward hierarchical meta-clustering, Euclidean distance, k = 6
    Stage 3  equal-frequency time bins, entropic optimal transport between
             adjacent bins (cost 0.5 on the diagonal and 1.0 off it, Laplace
             smoothing 1e-4, Sinkhorn regularisation 0.05, POT)
             drift index d = (1 - tr(pi)) / (1 - 1/n)
             birth and death events at a relative frequency change of 50 percent
             Chow, Bai-Perron and CUSUM breakpoint tests (statsmodels)

Additions that the reviewers asked for:
    R1.3  a semantic transport cost (1 - cosine similarity between topic
          vectors) is reported next to the uniform cost, so the drift index can
          be interpreted as semantic reorganisation rather than only as a
          change in topic proportions
    R1.5  a sensitivity grid over k, binning scheme, transport cost, Sinkhorn
          regularisation and the birth and death threshold
    R3.3  the drift index definition, the 50 percent threshold and the
          equal-frequency binning are reported with their consequences

Usage
    python3 Figure10_D3TEM_pipeline.py [FIGURE9_DIR] [OUTDIR]
    python3 Figure10_D3TEM_pipeline.py --sensitivity [FIGURE9_DIR] [OUTDIR]

Defaults
    FIGURE9_DIR  C:/72.wxjlx-1/Figure9_output
    OUTDIR       C:/72.wxjlx-1/Figure10_output
"""

import os
import pickle
import sys

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import pdist, squareform
from sklearn.decomposition import PCA
from scipy.stats import linregress
import statsmodels.api as sm
from statsmodels.stats.diagnostic import breaks_cusumolsresid

import ot

DEFAULT_IN = r"C:/72.wxjlx-1/Figure9_output"
DEFAULT_OUT = r"C:/72.wxjlx-1/Figure10_output"

N_BINS = 10
K_META = 6
LAPLACE = 1e-4
SINKHORN_REG = 0.05
BIRTH_DEATH_THRESHOLD = 0.50
CORE_TOPICS = 5
RANDOM_STATE = 42


# ------------------------------------------------------------------ loading
def load_inputs(in_dir):
    assign = pd.read_csv(os.path.join(in_dir, "topic_assignments.csv"),
                         encoding="utf-8-sig")
    assign = assign.rename(columns={"topic": "Topic"})
    with open(os.path.join(in_dir, "bertopic_model.pkl"), "rb") as handle:
        model = pickle.load(handle)

    info = model.get_topic_info()
    valid = [int(t) for t in info["Topic"] if t != -1]

    # full c-TF-IDF matrix for the valid topics (rows follow get_topic_info order)
    order = [int(t) for t in info["Topic"]]
    rows = [order.index(t) for t in valid]
    c_tf_idf = np.asarray(model.c_tf_idf_[rows].todense())
    return assign, model, valid, c_tf_idf


# ------------------------------------------------------------------ stage 2
def ward_meta_clusters(matrix, k):
    """Ward hierarchical clustering on the topic vectors."""
    if k >= matrix.shape[0]:
        k = matrix.shape[0] - 1
    linkage_matrix = linkage(matrix, method="ward", metric="euclidean")
    labels = fcluster(linkage_matrix, t=k, criterion="maxclust")
    return labels, linkage_matrix


# ------------------------------------------------------------------ stage 3
def build_bins(assign, valid, n_bins=N_BINS, scheme="equal_frequency"):
    """Return a list of (label, midpoint, topic frequency vector)."""
    frame = assign[assign["Topic"].isin(valid)].sort_values("PY").reset_index(drop=True)
    if scheme == "equal_frequency":
        groups = np.array_split(np.arange(len(frame)), n_bins)
    else:                                    # equal width in years
        years = frame["PY"].values
        edges = np.linspace(years.min(), years.max() + 1, n_bins + 1)
        groups = [np.where((years >= edges[i]) & (years < edges[i + 1]))[0]
                  for i in range(n_bins)]
        groups = [g for g in groups if len(g) > 0]

    bins = []
    for index, rows in enumerate(groups):
        subset = frame.iloc[rows]
        counts = np.array([(subset["Topic"] == t).sum() for t in valid], dtype=float)
        frequencies = counts / counts.sum() if counts.sum() else counts
        bins.append({
            "bin": index + 1,
            "midpoint": round(float(subset["PY"].mean()), 2),
            "year_min": int(subset["PY"].min()),
            "year_max": int(subset["PY"].max()),
            "documents": int(len(subset)),
            "frequencies": frequencies,
        })
    return bins


def cost_matrix(kind, c_tf_idf):
    """Uniform cost as published, or a semantic cost from topic similarity."""
    n = c_tf_idf.shape[0]
    if kind == "uniform":
        matrix = np.ones((n, n))
        np.fill_diagonal(matrix, 0.5)
        return matrix
    # cosine distance between topic c-TF-IDF vectors, scaled to [0.5, 1] so that
    # the diagonal term keeps the same role as in the published formulation
    norms = np.linalg.norm(c_tf_idf, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    unit = c_tf_idf / norms
    similarity = np.clip(unit @ unit.T, 0, 1)
    return 1.0 - 0.5 * similarity


def drift_index(pi, n):
    """Published normalisation: 0 means perfect continuity."""
    return float((1.0 - np.trace(pi)) / (1.0 - 1.0 / n))


def analyse_drift(bins, valid, cost, reg=SINKHORN_REG, threshold=BIRTH_DEATH_THRESHOLD):
    n = len(valid)
    records, events, plans = [], [], []
    for i in range(len(bins) - 1):
        left, right = bins[i], bins[i + 1]
        a = left["frequencies"] + LAPLACE
        b = right["frequencies"] + LAPLACE
        a, b = a / a.sum(), b / b.sum()
        pi = ot.sinkhorn(a, b, cost, reg)
        records.append({
            "transition": (f'{left["year_min"]}-{left["year_max"]} '
                           f'to {right["year_min"]}-{right["year_max"]}'),
            "from_label": f'{left["year_min"]}-{left["year_max"]}',
            "to_label": f'{right["year_min"]}-{right["year_max"]}',
            "from_midpoint": left["midpoint"],
            "to_midpoint": right["midpoint"],
            "drift_index": round(drift_index(pi, n), 4),
            "diagonal_mass": round(float(np.trace(pi)), 4),
        })
        plans.append((left, right, pi))
        for j, topic in enumerate(valid):
            previous, current = left["frequencies"][j], right["frequencies"][j]
            base = previous if previous > 0 else 1e-9
            change = (current - previous) / base
            label = None
            if change >= threshold:
                label = "birth"
            elif change <= -threshold:
                label = "death"
            if label:
                events.append({
                    "topic": topic,
                    "from_label": f'{left["year_min"]}-{left["year_max"]}',
                    "to_label": f'{right["year_min"]}-{right["year_max"]}',
                    "from_midpoint": left["midpoint"],
                    "to_midpoint": right["midpoint"],
                    "event": label,
                    "relative_change": round(float(change), 3),
                })
    return pd.DataFrame(records), pd.DataFrame(events), plans


# ------------------------------------------------------------------ stage 3b
def chow_test(y, break_index):
    """Chow test for a structural break, returning F and P."""
    n = len(y)
    x = sm.add_constant(np.arange(n))
    pooled = sm.OLS(y, x).fit()
    rss_pooled = pooled.ssr
    left = sm.OLS(y[:break_index], x[:break_index]).fit()
    right = sm.OLS(y[break_index:], x[break_index:]).fit()
    rss_split = left.ssr + right.ssr
    k = x.shape[1]
    df1, df2 = k, n - 2 * k
    if df2 <= 0 or rss_split <= 0:
        return np.nan, np.nan
    f_stat = ((rss_pooled - rss_split) / df1) / (rss_split / df2)
    from scipy.stats import f as f_dist
    return float(f_stat), float(1 - f_dist.cdf(f_stat, df1, df2))


def bai_perron_single_break(y, min_size=2):
    """Single breakpoint chosen by BIC over all admissible breakpoints."""
    n = len(y)
    best = {"bic": np.inf, "break_index": None, "f": np.nan, "p": np.nan}
    for break_index in range(min_size, n - min_size + 1):
        left = sm.OLS(y[:break_index], sm.add_constant(np.arange(break_index))).fit()
        right = sm.OLS(y[break_index:],
                       sm.add_constant(np.arange(break_index, n))).fit()
        rss = left.ssr + right.ssr
        if rss <= 0:
            continue
        bic = n * np.log(rss / n) + 4 * np.log(n)     # 2 segments x 2 parameters
        if bic < best["bic"]:
            f_stat, p_value = chow_test(y, break_index)
            best = {"bic": float(bic), "break_index": break_index,
                    "f": f_stat, "p": p_value}
    return best


def cusum_test(y):
    """CUSUM test on OLS recursive residuals (statsmodels)."""
    n = len(y)
    x = sm.add_constant(np.arange(n))
    fitted = sm.OLS(y, x).fit()
    try:
        statistic, p_value, _ = breaks_cusumolsresid(fitted.resid, ddof=2)
        return float(statistic), float(p_value)
    except Exception:                                            # noqa: BLE001
        return np.nan, np.nan


def breakpoint_table(bins, valid, core_topics):
    rows = []
    midpoints = [b["midpoint"] for b in bins]
    for topic in core_topics:
        series = np.array([b["frequencies"][valid.index(topic)] for b in bins])
        series = series / series.mean() if series.mean() else series
        results = [chow_test(series, k) for k in range(2, len(series) - 1)]
        if results:
            best_index = int(np.nanargmin([r[1] for r in results])) + 2
            chow_f, chow_p = results[best_index - 2]
        else:
            best_index, chow_f, chow_p = None, np.nan, np.nan
        perron = bai_perron_single_break(series)
        cusum_stat, cusum_p = cusum_test(series)
        rows.append({
            "topic": topic,
            "chow_break_midpoint": midpoints[best_index - 1] if best_index else None,
            "chow_F": round(chow_f, 3) if np.isfinite(chow_f) else np.nan,
            "chow_P": round(chow_p, 4) if np.isfinite(chow_p) else np.nan,
            "bai_perron_break_midpoint":
                midpoints[perron["break_index"] - 1] if perron["break_index"] else None,
            "bai_perron_BIC": round(perron["bic"], 3) if np.isfinite(perron["bic"]) else np.nan,
            "bai_perron_F": round(perron["f"], 3) if np.isfinite(perron["f"]) else np.nan,
            "bai_perron_P": round(perron["p"], 4) if np.isfinite(perron["p"]) else np.nan,
            "cusum_statistic": round(cusum_stat, 4) if np.isfinite(cusum_stat) else np.nan,
            "cusum_P": round(cusum_p, 4) if np.isfinite(cusum_p) else np.nan,
        })
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ main run
def run(in_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    assign, model, valid, c_tf_idf = load_inputs(in_dir)
    print(f">>> valid topics: {valid}")

    # ---------- panel A: meta-clusters
    labels, _ = ward_meta_clusters(c_tf_idf, K_META)
    coords = PCA(n_components=2, random_state=RANDOM_STATE).fit_transform(c_tf_idf)
    counts = [int((assign["Topic"] == t).sum()) for t in valid]
    panel_a = pd.DataFrame({
        "Topic": valid, "Meta_cluster": labels,
        "PC1": coords[:, 0], "PC2": coords[:, 1], "Documents": counts,
        "Top10": [", ".join(w for w, _ in (model.get_topic(t) or [])[:10]) for t in valid],
    })
    panel_a.to_csv(os.path.join(out_dir, "Figure10A_source_data.csv"),
                   index=False, encoding="utf-8-sig")

    # ---------- panel B: drift index and lifecycle
    bins = build_bins(assign, valid)
    uniform_cost = cost_matrix("uniform", c_tf_idf)
    semantic_cost = cost_matrix("semantic", c_tf_idf)

    drift_uniform, events_uniform, plans_uniform = analyse_drift(
        bins, valid, uniform_cost)
    drift_semantic, events_semantic, _ = analyse_drift(bins, valid, semantic_cost)

    drift_uniform.to_csv(os.path.join(out_dir, "Figure10B_drift_uniform.csv"),
                         index=False, encoding="utf-8-sig")
    drift_semantic.to_csv(os.path.join(out_dir, "Figure10B_drift_semantic.csv"),
                          index=False, encoding="utf-8-sig")
    events_uniform.to_csv(os.path.join(out_dir, "Figure10B_birth_death_uniform.csv"),
                          index=False, encoding="utf-8-sig")
    events_semantic.to_csv(os.path.join(out_dir, "Figure10B_birth_death_semantic.csv"),
                           index=False, encoding="utf-8-sig")
    pd.DataFrame([{"bin": b["bin"], "midpoint": b["midpoint"],
                   "year_min": b["year_min"], "year_max": b["year_max"],
                   "documents": b["documents"],
                   **{f"T{t}": round(float(b["frequencies"][i]), 4)
                      for i, t in enumerate(valid)}} for b in bins]).to_csv(
        os.path.join(out_dir, "Figure10B_bin_frequencies.csv"),
        index=False, encoding="utf-8-sig")

    # ---------- panel C: annual slopes
    annual = pd.read_csv(os.path.join(in_dir, "topics_over_time_annual_matrix.csv"),
                         index_col=0)
    annual.columns = [int(c) for c in annual.columns]
    slopes = []
    for topic in valid:
        series = annual[topic].values.astype(float)
        slope, intercept, r, p, se = linregress(annual.index.values.astype(float), series)
        slopes.append({"Topic": topic, "Documents": int(series.sum()),
                       "R2": round(r * r, 3), "P": round(float(p), 5),
                       "Slope": round(float(slope), 3),
                       "Significant": bool(p < 0.05 and slope > 0)})
    panel_c = pd.DataFrame(slopes).sort_values("Slope", ascending=False)
    panel_c.to_csv(os.path.join(out_dir, "Figure10C_source_data.csv"),
                   index=False, encoding="utf-8-sig")

    # ---------- panels D to G: coupling matrices
    with open(os.path.join(out_dir, "Figure10DG_coupling_matrices.csv"), "w",
              encoding="utf-8-sig", newline="") as handle:
        handle.write("transition,topic_from,topic_to,transport\n")
        for left, right, pi in plans_uniform:
            for i, t_from in enumerate(valid):
                for j, t_to in enumerate(valid):
                    handle.write(f'{left["year_min"]}-{left["year_max"]} to '
                                 f'{right["year_min"]}-{right["year_max"]},'
                                 f"{t_from},{t_to},{pi[i, j]:.8f}\n")

    # ---------- panel H: breakpoint tests
    core_topics = panel_c.head(CORE_TOPICS)["Topic"].tolist()
    panel_h = breakpoint_table(bins, valid, core_topics)
    panel_h.to_csv(os.path.join(out_dir, "Figure10H_breakpoints.csv"),
                   index=False, encoding="utf-8-sig")

    print("\n>>> drift index, uniform cost (as published)")
    print(drift_uniform[["transition", "drift_index", "diagonal_mass"]].to_string(index=False))
    print("\n>>> drift index, semantic cost (new)")
    print(drift_semantic[["transition", "drift_index", "diagonal_mass"]].to_string(index=False))
    print("\n>>> breakpoint tests")
    print(panel_h.to_string(index=False))
    print(f"\n>>> outputs written to {out_dir}")


# ------------------------------------------------------------------ sensitivity
def sensitivity(in_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    assign, model, valid, c_tf_idf = load_inputs(in_dir)

    configurations = [{"k": K_META, "scheme": "equal_frequency", "cost": "uniform",
                       "reg": SINKHORN_REG, "threshold": BIRTH_DEATH_THRESHOLD}]
    for k in (3, 4, 5, 6, 7):
        configurations.append(dict(configurations[0], k=k))
    configurations.append(dict(configurations[0], scheme="equal_width"))
    configurations.append(dict(configurations[0], cost="semantic"))
    for reg in (0.01, 0.2):
        configurations.append(dict(configurations[0], reg=reg))
    for threshold in (0.40, 0.60):
        configurations.append(dict(configurations[0], threshold=threshold))

    seen, unique = set(), []
    for config in configurations:
        key = tuple(sorted(config.items()))
        if key not in seen:
            seen.add(key)
            unique.append(config)

    rows = []
    for config in unique:
        bins = build_bins(assign, valid, scheme=config["scheme"])
        cost = cost_matrix(config["cost"], c_tf_idf)
        drift, events, _ = analyse_drift(bins, valid, cost, reg=config["reg"],
                                         threshold=config["threshold"])
        labels, _ = ward_meta_clusters(c_tf_idf, config["k"])
        drift_values = drift["drift_index"].values
        minimum = int(np.argmin(drift_values))
        u_shape = bool(drift_values[0] > drift_values[minimum]
                       and drift_values[-1] > drift_values[minimum])
        rows.append({
            **config,
            "bins": len(bins),
            "mean_drift": round(float(drift_values.mean()), 4),
            "min_drift": round(float(drift_values.min()), 4),
            "max_drift": round(float(drift_values.max()), 4),
            "drift_range": round(float(drift_values.max() - drift_values.min()), 4),
            "min_transition_index": minimum + 1,
            "U_shape_preserved": u_shape,
            "birth_events": int((events["event"] == "birth").sum()) if len(events) else 0,
            "death_events": int((events["event"] == "death").sum()) if len(events) else 0,
            "meta_cluster_sizes": ",".join(
                str(int((labels == c).sum())) for c in sorted(set(labels))),
        })
        print(f'>>> k={config["k"]} scheme={config["scheme"]} cost={config["cost"]} '
              f'reg={config["reg"]} threshold={config["threshold"]} '
              f'mean drift={rows[-1]["mean_drift"]}')

    result = pd.DataFrame(rows)
    result.to_csv(os.path.join(out_dir, "sensitivity_d3tem_grid.csv"),
                  index=False, encoding="utf-8-sig")
    print("\n" + result.to_string(index=False))
    print(f"\n>>> sensitivity outputs written to {out_dir}")


if __name__ == "__main__":
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]
    in_dir = positional[0] if positional else DEFAULT_IN
    out_dir = positional[1] if len(positional) > 1 else DEFAULT_OUT
    if "--sensitivity" in sys.argv:
        sensitivity(in_dir, out_dir)
    else:
        run(in_dir, out_dir)
