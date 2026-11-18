#!/usr/bin/env python3
"""Draws the methodology pipeline figure (Fig. 2 of the paper). Needs no data."""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

plt.rcParams["font.family"] = ["Carlito", "DejaVu Sans"]
NAVY, FILL, EDGE, DASH = "#1f3864", "#e8eef7", "#2f5597", "#7f7f7f"

steps = [
    ("1", "RBI source tables", "State Finances 2025-26: Statements 26, 27, 35\n(31 states / UTs, Budget Estimates)", False),
    ("2", "Cleaning and harmonisation", "harmonise names | drop all-states row\nno imputation (drop missing) | one stage only", False),
    ("3", "Scaling", "z-score each indicator (denominators differ)\n[CLR only for a closed sub-composition]", False),
    ("4", "Model selection", "K-means, k = 2...6, seed 42, n_init 50\nsilhouette (+ Calinski-Harabasz, Davies-Bouldin)", False),
    ("5", "Final models", "K-means and Ward hierarchical (same k)\nPCA (2 components) for visualisation", False),
    ("6", "Evaluation and profiles", "cluster sizes | mean indicators | silhouette\nWard vs K-means agreement (ARI)", False),
    ("7", "Outcome linkage (post-hoc)", "join literacy / health / SDG-index by state\nafter clustering; descriptive only, no causal claim", True),
]

h, gap, w = 1.08, 0.38, 4.8
fig_h = len(steps) * (h + gap)
fig, ax = plt.subplots(figsize=(w + 0.2, fig_h * 0.66 + 0.1))
ax.set_xlim(0, w + 0.2)
ax.set_ylim(0, fig_h)
ax.axis("off")

for i, (num, title, body, dashed) in enumerate(steps):
    y = fig_h - (i + 1) * (h + gap) + gap
    box = FancyBboxPatch((0.15, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                         fc="white" if dashed else FILL, ec=DASH if dashed else EDGE,
                         lw=1.2, ls="--" if dashed else "-")
    ax.add_patch(box)
    ax.text(0.40, y + h / 2, num, ha="center", va="center", fontsize=13, color=NAVY, fontweight="bold")
    ax.text(0.78, y + h - 0.25, title, ha="left", va="center", fontsize=11.5, color=NAVY, fontweight="bold")
    ax.text(0.78, y + 0.37, body, ha="left", va="center", fontsize=9.4, color="#222222", linespacing=1.25)
    if i < len(steps) - 1:
        ax.add_patch(FancyArrowPatch((0.15 + w / 2, y), (0.15 + w / 2, y - gap + 0.02),
                                     arrowstyle="-|>", mutation_scale=11,
                                     color=DASH if i == len(steps) - 2 else EDGE, lw=1.2,
                                     ls="--" if i == len(steps) - 2 else "-"))

os.makedirs("figures", exist_ok=True)
fig.savefig("figures/fig_workflow.png", dpi=250, bbox_inches="tight", facecolor="white")
print("wrote figures/fig_workflow.png")
