"""8 Å 非相邻接触计数 → 频率 → 归一化相互作用强度。

约定（与 Human IDRome 发表分析一致）：
- 坐标单位 nm（mdtraj）；cutoff_A=8 → 0.8 nm
- 丢掉平衡段前 skip_equil_frames 帧
- 非相邻：序列间隔 |i-j| ≥ min_seq_sep（默认 2）
- 氨基酸对表对称：C_ab = C_ba
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .aa import AA_INDEX, AA_ORDER, THREE_TO_ONE

N_AA = 20
# PDF: 1, 2–4, 5–8, 9–16, 17–32, >32
SEP_BANDS: tuple[tuple[int, int | None], ...] = (
    (1, 1),
    (2, 4),
    (5, 8),
    (9, 16),
    (17, 32),
    (33, None),
)
N_BANDS = len(SEP_BANDS)


def sep_band_index(sep: np.ndarray | int) -> np.ndarray | int:
    """Map sequence separation |i-j| onto the six PDF bands. Self (0) → -1."""
    s = np.asarray(sep)
    scalar = s.ndim == 0
    b = np.full(s.shape, -1, dtype=np.int32)
    b = np.where(s >= 1, 0, b)
    b = np.where(s >= 2, 1, b)
    b = np.where(s >= 5, 2, b)
    b = np.where(s >= 9, 3, b)
    b = np.where(s >= 17, 4, b)
    b = np.where(s >= 33, 5, b)
    if scalar:
        return int(np.asarray(b).reshape(-1)[0])
    return b


@dataclass
class ContactTable:
    """全局氨基酸对接触统计与归一化相互作用。"""

    cutoff_A: float
    min_seq_sep: int
    counts: np.ndarray  # (20, 20) float64
    opportunities: np.ndarray  # (20, 20) float64
    sep_counts: np.ndarray  # (S,) 按间隔汇总的接触
    sep_opps: np.ndarray  # (S,)
    n_chains: int
    n_frames_total: int
    log_delta: float = 1e-6

    @property
    def frequency(self) -> np.ndarray:
        return np.divide(
            self.counts,
            self.opportunities,
            out=np.zeros_like(self.counts),
            where=self.opportunities > 0,
        )

    @property
    def sep_frequency(self) -> np.ndarray:
        return np.divide(
            self.sep_counts,
            self.sep_opps,
            out=np.zeros_like(self.sep_counts),
            where=self.sep_opps > 0,
        )

    @property
    def interaction(self) -> np.ndarray:
        """ε_ab = log((f_ab+δ)/(f_global+δ))，f_global 为全表平均频率。"""
        f = self.frequency
        f_ref = float(f[self.opportunities > 0].mean()) if np.any(self.opportunities > 0) else 0.0
        d = self.log_delta
        eps = np.log((f + d) / (f_ref + d))
        eps = 0.5 * (eps + eps.T)
        return eps.astype(np.float32)

    def band_frequency(self) -> np.ndarray:
        """p_d: mean contact frequency in each sequence-separation band."""
        out = np.zeros(N_BANDS, dtype=np.float64)
        n_sep = int(self.sep_counts.shape[0])
        for b, (lo, hi) in enumerate(SEP_BANDS):
            end = n_sep if hi is None else min(hi + 1, n_sep)
            start = min(lo, n_sep)
            if start >= end:
                continue
            c = float(self.sep_counts[start:end].sum())
            o = float(self.sep_opps[start:end].sum())
            out[b] = c / o if o > 0 else 0.0
        return out

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path,
            cutoff_A=self.cutoff_A,
            min_seq_sep=self.min_seq_sep,
            counts=self.counts,
            opportunities=self.opportunities,
            sep_counts=self.sep_counts,
            sep_opps=self.sep_opps,
            n_chains=self.n_chains,
            n_frames_total=self.n_frames_total,
            log_delta=self.log_delta,
            aa_order=np.array(list(AA_ORDER)),
            interaction=self.interaction,
            frequency=self.frequency,
        )
        self.save_tables(path.with_suffix(""))

    def save_tables(self, stem: Path) -> None:
        """写出可读的 20×20 频率 / ε 表（不含轨迹）。"""
        import json

        stem = Path(stem)
        aa = list(AA_ORDER)
        freq = self.frequency
        eps = self.interaction
        for name, mat in (("freq", freq), ("eps", eps)):
            lines = ["aa\t" + "\t".join(aa)]
            for i, a in enumerate(aa):
                lines.append(a + "\t" + "\t".join(f"{mat[i, j]:.6g}" for j in range(N_AA)))
            (stem.parent / f"{stem.name}_{name}.tsv").write_text("\n".join(lines) + "\n")
        pair_lines = ["aa_i\taa_j\tcounts\topportunities\tfreq\teps"]
        for i, a in enumerate(aa):
            for j, b in enumerate(aa):
                if j < i:
                    continue
                pair_lines.append(
                    f"{a}\t{b}\t{self.counts[i, j]:.1f}\t{self.opportunities[i, j]:.1f}\t"
                    f"{freq[i, j]:.8g}\t{float(eps[i, j]):.8g}"
                )
        (stem.parent / f"{stem.name}_pairs.tsv").write_text("\n".join(pair_lines) + "\n")
        meta = {
            "cutoff_A": self.cutoff_A,
            "min_seq_sep": self.min_seq_sep,
            "n_chains": self.n_chains,
            "n_frames_total": self.n_frames_total,
            "log_delta": self.log_delta,
            "mean_freq": float(freq[self.opportunities > 0].mean()) if np.any(self.opportunities > 0) else 0.0,
            "aa_order": aa,
        }
        (stem.parent / f"{stem.name}_meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    @classmethod
    def load(cls, path: Path) -> "ContactTable":
        z = np.load(path, allow_pickle=False)
        return cls(
            cutoff_A=float(z["cutoff_A"]),
            min_seq_sep=int(z["min_seq_sep"]),
            counts=z["counts"].astype(np.float64),
            opportunities=z["opportunities"].astype(np.float64),
            sep_counts=z["sep_counts"].astype(np.float64),
            sep_opps=z["sep_opps"].astype(np.float64),
            n_chains=int(z["n_chains"]),
            n_frames_total=int(z["n_frames_total"]),
            log_delta=float(z["log_delta"]),
        )


def production_frames(xyz: np.ndarray, skip: int = 10) -> np.ndarray:
    n = xyz.shape[0]
    if n >= 1010:
        return xyz[skip:1010]
    if n > skip:
        return xyz[skip:]
    return xyz


def seq_to_idx(seq: str) -> np.ndarray:
    idx = np.empty(len(seq), dtype=np.int32)
    for i, c in enumerate(seq.upper()):
        if c not in AA_INDEX:
            raise ValueError(f"unknown amino acid {c!r} at {i}")
        idx[i] = AA_INDEX[c]
    return idx


def accumulate_chain(
    xyz_nm: np.ndarray,
    aa_idx: np.ndarray,
    *,
    cutoff_nm: float,
    min_seq_sep: int,
    max_sep_bins: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """一条链所有生产帧：更新 20×20 与按间隔的接触/观测。

    xyz_nm: (F, N, 3) nm
    """
    n_frames, n, _ = xyz_nm.shape
    counts = np.zeros((N_AA, N_AA), dtype=np.float64)
    opps = np.zeros((N_AA, N_AA), dtype=np.float64)
    sep_c = np.zeros(max_sep_bins, dtype=np.float64)
    sep_o = np.zeros(max_sep_bins, dtype=np.float64)
    cutoff2 = cutoff_nm * cutoff_nm
    for sep in range(min_seq_sep, n):
        diff = xyz_nm[:, : n - sep] - xyz_nm[:, sep:]
        r2 = np.einsum("fnk,fnk->fn", diff, diff)
        hit = (r2 < cutoff2).sum(axis=0)  # (n-sep,)
        a = aa_idx[: n - sep]
        b = aa_idx[sep:]
        np.add.at(counts, (a, b), hit)
        np.add.at(counts, (b, a), hit)
        np.add.at(opps, (a, b), n_frames)
        np.add.at(opps, (b, a), n_frames)
        sbin = min(sep, max_sep_bins - 1)
        sep_c[sbin] += float(hit.sum())
        sep_o[sbin] += float(n_frames * (n - sep))
    # 同型对角被 add.at 加了两次
    diag = np.arange(N_AA)
    counts[diag, diag] *= 0.5
    opps[diag, diag] *= 0.5
    return counts, opps, sep_c, sep_o


def empty_accumulators(max_sep_bins: int = 512) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    return (
        np.zeros((N_AA, N_AA), dtype=np.float64),
        np.zeros((N_AA, N_AA), dtype=np.float64),
        np.zeros(max_sep_bins, dtype=np.float64),
        np.zeros(max_sep_bins, dtype=np.float64),
    )


def fasta_from_pdb_resnames(resnames: list[str]) -> str:
    return "".join(THREE_TO_ONE[n] for n in resnames)
