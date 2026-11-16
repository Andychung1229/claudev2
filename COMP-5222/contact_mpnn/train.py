"""训练 / 验证循环。默认不在建模阶段调用。"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import yaml
from torch.optim import AdamW

from .dataset import IdromeGraphDataset, make_loader
from .model import ContactGAT


def set_seed(seed: int) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _log_base(tcfg: dict) -> str:
    return str(tcfg.get("log_base", "10"))


def _to_nm(pred: torch.Tensor, y: torch.Tensor, log_target: bool, log_base: str) -> tuple[torch.Tensor, torch.Tensor]:
    if not log_target:
        return pred, y
    if log_base in {"e", "ln", "nat"}:
        return torch.exp(pred), torch.exp(y)
    return torch.pow(10.0, pred), torch.pow(10.0, y)


def _dataset_kwargs(cfg: dict) -> dict:
    mcfg = cfg["model"]
    tcfg = cfg["train"]
    ccfg = cfg["contact"]
    gcfg = cfg.get("graph", {})
    return dict(
        max_len=int(mcfg["max_len"]),
        min_seq_sep=int(ccfg["min_seq_sep"]),
        log_target=bool(tcfg["log_target"]),
        log_base=_log_base(tcfg),
        graph_mode=str(gcfg.get("mode", "dense")),
        local_window=int(gcfg.get("local_window", 2)),
        topk=int(gcfg.get("topk", 8)),
        edge_rule=str(gcfg.get("edge_rule", "flat")),
        band_pseudocount=float(gcfg.get("band_pseudocount", 1e5)),
    )


@torch.no_grad()
def eval_metrics(model: nn.Module, loader, device: torch.device, log_target: bool, log_base: str = "10") -> dict:
    """原单位 MAE / RMSE / R2，以及 log 空间 MSE。"""
    model.eval()
    mae_log = []
    sq_log = []
    pred_nm_all = []
    y_nm_all = []
    for batch in loader:
        batch = {
            k: v.to(device, non_blocking=True) if torch.is_tensor(v) else v
            for k, v in batch.items()
        }
        with torch.amp.autocast("cuda", enabled=device.type == "cuda"):
            pred = model(batch).squeeze(-1)
        y = batch["y"].squeeze(-1)
        mae_log.append((pred - y).abs().cpu().numpy())
        sq_log.append(((pred - y) ** 2).cpu().numpy())
        pred_nm, y_nm = _to_nm(pred, y, log_target, log_base)
        pred_nm_all.append(pred_nm.detach().float().cpu().numpy())
        y_nm_all.append(y_nm.detach().float().cpu().numpy())
    if not mae_log:
        return {
            "val_log_mae": float("nan"),
            "val_log_mse": float("nan"),
            "val_mae_nm": float("nan"),
            "val_rmse_nm": float("nan"),
            "val_r2": float("nan"),
            "val_log10_mae": float("nan"),
        }
    pred_nm = np.concatenate(pred_nm_all)
    y_nm = np.concatenate(y_nm_all)
    ss_res = float(np.sum((pred_nm - y_nm) ** 2))
    ss_tot = float(np.sum((y_nm - y_nm.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    log_mae = float(np.concatenate(mae_log).mean())
    return {
        "val_log_mae": log_mae,
        "val_log_mse": float(np.concatenate(sq_log).mean()),
        "val_mae_nm": float(np.mean(np.abs(pred_nm - y_nm))),
        "val_rmse_nm": float(np.sqrt(np.mean((pred_nm - y_nm) ** 2))),
        "val_r2": r2,
        "val_log10_mae": log_mae,
    }


def train_loop(cfg: dict, table, device: torch.device | None = None) -> Path:
    device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
    set_seed(int(cfg["train"]["seed"]))
    p = cfg["paths"]
    mcfg = cfg["model"]
    tcfg = cfg["train"]
    gcfg = cfg.get("graph", {})
    out = Path(p["out_dir"])
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    dkw = _dataset_kwargs(cfg)
    log_base = dkw["log_base"]

    train_ds = IdromeGraphDataset(p["train_tsv"], table, **dkw)
    val_ds = IdromeGraphDataset(p["val_tsv"], table, **dkw)
    test_path = p.get("test_tsv")
    test_ds = IdromeGraphDataset(test_path, table, **dkw) if test_path else None
    pair_budget = int(tcfg.get("pair_budget", 0)) or None
    train_loader = make_loader(
        train_ds,
        int(tcfg["batch_size"]),
        True,
        int(tcfg["num_workers"]),
        pair_budget=pair_budget,
        seed=int(tcfg["seed"]),
    )
    val_loader = make_loader(
        val_ds,
        int(tcfg["batch_size"]),
        False,
        int(tcfg["num_workers"]),
        pair_budget=pair_budget,
        seed=int(tcfg["seed"]),
    )
    if device.type == "cuda":
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        torch.backends.cudnn.benchmark = True
    loss_name = str(tcfg.get("loss", "l1")).lower()
    print(
        f"device={device}  train_n={len(train_ds)}  val_n={len(val_ds)}  "
        f"test_n={len(test_ds) if test_ds is not None else 0}  "
        f"loss={loss_name}  log_target={bool(tcfg['log_target'])}  log_base={log_base}  "
        f"graph={gcfg.get('mode', 'dense')}  w={gcfg.get('local_window', '-')}  k={gcfg.get('topk', '-')}  "
        f"batch={tcfg['batch_size']}  pair_budget={pair_budget}  amp={bool(tcfg.get('amp', True))}",
        flush=True,
    )

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
    ).to(device)
    n_param = sum(x.numel() for x in model.parameters())
    print(
        f"model=ContactGAT  layers={mcfg['n_layers']}  heads={mcfg.get('n_heads', 4)}  "
        f"hidden={mcfg['hidden']}  node_dim={mcfg.get('node_dim', 20)}  "
        f"edge_in={mcfg.get('edge_in', 4)}  edge_mlp={mcfg.get('edge_hidden', 8)}  "
        f"readout={mcfg.get('readout', 'attn')}  params={n_param}",
        flush=True,
    )
    opt = AdamW(model.parameters(), lr=float(tcfg["lr"]), weight_decay=float(tcfg["weight_decay"]))
    if loss_name in {"mse", "l2"}:
        loss_fn = nn.MSELoss()
    else:
        loss_fn = nn.L1Loss()
    use_amp = bool(tcfg.get("amp", True)) and device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
    stop_key = str(tcfg.get("early_stop_metric", "val_log10_mae"))

    best = float("inf")
    stale = 0
    history = []
    for epoch in range(1, int(tcfg["epochs"]) + 1):
        model.train()
        losses = []
        for batch in train_loader:
            batch = {
                k: v.to(device, non_blocking=True) if torch.is_tensor(v) else v
                for k, v in batch.items()
            }
            opt.zero_grad(set_to_none=True)
            with torch.amp.autocast("cuda", enabled=use_amp):
                pred = model(batch)
                loss = loss_fn(pred, batch["y"])
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(opt)
            scaler.update()
            losses.append(float(loss.detach()))
        mets = eval_metrics(model, val_loader, device, bool(tcfg["log_target"]), log_base)
        rec = {
            "epoch": epoch,
            "train_loss": float(np.mean(losses)),
            "train_log10_mae": float(np.mean(losses)),
            **mets,
        }
        history.append(rec)
        print(
            f"epoch {epoch:3d}  train_loss={rec['train_loss']:.5f}  "
            f"val_mae={mets['val_mae_nm']:.4f} nm  val_rmse={mets['val_rmse_nm']:.4f} nm  "
            f"val_r2={mets['val_r2']:.4f}  val_log_mse={mets['val_log_mse']:.5f}",
            flush=True,
        )
        score = float(mets.get(stop_key, mets["val_mae_nm"]))
        if score < best:
            best = score
            stale = 0
            torch.save(
                {
                    "model": model.state_dict(),
                    "cfg": cfg,
                    "best_metric": best,
                    "best_stop_key": stop_key,
                    "best_val_mae_nm": mets["val_mae_nm"],
                    "best_val_rmse_nm": mets["val_rmse_nm"],
                    "best_val_r2": mets["val_r2"],
                    "best_val_log10_mae": mets["val_log_mae"],
                    "best_epoch": epoch,
                    "n_param": n_param,
                },
                out / "best.pt",
            )
        else:
            stale += 1
            if stale >= int(tcfg["patience"]):
                print(
                    f"early stop @ {epoch}  best_{stop_key}={best:.5f}",
                    flush=True,
                )
                break
    (out / "history.json").write_text(json.dumps(history, indent=2) + "\n")
    if test_ds is not None and (out / "best.pt").is_file():
        ckpt = torch.load(out / "best.pt", map_location=device, weights_only=False)
        model.load_state_dict(ckpt["model"])
        test_loader = make_loader(
            test_ds,
            int(tcfg["batch_size"]),
            False,
            int(tcfg["num_workers"]),
            pair_budget=pair_budget,
            seed=int(tcfg["seed"]),
        )
        test_mets = eval_metrics(model, test_loader, device, bool(tcfg["log_target"]), log_base)
        test_rec = {("test_" + k[4:] if k.startswith("val_") else k): v for k, v in test_mets.items()}
        (out / "test_metrics.json").write_text(json.dumps(test_rec, indent=2) + "\n")
        print(
            f"test  mae={test_mets['val_mae_nm']:.4f} nm  rmse={test_mets['val_rmse_nm']:.4f} nm  "
            f"r2={test_mets['val_r2']:.4f}",
            flush=True,
        )
    return out
