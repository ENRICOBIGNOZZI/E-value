# Theory audit — 16 October 2026

Scope: theory and simulations only. The attachments are scientific reference material;
the user's instruction supersedes their legacy approval and empirical-work instructions.
The old manuscript and results have been removed from the working tree. No old result
is evidence for the new design.

## Proof audit

| Result | Required assumptions | Verified argument | Implementation / verification |
|---|---|---|---|
| T1 | Conditional mean of Y nonpositive at **every** episode date; predictable nonnegative lambda; valid conditional raw-second-moment bound | Catoni inequalities, conditional multiplier expectation at most exp(-x)(1+x), conditional Ville inequality at the stopping-time start | `eprocess.py`; phi, scaling, controlled-null and timeline tests |
| T2a | Conditional mean at least delta>0 and second moment at most constant nu² | Inverse-capital expectation at most exp[-T(lambda delta-lambda² nu²)]; Markov; maximize this quadratic at delta/(2nu²) | stationary statistical experiments; not a claim about exact most powerful testing |
| T2b | **Constant** conditional mean delta; constant nu²; annual past-only sample mean | Martingale-difference orthogonality gives MSE <=nu²/n; projection is nonexpansive; harmonic sum gives expected quadratic-certificate regret <=C_K | plug-in betting and stationary experiments |
| T2c | Assumptions of T2b | Compensated inverse-capital supermartingale, Markov separately on capital and regret; bound 1-C_K/r-exp(-A_K+r)/alpha | stationary power curves; no regime-detection theorem |
| T3 | M and Lambda PSD; gamma M+eta Lambda PD; same state b, b_j=0; no leverage constraint | L1 subgradient majorant and Schur complement upper bound, frozen incumbent lower bound | independent constrained/unconstrained optimization checks |
| T4 | Uniform error of estimated objective <=epsilon; same feasible set and known cost | Each regret in [0,2epsilon]; difference bounded by 2epsilon, not 4epsilon | controlled moment perturbations; separate shadow states and state bridge |

All four main arguments in the supplied source pass the algebraic audit within these
assumptions. The strong-concavity refinement also follows from the variational
inequality plus the gradient error bound. No novelty claim is justified by this audit.

## Material limitations to keep visible

1. T1 controls one episode, not a search over 100 signals or repeated restarts. No
   familywise or false discovery rate control is provided in this design.
2. T2b/c do not establish power or logarithmic regret in the nonstationary market.
   The regret is for the quadratic lower certificate, not realized log-capital regret.
3. A rejection can reflect old benefits; it does not certify that alpha is positive now.
4. The design allows at most 14 changes in 14 OOS years. Recovering all 45 predictive
   functions is impossible under this calendar, even with perfect tests.
5. Population support monotonicity requires the same previous weights. Shadow
   policy comparisons use different previous weights and require T4's state version.
6. The public uniform second-moment bound uses stock-level caps and may dwarf actual
   sleeve risk. Empty E-process portfolios must be reported as such, not repaired by
   substituting a sample variance or lowering the threshold after seeing results.
7. Structural theta=0 is not economic uselessness. Noise and proxies are evaluated
   separately from the conditional sign of an implemented move.
8. The one-period oracle is not a dynamic optimum or a pathwise wealth upper bound.
9. Sleeve-target turnover is stylized; costs exclude turnover inside stock sleeves.
10. No empirical application or new data acquisition is in scope.

## Explicit implementation conventions

Unspecified numerical defaults are frozen in `configs/`: gamma=5, c=1bp,
eta=1bp, Lambda=I, L=1, diagonal shrinkage=0.1, ridge=1e-8,
base coefficient=2e-4, cap=2 times group base, revive-low target=5%.
The factor risk premium is zero. Stock beta bounds are (1.5,1,1,1).
Characteristic correlation groups contain five coordinates. Coefficient innovations
are uniform on +/-1% of the group base. Design seed=74021.
These are design choices, not calibrated market estimates. No choice uses the
relative performance of the methods. Smoke dimensions change N, h and horizon only;
the full library of 100 signals and the same state/cost mechanics remain.

## Literature boundary

Primary sources checked on 16 October 2026:

- Wang and Ramdas, *Catoni-style confidence sequences for heavy-tailed mean estimation*,
  https://arxiv.org/abs/2202.01250 — source of the Catoni construction.
- Ramdas, Grünwald, Vovk and Shafer, *Game-theoretic statistics and safe anytime-valid
  inference*, https://arxiv.org/abs/2210.01948 — sequential validity background.
- Boyd et al., *Multi-Period Trading via Convex Optimization*,
  https://web.stanford.edu/~boyd/papers/cvx_portfolio.html — convex trading framework.
- Harvey, Liu and Zhu, *… and the Cross-Section of Expected Returns*,
  https://www.nber.org/papers/w20592 — multiplicity is a separate problem.

The contribution currently supported is an explicit integration and audit of
economic policy comparisons, predictable betting and state-aware selection.
A publication-level novelty claim still needs a broader literature review.

The rebuilt manuscript also gives a deterministic counterexample: annual
rejection and a positive historical score mean can coexist with a negative
current conditional gain. This establishes an interpretation limit, not a new
type-I-error failure. See `reports/design_assessment.md` for its numerical values
and the conservative sufficient-horizon calculations.

## Declared higher-moment extension

The baseline package is unchanged. `park_revive_extensions` adds a separate
research design with public function/holding geometry and analytic score
moments through order four, hence return moments through order eight.

- Public mean caps solve a support-function LP over a uniform coefficient
  cap and total budget, with no true support labels. Tests compare against an
  independent linear-program solver and verify permutation invariance.
- Loading intervals and maximum normal/stress scales bound conditional
  variance; independent Laplace cumulants supply exact evaluator moments.
  Moment envelopes are derived algebraically and tested against convolution
  formulas and an independent conditional Monte Carlo sample.
- The sharp tail inequality gives a bias correction for lower winsorization.
  Predictable nonnegative linear factors and a fixed nine-component mixture
  preserve individual-episode validity for the original utility null.
  The correction is essential; the skew-null negative control verifies that
  omitting it can make rejection almost certain under a true null.
- A two-point null gives a local information bound at a deterministic positive
  alternative. Corrected-tail betting with a predeclared design effect attains
  the corresponding local moment-order rate. This is not global minimax
  optimality, a lower bound for the fixed Laplace DGP, or an optimality claim
  for the implemented nine-component mixture.
- A single-gate costless corollary translates waiting into cumulative utility
  opportunity cost. It does not bound the uncorrected 100-candidate search or
  substitute for stateful trading-cost accounting.

The original T2b/c constant-mean, constant-bound results are not assigned to
the variable-bound extension. The first-entry experiment has no actual fund
performance or PARK/REVIVE delay claim. The legacy detection-risk-set defect
is documented in `reports/detection_audit.md`.
