# Independent event/deployment reporting audit — 17 October 2026

This extends reporting verification during pilot execution. It changes no
scientific source, market, policy, parameter, seed, economic metric, analysis
contrast or final-sample rule. It does not alter the frozen final-analysis
plan or the running continuation controller.

The original `audit_full_snapshot.py` recalculates market metrics, paired
contrasts and incidence intervals. It hash-checks the event/deployment tables
but does not independently recompute their aggregation. The separate
`audit_full_event_snapshot.py` closes that reporting gap using standard-library
JSON, CSV and counters, without importing the simulator, selector, optimizer
or dataframe reporting builder.

For every member of an existing sealed snapshot, it checks complete status,
source/configuration identities and byte-current replay evidence. It binds
the raw data to the seal before and after the audit. The following are then
checked independently:

- Every field and exact row membership of opportunity, registry, decision and
  executed-deployment tables, including the compressed detail CSVs.
- Stable-event calendar and delay-field consistency, registry/status counts,
  selected-event/decision links and one choice per method per annual review.
- All 180 method/lifecycle/event-kind/follow-up cohort keys, the 1/3/5-year
  calendar eligibility denominators, selection/criterion numerators, fractions
  and contributing-market counts, and every market-specific count row.
- Executed versus terminal choices, policy metadata and four per-market
  decision/deployment metrics. Empty denominators remain undefined.

Fast responses remain eligible after their shadow continuation confirms
stability. A terminal choice can count as a selection within an eligible
calendar window, but never as an executed deployment. The audit does not
re-run stable-event adjudication from the full return history or recompute
evaluator conditional utilities/optimal allocations. The retained gain/new/old
utility identity is now checked at a ten-decimal serialization bound, not the
economic positivity tolerance or machine precision. Thus verification of
transcription and aggregation is distinct from
verification of those underlying scientific calculations.

The first-twenty audit covers 4,895 stable-event rows, 32,385 comparison-registry
rows, 212 decisions and 208 executed deployments. It makes 264,406 numeric
copy/aggregation checks with maximum discrepancy zero and 459,239 structural
checks. The maximum retained gain-field identity residual is 1.01e-10, below
the approximately 1.51e-10 serialization bound. These counts are not additional markets,
score replays, statistical sample sizes or evidence of economic superiority.

Twenty-four software controls use small synthetic fixtures, including prompt
responses, terminal choices, empty cohorts, wrong re-sealed denominators,
missing/duplicated report rows, stale raw data, malformed bound metadata and
an input added during the audit. The CLI refuses to write an audit report
inside either immutable input tree. Fixtures are never scientific observations.
Two precision controls verify the installed serializer default and reject a
gain residual that would have passed the former economic-tolerance check.

```sh
.venv/bin/python scripts/audit_full_event_snapshot.py \
  --snapshot reports/full_v3_snapshots/pilot_020 \
  --output outputs/park_revive_full_v3/pilot \
  --report reports/full_v3_snapshots/pilot_020_event_numeric_audit.json
```

The existing live controller is left unchanged. Its automatic audits still
have their original scope. After the complete pilot/final snapshots are
sealed, run this additional audit separately before using their event or
deployment tables in the manuscript:

```sh
# Only once pilot_100 exists with every requested market complete/replayed.
.venv/bin/python scripts/audit_full_event_snapshot.py \
  --snapshot reports/full_v3_snapshots/pilot_100 \
  --output outputs/park_revive_full_v3/pilot \
  --report reports/full_v3_snapshots/pilot_100_event_numeric_audit.json
# Only once the entire separate final study is sealed as main_500.
.venv/bin/python scripts/audit_full_event_snapshot.py \
  --snapshot reports/full_v3_snapshots/main_500 \
  --output outputs/park_revive_full_v3/main \
  --report reports/full_v3_snapshots/main_500_event_numeric_audit.json
```

Event populations remain method-specific. Audited event fractions do not
identify causal cross-method delay rankings or decompose the utility gap into
a causal cost of waiting. Deployment gains concern the next period after
transition costs, not lifetime trade value. No result in this reporting audit
completes the still-running pilot/final study or the overall paper goal.

The later `full_event_adjudication_protocol.md` documents a separate batch
reconstruction of the stable/unstable labels from annual score arrays and
ghost continuations. It includes this report audit and has additional controls;
the scope limitation above continues to describe this standalone reporting
auditor, not the later reconstruction.
