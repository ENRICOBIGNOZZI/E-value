# Executed results — 6 October 2026

This is a first complete research implementation, not a SOTA or publication-ready claim. The complete downloadable research bundle contains all path-level CSVs, generated figures/tables and compiled manuscript. The `Reproduce alpha lifecycle research` workflow reruns the experiments and retains them as a GitHub Actions artifact. Raw JKP files are never committed.

## Execution ledger

| Suite | Scenario-path evaluations | Periods |
|---|---:|---:|
| Main: 7 designs × Gaussian/Student-t × 200 paths | 2,800 | 1,800 |
| Two known bounded-score nulls | 4,000 | 720 |
| GARCH and AR stress tests | 800 | 1,200 |
| M=20,50,100,150 scaling diagnostics | 120 | 900 |
| Weak correlation shifts | 200 | 720 |
| Separate state-adaptation study | 1,500 | 1,800 |

Total: 9,420 scenario-path evaluations. This does not imply mutually independent samples across suites. Fifteen unit tests pass locally.

## Selected Gaussian results

Mean paired utility gain over always on, multiplied by 10,000; Monte Carlo standard error in parentheses. Each cell uses 200 common-return-path replications. Heuristic comparators are not matched to the certified lifetime error objective.

| Scenario | Standalone rolling | Portfolio rolling | Retire only | Retire + revive |
|---|---:|---:|---:|---:|
| Permanent death | 79.04 (0.27) | 79.39 (0.28) | 75.09 (0.30) | 75.09 (0.30) |
| Mean revival | 37.17 (0.20) | 37.32 (0.20) | 14.97 (0.28) | 27.88 (0.24) |
| Negative-return hedge | -27.20 (0.21) | -6.35 (0.15) | 0.00 (0.00) | 0.00 (0.00) |
| Positive redundant | 21.79 (0.48) | 70.54 (0.32) | 68.13 (0.38) | 68.13 (0.38) |
| Correlation revival | -5.24 (0.37) | 20.65 (0.24) | -8.45 (0.43) | -3.38 (0.41) |

The certified rule preserves the negative-return hedge and benefits from revival after strong mean recovery. It is too slow in the correlation-revival design and underperforms always on. Its average capped retirement delay is about 329 observations; reactivation delay about 412, with a 600-observation regime horizon.

## Null calibration

For five strategies monitored for 720 periods, the certified rule switches on 7/2,000 independent bounded-score paths (0.35%) and 4/2,000 predictable-volatility paths (0.20%). The lifetime upper bound is 5%. This is not a statement that 95% of economic decisions are correct. The theorem concerns alarms before an episode's directional conditional-mean null first fails.

## Real JKP replay

Official USA monthly capped-value data. January 1995–December 1999 burn-in; January 2000–December 2025 evaluation. All 153 factors qualify using only burn-in availability. The evaluation has 312 months. Returns are decimal and already signed as supplied.

All certified policies make **zero switches**, under the reference, zero-cost, and higher-cost specifications. The reference market-anchored always-on Sharpe proxy is 0.475, mean 6.59% and volatility 13.88% annualized. These are not incremental algorithm returns. Descriptive paired-block intervals for heuristic utility differences include zero.

Exploratory factor-only and 13-theme architectures, added after seeing the main zero-switch result, also produce no certified switches. No certified revival event study is fabricated.

The contemporary library and data vintage are retrospective. This is a past-only historical replay, not a publication/vintage point-in-time investment backtest. Cost deductions are explicit sensitivity assumptions, not stock-level execution estimates.
