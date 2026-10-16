# Full-strategy study v1 — locally frozen before new pilot markets

This study preserves the old baseline and first-entry evidence. The new code
lives under `research/park_revive_full` so adding it does not alter either
frozen package or invalidate the first-entry module manifest.

The financial DGP, daily quadratic utility, proportional turnover and quadratic
impact, leverage, 252-day training, annual expanding fits and at most one
Forward–Backward–Swap10 move per annual revision remain the same. Six methods
share every market: All Signals, Greedy, repeated HAC, constant-bound Catoni,
the declared geometric corrected-tail mixture, and a one-period Oracle.
All selection methods start empty. Tail scales/fractions remain (2,4,8) and
(.25,.5,.75); no threshold or economic DGP parameter is retuned.

Common numerical conventions are now explicit: positive episode mean must
exceed 1e-8 daily utility, ranking ties within 1e-9 use stable signal IDs, and
QP tolerance is 1e-10. These are declared common numerical guards, not a silent
rewrite of the earlier positive-only baseline. Empty/single-coordinate
optimization uses exact algebra checked against the independent QP; larger
supports use the same constrained optimizer. Oracle weights are formed before
the next shock is drawn. No hidden data enter investible policies.
An insufficient QP iteration budget triggers refinement at the same tolerances
with a longer budget and polishing; it does not change the objective or gate.

Fresh pools: software tests 51001–51003, pilot **50001–50100**, final **60001–60500**.
The representative pilot market is fixed at 50001. Start with one measured
full-size seed, then a small batch before committing to the complete pilot.
Any final 500-seed claim requires actual execution and remains outstanding.

## Response-independent economic opportunity assessment

An opportunity starts at a positive true annual block mean and is stable only
if the same fixed-support, own-state shadow pair has a positive mean in the
following block. Inception-positive runs and later sign changes are labeled
separately. ENTRY, PARK, REVIVE and SWAP are separate lifecycle categories.

When a comparison closes, every pending positive onset is adjudicated by
continuing its unchanged counterfactual policies for one more block. The
evaluator retains early responses, including zero-delay selections. It never
feeds this continuation to the learner. Separate optimizer instances prevent
evaluator queries from changing learner warm starts. One additional evaluator-
only market year resolves onsets in the last main year; main fund returns and
decisions end at the original 15-year horizon.

Criterion detection is distinguished from being selected: a candidate can meet
its method's criterion and lose the annual ranking. Selecting another move,
withdrawing a swap or a subsequent economic sign reversal is a competing
termination, not independent administrative censoring. Stable events awaiting
a response at the main horizon are administratively censored. Within-1/3/5-year
rates use cohorts with that full calendar follow-up, uniformly for early and
late responses. Terminal certifications are recorded but are not treated as
executed fund trades.

These are descriptive portfolio-specific economic risk sets, not null labels
for validating type-I error or a causal ranking of detector quality across
different reference portfolios. Single-episode guarantees and lack of global
multiple-testing control remain explicit. Current/next-period gain is not
certified by a historical rejection. A separate deployment ledger evaluates
actual next-period weight changes from the real fund state.
