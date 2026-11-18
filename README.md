# Results of the original analysis (as used in the paper)

These files are the results that appear in the paper's Section 6. They come from the **first analysis of a
31-unit CSV of 2025-26 Budget Estimates** (five indicators, K-means k = 2-6, Ward, PCA).

**Provenance and status**

* The figures are the original images from that analysis, unchanged.
* The numbers in `cluster_profiles_original_run.csv` are copied from the table in that analysis (one decimal).
* `cluster_membership_original_run.csv` was read off the labelled PCA figure; overlapping labels
  (West Bengal / Puducherry) were resolved by the cluster sizes (12 + 12 + 1 + 1 + 5 = 31).
* **They were not regenerated and the underlying CSV was not independently checked against RBI files.**
  After you verify the data, run `python run_experiments.py` and, if anything differs, replace these files
  and the paper's numbers with the new `outputs/`.

**Headline numbers (as reported by the original analysis)**

* n = 31 units (28 states + NCT Delhi, Jammu and Kashmir, Puducherry); 2025-26 BE
* Best k by silhouette = 5; silhouette = 0.329 (other k roughly 0.28-0.31, read from the figure)
* PC1 = 56.5%, PC2 = 30.3% of variance
* Cluster sizes 12, 12, 1, 1, 5 (single-unit clusters: Arunachal Pradesh, NCT Delhi)

**Not available from the original analysis** (so not reported): adjusted Rand index of Ward vs K-means,
Calinski-Harabasz and Davies-Bouldin per k, exact silhouette for k other than 5, PCA loadings.
`run_experiments.py` produces all of them.
