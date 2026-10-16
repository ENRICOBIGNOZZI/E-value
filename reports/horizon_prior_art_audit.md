# Direct prior-art audit for deadline betting — 17 October 2026

Status: primary sources read; closest antecedents added to the introduction,
the horizon-power section and the bibliography. This changes attribution and
scope, not any scientific simulation source, tuning parameter or observed path.

| Primary source | Relevant location | Overlap |
|---|---|---|
| [Taga, Oymak and Shekhar](https://arxiv.org/html/2603.19551), [published ICML version](https://proceedings.mlr.press/v306/taga26a.html) | Section 3, equations (13)–(15); Section 4 | Bounded-mean deadline power, time/log-capital control and numerical or learned betting policies |
| [Clerico, Wegel, Azangulov and Rebeschini](https://arxiv.org/html/2605.06521) | Sections 3–4 and 6 | Rejection-time rewards and Bellman reduction; hard-deadline simple-vs-simple relation to a terminal Neyman--Pearson test |
| [Baas, ter Schure and van Rosmalen](https://arxiv.org/html/2605.28653) | Section 3, equations (6)–(8) | Finite-horizon binary-trial design optimizing power or expected sample size |

The manuscript's finite-action Bellman induction is therefore a specialization
of established statistical control ideas, not merely an analogy with an older
control-theory paper. Its scope is the specified Catoni factor, public score
second-moment certificate, fixed 100-observation blocks, declared working law,
cap and numerical grids. The numerical experiment shows the behavior of that
specialization against its retained controls, including fresh deadline-optimal
constants. No numerical results are changed by the literature review.

Predictability protects validity under the real conditional moment contract;
working-model power is a different claim. The scalar log-capital/time state
is sufficient for the declared independent block law, but a financial policy
model must also account for its evolving estimation and allocation states.
The current scalar study does not implement that larger control problem.

The paper does not evaluate the cited learned or binary-trial procedures on
its unbounded score law. Their published rankings are not transplanted here,
and the current comparison does not establish a best available testing method.
The general contrast between growth, terminal power and rejection-time rewards
is not presented as a discovery of this paper.

The remaining scientific contribution must rest on the explicitly stated
utility/state/moment specialization, its proofs and its executed economic
assessment. Complete final-study evidence and a broader publication-level
novelty assessment remain outstanding. No guarantee of a journal outcome or a
"10/10" rating follows from this audit.
