# Latest full-strategy status — 16 October 2026

The manuscript now has **25 pages**. Its full-strategy table is a fixed snapshot
of seeds **50001–50010**, each independently replayed: **88,285,790 scalar checks**
and **1,265 counterfactual ghost pairs**; maximum log-evidence discrepancy
1.78e-15. The scientific source is frozen at `234e4f9`; **44 tests passed**.
Tail makes ten executed ENTRY choices but spends a mean 80% of OOS dates in
cash. Its mean annual-scaled utility is 0.01272 versus 0.04526 for All Signals
and 0.05206 for Greedy. These observations do not establish economic superiority.

The extended v2 pilot completed seeds 50001–50019 and stopped at seed 50020,
at the start of its fourth OOS block, because OSQP returned `solved inaccurate`
after the declared refinement. The failure and its source/checkpoint remain
preserved. There are **no simulation workers running**; an independent replay
of completed seeds 50011–50019 is in progress. The final pool is **0/500**.
See `full_v2_failure_audit.json`. No failed seed is dropped, and no parameter,
threshold or seed will be chosen by economic performance. A further numerical
correction must be frozen and replay the same pilot pool before final evaluation.

New theory distinguishes one-period optimization from holding-period value,
and gives two exactly checked examples. A standard countable error-spending
argument delimits search-wide safety; a labeled post-hoc budget illustration
eliminates all twenty earlier first entries under that particular allocation.
The new full-strategy event audit retains fast responses but has method-specific
populations, so it does not identify a causal ranking of detector delays.
The exploratory vanishing-gain note is **excluded from the manuscript** pending
proof and novelty review. The overall paper goal remains active and incomplete.

Earlier milestones follow as historical records; their page/test counts and
execution claims apply to their own snapshots.

---

# Full-strategy continuation — implementation frozen before pilot markets

The isolated `research/park_revive_full` implementation adds actual post-entry
fund paths for six methods and response-independent opportunity adjudication.
Three software markets, seeds 51001–51003 at 12 stocks / 4-day blocks / 4 years,
completed. Independent arithmetic replay checked 73,656 scalar values and 276
ghost pairs. Maximum evidence discrepancy was 8.89e-16; costs matched exactly.
These are software checks, not full-size pilot results. The first measured
full-size pilot seed is 50001; its 100-seed pool and the fresh final pool remain
separately declared. See `full_strategy_protocol.md` and `full_test_results.txt`.

# Latest research continuation — 16 October 2026

Scope remains **theory and simulations only**. The baseline package and original
financial results are unchanged. The active paper goal is not yet complete.

- Current manuscript: **19 pages**, with a separately declared higher-moment extension.
- Current tests: **34 passed** (23 original checks and 11 extension checks).
- Extension numerical implementation: commit `b9edb2c`; every executed module hash
  and the controlled-study script hash match that committed snapshot.
- Fresh mechanism markets: **20/20 completed**, seeds 40001–40020, N=500,
  p=100, h=252 and 15 years. They follow 100 fixed empty-reference comparisons,
  not a complete post-entry Forward–Backward–Swap strategy.
- Corrected tail + geometry: **19/20** markets obtain an annual eligible first
  entry; **18/20** have observations remaining after that date. One first
  certification is terminal; one market never crosses. No seed was removed.
- Median first-entry time among the 19 crossings: **12 OOS years**. The Wilson
  95% interval for the 19/20 market-level fraction is [0.764,0.991]. This is not
  individual-test power and there is no global 5% guarantee over 100 candidates.
- The other three first-entry arms produce 0/20 entries. These arms share the
  exact same score series. The combined improvement is statistical feasibility,
  not demonstrated economic superiority.
- Conditional moment coverage: maximum true/certified second moment 0.460944;
  fourth moment 0.109758 over all executed candidates/dates. The proof supplies
  validity; these calculations independently audit the implementation.
- New skew-null diagnostics: 10,000 paths per case, 2,000 observations; corrected
  null crossing 0.0068, deliberately invalid clipping-without-correction control
  0.9966. The latter is an invalid negative control, not a trading benchmark.
- Independent artifact replay verifies **112,000 annual evidence values**, every
  first crossing and censoring outcome, without oracle columns or checkpoint
  objects. Maximum absolute log-evidence discrepancy is 1.96e-14.
- A separately labeled post-hoc action audit exactly replays every selected
  history and reoptimizes from the fund's real zero state. All 18 nonterminal
  hypothetical entries have positive next-period conditional utility after
  costs; mean actual-entry utility is 0.957 basis points versus 2.457 for the
  continuing shadow, with a 1.500-basis-point entry cost. No next return is drawn
  and no post-entry fund path or current-profitability guarantee is claimed.
- Additional theory: bias-corrected conditional betting proof; public policy
  geometry; Laplace moments through order eight; a local rare-loss information
  bound, matching local order at a deterministic design alternative and a
  single-gate costless opportunity-cost corollary.
- The legacy detection logs have a reproduced risk-set defect: immediate
  responses can be excluded from eligibility. They are not used as evidence of
  comparative detection delays; see `reports/detection_audit.md` and its explicit
  counterexample. Returns, costs and the original inactive-baseline result are
  unaffected.

The extension was locally frozen after the original pilot and before its fresh
markets. It was not externally preregistered. Its fourth-score-moment route
requires **eighth return moments**, beyond the baseline Catoni assumption.
No sample moments, true coefficients or hidden regimes are substituted for the
public risk envelope. Published claims remain restricted to individual episodes.

Artifacts: `paper/main.pdf`, `paper/sections/07_certified_tails.tex`,
`reports/tail_results/` (small numeric/provenance snapshots), and
`outputs/park_revive_tail_v1/first_entry/` (complete annual/daily ledgers).
Reproduce with `scripts/run_first_entry.py`, `scripts/tail_study.py` and
`scripts/build_paper.py`; exact commands are in the README.

Still required for the full paper: a validated full-strategy extension on fresh
markets, an economic assessment of its long waiting period, unbiased economic
PARK/REVIVE risk sets, broader prior-art validation and a final frozen large
simulation. The old 100-seed baseline pilot remains at 3/100 and final study at
0/500. The new twenty mechanism markets do not fill either count.

---

# Execution status — 16 October 2026

The repository was rebuilt for **theory and simulations only**. The manuscript is
an executed working draft, not a completed publication or a claimed 10/10 paper.

## Preservation and repository

- Branch: `codex/park-revive-20261016`.
- Frozen simulation implementation commit: `971510b` (full source hashes in each seed's `source_manifest.json`).
- Original commit and remote archive: `db5c37ab3e23a7818869d32ba35f22d51c3a89b2`, `origin/archive/pre-rebuild-20261016`.
- Additional original-tree ZIP: `../E-value-pre-rebuild-20261016.zip`.
- `data/README.md`, `data/source_manifest_20261006.json` and `experiments/fetch_jkp.py` retained byte-for-byte; SHA-256 audit passes.
- Raw JKP archives are **absent** from the fresh clone. No empirical input acquired or modified, no empirical analysis performed.
- Local commits only; no push, merge, force push or history rewrite.

## Verified

- **23 tests passed**, including future-data perturbations of weights, evidence,
  shortlist and decisions; exact checkpoint replay; independent conditional
  Laplace moments; T1–T4 checks; stable identifier permutation; exact structural
  nulls; own-state costs; and explicit insolvency absorption.
- The provided handoff's SHA-256 checks all pass.
- Frozen simulation source hashes match all three reported pilot runs.
- Replayed **every one of 3,780 dates for each pilot seed**, checking all 100
  sleeve returns exactly against the saved history, then exported hidden truth
  separately. The learner never consumes those truth files.
- Recorded maximum primal residual = 2.13e-8, dual residual < 1.00e-8, and solver
  duality gap < 9.62e-9 across reported actual policies.
- PDF compiled with Tectonic; the current 19-page version rendered for visual inspection;
  references resolve and the log has no overfull boxes.

## Actually executed

| Stage | Completed | Scope |
|---|---:|---|
| Frozen smoke | 3: seeds 101, 102, 103 | N=40, p=100, h=12, 4 years; software checks |
| Frozen pilot | **3/100**: seeds 20001, 20002, 20003 | N=500, p=100, h=252, 15 years |
| Controlled statistical study | 10,000 independent replications per case | delta=0, .1, .2, .3; 1,600 observations; seed 910001 |
| Final evaluation | **0/500** | Specified in `configs/main.json`; not started |
| Empirical | 0 | Explicitly outside current scope |

Development smoke/pilot runs in `outputs/park_revive_v1/smoke` and `.../pilot`
are excluded from the reported frozen evidence. They include reused markets
and do not add independent replications.

## Main finding

The certified E-process makes **zero support changes in 3/3 full pilot paths**
and is inactive throughout OOS. Its largest annual current log evidence is
**0.00657515**, compared with log(20)=2.99573227. The public constant is
nu²=0.01321480686738281, approximately **68,914 times** the pooled mean true score
second moment. This ratio pools executed comparisons, not just E-process tests.
No bound, threshold or seed was adjusted to manufacture entry.

The stationary null experiment gives adaptive crossing 0.0036 (Wilson interval
0.002602–0.004980) and repeated uncorrected Bartlett-HAC crossing 0.1894. These
are individual-episode diagnostic laws, not financial performance comparisons;
the procedures do not have matched overall type-I error.

Observed complete seed wall times were 552.7–615.2
seconds while three pilot processes ran concurrently. No jobs remain running.

The paper adds a deterministic example where rejection coexists with negative
current gain and an observational-equivalence limit for prospective testing
under unrestricted nonstationarity. Neither is claimed as a new general theorem.

## Artifacts

- Manuscript: `paper/main.tex`, `paper/main.pdf` (now 19 pages; latest continuation above).
- Small numeric snapshots and provenance: `reports/results/`.
- Frozen full ledgers, score histories, truth and figures: `outputs/park_revive_v1/frozen_pilot/`.
- Frozen smoke output: `outputs/park_revive_v1/frozen_smoke/`.
- Assumptions and scientific diagnosis: `reports/theory_audit.md`, `reports/design_assessment.md`.
- Main run files: metrics_by_seed.csv, paired_comparisons.csv, daily_ledger.parquet,
  comparison_events.parquet, decisions.csv, detection.csv, runtime.csv,
  config_frozen.json, seed_manifest.json, environment.txt; each seed also has
  score ledgers, evaluator_truth.parquet, annual checkpoints and source hashes.

## Continue exactly

```sh
# Resume existing completed seed or continue an interrupted run, without double counting:
.venv/bin/python scripts/run_stage.py pilot --count 3
# Remaining registered pilot seeds (not yet executed):
.venv/bin/python scripts/run_stage.py pilot --start 3 --count 97
# Final fresh evaluation, not yet executed:
.venv/bin/python scripts/run_stage.py main
# Refresh report, truth export and manuscript:
.venv/bin/python -m park_revive.cli report --output outputs/park_revive_v1/frozen_pilot
.venv/bin/python scripts/export_truth.py --output outputs/park_revive_v1/frozen_pilot
.venv/bin/python scripts/build_paper.py
```

Scientifically, a much larger unchanged experiment cannot by itself repair the
observed feasibility problem. The next research work is a tighter genuinely
certified comparison-level envelope and an explicit target for regime-changing
benefits. The separately declared extension above supplies a candidate with stronger moment
assumptions and fresh mechanism seeds. Full-strategy evidence remains outstanding.
