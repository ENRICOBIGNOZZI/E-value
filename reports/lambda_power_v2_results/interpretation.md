# Selecting lambda for finite-horizon power

The earlier choice delta/(2 nu²) maximizes a quadratic lower certificate for
power. It does not maximize the actual probability of rejection by a deadline.
The new rule uses a Bellman recursion for that crossing probability, with
current log evidence and remaining review blocks as state. Its optimum is
relative to a declared working score law and finite action class; the
implemented state grid introduces an additional numerical approximation.

## Controlled evaluation

The fixed working law is N(.1,1), the public raw-second-moment bound is 1.09,
and every rule uses the same 100-observation betting/review calendar, stake cap
and individual nominal 5% threshold. Evaluation uses 20,000 paths under each
of the actual score means 0, .1, .2 and .3, with variance one. Within each law
all methods share the same paths. Different target horizons use different
deadline-specific policies, rather than one policy monitored at three dates.

At design mean .1:

| Rule | Power at 400 | Power at 800 | Power at 1600 |
|---|---:|---:|---:|
| Original past-mean certificate | 11.41% | 37.76% | 78.29% |
| Fixed certificate | 4.00% | 44.94% | 93.04% |
| Fixed exact log-growth optimum | 28.31% | 66.50% | 92.44% |
| Greedy one-block power | 25.53% | 34.10% | 36.04% |
| Horizon power, primary grid | **37.48%** | **72.83%** | **97.07%** |
| Horizon power, refined grid | 37.47% | 72.81% | 97.13% |

At 400 dates the primary policy rejects on 7,496/20,000 paths, versus
2,281/20,000 for the original past-mean rule. Their paired power difference is
26.08 percentage points, with Monte Carlo 95% interval [25.47,26.68]. These
figures use integer counts and decimal half-up rounding.

At the boundary null, the corresponding 400-date rejection fractions are
1.42% and .11%. Both procedures have the same individual nominal 5% validity
bound, but their actual type-I errors are not matched. This experiment does
not demonstrate dominance at matched actual size, search-wide 5% control, or
power optimality for an unknown score law. The fixed log-growth optimum also
loses to the fixed certificate at the longest horizon: log growth, a power
certificate and finite-deadline power are distinct objectives.

## Provenance and independent checks

Source freeze `bbd619f` preceded the corrected full replay. The protocol
records the v1 near-threshold lookup bug: rounding a strictly subthreshold
real capital into the absorbing grid boundary prematurely froze some paths.
V2 prevents that rounding. The entire original seed-440001 pool was replayed;
v1 and v2 are not additional replications. All model arrays are bitwise
identical between versions. V1 outputs remain diagnostics, with no change to
the working alternative, numerical grids, horizon, threshold, stake cap or
evaluation seed.

The two models' predicted design powers differ by at most .000396. All six
predicted-versus-observed power checks pass the declared .005 numerical
tolerance plus five Monte Carlo standard errors. The independent audit checks
12,331,336 scalar values, reconstructing every horizon-policy/fixed stake and
every first crossing. Direct multiplication of score factors and the
past-mean stake reconstruction cover the declared first sixteen paths per law;
they do not replay every generated score path. Maximum prefix log-capital
discrepancy is 6.18e-14. The complete repository suite passes 53 tests.

The retained small report includes the primary model so its figure and table
can be rebuilt without the large raw output directory. Full raw paths and
the refinement model remain in `outputs/lambda_power_v2/`; input hashes are
in `verification.json`. The manuscript adds a concavity proof for exact
working-model log growth and the standard finite-horizon Bellman argument.
Neither is presented as a new general optimal-control principle.

## Financial scope

This is a scalar statistical experiment, not a new financial market study or
a change to the frozen financial methods. A financial power model would need
the evolving estimation, allocation, cost and score states. Current results
do not establish improved economic performance or fix conservative financial
moment certificates. The original theory-and-simulation paper goal remains
active and incomplete; no empirical analysis was run.
