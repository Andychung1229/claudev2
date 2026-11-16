#!/usr/bin/env python3
"""Count 8 Å contacts once; optionally restrict by training sequence strings."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contact_mpnn.contacts import (
    N_AA, N_BANDS, ContactTable, accumulate_chain, empty_accumulators,
    fasta_from_pdb_resnames, production_frames, seq_to_idx,
)

DEFAULT_ZIP = Path('/media/cbe/18TB HDD1/Rg_hpc4/data/raw/idrome/conformational_ensembles.zip')


def load_yaml_cutoff(config: Path | None) -> tuple[float, int, int, float]:
    defaults = (8.0, 2, 10, 1e-6)
    if config is None or not config.is_file():
        return defaults
    import yaml
    c = yaml.safe_load(config.read_text()).get('contact', {})
    return (float(c.get('cutoff_A', 8.0)), int(c.get('min_seq_sep', 2)),
            int(c.get('skip_equil_frames', 10)), float(c.get('log_delta', 1e-6)))


def _write_ckpt(path: Path, **arrays) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name.replace('.npz', '.writing.npz'))
    np.savez_compressed(tmp, **arrays)
    tmp.replace(path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--zip', type=Path, default=DEFAULT_ZIP)
    ap.add_argument('--out', type=Path, default=ROOT / 'data/processed/aa_contact_table.npz')
    ap.add_argument('--config', type=Path, default=ROOT / 'configs/sparse_gat.yaml')
    ap.add_argument('--train-tsv', type=Path)
    ap.add_argument('--limit', type=int, default=0, help='first N trajectories; 0=all')
    ap.add_argument('--ckpt-every', type=int, default=200)
    args = ap.parse_args()
    if not args.zip.is_file():
        raise SystemExit(f'Missing trajectory archive: {args.zip}')
    if args.out.exists():
        raise SystemExit(f'Refusing to overwrite completed table: {args.out}')
    cutoff_A, min_sep, skip, delta = load_yaml_cutoff(args.config)
    train_sequences = None
    expected = None
    if args.train_tsv:
        with args.train_tsv.open() as f:
            rows = list(csv.DictReader(f, delimiter='\t'))
        train_sequences = {r['sequence'].strip().upper() for r in rows}
        expected = len(rows)
        if not expected:
            raise SystemExit('Training TSV is empty')
    identity = json.dumps({
        'zip': str(args.zip.resolve()), 'zip_size': args.zip.stat().st_size,
        'zip_mtime_ns': args.zip.stat().st_mtime_ns,
        'train_sha256': hashlib.sha256(args.train_tsv.read_bytes()).hexdigest() if args.train_tsv else None,
        'cutoff_A': cutoff_A, 'min_seq_sep': min_sep, 'skip': skip, 'limit': args.limit,
        'schema': 2,
    }, sort_keys=True)
    counts, opps, sep_c, sep_o = empty_accumulators(512)
    band_c = np.zeros((N_AA, N_AA, N_BANDS), dtype=np.float64)
    band_o = np.zeros_like(band_c)
    n_chains = n_frames_total = n_skipped = start = 0
    ckpt = args.out.with_suffix('.partial.npz')
    if ckpt.is_file():
        with np.load(ckpt, allow_pickle=False) as z:
            if 'identity' not in z or str(z['identity']) != identity:
                raise SystemExit('Checkpoint inputs/schema differ; use a new scratch --out path')
            counts, opps = z['counts'].copy(), z['opportunities'].copy()
            sep_c, sep_o = z['sep_counts'].copy(), z['sep_opps'].copy()
            band_c, band_o = z['band_counts'].copy(), z['band_opps'].copy()
            n_chains, n_frames_total = int(z['n_chains']), int(z['n_frames_total'])
            n_skipped, start = int(z['n_skipped']), int(z['n_done'])
        print(f'resume n_done={start} kept={n_chains} skipped={n_skipped}', flush=True)
    import mdtraj as md
    tmpdir = Path(os.environ.get('TMPDIR', tempfile.gettempdir()))
    if not tmpdir.is_dir():
        tmpdir = Path(tempfile.gettempdir())
    began = time.monotonic()
    with zipfile.ZipFile(args.zip) as z:
        infos = sorted((i for i in z.infolist() if i.filename.endswith('/traj.xtc')),
                       key=lambda i: i.header_offset)
        if args.limit > 0:
            infos = infos[:args.limit]
        total = len(infos)
        print(f'trajectories={total} expected_train={expected} tmp={tmpdir}', flush=True)
        with tempfile.TemporaryDirectory(dir=tmpdir) as tmp:
            top_p, xtc_p = Path(tmp) / 'top.pdb', Path(tmp) / 'traj.xtc'
            for k, info in enumerate(infos, 1):
                if k <= start:
                    continue
                top_p.write_bytes(z.read(info.filename.replace('traj.xtc', 'top.pdb')))
                topology = md.load_pdb(str(top_p)).topology
                sequence = fasta_from_pdb_resnames([r.name for r in topology.residues])
                if train_sequences is not None and sequence not in train_sequences:
                    n_skipped += 1
                else:
                    xtc_p.write_bytes(z.read(info.filename))
                    xyz = production_frames(md.load(str(xtc_p), top=str(top_p)).xyz, skip)
                    c, o, sc, so, bc, bo = accumulate_chain(
                        xyz, seq_to_idx(sequence), cutoff_nm=cutoff_A / 10,
                        min_seq_sep=min_sep, max_sep_bins=512)
                    counts += c
                    opps += o
                    sep_c += sc
                    sep_o += so
                    band_c += bc
                    band_o += bo
                    n_chains += 1
                    n_frames_total += len(xyz)
                if k % 50 == 0 or k == total:
                    print(f'{k}/{total} kept={n_chains} skipped={n_skipped} frames={n_frames_total}', flush=True)
                if args.ckpt_every > 0 and (k % args.ckpt_every == 0 or k == total):
                    _write_ckpt(ckpt, counts=counts, opportunities=opps,
                                sep_counts=sep_c, sep_opps=sep_o, band_counts=band_c,
                                band_opps=band_o, n_chains=n_chains, n_frames_total=n_frames_total,
                                n_skipped=n_skipped, n_done=k, identity=identity)
    if expected is not None and args.limit == 0 and abs(n_chains - expected) > max(1, expected * .01):
        raise SystemExit(f'Train count far off: kept {n_chains}, expected {expected}; checkpoint retained')
    table = ContactTable(cutoff_A=cutoff_A, min_seq_sep=min_sep, counts=counts,
                         opportunities=opps, sep_counts=sep_c, sep_opps=sep_o,
                         n_chains=n_chains, n_frames_total=n_frames_total,
                         log_delta=delta, band_counts=band_c, band_opps=band_o)
    table.save(args.out)
    meta_path = args.out.with_name(args.out.stem + '_meta.json')
    meta = json.loads(meta_path.read_text())
    meta.update({'source': json.loads(identity), 'n_skipped': n_skipped,
                 'expected_train_chains': expected, 'wall_seconds_this_pass': time.monotonic() - began})
    meta_path.write_text(json.dumps(meta, indent=2) + '\n')
    ckpt.unlink(missing_ok=True)
    print(f'wrote {args.out}; kept={n_chains} skipped={n_skipped}', flush=True)


if __name__ == '__main__':
    main()
