# Edge-rule ablation

This directory implements `CODEX_TASK.md` without changing the original model,
partitions, pooled contact table, checkpoints or presentation files. The source
branch is `comp5222-presentation` at `26673f7`; work is on `exp/edge-ablation`.

## Rules and compatibility

- `graph.edge_rule: flat` is the default and preserves the original graph
  byte-for-byte. The reference builder in `tests/reference_graph.py` is frozen
  from `26673f7`, rather than imported from the modified implementation.
- `distance_only` removes amino-acid information from ranking, while retaining
  amino-acid node features and contact-frequency edge features. Exact ranking
  ties use sequence-CRC32-seeded permutations. The undirected union can change
  degree, so this is a top-k-matched, not degree-matched, topology control.
- `band_resolved` uses real `(20,20,6)` contact/opportunity arrays and the
  requested shrinkage with `graph.band_pseudocount: 100000`. Zero-probability
  or unobserved bands have neutral enrichment 1. Self-loop prior is zero.
- All rule/config plumbing is opt-in. `contact_mpnn/model.py` is unchanged.

## Validate and audit before training

From `COMP-5222/`, in an environment satisfying `requirements.txt`:

```bash
python -m pip install -r requirements-test.txt
python -m pytest -q tests/
python experiments/edge_ablation/audit_graphs.py .
```

The audit reuses the 300 test-chain indices from `check_story.py`. Directed
choices and their band histogram are measured before symmetrization, while
mean degree is measured on the final undirected graph. Missing training-only
tables are recorded as blocked. A present E4 table must give a farthest-band
fraction below 0.90; otherwise the runner stops before any GPU training.

The preprocessing integration test creates a tiny real PDB/XTC archive and
executes `--limit 20` with train-sequence filtering. This validates the pipeline,
but is not a substitute for the requested smoke test on the original archive.

## Training-only table, when the source archive is available

```bash
python scripts/build_contact_table.py \
  --zip /path/to/conformational_ensembles.zip \
  --train-tsv data/processed/idrome_split_train.tsv \
  --limit 20 --out runs/edge_ablation/contact_smoke/table.npz

nohup python scripts/build_contact_table.py \
  --zip /path/to/conformational_ensembles.zip \
  --train-tsv data/processed/idrome_split_train.tsv \
  --out data/processed/aa_contact_table_train.npz \
  </dev/null >logs/edge_ablation/contact_table.log 2>&1 &
```

No trajectory folder-name assumption is made. The sequence decoded from the
PDB decides membership, including training chains longer than 512 residues.
Completed tables cannot be overwritten accidentally. Checkpoints bind the
archive path/size/mtime, training-file SHA-256 and contact parameters; a different
input or old checkpoint schema fails clearly. A full pass must keep within 1%
of the training TSV row count. Table correlation and band-frequency changes
are reported by `summarize.py` when a genuine new table exists.

## Detached execution

`run_experiments.py` accepts physical GPU UUIDs, a source commit and the project
root. Use `nohup` with all standard streams redirected. A per-user UUID lock
plus an immediate memory/utilization/process recheck implements a bounded
idle-GPU waiter; this is not a reservation against other cluster users.

E0 seed42 runs first. Its CPU-recomputed test MAE must be within 0.01 nm of
0.100 before the remaining seeds/variants can launch. This is the task's
reproduction gate, not a hyperparameter-selection procedure. Checkpoints are
selected only by validation MAE. Worker threads run independent subprocesses
on the supplied GPUs; each training process retains four DataLoader workers
and one BLAS/OpenMP thread.

In this execution the historical gate failed (E0 seed42 test MAE 0.127605 nm).
`run_reproduction_check.py` then compared three training epochs with untouched
26673f7 source on the same new host/GPU/runtime, without test evaluation. All
training/validation metrics matched exactly. The historical target remains
unreproduced; the precise component of the old runtime responsible is unknown.
The remaining ablations use this new E0 as a common-runtime control, retaining
the seed42 result. This execution decision is recorded in RESULTS.md.

The optional `--verified-environment-change PATH` argument accepts this
specific evidence after a failed numerical gate. It verifies the actual
three-epoch histories, source commit, host, torch/CUDA build and E0 result;
it never labels the old target as reproduced. Without this evidence the
default gate still stops. Initial launcher/environment records are retained.

An inference-only check of the immutable historical checkpoint also reproduces
the archived test MAE (0.100082 nm) and experimental MAE (0.295005 nm) under the
new CPU pipeline. All primary metric differences are below 3.2e-8. This check
does not retrain or replace the new E0; its separate output directory and logs
are retained. Input/table/split/weight hashes also match the user's historical
project archive byte-for-byte (`historical_input_comparison.json`).

Each run saves the exact commands in logs and a `run_record.json` with host,
GPU UUID, package versions, precision, source commit, input/config/output
hashes, owned process identities and separate training/evaluation wall times.
Failed and blocked seeds remain in the report. Existing failed attempts are
not silently restarted or overwritten. Completed runs are skipped on resume.

To stop this experiment, create `logs/edge_ablation/CANCEL` under its project
root. The launcher notices within about two seconds and terminates only its
owned child process groups. SIGTERM to the recorded launcher PID has the same
effect. Preserve output and cancellation records; inspect before resuming.

## Analysis

```bash
python scripts/plot_sparse_errors.py --run runs/edge_ablation/full_s42 --no-figs
python experiments/edge_ablation/summarize.py .
python experiments/edge_ablation/plot_ablation.py .
```

The summary imports only numpy/pandas and the standard library. It reproduces
the diagnostic's ridge composition model, centered log-length-residual share,
fixed sequence bootstrap and same-composition grouping. Spearman correlation
uses proper average tied ranks; the old diagnostic used double argsort.
Figures are rendered separately with matplotlib. Main-table sd is sample sd
across seeds. Bootstrap intervals condition on the fitted seeds and resample
sequences after averaging predictions across seeds.
`source_manifest_initial.json` and `source_manifest.json` preserve the two
training-code snapshots. `analysis_source_manifest.json` records the final
analysis/helpers, and summary.json also records the analysis script's own hash.

## Execution environment and unavailable data

The local Mac has no CUDA. `kee1706` did not resolve from this machine. At the
user's direction, Songcpu8 was selected after SSH/GPU/disk inspection. It has
L20 GPUs and an isolated environment under
`/data/kwchungac/comp5222-edge-ablation-20261116-26673f7/`.

System `venv` initially lacked ensurepip; `bootstrap_env.sh` uses
`venv --without-pip` and the official PyPA bootstrap in the new experiment
folder. No system or existing project environment was modified. The authoritative
remote tests use torch 2.7.1+cu126; the complete package snapshot is saved.
The bootstrap cache was moved into this experiment's persistent data folder;
the bootstrap helper now explicitly places pip cache and temporary files there.

The source trajectory archive was not found in local Downloads/Desktop/Documents
or mounted volumes, Songcpu8 user/shared storage, or Songcpu7 user/shared
storage. The original `/media/cbe/...` path is absent on the Mac. The pooled
20x20 table cannot recover training-only or pair-by-band counts. Accordingly,
E3/E4 are blocked as expressly allowed by the task; no factorized or synthetic
counts are used as experimental data. The synthetic table exists only inside
unit-test temporary directories.
