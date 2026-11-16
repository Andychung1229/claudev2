#!/usr/bin/env python3
"""Render test/experimental MAE after the numpy/pandas-only summary."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root', type=Path)
    args = ap.parse_args()
    out = args.root / 'experiments/edge_ablation'
    report = json.loads((out / 'summary.json').read_text())
    names = list(report['variants'])
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    for ax, dataset, title in zip(axes, ['test', 'exp151'], ['Simulated test', 'Experimental (151)']):
        for i, name in enumerate(names):
            v = report['variants'][name]
            m = v['metrics'].get(dataset)
            if m:
                error = m['sd']['mae'] if m['sd']['mae'] is not None else 0
                ax.bar(i, m['mean']['mae'], yerr=error, capsize=4, color='#3378b8', width=.65)
                ax.annotate(f"n={v['n_seeds']}", (i, m['mean']['mae'] + error),
                            xytext=(0, 5), textcoords='offset points', ha='center', fontsize=8)
            else:
                ax.text(i, .015, 'blocked', rotation=90, ha='center', va='bottom', color='#777777')
        baseline = report['baselines']['composition'][dataset]['mae']
        ax.axhline(baseline, color='#c45a27', linestyle='--', label='Linear composition baseline')
        ax.set_xticks(np.arange(len(names)), [n.replace('_', '\n') for n in names], fontsize=9)
        ax.set_title(title)
        ax.set_ylabel('MAE (nm), mean ± sample sd')
        ax.set_ylim(bottom=0)
        ax.grid(axis='y', alpha=.2)
        ax.set_axisbelow(True)
        ax.legend(fontsize=8)
    fig.savefig(out / 'ablation_mae.png', dpi=180)
    plt.close(fig)


if __name__ == '__main__':
    main()
