"""Small real PDB/XTC archive exercises filtering, counters and CLI output."""
from pathlib import Path
import csv
import json
import subprocess
import sys
import zipfile

import numpy as np
import pytest

md = pytest.importorskip('mdtraj')
ROOT = Path(__file__).resolve().parents[1]


def test_train_sequence_filter_and_limit_20(tmp_path):
    archive = tmp_path / 'tiny.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        for i in range(20):
            top = md.Topology()
            chain = top.add_chain()
            name = 'ALA' if i % 2 == 0 else 'CYS'
            for j in range(6):
                top.add_atom('CA', md.element.carbon, top.add_residue(name, chain))
            traj = md.Trajectory(np.random.RandomState(i).uniform(0, .1, (15, 6, 3)), top)
            pdb, xtc = tmp_path / 'top.pdb', tmp_path / 'traj.xtc'
            traj[0].save_pdb(str(pdb))
            traj.save_xtc(str(xtc))
            # Folder names intentionally do not match sequence IDs.
            z.write(pdb, f'unrelated_folder_{i}/top.pdb')
            z.write(xtc, f'unrelated_folder_{i}/traj.xtc')
    train = tmp_path / 'train.tsv'
    with train.open('w') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'sequence'], delimiter='\t')
        writer.writeheader()
        writer.writerows({'id': f'train_{i}', 'sequence': 'AAAAAA'} for i in range(10))
    output = tmp_path / 'table.npz'
    cmd = [sys.executable, str(ROOT / 'scripts/build_contact_table.py'), '--zip', str(archive),
           '--train-tsv', str(train), '--limit', '20', '--ckpt-every', '5', '--out', str(output)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    meta = json.loads((tmp_path / 'table_meta.json').read_text())
    assert meta['n_chains'] == meta['n_skipped'] == 10
    assert meta['n_frames_total'] == 50
    with np.load(output) as z:
        np.testing.assert_array_equal(z['band_counts'].sum(axis=2), z['counts'])
        assert z['band_counts'].shape == (20, 20, 6)
    assert (tmp_path / 'table_band_enrichment.tsv').is_file()
    assert not output.with_suffix('.partial.npz').exists()
    before = output.read_bytes()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    assert result.returncode != 0 and 'Refusing to overwrite' in result.stderr
    assert output.read_bytes() == before


def test_missing_archive_is_reported(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/build_contact_table.py'),
                             '--zip', str(tmp_path / 'absent.zip'), '--out', str(tmp_path / 'new.npz')],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode != 0 and 'Missing trajectory archive' in result.stderr
    assert not (tmp_path / 'new.npz').exists()
