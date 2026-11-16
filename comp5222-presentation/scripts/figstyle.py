"""Shared matplotlib style for the v4 deck figures: Carlito (Calibri metrics) and the deck palette."""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap

for f in Path(__file__).resolve().parent.parent.joinpath("fonts").glob("Carlito-*.ttf"):
    font_manager.fontManager.addfont(str(f))
INK, BODY, BLUE, ORANGE, DKORANGE, GRID = "#13233A", "#3C4757", "#2F6FB0", "#D9692A", "#A34D18", "#E1E5EA"
plt.rcParams.update({
    "font.family": "Carlito", "font.size": 17, "axes.labelsize": 18, "mathtext.fontset": "custom",
    "mathtext.rm": "Carlito", "mathtext.it": "Carlito:italic",
    "axes.edgecolor": BODY, "axes.labelcolor": INK, "xtick.color": BODY, "ytick.color": BODY,
    "figure.facecolor": "#FFFFFF", "axes.facecolor": "#FFFFFF", "savefig.facecolor": "#FFFFFF",
    "axes.spines.top": False, "axes.spines.right": False,
})
# blue = depleted, orange = enriched, matching the deck's colour meaning
DIVERGE = LinearSegmentedColormap.from_list("deck", ["#1F4E86", BLUE, "#A9C8E8", "#FFFFFF", "#F2C2A0", ORANGE, DKORANGE])
