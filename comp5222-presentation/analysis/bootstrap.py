"""Paired bootstrap: GAT vs linear composition baseline. Usage: bootstrap.py <COMP-5222 dir>"""
import csv, sys
from pathlib import Path
import numpy as np
R = Path(sys.argv[1]); AA = "ACDEFGHIKLMNPQRSTVWY"
rd = lambda p: list(csv.DictReader(open(p), delimiter="\t"))
F = lambda s: [1.0, np.log(len(s))] + [s.count(a) / len(s) for a in AA[:-1]]
tr = [r for r in rd(R/"data/processed/idrome_split_train.tsv") if int(r["seq_len"]) <= 512]
X = np.array([F(r["sequence"]) for r in tr]); y = np.log([float(r["rg_nm"]) for r in tr])
lam = 1e-3*np.eye(X.shape[1]); lam[0,0] = 0; w = np.linalg.solve(X.T@X+lam, X.T@y)
print("params", len(w))
run = R/"runs/contact_gat_idrome_sparse"
for name, lab, pred in (("test", "data/processed/idrome_split_test.tsv", "predictions_test.tsv"), ("exp151", "data/processed/labels_exp151.tsv", "predictions_exp151.tsv")):
    seq = {r["id"]: r["sequence"] for r in rd(R/lab)}
    P = rd(run/pred); yt = np.array([float(r["rg_true_nm"]) for r in P]); g = np.array([float(r["rg_pred_nm"]) for r in P])
    l = np.exp(np.array([F(seq[r["id"]]) for r in P]) @ w)
    d = np.abs(g-yt) - np.abs(l-yt); rng = np.random.RandomState(0)
    bs = np.array([d[rng.randint(0, len(d), len(d))].mean() for _ in range(5000)])
    print(f"{name}: n={len(d)} GAT MAE {np.abs(g-yt).mean():.3f}  linear MAE {np.abs(l-yt).mean():.3f}  diff {d.mean():+.4f} nm  95% CI [{np.percentile(bs,2.5):+.4f}, {np.percentile(bs,97.5):+.4f}]  GAT better on {np.mean(np.abs(g-yt)<np.abs(l-yt)):.2f} of chains")
