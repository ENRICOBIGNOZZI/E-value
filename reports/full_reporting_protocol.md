# Financial snapshot reporting contract — 17 October 2026

The economic source, configurations and seed pools remain the frozen v3 study.
This reporting contract changes no learner, test, optimizer, market or economic
parameter. It is specified during pilot execution, not externally registered
before the pilot. The final pool remains unexecuted at this checkpoint.

The first twenty v3 pilot markets will receive a separate **interim** snapshot,
50001–50020, after every requested market has completed independent replay.
This prefix is selected before reading its new aggregate performance table,
but after observing completion and the numerical recovery of seed 50020.
The earlier first-ten v2 manuscript snapshot remains unchanged. Their common
markets are repeated observations of the same simulated paths, not additions
to the sample size. Interim results will not determine economic retuning or
which declared pilot/final markets are included.

`scripts/seal_full_snapshot.py` requires every requested market to be complete,
with the exact frozen stage configuration and scientific source fingerprint.
Each saved source manifest must reproduce that fingerprint. Every independent
replay record must match the current verifier, source and configuration, and
the current digest of all non-checkpoint artifacts. Metrics must contain all
six methods once for the correct seed. Missing, incomplete, failed, unaudited,
stale, changed or duplicated inputs prevent publication of the snapshot.
Inputs are validated again after table/figure generation. A successful seal
records selected per-seed input digests, replay counts, reporting-source hashes
and all report-file hashes. It never overwrites an existing sealed directory.

Pilot snapshots use explicit prefixes beginning at 50001. The complete pilot
requires all **100** declared markets. Final reporting requires all **500**
markets 60001–60500; a smaller final subset is rejected. A seal verifies input
membership, provenance and arithmetic replay, not power, superiority, novelty,
global error control or the completion of the overall paper goal.

```sh
# Interim diagnostic; does not change the current manuscript.
.venv/bin/python scripts/seal_full_snapshot.py pilot --count 20
# Only after the complete pilot and its independent replays finish:
.venv/bin/python scripts/seal_full_snapshot.py pilot
# Only after the entire separate final study and its replays finish:
.venv/bin/python scripts/seal_full_snapshot.py main
```

The existing stage runner's generated aggregates remain ordinary working
reports. Manuscript promotion to a new primary financial sample must name the
corresponding sealed snapshot and update all surrounding sample/scope claims;
it must not overwrite the historical first-ten v2 provenance with v3 numbers.
