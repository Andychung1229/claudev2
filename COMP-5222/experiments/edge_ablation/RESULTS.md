# ContactGAT edge-rule ablation

Completed 9/15 requested runs. All seeds, including failures and blocked runs, are listed below.

## Setup

Fixed seed-42 UniProt/exact-sequence grouped partitions. Training labels are simulated Rg; train N ≤ 512. Only graph rule/top-k/contact table and training seed vary; model, optimizer, batching and validation early stopping stay fixed.

| Variant | Seed | Host | GPU UUID | Code commit | Train wall (s) | Eval wall (s) |
|---|---:|---|---|---|---:|---:|
| full | 42 | songcpu8 | GPU-5c1ba65f-10ff-a704-6065-5c5867e72807 | 7e01db4e491ab15dbc9ade2d9865ab016b4a2d7d | 1027.1 | 108.1 |
| full | 43 | songcpu8 | GPU-35939f05-9cb5-2a8e-ea8a-348a93c5c35b | 58667d09d288da7c00efe530a5ef85b62aeb216d | 1914.0 | 112.1 |
| full | 44 | songcpu8 | GPU-5c1ba65f-10ff-a704-6065-5c5867e72807 | 58667d09d288da7c00efe530a5ef85b62aeb216d | 2256.3 | 112.1 |
| local_only | 42 | songcpu8 | GPU-0243affa-d1e6-5bc1-ae25-82e0b3cfe458 | 58667d09d288da7c00efe530a5ef85b62aeb216d | 3549.7 | 106.1 |
| local_only | 43 | songcpu8 | GPU-35939f05-9cb5-2a8e-ea8a-348a93c5c35b | 58667d09d288da7c00efe530a5ef85b62aeb216d | 2656.7 | 108.1 |
| local_only | 44 | songcpu8 | GPU-5c1ba65f-10ff-a704-6065-5c5867e72807 | 58667d09d288da7c00efe530a5ef85b62aeb216d | 2394.4 | 118.1 |
| distance_only | 42 | songcpu8 | GPU-0243affa-d1e6-5bc1-ae25-82e0b3cfe458 | 58667d09d288da7c00efe530a5ef85b62aeb216d | 806.8 | 112.1 |
| distance_only | 43 | songcpu8 | GPU-0243affa-d1e6-5bc1-ae25-82e0b3cfe458 | 58667d09d288da7c00efe530a5ef85b62aeb216d | 4104.3 | 112.1 |
| distance_only | 44 | songcpu8 | GPU-35939f05-9cb5-2a8e-ea8a-348a93c5c35b | 58667d09d288da7c00efe530a5ef85b62aeb216d | 3039.1 | 116.1 |

Environment and input/code hashes are in `environment.json`, `environment_sessions.json`, `environment.txt`, `protected_inputs.json` and each run’s `run_record.json`.

Additional shared-GPU activity was observed during distance_only_s43. Wall times are observed shared-hardware times, not isolated efficiency measurements. See `gpu_contention_snapshots.json`.

## Historical reproduction investigation

E0 seed42 test MAE is 0.127605 nm, versus the historical 0.100 nm target; the ±0.01 nm numerical gate failed. The original launcher stopped before the other runs.

A separate three-epoch diagnostic ran the untouched 26673f7 training source on the same new host, GPU and environment. All training/validation metric differences were 0. No diagnostic test evaluation was performed. The frozen source, hashes, diagnostic config/history/checkpoint and logs are retained under `reference_src/`, `runs/edge_ablation/reference_diagnostic_s42/` and `logs/edge_ablation/`.

This verifies refactor equivalence for the observed training trajectory, but does not reproduce the historical numerical target. The original RTX 5060 Ti environment was not fully archived, so the exact hardware/runtime component causing the cross-host difference remains unresolved. After this investigation, the remaining fixed-config runs use the new E0 as their common-runtime control. E0 seed42 is retained, not replaced or tuned. This is an explicit execution decision and a limitation of comparisons to the published single-seed result.

An additional inference-only diagnostic evaluated the immutable archived checkpoint with the new CPU pipeline: test MAE 0.100082 nm, exp151 MAE 0.295005 nm. The largest absolute difference across MAE/RMSE/R²/Pearson metrics was 3.2e-08. No training was performed. This confirms checkpoint/inference compatibility and narrows the historical mismatch to retraining rather than changed inputs or inference. Outputs are retained under `runs/edge_ablation/historical_checkpoint_eval/`.

## Main table

Mean ± sample sd across seeds, in nm where applicable. A one-seed entry is explicitly labelled. The residual share uses the exact centered log-residual definition from `check_story.py`.

| Model | Seeds | Test MAE | Test RMSE | Test R² | Test residual share | Exp MAE | Exp R² | Exp Pearson r |
|---|---:|---|---|---|---|---|---|---|
| length_only | — | 0.1240 | 0.2099 | 0.9719 | -0.0000 | 0.4159 | 0.7439 | 0.8649 |
| composition | — | 0.0984 | 0.1771 | 0.9800 | 0.3050 | 0.3310 | 0.8224 | 0.9081 |
| full | 3/3 | 0.1111 ± 0.0150 | 0.1736 ± 0.0234 | 0.9806 ± 0.0053 | 0.1975 ± 0.2037 | 0.3011 ± 0.0092 | 0.8384 ± 0.0074 | 0.9188 ± 0.0028 |
| local_only | 3/3 | 0.0660 ± 0.0070 | 0.1221 ± 0.0101 | 0.9904 ± 0.0016 | 0.6830 ± 0.0608 | 0.3030 ± 0.0073 | 0.8409 ± 0.0040 | 0.9181 ± 0.0015 |
| distance_only | 3/3 | 0.0943 ± 0.0398 | 0.1573 ± 0.0657 | 0.9824 ± 0.0148 | 0.3983 ± 0.4758 | 0.3203 ± 0.0195 | 0.8176 ± 0.0096 | 0.9069 ± 0.0023 |
| train_table | 0/3 | — | — | — | — | — | — | — |
| band_resolved | 0/3 | — | — | — | — | — | — | — |

## Paired bootstrap

Differences are variant minus reference MAE; negative favours the variant. Predictions are averaged across available seeds before resampling sequences. These intervals do not integrate uncertainty from training new seeds.

| Variant | Dataset | Reference | Seeds | Difference [95% CI], nm |
|---|---|---|---:|---|
| full | test | composition | 3 | +0.0076 [+0.0049, +0.0103] |
| full | test | full | 3 | +0.0000 [+0.0000, +0.0000] |
| full | exp151 | composition | 3 | -0.0361 [-0.0535, -0.0184] |
| full | exp151 | full | 3 | +0.0000 [+0.0000, +0.0000] |
| local_only | test | composition | 3 | -0.0359 [-0.0383, -0.0334] |
| local_only | test | full | 3 | -0.0435 [-0.0460, -0.0411] |
| local_only | exp151 | composition | 3 | -0.0285 [-0.0477, -0.0082] |
| local_only | exp151 | full | 3 | +0.0076 [-0.0121, +0.0281] |
| distance_only | test | composition | 3 | -0.0191 [-0.0223, -0.0158] |
| distance_only | test | full | 3 | -0.0267 [-0.0296, -0.0239] |
| distance_only | exp151 | composition | 3 | -0.0296 [-0.0522, -0.0044] |
| distance_only | exp151 | full | 3 | +0.0064 [-0.0141, +0.0288] |

## Permutation sensitivity

Same-composition groups use the exact sorted-sequence grouping from `perm_check.py`. Spearman uses average tied ranks. Predictions are averaged over seeds.

| Variant | Seeds | Group size × length | Measured range (nm) | Predicted range (nm) | Spearman |
|---|---:|---|---:|---:|---:|
| full | 3 | 6 × 107 | 0.7300 | 0.0612 | 0.771 |
| local_only | 3 | 6 × 107 | 0.7300 | 0.4740 | 0.943 |
| distance_only | 3 | 6 × 107 | 0.7300 | 0.2584 | 0.771 |
| full | 3 | 7 × 334 | 1.3870 | 0.0765 | 0.214 |
| local_only | 3 | 7 × 334 | 1.3870 | 0.1683 | -0.036 |
| distance_only | 3 | 7 × 334 | 1.3870 | 0.2923 | 0.214 |

## Edge audit

The same 300 chains as `check_story.py`: RandomState(0), sampling without replacement. Band frequencies describe directed choices before symmetrization. Degree describes the final undirected graph. The distance-only control matches top-k, but is not a matched-degree control.

| Variant | Mean non-local degree | Farthest-band fraction | Chosen counts by band [1, 2–4, 5–8, 9–16, 17–32, >32] |
|---|---:|---:|---|
| full | 12.4687 | 0.966361 | [0, 0, 0, 2240, 27142, 237866] |
| local_only | 0.0000 | N/A (no non-local edges) | [0, 0, 0, 0, 0, 0] |
| distance_only | 14.7534 | 0.966361 | [0, 0, 0, 2240, 27142, 237866] |
| train_table | blocked | blocked | missing training-only table |
| band_resolved | blocked | blocked | missing training-only table |

E4 must have a farthest-band fraction below 0.90 before training; otherwise the pipeline stops for investigation.

## Training-table sanity

Unavailable: no training-only table could be built without the source trajectory archive.

## Answers to Q1–Q4

Q1. Do non-local edges improve on local-only? **Inconclusive.** Evidence that the original non-local edges improve prediction, assessed using seed-averaged predictions. Test: not supported, variant − E0 MAE -0.0435 [-0.0460, -0.0411] nm. Exp151: inconclusive, +0.0076 [-0.0121, +0.0281] nm. A zero-crossing interval does not establish equivalence; mixed dataset results remain inconclusive overall.

Q2. Does the amino-acid term improve on the distance-only topology? **Inconclusive.** Evidence that the amino-acid term improves prediction, assessed using seed-averaged predictions. Test: not supported, variant − E0 MAE -0.0267 [-0.0296, -0.0239] nm. Exp151: inconclusive, +0.0064 [-0.0141, +0.0288] nm. A zero-crossing interval does not establish equivalence; mixed dataset results remain inconclusive overall.

Q3. **Inconclusive.** E3 requires the original trajectory archive to build a training-only prior; it is not recoverable from the pooled old table.

Q4. **Inconclusive.** E4 requires genuine amino-acid-pair-by-band counts and three completed seeds. No synthetic or factorized counts are substituted for experimental runs.

## Seed coverage, failures and decisions

| Variant | Seed | Status | Detail |
|---|---:|---|---|
| full | 42 | complete |  |
| full | 43 | complete |  |
| full | 44 | complete |  |
| local_only | 42 | complete |  |
| local_only | 43 | complete |  |
| local_only | 44 | complete |  |
| distance_only | 42 | complete |  |
| distance_only | 43 | complete |  |
| distance_only | 44 | complete |  |
| train_table | 42 | blocked_missing_trajectory_table | Source conformational_ensembles.zip not found; genuine train-only band counts unavailable |
| train_table | 43 | blocked_missing_trajectory_table | Source conformational_ensembles.zip not found; genuine train-only band counts unavailable |
| train_table | 44 | blocked_missing_trajectory_table | Source conformational_ensembles.zip not found; genuine train-only band counts unavailable |
| band_resolved | 42 | blocked_missing_trajectory_table | Source conformational_ensembles.zip not found; genuine train-only band counts unavailable |
| band_resolved | 43 | blocked_missing_trajectory_table | Source conformational_ensembles.zip not found; genuine train-only band counts unavailable |
| band_resolved | 44 | blocked_missing_trajectory_table | Source conformational_ensembles.zip not found; genuine train-only band counts unavailable |

Implementation decisions:

- The original graph builder is frozen in `tests/reference_graph.py` from commit 26673f7. Default and explicit flat rules are checked byte-for-byte on 50 random training sequences.
- Distance-only exact ties use sequence-CRC32-seeded permutations and stable sorting; contact-frequency edge features remain unchanged.
- Unobserved/zero-probability bands use neutral enrichment E=1. Self-loop prior stays zero; band-resolved log enrichment is clipped to [-3,3].
- Existing runs, pooled contact tables, partitions and presentation files are protected by SHA-256 checks.
- A GPU snapshot is not a reservation. A per-user GPU lock, bounded idle check and immediate process/memory recheck precede each launch.
- Training-only preprocessing includes long training chains; the neural predictor still uses N ≤ 512.
- The missing trajectory archive blocks E3/E4 as permitted by CODEX_TASK.md; no proxy table is presented as training-only data.
