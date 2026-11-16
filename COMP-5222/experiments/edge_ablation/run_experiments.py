#!/usr/bin/env python3
"""Detached, cancellable runner; audit and E0 reproduction gate precede other runs."""
from __future__ import annotations

import argparse
import concurrent.futures
import fcntl
import hashlib
import json
import os
import platform
import queue
import signal
import socket
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import torch
import yaml

from audit_graphs import VARIANTS, run_audit

STOP = threading.Event()


def write_json(path: Path, value: dict) -> None:
    tmp = path.with_suffix('.tmp.json')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    tmp.replace(path)


def verify_protected(root: Path) -> None:
    manifest = json.loads((root / 'experiments/edge_ablation/protected_inputs.json').read_text())
    for name, expected in manifest.items():
        path = root.parent / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError(f'Protected input changed: {name}')


def verify_reproduction_evidence(root: Path, path: Path, mae: float) -> dict:
    """Admit a changed runtime only after an untouched-source training comparison."""
    evidence = json.loads(path.read_text())
    if evidence.get('reference_commit') != '26673f7' or evidence.get('comparison_epochs') != 3:
        raise ValueError('Reference evidence must cover three epochs of untouched 26673f7 source')
    environment = evidence['environment']
    if (environment['host'] != socket.gethostname() or environment['torch'] != torch.__version__
            or environment['cuda_build'] != torch.version.cuda):
        raise ValueError('Reference evidence belongs to a different runtime')
    if abs(evidence['refactor_test_mae'] - mae) > 1e-10:
        raise ValueError('Reference evidence does not match this E0 result')
    current = json.loads((root / 'runs/edge_ablation/full_s42/history.json').read_text())[:3]
    reference = json.loads((root / 'runs/edge_ablation/reference_diagnostic_s42/history.json').read_text())
    if len(current) != 3 or len(reference) != 3:
        raise ValueError('Missing actual three-epoch reference histories')
    for a, b in zip(current, reference):
        for key in a:
            if not np.isfinite(a[key]) or not np.isfinite(b[key]) or abs(a[key] - b[key]) >= 1e-7:
                raise ValueError(f'Untouched reference and refactor diverge: epoch {a["epoch"]}, {key}')
    return {'status': 'refactor_equivalence_verified_historical_target_unreproduced',
            'historical_target_reproduced': False, 'e0_test_mae': mae,
            'evidence_path': str(path),
            'decision': 'Continue fixed-config ablations against E0 in the same new runtime. '
                        'The archived historical numerical target remains unreproduced; no seed is replaced.'}


def gpu_snapshot(uuid: str) -> dict:
    text = subprocess.check_output(['nvidia-smi', f'--id={uuid}',
                                   '--query-gpu=uuid,name,memory.used,utilization.gpu',
                                   '--format=csv,noheader,nounits'], text=True, timeout=15)
    parts = [p.strip() for p in text.strip().split(',')]
    processes = subprocess.check_output(['nvidia-smi', f'--id={uuid}',
                                        '--query-compute-apps=pid,used_gpu_memory',
                                        '--format=csv,noheader,nounits'], text=True, timeout=15)
    return {'uuid': parts[0], 'name': parts[1], 'used_mib': int(parts[2]),
            'utilization': int(parts[3]), 'processes': processes.strip()}


def cancelled(root: Path) -> bool:
    return STOP.is_set() or (root / 'logs/edge_ablation/CANCEL').exists()


@contextmanager
def idle_gpu(root: Path, uuid: str, timeout: float = 1800):
    lock_dir = Path('/data/kwchungac/.gpu-locks')
    lock_dir.mkdir(exist_ok=True)
    began = time.monotonic()
    with (lock_dir / f'{uuid}.lock').open('a') as lock:
        while not cancelled(root):
            if time.monotonic() - began > timeout:
                raise TimeoutError(f'No idle GPU within {timeout}s: {uuid}')
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                time.sleep(2)
                continue
            state = gpu_snapshot(uuid)
            if state['used_mib'] < 256 and state['utilization'] <= 5 and not state['processes']:
                yield state
                fcntl.flock(lock, fcntl.LOCK_UN)
                return
            fcntl.flock(lock, fcntl.LOCK_UN)
            time.sleep(2)
        raise RuntimeError('Cancelled while waiting for GPU')


def execute(root: Path, command: list[str], env: dict, log_path: Path, record: dict, record_path: Path, phase: str) -> float:
    started = time.monotonic()
    with log_path.open('w') as log:
        log.write('COMMAND ' + json.dumps(command) + '\n')
        log.flush()
        child = subprocess.Popen(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT,
                                 stdin=subprocess.DEVNULL, start_new_session=True)
        record.update(phase=phase, child_pid=child.pid, child_pgid=child.pid,
                      child_start_ticks=Path(f'/proc/{child.pid}/stat').read_text().split()[21])
        write_json(record_path, record)
        while child.poll() is None:
            if cancelled(root):
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
                raise RuntimeError('Cancelled: owned child process group terminated')
            if time.monotonic() - started > 6 * 3600:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
                raise TimeoutError(f'{phase} exceeded six-hour run ceiling')
            time.sleep(2)
    if child.returncode:
        raise RuntimeError(f'{phase} exited {child.returncode}; see {log_path.name}')
    return time.monotonic() - started


def single_run(root: Path, variant: str, seed: int, uuid: str, commit: str) -> dict:
    run = root / f'runs/edge_ablation/{variant}_s{seed}'
    run.mkdir(parents=True, exist_ok=True)
    record_path = run / 'run_record.json'
    if record_path.exists():
        old = json.loads(record_path.read_text())
        if old['status'] == 'complete':
            print(f'SKIP complete {variant}_s{seed}', flush=True)
            return old
        if old['status'] not in {'blocked_missing_trajectory_table', 'queued'}:
            raise RuntimeError(f'Existing attempt {variant}_s{seed} has status {old["status"]}; inspect before retrying')
    config_path = root / f'configs/edge_ablation/{variant}.yaml'
    cfg = yaml.safe_load(config_path.read_text())
    table = root / cfg['paths']['contact_table']
    record = {'variant': variant, 'seed': seed, 'status': 'waiting_for_gpu', 'host': socket.gethostname(),
              'gpu_uuid': uuid, 'commit': commit, 'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'pid': os.getpid(), 'uid': os.getuid(), 'torch': torch.__version__, 'cuda_build': torch.version.cuda,
              'numpy': np.__version__, 'precision': 'CUDA autocast float16; GradScaler; TF32 enabled as original',
              'table_sha256': hashlib.sha256(table.read_bytes()).hexdigest(),
              'config_sha256': hashlib.sha256(config_path.read_bytes()).hexdigest()}
    write_json(record_path, record)
    env = os.environ.copy()
    env.update(CUDA_VISIBLE_DEVICES=uuid, OMP_NUM_THREADS='1', MKL_NUM_THREADS='1',
               OPENBLAS_NUM_THREADS='1', PYTHONUNBUFFERED='1')
    try:
        with idle_gpu(root, uuid) as snapshot:
            record.update(status='running', gpu_snapshot_before=snapshot)
            command = [sys.executable, str(root / 'scripts/train.py'), '--config', str(config_path),
                       '--seed', str(seed), '--out-dir', str(run)]
            print(f'START {variant}_s{seed} on {uuid}', flush=True)
            record['train_wall_seconds'] = execute(root, command, env, root / f'logs/edge_ablation/{variant}_s{seed}.log',
                                                   record, record_path, 'training')
        env['CUDA_VISIBLE_DEVICES'] = ''
        command = [sys.executable, str(root / 'scripts/plot_sparse_errors.py'), '--run', str(run), '--no-figs']
        record['eval_wall_seconds'] = execute(root, command, env, root / f'logs/edge_ablation/{variant}_s{seed}_eval.log',
                                              record, record_path, 'evaluation')
        required = ['config.yaml', 'history.json', 'test_metrics.json', 'plot_metrics.json',
                    'predictions_test.tsv', 'predictions_exp151.tsv', 'best.pt']
        record['output_sha256'] = {name: hashlib.sha256((run / name).read_bytes()).hexdigest() for name in required}
        record.update(status='complete', phase='complete', finished_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
        print(f'DONE {variant}_s{seed}, training={record["train_wall_seconds"]:.1f}s', flush=True)
    except Exception as error:
        record.update(status='cancelled' if cancelled(root) else 'failed', error=repr(error))
        print(f'FAILED {variant}_s{seed}: {error}', flush=True)
    write_json(record_path, record)
    return record


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('root', type=Path)
    ap.add_argument('--gpus', nargs='+', required=True)
    ap.add_argument('--commit', required=True)
    ap.add_argument('--verified-environment-change', type=Path,
                    help='three-epoch untouched-source evidence; does not claim the old MAE was reproduced')
    args = ap.parse_args()
    root = args.root.resolve()
    logs = root / 'logs/edge_ablation'
    logs.mkdir(parents=True, exist_ok=True)
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: STOP.set())
    with (logs / 'launcher.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        verify_protected(root)
        report = run_audit(root)
        e4 = report['variants']['band_resolved']
        if e4['status'] == 'complete' and not e4['band_resolved_gate']:
            raise RuntimeError('E4 audit failed; no GPU work launched')
        available = [name for name in VARIANTS if report['variants'][name]['status'] == 'complete']
        for name in VARIANTS:
            if name in available:
                continue
            for seed in (42, 43, 44):
                path = root / f'runs/edge_ablation/{name}_s{seed}'
                path.mkdir(parents=True, exist_ok=True)
                write_json(path / 'run_record.json', {'variant': name, 'seed': seed,
                           'status': 'blocked_missing_trajectory_table',
                           'error': 'Source conformational_ensembles.zip not found; genuine train-only band counts unavailable'})
        environment = {'host': socket.gethostname(), 'platform': platform.platform(), 'python': sys.version,
                       'torch': torch.__version__, 'cuda_build': torch.version.cuda, 'numpy': np.__version__,
                       'commit': args.commit, 'gpus': args.gpus, 'pid': os.getpid(), 'uid': os.getuid(),
                       'start_ticks': Path('/proc/self/stat').read_text().split()[21],
                       'scheduler': 'none found; bounded idle-GPU waiter with per-user UUID locks, not a cluster reservation'}
        environment_path = root / 'experiments/edge_ablation/environment.json'
        sessions_path = root / 'experiments/edge_ablation/environment_sessions.json'
        sessions = json.loads(sessions_path.read_text()) if sessions_path.exists() else []
        if environment_path.exists() and not sessions:
            sessions.append(json.loads(environment_path.read_text()))
        sessions.append(environment)
        write_json(sessions_path, sessions)
        write_json(environment_path, environment)
        # Gate all other GPU runs on E0 seed-42 reproduction, exactly as requested.
        first = single_run(root, 'full', 42, args.gpus[0], args.commit)
        if first['status'] != 'complete':
            raise RuntimeError('E0 seed42 failed; remaining runs not launched')
        metric_path = root / 'runs/edge_ablation/full_s42/plot_metrics.json'
        mae = json.loads(metric_path.read_text())['test']['mae']
        if abs(mae - .100) > .01:
            if args.verified_environment_change is None:
                raise RuntimeError(f'E0 reproduction gate failed: test MAE={mae}; investigate before other seeds')
            decision = verify_reproduction_evidence(root, args.verified_environment_change.resolve(), mae)
            write_json(root / 'experiments/edge_ablation/reproduction_gate.json', decision)
            print('HISTORICAL MAE NOT REPRODUCED; untouched-source equivalence verified. '
                  f'Continue against common-runtime E0 MAE={mae:.6f}', flush=True)
        else:
            write_json(root / 'experiments/edge_ablation/reproduction_gate.json',
                       {'status': 'historical_target_reproduced', 'historical_target_reproduced': True,
                        'e0_test_mae': mae})
            print(f'E0 REPRODUCTION PASSED: MAE={mae:.6f}', flush=True)
        jobs = queue.Queue()
        for name in available:
            for seed in (42, 43, 44):
                if (name, seed) != ('full', 42):
                    jobs.put((name, seed))
        outcomes = []
        def worker(uuid):
            while not cancelled(root):
                try:
                    name, seed = jobs.get_nowait()
                except queue.Empty:
                    return
                outcomes.append(single_run(root, name, seed, uuid, args.commit))
                jobs.task_done()
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(args.gpus)) as pool:
            futures = [pool.submit(worker, uuid) for uuid in args.gpus]
            for future in futures:
                future.result()
        verify_protected(root)
        env = os.environ.copy()
        env.update(CUDA_VISIBLE_DEVICES='', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
        subprocess.run([sys.executable, str(root / 'experiments/edge_ablation/summarize.py'), str(root)], env=env, check=True)
        subprocess.run([sys.executable, str(root / 'experiments/edge_ablation/plot_ablation.py'), str(root)], env=env, check=True)
        write_json(logs / 'completion.json', {'status': 'cancelled' if cancelled(root) else 'finished_available_runs',
                                             'available_variants': available, 'outcomes': [{k: r[k] for k in ('variant','seed','status')} for r in [first] + outcomes]})
        if any(r['status'] != 'complete' for r in outcomes):
            raise SystemExit('One or more runs failed; all outcomes retained')


if __name__ == '__main__':
    main()
