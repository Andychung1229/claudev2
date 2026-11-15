"""Human IDRome 序列 + Rg 标签 → 图。"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

from .contacts import ContactTable
from .graph import build_graph, build_sparse_graph, collate_graphs


class IdromeGraphDataset(Dataset):
    def __init__(
        self,
        tsv: str | Path,
        table: ContactTable,
        *,
        max_len: int = 512,
        min_seq_sep: int | None = None,
        log_target: bool = True,
        log_base: str = "10",
        graph_mode: str = "dense",
        local_window: int = 2,
        topk: int = 8,
        sequence_col: str = "sequence",
        label_col: str = "rg_nm",
        id_col: str = "id",
    ) -> None:
        self.df = pd.read_csv(tsv, sep="\t")
        seqs = self.df[sequence_col].astype(str).str.strip()
        keep = seqs.str.len().between(1, max_len)
        n_skip = int((~keep).sum())
        if n_skip:
            print(f"{Path(tsv).name}: skip {n_skip} sequences with N not in [1, {max_len}]", flush=True)
        self.df = self.df.loc[keep].reset_index(drop=True)
        self.table = table
        self.min_seq_sep = int(min_seq_sep if min_seq_sep is not None else table.min_seq_sep)
        self.log_target = bool(log_target)
        self.log_base = str(log_base)
        self.graph_mode = str(graph_mode)
        self.local_window = int(local_window)
        self.topk = int(topk)
        self.sequence_col = sequence_col
        self.label_col = label_col
        self.id_col = id_col
        self.interaction = table.interaction
        self.lengths = self.df[self.sequence_col].astype(str).str.len().to_numpy(dtype=np.int32)

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> dict:
        row = self.df.iloc[idx]
        seq = str(row[self.sequence_col]).strip()
        if self.graph_mode == "sparse":
            g = build_sparse_graph(
                seq,
                self.table,
                local_window=self.local_window,
                topk=self.topk,
            )
        else:
            g = build_graph(seq, self.interaction, min_seq_sep=self.min_seq_sep)
        y = float(row[self.label_col])
        if self.log_target:
            y = max(y, 1e-6)
            g["y"] = float(np.log(y) if self.log_base in {"e", "ln", "nat"} else np.log10(y))
        else:
            g["y"] = y
        g["id"] = str(row[self.id_col]) if self.id_col in row.index else str(idx)
        return g


class LengthBudgetBatchSampler(torch.utils.data.Sampler):
    """按长度相近组 batch，使 B·N² 贴近 pair_budget，把 GPU 填满。"""

    def __init__(
        self,
        lengths: np.ndarray,
        *,
        pair_budget: int,
        max_batch: int,
        shuffle: bool,
        seed: int = 42,
    ) -> None:
        self.lengths = np.asarray(lengths, dtype=np.int32)
        self.pair_budget = int(pair_budget)
        self.max_batch = int(max_batch)
        self.shuffle = bool(shuffle)
        self.seed = int(seed)
        self.epoch = 0

    def __iter__(self):
        rng = np.random.RandomState(self.seed + self.epoch)
        self.epoch += 1
        order = np.argsort(self.lengths, kind="mergesort")
        if self.shuffle:
            win = 256
            for s in range(0, len(order), win):
                sl = order[s : s + win]
                rng.shuffle(sl)
                order[s : s + win] = sl
        i = 0
        n = len(order)
        batches = []
        while i < n:
            nmax = int(self.lengths[order[i]])
            j = i + 1
            while j < n:
                nmax_j = max(nmax, int(self.lengths[order[j]]))
                bs = max(1, min(self.max_batch, self.pair_budget // max(nmax_j * nmax_j, 1)))
                if (j - i + 1) > bs:
                    break
                nmax = nmax_j
                j += 1
            batches.append(order[i:j].tolist())
            i = j
        if self.shuffle:
            rng.shuffle(batches)
        yield from batches

    def __len__(self) -> int:
        return max(1, (len(self.lengths) + self.max_batch - 1) // self.max_batch)


def make_loader(
    dataset: IdromeGraphDataset,
    batch_size: int,
    shuffle: bool,
    num_workers: int = 0,
    *,
    pair_budget: int | None = None,
    seed: int = 42,
):
    kwargs = dict(
        collate_fn=collate_graphs,
        num_workers=num_workers,
        pin_memory=True,
        persistent_workers=num_workers > 0,
    )
    if pair_budget:
        sampler = LengthBudgetBatchSampler(
            dataset.lengths,
            pair_budget=pair_budget,
            max_batch=batch_size,
            shuffle=shuffle,
            seed=seed,
        )
        return torch.utils.data.DataLoader(dataset, batch_sampler=sampler, **kwargs)
    return torch.utils.data.DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        drop_last=False,
        **kwargs,
    )
