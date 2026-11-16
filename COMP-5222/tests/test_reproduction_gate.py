"""A failed historical target requires real unchanged-source trajectory evidence."""
import json
from pathlib import Path
import socket
import sys

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experiments/edge_ablation'))
from run_experiments import verify_reproduction_evidence


def evidence_fixture(root):
    history = [{'epoch': i, 'train_loss': .1 / i, 'val_mae_nm': .2 / i} for i in (1, 2, 3)]
    for name in ('full_s42', 'reference_diagnostic_s42'):
        p = root / f'runs/edge_ablation/{name}'
        p.mkdir(parents=True)
        (p / 'history.json').write_text(json.dumps(history))
    evidence = {'reference_commit': '26673f7', 'comparison_epochs': 3, 'refactor_test_mae': .1276,
                'environment': {'host': socket.gethostname(), 'torch': torch.__version__, 'cuda_build': torch.version.cuda}}
    path = root / 'evidence.json'
    path.write_text(json.dumps(evidence))
    return path


def test_verified_runtime_never_labels_old_target_reproduced(tmp_path):
    path = evidence_fixture(tmp_path)
    result = verify_reproduction_evidence(tmp_path, path, .1276)
    assert result['historical_target_reproduced'] is False
    assert result['status'] == 'refactor_equivalence_verified_historical_target_unreproduced'


def test_reference_flag_without_matching_histories_is_rejected(tmp_path):
    path = evidence_fixture(tmp_path)
    target = tmp_path / 'runs/edge_ablation/reference_diagnostic_s42/history.json'
    history = json.loads(target.read_text())
    history[1]['train_loss'] += .001
    target.write_text(json.dumps(history))
    with pytest.raises(ValueError, match='diverge'):
        verify_reproduction_evidence(tmp_path, path, .1276)
    with pytest.raises(ValueError, match='does not match'):
        verify_reproduction_evidence(tmp_path, path, .10)
