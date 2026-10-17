# Closest prior work and scope of the contribution

Primary sources consulted in this continuation:

- Henzi and Ziegel, *Valid sequential inference on probability forecast performance*,
  https://arxiv.org/abs/2103.08402 and published correction
  https://doi.org/10.1093/biomet/asac043. Sequential comparison of competing
  forecast scores using e-values already exists; this is not a new general idea.
- Choe and Ramdas, *Comparing Sequential Forecasters*,
  https://arxiv.org/abs/2110.00115. This includes time-varying average score
  comparisons and weak-null formulations. The baseline T1 only proves its
  datewise conditional null, so its guarantee must not be advertised as
  weak-null average-performance control.
- Waudby-Smith and Ramdas, *Estimating means of bounded random variables by betting*,
  https://arxiv.org/abs/2010.09686. Predictable linear betting and mixtures are
  established tools. The new section specializes these using a lower-tail bias
  correction, without claiming to invent the general construction.
- Lugosi and Mendelson, *Mean estimation and regression under heavy-tailed
  distributions—a survey*, https://arxiv.org/abs/1906.04280. Moment-based
  inference and rare-event lower-bound techniques have a substantial existing
  literature. The two-point local information bound in this manuscript is
  presented with its proof and scope, not as an unqualified novel minimax result.

All sleeve outcomes are observed on the common market path. The problem is
full-information comparison of adaptive investment policies with stateful
costs; it does not require the importance-weighting machinery used when rewards
for unchosen actions are missing. This distinction matters when selecting
related work and benchmarks.

Additional close primary sources checked for the full-strategy continuation:

- DeMiguel, Martín-Utrera, Nogales and Uppal (2020),
  [A Transaction-Cost Perspective on the Multitude of Firm Characteristics](https://doi.org/10.1093/rfs/hhz085).
  Evaluating characteristics jointly through portfolio risk, trading costs and
  out-of-sample performance predates this paper. The earlier author manuscript
  also discusses a characteristic with a hedging role despite negligible own
  mean return. Their stock-trade netting mechanism is outside our simplified
  sleeve-target turnover model. The economic framing alone is not a novelty claim.
- Carrasco and Koné (2024),
  [Test for Trading Costs Effect in a Portfolio Selection Problem with Recursive Utility](https://doi.org/10.1093/jjfinec/nbad015),
  with [author working paper](https://enavantmath.org/files/publications/2023s-03.pdf).
  GMM inference for transaction-cost effects and economic portfolio assessment
  already exist. Our conditional sequential policy-pair null differs from their
  structural parameter/boundary inference problem.
- Wang, Wang and Ziegel (2026),
  [E-backtesting](https://doi.org/10.1287/mnsc.2023.01659),
  [author version](https://arxiv.org/abs/2209.00991).
  Financial applications of e-processes, including VaR/ES risk forecasts,
  already exist. No first-use-in-finance claim is defensible here.
- Jiao, Wang and Zhao,
  [Comparative e-backtests for general risk measures](https://arxiv.org/abs/2511.05840),
  revised March 2026. Anytime-valid comparative risk-forecast evaluation is a
  close antecedent. Our implementable utility scores include separate allocation
  states and turnover; that specialization needs to carry the contribution.
- Waudby-Smith, Sandoval and Jordan,
  [Instance-Log-Optimality of Portfolio-Based E-Processes and their Sequential Hypothesis Tests](https://arxiv.org/abs/2504.02818),
  revised September 2026. General regret-to-log-optimality and rejection-time
  results are substantially stronger than our T2 growth-certificate argument.
  Their portfolios allocate statistical betting capital. Our investible
  portfolios generate the scores being tested. We claim neither a new general
  regret principle nor instance optimality/minimaxity of the proposed fund.

Additional sources for the lambda and nested-model sections:

- Chatterjee, Cinquemani and Lygeros, [author version](https://arxiv.org/html/0904.4143):
  finite-horizon target-reaching probabilities and their Bellman recursion are
  standard control tools. The manuscript applies that objective to predictable
  Catoni bets; it does not claim to invent dynamic programming or global power
  optimization under an unknown law.
- Clark and McCracken, [author version](https://www.kansascityfed.org/documents/5266/pdf-rwp99-11.pdf),
  and Clark and West, [author version](https://www.kansascityfed.org/documents/5368/pdf-RWP05-05.pdf):
  nested-model forecast tests and estimation-noise adjustments precede this
  work. Our implemented-policy utility comparison retains that estimation loss
  rather than adjusting it away to infer population predictive content.

The contribution currently under assessment combines explicit economic/state
accounting, public policy-geometry moment envelopes and the corrected-tail
implementation with two analytic specializations: the directional ENTRY frontier
and the estimated-reference cash-PARK waiting example. Their proofs specialize
established testing principles. The individual examples and their economic
interpretation need to carry the contribution; the underlying construction
tools cannot. Complete final evidence and broader prior-art validation remain
necessary for a strong publication or priority claim.

Further primary sources checked for integration of the cash-PARK example:

- Arnold, Gavrilopoulos, Schulz and Ziegel,
  [Sequential model confidence sets](https://arxiv.org/html/2404.18678),
  author version v4, January 2026, published DOI
  [10.1093/jrsssb/qkag066](https://doi.org/10.1093/jrsssb/qkag066).
  Simultaneous time-uniform inference for superior forecasters is established.
  The reported financial strategy does not implement that coverage guarantee.
- Frazier and Poskitt,
  [Sequential Scoring Rule Evaluation for Forecast Method Selection](https://arxiv.org/html/2505.09090v1).
  Sequential comparisons of estimated forecast methods via exponentiated scores
  and change of measure are close prior work. Their conditional-factor and
  moment assumptions must not be identified with our raw-score mean null.
- Grünwald and de Rooij,
  [Asymptotic Log-loss of Prequential Maximum Likelihood Codes](https://arxiv.org/abs/cs/0502004).
  Logarithmic estimation losses of plug-in sequential predictors are known.
  The cash-PARK example retains that policy loss in its utility target and
  specializes standard likelihood comparison to an adaptive boundary null;
  it does not introduce logarithmic prequential regret as a general principle.

For the directional moment section, primary-source review also includes
[Bertanha and Moreira](https://arxiv.org/html/1612.02024), whose null-density
framework covers classical contamination/trivial-power arguments, and
[Fan, Jiao and Wang](https://sas.uwaterloo.ca/~wang/papers/2024Fan-Jiao-Wang-Biom.pdf),
who study existing conditional mean/variance e-processes. The manuscript
specializes these principles to quadratic-utility direction and an explicit
second-return-moment frontier. It gives the contamination, sufficiency and
above-two-moment proofs in full; no new general impossibility, mixture or
mean-testing principle is claimed. The fixed Laplace financial law is not the
entire iid moment class appearing in that theorem.

`directional_prior_art_audit.md` records a more specific hypothesis comparison
and the finite-prefix total-variation argument. The bibliography now uses the
published 2025 Fan--Jiao--Wang record while retaining the inspected 2024 author
preprint. This targeted mapping is not an exhaustive priority review.

Direct antecedents for the horizon-betting section were subsequently checked:

- [Taga, Oymak and Shekhar (ICML 2026)](https://proceedings.mlr.press/v306/taga26a.html)
  already use time/evidence state and finite-horizon control for bounded means.
  Their paper also studies learned betting policies.
- [Clerico, Wegel, Azangulov and Rebeschini (2026)](https://arxiv.org/html/2605.06521)
  formulate rejection-time rewards, their Bellman representation and the
  hard-deadline simple-vs-simple Neyman--Pearson connection.
- [Baas, ter Schure and van Rosmalen (2026)](https://arxiv.org/html/2605.28653)
  develop power/expected-sample-size optimal binary clinical-trial designs
  through dynamic programming.

These are direct statistical antecedents, beyond the generic reachability
reference. The manuscript now explicitly describes its horizon-power recursion
as a blockwise Catoni specialization and disclaims a comparison against their
learned or binary-design policies. Its existing fixed/optimized-constant
benchmarks do not establish a state-of-the-art power ranking. See
`horizon_prior_art_audit.md` for the exact scope mapping.

The cash-PARK section now also cites existing predictable heteroscedastic Catoni
certificates and an iid Catoni confidence-sequence width lower bound. The
statement-by-statement comparison is in `cash_park_prior_art_audit.md`. It
separates our explicit adaptive estimated-policy instance from general
supermartingale, width and numeraire results without declaring a new general
principle or an established priority claim.
