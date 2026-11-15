# Codex task: edge-rule ablation for ContactGAT

You are running a follow-up experiment for the COMP 5222 ContactGAT project
(IDP radius-of-gyration prediction from sequence). Read this whole file before
touching anything. Work inside `COMP-5222/` on branch `comp5222-presentation`
of `Andychung1229/claudev2`.

## 1. Why this experiment exists

The current model (`runs/contact_gat_idrome_sparse/`, seed 42) gets
test MAE 0.100 nm / R² 0.981 on 4,103 unseen IDRome proteins and
MAE 0.295 nm / r 0.921 on 151 experimental Rg values. Three diagnostics
(scripts in `../comp5222-presentation/analysis/`) showed:

1. A 21-parameter linear model on amino-acid composition + log N ties the
   GAT on the simulated test set (MAE 0.098 vs 0.100; paired-bootstrap 95% CI
   of the difference [−0.001, +0.005]). The GAT does beat it on the 151
   experiments (0.295 vs 0.331, CI [−0.054, −0.018]).
2. The non-local edge rule in `contact_mpnn/graph.py::build_sparse_graph`
   ranks partners by `f_ab / p_d`. `f_ab` (20×20 pair frequency) varies ~2×,
   `p_d` (mean contact frequency of the distance band) varies ~1,300×. So
   distance decides the edges: 96.6% of chosen partners lie in the farthest
   available band, and the amino-acid type only breaks ties within a band.
3. In the exp151 set, two groups of same-composition, reordered sequences
   (6 × 107 aa, 7 × 334 aa) have measured Rg spreads of 0.73 and 1.38 nm,
   but GAT prediction spreads of only 0.08 and 0.06 nm. The graph barely sees
   residue order.

The proposal's intended rule (eq. 2) uses a band-resolved table `p_abd`
and enrichment `p_abd / p_d`, which compares amino-acid pairs at the same
distance. The current code has no (a, b, band) counts. Also, the existing
contact table was counted over all 28,058 trajectories, including val/test
(a small leak).

**Questions to answer:**

- Q1. Do the non-local edges help at all? (local-only ablation)
- Q2. Does the amino-acid term in the current rule matter, or is it
  equivalent to "random partners in the farthest band"? (distance-only control)
- Q3. Does removing the val/test leak from the contact table change anything?
- Q4. Does the band-resolved enrichment rule (the proposal's rule) improve
  accuracy vs. the composition baseline, and does it make predictions more
  sensitive to residue order?

## 2. Environment

- The original run was on host `kee1706`, repo at `/media/cbe/18TB HDD1/COMP-5222`,
  Python `/home/cbe/miniconda3/bin/python3` (torch 2.7.1, CUDA, RTX 5060 Ti).
  One training run takes ~13 min on that GPU.
- The trajectory zip is only needed for step 4.3. Default location
  (`scripts/build_contact_table.py::DEFAULT_ZIP`):
  `/media/cbe/18TB HDD1/Rg_hpc4/data/raw/idrome/conformational_ensembles.zip`.
  If it is not there, search for `conformational_ensembles.zip` on the machine.
  If you cannot find it, do steps 4.1–4.2 and the runs that don't need it
  (E0, E1, E2), and report that E3/E4 are blocked.
- Paths contain a space (`18TB HDD1`). Quote them.
- Use `tmux` or `nohup` for anything longer than a few minutes, and write logs
  under `logs/edge_ablation/`.

## 3. Ground rules

- **Do not modify or overwrite** `runs/contact_gat_idrome_sparse/`,
  `data/processed/aa_contact_table.npz` (or its `.tsv`/`.json` siblings),
  the split TSVs, or anything in `../comp5222-presentation/` except adding
  files. New outputs go under `runs/edge_ablation/` and
  `data/processed/aa_contact_table_train*.npz`.
- Keep the split fixed (the seed-42 UniProt-grouped split). Vary only
  `train.seed`.
- Select checkpoints by validation only (the existing early stopping on
  `val_mae_nm`). Never tune anything on test or exp151.
- All new behaviour must be opt-in through config keys. The defaults must
  reproduce the current graph exactly, so old configs and the old checkpoint
  still work.
- Match the existing code style (short Chinese or English comments,
  type hints, numpy-first graph code).
- Report every run, including failures and surprising results. Do not drop
  seeds.

## 4. Implementation

### 4.1 Edge rules in `contact_mpnn/graph.py`

Add a keyword `edge_rule: str = "flat"` to `build_sparse_graph`, and plumb it
through `graphs_from_table`, `IdromeGraphDataset` (`contact_mpnn/dataset.py`)
and `_dataset_kwargs` (`contact_mpnn/train.py`) from a new config key
`graph.edge_rule` (default `"flat"`). Rules:

| `edge_rule` | non-local ranking score for pair (i, j), band d = band(abs(i−j)) | `prior` edge feature (channel 0) |
|---|---|---|
| `flat` (current, default) | `f_ab / (p_d + ε)`, ties → smaller j | `f_ab` |
| `distance_only` | `1 / (p_d + ε)`; ties broken by a **deterministic random** permutation seeded from the sequence (e.g. `zlib.crc32(seq.encode())`), not by smaller j | `f_ab` (unchanged, so only the topology changes) |
| `band_resolved` | `E_abd = p̃_abd / p_d`, where `p̃_abd = (c_abd + α·p_d) / (o_abd + α)` (shrinkage toward the band mean; α = `graph.band_pseudocount`, default `1.0e5` frame-pairs) | `log(E_abd)`, clipped to [−3, 3] |

`topk: 0` must keep working and give a local-only graph (it already does,
since `k_eff == 0` skips selection; keep it that way).

Local edges, self-loops, the band one-hot, `|i−j|/(N−1)`, and the local/self
flags stay as they are, so `edge_in` stays 10 and the model code is untouched.

**Regression test (required):** add `tests/test_graph_rules.py`. It should
check that `edge_rule="flat"` gives arrays bit-identical to the current
`build_sparse_graph` (copy the current function into the test as a reference,
or compare against `git show HEAD:COMP-5222/contact_mpnn/graph.py`) on
50 random training sequences. Also check that `topk=0` leaves only local and
self edges. Run it with `python -m pytest -q tests/`.

### 4.2 `ContactTable` band-resolved counts (`contact_mpnn/contacts.py`)

- Add optional fields `band_counts` and `band_opps`, each with shape
  (20, 20, N_BANDS), float64. Make them `None` when the npz doesn't have
  them, so the old table still loads.
- Add `band_pair_frequency()` that returns `c_abd / o_abd` (0 where o = 0), and
  `band_enrichment(alpha)` that implements the shrunk `E_abd` above.
- `save()` writes the new arrays when they are present. Also write a readable
  `<stem>_band_enrichment.tsv` (rows `aa_i aa_j band counts opps p_abd E_abd`).
- Extend `accumulate_chain` to also fill the (20, 20, band) accumulators.
  Use `sep_band_index(sep)` per separation. Make the diagonal halving
  consistent with the existing 20×20 code.
- `build_sparse_graph(edge_rule="band_resolved")` must raise a clear error if
  the table has no band counts.

### 4.3 Train-only contact table (`scripts/build_contact_table.py`)

- Add `--train-tsv PATH`. When it is set, only accumulate trajectories whose
  sequence is in the training split. Match on the **sequence string** decoded
  from `top.pdb` (the split keeps identical sequences together, so this is
  unambiguous). Do not match on folder names unless you first verify that they
  equal the `id`/`seq_name` column. Log how many chains were kept and skipped.
  Expect about 19,615 kept (all train chains, including N > 512). Stop with an
  error if the number is far off.
- The band-resolved accumulators are always filled. A single pass produces one
  npz that serves E3 (flat rule) and E4 (band-resolved rule).
- Run with `--out data/processed/aa_contact_table_train.npz`.
  The script already checkpoints and resumes (`.partial.npz`). Smoke-test with
  `--limit 20` on a scratch `--out` path first.
- This scans ~19.6k trajectories and will take a while. Start it early in the
  background and do E0–E2 on the GPU while it runs.
- Sanity check after it finishes: the train-only `f_ab` should correlate
  r > 0.99 with the old table's `f_ab`, and `p_d` should be within a few
  percent of the old values. Report both.

### 4.4 Evaluation script

`scripts/plot_sparse_errors.py` hardcodes `RUN`. Add `--run DIR` (default:
the current path) and `--no-figs`. It must write `predictions_test.tsv`,
`predictions_exp151.tsv` and `plot_metrics.json` into the given run dir. Run it
on every new run (CPU is fine).

## 5. Runs

Five variants × three seeds (42, 43, 44) = 15 runs, about 3.5 GPU-hours.
For each variant, copy `configs/sparse_gat.yaml` to
`configs/edge_ablation/<variant>.yaml`. Override the seed per run, either by
generating one config per seed or by adding a `--seed` / `--out-dir` CLI
override to `scripts/train.py` (preferred). Output dirs go to
`runs/edge_ablation/<variant>_s<seed>/`.

| ID | variant | contact table | `graph.topk` | `graph.edge_rule` | answers |
|---|---|---|---|---|---|
| E0 | `full` | `aa_contact_table.npz` (old) | 8 | `flat` | baseline; seed 42 should land near test MAE 0.100 |
| E1 | `local_only` | old | 0 | `flat` | Q1 |
| E2 | `distance_only` | old | 8 | `distance_only` | Q2 |
| E3 | `train_table` | `aa_contact_table_train.npz` | 8 | `flat` | Q3 |
| E4 | `band_resolved` | `aa_contact_table_train.npz` | 8 | `band_resolved` | Q4 |

Before any GPU time, run a **CPU graph audit** for each variant on the same
300 random test chains that `check_story.py` uses (`RandomState(0)`). Report:
mean non-local edges per residue, the fraction of chosen partners in the
farthest available band (current rule ≈ 0.966), and a histogram of chosen
partners by band. For E4, this fraction must be clearly below 0.966.
If it isn't, the rule is not doing what it should. Stop and investigate
before training.

E0 seed 42 is a reproducibility check of the refactor. If test MAE is off by
more than ~0.01 nm from 0.100, find out why before running the rest.

## 6. Analysis

Write `experiments/edge_ablation/summarize.py` (numpy/pandas only, usage
`python experiments/edge_ablation/summarize.py .`). It must reuse the exact
composition baseline from `../comp5222-presentation/analysis/check_story.py`
(ridge λ = 1e-3, features `[1, ln N, 19 composition fractions]`, fit on
train N ≤ 512). It should produce:

1. **Main table.** Per variant: mean ± sd over 3 seeds of test MAE, RMSE, R²,
   and exp151 MAE, R², Pearson r. Also the share of length-residual variance
   captured on test (same definition as `check_story.py`). Add rows for the
   length-only power law and the linear composition baseline.
2. **Paired bootstrap** (5,000 resamples over sequences, `RandomState(0)`,
   same as `bootstrap.py`) on the **seed-averaged** predictions of each
   variant, for both test and exp151:
   - variant − composition baseline (MAE difference, 95% CI)
   - variant − E0 full (MAE difference, 95% CI)
3. **Permutation sensitivity** on the two same-composition groups in exp151
   (same grouping as `perm_check.py`). Per variant: predicted Rg range per
   group (seed-averaged) vs. the measured range, and Spearman correlation with
   the measured values.
4. **Edge audit** numbers from section 5.
5. Seed-to-seed sd, so readers can judge whether differences exceed training
   noise.

Write the result to `experiments/edge_ablation/RESULTS.md` with these sections:
setup (host, GPU, commit hash, wall time per run), the tables above, and a short
plain-English answer to Q1–Q4. Each answer says "supported / not supported /
inconclusive" and cites the numbers. Expected outcomes, to check against and
not to force:

- If E1 ≈ E0 within seed noise, the non-local edges add nothing (consistent
  with diagnostic 2).
- If E2 ≈ E0, the amino-acid term in the current rule is irrelevant.
- E3 ≈ E0 is expected (the leak is small). A large change would be a red flag
  worth explaining.
- E4 is the real test. Report honestly whether it beats E0 and the composition
  baseline on test and exp151, and whether the permutation spreads grow.
  A null result is a valid result.

Also save a small figure `experiments/edge_ablation/ablation_mae.png` with
test and exp151 MAE per variant, mean ± sd over seeds, and the composition
baseline as a horizontal line.

## 7. Deliverables and git

Commit on a new branch `exp/edge-ablation` created from
`comp5222-presentation`. Make small, focused commits (code, tests, configs,
analysis, results). Push the branch. Do **not** push to `main` or
`comp5222-presentation`.

Commit:
- code changes (`contact_mpnn/`, `scripts/`, `tests/`)
- `configs/edge_ablation/*.yaml`
- `data/processed/aa_contact_table_train.npz` and its tsv/json siblings
  (small, ~tens of KB)
- for each run: `config.yaml`, `history.json`, `test_metrics.json`,
  `plot_metrics.json`, `predictions_test.tsv`, `predictions_exp151.tsv`,
  `best.pt` (~100 KB each, fine to commit), and the training log
- `experiments/edge_ablation/{summarize.py,RESULTS.md,ablation_mae.png}`

Do not commit the trajectory zip, `.partial.npz` checkpoints, or anything over
~5 MB.

When done, reply with: the branch name, the main results table, the Q1–Q4
answers, and anything that went wrong or that you had to decide yourself.
