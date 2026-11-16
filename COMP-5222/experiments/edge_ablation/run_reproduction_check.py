#!/usr/bin/env python3
"""Compare three training epochs with the untouched baseline source, without test evaluation."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import socket
import sys
from pathlib import Path

import numpy as np
import torch
import yaml

from run_experiments import STOP, execute, idle_gpu, verify_protected, write_json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root', type=Path)
    ap.add_argument('--gpu', required=True)
    args = ap.parse_args()
    root = args.root.resolve()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: STOP.set())
    verify_protected(root)
    source = root / 'experiments/edge_ablation/reference_src'
    manifest = json.loads((source / 'source.json').read_text())
    for name, expected in manifest['files'].items():
        assert hashlib.sha256((source / name).read_bytes()).hexdigest() == expected
    run = root / 'runs/edge_ablation/reference_diagnostic_s42'
    if run.exists():
        raise SystemExit('Existing reference diagnostic; inspect before retrying')
    run.mkdir(parents=True)
    cfg = yaml.safe_load((root / 'configs/sparse_gat.yaml').read_text())
    for name, path in list(cfg['paths'].items()):
        cfg['paths'][name] = str(root / path)
    cfg['paths'].pop('test_tsv', None)
    cfg['paths']['out_dir'] = str(run)
    cfg['train']['epochs'] = 3
    config_path = run / 'diagnostic_config.yaml'
    config_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    record = {'status': 'running', 'diagnostic_only': True, 'host': socket.gethostname(),
              'gpu_uuid': args.gpu, 'torch': torch.__version__, 'cuda_build': torch.version.cuda,
              'reference_commit': manifest['commit'], 'epochs': 3, 'test_evaluation': False,
              'purpose': 'Untouched reference under same new environment; compare training trajectory, not select hyperparameters'}
    record_path = run / 'run_record.json'
    env = os.environ.copy()
    env.update(CUDA_VISIBLE_DEVICES=args.gpu, OMP_NUM_THREADS='1', MKL_NUM_THREADS='1',
               OPENBLAS_NUM_THREADS='1', PYTHONUNBUFFERED='1')
    with idle_gpu(root, args.gpu) as snapshot:
        record['gpu_snapshot_before'] = snapshot
        command = [sys.executable, str(source / 'scripts/train.py'), '--config', str(config_path)]
        record['train_wall_seconds'] = execute(root, command, env,
            root / 'logs/edge_ablation/reference_diagnostic_s42.log', record, record_path, 'reference_training')
    old = json.loads((root / 'runs/edge_ablation/full_s42/history.json').read_text())[:3]
    reference = json.loads((run / 'history.json').read_text())
    deltas = {key: max(abs(a[key] - b[key]) for a, b in zip(old, reference))
              for key in old[0] if key != 'epoch'}
    exact = all(value == 0 for value in deltas.values())
    close = all(value < 1e-7 for value in deltas.values())
    report = {'reference_commit': manifest['commit'], 'comparison_epochs': 3,
              'max_absolute_metric_differences': deltas, 'bit_identical_metrics': exact,
              'all_metrics_within_1e-7': close,
              'refactor_test_mae': json.loads((root / 'runs/edge_ablation/full_s42/plot_metrics.json').read_text())['test']['mae'],
              'original_published_test_mae': .100,
              'environment': {'host': socket.gethostname(), 'torch': torch.__version__,
                              'cuda_build': torch.version.cuda, 'gpu_uuid': args.gpu},
              'conclusion': ('Untouched source and refactor reproduce the same first three training epochs. '
                             'The failure to match the original host is not introduced by this refactor; '
                             'cross-host/runtime training is not numerically reproduced.' if close else
                             'Reference and refactor differ; investigate before more GPU work.'),
              'test_used_for_tuning': False}
    record.update(status='complete', comparison=report)
    write_json(record_path, record)
    write_json(root / 'experiments/edge_ablation/reproduction_check.json', report)
    verify_protected(root)
    print(json.dumps(report, indent=2), flush=True)
    if not close:
        raise SystemExit('Reference comparison failed')


if __name__ == '__main__':
    main()
