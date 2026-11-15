#!/usr/bin/env python3
"""Human IDRome 70/15/15 分组划分：同一 UniProt、相同序列留在同一折。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _union_find(n: int):
    parent = np.arange(n, dtype=np.int32)

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = int(parent[x])
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    return parent, find, union


def main() -> None:
    seed = 42
    out_dir = ROOT / "data/processed"
    db = pd.read_csv(ROOT / "data/raw/idrome/IDRome_DB.csv")
    df = pd.DataFrame(
        {
            "id": db["seq_name"],
            "sequence": db["fasta"].astype(str).str.strip(),
            "seq_len": db["N"].astype(int),
            "rg_nm": db["Rg/nm"].astype(float),
            "source": "HumanIDRome",
            "data_type": "simulation",
            "orig_id": db["seq_name"],
            "UniProt_ID": db["UniProt_ID"].astype(str),
        }
    )
    missing = int(df["UniProt_ID"].isna().sum())
    if missing:
        raise SystemExit(f"缺少 UniProt_ID: {missing}")
    n = len(df)
    _, find, union = _union_find(n)
    up_first: dict[str, int] = {}
    for i, uid in enumerate(df["UniProt_ID"].astype(str)):
        if uid in up_first:
            union(up_first[uid], i)
        else:
            up_first[uid] = i
    seq_first: dict[str, int] = {}
    for i, seq in enumerate(df["sequence"].astype(str)):
        if seq in seq_first:
            union(seq_first[seq], i)
        else:
            seq_first[seq] = i
    root_of = np.fromiter((find(i) for i in range(n)), dtype=np.int32, count=n)
    groups = {}
    for i, r in enumerate(root_of):
        groups.setdefault(int(r), []).append(i)
    gids = sorted(groups)
    rng = np.random.RandomState(seed)
    rng.shuffle(gids)
    n_g = len(gids)
    n_train = int(round(0.70 * n_g))
    n_val = int(round(0.15 * n_g))
    train_g = set(gids[:n_train])
    val_g = set(gids[n_train : n_train + n_val])
    test_g = set(gids[n_train + n_val :])
    split = np.full(n, "train", dtype=object)
    for r, idxs in groups.items():
        if r in val_g:
            lab = "val"
        elif r in test_g:
            lab = "test"
        else:
            lab = "train"
        split[idxs] = lab
    df["split"] = split
    keep_cols = [
        "id",
        "sequence",
        "seq_len",
        "rg_nm",
        "source",
        "data_type",
        "split",
        "orig_id",
        "UniProt_ID",
    ]
    for name in ("train", "val", "test"):
        part = df.loc[df["split"] == name, keep_cols]
        path = out_dir / f"idrome_split_{name}.tsv"
        part.to_csv(path, sep="\t", index=False)
        print(f"{name}: n={len(part)}  groups={len(part['UniProt_ID'].unique())}  N<=512={(part.seq_len<=512).sum()}  -> {path}")
    meta = {
        "seed": seed,
        "rule": "same UniProt_ID and identical sequences stay together; 70/15/15 of connected groups",
        "n_sequences": int(n),
        "n_groups": int(n_g),
        "n_uniprot": int(df["UniProt_ID"].nunique()),
        "n_train_groups": int(len(train_g)),
        "n_val_groups": int(len(val_g)),
        "n_test_groups": int(len(test_g)),
        "n_train": int((df.split == "train").sum()),
        "n_val": int((df.split == "val").sum()),
        "n_test": int((df.split == "test").sum()),
        "n_train_le512": int(((df.split == "train") & (df.seq_len <= 512)).sum()),
        "n_val_le512": int(((df.split == "val") & (df.seq_len <= 512)).sum()),
        "n_test_le512": int(((df.split == "test") & (df.seq_len <= 512)).sum()),
    }
    (out_dir / "idrome_split_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
