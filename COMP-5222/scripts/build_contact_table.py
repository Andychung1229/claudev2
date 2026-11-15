#!/usr/bin/env python3
"""从 Human IDRome conformational_ensembles.zip 统计 8 Å 非相邻接触。

轨迹只在有 zip 的机器上扫一次；写出的是小表（npz + tsv），训练不再需要 zip。
默认 zip：Rg_hpc4 原始位置（不在 COMP-5222 内）。
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from contact_mpnn.contacts import (  # noqa: E402
    ContactTable,
    accumulate_chain,
    empty_accumulators,
    fasta_from_pdb_resnames,
    production_frames,
    seq_to_idx,
)

DEFAULT_ZIP = Path("/media/cbe/18TB HDD1/Rg_hpc4/data/raw/idrome/conformational_ensembles.zip")


def load_yaml_cutoff(config: Path | None) -> tuple[float, int, int, float]:
    cutoff_A, min_sep, skip, delta = 8.0, 2, 10, 1e-6
    if config is None or not config.is_file():
        return cutoff_A, min_sep, skip, delta
    import yaml

    cfg = yaml.safe_load(config.read_text())
    c = cfg.get("contact", {})
    return (
        float(c.get("cutoff_A", cutoff_A)),
        int(c.get("min_seq_sep", min_sep)),
        int(c.get("skip_equil_frames", skip)),
        float(c.get("log_delta", delta)),
    )


def _write_ckpt(path: Path, *, counts, opps, sep_c, sep_o, n_chains, n_frames, n_done) -> None:
    import numpy as np

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name.replace(".npz", ".writing.npz"))
    np.savez_compressed(
        tmp,
        counts=counts,
        opportunities=opps,
        sep_counts=sep_c,
        sep_opps=sep_o,
        n_chains=n_chains,
        n_frames_total=n_frames,
        n_done=n_done,
    )
    Path(tmp).replace(path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    ap.add_argument("--out", type=Path, default=ROOT / "data/processed/aa_contact_table.npz")
    ap.add_argument("--config", type=Path, default=ROOT / "configs/sparse_gat.yaml")
    ap.add_argument("--limit", type=int, default=0, help="只处理前 N 条，0=全部")
    ap.add_argument("--ckpt-every", type=int, default=200)
    args = ap.parse_args()

    if not args.zip.is_file():
        raise SystemExit(f"找不到轨迹 zip：{args.zip}（建表只需跑一次，训练不需要 zip）")

    cutoff_A, min_sep, skip, delta = load_yaml_cutoff(args.config)
    cutoff_nm = cutoff_A / 10.0
    counts, opps, sep_c, sep_o = empty_accumulators(512)
    n_chains = 0
    n_frames_total = 0
    start = 0
    ckpt = args.out.with_suffix(".partial.npz")
    if ckpt.is_file():
        import numpy as np

        z = np.load(ckpt)
        counts = z["counts"].astype(np.float64)
        opps = z["opportunities"].astype(np.float64)
        sep_c = z["sep_counts"].astype(np.float64)
        sep_o = z["sep_opps"].astype(np.float64)
        n_chains = int(z["n_chains"])
        n_frames_total = int(z["n_frames_total"])
        start = int(z["n_done"])
        print(f"resume from {ckpt}  n_done={start}  chains={n_chains}", flush=True)

    import mdtraj as md

    tmpdir = Path(os.environ.get("TMPDIR", "/dev/shm"))
    if not tmpdir.is_dir() or os.statvfs(str(tmpdir)).f_bavail * os.statvfs(str(tmpdir)).f_frsize < 64 * 1024**2:
        tmpdir = Path(tempfile.gettempdir())

    with zipfile.ZipFile(args.zip) as z:
        infos = [i for i in z.infolist() if i.filename.endswith("/traj.xtc")]
        infos.sort(key=lambda i: i.header_offset)
        if args.limit > 0:
            infos = infos[: args.limit]
        n_all = len(infos)
        print(f"xtc={n_all}  zip={args.zip}  tmp={tmpdir}", flush=True)
        with tempfile.TemporaryDirectory(dir=str(tmpdir)) as tmp:
            top_p = Path(tmp) / "top.pdb"
            xtc_p = Path(tmp) / "traj.xtc"
            for k, info in enumerate(infos, 1):
                if k <= start:
                    continue
                top_name = info.filename.replace("traj.xtc", "top.pdb")
                with z.open(top_name) as src, top_p.open("wb") as dst:
                    dst.write(src.read())
                with z.open(info.filename) as src, xtc_p.open("wb") as dst:
                    dst.write(src.read())
                traj = md.load(str(xtc_p), top=str(top_p))
                resnames = [res.name for res in traj.top.residues]
                fasta = fasta_from_pdb_resnames(resnames)
                xyz = production_frames(traj.xyz, skip=skip)
                aa = seq_to_idx(fasta)
                c, o, sc, so = accumulate_chain(
                    xyz, aa, cutoff_nm=cutoff_nm, min_seq_sep=min_sep, max_sep_bins=512
                )
                counts += c
                opps += o
                sep_c += sc
                sep_o += so
                n_chains += 1
                n_frames_total += int(xyz.shape[0])
                if k % 50 == 0 or k == n_all:
                    print(
                        f"{k}/{n_all}  chains={n_chains}  frames={n_frames_total}",
                        flush=True,
                    )
                if args.ckpt_every > 0 and (k % args.ckpt_every == 0 or k == n_all):
                    _write_ckpt(
                        ckpt,
                        counts=counts,
                        opps=opps,
                        sep_c=sep_c,
                        sep_o=sep_o,
                        n_chains=n_chains,
                        n_frames=n_frames_total,
                        n_done=k,
                    )

    table = ContactTable(
        cutoff_A=cutoff_A,
        min_seq_sep=min_sep,
        counts=counts,
        opportunities=opps,
        sep_counts=sep_c,
        sep_opps=sep_o,
        n_chains=n_chains,
        n_frames_total=n_frames_total,
        log_delta=delta,
    )
    table.save(args.out)
    if ckpt.is_file():
        ckpt.unlink()
    print(f"wrote {args.out}  n_chains={n_chains}  mean_f={table.frequency[opps > 0].mean():.6f}")


if __name__ == "__main__":
    main()
