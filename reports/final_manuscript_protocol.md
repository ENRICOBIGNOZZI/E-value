# Complete-final manuscript packet

The existing `build_full_results.py` renderer describes pilot evidence. Do not
use it to relabel a final sample. The separate final packet builder consumes
the complete final snapshot and its existing verification chain. It draws no
returns, changes no frozen analysis and does not rewrite the current paper.
This preparation was made during the pilot; it is not final-study evidence.

## Required evidence

The automatic continuation already requires the complete 100-market pilot
before launching the declared final pool. After its terminal phase
`final_audited_ready_for_manuscript`, the separate event-label reconstruction
audits are still required for the complete pilot and final sample. Their
protocols are `full_event_adjudication_protocol.md` and
`full_event_reporting_protocol.md`. No positive economic result is required.

The final packet builder requires:

- A complete `main_500` seal with exactly seeds 60001--60500, unchanged source,
  stage configuration and exact whole final-analysis plan.
- All required report files, with current seal hashes, including the two figures.
- The numeric report audit and independent event reconstruction, including its
  nested event/deployment aggregation audit. Their source hashes, exact seed
  membership and seal binding must match.
- The final assessment exactly reproduced by the frozen complete-sample
  analysis; a pilot diagnostic cannot pass.
- Current independent raw replay evidence for all 500 markets. Per-market
  input digests and total replay/ghost counts must agree with the seal.

All guards apply before publication. A second complete validation runs after
formatting/copying; an evidence change removes the temporary packet. Figure
copies must match their sealed input bytes. Existing output directories are
never overwritten, and output cannot be placed inside a snapshot or raw
scientific output directory. There is no pilot mode, count argument,
performance condition or skip-validation option.

Once the complete snapshots exist, run the outstanding reconstruction audits
if their current reports do not already exist:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/audit_full_event_adjudication.py \
  --snapshot reports/full_v3_snapshots/pilot_100 \
  --output outputs/park_revive_full_v3/pilot \
  --report reports/full_v3_snapshots/pilot_100_event_adjudication_audit.json
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/audit_full_event_adjudication.py \
  --snapshot reports/full_v3_snapshots/main_500 \
  --output outputs/park_revive_full_v3/main \
  --report reports/full_v3_snapshots/main_500_event_adjudication_audit.json
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/build_final_manuscript_results.py
```

The default new destination is `reports/final_manuscript_packet/`. It contains
`generated_final_results.tex`, separately named `figures/final_strategy_*.png`
and `verification.json`. The manifest binds consumed audits, the seal, frozen
plan, builder and output bytes. Pilot and final figures cannot overwrite one
another by sharing a basename.

## Content and remaining editorial work

The packet includes all six methods' fund outcomes, all five frozen paired
contrasts with primary/secondary roles, lifecycle counts including terminal
choices, executed next-period deployment gains, and 1/3/5-year stable-event
cohorts. Empty deployment groups remain visible with undefined summaries.
Intervals use the existing frozen analysis. Secondary contrasts are unadjusted;
method-specific events do not identify causal delay comparisons, and one-day
gains are not lifetime trade values. Positive deployment gain retains the
unchanged 1e-8 daily-utility threshold. Neither sign nor statistical significance
changes the reported set of methods, comparisons or markets.

After validating the real packet, integrate it into the manuscript, update
the evidence map and the abstract/discussion using the actual complete
economic result, and preserve earlier exploratory results in their labeled
role or repository supplement. Copy the final figures under their separate
names. Compile and visually inspect the full PDF, then bind its final inputs
and page count. The current incomplete final-study text must not remain in a
manuscript claiming completed final evidence.

Software controls use synthetic reporting fixtures, including 500 identifiers
to exercise exact sample membership. Their raw replay validator is stubbed
only inside unit tests; a separate test verifies that complete-looking reports
without actual raw replay fail. Fixture results are not markets, economic
estimates, final packets or proof of rendering quality for the future study.
No production packet has been generated before the actual final evidence.
