# Fresh companion: the best constant lambda for each rejection deadline

This is a new comparison motivated after the original controlled study. It
does not replace that study or change its already observed 80,000 paths. Its
scientific code, working-model choices and numeric models will be frozen
before drawing the fresh evaluation stream.

The working law remains N(.1,1), alpha .05, common raw-second-moment bound
1.09, and common cap .5/sqrt(1.09). Every rule keeps its bet for 100 dates and
can reject only at the same 100-date reviews. Deadlines remain 400, 800 and
1600 observations. Both original primary and refinement state/action grids
are retained. No financial design, learner, moment envelope or source is changed.

For each grid and deadline, compute the probability of crossing at a review
when each available action is used as a single constant lambda. Select the
smallest maximizing grid action, using only the fixed working law. This
optimizes actual working-model review-time power rather than expected log
growth or the old lower power certificate. It is not a continuous-action or
unknown-law global optimum. Kernel truncation and the lower computational
boundary are numerical approximations, checked by the existing refinement
criterion .005. Actual fixed-arm simulation keeps the same constant until
crossing or its deadline, including below the computational lower boundary.

The predeclared new study uses seed **450001**, four independent spawned law
streams, and **20,000 paths per law** at actual means 0, .1, .2 and .3, all
with variance one. All arms share a score path within each law. Existing
original arms are evaluated unchanged, including both deadline-specific
Bellman policies. Six new constant-power arms use the primary/refined grid
choices and their own deadlines. Actual law means generate scores but are
not given to betting policies. Different deadline policies are not one policy
observed at three dates.

Primary comparison: paired horizon-DP minus best-constant crossing indicators
at mean .1, separately at each horizon and on each grid. Report individual
null crossing fractions, exact counts, pointwise Wilson intervals, paired
Monte Carlo intervals and predicted-versus-observed power. No matched actual
type-I error claim is made. Two-sided 95% Monte Carlo intervals are descriptive,
unadjusted across horizons and comparisons. The common model-calibration
criterion is .005 plus five Monte Carlo standard errors. All other laws and
all failed-to-cross outcomes remain visible. The original and companion
results are kept separate rather than pooled or substituted by performance.

Before evaluation, direct discrete software tests use small configurations
and independent seed 960001, disjoint from both scientific studies. Numerical
power-refinement failure stops evaluation. A subsequent independent audit
reconstructs every fixed/DP stake and crossing, with direct score-factor
multiplication on the declared sixteen-path prefix per law. It is not a
replay of every score path. Raw arrays, source/config/model hashes and complete
counts are retained. No favorable seed, stake, horizon or bound is selected
after evaluation. This is a scalar statistical study, not extra financial
market replications or a financial performance claim.
