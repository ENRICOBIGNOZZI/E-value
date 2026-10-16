# PARK/REVIVE — theory and simulations

Fresh research implementation for sequential comparison of **estimated investment
policies**, with quadratic utility and shared turnover/impact costs. The current
scope excludes empirical analysis. No legacy results are reused.

The working manuscript is [`paper/main.tex`](paper/main.tex); mathematical
assumptions and limitations are audited in [`reports/theory_audit.md`](reports/theory_audit.md).
The supplied handoff is preserved unchanged under [`docs/spec/`](docs/spec/).
Its operational instructions are reference material; the user's explicit restart
and theory/simulation scope govern this reconstruction.

## Reproduce

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-tested.txt
.venv/bin/python -m pip install '.[test]'
.venv/bin/python -m pytest -q
.venv/bin/python -m park_revive.cli audit
.venv/bin/python -m park_revive.cli simulate --config configs/smoke.json --stage smoke --seeds 101 102 103 --output outputs/park_revive_v1/frozen_smoke
.venv/bin/python -m park_revive.cli report --output outputs/park_revive_v1/frozen_smoke
```

An existing run requires `resume` in place of `simulate`. Checkpoints are local
generated Python pickles: resume only checkpoints created by this pipeline.
All score observations are consumed once; resuming at an annual checkpoint
reproduces the uninterrupted numerical run. Incomplete block files are replaced
when replaying that block. Completed seed directories are used by the report.

```sh
# Full dimensions, first pilot seed (500 stocks, 100 signals, 15 years).
.venv/bin/python scripts/run_stage.py pilot --count 1
# Resume or extend the 100-seed pilot.
.venv/bin/python scripts/run_stage.py pilot
# Separate controlled null/power diagnostics, not additional financial DGPs.
.venv/bin/python -m park_revive.cli statistics --output outputs/park_revive_v1/frozen_pilot
.venv/bin/python -m park_revive.cli report --output outputs/park_revive_v1/frozen_pilot
# Export hidden simulation truth separately, verifying every replayed return.
.venv/bin/python scripts/export_truth.py --output outputs/park_revive_v1/frozen_pilot
# Compile the paper after completed pilot results exist; requires Tectonic.
.venv/bin/python scripts/build_paper.py --results outputs/park_revive_v1/frozen_pilot
# Planned final 500 fresh seeds, not a claim that these have been executed.
.venv/bin/python scripts/run_stage.py main
```

Do not choose a new threshold, risk bound, seed or design based on which method
wins. Any revised design needs a new named configuration, new output directory,
an explicit change rationale and fresh evaluation seeds.

## What is implemented

- One characteristic-driven stock market, with 45 coefficient-bearing functions,
  40 exact structural noise functions and 15 correlated proxies.
- Strictly OOS annual expanding estimates, all additions/removals and Swap10.
- Separate actual and shadow allocation states; actual transitions pay actual costs.
- Catoni log evidence with past-only bets and a public analytic raw-second-moment bound.
- All Signals, Greedy, Repeated-HAC-p, E-process and one-period Oracle benchmarks.
- Evaluator-only Laplace score moments and state-matched full-universe oracle regret.
- Daily ledgers, immutable score ledgers, comparison events, annual decisions,
  censored economic detection events, runtime, paired seed comparisons and figures.
- Atomic annual checkpointing, source/configuration hashes and disjoint seed pools.

## What the results can establish

The 5% error guarantee belongs to a **single comparison episode**. There is no
multiple-testing correction across signals or restarts. Stationary betting-power
results do not imply regime-detection guarantees. One structural move per year
permits at most 14 changes in 14 OOS years. The public moment envelope can be
very conservative; an inactive E-process portfolio is a valid possible outcome.
The oracle optimizes current conditional utility and need not have the best
realized wealth. Structural noise can be an economically useful hedge.

Smoke runs are software checks. The 100-seed pilot and 500-seed main design are
specified separately. **Read [`reports/execution_status.md`](reports/execution_status.md)
for the actual completed seeds, test results and remaining work.** A manuscript
draft and passing tests are not proof of publication readiness or superiority.

## Preserved empirical inputs

`data/README.md`, `data/source_manifest_20261006.json` and the historical acquisition
helper `experiments/fetch_jkp.py` are preserved byte-for-byte. Raw JKP archives
are absent from this fresh clone. Nothing was downloaded, interpolated or used
in an empirical application. The historical helper is retained for provenance;
it is not part of the current simulation pipeline.

The old tree is recoverable at `origin/archive/pre-rebuild-20261016` and from the
adjacent `../E-value-pre-rebuild-20261016.zip`. SHA-256 inventory and exact cleanup
list are in `reports/data_preservation_manifest.json` and
`reports/legacy_cleanup_plan.md`. The rebuild uses branch
`codex/park-revive-20261016`; no push, merge or history rewrite is implicit.

## Declared higher-moment extension

`src/park_revive_extensions/` adds a separately declared corrected-tail test
and observable policy-moment certificates. It leaves the frozen baseline
package unchanged. The fourth score moment requires eighth return moments;
this is stronger information than the original Catoni test requires.

The first-entry mechanism study uses fresh seeds 40001–40020, fixed empty
reference portfolios and identical candidate score series for all four arms.
It measures whether entry can be certified at all, without claiming post-entry
portfolio performance. The protocol was fixed before these new markets:
[`reports/extension_protocol.md`](reports/extension_protocol.md).

```sh
# Use the source tree explicitly during development.
PYTHONPATH=src .venv/bin/python -m pytest -q
.venv/bin/python scripts/run_first_entry.py --count 20
.venv/bin/python scripts/tail_study.py controlled
.venv/bin/python scripts/tail_study.py report
.venv/bin/python scripts/verify_first_entry.py
.venv/bin/python scripts/audit_deployment.py
.venv/bin/python scripts/build_paper.py
```

The legacy `detection.csv` denominators are conditioned on comparison survival.
They cannot support cross-method delay rankings; see
[`reports/detection_audit.md`](reports/detection_audit.md). The new fixed-reference
study follows all comparisons to the common horizon, including after crossing.
The original `true_current_mean` event field describes the last evaluated
pre-return shadow gain. A separate post-hoc deployment audit values the next
action from the real zero allocation, pays its entry cost and draws no next
return; it is not a post-entry fund performance result.

## Full-strategy extension

`research/park_revive_full/` adds a separate six-method study, preserving both
frozen packages. Its actual funds include waiting in cash, post-entry returns
and actual transition costs. Economic opportunity labels use counterfactual
continuations after early closures, so fast responses remain in the risk set.
The protocol and fresh seed pools are in
[`reports/full_strategy_protocol.md`](reports/full_strategy_protocol.md).
The software checks do not count as financial pilot markets.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/run_full_strategy.py --config configs/full_smoke.json --output outputs/park_revive_full_v3/software --seeds 51001 51002 51003
.venv/bin/python scripts/verify_full_strategy.py --output outputs/park_revive_full_v3/software
# First full-size pilot block; resume the same seed to complete its horizon.
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/run_full_strategy.py --config configs/full_pilot.json --output outputs/park_revive_full_v3/pilot --seeds 50001 --stop-after-blocks 1
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/run_full_strategy.py --config configs/full_pilot.json --output outputs/park_revive_full_v3/pilot --seeds 50001 --resume
```

The arithmetic verifier independently reconstructs fund and paired utility,
turnover costs, pre-return geometric certificates, Catoni bets and the nine
tail betting capitals from saved weights and replayed market returns. It also
checks the evaluator-only continuations. It loads no checkpoint or test-process
state. This verifies numerical consistency, not global testing control or
economic superiority.

The initial full-strategy v1 is retained as diagnostics after a cancellation
failure in seed 50005. Version 2 forms policy differences before projection
and utility evaluation, with no economic retuning; it replays the complete
original pilot pool and retains the failed market. See the protocol for the
correction and counting rule. Completed checkpoints are losslessly compressed
and verified by SHA-256; unfinished annual checkpoints remain resumable.

```sh
# Run a declared contiguous pilot pool using independent worker processes.
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/run_full_strategy.py --config configs/full_pilot.json --output outputs/park_revive_full_v3/pilot --start-seed 50001 --count 100 --workers 2 --resume
.venv/bin/python scripts/verify_full_strategy.py --output outputs/park_revive_full_v3/pilot
.venv/bin/python scripts/build_full_results.py --output outputs/park_revive_full_v3/pilot --destination reports/full_v3_results
# Final pool: specified, not a statement of completed execution.
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/run_full_strategy.py --config configs/full_main.json --output outputs/park_revive_full_v3/main --start-seed 60001 --count 500 --workers 2 --resume
```


For larger stages, the staged runner executes and independently verifies batches
before releasing their regenerable checkpoint caches. All score, weight,
return and event ledgers stay available; empirical inputs are never touched.
Cached replay checks are reused only when the verifier and every relevant
input byte still match.

```sh
.venv/bin/python scripts/run_full_study.py pilot --workers 2 --batch-size 10 --compact-verified-checkpoints
# Run the separate final stage only after assessing the completed pilot.
.venv/bin/python scripts/run_full_study.py main --workers 2 --batch-size 10 --compact-verified-checkpoints
.venv/bin/python scripts/audit_horizon_examples.py
.venv/bin/python scripts/audit_search_budget.py
```

The manuscript title now emphasizes trading costs, moment information and the
cost of waiting. PARK/REVIVE remains the implementation name. Mathematical
research notes under `paper/notes/` are explicitly excluded from the manuscript
until separately audited; they are not reported theorems or simulation results.

The current full-strategy implementation is v3: a preserved QP convergence
failure triggers exact objective preconditioning, with original-unit KKT guards.
The same whole pilot pool is replayed; no failed seed is excluded. The manuscript
currently retains its explicitly labeled first-ten **v2** snapshot. To reproduce
that paper snapshot, use `scripts/build_paper.py --full-pilot-count 10`; its default
input is deliberately still the retained v2 directory. New v3 results are kept
separately until audited. See `reports/full_strategy_protocol.md`.

## Separate vanishing-gain research diagnostic

The costless scalar cash-PARK study is frozen separately at `57752eb`. It has
4,096 paths per law and 65,536 observations, with no financial minimum-effect
floor. It does not add financial market replications or alter the primary arms.
The proof audit and completed results are in
[`reports/vanishing_gain_proof_audit.md`](reports/vanishing_gain_proof_audit.md) and
[`reports/vanishing_gain_results/interpretation.md`](reports/vanishing_gain_results/interpretation.md).
Only three alternative paths cross the 5% threshold under linear betting;
asymptotic information growth does not imply useful finite-horizon power.
The audited cash-PARK theorem and its complete proof are now included in the
main manuscript, together with this low-power diagnostic. Historical derivation
notes remain separate. The sharp confidence exponent concerns this particular
costless instance; it is not an expected stopping-time theorem or a claim of
financial superiority.

```sh
# Fresh checkout: generate the declared scalar streams once.
.venv/bin/python scripts/vanishing_gain_study.py
# Independently replay eight paths per law and build the diagnostic report.
.venv/bin/python scripts/audit_vanishing_gain.py
# Re-render the retained report without repeating simulation or arithmetic replay.
.venv/bin/python scripts/audit_vanishing_gain.py --plot-only
# Deterministic quadrature checks of identities used in the proof.
.venv/bin/python scripts/audit_vanishing_theory.py
# Rebuild the manuscript table from the retained audited report.
.venv/bin/python scripts/build_vanishing_results.py
```

## Selecting lambda for a rejection horizon

The manuscript now distinguishes maximizing a lower power certificate, exact
working-model log growth, and rejection probability by a fixed deadline.
A predictable Bellman policy targets the third objective. In the controlled
Gaussian score study, its 400-observation power is 37.48% versus 11.41% for the
original past-mean certificate rule. Both have individual nominal 5% bounds;
actual null rates differ. This does not establish financial outperformance.
See [`reports/lambda_power_v2_results/interpretation.md`](reports/lambda_power_v2_results/interpretation.md)
and the version-correction record in
[`reports/lambda_power_protocol.md`](reports/lambda_power_protocol.md).

```sh
# Fresh checkout only: generate the separately frozen controlled experiment.
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/lambda_power_study.py build
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/lambda_power_study.py evaluate
# Independent replay of its retained paths and stakes.
.venv/bin/python scripts/audit_lambda_power.py
# Rebuild only table and figure from the retained small report.
.venv/bin/python scripts/build_lambda_results.py
# Rebuild the manuscript while keeping the financial snapshot at ten v2 seeds.
.venv/bin/python scripts/build_paper.py --full-pilot-count 10
```
