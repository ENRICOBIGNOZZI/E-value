# Complete pilot: 100 independent markets

The declared pilot contains exactly seeds **50001–50100**, with six methods
in every market. The separate final pool is **60001–60500**. Earlier snapshots
and same-seed corrected implementations are not additional replications.
Scientific settings, betting rules and the final analysis remain frozen.
No empirical inputs are read or acquired.

| Method | Mean h-scaled utility | MC SE | Mean final wealth | Mean inactive fraction |
|---|---:|---:|---:|---:|
| All Signals | 0.044286 | 0.001128 | 1.889 | 0.000 |
| Greedy | 0.051661 | 0.000743 | 2.083 | 0.071 |
| HAC | 0.051000 | 0.000754 | 2.064 | 0.071 |
| Catoni | 0.000000 | 0.000000 | 1.000 | 1.000 |
| Tail | 0.011038 | 0.000432 | 1.170 | 0.821 |
| Oracle | 0.058438 | 0.000497 | 2.282 | 0.000 |

Utility is mean out-of-sample daily quadratic utility multiplied by h=252,
including modeled actual costs and waiting dates. It is not an annual return
or certainty equivalent. The Oracle uses current moments and is myopic;
its wealth is not an upper bound on lifetime wealth.

The paired Tail-minus-All-Signals difference is **−0.033248**, with approximate
pointwise Student 95% Monte Carlo interval **[−0.035601, −0.030894]**, using
100 paired markets and 99 degrees of freedom. Tail-minus-Greedy is −0.040623,
interval [−0.041867, −0.039378]. These are exploratory pilot contrasts.
Comparator priority for the final analysis was fixed after inspecting the
first ten v2 and twenty v3 pilot results, before any final output; it was not
registered before pilot inspection. All five contrasts are retained in
`pilot_100_planned_analysis_diagnostic.json`, including negative differences.
Secondary intervals are unadjusted. Different allocation paths and support
choices prevent a causal decomposition of these gaps into waiting costs alone.

Tail makes **99 choices in 99 markets**, all ENTRY and all executed before
the horizon. It has no PARK, REVIVE or SWAP, and one market remains in cash.
Entry reviews are in simulation calendar years 10–14, including the training
year. The mean inactive fraction is 0.821429. These observations do not support
claims of successful parking/revival or general economic superiority.
Catoni makes no choices in any market; zero observed entry does not imply
zero population probability. All Signals permits 100 signals but averages
**4.5408 effective sleeves**, counted after the run at absolute weight above
1e-6. The design charges no fixed per-signal research cost.

All 99 Tail deployments have positive evaluator-only next-period gains,
averaging **0.930833 basis points** of daily utility after entry costs.
Greedy and HAC execute 620 and 285 deployments; their mean next-period gains
are −0.712123 and −0.255833 basis points. A negative first-day gain need not
mean negative lifetime trade value. These gains are descriptive evaluator
quantities, not quantities certified by the historical episode test. The
full fund paths supply the executed economic comparison. Terminal choices
remain in the decision count and are excluded from deployments.

The independent arithmetic replays contain **883,124,214 scalar checks**
and **13,201 ghost pairs**. The complete seal binds current raw digests and
all report files. The independent market-summary audit checks **14,945
scalar summaries**, with maximum discrepancy 1.78e-15. A separate raw-JSON
report audit checks **1,275,416 numeric values** and **2,223,533 structural
conditions**, with zero aggregation discrepancy. It covers 23,248 events,
157,708 registry rows, 1,033 choices and 1,004 executed deployments.
The retained deployment-identity residual is at most 1.01e-10, below the
serialization-derived 1.51e-10 bound; the economic positivity tolerance
remains 1e-8.

Independent event reconstruction reproduces **23,248 stable events** and
**2,206 unstable runs**, using 602,810 annual-mean checks and 13,201 ghost
columns. It retains 524 events selected at onset and confirmed after closure,
including terminal choices; these are not all executed deployments. The
largest annual-mean discrepancy is 1.09e-19. Method-specific event populations
are not common causal risk sets. Checks of existing records add no markets
and do not substitute for the assumptions of the mathematical results.

The paper now displays this complete pilot instead of its earlier ten-market
snapshot. The separate lambda-power experiments and analytic stake-selection
results remain separate evidence: they are not new financial arms or grounds
for tuning the current financial study. The final 500-market assessment,
final graphics and final manuscript integration remain outstanding.
