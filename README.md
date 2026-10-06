# When Should I Kill—and Revive—an Alpha?

**Portfolio-aware sequential monitoring and the cost of certification.**

V4 research status, 6 October 2026.

## Core idea

A strategy is monitored by its conditional marginal contribution to portfolio utility, not its standalone mean return. Capital can move reversibly between **ACTIVE** and **PARKED** states; parked strategies continue in shadow mode and may later be revived.

Two policies are kept distinct:

- **SAFE:** lifetime-valid certification benchmark; intentionally conservative.
- **FAST:** 31-component bounded-mean mixture e-CUSUM + e-d-BH, using finite-patience / error-over-patience control.

The statistical primitives are attributed to the modern e-detector literature. The finance contribution is the portfolio-relative target, reversible lifecycle decision, economic indifference region, and the mapping from information-theoretic detection delay into unavoidable portfolio regret.

## V4 theory

The manuscript establishes or applies:

1. exact portfolio-value characterization under quadratic utility;
2. e-CUSUM validity under a global-filtration conditional-mean null;
3. multi-alpha EOP control via e-d-BH;
4. a finite-sample bounded-mean delay bound;
5. sharp first-order single-stream information limits from existing quickest-detection theory;
6. first-order **economic delay-regret** optimality;
7. repeated PARK/REVIVE true-change regret decomposition;
8. a cost-weighted economic-error-over-patience extension.

All proofs are placed in the manuscript appendix. The complete V4 source and research outputs are kept in the current research deliverable; the repository will retain reproducible scripts rather than raw licensed JKP archives.

## Simulation result

The final suite uses 150 common-random-number replications × 900 observations for six economic scenarios under Gaussian, Student-t, GARCH, and AR noise.

FAST is materially faster than SAFE at a finite-patience operating point, preserves the negative-return hedge, and reacts to death/revival and covariance-only state changes. It does **not** uniformly dominate rolling or HMM heuristics, which do not provide the same sequential guarantee.

A matched-strictness experiment is intentionally retained. When FAST is calibrated to approximately SAFE's very low false-switch frequency, the advantage becomes modest and is not uniform. The main operational gain therefore comes from using a finite-patience error criterion appropriate for capital allocation, not from a free statistical improvement.

## Information experiment

A least-favourable Bernoulli bounded-mean experiment uses 3,000 paths per design point. Observed delay divided by `log(A)/KL` moves toward one as patience grows, consistent with the first-order information frontier.

## JKP validation

The public validation uses 153 official U.S. daily value-weighted JKP factors, a 252-trading-day pre-2000 burn-in, daily evidence updates, and month-end allocation decisions through 2025.

This is a retrospective factor-library validation, **not** a historical-publication-date point-in-time backtest. The factor-only results show only modest descriptive improvement for some pre-specified patience values; post-PARK event evidence is mixed and moderate-patience runs contain little revival evidence. No profitability claim is made.

## Reproducibility

The V4 build passes **27 unit tests**. Raw JKP data are not committed. Generated performance claims must be traceable to path-level results and manifests; no synthetic empirical fallback is allowed.
