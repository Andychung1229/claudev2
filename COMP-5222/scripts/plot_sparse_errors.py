#!/usr/bin/env python3
"""contact_gat_idrome_sparse：测试集 / 实验 Rg 误差图。默认 CPU，不占 GPU。"""
from __future__ import annotations

import json
import argparse
import sys
from pathlib import Path

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from contact_mpnn.contacts import ContactTable
from contact_mpnn.dataset import IdromeGraphDataset, make_loader
from contact_mpnn.model import ContactGAT
from contact_mpnn.train import _dataset_kwargs, _to_nm

RUN = ROOT / "runs" / "contact_gat_idrome_sparse"
EXP_TSV = ROOT / "data" / "processed" / "labels_exp151.tsv"
DPI = 600
INK = "#0b3d91"
INK_EDGE = "#071a40"
DEEP_BLUES = mcolors.LinearSegmentedColormap.from_list(
    "deep_blues",
    plt.cm.Blues(np.linspace(0.55, 1.0, 256)),
)


def _style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.labelsize": 12,
            "axes.titlesize": 12,
            "figure.dpi": 120,
            "savefig.dpi": DPI,
            "axes.linewidth": 0.8,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def metrics(y: np.ndarray, pred: np.ndarray) -> dict:
    err = pred - y
    r2 = 1.0 - float(np.sum(err**2) / np.sum((y - y.mean()) ** 2))
    pearson = float(np.corrcoef(y, pred)[0, 1]) if len(y) > 1 else float("nan")
    return {
        "n": int(len(y)),
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(np.sqrt(np.mean(err**2))),
        "r2": r2,
        "pearson": pearson,
        "mape": float(np.mean(np.abs(err) / np.maximum(y, 1e-6)) * 100.0),
    }


@torch.no_grad()
def predict_split(model, cfg, table, tsv: Path, device: torch.device) -> pd.DataFrame:
    dkw = _dataset_kwargs(cfg)
    ds = IdromeGraphDataset(tsv, table, **dkw)
    loader = make_loader(ds, batch_size=8, shuffle=False, num_workers=0)
    rows = []
    offset = 0
    log_target = bool(cfg["train"]["log_target"])
    log_base = dkw["log_base"]
    model.eval()
    for batch in loader:
        batch = {k: v.to(device) if torch.is_tensor(v) else v for k, v in batch.items()}
        pred = model(batch).squeeze(-1)
        y = batch["y"].squeeze(-1)
        pred_nm, y_nm = _to_nm(pred, y, log_target, log_base)
        pred_nm = pred_nm.float().cpu().numpy()
        y_nm = y_nm.float().cpu().numpy()
        n = len(pred_nm)
        chunk = ds.df.iloc[offset : offset + n]
        for i, (_, rec) in enumerate(chunk.iterrows()):
            rows.append(
                {
                    "id": rec["id"],
                    "seq_len": int(rec["seq_len"]) if "seq_len" in rec else int(len(str(rec["sequence"]))),
                    "rg_true_nm": float(y_nm[i]),
                    "rg_pred_nm": float(pred_nm[i]),
                }
            )
        offset += n
    return pd.DataFrame(rows)


def save_fig(fig, path: Path) -> None:
    fig.savefig(path.with_suffix(".png"), dpi=DPI, bbox_inches="tight", facecolor="white")
    fig.savefig(path.with_suffix(".svg"), bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", path.with_suffix(".png"))


def plot_history(history: list[dict], best_epoch: int, out: Path) -> None:
    ep = [r["epoch"] for r in history]
    fig, ax = plt.subplots(figsize=(5.2, 3.8))
    ax.plot(ep, [r["val_mae_nm"] for r in history], color="#1f4e79", lw=1.6, label="val MAE")
    ax.plot(ep, [r["val_rmse_nm"] for r in history], color="#c0392b", lw=1.4, ls="--", label="val RMSE")
    ax.axvline(best_epoch, color="0.45", ls=":", lw=1.0, label=f"best epoch {best_epoch}")
    ax.set_xlabel("epoch")
    ax.set_ylabel(r"$R_g$ error (nm)")
    ax.set_xlim(1, max(ep))
    ax.grid(True, ls="--", alpha=0.35)
    ax.legend(frameon=True, fontsize=9)
    fig.tight_layout()
    save_fig(fig, out / "history_val_error")


def _parity_box(ax, st: dict) -> None:
    ax.text(
        0.04,
        0.96,
        f"n = {st['n']}\n"
        f"MAE = {st['mae']:.3f} nm\n"
        f"RMSE = {st['rmse']:.3f} nm\n"
        f"$R^2$ = {st['r2']:.3f}\n"
        f"Pearson r = {st['pearson']:.3f}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="0.55", alpha=0.95),
    )


def plot_parity(
    frame: pd.DataFrame,
    st: dict,
    out: Path,
    stem: str,
    title: str,
    xlabel: str,
    dense: bool = False,
) -> None:
    y = frame.rg_true_nm.to_numpy()
    p = frame.rg_pred_nm.to_numpy()
    lo = float(min(y.min(), p.min()))
    hi = float(max(y.max(), p.max()))
    pad = 0.06 * max(hi - lo, 0.5)
    fig, ax = plt.subplots(figsize=(4.6, 4.6))
    ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad], color="0.2", ls="--", lw=1.1, zorder=2)
    if dense:
        hb = ax.hexbin(
            y,
            p,
            gridsize=42,
            cmap=DEEP_BLUES,
            mincnt=1,
            bins="log",
            linewidths=0.2,
            edgecolors="0.2",
        )
        fig.colorbar(hb, ax=ax, fraction=0.046, pad=0.04, label="count")
    else:
        ax.scatter(
            y,
            p,
            s=38,
            c=INK,
            alpha=0.9,
            edgecolors=INK_EDGE,
            linewidths=0.45,
            zorder=3,
        )
    ax.set_xlim(lo - pad, hi + pad)
    ax.set_ylim(lo - pad, hi + pad)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(r"predicted $R_g$ (nm)")
    ax.set_title(title)
    ax.grid(True, ls="--", alpha=0.3)
    _parity_box(ax, st)
    fig.tight_layout()
    save_fig(fig, out / stem)


def plot_residual(frame: pd.DataFrame, out: Path, stem: str, xlabel_true: str) -> None:
    y = frame.rg_true_nm.to_numpy()
    err = frame.rg_pred_nm.to_numpy() - y
    n = frame.seq_len.to_numpy()
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.7))
    for ax, x, xlab in (
        (axes[0], y, xlabel_true),
        (axes[1], n, "sequence length $N$"),
    ):
        ax.axhline(0.0, color="0.25", ls="--", lw=0.9)
        ax.scatter(
            x,
            err,
            s=16 if stem.startswith("exp") else 10,
            c=INK,
            alpha=0.7 if stem.startswith("exp") else 0.55,
            edgecolors=INK_EDGE,
            linewidths=0.25,
            rasterized=True,
        )
        ax.set_xlabel(xlab)
        ax.set_ylabel(r"pred $-$ true (nm)")
        ax.grid(True, ls="--", alpha=0.3)
    fig.tight_layout()
    save_fig(fig, out / stem)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, default=RUN)
    ap.add_argument("--no-figs", action="store_true")
    args = ap.parse_args()
    run = args.run.resolve()
    cfg = yaml.safe_load((run / "config.yaml").read_text())
    # Allow archived runs to be evaluated after moving to another host.
    for key in ("train_tsv", "val_tsv", "test_tsv", "contact_table"):
        p = Path(cfg["paths"][key])
        if not p.is_file():
            p = ROOT / p if not p.is_absolute() else ROOT / "data/processed" / p.name
        if not p.is_file():
            raise FileNotFoundError(f"{key}: {p}")
        cfg["paths"][key] = str(p)
    history = json.loads((run / "history.json").read_text())
    ckpt = torch.load(run / "best.pt", map_location="cpu", weights_only=False)
    best_epoch = int(ckpt["best_epoch"])
    if not args.no_figs:
        _style()
        plot_history(history, best_epoch, run)

    device = torch.device("cpu")
    table = ContactTable.load(Path(cfg["paths"]["contact_table"]))
    mcfg = cfg["model"]
    model = ContactGAT(
        node_dim=int(mcfg.get("node_dim", 20)),
        hidden=int(mcfg["hidden"]),
        n_layers=int(mcfg["n_layers"]),
        edge_in=int(mcfg.get("edge_in", 4)),
        edge_hidden=int(mcfg.get("edge_hidden", 8)),
        n_heads=int(mcfg.get("n_heads", 4)),
        dropout=float(mcfg["dropout"]),
        readout=str(mcfg.get("readout", "attn")),
        activate=bool(mcfg.get("activate", False)),
    )
    model.load_state_dict(ckpt["model"])
    model.to(device)
    model.eval()

    test_path = run / "predictions_test.tsv"
    test = predict_split(model, cfg, table, Path(cfg["paths"]["test_tsv"]), device)
    test.to_csv(test_path, sep="\t", index=False)
    st_test = metrics(test.rg_true_nm.to_numpy(), test.rg_pred_nm.to_numpy())
    print("test", json.dumps(st_test))
    if not args.no_figs:
        plot_parity(
            test,
            st_test,
            run,
            "test_parity",
            "ContactGAT sparse  ·  IDRome test",
            r"CALVADOS $R_g$ (nm)",
            dense=True,
        )
        plot_residual(test, run, "test_residual", r"CALVADOS $R_g$ (nm)")

    exp = predict_split(model, cfg, table, EXP_TSV, device)
    exp.to_csv(run / "predictions_exp151.tsv", sep="\t", index=False)
    st_exp = metrics(exp.rg_true_nm.to_numpy(), exp.rg_pred_nm.to_numpy())
    print("exp151", json.dumps(st_exp))
    if not args.no_figs:
        plot_parity(
            exp,
            st_exp,
            run,
            "exp151_parity",
            "ContactGAT sparse  ·  experimental $R_g$",
            r"experimental $R_g$ (nm)",
            dense=False,
        )
        plot_residual(exp, run, "exp151_residual", r"experimental $R_g$ (nm)")
    (run / "plot_metrics.json").write_text(
        json.dumps({"test": st_test, "exp151": st_exp, "best_epoch": best_epoch}, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
