"""Per-seed MAE table for the ablation. Usage: seed_mae.py <exp dir> -> JSON"""
import csv, json, sys
from pathlib import Path
D = Path(sys.argv[1]); out = {}
for ds in ("test", "exp151"):
    for v in ("full", "distance_only", "local_only"):
        ms = []
        for s in (42, 43, 44):
            r = list(csv.DictReader(open(D / f"{v}_s{s}_{ds}.tsv"), delimiter="\t"))
            ms.append(round(sum(abs(float(x["rg_pred_nm"]) - float(x["rg_true_nm"])) for x in r) / len(r), 4))
        out[f"{ds}/{v}"] = ms
print(json.dumps(out))
