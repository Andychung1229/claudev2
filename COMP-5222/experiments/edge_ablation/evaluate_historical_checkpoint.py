#!/usr/bin/env python3
"""Read-only compatibility evaluation of the archived checkpoint in a new directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import sys

import torch

from run_experiments import STOP, execute, verify_protected, write_json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root', type=Path)
    root = ap.parse_args().root.resolve()
    verify_protected(root)
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: STOP.set())
    source = root / 'runs/contact_gat_idrome_sparse'
    run = root / 'runs/edge_ablation/historical_checkpoint_eval'
    run.mkdir(exist_ok=False)
    for name in ('config.yaml', 'history.json', 'best.pt'):
        shutil.copy2(source / name, run / name)
    record = {'status': 'running', 'diagnostic_only': True, 'training_performed': False,
              'host': socket.gethostname(), 'torch': torch.__version__,
              'source_checkpoint_sha256': hashlib.sha256((source / 'best.pt').read_bytes()).hexdigest()}
    env = os.environ.copy()
    env.update(CUDA_VISIBLE_DEVICES='', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1',
               OPENBLAS_NUM_THREADS='1', PYTHONUNBUFFERED='1')
    command = [sys.executable, str(root / 'scripts/plot_sparse_errors.py'), '--run', str(run), '--no-figs']
    record['eval_wall_seconds'] = execute(root, command, env,
        root / 'logs/edge_ablation/historical_checkpoint_eval.log', record, run / 'run_record.json', 'CPU_inference')
    actual = json.loads((run / 'plot_metrics.json').read_text())
    historical = json.loads((source / 'plot_metrics.json').read_text())
    delta = {dataset: {metric: actual[dataset][metric] - historical[dataset][metric]
                       for metric in ('mae', 'rmse', 'r2', 'pearson')}
             for dataset in ('test', 'exp151')}
    record.update(status='complete', metrics=actual, historical_metrics=historical,
                  differences=delta, all_metrics_within_1e_minus_5=all(abs(x) < 1e-5 for d in delta.values() for x in d.values()))
    write_json(run / 'run_record.json', record)
    write_json(root / 'experiments/edge_ablation/historical_checkpoint_check.json', record)
    verify_protected(root)
    print(json.dumps(record, indent=2), flush=True)


if __name__ == '__main__':
    main()
