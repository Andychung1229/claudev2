#!/usr/bin/env python3
"""Audit directed top-k choices and the resulting undirected graph on fixed chains."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contact_mpnn.aa import AA_INDEX
from contact_mpnn.contacts import ContactTable, SEP_BANDS, sep_band_index
from contact_mpnn.graph import build_sparse_graph, select_nonlocal

VARIANTS = ('full', 'local_only', 'distance_only', 'train_table', 'band_resolved')


def audit_variant(rows: pd.DataFrame, cfg: dict, table: ContactTable) -> dict:
    gcfg = cfg['graph']
    rule, k, w = gcfg.get('edge_rule', 'flat'), int(gcfg['topk']), int(gcfg['local_window'])
    histogram = np.zeros(len(SEP_BANDS), dtype=np.int64)
    far = selected = n_residues = undirected_degree_sum = 0
    per_chain_degree = []
    for seq in rows.sequence:
        n = len(seq)
        aa = np.array([AA_INDEX[a] for a in seq])
        sep = abs(np.arange(n)[:, None] - np.arange(n)[None, :])
        band = sep_band_index(sep)
        valid = band >= 0
        pd_ = table.band_frequency().astype(np.float32)
        pij = np.zeros((n, n), np.float32)
        pij[valid] = pd_[band[valid]]
        f = table.frequency.astype(np.float32)[aa[:, None], aa[None, :]]
        if rule == 'flat':
            score = f / (pij + 1e-8)
        elif rule == 'distance_only':
            score = 1.0 / (pij + 1e-8)
        else:
            enrichment = table.band_enrichment(float(gcfg.get('band_pseudocount', 1e5)))
            score = enrichment[aa[:, None], aa[None, :], np.maximum(band, 0)]
        nl = sep > w
        picked = select_nonlocal(score, nl, k, seq, rule)
        selected += int(picked.sum())
        histogram += np.bincount(band[picked], minlength=len(SEP_BANDS))
        farthest = np.where(nl, band, -1).max(axis=1)
        far += int((picked & (band == farthest[:, None])).sum())
        graph = build_sparse_graph(seq, table, local_window=w, topk=k, edge_rule=rule,
                                   band_pseudocount=float(gcfg.get('band_pseudocount', 1e5)))
        expected = picked | picked.T | (sep <= w)
        np.testing.assert_array_equal(graph['edge_mask'] > 0, expected)
        degree_sum = int(((graph['edge_mask'] > 0) & nl).sum())
        undirected_degree_sum += degree_sum
        per_chain_degree.append(degree_sum / n)
        n_residues += n
    fraction = far / selected if selected else None
    return {
        'status': 'complete', 'edge_rule': rule, 'topk': k, 'chains': len(rows),
        'residues': n_residues, 'directed_topk_selections': selected,
        'mean_nonlocal_edges_per_residue': undirected_degree_sum / n_residues,
        'mean_of_chain_mean_nonlocal_degree': float(np.mean(per_chain_degree)),
        'farthest_available_band_fraction': fraction,
        'chosen_partner_band_counts': histogram.tolist(),
        'chosen_partner_band_fractions': (histogram / selected).tolist() if selected else [0.] * len(SEP_BANDS),
        'band_resolved_gate': fraction < .90 if rule == 'band_resolved' and fraction is not None else None,
    }


def run_audit(root: Path, output: Path | None = None) -> dict:
    te = pd.read_csv(root / 'data/processed/idrome_split_test.tsv', sep='\t')
    te = te.loc[te.seq_len <= 512].reset_index(drop=True)
    sample = te.iloc[np.random.RandomState(0).choice(len(te), 300, replace=False)]
    report = {'sampling': 'RandomState(0), choice 300 without replacement, test N <= 512',
              'sample_ids': sample.id.tolist(), 'bands': list(SEP_BANDS),
              'definitions': {'degree': 'undirected non-local degree, weighted by residue count',
                              'band_histogram': 'directed selections before undirected union',
                              'E4_gate': 'farthest-band fraction < 0.90; otherwise investigate before training'},
              'variants': {}}
    for name in VARIANTS:
        cfg = yaml.safe_load((root / f'configs/edge_ablation/{name}.yaml').read_text())
        path = root / cfg['paths']['contact_table']
        if not path.is_file():
            report['variants'][name] = {'status': 'blocked_missing_contact_table', 'path': str(path)}
            print(f'{name}: BLOCKED, missing {path}', flush=True)
            continue
        result = audit_variant(sample, cfg, ContactTable.load(path))
        result['table_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        report['variants'][name] = result
        print(f'{name}: degree={result["mean_nonlocal_edges_per_residue"]:.3f}, '
              f'farthest={result["farthest_available_band_fraction"]}, '
              f'band_counts={result["chosen_partner_band_counts"]}', flush=True)
    output = output or root / 'experiments/edge_ablation/edge_audit.json'
    output.write_text(json.dumps(report, indent=2) + '\n')
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('root', type=Path, nargs='?', default=ROOT)
    args = ap.parse_args()
    report = run_audit(args.root.resolve())
    e4 = report['variants']['band_resolved']
    if e4['status'] == 'complete' and not e4['band_resolved_gate']:
        raise SystemExit('E4 audit failed: investigate distance bias before training')


if __name__ == '__main__':
    main()
