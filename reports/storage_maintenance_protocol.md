# Verified scientific bytes and physical storage

This optional maintenance supports the existing 100-pilot/500-final study.
It changes neither scientific source nor configuration, analysis, thresholds,
seed membership, arithmetic-replay counts or economic outcomes.
The original controller and two-worker runner remain unchanged.

macOS ditto's native filesystem compression is transparent to ordinary file
reads. A copy probe confirmed equal logical SHA-256 bytes with fewer allocated
blocks. The operational utility processes only requested, completed markets
whose exact source/configuration and current independent-replay input digests
pass the existing snapshot validator.

Only JSON files of at least 16 KiB are candidates. Checkpoint files, original
empirical inputs and active/unverified markets are excluded. Each candidate
is copied into temporary staging on the same filesystem, outside the seed
directory. Both byte streams and source identity are checked; timestamps and
permissions must match. Only a smaller allocated copy replaces the original,
atomically. Exact logical SHA-256 bytes and whole-market replay digests are
checked again. No extra marker is written inside a scientific seed directory.

The first-ninety pilot transaction and its dry run are retained under
full_v3_results. All ninety existing replay input digests remain identical.
Allocation accounting uses st_blocks and is distinct from unrelated changes
in whole-filesystem free space. Superseded temporary PDF-render PNGs are
separately removed, retaining source PDFs, all scientific files, live logs and
the current manuscript, pilot-preview and software-layout render caches.

The separate final-storage observer attaches to the actual existing
continuation controller. It launches no simulation and restarts no process.
It waits for verified final prefixes, with at least fifty additional markets
or the terminal complete prefix. The same byte-preserving utility and source/
analysis gates then apply. A source pin and separate process lock prevent
silent loaded-source changes and duplicate maintenance. Invalid or changed
evidence stops maintenance; the scientific runner's existing 2 GiB per-seed
reserve remains in force. Observation failures retry the same handle.

Operational state and immutable per-prefix records live outside per-market
inputs, under outputs/park_revive_full_v3/storage_maintenance. A terminal
storage-check phase is not completion of the scientific analyses or paper.
Actual final data, event reconstruction, report assessment, manuscript
integration and visual review remain separate requirements.

The maintenance is macOS-specific and optional. Reproduction of the paper
requires the logical scientific bytes, not this filesystem encoding. Current
capacity estimates and measured allocation reductions are not guarantees
against future file-size variation, in-flight caches or unrelated disk usage.

Controls cover corrupted/partial copies, concurrent writes, timestamp loss,
symlinks, protected/existing output destinations, stale replay, fingerprint
drift, exact final-pool progress and monotone fifty-market scheduling.
They generate no financial markets.
