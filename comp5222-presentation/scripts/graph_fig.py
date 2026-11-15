"""Clearer graph figures. Usage: graph_fig.py <COMP-5222 dir> <out dir>"""
import sys, csv
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Arc
from matplotlib.colors import ListedColormap
ROOT, OUT = Path(sys.argv[1]), Path(sys.argv[2])
INK, BODY, BLUE, ORANGE, PAPER = "#13233A", "#44505F", "#2F6FB0", "#D9692A", "#FFFFFF"
AA = "ACDEFGHIKLMNPQRSTVWY"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 15, "figure.facecolor": PAPER,
                     "axes.facecolor": PAPER, "savefig.facecolor": PAPER})
z = np.load(ROOT / "data/processed/aa_contact_table.npz", allow_pickle=False)
c, o = z["counts"], z["opportunities"]
freq = np.divide(c, o, out=np.zeros_like(c), where=o > 0)
sc, so = z["sep_counts"], z["sep_opps"]
bands = [(1, 1), (2, 4), (5, 8), (9, 16), (17, 32), (33, 511)]
p_d = np.array([sc[a:b + 1].sum() / max(so[a:b + 1].sum(), 1) for a, b in bands])

def graph(seq, w=2, k=8):
    n = len(seq); a = np.array([AA.index(x) for x in seq])
    ii, jj = np.meshgrid(np.arange(n), np.arange(n), indexing="ij"); sep = abs(ii - jj)
    b = np.full(sep.shape, -1)
    for t, (lo, hi) in enumerate(bands): b[(sep >= lo) & (sep <= hi)] = t
    score = freq[a[:, None], a[None, :]] / (np.where(b >= 0, p_d[np.clip(b, 0, 5)], 0) + 1e-8)
    nl = sep > w
    s = np.where(nl, score, -1e30) - np.arange(n)[None, :] * 1e-12
    pick = np.argpartition(s, -k, axis=1)[:, -k:]
    own = np.zeros((n, n), bool); own[np.arange(n)[:, None], pick] = nl[np.arange(n)[:, None], pick]
    return own, own | own.T, (sep >= 1) & (sep <= w), score

rows = list(csv.DictReader(open(ROOT / "data/processed/idrome_split_test.tsv"), delimiter="\t"))
seq = [r for r in rows if 36 <= int(r["seq_len"]) <= 42][0]["sequence"]
own, sym, local, score = graph(seq); n = len(seq)
i0 = seq.index("F")  # first aromatic residue as the focus node
fig, ax = plt.subplots(figsize=(16, 4.6))
for j in np.nonzero(own[i0])[0]:
    lo, hi = sorted((i0, j)); ax.add_patch(Arc(((lo + hi) / 2, 0), hi - lo, (hi - lo) * 0.8, theta1=0, theta2=180, color=ORANGE, lw=3))
for j in range(max(0, i0 - 2), min(n, i0 + 3)):
    if j != i0:
        lo, hi = sorted((i0, j)); ax.add_patch(Arc(((lo + hi) / 2, 0), hi - lo, 0.9 * (hi - lo), theta1=180, theta2=360, color=BLUE, lw=3))
ax.plot([0, n - 1], [0, 0], color=INK, lw=2.2, zorder=1)
for i, ch in enumerate(seq):
    fc = ORANGE if i == i0 else ("#F6DCCB" if own[i0, i] else ("#D3E3F3" if local[i0, i] else "#FFFFFF"))
    ax.scatter(i, 0, s=420, color=fc, edgecolors=INK, linewidths=1.4, zorder=3)
    ax.text(i, 0, ch, ha="center", va="center", fontsize=13, color=INK if i != i0 else "white", fontweight="bold", zorder=4)
far = max(abs(j - i0) for j in np.nonzero(own[i0])[0])
ax.set_xlim(-1, n); ax.set_ylim(-1.6, far * 0.42 + 0.8); ax.set_aspect("equal"); ax.axis("off")
fig.tight_layout(); fig.savefig(OUT / "graph_one_node.png", dpi=170); plt.close(fig)

long = [r for r in rows if 150 <= int(r["seq_len"]) <= 160][0]["sequence"]
_, symL, localL, _ = graph(long); N = len(long)
M = np.zeros((N, N)); M[symL] = 2; M[localL] = 1; np.fill_diagonal(M, 1)
fig, ax = plt.subplots(figsize=(6.2, 6.2))
ax.imshow(M, cmap=ListedColormap([PAPER, BLUE, ORANGE]), vmin=0, vmax=2, interpolation="nearest")
ax.set_xticks([0, 50, 100, 150]); ax.set_yticks([0, 50, 100, 150])
ax.set_xlabel("residue j"); ax.set_ylabel("residue i")
for s in ax.spines.values(): s.set_color(BODY)
fig.tight_layout(); fig.savefig(OUT / "adjacency_long.png", dpi=170); plt.close(fig)
und = int(np.triu(symL | localL, 1).sum())
print("focus", i0, seq[i0], "partners", "".join(seq[j] for j in np.nonzero(own[i0])[0]), "N", N, "edges", und, "complete", N * (N - 1) // 2, "frac", und / (N * (N - 1) / 2))
