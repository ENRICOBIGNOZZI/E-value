# Portfolio learning, utility loss and logarithmic averaging

17 October 2026. Targeted attribution review; no new theorem, estimate,
algorithm or simulation. It does not establish exhaustive priority.

| Primary source and inspected material | What it supports here | Boundary |
|---|---|---|
| [Kan and Zhou (2007), publisher abstract and publication record](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/optimal-portfolio-choice-with-parameter-uncertainty/A0E9F31F3B3E0873109AD8B2C8563393) | Analytical expected portfolio-utility loss from estimating return means and covariance is an established topic | Full derivations were not available at the inspected publisher page; no particular numbered formula is attributed from it. The old author-PDF URL returned 404. Print publication is 2007, despite the publisher's 2009 online date. |
| [Kato (2026), arXiv v1, 1 October](https://arxiv.org/html/2610.02290v1) | Sections 2.1–2.3, 7.1, Proposition 7.1, Theorem 7.2 and equations (75)–(84): static expected regret, a local near-cash allocation expansion and leading minimax/Bayes constants | Its cited local result uses a bounded exponential-family baseline, positive definite covariance, smooth increasing concave utility and shrinking mean neighborhoods. It is not directly a theorem for our unbounded Gaussian quadratic score, positive-ridge learner or evidence-constrained stopping time. |
| [Chaâbane (2002), publisher abstract and introduction extract](https://www.sciencedirect.com/science/article/abs/pii/S0167715202002079) | Logarithmic averaging and Gaussian/martingale strong laws have classical formulations; the introduction describes the Ornstein–Uhlenbeck transformation of Brownian motion | The displayed introductory argument is an antecedent for the clock, not an unchecked application of its full martingale hypotheses to our unbounded matrix ratio. We retain the direct covariance/Hermite proof. |

## The objectives are different

Our costless Gaussian instance fixes an estimated reference. It does not
optimize a portfolio rule over all allocation procedures. The conditional
cash advantage is the same quadratic utility loss that a zero-mean risky
allocation incurs, so interpreting estimation in utility units is not new.
At zero population mean the mean–variance and raw-second-moment population
objectives coincide; that equality does not hold generally away from zero.

As a direct elementary comparison, consider a separate unconstrained learner
with fixed symmetric positive definite curvature H and mean estimate from m iid
zero-mean observations with covariance Sigma:

    u_m = H^-1 * mu_hat_m / gamma,
    E[gamma*u_m' Sigma u_m/2]
        = tr(H^-1 Sigma H^-1 Sigma)/(2*gamma*m).

The Gaussian assumption is unnecessary for this expectation identity.
If H=Sigma and Sigma is nonsingular, the coefficient is p/(2*gamma).
Summing over fixed deterministic dates gives a logarithmic expected cumulative
loss. This calculation is our algebraic comparison, not an attributed
uninspected formula, a statement for the actual constrained estimated-H
learner, a zero-ridge limit of Theorem 20 or an expected stopped-cost theorem.

The paper's additional question is how long a valid sequential comparison
must wait while that reference evolves. Its adaptive null, logarithmic
likelihood scale and first-passage normalization give the coefficient
4/gamma per log(1/alpha). The probability-family lower bound fixes the
comparison experiment and learner. It is not a minimax allocation-regret
claim, an expected stopped-loss limit or a causal decomposition of the
financial methods' utility differences.

## What the logarithmic law needs

A weak almost-sure limit for logarithmically weighted empirical measures
does not automatically imply a limit for an unbounded function. Our
quadratic form and matrix ratio are unbounded. The appendix verifies their
Gaussian covariance/Hermite bounds, obtains O(log n) variance for the weighted
sum, and uses a positive-sum subsequence argument. That supplies the needed
moment law directly; no unproved uniform-integrability step is imported from
an almost-sure central limit theorem.

The same distinction prevents transferring static expected-regret limits to
random stopping times. The current paper asserts pathwise limits and lower
bounds in probability; it has not established the tail/uniform-integrability
conditions for expected stopped-cost equivalence.

The manuscript adds these three antecedents and distinguishes the relevant
objectives. It claims neither a new concept of portfolio estimation loss nor
a new general logarithmic averaging principle. This review changes no frozen
sources, scientific configuration, analysis plan, endpoint, comparator or
seed membership. The completed final study and broader novelty assessment
remain outstanding.
