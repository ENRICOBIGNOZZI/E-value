# Fresh comparison against horizon-optimized constant bets

The original lambda study establishes a large improvement over its past-mean
certificate and log-growth comparators. Those rules do not optimize actual
deadline power, so that comparison alone cannot isolate the benefit of
adapting to accumulated evidence. This separately frozen companion supplies
the missing constant-power benchmark, with the same working model, stake cap,
nominal level and betting/review calendar.

The code, protocol and models were frozen at **c73e713**, before drawing the
fresh **450001** evaluation stream. Each actual score mean 0, .1, .2 and .3
has 20,000 independent Gaussian paths with variance one. All arms share paths
within each law. Earlier study results are neither pooled nor replaced.
Regenerating each stream to evaluate the new constant arms does not add
replications; it shares exactly the same scores with the original arms.

## Model selection before evaluation

For each of the original primary/refinement action grids, compute a hitting
probability recursion with the same single constant action at every state.
Maximize its initial value separately at each deadline. Both grids select:

| Deadline | Selected constant lambda | Primary predicted power | Refined predicted power |
|---|---:|---:|---:|
| 400 | .1272113035 | .327695 | .327231 |
| 800 | .0897962142 | .663445 | .663040 |
| 1600 | .0636056518 | .945798 | .945779 |

The maximum refinement difference is .000465, below the existing .005
criterion. The optimizer is relative to the declared working law and grid;
it is not a continuous-action or unknown-law global optimum. The numerical
lower boundary is absorbing in the value calculation. The actual constant
rule keeps betting below that boundary until rejection or its deadline;
predicted-versus-observed calibration explicitly assesses this approximation.

## Fresh observed design-law results

| Deadline | Best constant | Horizon DP | Paired DP gain (percentage points) | 95% MC interval |
|---|---:|---:|---:|---:|
| 400 | 6619/20000 = 33.10% | 7470/20000 = 37.35% | 4.26 | [3.96,4.55] |
| 800 | 13203/20000 = 66.02% | 14542/20000 = 72.71% | 6.70 | [6.33,7.06] |
| 1600 | 18883/20000 = 94.42% | 19351/20000 = 96.76% | 2.34 | [2.12,2.56] |

Percentages use exact integer counts and decimal half-up rounding. Intervals
use independent paths and paired crossing indicators; they are pointwise
normal approximations and unadjusted across comparisons. In the stronger-law
CSV, a paired interval can have zero estimated width when every paired outcome
coincides. That is not proof of population equality or absence of Monte Carlo
uncertainty; marginal Wilson intervals remain nondegenerate. Refined DP powers are 37.41%, 72.74% and
96.79%, with paired gains 4.31, 6.73 and 2.37 percentage points. The constants
are the same on both grids and therefore their actual paths coincide.

At the boundary null, primary-DP crossing fractions are 1.29%, 1.85% and
2.16%; corresponding constant fractions are 1.04%, 1.46% and 1.71%. The
comparison has a common **individual nominal 5%** validity bound, not matched
actual type-I errors. It demonstrates improvement relative to the chosen
constant-power benchmark at that nominal bound, not matched-size dominance
or search-wide error control. The stronger actual alternatives .2 and .3,
every earlier comparison arm, and all failed-to-cross paths are retained in
the complete CSV. Power approaches one under stronger effects; no universal
ranking outside the specified design law is inferred.

## Verification and scope

All twelve predicted-versus-observed DP/constant design-power checks pass the
predeclared .005 numerical tolerance plus five Monte Carlo standard errors.
The independent audit checks **20,497,504 scalar values**, reconstructing every
DP/fixed stake and every first crossing. Direct multiplicative score replay
and past-mean reconstruction cover the declared sixteen-path prefix per law,
not every score path. The maximum prefix log-capital discrepancy is 8.89e-14.
Source/configuration/model fingerprints match the pre-evaluation freeze.
The full repository suite has **55 passing tests**; the fresh scientific run
took 65.44 seconds alongside the ongoing financial study.

The added benchmark is subsequent research with a fresh evaluation, explicitly
distinguished from the original lambda experiment. It changes no financial
scientific source or configuration, adds no financial market replications,
and supplies no claim of improved fund performance. The broader paper goal
remains active and incomplete.

All four small numeric models are retained in this report directory. A fresh
checkout can copy these and `model_manifest.json` into an empty output directory
and run the frozen evaluation without first rebuilding or obtaining any old
score paths. The README gives the exact commands. The independent audit checks
the restored model bytes against the pre-evaluation freeze.
