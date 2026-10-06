# Verification record — 6 October 2026

## Source and provenance

The numerical implementation was verified at repository commit
`12e4e4477c55e5d2271475b682fd29e1749dcedd`.
The completed GitHub Actions run is `37506160562`; its research artifact is
`11431608607`, SHA-256
`8baea48bf33709538c43b9b76703c6f2e716237b0b3d0f8111e11a43204af69c`.

The official JKP source artifact is `11429668210` from run `37501574532`.
All four source files match the SHA-256 values in
`data/source_manifest_20261006.json`.

## Re-execution

Fifteen unit tests pass. The complete primary Monte Carlo was rerun as four
partitions using the same scenario-indexed random seeds: seven designs, Gaussian
and Student innovations, 200 replications each, 1,800 observations per path.
All 2,800 scenario-path evaluations match the completed full run. In particular,
22,400 method-path records, 112 summary rows, and 194,880 fixed-path trace rows
have zero maximum numerical difference from the original outputs.

The JKP replay was rerun from the official archives: 153 USA monthly factors,
60 months of pre-launch history, January 2000–December 2025 evaluation, eight
policies and three cost specifications. Its 24 summary rows, 7,488 monthly
records, 2,229 action records and eight paired-bootstrap summaries also match
exactly. All certified policies make zero switches. The remaining simulation
suites are retained from the completed full workflow; this verification does not
count reruns as additional independent experiments.

The final manuscript is compiled from LaTeX and has 20 pages. All proofs are in
Appendix A. A page-by-page rendered contact sheet and enlarged pages were used
for layout review. Raw JKP archives, Python bytecode, build caches and font files
are excluded from the delivered source bundle.

## Literature and interpretation

The final manuscript adds the close methodological predecessor Choe and Ramdas,
*Comparing Sequential Forecasters*, Operations Research 72(4), 1368–1387,
DOI 10.1287/opre.2021.0792. This attribution changes no algorithm, configuration,
reported number, or proof. The reference method is not asserted to be SOTA;
lifetime false-alarm control is not a current-state economic guarantee.

The results establish a reproducible baseline and reveal a power limitation.
They do not establish incremental JKP performance or commercial deployability.
