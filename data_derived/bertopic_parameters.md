# BERTopic pipeline parameters

Corpus
- eligible documents: 1532
- publication years: 2016 to 2025

Text preparation
- fields concatenated: title, abstract, author keywords, keywords plus
- lower cased, non-alphabetic characters removed, whitespace normalised
- records with fewer than 30 characters or without a publication year removed

Embedding
- model: paraphrase-multilingual-MiniLM-L12-v2
- document embeddings cached in document_embeddings.npy

Dimensionality reduction (UMAP)
- n_neighbors = 15
- n_components = 5
- min_dist = 0.05
- metric = cosine

Clustering (HDBSCAN)
- min_cluster_size = 25
- min_samples = 10
- cluster_selection_method = eom

Topic representation
- CountVectorizer with stop_words english, ngram_range (1,2), min_df = 2
- class based TF-IDF weighting

Temporal analysis
- annual bins across 2016 to 2025
- linear regression of topic frequency on time, R2 and P reported
- topics with fewer than five time points excluded from trend testing

Result of this run
- topics including the outlier topic: 12
- share of documents assigned to topic -1: 22.3 percent
- random_state fixed at 42 for UMAP and for the visualisation reducer
