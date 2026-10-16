# Economic analysis fixed before the final study

This plan is frozen **during the pilot**, after inspecting the first-ten v2
table and the first-twenty v3 interim performance report. It is not a plan
registered before those pilot results. No final-market output is present at
this freeze. The economic source, configurations, signal library, methods,
thresholds and previously declared seed pools remain unchanged.

The final sample is all **500 markets 60001–60500**. Pilot markets, same-seed
version replays, software fixtures and controlled score experiments contribute
zero observations to that final sample. All six methods share a market within
each seed; markets are independent conditional on the fixed signal library and
the stated DGP. No sequential increase/decrease of the final sample size is
allowed according to interim effect estimates or interval widths.

The primary metric remains **mean OOS daily quadratic utility multiplied by
h=252**, as in the supplied specification and the implemented protocol. It
includes all actual fund costs and waiting in cash. Scaling by h changes
units; this is not an annual return or annual certainty equivalent.

The primary economic contrast is **Tail minus All Signals** in that metric,
averaged across paired markets. All Signals permits all candidates under the
same allocation constraints; its effective holdings may already be sparse.
This asks whether the extra statistical support filter improves realized
implemented utility in this design, which charges no per-signal research cost.
The comparator priority is selected at this pilot-stage freeze, not before
observing the unfavorable pilot gap. Final evaluation remains separate.

Tail-minus-Greedy, HAC, Catoni and Oracle contrasts are retained as secondary.
Every contrast uses its 500 within-market utility differences, their mean,
sample standard deviation divided by sqrt(500), and a **two-sided pointwise
95% Student Monte Carlo interval with 499 degrees of freedom**. These are
approximate MC intervals for the stated simulation law, not finite-sample
distribution-free or simultaneous guarantees. The primary contrast has no
outcome-dependent choice of direction or reference. Secondary intervals remain
unadjusted and descriptive. A zero observed standard error does not establish
zero population uncertainty. Missing/nonfinite primary utility outcomes cannot
be dropped or replaced by zero; they prevent a complete final assessment.

The report retains all six methods, every original per-seed metric and every
declared paired contrast, including negative results. Final wealth, drawdown,
inactivity, support size, permitted/effective sleeve counts, structural choices
and lifecycle incidences remain secondary. Undefined Sharpe ratios retain
their actual denominators. Event-rate summaries use the previously defined
response-independent cohorts and are descriptive of method-specific
populations. They do not give causal delay rankings or enlarge the number of
independent replications. A one-day deployment gain is not lifetime trade value.

The individual e-test validity contract and the economic comparison are
separate: common nominal individual thresholds do not match actual test size
or provide search-wide 5% protection. Financial inputs do not silently acquire
the separately studied horizon-power lambda policy. No favorable result is
required. A negative final economic comparison is reported without changing
costs, thresholds, seed membership or the reference comparator.

The entire 100-market pilot and its independent replays must finish before
starting final generation. Every final market must finish and independently
replay before sealing `main_500`. Numerical errors stop the run; they do not
exclude a market. Any necessary correction is recorded with its scope and
source freeze, retaining superseded diagnostics and the original failed seed.
No automatic claim of an unchanged scientific design follows from a correction.

`final_analysis_plan.json` binds the machine-readable choices and analysis code
to the existing scientific freeze. `scripts/assess_final_study.py` refuses to
label a pilot or partial final sample as final. Its explicit pilot diagnostic
mode exercises the frozen arithmetic on previously observed pilot paths; it
does not turn them into new evidence. The primary result remains unobserved
until all final markets complete.

```sh
# After every final market and independent replay finishes and main_500 is sealed:
.venv/bin/python scripts/assess_final_study.py \
  --snapshot reports/full_v3_snapshots/main_500 \
  --report reports/full_final_assessment.json
```
