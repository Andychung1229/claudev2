"""Find same-composition (permutation) groups in exp151 and compare predictions. Usage: perm_check.py <COMP-5222 dir>"""
import csv, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
R = Path(sys.argv[1])
rd = lambda p: list(csv.DictReader(open(p), delimiter="\t"))
seq = {r["id"]: r["sequence"] for r in rd(R/"data/processed/labels_exp151.tsv")}
P = {r["id"]: r for r in rd(R/"runs/contact_gat_idrome_sparse/predictions_exp151.tsv")}
groups = defaultdict(list)
for i, s in seq.items(): groups["".join(sorted(s))].append(i)
multi = [g for g in groups.values() if len(g) > 1]
print("permutation groups:", len(multi), "sequences in them:", sum(map(len, multi)))
hit = tot = 0
for g in multi:
    t = np.array([float(P[i]["rg_true_nm"]) for i in g]); p = np.array([float(P[i]["rg_pred_nm"]) for i in g])
    print(f"  n={len(g)} len={len(seq[g[0]])} true range {t.min():.2f}-{t.max():.2f}  GAT range {p.min():.2f}-{p.max():.2f}  spearman-ish order agree: {np.corrcoef(np.argsort(np.argsort(t)), np.argsort(np.argsort(p)))[0,1]:.2f}")
    print("     e.g.", seq[g[0]][:60])
