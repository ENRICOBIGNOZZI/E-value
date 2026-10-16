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
