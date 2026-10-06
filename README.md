# When Should I Kill—and Revive—an Alpha?

**Portfolio-aware sequential evidence and the cost of certification.**
Research implementation, manuscript, and executed results. All proofs are in the manuscript appendix. Empirical data are **JKP only**. Nothing places orders or manages real money.

## Actual status — October 6, 2026

- Full English manuscript in `paper/main.tex`, with all mathematical proofs in Appendix A.
- **9,420 scenario-path evaluations** across main, null, dependence, scaling, weak-signal, and delay studies. Some designs share common random numbers; this is not a count of mutually independent worlds.
- Eight transparent policies in the main Monte Carlo and JKP replay.
- Real official **153-factor USA monthly JKP replay, January 2000–December 2025 (312 months)**; 1995–1999 burn-in. Three cost specifications and explicitly exploratory factor-only / 13-theme architecture checks.
- Unit tests, path-level simulation results, source hashes, paired uncertainty estimates, and generated paper tables/figures.

## The results are mixed, not a SOTA claim

The portfolio score preserves a negative-return hedge that standalone screening removes. Retirement plus revival improves on permanent retirement after strong mean recovery. But the certified rule reacts too slowly in the correlation-only revival experiment and **underperforms always on** there. In the primary JKP replay, **all certified policies make zero switches** and exactly reproduce always on. This is an identified power limitation, not a missing result.

The recorded false-alarm rates are 7/2,000 (0.35%) and 4/2,000 (0.20%) for the two bounded-score null designs, under a 5% lifetime upper bound. Very low size is not evidence of good trading decisions.

## Reproduce

Requires Python >=3.10 and NumPy, pandas, SciPy, matplotlib, pytest. Install from the project directory:

```bash
python -m pip install -e '.[test]'
python -m pytest -q
python experiments/reproduce.py --download --pdf
```

`--download` retrieves official JKP archives with TLS verification. `--pdf` requires `pdflatex` and standard packages: amsmath, amssymb, amsthm, mathtools, booktabs, graphicx, natbib, enumitem, hyperref, microtype, fancyhdr, and geometry. Omit `--pdf` to run all empirical/simulation experiments without TeX.

Original JKP source hashes are recorded in `data/source_manifest_20261006.json`. The public provider can revise files; a new download is not guaranteed to reproduce the exact archived vintage. Raw licensed data are not tracked in Git. There is no synthetic fallback if the empirical download fails.

Individual commands:

```bash
python experiments/run.py --name main --reps 200 --periods 1800 --noises gaussian,student
python experiments/run.py --task null --name null --reps 2000 --periods 720 --m 5
python experiments/delay.py
python experiments/empirical.py
python experiments/empirical_diagnostics.py
python experiments/report.py
```

A small smoke test is `python experiments/run.py --name smoke --reps 5 --periods 240 --scenarios revival --noises gaussian --methods always_on,e_restart`.

## What the method certifies

Before observing a return vector, specify paired fixed-slot books with and without candidate j. Parked capital goes to cash; survivors are **not renormalized**. Compute quadratic-utility difference D, normalize by a burn-in scale, and clip to [-1,1]. Two directional betting rules support PARK and REVIVE with hysteresis. Restart mixtures keep unstarted capital, safely discard expired wealth, and spend delta/[M*k*(k+1)] in episode k. At most one strategy changes state per book per period, effective next period.

The guarantee concerns any false alarm **before an episode's directional conditional-mean null has ever failed**. It does **not** guarantee that every switch matches the current economic state after arbitrary reversals. The certified target is the conditional mean of the **clipped utility difference**, not an unrestricted expected return. No independence is needed once the conditional moment null is assumed; arbitrary financial dependence does not automatically satisfy that assumption.

Optional assets cannot lower population-optimal utility if zero weight remains feasible. Negative contribution here means negative value of a **specified allocation**, not negative value of access to an asset. Switching charges are evaluated in realized returns; the hysteresis rule is not a solved optimal-switching problem.

## Experiments and limitations

`results/*/replications.csv` holds method/path-level records. `summary.csv` holds paired Monte Carlo means and standard errors; `first_path.csv` fixes the illustrative path to replication zero rather than selecting a favorable trajectory. Manifests identify seeds, dimensions, assumptions, and execution. Binary generated plots and the built PDF are distributed with the research bundle or regenerated locally.

The JKP replay is past-only in its observation and trading clock, but the library and data vintage are retrospective. This is **not a historical-publication-date point-in-time backtest**. Costs are stated deductions, not estimates of underlying stock turnover, impact, or borrow fees. All 153 factors qualify using only the 60-month pre-launch history; missing post-launch returns cause an error, not hindsight deletion.

CUSUM/HMM/rolling comparators are fixed transparent heuristics, not error-rate-matched SOTA implementations. The one-alpha oracle is a **one-period conditional opportunity-loss diagnostic**, not global optimal-switching regret. Null calibration and raw-utility state adaptation are evaluated separately. The paper makes no minimax claim for the reversible financial policy.

## Data attribution and access

Jensen, T. I., Kelly, B., and Pedersen, L. H. (2023), *Is There a Replication Crisis in Finance?*, Journal of Finance 78(5), 2465–2518, DOI 10.1111/jofi.13249. Official portal: https://jkpfactors.com/data.

JKP data are provided under **CC BY-NC 4.0**, not a blanket license for hedge-fund commercial use. Raw archives stay outside Git. Data-derived experimental outputs are research outputs subject to the source's terms. No credentials, portfolio holdings, or user-local datasets are included.
