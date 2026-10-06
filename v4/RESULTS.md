# Executed V4 results

## Independent null matching

One stream, 720 observations. Training: 3000 paths per null; validation: 10000 different paths per null. CUSUM threshold 925.0386845621259; SR threshold 12150.636621635254. Validation first alarms:

| Null | SAFE | Matched CUSUM | Matched SR |
|---|---:|---:|---:|
| iid bounded score | 48/10000 | 40/10000 | 38/10000 |
| Predictable volatility | 28/10000 | 19/10000 | 31/10000 |

At common nominal A=252, iid first-alarm probabilities are 1.72% for CUSUM versus 98.51% for SR. A common ARL lower bound is not a common finite-horizon size.

## Main Gaussian portfolio cases

Conditional utility gain per observation over Always On, multiplied by 10000; 300 common-return paths per cell:

| Scenario | SAFE | CUSUM matched | CUSUM 252 |
|---|---:|---:|---:|
| Permanent death | 73.79 | 76.31 | 77.33 |
| Mean revival | 24.07 | 29.50 | 31.66 |
| Negative-return hedge | 0 | 0 | 0 |
| Positive redundant | 65.19 | 61.14 | 63.62 |
| Correlation revival | -6.83 | -3.53 | 0.60 |
| Gradual | -0.39 | 1.47 | 3.73 |
| Repeated | 3.10 | 4.38 | 5.07 |

Thus the new matched detector does not dominate. Re-entry helps strong mean recovery but can hurt in short repeating regimes. Strong mechanism shifts are not estimates of achievable financial alpha.

## Theory audits

24000 canonical single-change stopping paths, no censoring; 6000 repeated-switch paths. In the bounded-gain experiment with M=1, gap=.4, A=252, T=2400, observed total loss is 56.28, proved upper 612.21, trivial upper 984. The upper bound is conservative and is vacuous in some weak-gap cells. It is not a sharp total-regret theorem.

## Actual JKP

153 USA capped-value factors. Admission from complete 1995-1999 monthly history; evaluation 2000-2025. 312 monthly and 6539 daily test observations. The library and source vintage are retrospective; the same history was inspected in prior versions. No untouched point-in-time backtest is claimed.

Monthly reference certified policies make zero switches, including CUSUM A=12. Daily factor-only/month-end results:

| Policy | Sharpe proxy | Annual utility | Implemented switches |
|---|---:|---:|---:|
| Always On | .470665 | .012175 | 0 |
| CUSUM 60 | .475449 | .012270 | 2 |
| CUSUM 252 | .470665 | .012175 | 0 |
| SR 252 | .494651 | .012219 | 706 |

Gains are small and exploratory. The SR comparison is not matched on actual error. Assumed fee deductions are not stock-level execution-cost estimates. Full path-level CSVs, paired standard errors and bootstrap intervals, hashes, all scripts, and manuscript exhibits are in the delivered V4 ZIP. Raw licensed JKP archives are excluded.
