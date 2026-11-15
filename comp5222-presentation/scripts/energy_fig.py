"""Two energy-landscape sketches. Usage: energy_fig.py <out dir>"""
import sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
out = Path(sys.argv[1])
x = np.linspace(-1, 1, 400)
for name, y, col, dots in (
    ("energy_folded", -np.exp(-(x / 0.22) ** 2) * 1.0, "#2F6FB0", [0.0]),
    ("energy_idr", 0.12 * np.sin(9 * x) + 0.05 * np.sin(23 * x) - 0.15, "#D9692A", [-0.84, -0.14, 0.53]),
):
    fig, ax = plt.subplots(figsize=(6, 1.9))
    ax.plot(x, y, color=col, lw=5, solid_capstyle="round")
    for d in dots:
        yd = np.interp(d, x, y)
        ax.scatter([d], [yd + 0.08], s=160, color="#13233A", zorder=3)
    ax.set_ylim(-1.1, 0.25); ax.axis("off")
    fig.savefig(out / f"{name}.png", dpi=200, facecolor="white", bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
