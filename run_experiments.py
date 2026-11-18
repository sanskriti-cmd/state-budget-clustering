#!/usr/bin/env python3
"""
Clustering Indian states by budget priorities (RBI, "State Finances: A Study of Budgets").

Reads one CSV (one row per state/UT), standardises five fiscal indicators, compares K-means
solutions for k = kmin..kmax (silhouette, Calinski-Harabasz, Davies-Bouldin), fits K-means and
Ward hierarchical clustering with the selected k, runs PCA, and writes every table and figure
used in the paper to --out. Nothing is typed in by hand.

Examples
--------
python run_experiments.py --data data/state_budget_features_2025_26_BE.csv
python run_experiments.py --data data/panel.csv --year 2023-24 --stage Accounts
python run_experiments.py --data data/state_budget_features_2025_26_BE.csv --outcomes data/outcomes.csv
"""
import argparse
import json
import os
import platform
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.stats import kruskal
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import (adjusted_rand_score, calinski_harabasz_score,
                             davies_bouldin_score, silhouette_samples,
                             silhouette_score)
from sklearn.preprocessing import StandardScaler

# canonical name -> display name, plain-language label, and keywords used to find the CSV column
FEATURES = {
    "education_share": ("Education", "Education expenditure, % of aggregate expenditure (RBI Statement 26)", ["educ"]),
    "health_share": ("Health", "Medical, public health & family welfare, % of aggregate expenditure (Statement 27)", ["health", "medic"]),
    "development_gsdp": ("Dev/GSDP", "Development expenditure, % of GSDP (Statement 35)", ["develop"]),
    "social_sector_gsdp": ("Social/GSDP", "Social-sector expenditure, % of GSDP (Statement 35)", ["social"]),
    "capital_outlay_gsdp": ("Capex/GSDP", "Capital outlay, % of GSDP (Statement 35)", ["capital", "capex"]),
}
AGGREGATE_NAMES = {"all states", "all states and uts", "all states and union territories",
                   "total", "india", "all india", "all-india"}
SEED = 42


# --------------------------------------------------------------------------- data
def resolve_columns(df):
    """Find the state column and map the CSV's columns onto the canonical feature names."""
    cols = list(df.columns)
    exact = [c for c in cols if c.lower().strip() in ("state", "state_ut", "state/ut", "state_name", "unit")]
    loose = [c for c in cols if "state" in c.lower()]
    state_col = (exact or loose or [cols[0]])[0]
    mapping = {}
    for canon, (_, _, keys) in FEATURES.items():
        if canon in cols:
            mapping[canon] = canon
            continue
        hits = [c for c in cols if c != state_col and any(k in c.lower() for k in keys)]
        if len(hits) != 1:
            sys.exit(f"Cannot map feature '{canon}' to a single CSV column (candidates: {hits}). "
                     f"Rename the column to '{canon}'. Columns found: {cols}")
        mapping[canon] = hits[0]
    if len(set(mapping.values())) != len(mapping):
        sys.exit(f"Two features map to the same column: {mapping}")
    return state_col, mapping


def load_data(path, year=None, stage=None):
    raw = pd.read_csv(path)
    for col, val in (("year", year), ("stage", stage)):
        if val is not None:
            if col not in raw.columns:
                sys.exit(f"--{col} given but the CSV has no '{col}' column")
            raw = raw[raw[col].astype(str) == str(val)]
    state_col, mapping = resolve_columns(raw)
    print("Column mapping (CSV -> feature):")
    for canon, src in mapping.items():
        print(f"  {src!r:50} -> {canon}")
    df = raw[[state_col] + list(mapping.values())].copy()
    df.columns = ["state"] + list(mapping.keys())
    df["state"] = df["state"].astype(str).str.strip()
    n_raw = len(df)
    df = df[~df["state"].str.lower().isin(AGGREGATE_NAMES)]
    for c in FEATURES:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    n_before = len(df)
    df = df.dropna(subset=list(FEATURES)).reset_index(drop=True)
    if df["state"].duplicated().any():
        dup = df.loc[df["state"].duplicated(), "state"].tolist()
        sys.exit(f"Duplicate state rows {dup}. Use --year/--stage to select one observation per state.")
    print(f"Rows read: {n_raw}; aggregates removed: {n_raw - n_before}; "
          f"dropped for missing features: {n_before - len(df)}; used: {len(df)}")
    return df


# ----------------------------------------------------------------------- modelling
def model_selection(X, kmin, kmax, n_init):
    rows = []
    for k in range(kmin, min(kmax, len(X) - 1) + 1):
        km = KMeans(n_clusters=k, random_state=SEED, n_init=n_init).fit(X)
        sizes = np.bincount(km.labels_)
        rows.append({
            "k": k,
            "silhouette": silhouette_score(X, km.labels_),
            "calinski_harabasz": calinski_harabasz_score(X, km.labels_),
            "davies_bouldin": davies_bouldin_score(X, km.labels_),
            "inertia": km.inertia_,
            "smallest_cluster": int(sizes.min()),
            "n_singleton_clusters": int((sizes == 1).sum()),
        })
    return pd.DataFrame(rows)


def link_outcomes(assign, path, outdir):
    """Post-hoc only: outcomes are never used to build clusters."""
    oc = pd.read_csv(path)
    key = lambda s: s.astype(str).str.lower().str.replace(r"[^a-z0-9]", "", regex=True)
    scol = "state" if "state" in oc.columns else oc.columns[0]
    left = assign[["state", "cluster"]].assign(_k=key(assign["state"]))
    right = oc.assign(_k=key(oc[scol])).drop(columns=[scol])
    merged = left.merge(right, on="_k", how="left").drop(columns="_k")
    num = [c for c in merged.select_dtypes("number").columns if c != "cluster"]
    means = merged.groupby("cluster")[num].mean().round(3)
    means.insert(0, "n_units", merged.groupby("cluster").size())
    means.to_csv(os.path.join(outdir, "outcomes_by_cluster.csv"))
    tests = []
    for c in num:
        groups = [g.dropna().values for _, g in merged.groupby("cluster")[c]]
        groups = [g for g in groups if len(g)]
        try:
            p = kruskal(*groups).pvalue if len(groups) > 1 else np.nan
        except ValueError:
            p = np.nan
        tests.append({"outcome": c, "n_matched": int(merged[c].notna().sum()), "kruskal_p": p})
    pd.DataFrame(tests).to_csv(os.path.join(outdir, "outcomes_tests.csv"), index=False)
    print("Outcome linkage written (descriptive; small clusters, no causal claim).")


# ---------------------------------------------------------------------------- plots
def make_figures(df, feats, shorts, X, sel, best_k, labels, pcs, pca, outdir):
    cmap = plt.get_cmap("tab10")
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})

    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    ax.plot(sel["k"], sel["silhouette"], "o-", color="#1f4e79")
    ax.plot(best_k, sel.loc[sel.k == best_k, "silhouette"].iloc[0], "o", ms=11, mfc="none", mec="#c0392b")
    ax.set_xlabel("Number of clusters (k)")
    ax.set_ylabel("Mean silhouette score")
    ax.set_xticks(sel["k"])
    ax.grid(alpha=.25)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "fig_silhouette_vs_k.png"), dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5.2))
    for c in sorted(set(labels)):
        m = labels == c
        ax.scatter(pcs[m, 0], pcs[m, 1], s=42, color=cmap((c - 1) % 10), label=f"Cluster {c}")
        for i in np.where(m)[0]:
            ax.annotate(df.state[i], (pcs[i, 0], pcs[i, 1]), fontsize=6.5, xytext=(3, 3), textcoords="offset points")
    ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0] * 100:.1f}% variance)")
    ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1] * 100:.1f}% variance)")
    ax.legend(frameon=False)
    ax.grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "fig_pca_clusters.png"), dpi=220)
    plt.close(fig)

    prof = df.assign(cluster=labels).groupby("cluster")[feats].mean()
    fig, ax = plt.subplots(figsize=(7, 4.2))
    w = 0.8 / len(feats)
    for j, f in enumerate(feats):
        ax.bar(np.arange(len(prof)) + j * w, prof[f], w, label=shorts[j])
    ax.set_xticks(np.arange(len(prof)) + 0.4 - w / 2)
    ax.set_xticklabels(prof.index)
    ax.set_xlabel("K-means cluster")
    ax.set_ylabel("Mean (%)")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "fig_cluster_mean_indicators.png"), dpi=220)
    plt.close(fig)

    corr = df[feats].corr()
    fig, ax = plt.subplots(figsize=(5.6, 4.6))
    im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(feats)))
    ax.set_xticklabels(shorts, rotation=30, ha="right")
    ax.set_yticks(range(len(feats)))
    ax.set_yticklabels(shorts)
    for i in range(len(feats)):
        for j in range(len(feats)):
            ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, label="Pearson correlation")
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "fig_correlation_matrix.png"), dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.2))
    dendrogram(linkage(X, "ward"), labels=df.state.tolist(), leaf_rotation=90, leaf_font_size=7, ax=ax,
               color_threshold=0, above_threshold_color="#1f4e79")
    ax.set_ylabel("Ward distance")
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "fig_dendrogram_ward.png"), dpi=220)
    plt.close(fig)


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True, help="CSV with one row per state/UT")
    ap.add_argument("--out", default="outputs")
    ap.add_argument("--kmin", type=int, default=2)
    ap.add_argument("--kmax", type=int, default=6)
    ap.add_argument("--k", type=int, default=None, help="override the silhouette-selected k")
    ap.add_argument("--n-init", type=int, default=50)
    ap.add_argument("--year", default=None)
    ap.add_argument("--stage", default=None, help="e.g. Accounts, RE or BE (never mix stages)")
    ap.add_argument("--outcomes", default=None, help="optional CSV of development outcomes (post-hoc profiling)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    df = load_data(a.data, a.year, a.stage)
    feats = list(FEATURES)
    shorts = [FEATURES[f][0] for f in feats]
    X = StandardScaler().fit_transform(df[feats])

    sel = model_selection(X, a.kmin, a.kmax, a.n_init)
    sel.to_csv(os.path.join(a.out, "model_selection.csv"), index=False)
    best_k = a.k or int(sel.loc[sel["silhouette"].idxmax(), "k"])
    print("\nModel selection (K-means):\n", sel.round(3).to_string(index=False))
    print(f"Selected k = {best_k}")

    km = KMeans(n_clusters=best_k, random_state=SEED, n_init=a.n_init).fit(X)
    labels = km.labels_ + 1
    ward = AgglomerativeClustering(n_clusters=best_k, linkage="ward").fit_predict(X) + 1
    ari = adjusted_rand_score(labels, ward)

    assign = df.assign(kmeans_cluster=labels, ward_cluster=ward,
                       silhouette_i=silhouette_samples(X, labels))
    assign.rename(columns={"kmeans_cluster": "cluster"}).to_csv(os.path.join(a.out, "state_cluster_assignments.csv"), index=False)
    pd.crosstab(assign.kmeans_cluster, assign.ward_cluster, margins=True).to_csv(os.path.join(a.out, "hierarchical_vs_kmeans.csv"))
    pd.DataFrame([{"adjusted_rand_index": ari}]).to_csv(os.path.join(a.out, "hierarchical_agreement.csv"), index=False)

    prof = df.assign(cluster=labels).groupby("cluster")[feats].mean().round(2)
    prof.insert(0, "n_units", pd.Series(labels).value_counts().sort_index())
    prof.to_csv(os.path.join(a.out, "cluster_profiles.csv"))
    (df.assign(cluster=labels).groupby("cluster")["state"].apply(lambda s: "; ".join(sorted(s)))
       .to_csv(os.path.join(a.out, "cluster_members.csv")))
    df[feats].corr().round(3).to_csv(os.path.join(a.out, "correlation_matrix.csv"))

    pca_full = PCA().fit(X)
    pca = PCA(n_components=2).fit(X)
    pcs = pca.transform(X)
    pd.DataFrame({"state": df.state, "PC1": pcs[:, 0], "PC2": pcs[:, 1], "cluster": labels}).to_csv(
        os.path.join(a.out, "pca_coordinates.csv"), index=False)
    pd.DataFrame(pca_full.components_[:2].T, index=feats, columns=["PC1_loading", "PC2_loading"]).round(3).to_csv(
        os.path.join(a.out, "pca_loadings.csv"))
    pd.DataFrame({"PC": range(1, len(feats) + 1), "explained_variance_ratio": pca_full.explained_variance_ratio_}).to_csv(
        os.path.join(a.out, "pca_explained_variance.csv"), index=False)

    make_figures(df, feats, shorts, X, sel, best_k, labels, pcs, pca, a.out)
    if a.outcomes:
        link_outcomes(assign, a.outcomes, a.out)

    info = {"n_units": int(len(df)), "features": feats, "selected_k": best_k,
            "silhouette_at_k": float(sel.loc[sel.k == best_k, "silhouette"].iloc[0]),
            "cluster_sizes": {int(k): int(v) for k, v in pd.Series(labels).value_counts().sort_index().items()},
            "adjusted_rand_ward_vs_kmeans": float(ari),
            "pc1_pc2_variance": [float(v) for v in pca.explained_variance_ratio_],
            "seed": SEED, "n_init": a.n_init,
            "python": platform.python_version(), "scikit_learn": sklearn.__version__,
            "pandas": pd.__version__, "numpy": np.__version__}
    with open(os.path.join(a.out, "run_info.json"), "w") as fh:
        json.dump(info, fh, indent=2)
    print("\nCluster profiles:\n", prof.to_string())
    print(f"\nWard vs K-means adjusted Rand index: {ari:.3f}")
    print(f"PC1+PC2 variance: {100 * pca.explained_variance_ratio_.sum():.1f}%")
    print(f"All outputs written to {a.out}/")


if __name__ == "__main__":
    main()
