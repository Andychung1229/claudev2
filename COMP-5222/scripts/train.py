#!/usr/bin/env python3
"""ContactGAT sparse 训练入口。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from contact_mpnn.contacts import ContactTable  # noqa: E402
from contact_mpnn.train import train_loop  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=ROOT / "configs/sparse_gat.yaml")
    args = ap.parse_args()
    cfg = yaml.safe_load(args.config.read_text())

    def _abs(p: str | Path) -> Path:
        p = Path(p)
        return p if p.is_absolute() else (ROOT / p)

    for key, val in list(cfg["paths"].items()):
        cfg["paths"][key] = str(_abs(val))
    table_path = Path(cfg["paths"]["contact_table"])
    if not table_path.is_file():
        raise SystemExit(
            f"缺少接触表 {table_path}。先运行 scripts/build_contact_table.py"
        )
    table = ContactTable.load(table_path)
    train_loop(cfg, table)


if __name__ == "__main__":
    main()
