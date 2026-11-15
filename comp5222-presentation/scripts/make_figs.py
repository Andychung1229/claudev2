"""Figures + summary numbers for the ContactGAT talk. Usage: make_figs.py <COMP-5222 dir> <out dir>"""
import csv
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Arc

ROOT = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

INK = "#13233A"
BODY = "#44505F"
BLUE = "#2F6FB0"
ORANGE = "#D9692A"
PAPER = "#FFFFFF"
GRID = "#D8DDE3"
AA = "ACDEFGHIKLMNPQRSTVWY"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 15, "axes.labelsize": 17,
    "axes.edgecolor": BODY, "axes.labelcolor": INK, "xtick.color": BODY, "ytick.color": BODY,
    "figure.facecolor": PAPER, "axes.facecolor": PAPER, "savefig.facecolor": PAPER,
    "axes.spines.top": False, "axes.spines.right": False,
})


def rd(p):
    with open(p) as f:
        return list(csv.DictReader(f, delimiter="\t"))


def stats(y, p):
    e = p - y
    return dict(n=len(y), mae=float(np.abs(e).mean()), rmse=float(np.sqrt((e ** 2).mean())),
                r2=float(1 - (e ** 2).sum() / ((y - y.mean()) ** 2).sum()),
                pearson=float(np.corrcoef(y, p)[0, 1]))


summary = {}

# ---------- contact table ----------
z = np.load(ROOT / "data/processed/aa_contact_table.npz", allow_pickle=False)
counts, opps = z["counts"], z["opportunities"]
freq = np.divide(counts, opps, out=np.zeros_like(counts), where=opps > 0)
eps = np.asarray(z["interaction"], dtype=float)
sep_c, sep_o = z["sep_counts"], z["sep_opps"]
bands = [(1, 1), (2, 4), (5, 8), (9, 16), (17, 32), (33, 511)]
p_d = np.array([sep_c[lo:hi + 1].sum() / max(sep_o[lo:hi + 1].sum(), 1) for lo, hi in bands])
summary["band_freq"] = p_d.tolist()

# reorder residues by chemistry for a readable heatmap
order = "KREDHNQSTGPACMVILFYW"
idx = [AA.index(a) for a in order]
E = eps[np.ix_(idx, idx)]
fig, ax = plt.subplots(figsize=(7.2, 6.4))
lim = float(np.abs(E).max())
im = ax.imshow(E, cmap="RdBu_r", vmin=-lim, vmax=lim)
ax.set_xticks(range(20), list(order), fontsize=13)
ax.set_yticks(range(20), list(order), fontsize=13)
ax.tick_params(length=0)
for s in ax.spines.values():
    s.set_visible(False)
cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
cb.set_label(r"enrichment  $\varepsilon_{ab}=\log(f_{ab}/\bar f)$", fontsize=15)
cb.outline.set_visible(False)
fig.tight_layout()
fig.savefig(OUT / "contact_heatmap.png", dpi=200)
plt.close(fig)
top = sorted(((eps[i, j], AA[i] + AA[j]) for i in range(20) for j in range(i, 20)), reverse=True)
summary["eps_top"] = [(p, round(v, 3)) for v, p in top[:6]]
summary["eps_bottom"] = [(p, round(v, 3)) for v, p in top[-6:]]


# ---------- sparse graph for one real sequence (same rule as build_sparse_graph) ----------
def sparse_edges(seq, w=2, k=8):
    n = len(seq)
    a = np.array([AA.index(c) for c in seq])
    ii, jj = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    sep = np.abs(ii - jj)
    b = np.full(sep.shape, -1)
    for t, (lo, hi) in enumerate(bands):
        b[(sep >= lo) & (sep <= hi)] = t
    p = np.where(b >= 0, p_d[np.clip(b, 0, 5)], 0.0)
    score = freq[a[:, None], a[None, :]] / (p + 1e-8)
    nl = sep > w
    s = np.where(nl, score, -1e30) - np.arange(n)[None, :] * 1e-12
    pick = np.argpartition(s, -k, axis=1)[:, -k:]
    m = np.zeros((n, n), bool)
    m[np.arange(n)[:, None], pick] = nl[np.arange(n)[:, None], pick]
    m |= m.T
    return m, score


test = rd(ROOT / "data/processed/idrome_split_test.tsv")
cand = [r for r in test if 36 <= int(r["seq_len"]) <= 42]
ex = cand[0]
seq = ex["sequence"]
m, score = sparse_edges(seq)
n = len(seq)
summary["example"] = dict(id=ex["id"], seq=seq, n=n, rg=float(ex["rg_nm"]),
                          n_nonlocal_undirected=int(np.triu(m).sum()),
                          n_local_undirected=int(2 * n - 3), n_complete_undirected=n * (n - 1) // 2)

fig, ax = plt.subplots(figsize=(16, 4.4))
iu = [(i, j) for i in range(n) for j in range(i + 1, n) if m[i, j]]
smax = max(score[i, j] for i, j in iu)
for i, j in iu:
    c = (i + j) / 2
    wdt = j - i
    alpha = 0.25 + 0.65 * (score[i, j] / smax)
    ax.add_patch(Arc((c, 0), wdt, wdt * 0.9, theta1=0, theta2=180, color=ORANGE, lw=1.6, alpha=alpha))
for i in range(n - 1):
    ax.plot([i, i + 1], [0, 0], color=INK, lw=2.4, zorder=2)
for i in range(n - 2):
    ax.add_patch(Arc((i + 1, 0), 2, 1.1, theta1=180, theta2=360, color=BLUE, lw=1.4, alpha=0.8))
hydro = set("FWYILMV")
charged = set("KRDE")
for i, c in enumerate(seq):
    fc = "#F3D9C6" if c in hydro else ("#CFE0F1" if c in charged else "#FFFFFF")
    ax.scatter(i, 0, s=330, color=fc, edgecolors=INK, linewidths=1.4, zorder=3)
    ax.text(i, 0, c, ha="center", va="center", fontsize=12, color=INK, zorder=4, fontweight="bold")
ax.set_xlim(-1, n)
ax.set_ylim(-1.1, max(j - i for i, j in iu) * 0.47 + 0.6)
ax.set_aspect("equal")
ax.axis("off")
fig.tight_layout()
fig.savefig(OUT / "graph_example.png", dpi=200)
plt.close(fig)

# ---------- length-only baseline (fit on train, as in proposal Table 1) ----------
train = [r for r in rd(ROOT / "data/processed/idrome_split_train.tsv") if int(r["seq_len"]) <= 512]
Ntr = np.array([int(r["seq_len"]) for r in train], float)
Ytr = np.array([float(r["rg_nm"]) for r in train])
b1, b0 = np.polyfit(np.log(Ntr), np.log(Ytr), 1)
summary["length_fit"] = dict(nu=float(b1), R0=float(np.exp(b0)))

pred = rd(ROOT / "runs/contact_gat_idrome_sparse/predictions_test.tsv")
Nte = np.array([int(r["seq_len"]) for r in pred], float)
Yte = np.array([float(r["rg_true_nm"]) for r in pred])
Pte = np.array([float(r["rg_pred_nm"]) for r in pred])
Lte = np.exp(b0) * Nte ** b1
summary["test_gat"] = stats(Yte, Pte)
summary["test_length_only"] = stats(Yte, Lte)
# share of the length-independent ("compaction") variance the GAT explains, in log space
res_true = np.log(Yte) - np.log(Lte)
summary["test_compaction_r2"] = float(1 - ((np.log(Pte) - np.log(Yte)) ** 2).sum() / ((res_true - res_true.mean()) ** 2).sum())

fig, ax = plt.subplots(figsize=(6.6, 6.2))
lo, hi = 0.8, float(max(Yte.max(), Pte.max())) * 1.03
ax.plot([lo, hi], [lo, hi], color=BODY, ls="--", lw=1.2)
hb = ax.hexbin(Yte, Pte, gridsize=45, bins="log", mincnt=1, cmap="Blues", extent=(lo, hi, lo, hi), linewidths=0.1)
ax.set_xlim(lo, hi); ax.set_ylim(lo, hi); ax.set_aspect("equal")
ax.set_xlabel(r"simulated $R_g$ (nm)"); ax.set_ylabel(r"predicted $R_g$ (nm)")
cb = fig.colorbar(hb, ax=ax, fraction=0.046, pad=0.03); cb.set_label("chains per bin (log)"); cb.outline.set_visible(False)
ax.grid(color=GRID, lw=0.6)
fig.tight_layout(); fig.savefig(OUT / "test_parity.png", dpi=200); plt.close(fig)

# ---------- experimental set, flag overlap with training sequences ----------
exp_lab = {r["id"]: r["sequence"] for r in rd(ROOT / "data/processed/labels_exp151.tsv")}
train_all = [r["sequence"] for r in rd(ROOT / "data/processed/idrome_split_train.tsv")]
pe = rd(ROOT / "runs/contact_gat_idrome_sparse/predictions_exp151.tsv")
Ye = np.array([float(r["rg_true_nm"]) for r in pe])
Pe = np.array([float(r["rg_pred_nm"]) for r in pe])
ov = np.array([any(exp_lab[r["id"]] in t for t in train_all) for r in pe])
summary["exp_all"] = stats(Ye, Pe)
summary["exp_no_overlap"] = stats(Ye[~ov], Pe[~ov])
summary["exp_overlap_n"] = int(ov.sum())
Ne = np.array([int(r["seq_len"]) for r in pe], float)
summary["exp_length_only"] = stats(Ye, np.exp(b0) * Ne ** b1)

fig, ax = plt.subplots(figsize=(6.6, 6.2))
lo, hi = 0.0, float(max(Ye.max(), Pe.max())) * 1.05
ax.plot([lo, hi], [lo, hi], color=BODY, ls="--", lw=1.2)
ax.scatter(Ye[~ov], Pe[~ov], s=42, color=BLUE, edgecolors=INK, linewidths=0.4, alpha=0.85, label="not in training set")
ax.scatter(Ye[ov], Pe[ov], s=46, marker="D", color=ORANGE, edgecolors=INK, linewidths=0.4, label="inside a training sequence")
ax.set_xlim(lo, hi); ax.set_ylim(lo, hi); ax.set_aspect("equal")
ax.set_xlabel(r"experimental $R_g$ (nm)"); ax.set_ylabel(r"predicted $R_g$ (nm)")
ax.legend(loc="upper left", frameon=False, fontsize=14)
ax.grid(color=GRID, lw=0.6)
fig.tight_layout(); fig.savefig(OUT / "exp_parity.png", dpi=200); plt.close(fig)

# ---------- validation curve ----------
h = json.loads((ROOT / "runs/contact_gat_idrome_sparse/history.json").read_text())
ep = [r["epoch"] for r in h]
fig, ax = plt.subplots(figsize=(7.4, 4.6))
ax.plot(ep, [r["val_mae_nm"] for r in h], color=BLUE, lw=2.2, label="validation MAE")
ax.plot(ep, [r["val_rmse_nm"] for r in h], color=ORANGE, lw=1.8, ls="--", label="validation RMSE")
best = min(h, key=lambda r: r["val_mae_nm"])["epoch"]
ax.axvline(best, color=BODY, ls=":", lw=1.4)
ax.text(best + 0.6, 0.58, f"best epoch {best}", color=BODY, fontsize=14)
ax.set_xlabel("epoch"); ax.set_ylabel(r"$R_g$ error (nm)")
ax.set_xlim(1, max(ep)); ax.set_ylim(0, 0.66)
ax.grid(color=GRID, lw=0.6); ax.legend(frameon=False, fontsize=14, loc="upper right")
fig.tight_layout(); fig.savefig(OUT / "val_curve.png", dpi=200); plt.close(fig)

print(json.dumps(summary, indent=1))
