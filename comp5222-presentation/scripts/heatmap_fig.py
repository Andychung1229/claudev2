"""Contact-enrichment heatmap in deck colours. Usage: heatmap_fig.py <COMP-5222 dir> <out.png>"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from figstyle import DIVERGE, plt  # noqa: E402

ROOT, OUT = Path(sys.argv[1]), sys.argv[2]
AA, order = "ACDEFGHIKLMNPQRSTVWY", "KREDHNQSTGPACMVILFYW"
eps = np.asarray(np.load(ROOT / "data/processed/aa_contact_table.npz")["interaction"], dtype=float)
idx = [AA.index(a) for a in order]
E = eps[np.ix_(idx, idx)]
lim = float(np.abs(E).max())
fig, ax = plt.subplots(figsize=(7.2, 6.4), dpi=200)
im = ax.imshow(E, cmap=DIVERGE, vmin=-lim, vmax=lim)
ax.set_xticks(range(20), list(order), fontsize=15)
ax.set_yticks(range(20), list(order), fontsize=15)
ax.tick_params(length=0)
for s in ax.spines.values():
    s.set_visible(False)
cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
cb.set_label("enrichment  log( f(a,b) / mean f )", fontsize=17)
cb.outline.set_visible(False)
fig.tight_layout()
fig.savefig(OUT)
