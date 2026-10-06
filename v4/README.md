# V4: reversible portfolio monitoring

The complete V4 research delivery is `E_value_V4_complete.zip`, supplied with the conversation: a 31-page English manuscript, all proofs in Appendix A, all experiment scripts, 6 figures, 10 generated tables, path-level outputs, JKP monthly/daily replays, and verification records. The legacy root manuscript and simulations are preserved rather than silently relabeled as the new version.

This repository update adds the exact FAST detector implementation (`fast.py`), a standalone test, the total-loss theorem and proof (`THEORY.md`), and an executed-results ledger (`RESULTS.md`). The full self-contained rerun workspace, including all retained CSVs and manuscript sources, is in the delivered ZIP. These repository files do not claim that the older root pipeline has automatically become the full V4 rerun pipeline.

## Main correction

Single-change first-order delay optimality does not establish total economic regret optimality. V4 proves an explicit finite-horizon upper bound for exogenous, bounded, fully observed shadow gains. It pays for fresh-null false switches, stale evidence after true reversals, correction delays, and switching costs. No global minimax result for arbitrary endogenous portfolios is claimed.

The FAST controller uses a 31-bet CUSUM mixture and e-detector BH. It provides patience-based monitoring, not lifetime current-state FDR. Clipped-score inference is not raw-dollar inference. The fixed grid is not asserted universally optimal.

## Executed findings

8,400 main portfolio scenario-path cases; 6,000 independent-null training paths and 20,000 disjoint null-validation paths; 24,000 single-change delay paths; 6,000 repeated-switch audits. Weak-shift, larger-book, and patience-frontier results are also retained. Several comparisons intentionally share return paths.

Matched CUSUM improves several scenarios but does not dominate SAFE. Monthly reference JKP certified policies make no changes. Daily/month-end CUSUM A=60 makes two changes and gives a small Sharpe-proxy gain; A=252 makes none in V4. No SOTA, publication, or large economic-outperformance claim is made.

Run the repository-local test with `python v4/test_fast.py`. Nothing places orders. Raw JKP data, account credentials, and font files are not included.
