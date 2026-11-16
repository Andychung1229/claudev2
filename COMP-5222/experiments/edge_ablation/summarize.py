#!/usr/bin/env python3
"""Numpy/pandas-only analysis. Usage: python experiments/edge_ablation/summarize.py ."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

AA = 'ACDEFGHIKLMNPQRSTVWY'
VARIANTS = ('full', 'local_only', 'distance_only', 'train_table', 'band_resolved')
SEEDS = (42, 43, 44)
METRICS = ('mae', 'rmse', 'r2', 'pearson', 'length_residual_share')


def features(sequences) -> np.ndarray:
    # Exactly check_story.py: intercept, ln N, first 19 AA fractions.
    return np.array([[1., np.log(len(s))] + [s.count(a) / len(s) for a in AA[:-1]] for s in sequences])


def baselines(train: pd.DataFrame, datasets: dict) -> tuple[dict, dict, np.ndarray, np.ndarray]:
    x = features(train.sequence)
    y = np.log(train.rg_nm.to_numpy())
    penalty = 1e-3 * np.eye(x.shape[1])
    penalty[0, 0] = 0
    weights = np.linalg.solve(x.T @ x + penalty, x.T @ y)
    length_fit = np.polyfit(np.log(train.seq_len.to_numpy()), y, 1)
    composition, length = {}, {}
    for name, rows in datasets.items():
        composition[name] = np.exp(features(rows.sequence) @ weights)
        length[name] = np.exp(np.polyval(length_fit, np.log(rows.sequence.str.len().to_numpy())))
    return composition, length, weights, length_fit


def metrics(y, prediction, length_prediction) -> dict:
    err = prediction - y
    residual = np.log(y) - np.log(length_prediction)
    denom = np.sum((residual - residual.mean()) ** 2)
    return {
        'mae': float(np.abs(err).mean()), 'rmse': float(np.sqrt(np.mean(err ** 2))),
        'r2': float(1 - np.sum(err ** 2) / np.sum((y - y.mean()) ** 2)),
        'pearson': float(np.corrcoef(y, prediction)[0, 1]),
        # Exactly check_story.py: centered log-length residual denominator.
        'length_residual_share': float(1 - np.sum((np.log(prediction) - np.log(y)) ** 2) / denom),
    }


def paired_bootstrap(y, a, b) -> dict:
    delta = np.abs(a - y) - np.abs(b - y)
    rng = np.random.RandomState(0)
    samples = np.array([delta[rng.randint(0, len(delta), len(delta))].mean() for _ in range(5000)])
    return {'difference_nm': float(delta.mean()), 'ci_low': float(np.percentile(samples, 2.5)),
            'ci_high': float(np.percentile(samples, 97.5)), 'resamples': 5000}


def spearman(a, b) -> float | None:
    # Average tied ranks, unlike the old script's double-argsort approximation.
    ar, br = pd.Series(a).rank().to_numpy(), pd.Series(b).rank().to_numpy()
    if np.std(ar) == 0 or np.std(br) == 0:
        return None
    return float(np.corrcoef(ar, br)[0, 1])


def load_prediction(path: Path, rows: pd.DataFrame) -> np.ndarray:
    frame = pd.read_csv(path, sep='\t')
    if frame.id.duplicated().any() or set(frame.id) != set(rows.id):
        raise ValueError(f'Wrong or duplicate prediction IDs in {path}')
    frame = frame.set_index('id').loc[rows.id]
    if not np.allclose(frame.rg_true_nm.to_numpy(), rows.rg_nm.to_numpy(), rtol=1e-5, atol=1e-6):
        raise ValueError(f'Target mismatch in {path}')
    prediction = frame.rg_pred_nm.to_numpy()
    if not np.isfinite(prediction).all() or (prediction <= 0).any():
        raise ValueError(f'Non-finite/non-positive predictions in {path}')
    return prediction


def cell(value: dict, metric: str) -> str:
    if not value:
        return '—'
    sd = value['sd'][metric]
    return f"{value['mean'][metric]:.4f} ± {sd:.4f}" if sd is not None else f"{value['mean'][metric]:.4f} (1 seed)"


def interval(value: dict) -> str:
    return f"{value['difference_nm']:+.4f} [{value['ci_low']:+.4f}, {value['ci_high']:+.4f}]"


def interpret(bootstrap: dict, variant: str, description: str) -> str:
    key = f'{variant}:test:full'
    if key not in bootstrap:
        return f'**Inconclusive.** {description}: required runs are missing or incomplete.'
    v = bootstrap[key]
    if v['n_seeds'] != 3 or v['reference_n_seeds'] != 3:
        return f'**Inconclusive.** {description}: only partial seed coverage is available.'
    if v['ci_low'] > 0:
        direction = 'The variant has higher test MAE than E0.'
    elif v['ci_high'] < 0:
        direction = 'The variant has lower test MAE than E0.'
    else:
        direction = 'The sequence-bootstrap interval includes zero; this does not establish equivalence.'
    label = 'Supported' if v['ci_low'] > 0 else ('Not supported' if v['ci_high'] < 0 else 'Inconclusive')
    extra = bootstrap.get(f'{variant}:exp151:full')
    return (f'**{label}.** {description}. Variant − E0 test MAE: {interval(v)} nm. '
            f'{direction} Exp151: {interval(extra)} nm.' if extra else
            f'**{label}.** {description}. Variant − E0 test MAE: {interval(v)} nm. {direction}')


def summarize(root: Path) -> dict:
    out = root / 'experiments/edge_ablation'
    out.mkdir(parents=True, exist_ok=True)
    train = pd.read_csv(root / 'data/processed/idrome_split_train.tsv', sep='\t')
    train = train.loc[train.seq_len <= 512].reset_index(drop=True)
    te = pd.read_csv(root / 'data/processed/idrome_split_test.tsv', sep='\t')
    te = te.loc[te.seq_len <= 512].reset_index(drop=True)
    ex = pd.read_csv(root / 'data/processed/labels_exp151.tsv', sep='\t')
    datasets = {'test': te, 'exp151': ex}
    composition, length, weights, length_fit = baselines(train, datasets)
    baseline_metrics = {name: {ds: metrics(rows.rg_nm.to_numpy(), preds[ds], length[ds])
                              for ds, rows in datasets.items()}
                        for name, preds in [('length_only', length), ('composition', composition)]}
    predictions, per_seed, run_status, setup = {}, [], [], []
    for variant in VARIANTS:
        predictions[variant] = {}
        for seed in SEEDS:
            run = root / f'runs/edge_ablation/{variant}_s{seed}'
            record_path = run / 'run_record.json'
            record = json.loads(record_path.read_text()) if record_path.is_file() else {}
            missing = [name for name in datasets if not (run / f'predictions_{name}.tsv').is_file()]
            if missing or record.get('status') not in {'complete', None}:
                status = record.get('status', 'not_run')
                if variant in {'train_table', 'band_resolved'} and not (root / 'data/processed/aa_contact_table_train.npz').is_file():
                    status = 'blocked_missing_trajectory_table'
                run_status.append({'variant': variant, 'seed': seed, 'status': status,
                                   'reason': record.get('error', ', '.join(missing))})
                continue
            values = {ds: load_prediction(run / f'predictions_{ds}.tsv', rows) for ds, rows in datasets.items()}
            predictions[variant][seed] = values
            run_status.append({'variant': variant, 'seed': seed, 'status': 'complete', 'reason': ''})
            setup.append({'variant': variant, 'seed': seed, **record})
            for ds, rows in datasets.items():
                per_seed.append({'variant': variant, 'seed': seed, 'dataset': ds,
                                 **metrics(rows.rg_nm.to_numpy(), values[ds], length[ds])})
    seed_frame = pd.DataFrame(per_seed)
    seed_frame.to_csv(out / 'seed_metrics.tsv', sep='\t', index=False)
    pd.DataFrame(run_status).to_csv(out / 'run_status.tsv', sep='\t', index=False)
    summary, averaged = {}, {}
    for variant in VARIANTS:
        seeds = sorted(predictions[variant])
        summary[variant] = {'n_seeds': len(seeds), 'seeds': seeds, 'metrics': {}}
        if not seeds:
            continue
        averaged[variant] = {}
        for ds in datasets:
            subset = seed_frame.loc[(seed_frame.variant == variant) & (seed_frame.dataset == ds)]
            summary[variant]['metrics'][ds] = {
                'mean': {m: float(subset[m].mean()) for m in METRICS},
                'sd': {m: float(subset[m].std(ddof=1)) if len(seeds) > 1 else None for m in METRICS},
            }
            averaged[variant][ds] = np.mean([predictions[variant][s][ds] for s in seeds], axis=0)
    bootstrap = {}
    for variant, by_ds in averaged.items():
        for ds, a in by_ds.items():
            references = {'composition': composition[ds]}
            if 'full' in averaged:
                references['full'] = averaged['full'][ds]
            for reference, b in references.items():
                bootstrap[f'{variant}:{ds}:{reference}'] = {
                    'variant': variant, 'dataset': ds, 'reference': reference,
                    'n_seeds': summary[variant]['n_seeds'],
                    'reference_n_seeds': summary['full']['n_seeds'] if reference == 'full' else None,
                    **paired_bootstrap(datasets[ds].rg_nm.to_numpy(), a, b),
                }
    pd.DataFrame(bootstrap.values()).to_csv(out / 'bootstrap.tsv', sep='\t', index=False)
    groups = defaultdict(list)
    for index, sequence in enumerate(ex.sequence):
        groups[''.join(sorted(sequence))].append(index)
    sensitivity = []
    for indices in groups.values():
        if len(indices) <= 1:
            continue
        truth = ex.iloc[indices].rg_nm.to_numpy()
        for variant in averaged:
            pred = averaged[variant]['exp151'][indices]
            sensitivity.append({'variant': variant, 'n_seeds': summary[variant]['n_seeds'],
                                'n_sequences': len(indices), 'length': len(ex.iloc[indices[0]].sequence),
                                'ids': ex.iloc[indices].id.tolist(), 'measured_range_nm': float(np.ptp(truth)),
                                'predicted_range_nm': float(np.ptp(pred)), 'spearman': spearman(truth, pred)})
    pd.DataFrame(sensitivity).to_csv(out / 'permutation_sensitivity.tsv', sep='\t', index=False)
    audit_path = out / 'edge_audit.json'
    audit = json.loads(audit_path.read_text()) if audit_path.is_file() else {}
    sanity = None
    table_path = root / 'data/processed/aa_contact_table_train.npz'
    if table_path.is_file():
        old = np.load(root / 'data/processed/aa_contact_table.npz')
        new = np.load(table_path)
        f = lambda z: np.divide(z['counts'], z['opportunities'], out=np.zeros_like(z['counts']), where=z['opportunities'] > 0)
        def band_mean(z):
            bounds = [(1, 2), (2, 5), (5, 9), (9, 17), (17, 33), (33, len(z['sep_counts']))]
            return np.array([z['sep_counts'][lo:hi].sum() / max(z['sep_opps'][lo:hi].sum(), 1) for lo, hi in bounds])
        old_pd, new_pd = band_mean(old), band_mean(new)
        sanity = {'frequency_pearson': float(np.corrcoef(f(old).ravel(), f(new).ravel())[0, 1]),
                  'old_band_frequency': old_pd.tolist(), 'new_band_frequency': new_pd.tolist(),
                  'band_relative_change': np.divide(new_pd-old_pd, old_pd, out=np.zeros_like(old_pd), where=old_pd > 0).tolist()}
    report = {'variants': summary, 'baselines': baseline_metrics, 'bootstrap': bootstrap,
              'permutation_sensitivity': sensitivity, 'run_status': run_status,
              'setup': setup, 'edge_audit': audit, 'train_table_sanity': sanity,
              'baseline_coefficients': {'composition': weights.tolist(), 'length': length_fit.tolist()},
              'definitions': {'sd': 'sample standard deviation across training seeds (ddof=1)',
                              'bootstrap': '5000 sequence resamples, RandomState(0), seed-averaged predictions; conditional on fitted seeds',
                              'residual_share': '1 - SSE(log prediction) / sum(centered log-length residual squared)',
                              'spearman': 'Pearson correlation of average tied ranks; undefined for a constant vector'}}
    (out / 'summary.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    write_markdown(root, report)
    return report


def write_markdown(root: Path, report: dict) -> None:
    variants, baseline = report['variants'], report['baselines']
    complete = sum(r['status'] == 'complete' for r in report['run_status'])
    lines = ['# ContactGAT edge-rule ablation', '', f'Completed {complete}/15 requested runs. All seeds, including failures and blocked runs, are listed below.', '',
             '## Setup', '', 'Fixed seed-42 UniProt/exact-sequence grouped partitions. Training labels are simulated Rg; train N ≤ 512. '
             'Only graph rule/top-k/contact table and training seed vary; model, optimizer, batching and validation early stopping stay fixed.', '',
             '| Variant | Seed | Host | GPU UUID | Code commit | Train wall (s) | Eval wall (s) |',
             '|---|---:|---|---|---|---:|---:|']
    for r in report['setup']:
        lines.append(f"| {r['variant']} | {r['seed']} | {r.get('host','unknown')} | {r.get('gpu_uuid','unknown')} | {r.get('commit','unknown')} | {r.get('train_wall_seconds',0):.1f} | {r.get('eval_wall_seconds',0):.1f} |")
    lines += ['', 'Environment and input/code hashes are in `environment.json`, `environment.txt`, `protected_inputs.json` and each run’s `run_record.json`.', '',
              '## Main table', '', 'Mean ± sample sd across seeds, in nm where applicable. A one-seed entry is explicitly labelled. '
              'The residual share uses the exact centered log-residual definition from `check_story.py`.', '',
              '| Model | Seeds | Test MAE | Test RMSE | Test R² | Test residual share | Exp MAE | Exp R² | Exp Pearson r |',
              '|---|---:|---|---|---|---|---|---|---|']
    for name in ('length_only', 'composition'):
        t, e = baseline[name]['test'], baseline[name]['exp151']
        lines.append(f"| {name} | — | {t['mae']:.4f} | {t['rmse']:.4f} | {t['r2']:.4f} | {t['length_residual_share']:.4f} | {e['mae']:.4f} | {e['r2']:.4f} | {e['pearson']:.4f} |")
    for name, v in variants.items():
        t, e = v['metrics'].get('test', {}), v['metrics'].get('exp151', {})
        lines.append(f"| {name} | {v['n_seeds']}/3 | {cell(t,'mae')} | {cell(t,'rmse')} | {cell(t,'r2')} | {cell(t,'length_residual_share')} | {cell(e,'mae')} | {cell(e,'r2')} | {cell(e,'pearson')} |")
    lines += ['', '## Paired bootstrap', '', 'Differences are variant minus reference MAE; negative favours the variant. '
              'Predictions are averaged across available seeds before resampling sequences. These intervals do not integrate uncertainty from training new seeds.', '',
              '| Variant | Dataset | Reference | Seeds | Difference [95% CI], nm |', '|---|---|---|---:|---|']
    for v in report['bootstrap'].values():
        lines.append(f"| {v['variant']} | {v['dataset']} | {v['reference']} | {v['n_seeds']} | {interval(v)} |")
    lines += ['', '## Permutation sensitivity', '', 'Same-composition groups use the exact sorted-sequence grouping from `perm_check.py`. '
              'Spearman uses average tied ranks. Predictions are averaged over seeds.', '',
              '| Variant | Seeds | Group size × length | Measured range (nm) | Predicted range (nm) | Spearman |', '|---|---:|---|---:|---:|---:|']
    for v in report['permutation_sensitivity']:
        rho = f"{v['spearman']:.3f}" if v['spearman'] is not None else 'undefined'
        lines.append(f"| {v['variant']} | {v['n_seeds']} | {v['n_sequences']} × {v['length']} | {v['measured_range_nm']:.4f} | {v['predicted_range_nm']:.4f} | {rho} |")
    lines += ['', '## Edge audit', '', 'The same 300 chains as `check_story.py`: RandomState(0), sampling without replacement. '
              'Band frequencies describe directed choices before symmetrization. Degree describes the final undirected graph. '
              'The distance-only control matches top-k, but is not a matched-degree control.', '',
              '| Variant | Mean non-local degree | Farthest-band fraction | Chosen counts by band [1, 2–4, 5–8, 9–16, 17–32, >32] |', '|---|---:|---:|---|']
    for name, v in report['edge_audit'].get('variants', {}).items():
        if v['status'] != 'complete':
            lines.append(f'| {name} | blocked | blocked | missing training-only table |')
        else:
            far = v['farthest_available_band_fraction']
            fraction = f'{far:.6f}' if far is not None else 'N/A (no non-local edges)'
            lines.append(f"| {name} | {v['mean_nonlocal_edges_per_residue']:.4f} | {fraction} | {v['chosen_partner_band_counts']} |")
    lines += ['', 'E4 must have a farthest-band fraction below 0.90 before training; otherwise the pipeline stops for investigation.', '', '## Training-table sanity', '',
              json.dumps(report['train_table_sanity'], indent=2) if report['train_table_sanity'] else
              'Unavailable: no training-only table could be built without the source trajectory archive.', '', '## Answers to Q1–Q4', '',
              'Q1. Do non-local edges improve on local-only? ' + interpret(report['bootstrap'], 'local_only', 'Evidence that the original non-local edges improve prediction'), '',
              'Q2. Does the amino-acid term improve on the distance-only topology? ' + interpret(report['bootstrap'], 'distance_only', 'Evidence that the amino-acid term improves prediction'), '']
    q3 = report['bootstrap'].get('train_table:test:full')
    if q3 and variants['train_table']['n_seeds'] == variants['full']['n_seeds'] == 3:
        changed = q3['ci_low'] > 0 or q3['ci_high'] < 0
        lines.append(f"Q3. Does removing prior leakage change performance? **{'Supported' if changed else 'Inconclusive'}.** Test MAE change: {interval(q3)} nm. A zero-crossing interval is not proof of equivalence.")
    else:
        lines.append('Q3. **Inconclusive.** E3 requires the original trajectory archive to build a training-only prior; it is not recoverable from the pooled old table.')
    if variants['band_resolved']['n_seeds'] == variants['full']['n_seeds'] == 3:
        comparisons = [report['bootstrap'][f'band_resolved:{ds}:{ref}']
                       for ds in ('test', 'exp151') for ref in ('composition', 'full')]
        e4_groups = {v['length']: v for v in report['permutation_sensitivity'] if v['variant'] == 'band_resolved'}
        e0_groups = {v['length']: v for v in report['permutation_sensitivity'] if v['variant'] == 'full'}
        ranges_grow = bool(e4_groups) and all(v['predicted_range_nm'] > e0_groups[n]['predicted_range_nm'] for n, v in e4_groups.items())
        improves_all = all(v['ci_high'] < 0 for v in comparisons)
        label = 'Supported' if improves_all and ranges_grow else 'Not supported'
        details = '; '.join(f"{v['dataset']} minus {v['reference']}: {interval(v)} nm" for v in comparisons)
        q4 = (f'Q4. **{label}.** Joint claim that band-resolved enrichment improves both datasets versus E0 and composition, '
              f'and increases both permutation-group spreads. {details}. Both predicted ranges increase: {ranges_grow}. '
              'Mixed improvements are reported individually rather than hidden by this joint assessment.')
    else:
        q4 = 'Q4. **Inconclusive.** E4 requires genuine amino-acid-pair-by-band counts and three completed seeds. No synthetic or factorized counts are substituted for experimental runs.'
    lines += ['', q4, '',
              '## Seed coverage, failures and decisions', '', '| Variant | Seed | Status | Detail |', '|---|---:|---|---|']
    for v in report['run_status']:
        lines.append(f"| {v['variant']} | {v['seed']} | {v['status']} | {str(v['reason']).replace('|','/')} |")
    lines += ['', 'Implementation decisions:', '',
              '- The original graph builder is frozen in `tests/reference_graph.py` from commit 26673f7. Default and explicit flat rules are checked byte-for-byte on 50 random training sequences.',
              '- Distance-only exact ties use sequence-CRC32-seeded permutations and stable sorting; contact-frequency edge features remain unchanged.',
              '- Unobserved/zero-probability bands use neutral enrichment E=1. Self-loop prior stays zero; band-resolved log enrichment is clipped to [-3,3].',
              '- Existing runs, pooled contact tables, partitions and presentation files are protected by SHA-256 checks.',
              '- A GPU snapshot is not a reservation. A per-user GPU lock, bounded idle check and immediate process/memory recheck precede each launch.',
              '- Training-only preprocessing includes long training chains; the neural predictor still uses N ≤ 512.',
              '- The missing trajectory archive blocks E3/E4 as permitted by CODEX_TASK.md; no proxy table is presented as training-only data.', '']
    (root / 'experiments/edge_ablation/RESULTS.md').write_text('\n'.join(lines))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('root', type=Path)
    args = ap.parse_args()
    report = summarize(args.root.resolve())
    print('completed', sum(r['status'] == 'complete' for r in report['run_status']), '/ 15 runs')


if __name__ == '__main__':
    main()
