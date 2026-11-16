"""Per-seed MAE of the edge ablation vs baselines.
Usage: ablation_fig.py <dir with {variant}_s{seed}_{test,exp151}.tsv> <test|exp151> <out.png> [paper hex]"""
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

D, DS, OUT = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
PAPER = sys.argv[4] if len(sys.argv) > 4 else "#FFFFFF"
INK, BODY, BLUE, ORANGE, GREY, GRID = "#13233A", "#44505F", "#2F6FB0", "#D9692A", "#9AA5B1", "#D8DDE3"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 15, "axes.labelsize": 17,
    "axes.edgecolor": BODY, "axes.labelcolor": INK, "xtick.color": BODY, "ytick.color": BODY,
    "figure.facecolor": PAPER, "axes.facecolor": PAPER, "savefig.facecolor": PAPER,
    "axes.spines.top": False, "axes.spines.right": False,
})

# baselines from check_story.py (single deterministic fits)
BASE = {"test": {"Length\nonly": 0.1240, "Composition\n+ length": 0.0984},
        "exp151": {"Length\nonly": 0.4159, "Composition\n+ length": 0.3310}}[DS]
VARS = [("full", "GAT\ncontact\nedges (full)", BLUE), ("distance_only", "GAT\ndistance\nedges", BLUE),
        ("local_only", "GAT\nlocal\nonly", ORANGE)]


def mae(v, s):
    r = list(csv.DictReader(open(D / f"{v}_s{s}_{DS}.tsv"), delimiter="\t"))
    return np.mean([abs(float(x["rg_pred_nm"]) - float(x["rg_true_nm"])) for x in r])


fig, ax = plt.subplots(figsize=(7.0, 6.6), dpi=200)
TOP = 0.48 if DS == "exp151" else 0.155
labels = list(BASE)
for i, (k, v) in enumerate(BASE.items()):
    ax.bar(i, v, width=0.62, color=GREY, alpha=0.55)
    ax.text(i, v, f"{v:.3f}", ha="center", va="bottom", fontsize=14, color=BODY)
for j, (v, lab, col) in enumerate(VARS):
    i = len(BASE) + j
    m = np.array([mae(v, s) for s in (42, 43, 44)])
    ax.bar(i, m.mean(), width=0.62, color=col, alpha=0.30)
    ax.scatter(i + np.array([-0.15, 0, 0.15]), m, s=70, color=col, edgecolors=INK, linewidths=0.7, zorder=3)
    ax.text(i, m.max() + TOP * 0.02, f"{m.mean():.3f}", ha="center", va="bottom", fontsize=14,
            color=INK if col == BLUE else "#A34D18", fontweight="bold" if col == ORANGE else "normal",
            bbox=dict(fc=PAPER, ec="none", pad=1.5), zorder=4)
    labels.append(lab)
comp = BASE["Composition\n+ length"]
ax.axhline(comp, color=BODY, ls="--", lw=1.2, zorder=1)
ax.set_xticks(range(len(labels)), labels, fontsize=11.5)
ax.set_ylabel("MAE (nm)  ·  dots = 3 training seeds")
ax.set_ylim(0, TOP)
ax.grid(axis="y", color=GRID, lw=0.6)
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(OUT)
print("wrote", OUT)
