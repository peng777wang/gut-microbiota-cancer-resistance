#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Figure 9 replication pipeline, built to answer the BERTopic-related reviewer
comments on this manuscript.

Every reviewer requirement that code can satisfy is produced as a file:

  R1.10  complete per-document topic assignments ........ topic_assignments.csv
  R1.10  reproducible code and versions ................. software_versions.txt
  R3.3   BERTopic parameter sensitivity ................. sensitivity_grid.csv
                                                         sensitivity_stability.csv
  R3.3   outlier topic information loss ................. outlier_topic_report.txt
                                                         outlier_reallocation.csv
  R3.7   limitation evidence for the outlier topic ...... outlier_topic_report.txt
  R2.7   summarised pipeline parameters ................. methods_parameters.md
  R2.10  deposited analysis artefacts ................... all files in OUT_DIR
  R3.m   software citations ............................. software_citations.md
  R2.3   panel-by-panel source data ..................... Figure9A_*.csv,
                                                         Figure9B_*.csv,
                                                         Figure9C_*.csv,
                                                         Figure9D_*.csv

Usage
-----
    python3 Figure9_BERTopic_pipeline.py [CORPUS] [OUTDIR]     # main analysis
    python3 Figure9_BERTopic_pipeline.py --sensitivity ...
    python3 Figure9_BERTopic_pipeline.py --outlier ...
    python3 Figure9_BERTopic_pipeline.py --all ...

Defaults
    CORPUS  /media/desk16/tly8627/1.txt
    OUTDIR  /media/desk16/tly8627/figure9_results

Method, fixed so that the code and the manuscript agree
    text          title + abstract + author keywords + keywords plus, lower cased,
                  non-alphabetic characters removed
    eligibility   >= 30 characters and a known publication year
    embedding     paraphrase-multilingual-MiniLM-L12-v2 (384 dimensions)
    UMAP          n_neighbors 15, n_components 5, min_dist 0.05, cosine
    HDBSCAN       min_cluster_size 25, min_samples 10, EOM selection
    vectorizer    stop_words english, ngram_range (1,2), min_df 2
    over time     annual bins over 2016-2025
    trends        linear regression per topic, R2 and P, topics with fewer than
                  five time points excluded
"""

import importlib
import json
import os
import pickle
import platform
import re
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")                      # headless server
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import linregress
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from umap import UMAP
from hdbscan import HDBSCAN

# ----------------------------------------------------------------- configuration
DEFAULT_CORPUS = "/media/desk16/tly8627/1.txt"
DEFAULT_OUTDIR = "/media/desk16/tly8627/figure9_results"

EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
RANDOM_STATE = 42
MIN_CHARS = 30
YEARS = list(range(2016, 2026))

BASE_CONFIG = {
    "n_neighbors": 15,
    "n_components": 5,
    "min_dist": 0.05,
    "min_cluster_size": 25,
    "min_samples": 10,
    "min_df": 2,
}


# ----------------------------------------------------------------- data handling
def parse_wos_plaintext(path):
    """Parse a Web of Science plain-text export."""
    records, current, field = [], {}, None
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.rstrip("\n").rstrip("\r")
            if line.startswith("PT "):
                current, field = {"PT": line[3:].strip()}, "PT"
            elif line.startswith("ER"):
                if current.get("TI"):
                    records.append(current)
                current, field = {}, None
            elif len(line) >= 3 and line[:2].isalnum() and line[2] == " ":
                field = line[:2]
                current[field] = line[3:].strip()
            elif line.startswith("   ") and field:
                current[field] = current.get(field, "") + " " + line.strip()
    if current.get("TI"):
        records.append(current)

    df = pd.DataFrame(records)
    for column in ["TI", "AB", "DE", "ID", "PY", "SO", "DI"]:
        if column not in df.columns:
            df[column] = ""
    df["PY"] = pd.to_numeric(df["PY"], errors="coerce")
    return df


def clean_text(value):
    if pd.isna(value):
        return ""
    text = re.sub(r"[^a-zA-Z\s]", " ", str(value).lower())
    return re.sub(r"\s+", " ", text).strip()


def build_corpus(path):
    df = parse_wos_plaintext(path)
    print(f">>> parsed records: {len(df)}")
    df["corpus"] = (df["TI"].fillna("") + " " + df["AB"].fillna("") + " "
                    + df["DE"].fillna("") + " " + df["ID"].fillna("")).apply(clean_text)
    df = df[(df["corpus"].str.len() > MIN_CHARS) & df["PY"].notna()].copy()
    df["PY"] = df["PY"].astype(int)

    years = sorted(int(y) for y in df["PY"].unique())
    print(f">>> eligible documents: {len(df)}")
    print(f">>> years present: {years}")
    if years != YEARS:
        print(">>> STOP: the year range is not 2016-2025.")
        print(">>>       Check that the corpus file is the cleaned, final one.")
        sys.exit(1)
    return df


# ----------------------------------------------------------------- modelling
def build_model(embedder, config):
    return BERTopic(
        embedding_model=embedder,
        umap_model=UMAP(n_neighbors=config["n_neighbors"],
                        n_components=config["n_components"],
                        min_dist=config["min_dist"],
                        metric="cosine",
                        random_state=RANDOM_STATE),
        hdbscan_model=HDBSCAN(min_cluster_size=config["min_cluster_size"],
                              min_samples=config["min_samples"],
                              cluster_selection_method="eom",
                              prediction_data=True),
        vectorizer_model=CountVectorizer(stop_words="english",
                                         ngram_range=(1, 2),
                                         min_df=config["min_df"]),
        calculate_probabilities=False,
        verbose=False,
    )


def topic_term_matrix(topic_model, topics):
    """Rows are topics, columns are the union of their top terms."""
    per_topic = [topic_model.get_topic(t) or [] for t in topics]
    vocabulary = sorted({w for words in per_topic for w, _ in words})
    position = {w: i for i, w in enumerate(vocabulary)}
    matrix = np.zeros((len(topics), len(vocabulary)))
    for row, words in enumerate(per_topic):
        for word, weight in words:
            matrix[row, position[word]] = weight
    return matrix, vocabulary


def top_term_sets(topic_model, topics, k=10):
    return {t: {w for w, _ in (topic_model.get_topic(t) or [])[:k]} for t in topics}


def jaccard(a, b):
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


# ----------------------------------------------------------------- figures
def _save(fig, out_dir, stem):
    fig.savefig(os.path.join(out_dir, stem + ".png"), dpi=600)
    fig.savefig(os.path.join(out_dir, stem + ".pdf"))
    plt.close(fig)


def figure_9a(embeddings, topics, df, out_dir):
    """A. Document level projection of topics (UMAP, two components)."""
    coords = UMAP(n_neighbors=15, n_components=2, min_dist=0.1,
                  metric="cosine", random_state=RANDOM_STATE).fit_transform(embeddings)
    fig, ax = plt.subplots(figsize=(9, 7))
    scatter = ax.scatter(coords[:, 0], coords[:, 1], c=topics, cmap="Spectral",
                         s=12, alpha=0.75, linewidths=0)
    for topic in sorted(set(topics)):
        mask = np.asarray(topics) == topic
        if not mask.any():
            continue
        label = "Topic -1" if topic == -1 else f"T{topic}"
        ax.text(coords[mask, 0].mean(), coords[mask, 1].mean(), label,
                fontsize=7, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="grey",
                          lw=0.4, alpha=0.85))
    ax.set_xlabel("UMAP 1")
    ax.set_ylabel("UMAP 2")
    ax.set_title("Documents and Topics")
    fig.colorbar(scatter, ax=ax, label="Topic")
    fig.tight_layout()
    _save(fig, out_dir, "Figure9A_documents_topics")

    pd.DataFrame({"UMAP1": coords[:, 0], "UMAP2": coords[:, 1],
                  "Topic": topics, "PY": df["PY"].values,
                  "TI": df["TI"].values}).to_csv(
        os.path.join(out_dir, "Figure9A_source_data.csv"),
        index=False, encoding="utf-8-sig")


def figure_9b(matrix, topics, counts, out_dir):
    """B. Intertopic distance map (PCA of the topic-term weight space)."""
    coords = PCA(n_components=2, random_state=RANDOM_STATE).fit_transform(matrix)
    counts = np.asarray(counts, dtype=float)
    sizes = 40 + 460 * counts / counts.max()
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.scatter(coords[:, 0], coords[:, 1], s=sizes, alpha=0.7,
               edgecolors="black", linewidths=0.5)
    for i, topic in enumerate(topics):
        ax.annotate(f"T{topic}", coords[i], fontsize=8, fontweight="bold")
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.set_title("Intertopic Distance Map")
    fig.tight_layout()
    _save(fig, out_dir, "Figure9B_intertopic_distance")

    pd.DataFrame({"Topic": topics, "PC1": coords[:, 0], "PC2": coords[:, 1],
                  "Documents": counts.astype(int)}).to_csv(
        os.path.join(out_dir, "Figure9B_source_data.csv"),
        index=False, encoding="utf-8-sig")
    return coords


def figure_9c(matrix, topics, out_dir):
    """C. Topic similarity matrix (cosine similarity of topic-term vectors)."""
    similarity = cosine_similarity(matrix)
    labels = [f"T{t}" for t in topics]
    fig, ax = plt.subplots(figsize=(10, 9))
    sns.heatmap(similarity, xticklabels=labels, yticklabels=labels,
                cmap="YlGnBu", vmin=0, vmax=1, square=True,
                cbar_kws={"label": "Cosine similarity"}, ax=ax)
    ax.set_title("Similarity Matrix")
    fig.tight_layout()
    _save(fig, out_dir, "Figure9C_similarity_matrix")

    pd.DataFrame(similarity, index=labels, columns=labels).to_csv(
        os.path.join(out_dir, "Figure9C_source_data.csv"), encoding="utf-8-sig")
    return similarity


def figure_9d(over_time, out_dir):
    """D. Annual topic frequency."""
    pivot = (over_time.pivot(index="Timestamp", columns="Topic", values="Frequency")
             .fillna(0).sort_index())
    pivot = pivot[[c for c in pivot.columns if c != -1]]
    fig, ax = plt.subplots(figsize=(11, 6))
    for topic in pivot.columns:
        ax.plot(pivot.index, pivot[topic], marker="o", markersize=3,
                linewidth=1.2, label=f"Topic {topic}")
    ax.set_xlabel("Year")
    ax.set_ylabel("Frequency")
    ax.set_title("Topics over Time")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=7, ncol=2)
    fig.tight_layout()
    _save(fig, out_dir, "Figure9D_topics_over_time")
    pivot.to_csv(os.path.join(out_dir, "Figure9D_source_data.csv"),
                 encoding="utf-8-sig")
    return pivot


def trend_table(over_time, min_points=5):
    rows = []
    for topic in sorted(t for t in over_time["Topic"].unique() if t != -1):
        sub = over_time[over_time["Topic"] == topic].sort_values("Timestamp")
        if len(sub) < min_points:
            rows.append({"Topic": topic, "N_timepoints": len(sub), "R2": None,
                         "P": None, "Slope": None,
                         "Trend": f"excluded (<{min_points} time points)"})
            continue
        slope, intercept, r, p, se = linregress(sub["Timestamp"], sub["Frequency"])
        if not np.isfinite(r) or not np.isfinite(p):
            # a constant series has no variance, so no trend can be estimated
            rows.append({"Topic": topic, "N_timepoints": len(sub), "R2": None,
                         "P": None, "Slope": round(slope, 3),
                         "Trend": "constant, no trend estimable"})
            continue
        if p < 0.05 and slope > 0:
            label = "significant increase"
        elif p < 0.05 and slope < 0:
            label = "significant decrease"
        else:
            label = "no significant trend"
        rows.append({"Topic": topic, "N_timepoints": len(sub),
                     "R2": round(r * r, 3), "P": p, "Slope": round(slope, 3),
                     "Trend": label})
    return pd.DataFrame(rows)


def annual_frequency_long(df, exclude_outlier=True):
    """Annual topic frequencies taken straight from the document assignments.

    BERTopic's topics_over_time() splits the year axis into equal width bins,
    which shifts the labels (2016 becomes 2015.99 and 2025 is merged into
    2024) and therefore does not give annual counts. The counts below are
    computed per publication year, which is what the manuscript describes.
    """
    topics = sorted(t for t in df["topic"].unique()
                    if not (exclude_outlier and t == -1))
    pivot = (df[df["topic"].isin(topics)]
             .groupby(["PY", "topic"]).size().unstack(fill_value=0)
             .reindex(sorted(YEARS), fill_value=0)
             .reindex(columns=topics, fill_value=0))
    rows = []
    for year in pivot.index:
        for topic in pivot.columns:
            rows.append({"Topic": int(topic), "Timestamp": int(year),
                         "Frequency": int(pivot.loc[year, topic])})
    return pd.DataFrame(rows), pivot


# ----------------------------------------------------------------- reporting
def software_inventory(out_dir):
    modules = ["bertopic", "sentence_transformers", "umap", "hdbscan",
               "sklearn", "pandas", "numpy", "scipy", "matplotlib", "seaborn",
               "torch", "transformers", "ot", "statsmodels"]
    lines = [f"python {platform.python_version()}",
             f"platform {platform.platform()}", ""]
    for name in modules:
        try:
            module = importlib.import_module(name)
            version = getattr(module, "__version__", "unknown")
            lines.append(f"{name}=={version}")
        except Exception as exc:                                  # noqa: BLE001
            lines.append(f"{name} NOT INSTALLED ({exc.__class__.__name__})")
    with open(os.path.join(out_dir, "software_versions.txt"), "w",
              encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    print(">>> software_versions.txt written")


def software_citations(out_dir):
    text = """# Software citations (verify each entry in the reference manager before submission)

BERTopic      Grootendorst M. BERTopic: Neural topic modeling with a class-based
              TF-IDF procedure. arXiv:2203.05794, 2022.
sentence-     Reimers N, Gurevych I. Sentence-BERT: Sentence embeddings using
transformers  Siamese BERT-networks. EMNLP-IJCNLP, 2019.
UMAP          McInnes L, Healy J, Melville J. UMAP: Uniform Manifold Approximation
              and Projection for Dimension Reduction. arXiv:1802.03426, 2018.
HDBSCAN       McInnes L, Healy J, Astels S. hdbscan: Hierarchical density based
              clustering. Journal of Open Source Software, 2017;2(11):205.
scikit-learn  Pedregosa F, et al. Scikit-learn: Machine learning in Python.
              Journal of Machine Learning Research, 2011;12:2825-2830.
POT           Flamary R, et al. POT: Python Optimal Transport. Journal of Machine
              Learning Research, 2021;22(78):1-8.
statsmodels   Seabold S, Perktold J. statsmodels: Econometric and statistical
              modeling with Python. SciPy Conference, 2010.
"""
    with open(os.path.join(out_dir, "software_citations.md"), "w",
              encoding="utf-8") as handle:
        handle.write(text)
    print(">>> software_citations.md written")


def methods_parameters(out_dir, n_docs, config, n_topics, outlier_share):
    text = f"""# BERTopic pipeline parameters

Corpus
- eligible documents: {n_docs}
- publication years: {YEARS[0]} to {YEARS[-1]}

Text preparation
- fields concatenated: title, abstract, author keywords, keywords plus
- lower cased, non-alphabetic characters removed, whitespace normalised
- records with fewer than {MIN_CHARS} characters or without a publication year removed

Embedding
- model: {EMBEDDING_MODEL}
- document embeddings cached in document_embeddings.npy

Dimensionality reduction (UMAP)
- n_neighbors = {config['n_neighbors']}
- n_components = {config['n_components']}
- min_dist = {config['min_dist']}
- metric = cosine

Clustering (HDBSCAN)
- min_cluster_size = {config['min_cluster_size']}
- min_samples = {config['min_samples']}
- cluster_selection_method = eom

Topic representation
- CountVectorizer with stop_words english, ngram_range (1,2), min_df = {config['min_df']}
- class based TF-IDF weighting

Temporal analysis
- annual bins across {YEARS[0]} to {YEARS[-1]}
- linear regression of topic frequency on time, R2 and P reported
- topics with fewer than five time points excluded from trend testing

Result of this run
- topics including the outlier topic: {n_topics}
- share of documents assigned to topic -1: {outlier_share:.1f} percent
- random_state fixed at {RANDOM_STATE} for UMAP and for the visualisation reducer
"""
    with open(os.path.join(out_dir, "methods_parameters.md"), "w",
              encoding="utf-8") as handle:
        handle.write(text)
    print(">>> methods_parameters.md written")


def outlier_report(df, topic_model, out_dir):
    share = float((df["topic"] == -1).mean() * 100)
    words = topic_model.get_topic(-1) or []
    counts = df["topic"].value_counts().sort_index()
    text = [
        f"documents total: {len(df)}",
        f"documents in topic -1: {int((df['topic'] == -1).sum())}",
        f"share of topic -1: {share:.1f} percent",
        "",
        "topic sizes (topic, documents):",
        ", ".join(f"{int(t)}:{int(n)}" for t, n in counts.items()),
        "",
        "most frequent terms inside topic -1:",
        ", ".join(w for w, _ in words[:20]),
        "",
        "interpretation note for the Discussion:",
        "documents in topic -1 carry no shared topical signal, so they contribute",
        "to the corpus but not to any topic level trend. Report the share above,",
        "state that the topic level analyses therefore describe the remaining",
        "documents, and report outlier_reallocation.csv as the sensitivity check.",
    ]
    with open(os.path.join(out_dir, "outlier_topic_report.txt"), "w",
              encoding="utf-8") as handle:
        handle.write("\n".join(text) + "\n")
    print(f">>> outlier share {share:.1f} percent")
    return share


def outlier_reallocation(topic_model, docs, topics, out_dir):
    """Reassign outliers with the c-TF-IDF strategy and report the effect."""
    try:
        new_topics = topic_model.reduce_outliers(docs, list(topics),
                                                 strategy="c-tf-idf")
    except Exception as exc:                                      # noqa: BLE001
        print(f">>> reduce_outliers unavailable ({exc}); skipping")
        return
    before = pd.Series(topics).value_counts().sort_index()
    after = pd.Series(new_topics).value_counts().sort_index()
    table = (pd.DataFrame({"documents_before": before, "documents_after": after})
             .fillna(0).astype(int))
    table.index.name = "Topic"
    table.to_csv(os.path.join(out_dir, "outlier_reallocation.csv"),
                 encoding="utf-8-sig")
    share_before = float((pd.Series(topics) == -1).mean() * 100)
    share_after = float((pd.Series(new_topics) == -1).mean() * 100)
    print(f">>> outlier share before {share_before:.1f} percent, "
          f"after reassignment {share_after:.1f} percent")


def labeling_worksheet(topic_model, topics, df, out_dir):
    """Worksheet for the two independent raters named in the Methods."""
    try:
        representatives = topic_model.get_representative_docs()
    except Exception:                                             # noqa: BLE001
        representatives = {}
    rows = []
    for topic in topics:
        words = topic_model.get_topic(topic) or []
        docs = representatives.get(topic, [])[:3]
        rows.append({
            "Topic": topic,
            "Documents": int((df["topic"] == topic).sum()),
            "Top10_terms": ", ".join(w for w, _ in words[:10]),
            "Representative_document_1": docs[0] if len(docs) > 0 else "",
            "Representative_document_2": docs[1] if len(docs) > 1 else "",
            "Representative_document_3": docs[2] if len(docs) > 2 else "",
            "Label_rater_1": "",
            "Label_rater_2": "",
            "Agreement_yes_no": "",
            "Final_label_after_discussion": "",
        })
    pd.DataFrame(rows).to_csv(os.path.join(out_dir, "topic_labeling_worksheet.csv"),
                              index=False, encoding="utf-8-sig")
    print(">>> topic_labeling_worksheet.csv written")


# ----------------------------------------------------------------- modes
def run_main(corpus_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    software_inventory(out_dir)
    software_citations(out_dir)

    df = build_corpus(corpus_path)
    docs = df["corpus"].tolist()
    years = df["PY"].tolist()

    embedder = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = embedder.encode(docs, show_progress_bar=True, batch_size=64)
    np.save(os.path.join(out_dir, "document_embeddings.npy"), embeddings)

    topic_model = build_model(embedder, BASE_CONFIG)
    topics, _ = topic_model.fit_transform(docs, embeddings)
    df["topic"] = topics
    with open(os.path.join(out_dir, "bertopic_model.pkl"), "wb") as handle:
        pickle.dump(topic_model, handle)

    info = topic_model.get_topic_info()
    info.to_csv(os.path.join(out_dir, "topic_info.csv"), index=False,
                encoding="utf-8-sig")
    valid = sorted(t for t in info["Topic"] if t != -1)

    assignment = df[["TI", "PY", "SO", "DI", "topic"]].copy()
    assignment["topic_terms"] = assignment["topic"].map(
        lambda t: ", ".join(w for w, _ in (topic_model.get_topic(t) or [])[:10]))
    assignment.to_csv(os.path.join(out_dir, "topic_assignments.csv"),
                      index=False, encoding="utf-8-sig")

    top_words = pd.DataFrame(
        [{"Topic": t, "Count": int((df["topic"] == t).sum()),
          "Top10": ", ".join(w for w, _ in (topic_model.get_topic(t) or [])[:10])}
         for t in valid])
    top_words.to_csv(os.path.join(out_dir, "topic_topwords.csv"),
                     index=False, encoding="utf-8-sig")

    matrix, vocabulary = topic_term_matrix(topic_model, valid)
    np.save(os.path.join(out_dir, "topic_term_matrix.npy"), matrix)
    pd.DataFrame(matrix, index=[f"T{t}" for t in valid],
                 columns=vocabulary).to_csv(
        os.path.join(out_dir, "topic_term_matrix.csv"), encoding="utf-8-sig")

    over_time, annual_pivot = annual_frequency_long(df)
    over_time.to_csv(os.path.join(out_dir, "topics_over_time.csv"), index=False)
    annual_pivot.to_csv(os.path.join(out_dir, "topics_over_time_annual_matrix.csv"))
    trends = trend_table(over_time)
    trends.to_csv(os.path.join(out_dir, "topic_trends.csv"), index=False,
                  encoding="utf-8-sig")

    figure_9a(embeddings, topics, df, out_dir)
    figure_9b(matrix, valid, [int((df["topic"] == t).sum()) for t in valid], out_dir)
    figure_9c(matrix, valid, out_dir)
    figure_9d(over_time, out_dir)

    share = outlier_report(df, topic_model, out_dir)
    labeling_worksheet(topic_model, valid, df, out_dir)
    methods_parameters(out_dir, len(df), BASE_CONFIG, len(info), share)

    summary = pd.DataFrame([{
        "documents": len(df),
        "topics_including_outlier": len(info),
        "valid_topics": len(valid),
        "outlier_share_percent": round(share, 1),
        "significant_increase": int((trends["Trend"] == "significant increase").sum()),
        "year_min": int(df["PY"].min()),
        "year_max": int(df["PY"].max()),
    }])
    summary.to_csv(os.path.join(out_dir, "run_summary.csv"), index=False)
    print(summary.to_string(index=False))
    print(f">>> main run finished, outputs in {out_dir}")


def run_sensitivity(corpus_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    df = build_corpus(corpus_path)
    docs, years = df["corpus"].tolist(), df["PY"].tolist()
    embedder = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = embedder.encode(docs, show_progress_bar=True, batch_size=64)

    one_factor = []
    for key, values in [("n_neighbors", [10, 30]),
                        ("min_cluster_size", [15, 40]),
                        ("min_samples", [5, 20]),
                        ("min_df", [1, 5])]:
        for value in values:
            config = dict(BASE_CONFIG)
            config[key] = value
            one_factor.append(config)
    grid = [dict(BASE_CONFIG, n_neighbors=n, min_cluster_size=c)
            for n in (10, 15, 30) for c in (15, 25, 40)]

    seen, configs = set(), []
    for config in [dict(BASE_CONFIG)] + one_factor + grid:
        key = tuple(sorted(config.items()))
        if key not in seen:
            seen.add(key)
            configs.append(config)

    print(f">>> sensitivity: {len(configs)} configurations")
    base_sets, rows, stability_rows = None, [], []
    topic_stability = {}          # baseline topic -> {configuration: best jaccard}
    for index, config in enumerate(configs, 1):
        tag = (f"n{config['n_neighbors']}_c{config['min_cluster_size']}"
               f"_s{config['min_samples']}_d{config['min_df']}")
        print(f"[{index}/{len(configs)}] {tag}")
        model = build_model(embedder, config)
        topics, _ = model.fit_transform(docs, embeddings)
        info = model.get_topic_info()
        valid = sorted(t for t in info["Topic"] if t != -1)
        shares = top_term_sets(model, valid)
        if base_sets is None:
            base_sets = shares
            matched, fraction = len(valid), 1.0
            best_per_topic = {t: 1.0 for t in base_sets}
        else:
            hits = 0
            best_per_topic = {}
            for topic, terms in base_sets.items():
                best = max((jaccard(terms, other) for other in shares.values()),
                           default=0.0)
                best_per_topic[topic] = best
                if best >= 0.5:
                    hits += 1
            matched = hits
            fraction = hits / max(len(base_sets), 1)
        for topic, value in best_per_topic.items():
            topic_stability.setdefault(topic, {})[tag] = round(value, 2)
        rows.append({
            "configuration": tag,
            **config,
            "topics_including_outlier": len(info),
            "valid_topics": len(valid),
            "outlier_share_percent": round(
                float((np.asarray(topics) == -1).mean() * 100), 1),
            "base_topics_recovered_at_jaccard_0.5": matched,
            "base_topics_recovered_fraction": round(fraction, 2),
        })

    result = pd.DataFrame(rows)
    result.to_csv(os.path.join(out_dir, "sensitivity_grid.csv"), index=False)

    stability_matrix = pd.DataFrame(topic_stability).T
    stability_matrix.index.name = "Baseline_topic"
    stability_matrix.to_csv(os.path.join(out_dir, "sensitivity_topic_stability.csv"),
                            encoding="utf-8-sig")
    print(stability_matrix.to_string())

    stability = (result[["configuration", "topics_including_outlier",
                         "valid_topics", "outlier_share_percent",
                         "base_topics_recovered_fraction"]]
                 .sort_values("base_topics_recovered_fraction", ascending=False))
    stability.to_csv(os.path.join(out_dir, "sensitivity_stability.csv"),
                     index=False)
    print(result.to_string(index=False))
    print(f">>> sensitivity finished, outputs in {out_dir}")


def run_outlier(corpus_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    df = build_corpus(corpus_path)
    docs, years = df["corpus"].tolist(), df["PY"].tolist()
    embedder = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = embedder.encode(docs, show_progress_bar=True, batch_size=64)
    model = build_model(embedder, BASE_CONFIG)
    topics, _ = model.fit_transform(docs, embeddings)
    df["topic"] = topics
    outlier_report(df, model, out_dir)
    outlier_reallocation(model, docs, topics, out_dir)
    print(f">>> outlier analysis finished, outputs in {out_dir}")


if __name__ == "__main__":
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]
    corpus = positional[0] if positional else DEFAULT_CORPUS
    outdir = positional[1] if len(positional) > 1 else DEFAULT_OUTDIR

    if "--all" in sys.argv:
        run_main(corpus, outdir)
        run_sensitivity(corpus, os.path.join(outdir, "sensitivity"))
        run_outlier(corpus, os.path.join(outdir, "outlier"))
    elif "--sensitivity" in sys.argv:
        run_sensitivity(corpus, outdir)
    elif "--outlier" in sys.argv:
        run_outlier(corpus, outdir)
    else:
        run_main(corpus, outdir)
