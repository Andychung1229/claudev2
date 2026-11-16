"""Schematic of the three graph variants (contact edges, distance-only edges, chain only).
Usage: variant_fig.py <out dir>"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from figstyle import BLUE, INK, ORANGE, plt  # noqa: E402
from matplotlib.patches import Arc  # noqa: E402

OUT = Path(sys.argv[1])
GREY = "#8C96A3"
N = 16
# long-range partners for a few residues; both rules end up far along the chain
LONG = {"contact": ([(2, 13), (2, 15), (5, 14), (9, 1), (11, 0)], ORANGE),
        "distance": ([(2, 14), (3, 15), (6, 15), (10, 0), (12, 1)], GREY),
        "local": ([], None)}
for name, (pairs, col) in LONG.items():
    fig, ax = plt.subplots(figsize=(6.4, 1.9), dpi=200)
    for a, b in pairs:
        lo, hi = sorted((a, b))
        ax.add_patch(Arc(((lo + hi) / 2, 0), hi - lo, (hi - lo) * 0.55, theta1=0, theta2=180, color=col, lw=2.2))
    for i in range(N - 2):
        ax.add_patch(Arc((i + 1, 0), 2, 1.1, theta1=180, theta2=360, color=BLUE, lw=1.6, alpha=0.8))
    ax.plot([0, N - 1], [0, 0], color=BLUE, lw=2.6, zorder=1)
    ax.scatter(range(N), [0] * N, s=150, color="white", edgecolors=INK, linewidths=1.3, zorder=3)
    ax.set_xlim(-0.6, N - 0.4)
    ax.set_ylim(-0.75, 4.4)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.subplots_adjust(0, 0, 1, 1)
    fig.savefig(OUT / f"variant_{name}.png", transparent=True)
    plt.close(fig)
print("wrote variants")
