# Automatic continuation of the frozen study

The live continuation observes the existing 100-market pilot runner. It does
not start or restart a pilot. Its controller uses an operating-system process
lock, and its recorded PID must be checked against the actual process before
treating a status file as evidence of ongoing execution.

After the original pilot handle ends, the controller requires the exact
100-market stage-completion record. It then checks the original source,
configurations, analysis code and exact plan bytes committed at c7f7275,
seals every requested market
against byte-current independent replay, independently recalculates its report
summaries, and writes the explicitly labeled pilot assessment. A completion
file by itself cannot pass these gates.

It then launches the **500 declared final markets**, 60001–60500, with **two
workers**, batches of ten and verified checkpoint-cache compaction. It refuses
to launch a second active final-stage runner. Observation timeouts only trigger
another wait on the same process; they never trigger a restart. No condition
on economic performance, effect direction, interval width or event counts
determines whether the final study proceeds. The existing per-seed disk-space
guard and failure handling remain in force. Numerical or execution errors stop
the continuation and retain the generated data for diagnosis.

After the final stage ends successfully, all 500 markets must pass the same
source/configuration/completion/replay gates. The controller seals `main_500`,
independently checks its reporting arithmetic, and applies the already frozen
economic analysis. Existing sealed results and assessments can be reused only
when their bytes/inputs agree; a different prior report is not overwritten.

The terminal success phase is **`final_audited_ready_for_manuscript`**. It
means the simulation evidence is ready for editorial synthesis. It is not
publication, remote Git deployment, a scientific superiority claim or
completion of the overall paper goal. The manuscript is not automatically
rewritten. Source corrections, scientific amendments, storage failures and
unexpected results still require explicit diagnosis within the ongoing work.

Operational state lives in the ignored output directory:
`outputs/park_revive_full_v3/continuation_status.json`. Controller and final
logs are `tmp/full-study-continuation.log` and `tmp/full-v3-final500.log`.
An independently captured live-process snapshot is retained in
`reports/full_v3_results/continuation_checkpoint.json`.

The recorded current launch attaches to pilot PID 64355:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python \
  scripts/continue_full_study.py --pilot-pid 64355 --workers 2
```

This is the historical launch command, not an instruction to reuse that PID
after it ends. A new invocation needs the actual intended live pilot handle or
complete terminal-stage evidence, and must not duplicate an existing controller
or final runner. Nineteen software controls cover exact stage membership,
source/plan drift, missing/reused process handles, no observer restart,
immutable assessments, the insufficiency of completion metadata alone and a
real two-process lock. Failed process observations check the actual handle
and retry if it is still live or unconfirmed. A changed machine-readable
comparator is rejected even if all other freeze fields still match. They
generate no financial markets.
