"""Frozen-builder regression plus graph-rule and contact-statistic checks."""
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contact_mpnn.contacts import ContactTable, N_BANDS, accumulate_chain, seq_to_idx
from contact_mpnn.graph import build_sparse_graph, graphs_from_table
from reference_graph import build_sparse_graph as reference_graph


@pytest.fixture
def table():
    return ContactTable.load(ROOT / 'data/processed/aa_contact_table.npz')


def with_bands(table):
    pd_ = table.band_frequency()[None, None, :]
    table.band_opps = np.full((20, 20, N_BANDS), 1e6, dtype=np.float64)
    factors = np.linspace(.5, 1.5, 20)
    table.band_counts = table.band_opps * pd_ * (factors[:, None, None] + factors[None, :, None]) / 2
    return table


def test_flat_bit_identical_for_50_training_sequences(table):
    rows = pd.read_csv(ROOT / 'data/processed/idrome_split_train.tsv', sep='\t')
    rows = rows.loc[rows.seq_len <= 512]
    seqs = rows.iloc[np.random.RandomState(0).choice(len(rows), 50, replace=False)].sequence
    for seq in seqs:
        expected = reference_graph(seq, table)
        for actual in (build_sparse_graph(seq, table), build_sparse_graph(seq, table, edge_rule='flat')):
            assert actual.keys() == expected.keys()
            for key in actual:
                assert actual[key].dtype == expected[key].dtype
                assert actual[key].shape == expected[key].shape
                assert actual[key].tobytes() == expected[key].tobytes(), (seq, key)


@pytest.mark.parametrize('rule', ['flat', 'distance_only', 'band_resolved'])
@pytest.mark.parametrize('seq', ['A', 'AC', 'ACDEFGHIKLMNPQRSTVWY' * 3])
def test_topk_zero_is_local_and_self_only(table, rule, seq):
    table = with_bands(table)
    g = build_sparse_graph(seq, table, topk=0, edge_rule=rule)
    sep = abs(np.arange(len(seq))[:, None] - np.arange(len(seq))[None, :])
    np.testing.assert_array_equal(g['edge_mask'], sep <= 2)
    assert g['edge'].shape == (len(seq), len(seq), 10)


def test_distance_only_deterministic_and_changes_only_topology(table):
    seq = 'ACDEFGHIKLMNPQRSTVWY' * 5
    a = build_sparse_graph(seq, table, edge_rule='distance_only')
    b = build_sparse_graph(seq, table, edge_rule='distance_only')
    flat = build_sparse_graph(seq, table)
    np.testing.assert_array_equal(a['edge_mask'], b['edge_mask'])
    np.testing.assert_array_equal(a['edge_mask'], a['edge_mask'].T)
    assert not np.array_equal(a['edge_mask'], flat['edge_mask'])
    common = (a['edge_mask'] > 0) & (flat['edge_mask'] > 0)
    np.testing.assert_array_equal(a['edge'][common], flat['edge'][common])
    for key in a:
        np.testing.assert_array_equal(a[key], graphs_from_table(seq, table, graph_mode='sparse', edge_rule='distance_only')[key])


def test_band_rule_requires_new_counts(table):
    with pytest.raises(ValueError, match='requires band counts'):
        build_sparse_graph('ACDEFG', table, edge_rule='band_resolved')
    with pytest.raises(ValueError, match='unknown edge_rule'):
        build_sparse_graph('ACDEFG', table, edge_rule='typo')


def test_band_enrichment_and_roundtrip(table, tmp_path):
    table = with_bands(table)
    alpha = 1e5
    pd_ = table.band_frequency()
    d = 3
    expected = (table.band_counts[0, 1, d] + alpha * pd_[d]) / (table.band_opps[0, 1, d] + alpha) / pd_[d]
    assert table.band_enrichment(alpha)[0, 1, d] == pytest.approx(expected)
    # Band 1 is unobserved with min_seq_sep=2, so its feature is neutral.
    np.testing.assert_array_equal(table.band_enrichment(alpha)[:, :, 0], 1)
    table.band_opps[0, 1, d] = table.band_counts[0, 1, d] = 0
    assert table.band_enrichment(alpha)[0, 1, d] == pytest.approx(1)
    assert table.band_pair_frequency()[0, 1, d] == 0
    path = tmp_path / 'table.npz'
    table.save(path)
    restored = ContactTable.load(path)
    np.testing.assert_array_equal(restored.band_counts, table.band_counts)
    np.testing.assert_array_equal(restored.band_opps, table.band_opps)
    assert (tmp_path / 'table_band_enrichment.tsv').is_file()
    g = build_sparse_graph('ACDEFGHIKLMNPQRSTVWY' * 2, restored, edge_rule='band_resolved')
    assert np.isfinite(g['edge']).all()
    assert abs(g['edge'][..., 0]).max() <= 3
    np.testing.assert_array_equal(g['edge'][np.arange(40), np.arange(40), 0], 0)


def test_accumulate_band_counts_against_explicit_pairs():
    seq = 'AACACA'
    aa = seq_to_idx(seq)
    xyz = np.random.RandomState(7).uniform(0, 1.5, (4, len(seq), 3))
    c, o, sc, so, bc, bo = accumulate_chain(xyz, aa, cutoff_nm=.8, min_seq_sep=2, max_sep_bins=512)
    expected_c = np.zeros((20, 20))
    expected_o = np.zeros_like(expected_c)
    for i in range(len(seq)):
        for j in range(i + 2, len(seq)):
            hits = sum(np.linalg.norm(frame[i] - frame[j]) < .8 for frame in xyz)
            expected_c[aa[i], aa[j]] += hits
            expected_o[aa[i], aa[j]] += len(xyz)
            if aa[i] != aa[j]:
                expected_c[aa[j], aa[i]] += hits
                expected_o[aa[j], aa[i]] += len(xyz)
    np.testing.assert_array_equal(c, expected_c)
    np.testing.assert_array_equal(o, expected_o)
    np.testing.assert_array_equal(bc.sum(axis=2), c)
    np.testing.assert_array_equal(bo.sum(axis=2), o)
    np.testing.assert_array_equal(bc, bc.transpose(1, 0, 2))
    np.testing.assert_array_equal(bo, bo.transpose(1, 0, 2))


def test_old_table_still_loads_without_band_arrays(table, tmp_path):
    path = tmp_path / 'old.npz'
    table.save(path)
    loaded = ContactTable.load(path)
    assert loaded.band_counts is None and loaded.band_opps is None
    np.testing.assert_array_equal(loaded.frequency, table.frequency)
