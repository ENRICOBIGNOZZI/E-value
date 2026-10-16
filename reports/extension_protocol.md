# Declared extension protocol — before fresh simulation

Baseline commit `971510b` and its three pilot markets remain unchanged. This
extension is exploratory development after inspecting the baseline pilot.
It is not an undisclosed parameter adjustment or a confirmatory final study.

## Scientific changes

The new test lower-winsorizes a utility difference Y at -B, then subtracts an
analytic upper bound on the clipping bias. It uses the mixture of nine
nonnegative linear-betting processes with scales (2,4,8) and fractions
(0.25,0.5,0.75). None is selected after seeing the new results. The mixture
itself is the reported process; its loss to a component is at most log(9).

For p>1, `(x-B)+ <= [(p-1)^(p-1)/p^p] x^p/B^(p-1)` for x>=0.
Therefore a predictable bias b=min(v2/(4B),27*v4/(256*B^3)) certifies
E[max(Y,-B)-b | past]<=0 under the original mean null. The factors
1+lambda*(max(Y,-B)-b), with 0<=lambda<1/(B+b), form a nonnegative
supermartingale. No sample moment is substituted for a certified moment.

This changes the moment assumption: a fourth moment of a quadratic utility
score is obtained from **eighth return moments**. The Laplace market supplies
these, but the original T1 applies under weaker assumptions. Neither test is
universally superior on its other's assumption class.

## Public information and geometric certificate

The extension observes the contemporaneous public function values and sleeve
stock weights, already available in the economic filtration but not exposed by
the original minimal allocator API. It never receives theta, realized stock
betas, regimes, structural labels or oracle moments.

The public coefficient set allows **every** signal to have a nonnegative
coefficient up to the common cap, subject to the total coefficient budget.
This contains the true coefficient vector without revealing its support.
The DGP-wide beta intervals [.5,1.5] and [-1,1] for the other three factors are
implied by the generator; no individual beta vector is supplied. Maximum risk
scales cover both normal and stress, even if the multiplier is below one.

Minkowski and Hölder turn public mean/variance caps for the difference and sum
of stock exposures into comparison-specific second/fourth score moments.
These are predictable moments. The constant-nu plug-in T2b/c are not claimed
for this variant.

## First-entry mechanism experiment

- Markets: unchanged N=500, p=100, D=30, h=252, 15-year DGP.
- New seed pool: **40001–40020**; representative seed fixed at 40001.
- One common empty reference and 100 single-sleeve shadow policies. Each
  shadow is trained annually on expanding data and pays its own target costs.
- Daily one-dimensional constrained optimization has an exact soft-threshold
  solution. Verify it against the original independent QP solver before runs.
- All tests receive the exact same realized scores. Arms: frozen Catoni
  constant certificate; predictable Catoni geometric certificate; corrected
  tail betting with a uniform fourth moment; corrected tail betting with the
  geometric fourth moment. The nine-component mixture is used in both tail arms.
- Decisions checked only annually. Record current evidence and first crossing
  per signal and first candidate eligible for entry, with right censoring.
- A positive historical mean score remains a common eligibility filter.
- No post-entry fund, Forward–Backward–Swap strategy, wealth, structural FDR or
  current-regime detection claim is inferred from this mechanism study.
- The individual level is 5%; the maximum across 100 tests has no 5% global claim.
- Conditional-moment oracle calculations are evaluator-only coverage checks.

This experiment asks whether certified first entry is feasible under the
declared stronger moment information. A successful entry does not establish
economic superiority of a full adaptive strategy. A failed entry is retained.

Controlled statistical diagnostics are separately fixed at seed 420001,
10,000 independent paths per case, 2,000 observations and looks every 100.
The cases have conditional means 0, .02 and .05 under a predictable skewed
two-point law. Omitting the clipping correction is an explicitly invalid
negative control, never an investment-method comparator.
Specifically, this deliberately invalid control is a single bettor with
B_t=V4_t^(1/4) and betting fraction .75. It is an invalidity example, not a
matched hyperparameter or power comparison with the nine-component mixture.

## Post-hoc field clarification and action valuation

The event field `true_current_mean` is the conditional gain on the **last
evaluated pre-return shadow pair**. It is not a certificate about the next
period's gain or deployment from the real fund state. This semantic
clarification changes none of the test inputs or decisions.

After the frozen experiment, a separately labeled descriptive audit replays
the histories of every selected first entry. It refits from available past
returns and reoptimizes the candidate from the fund's real zero allocation,
then uses the simulator's current conditional moments only for valuation.
No next-period return is drawn and no result feeds the test or signal choice.
Terminal entries remain in the file and are excluded from within-horizon
action summaries. This is not a full fund backtest or confirmatory evidence
of current-profitability inference.
