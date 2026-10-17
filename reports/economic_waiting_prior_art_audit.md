# Economic waiting and stopping-time normalization — targeted review

17 October 2026. This review addresses the estimated-reference cash-PARK
example and its economic interpretation. It changes attribution only: no
theorem, algorithm, parameter, random stream or reported estimate is changed.

| Primary source inspected | Location | Established antecedent |
|---|---|---|
| [Thijssen and Bregantini, accepted author manuscript, 16 December 2016; published 2017](https://eprints.whiterose.ac.uk/id/eprint/113052/1/HTA_JEDC_R2.pdf) | Section 3, Remarks 2--3, equation (4), Proposition 1 | Discounted project valuation includes a running penalty for delayed adoption. Optimal investment/abandonment follows posterior stopping thresholds. Economic costs of waiting for information are already explicit. |
| [Artola Velasco, Tsirtsis and Gomez-Rodriguez, arXiv v1, 7 May 2026](https://arxiv.org/html/2605.06520v1) | Section 2, equations (4), (7); Sections 3--5, Propositions 4 and 8 | E-value approval, experimentation costs and subsidies are combined with belief-state control. Sequential evidence and economic utility are already studied together. |
| [Ram and Ramdas, arXiv v1, 12 May 2026](https://arxiv.org/html/2605.12720v1) | Definitions 2.2 and 5.1; Theorem 3.1; Proposition 5.3; Appendix A.1 | WAIT aggregation connects level-indexed stopping families and log growth. Their formulations distinguish expectation, probability and pathwise optimality. Proposition 5.3 assumes nondecreasing capital. |

The published first reference is *Journal of Economic Dynamics and Control*
77, 202--229, DOI [10.1016/j.jedc.2017.01.016](https://doi.org/10.1016/j.jedc.2017.01.016).
The inspected PDF's cover and title page confirm Thijssen first, Bregantini
second; one repository catalogue reverses the author order.

## Mapping to this manuscript

Our cash-PARK calculation fixes a frequentist evidence constraint and an
expanding-fit reference policy. Its mean advantage, score variance and
information scale depend on that reference. The cumulative cost is derived
from the implemented quadratic utility and its realized score; it is not an
exogenously specified observation fee, subsidy or discounted adoption payoff.
These are distinct objectives and models, not grounds for a numerical ranking
against either economic decision framework. Their policies are not new arms
of the frozen financial simulation.

Our return-date index is n. The proved normalization is

    log G_n / log n -> kappa,
    log tau_alpha / log(1/alpha) -> 1/kappa.

In particular log G_n/n ->0: substituting kappa as a positive per-date growth
rate into a linear-clock theorem would be wrong. G_n can fall. Its running
maximum has the same threshold times, but a running maximum of a valid
e-process need not itself be an e-process. The direct first-passage argument
in Appendix C establishes the needed normalization without either shortcut.
Deterministic changes of clock can still convey general inversion ideas;
no claim is made that existing asymptotic frameworks can never accommodate
such clocks.

The stated almost-sure limits and probability lower bounds are not expected
stopped-time or expected stopped-utility limits. No uniform-integrability or
tail argument has been supplied to justify those stronger expectations.
This distinction is essential independently of the recent aggregation paper.
The manuscript's concrete coefficient 4/gamma and adaptive Gaussian null
remain instance calculations; neither costly learning nor the general relation
between evidence growth and rejection time is claimed as a new principle.

The review fills adjacent attribution gaps and sharpens the comparison. It
does not establish exhaustive priority for the exact example or publication
quality, and it does not replace the outstanding complete final simulation.
