# Equality of completed v2/v3 financial paths

The v3 correction changes numerical recovery of the same optimization problem.
This audit checks its actual retained outputs across the entire completed
common v2/v3 pool, rather than relying solely on the representative market.
It runs read-only alongside the independent arithmetic replay.

- **Nineteen complete markets**, seeds 50001–50019: **3,495 data-file pairs**
  agree byte for byte across all fourteen OOS blocks and root aggregates.
- The v2 failure at seed 50020 has only three sealed blocks. Those blocks and
  its feature library add **39 identical file pairs**. Its v3 continuation
  after that prefix has no completed v2 counterpart and is not declared equal.
- Total: **269 sealed block pairs**, **3,534 artifact-file pairs**, and
  **477,416,821 equal artifact bytes per version**.
- Every parsed configuration field agrees except the explicit version label:
  `full-strategy-v2-pilot` versus `full-strategy-v3-pilot`.

The compared data include actual weights, gross/net returns, costs, utilities,
wealth, solver residual fields in the fund ledgers, saved daily comparison
arrays, annual evidence, closed episodes, shortlists, economic event labels,
ghost continuations, decisions, deployments and performance metrics. Terminal
ghost files absent in both versions because no adjudication was needed are
recorded as matched absence, not as mismatched or compared file contents.

The audit explicitly separates source/status/version metadata, runtime,
regenerable checkpoints and v3-specific numerical-recovery diagnostics. It
does not ignore changed economic parameters: every configuration field other
than the version label is compared. Complete per-file SHA-256 pairs and
scope flags are retained in `cross_version_equality.json`.

Two copied one-block integrity controls exercise failure cases:
changing risk aversion is detected, as is changing a byte of the saved score
archive. The unmodified copied block passes. All original source-output hashes
remain unchanged; see `cross_version_integrity_controls.json`. These controls
add no simulated markets, arithmetic-replay checks or pytest test counts.

Byte equality cannot establish correctness of a computation shared by both
versions. Independent replay therefore remains required. The v3 pilot has
completed its first twenty generated markets and is replaying the second
batch before moving on. The complete 100-market pilot and separate 500-market
final stage remain outstanding. No financial parameter is retuned and no
failed market is excluded. These replayed paths count once, not as nineteen
additional replications.
