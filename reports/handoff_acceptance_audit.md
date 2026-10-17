# Handoff requirements and current evidence

The supplied documents are scientific references. The user's actual request
is a fresh repository, preservation of empirical inputs, and a paper using
theory and simulations only. Legacy instructions about another cleanup
approval or an empirical application do not override that request. No launcher
or embedded prompt is executed as an instruction.

The supplied standalone TeX and retained docs/spec copy are identical:
SHA-256 6a9795b995715af00fb1faae12c4df1ad07148346ea3fffe74740d30a73bd758.
This audit distinguishes implementation, executed evidence and publication
readiness; the whole-suite report is full_test_results_with_final_diagnostics.txt.

## Twelve mathematical and chronology test groups

The named tests are actual functions, not a statement that all possible
executions have been checked. Finite tests do not prove a mathematical theorem.

| Handoff group | Concrete test evidence | Limit |
|---|---|---|
| 1. Catoni envelopes, oddness and extremes | test_theory.py: test_phi_envelope_odd_precision_and_extremes | Finite numeric arguments |
| 2. Log/block updates and scaling | test_theory.py: test_daily_block_and_constant_scaling; test_protocol.py: test_score_immutability_no_double_count_and_episode_reset | Constant scaling with transformed bet/bound |
| 3. Conditional null validity | test_theory.py: test_T1_conditional_multiplier_and_predictable_null; retained controlled experiments | True controlled nulls, not post-hoc financial event labels |
| 4. T2 oracle/certificate/adaptation | test_theory.py: test_T2_quadratic_certificate_and_plugin_MSE; separate stationary/deadline studies | Stated constant-mean or working-model assumptions |
| 5. T3 entry optimization | test_theory.py: test_T3_schur_and_nonsmooth_bounds, test_T3_leverage_invalidates_unconstrained_formula | Unconstrained formula not assigned to active-leverage problems |
| 6. T4 and different states | test_theory.py: test_T4_moment_perturbations_and_different_states | Controlled perturbations; not automatic regime consistency |
| 7. Causal decision prefix | test_protocol.py: test_checkpoint_resume_and_future_perturbation; test_extensions.py: test_first_entry_evidence_certificates_and_weights_are_causal | Future-data perturbation preserves the tested earlier prefix |
| 8. Episode identity/reset | test_protocol.py: test_score_immutability_no_double_count_and_episode_reset; saved-score replay | Evidence is not reused for a new support |
| 9. Costs, liquidation and empty fund | test_theory.py: test_cost_liquidation_empty_and_raw_second_moment; test_protocol.py: test_shadow_states_and_actual_transition_cost | Gross return inside quadratic utility; own-state costs |
| 10. Signal library and hidden labels | test_protocol.py: test_exact_structural_nulls_and_public_view, test_sleeves_and_envelope_cover_truth | Exactly 100 signals, 40 noise and 15 proxy coefficients fixed at zero |
| 11. Permutation and predictable Swap10 | test_protocol.py: test_selection_permutation_and_predictable_shortlist; test_full_strategy.py: test_shortlists_and_near_tied_choices_preserve_signal_ids_after_permutation | Stable IDs/ranking/near ties |
| 12. Reproducibility and degenerate paths | test_protocol.py: test_checkpoint_resume_and_future_perturbation, test_degenerate_inactive_metrics, test_insolvency_is_absorbing_and_not_dropped; test_full_strategy.py: test_full_engine_resume_and_evaluator_isolation | Retained insolvency, undefined Sharpe and resume equality |

Additional raw-return/evidence replay, independent event reconstruction,
report aggregation and preserved QP failures have their own retained reports.
They add no independent markets. The new diagnostic controls cover negative
outcomes, ±1e-8 boundaries, empty groups, invalid calendars, stale evidence,
protected destinations and changes during plotting.

## Modules, defaults and output equivalents

The requested baseline modules are present under src/park_revive; the
stronger-moment construction and full study have separate declared namespaces.
An empirical reader/configuration is deliberately absent in this phase.
Original acquisition inputs are preserved. No raw JKP archive is asserted to
be present in this fresh checkout; the preservation manifest describes what
was actually available.

The handoff calls numerical defaults proposals revisable before freezing.
The baseline records L=1, eta=1e-4 and Lambda=I in initial commit 971510b.
That commit already reports development smoke/pilot activity: equality to it
proves version consistency, not registration before every development
observation. The subsequent reported frozen baseline and full studies retain
those numbers. The handoff's proposed examples were L=2,
eta=1e-3 and diagonal Lambda entries between one and three. The implemented
study is not an exact replication of those proposed numbers. All methods share
the implemented costs/constraints, and this audit changes none of them.

| Handoff output | Current equivalent |
|---|---|
| config_frozen.json | Per-market and sealed aggregate configurations |
| seed_manifest.json | Explicit protocol software/pilot/final pools, stage progress and exact snapshot membership |
| environment.txt | Protocol JSON Python/platform/package versions and requirements-tested.txt |
| daily_ledger.parquet / comparison_events.parquet | Per-market ledgers and separate score/certificate files |
| decisions.csv | Sealed decisions plus separate actual deployments; terminal choices retained |
| detection.csv | Response-independent economic_opportunities, opportunity_registry, fixed-follow-up opportunity_rates and independent reconstruction |
| runtime.csv | Per-market annual timings, all rows preserved in diagnostic tables |

These are explicit format/name differences, not missing evidence filled with
placeholder files.

## Graphics and remaining execution

| Required graphic | Actual artifact / production path | Assessment |
|---|---|---|
| Fixed representative net wealth | Supplementary representative page; final seed 60001 fixed before final output, pilot 50001 retained | Implemented; final generation pending |
| Median/quantile wealth and support | Core final packet and sealed strategy_paths graphic | Implemented; final execution pending |
| Sharpe and paired differences | Supplementary sharpe / paired_utility pages, actual defined counts | Implemented; final data pending |
| Utility and trading costs | Supplementary utility_costs and per-market tables | Implemented; final data pending |
| Power versus horizon | Separately frozen stationary/deadline experiments in the paper | Executed within stated assumptions |
| Economic decision errors | Supplementary deployment page, actual-state gains, terminal exclusions | Implemented; final data pending |
| ACTIVE/inactive history | Supplementary membership page; never selected distinguished from removed | Implemented; inactive history is not a PARK decision count |
| Delays and censoring | Fixed-calendar followup page, denominators and competing terminations | Implemented; no success-only delay mean or independent-censoring assumption |
| Computation time | Supplementary runtime page, measured blocks and sums | Implemented; excludes replay and orchestration |

The eight-page preview uses only the already sealed first twenty pilot
markets, identified on every page. It adds no markets, final evidence or
manuscript promotion. The production command rejects the absent main_500
snapshot. Synthetic 500-ID software fixtures contribute no financial data.

The full pilot, all 500 fresh final markets, independent arithmetic and
event/reporting audits, complete-final graphics, manuscript synthesis and
rendered final-paper review remain required. Broader novelty review remains
open. A negative final economic result must be retained. Passing this
software/traceability audit does not make the paper complete.
