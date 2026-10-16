# Interim financial evidence: first twenty v3 pilot markets

This snapshot contains **50001–50020**, each with all six methods, the same
frozen v3 source and the exact pilot configuration. It is an interim prefix
of the declared 100-market pilot, not a completed pilot or final study. The
reporting contract was specified during pilot execution; this is not an
externally preregistered new experiment. Earlier v1/v2 versions and the same
markets in earlier snapshots are not additional replications.

Independent pathwise arithmetic replay contributes **176,784,154 scalar checks**
and **2,756 ghost pairs** across these twenty markets. The new independent
CSV-based report audit checks **3,425 scalar values**, with maximum absolute
discrepancy 8.89e-16. It recalculates all retained original metrics, method-level
means/medians/standard errors/Student intervals, paired contrasts and market
move incidence. Event-rate and deployment tables are hash-bound by the seal,
but are not independently reaggregated by this report audit. Neither audit
substitutes for the mathematical assumptions or proves economic superiority.

| Method | Mean h-scaled utility | MC SE | Mean final wealth | Mean inactive fraction |
|---|---:|---:|---:|---:|
| All Signals | 0.044146 | 0.002910 | 1.891 | 0.000 |
| Greedy | 0.052368 | 0.001620 | 2.102 | 0.071 |
| HAC | 0.050813 | 0.001543 | 2.056 | 0.071 |
| Catoni | 0.000000 | 0.000000 | 1.000 | 1.000 |
| Tail | 0.012061 | 0.000961 | 1.187 | 0.811 |
| Oracle | 0.058553 | 0.001144 | 2.285 | 0.000 |

Utility is mean daily quadratic utility multiplied by h=252, not an annual
return or annual certainty equivalent. Wealth includes actual modeled costs
and all time spent waiting. The Oracle is a state-matched myopic benchmark,
not an upper bound on attainable lifetime wealth. MC uncertainty uses twenty
independent paired markets; dependent daily observations or events do not
increase that count.

Tail makes and executes exactly one ENTRY in each market, with **no PARK,
REVIVE or SWAP**. The ENTRY reviews occur in simulation calendar years 11–14
(including the initial training year). Its mean inactive fraction is
0.810714. Catoni makes no choices and stays in cash; zero observed entries
does not imply zero entry probability (market-level Wilson 95% interval
[0,0.161125]). Tail's utility is positive relative to cash, but considerably
lower than Greedy, HAC and All Signals in this prefix.

Tail-minus-All-Signals mean h-scaled utility is **−0.032085**, with pointwise
paired Student 95% MC interval [−0.038955,−0.025215]. Tail-minus-Greedy is
**−0.040307**, interval [−0.042850,−0.037765]. These exploratory intervals are
unadjusted across comparisons. They describe this law and prefix, not universal
dominance or a matched-actual-size comparison of statistical procedures.
The performance gaps do not causally isolate waiting: the selected portfolios
and subsequent exposures also differ.

All Signals permits one hundred signals but holds an average of **4.4 effective
sleeves**, counted after the run at absolute weight above 1e-6; its per-market
mean ranges from two to seven. Thus the allocator already supplies considerable
sparsity. The design charges no fixed per-signal research or monitoring cost.
Successful certification alone therefore supplies no economic advantage over
this baseline in the observed prefix.

All twenty Tail deployments have positive evaluator-only next-period gains
after their modeled entry costs. This concerns one day and is not a guarantee
supplied by the historical test. Greedy/HAC moves often have negative first-day
gain after upfront transition costs; that alone does not classify their
subsequent holding value. The full utility paths provide the relevant executed
economic comparison. Method-specific opportunity populations do not identify
causal cross-method delay rankings.

Both snapshot figures were visually inspected: labels and legends are legible,
with no clipping or overlap. The wealth bands are descriptive 10–90% market
quantiles. The evidence plot averages the largest currently open annual capital;
its later decline reflects closing comparisons and does not undo prior
certification. Its dashed threshold is individual, not search-wide protection.

The current manuscript deliberately retains its separate first-ten v2 table.
No parameters, thresholds, seed pools or financial methods are changed by this
report. The same pilot continues to 100 markets, followed by the separate
500-market final pool. No empirical data are acquired or analyzed.
