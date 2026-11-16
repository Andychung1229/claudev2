"""GAT：节点=氨基酸 one-hot（稀疏图再加归一化位置），边特征进入注意力。"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class GATLayer(nn.Module):
    """稠密 GAT（带边特征）。α_ij = softmax_j LeakyReLU(a_s·Wh_i + a_t·Wh_j + a_e·e_ij)。"""

    def __init__(
        self,
        hidden: int,
        edge_dim: int,
        n_heads: int,
        dropout: float,
        activate: bool = False,
    ) -> None:
        super().__init__()
        if hidden % n_heads != 0:
            raise ValueError(f"hidden={hidden} must divide n_heads={n_heads}")
        self.n_heads = n_heads
        self.d = hidden // n_heads
        self.activate = bool(activate)
        self.W = nn.Linear(hidden, hidden, bias=False)
        self.att_src = nn.Parameter(torch.empty(n_heads, self.d))
        self.att_dst = nn.Parameter(torch.empty(n_heads, self.d))
        self.att_edge = nn.Linear(edge_dim, n_heads, bias=False)
        self.leaky = nn.LeakyReLU(0.2)
        self.drop = nn.Dropout(dropout)
        self.norm = nn.LayerNorm(hidden)
        self.reset_parameters()

    def reset_parameters(self) -> None:
        nn.init.xavier_uniform_(self.W.weight)
        nn.init.xavier_uniform_(self.att_src)
        nn.init.xavier_uniform_(self.att_dst)
        nn.init.xavier_uniform_(self.att_edge.weight)

    def forward(
        self,
        h: torch.Tensor,
        edge: torch.Tensor,
        edge_mask: torch.Tensor,
        return_attn: bool = False,
    ) -> torch.Tensor | tuple[torch.Tensor, torch.Tensor]:
        b, n, _ = h.shape
        wh = self.W(h).view(b, n, self.n_heads, self.d)
        src = (wh * self.att_src).sum(-1).unsqueeze(2)
        dst = (wh * self.att_dst).sum(-1).unsqueeze(1)
        e_bias = self.att_edge(edge)
        logits = self.leaky(src + dst + e_bias)
        fill = torch.finfo(logits.dtype).min
        logits = logits.masked_fill(edge_mask.unsqueeze(-1) < 0.5, fill)
        alpha = F.softmax(logits, dim=2)
        alpha = torch.nan_to_num(alpha, nan=0.0)
        alpha = self.drop(alpha)
        out = torch.einsum("bijh,bjhd->bihd", alpha, wh).reshape(b, n, -1)
        h_out = self.norm(h + out)
        if self.activate:
            h_out = F.elu(h_out)
        if return_attn:
            return h_out, alpha
        return h_out


class ContactGAT(nn.Module):
    def __init__(
        self,
        node_dim: int = 20,
        hidden: int = 64,
        n_layers: int = 3,
        edge_in: int = 4,
        edge_hidden: int = 8,
        n_heads: int = 4,
        dropout: float = 0.2,
        readout: str = "attn",
        activate: bool = False,
    ) -> None:
        super().__init__()
        self.readout = str(readout)
        self.node_embed = nn.Linear(node_dim, hidden)
        self.edge_mlp = nn.Sequential(
            nn.Linear(edge_in, edge_hidden),
            nn.GELU(),
            nn.Linear(edge_hidden, edge_hidden),
        )
        self.layers = nn.ModuleList(
            [
                GATLayer(hidden, edge_hidden, n_heads, dropout, activate=activate)
                for _ in range(n_layers)
            ]
        )
        if self.readout == "meanmax":
            self.attn = None
            self.head = nn.Sequential(
                nn.Linear(hidden * 2 + 1, hidden),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(hidden, 1),
            )
        else:
            self.attn = nn.Linear(hidden, 1)
            self.head = nn.Sequential(
                nn.Linear(hidden, hidden),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(hidden, 1),
            )

    def encode(
        self,
        batch: dict[str, torch.Tensor],
        return_attn: bool = False,
    ) -> torch.Tensor | tuple[torch.Tensor, torch.Tensor]:
        h = self.node_embed(batch["node"])
        e = self.edge_mlp(batch["edge"])
        nmask = batch["node_mask"].unsqueeze(-1)
        h = h * nmask
        attns = []
        for layer in self.layers:
            if return_attn:
                h, alpha = layer(h, e, batch["edge_mask"], return_attn=True)
                attns.append(alpha)
            else:
                h = layer(h, e, batch["edge_mask"])
            h = h * nmask
        if return_attn:
            return h, torch.stack(attns, dim=0)
        return h

    def _pool(self, h: torch.Tensor, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        if self.readout == "meanmax":
            nmask = batch["node_mask"]
            m = nmask.unsqueeze(-1)
            h_m = h * m
            denom = nmask.sum(dim=1, keepdim=True).clamp_min(1.0)
            mean = h_m.sum(dim=1) / denom
            fill = torch.finfo(h.dtype).min
            h_max = h.masked_fill(m < 0.5, fill)
            maxp = h_max.max(dim=1).values
            logn = torch.log(batch["length"].clamp_min(1).to(dtype=h.dtype)).unsqueeze(-1)
            return torch.cat([mean, maxp, logn], dim=-1)
        w = self.attn(h).squeeze(-1)
        w = w.masked_fill(batch["node_mask"] < 0.5, torch.finfo(w.dtype).min)
        a = torch.softmax(w, dim=1)
        return torch.einsum("bn,bnh->bh", a, h)

    def forward(
        self,
        batch: dict[str, torch.Tensor],
        return_attn: bool = False,
    ) -> torch.Tensor | tuple[torch.Tensor, torch.Tensor]:
        if return_attn:
            h, attns = self.encode(batch, return_attn=True)
        else:
            h = self.encode(batch)
        pooled = self._pool(h, batch)
        out = self.head(pooled)
        if return_attn:
            return out, attns
        return out
