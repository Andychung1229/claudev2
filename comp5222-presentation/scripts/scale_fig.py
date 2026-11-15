"""Edge-score scales: pair frequency f(a,b) vs band frequency p(d). Usage: scale_fig.py <COMP-5222 dir> <out.png> [paper hex]"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT, OUT = Path(sys.argv[1]), Path(sys.argv[2])
PAPER = sys.argv[3] if len(sys.argv) > 3 else "#FFFFFF"
INK, BODY, BLUE, ORANGE, GRID = "#13233A", "#44505F", "#2F6FB0", "#D9692A", "#D8DDE3"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 15, "axes.labelsize": 17,
    "axes.edgecolor": BODY, "axes.labelcolor": INK, "xtick.color": BODY, "ytick.color": BODY,
    "figure.facecolor": PAPER, "axes.facecolor": PAPER, "savefig.facecolor": PAPER,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
})

z = np.load(ROOT / "data/processed/aa_contact_table.npz")
c, o = z["counts"], z["opportunities"]
f = c[o > 0] / o[o > 0]
sc, so = z["sep_counts"], z["sep_opps"]
bands = [("2–4", 2, 4), ("5–8", 5, 8), ("9–16", 9, 16), ("17–32", 17, 32), (">32", 33, 511)]
pd_ = np.array([sc[a:b + 1].sum() / so[a:b + 1].sum() for _, a, b in bands])

fig, ax = plt.subplots(figsize=(7.4, 4.6), dpi=200)
ax.set_xscale("log")
ax.set_xlim(1.5e-4, 1.2)
ax.set_ylim(-0.7, 1.8)
# distance bands
ax.plot([pd_.min(), pd_.max()], [1, 1], color=BLUE, lw=8, alpha=0.25, solid_capstyle="round")
ax.scatter(pd_, np.ones_like(pd_), s=110, color=BLUE, edgecolors=INK, linewidths=0.8, zorder=3)
for (lab, _, _), v in zip(bands, pd_):
    ax.text(v, 1.22, lab, ha="center", va="bottom", fontsize=13, color=BLUE)
ax.text(np.sqrt(pd_.min() * pd_.max()), 0.62, f"{pd_.max() / pd_.min():,.0f}×", ha="center", va="center",
        fontsize=20, fontweight="bold", color=BLUE)
# pair frequencies
ax.plot([f.min(), f.max()], [0, 0], color=ORANGE, lw=8, solid_capstyle="round")
ax.text(f.max() * 1.5, 0, f"{f.max() / f.min():.1f}×", ha="left", va="center", fontsize=20, fontweight="bold",
        color=ORANGE)
ax.set_yticks([1, 0])
ax.set_yticklabels(["distance band\np(d)", "amino-acid pair\nf(a,b)"], fontsize=15, color=INK)
ax.tick_params(axis="y", length=0)
ax.set_xlabel("contact frequency (log scale)")
ax.grid(axis="x", color=GRID, lw=0.6)
fig.tight_layout()
fig.savefig(OUT)
print("p_d", np.round(pd_, 5).tolist(), "f range", round(float(f.min()), 5), round(float(f.max()), 5))
