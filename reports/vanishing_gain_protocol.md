# Frozen controlled diagnostic: vanishing cash-PARK gains

This is a new scalar statistical experiment, **not** another financial market
replication, another primary investment method, or a modification of the frozen
full-strategy design. The associated proof audit is `vanishing_gain_proof_audit.md`.
The working research note remains excluded from the manuscript.

Before generating the declared stream, freeze `configs/vanishing_gain.json` and
`scripts/vanishing_gain_study.py` in Git. Scientific seed **430001** has not been
used for development. Two independent `SeedSequence.spawn` children generate
the two laws; all four evidence rules within a law receive identical scores.
Software checks use a separate seed, 940001. Retain every replication.

There are **4,096 paths per law**, 32 initial observations, and **65,536**
evaluated dates. Set gamma=sigma=1, leverage=.5, costs=0, ridge=0. At each date,
before drawing its return, the reference target is the clipped historical mean
divided by gamma times the historical **raw** second moment. The candidate is
cash. The score is `Y=-w*A+gamma*w*w*A*A/2`. The conditional null is datewise
nonpositive mean score. No minimum-effect floor, competing comparison closure,
shortlist or search across signals is applied.

Laws:

- Alternative: iid N(0,1), including initial training. Its score mean is w²/2.
- Conditional boundary null: training has the same iid N(0,1) law. Subsequently
  set a=w/2, mean=a/(1+a²), sd=1/(1+a²), using the pre-return target. Its
  conditional score mean is zero, raw second moment is at most one and raw
  fourth moment at most three. Positive-mean iid noisy returns would **not**
  generally be a datewise null for an estimated target with random sign.

Evidence rules:

1. Standard linear betting specialized to cash-PARK: product(1+Y/2). Quadratic
   utility gives Y>=-.5, so every factor is at least .75. No certified fourth
   moment is needed by this rule.
2. Catoni with fixed lambda=.5 and the predictable geometry certificate
   `w²*(sqrt(M2)+gamma*abs(w)*sqrt(M4)/2)²`.
3. The same fixed lambda and the uniform certificate obtained by replacing
   abs(w) with leverage in that formula.
4. Uniform Catoni with the original past-positive-mean plug-in bet, revised
   every 252 evaluated dates, initial gain=.0001, cap=1/(2*sqrt(nu²)).

Both Catoni certificates use the common public contract M2=1, M4=6; sample
moments are **not** substituted into a certificate. Fixed-lambda methods are
predeclared diagnostic variants, not the variable-bet financial implementation.
The linear and fixed Catoni variants can have a weak cumulative-null
interpretation, but calibration here uses the common stronger datewise null.

Report all-date first crossings at alpha .05, .01, .001, and separately the
first crossings at 252-date reviews. Administrative noncrossing is retained.
Use path-level Wilson intervals; do not condition delay comparisons on success.
Record mean log capital and its Monte Carlo SE, integrated squared targets,
cumulative conditional benefit, realized score sum, and Gaussian P/Q log ratio
at fixed powers of two, annual reviews and the final horizon. Store per-path
checkpoint arrays and source/configuration hashes. The P/Q ratio is evaluator
output and never affects a target or bet.

The asymptotic predictions are a 1/8 log-capital slope in log time for linear
and geometric fixed betting, finite almost-sure terminal capital for uniform
past-mean betting, and negative linear-in-time log growth for uniform fixed
betting. Finite-horizon plots need not approach those limits closely and need
not show high crossing power. No horizon, threshold, seed, risk bound or bet
will be adjusted after observing these paths. This diagnostic neither proves
the asymptotic theorem nor estimates an expected rejection-time equivalence.
