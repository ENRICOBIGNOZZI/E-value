# Detection-risk-set audit

The frozen `park_revive.metrics.detection_table` requires two consecutive
favorable annual rows with the same comparison ID. A support change closes
that comparison. Consequently, a method that accepts the beneficial move at
the first opportunity can fail to contribute an eligible event at all,
whereas a method that waits contributes an event. The denominators depend on
the response being measured. Right-censoring nonresponses does not repair
this exclusion of rapid responses.

The legacy detection.csv files are therefore exploratory survivor-conditioned
logs, **not** comparable event-detection distributions. No delay ranking or
claim of successful regime recognition may be based on them. This affects
the interpretation of the event logs, not the frozen daily portfolio returns,
costs, utility, evidence or the finding that the baseline remains inactive.

A valid economic-event design needs a risk set defined independently of the
response, for example continuing the exact counterfactual shadow pair after
its active comparison closes until the event-persistence classification is
resolved. This can be implemented in a future full-strategy study. Structural
coefficient or Markov-state events could also be followed, but must not be
renamed economic sign changes.

The new first-entry mechanism audit avoids this particular problem: every
one of the 100 fixed-reference comparisons is followed for the complete
horizon, including after a threshold crossing. It reports the first annual
eligible entry or censoring at the common end, and makes no PARK/REVIVE delay
claim.

The later full-strategy v3 implementation now retains these shadow
continuations and separates criterion dates, selected choices and executed
deployments. Its independent aggregation audit and scope are documented in
`full_event_reporting_protocol.md`. It checks reported denominators and rates
against retained JSON records. The separate reconstruction described in
`full_event_adjudication_protocol.md` now also derives the stable/unstable
labels from annual conditional-score arrays and ghost continuations, including
fast responses. Neither makes method-specific populations comparable causal
risk sets. The legacy limitation above remains in force for the old logs.
