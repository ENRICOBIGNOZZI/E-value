# Independent reconstruction of event labels — 17 October 2026

The preceding event-report audit verifies JSON transcription, cohort arithmetic
and internal calendars. A separate reconstruction now checks the underlying
stable/unstable labels. It changes no scientific source, allocation rule,
economic threshold, study membership or frozen final-analysis choice.

`audit_full_event_adjudication.py` first runs the existing independent report
audit and its source/replay/seal checks. It then reads every annual comparison
order, daily conditional-score array, annual comparison record, closure log and
one-block ghost continuation. It imports neither `EventTracker` nor the
simulator/selector/optimizer. Its classification is a batch calculation of
maximal positive annual runs rather than a copy of the online state machine.

For each comparison, the reconstruction:

- Averages saved daily conditional means with `math.fsum`, checks the annual
  Parquet mean and preserves the strict fixed positivity threshold.
- Requires consecutive annual observations, consistent policy metadata, one
  closing record and coherent selected/competing/administrative/shortlist causes.
- Classifies positive runs of at least two blocks as stable. A single positive
  block followed by a nonpositive block is unstable.
- Requires exactly one future ghost block when a comparison closes during an
  unconfirmed positive run. Its sign settles stability without adding a
  selection or criterion response after closure. Extra/mistimed ghosts fail.
- Reconstructs all event indices, onsets, kinds, confirmations, criterion/
  selection dates and delays, terminations and registry stable/unstable counts,
  then compares complete records and exact membership.

The first twenty sealed v3 markets reproduce **4,895 stable events and 483
unstable runs across 32,385 comparison episodes**. There are **120,630 annual
mean checks**, **2,756 ghost columns** and 38 terminal ghost means. Maximum
annual-mean discrepancy is 5.43e-20. All **118 stable events selected at their
first positive review** are retained and confirmed after closure; these are
selected choices, including terminal choices, not necessarily executed trades.
The counts are existing paths, not new market replications. The separate
raw-score arithmetic replay remains the evidence for stored conditional-mean
formulas and selector eligibility/priority; this program resimulates no DGP
and reruns no optimizer.

Twenty-seven reconstruction controls cover fast selected responses, failed
ghost confirmations, strict threshold equality, multiple positive runs,
delayed criteria, selection during a negative block, missing/spurious/mistimed
ghosts, invalid calendars, coherently omitted fast responses, wrong unstable
counts and altered annual means or policies. They pass with the 24 event-report
controls, giving 51 combined tests. All fixtures are synthetic software data.

```sh
.venv/bin/python scripts/audit_full_event_adjudication.py \
  --snapshot reports/full_v3_snapshots/pilot_020 \
  --output outputs/park_revive_full_v3/pilot \
  --report reports/full_v3_snapshots/pilot_020_event_adjudication_audit.json
# After the complete pilot is sealed:
.venv/bin/python scripts/audit_full_event_adjudication.py \
  --snapshot reports/full_v3_snapshots/pilot_100 \
  --output outputs/park_revive_full_v3/pilot \
  --report reports/full_v3_snapshots/pilot_100_event_adjudication_audit.json
# After the entire separate final study is sealed:
.venv/bin/python scripts/audit_full_event_adjudication.py \
  --snapshot reports/full_v3_snapshots/main_500 \
  --output outputs/park_revive_full_v3/main \
  --report reports/full_v3_snapshots/main_500_event_adjudication_audit.json
```

The live controller is unchanged and keeps its original automatic audit scope.
Run this additional reconstruction after each complete snapshot exists. It
includes the event-report audit, so separately repeating that same audit is
unnecessary when the reconstruction succeeds.

## Precision of retained deployment gains

The frozen engine writes annual decisions/deployments with `DataFrame.to_json`
and its default `double_precision=10`, confirmed in installed pandas 3.0.6 and
the [official documentation](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_json.html).
The final JSON concatenates those rounded records. This accounts for the
approximately 1e-10 gain/new/old identity residual without changing any value.

The reporting auditor now checks that identity against
`3 * (0.5 * 10^-10) + 4 ulps at the record scale`, replacing its looser 1e-8
economic-tolerance check. Each of three serialized fields contributes at most
half a decimal unit; ulps allow floating arithmetic. The retained first-twenty
maximum residual remains 1.01e-10, below the approximately 1.51e-10 bound.
The **1e-8 positivity threshold is unchanged**. Neither audit recomputes the
underlying evaluator conditional utilities or lifetime trade value.

Method-specific event populations do not identify causal cross-method delay
rankings or a causal decomposition of the performance gap into waiting costs.
Complete final-study evidence and overall paper completion remain outstanding.
