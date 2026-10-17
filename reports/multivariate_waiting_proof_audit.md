# Estimated-matrix cash-PARK extension: proof and scope audit

The extension treats fixed finite dimension, iid zero-mean Gaussian returns,
a fixed positive ridge, fixed diagonal shrinkage, an L1 leverage constraint
and an expanding mean/raw-second-moment learner. Covariance may be singular
but is nonzero. There are no transaction costs, changing regimes, competing
closures, positive effect floors or growing-dimensional limit here. It changes
no frozen financial or scalar simulation and introduces no simulated paths.

## Integrated learning coefficient

With H=(1-rho)Sigma+rho*diag(Sigma)+r*I, r>0, define
chi=tr((H^-1 Sigma)^2). The Gaussian quadratic covariance identity gives an
integrated strong law by the same positive-sum subsequence argument as the
scalar proof. The inverse estimated curvature converges to H^-1 and the
constraint eventually becomes inactive. Operator-norm convergence and the
integrated law for the squared sample mean justify weighted Cesaro; no
summability rate for the covariance estimator is silently assumed.

The first-order condition along -w yields gamma*r*||w||²<=mu_hat'w, hence
||w||<=||mu_hat||/(gamma*r). Gaussian sample-mean moments then supply the
summable third/fourth target moments needed by the likelihood expansion.
Positive ridge is substantive: it avoids requiring inverse-Wishart moments
and permits n0>=1. The original scalar zero-ridge result remains separate.
The learner's chi can exceed p under shrinkage; it is not generally a rank or
a count of independent signals. For isotropic returns and no diagonal
distortion it is p*(sigma²/(sigma²+r))².

## Adaptive conditional null and support

Only the fitted-return direction is changed under Q. With v=w'Sigma*w and
a=gamma*sqrt(v)/2, that standardized direction has mean a/(1+a²) and variance
(1+a²)^-2; orthogonal directions remain centered Gaussian. The raw second
matrix is Sigma minus a positive rank-one matrix. The conditional cash
advantage is exactly zero. Gaussian directional fourth moments are bounded
using 3*(raw second)^2-2*(mean)^4, so the raw matrix/fourth-moment contracts
are preserved. Zero-risk dates use the original kernel. Singular covariance
is handled on its range, where the two kernels have the same support and
positive finite-prefix densities. The training law is identical under P and Q.

This is a single adaptive null with the same history-dependent learner,
not a null separately selected at each alpha and not a restriction to iid
null returns. Any testing upper bound requires Q-validity or a larger null
class containing Q. No optimality over an iid-null-only class is asserted.

## Information and utility limits

The one-dimensional conditional projection gives exactly the earlier scalar
log-likelihood increment. Its summable remainder and martingale proof apply
because the required moment bounds have just been established. Thus

    sum(v_t)/log(n) -> chi/gamma²,
    log(G_n)/log(n) -> chi/8,
    C_n/log(n), J_n/log(n) -> chi/(2*gamma).

The scalar change-of-measure and direct first-passage argument give the time
exponent 8/chi. The two chi factors cancel in stopped cumulative utility,
giving 4/gamma. Arbitrary level-indexed Q-valid test families have the stated
lower bound in probability. The fixed e-process rate bound and the family
bound are separate quantifiers. No stopped expectation follows from these
almost-sure/probability statements.

## Two certificate consequences

For any fixed public cap K>=Sigma, put A=Sigma^(1/2) H^-1 Sigma H^-1
Sigma^(1/2) and B=Sigma^(1/2) H^-1 K H^-1 Sigma^(1/2). Let chi_K=tr(B) and
psi=E[(Z'A Z)^2/(Z'B Z)] for standard Gaussian Z. The ratio is nonnegative,
even and square integrable. The Gaussian Hermite covariance bound, followed
by the same positive-sum subsequence argument, proves its integrated strong
law. A gradient bound and inverse-curvature convergence pass it to the actual
estimated targets; this is not an unproved interchange of directional limits.

Pointwise square completion gives the best bounded-rule rate psi/8.
The observable projected raw-moment stake approaches the directional oracle
uniformly on K's range, without knowing Sigma. The error's accumulated
square-completion loss is o(log n). The best constant instead has rate
chi²/(8*chi_K). Cauchy--Schwarz and A<=B give chi²/chi_K<=psi<=chi.
The attained utility coefficients are 4*chi/(gamma*psi) and
4*chi_K/(gamma*chi). Neither is a deadline-power optimum or a bound uniform
over level-dependent policy families.

For K=q*Sigma the rates coincide and the coefficient is 4q/gamma. For two
isotropic signals with relative caps k1,k2, the adaptive and constant
coefficients use their geometric and arithmetic means, respectively.
The (1,9) example gives 12/gamma versus 20/gamma; these are analytic
high-confidence coefficients, not observed costs. Gaussian integration gives
a one-dimensional deterministic integral for psi, checked separately from
the asymptotic proof.

For a constant certificate, the common compensator sum gamma²*v_t²/(8*d_*)
has finite expectation by the explicit Gaussian sample-mean fourth-moment
bound. The existing Ville/Markov proof gives a ceiling uniform over all
predictable bet policies, including level-dependent ones. Its displayed
positive-ridge upper bound may be enormous for small r; no informative
finite-level numeric power bound is claimed from it.

## Deterministic checking and attribution

`scripts/audit_multivariate_waiting.py` checks selected full-rank and singular
matrix identities, Gaussian density ratios against an independent multivariate
density evaluation, raw-moment inequalities, the isotropic dimension formula
and scalar quadratic bet optimizers. Those finite checks do not prove an
asymptotic statement or estimate power. Tiny negative numerical eigenvalue
gaps are reported explicitly as floating-point residuals; the positive
rank-one matrix formula supplies the analytic Loewner proof.

The retained audit contains 573 identity comparisons, 250 inequality checks
and 17 optimizer checks. The maximum absolute identity discrepancy is
1.14e-13 (scaled 2.48e-15); the minimum inequality gap is -6.67e-16.
The largest numerical optimizer-location discrepancy is 7.84e-9.
Anisotropic Gaussian-ratio integrals are compared with independent angular
quadrature in two dimensions and exact proportional/spherical formulas,
including singular examples. No parameter is fitted to those comparisons.

As an external check of the standard Hermite step, Lizhong Zheng's
[Hermite exposition](https://lizhongzheng.github.io/blog/2025/Hermite/)
was inspected on 2026-10-17, specifically its Mehler formula and multivariate
product-basis discussion. The rho-to-the-degree correlation identity is
standard. The appendix applies it to an even function and derives the
weighted law needed here; no new Hermite or Gaussian-correlation principle
is claimed.

The extension uses established Gaussian moment identities, the existing safe
linear rule and standard likelihood/martingale arguments. The claim is the
explicit estimated-matrix instance and its coefficients. No new general
e-process, quadratic strong law, matrix testing principle or exhaustive
priority claim is made. Existing scalar tests/paths and the separate complete
final financial study retain their original roles.
