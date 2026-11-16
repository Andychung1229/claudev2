"""Frozen graph builder from commit 26673f7; regression oracle."""
from __future__ import annotations
import numpy as np
from contact_mpnn.aa import AA_INDEX
from contact_mpnn.contacts import ContactTable, N_BANDS, sep_band_index
N_AA = 20

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
