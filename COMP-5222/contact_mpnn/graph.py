"""序列 + 接触表 → 图张量（pad 到 batch 最大 N）。

dense：旧跑法，|i-j|≥min_seq_sep 的稠密边。
sparse：PDF 构图——局部窗 + 每点 top-k 非局部边 + 自环。
"""
from __future__ import annotations

import numpy as np
import torch

from .aa import AA_INDEX
from .contacts import N_BANDS, ContactTable, sep_band_index

N_AA = 20
SPARSE_EDGE_DIM = 2 + N_BANDS + 2  # prior, |i-j|/N, band one-hot, local, self


def build_graph(
    sequence: str,
    interaction: np.ndarray,
    *,
    min_seq_sep: int = 2,
) -> dict[str, np.ndarray]:
    """单条序列（稠密边：|i-j|≥min_seq_sep）。

    node: (N, 20) one-hot
    edge: (N, N, 4)  [ε_{a_i a_j}, j-i, i/N, j/N]
    mask: (N, N)  |i-j| ≥ min_seq_sep（无上限）
    """
    seq = sequence.strip().upper()
    n = len(seq)
    node = np.zeros((n, N_AA), dtype=np.float32)
    aa = np.empty(n, dtype=np.int32)
    for i, c in enumerate(seq):
        if c not in AA_INDEX:
            raise ValueError(f"unknown residue {c!r}")
        aa[i] = AA_INDEX[c]
        node[i, AA_INDEX[c]] = 1.0

    ii, jj = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    rel = (jj - ii).astype(np.float32)
    n_f = float(n)
    i_frac = ii.astype(np.float32) / n_f
    j_frac = jj.astype(np.float32) / n_f
    mask = np.abs(rel) >= min_seq_sep
    eps = interaction[aa[:, None], aa[None, :]].astype(np.float32)
    edge = np.stack([eps, rel, i_frac, j_frac], axis=-1)
    edge = np.where(mask[..., None], edge, 0.0)
    return {
        "node": node,
        "edge": edge,
        "edge_mask": mask.astype(np.float32),
        "length": np.array(n, dtype=np.int32),
        "aa_idx": aa,
    }


def build_sparse_graph(
    sequence: str,
    table: ContactTable,
    *,
    local_window: int = 2,
    topk: int = 8,
    rank_eps: float = 1e-8,
) -> dict[str, np.ndarray]:
    """PDF 构图：局部边 1≤|i-j|≤w，非局部每点 top-k（无向下接触富集），加自环。

    边排序分：f_ab / (p_d + ε)。无 (aa,aa,band) 三维计数时，f_ab 用 20×20 频率，
    p_d 用表内按间隔带汇总的平均接触频率。边特征仍用原始频率 f_ab。
    """
    seq = sequence.strip().upper()
    n = len(seq)
    node = np.zeros((n, N_AA + 1), dtype=np.float32)
    aa = np.empty(n, dtype=np.int32)
    for i, c in enumerate(seq):
        if c not in AA_INDEX:
            raise ValueError(f"unknown residue {c!r}")
        aa[i] = AA_INDEX[c]
        node[i, AA_INDEX[c]] = 1.0
    denom = float(max(n - 1, 1))
    node[:, N_AA] = np.arange(n, dtype=np.float32) / denom

    ii, jj = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    abs_sep = np.abs(ii - jj)
    freq = table.frequency.astype(np.float32)
    f_ab = freq[aa[:, None], aa[None, :]]
    p_d = table.band_frequency().astype(np.float32)
    band = sep_band_index(abs_sep)
    p_ij = np.zeros((n, n), dtype=np.float32)
    valid_band = band >= 0
    p_ij[valid_band] = p_d[band[valid_band]]
    score = f_ab / (p_ij + rank_eps)

    local = (abs_sep >= 1) & (abs_sep <= local_window)
    self_loop = abs_sep == 0
    nl = abs_sep > local_window
    score_work = np.where(nl, score, -1e30).astype(np.float64)
    # 同分时取较小 j，保证可复现
    score_work = score_work - np.arange(n, dtype=np.float64)[None, :] * 1e-12
    k_eff = min(int(topk), n)
    topk_mask = np.zeros((n, n), dtype=bool)
    if k_eff > 0 and n > 0:
        idx = np.argpartition(score_work, -k_eff, axis=1)[:, -k_eff:]
        rows = np.arange(n)[:, None]
        topk_mask[rows, idx] = nl[rows, idx]
        topk_mask |= topk_mask.T

    mask = local | self_loop | topk_mask
    band_oh = np.zeros((n, n, N_BANDS), dtype=np.float32)
    if np.any(valid_band):
        bi, bj = np.nonzero(valid_band)
        band_oh[bi, bj, band[bi, bj]] = 1.0
    sep_norm = abs_sep.astype(np.float32) / denom
    local_ind = local.astype(np.float32)
    self_ind = self_loop.astype(np.float32)
    prior = np.where(self_loop, 0.0, f_ab).astype(np.float32)
    edge = np.concatenate(
        [
            prior[..., None],
            sep_norm[..., None],
            band_oh,
            local_ind[..., None],
            self_ind[..., None],
        ],
        axis=-1,
    )
    edge = np.where(mask[..., None], edge, 0.0)
    return {
        "node": node,
        "edge": edge.astype(np.float32),
        "edge_mask": mask.astype(np.float32),
        "length": np.array(n, dtype=np.int32),
        "aa_idx": aa,
    }


def graphs_from_table(sequence: str, table: ContactTable, **kwargs) -> dict[str, np.ndarray]:
    mode = str(kwargs.pop("graph_mode", "dense"))
    if mode == "sparse":
        kw = dict(local_window=2, topk=8)
        kw.update({k: v for k, v in kwargs.items() if k in {"local_window", "topk", "rank_eps"}})
        return build_sparse_graph(sequence, table, **kw)
    kw = dict(min_seq_sep=table.min_seq_sep)
    kw.update({k: v for k, v in kwargs.items() if k == "min_seq_sep"})
    return build_graph(sequence, table.interaction, **kw)


def collate_graphs(
    items: list[dict],
) -> dict[str, torch.Tensor]:
    n_max = max(int(x["length"]) for x in items)
    b = len(items)
    n_dim = int(items[0]["node"].shape[-1])
    e_dim = int(items[0]["edge"].shape[-1])
    node = torch.zeros(b, n_max, n_dim)
    edge = torch.zeros(b, n_max, n_max, e_dim)
    emask = torch.zeros(b, n_max, n_max)
    nmask = torch.zeros(b, n_max)
    y = torch.zeros(b, 1)
    length = torch.zeros(b, dtype=torch.long)
    for i, it in enumerate(items):
        n = int(it["length"])
        node[i, :n] = torch.from_numpy(np.ascontiguousarray(it["node"]))
        edge[i, :n, :n] = torch.from_numpy(np.ascontiguousarray(it["edge"]))
        emask[i, :n, :n] = torch.from_numpy(np.ascontiguousarray(it["edge_mask"]))
        nmask[i, :n] = 1.0
        length[i] = n
        if "y" in it:
            y[i, 0] = float(it["y"])
    return {
        "node": node,
        "edge": edge,
        "edge_mask": emask,
        "node_mask": nmask,
        "length": length,
        "y": y,
    }
