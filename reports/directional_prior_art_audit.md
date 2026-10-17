# Targeted hypothesis/attribution audit: ENTRY frontier — 17 October 2026

Status: primary statements inspected; no scientific simulation, test rule,
parameter, mathematical result or observed estimate changed. This targeted
comparison does not establish publication-level priority.

| Primary source | Inspected location | Boundary to preserve |
|---|---|---|
| [Fan, Jiao and Wang, author preprint, 24 September 2024](https://sas.uwaterloo.ca/~wang/papers/2024Fan-Jiao-Wang-Biom.pdf) | Section 2.1; Theorem 1; Section 4.1, equations (5)--(7) and Proposition 1; Section 4.3 | Their baseline concerns conditional mean and variance upper bounds; e-variable construction and predictable betting precede our specialization. Additional shape restrictions narrow their classes. |
| [Bertanha and Moreira, author version](https://arxiv.org/html/1612.02024) | Section 2, Corollary 1 and Theorem 2 | The total-variation corollary applies to bounded measurable tests. The weak-topology theorem has a continuity qualification. The manuscript's explicit coupling uses total variation. |

The Fan--Jiao--Wang [published record](https://academic.oup.com/biomet/issue/112/1)
is *Biometrika* 112(1), asae049 (2025), DOI 10.1093/biomet/asae049.
The manuscript now cites that record and retains the dated author preprint;
the locations above refer to the inspected preprint.

## Explicit comparison for our iid class

Put c=gamma*K2/2 and U(r)=r-gamma*r²/2. Our theorem fixes

    P(K2) = {iid P: E_P r² <= K2},
    H0_U  = {P in P(K2): E_P U(r) <= 0}.

For every Q in H0_U,

    E_Q r <= (gamma/2) E_Q r² <= c,
    Var_Q r <= E_Q r² <= K2.

Hence H0_U is contained in the iid part of the joint mean/variance null
with mean cap c and variance cap K2. This is a conservative valid route,
not equality of hypotheses. At gamma=K2=1, deterministic r=.2 has utility
.18, mean .2<=.5 and variance zero. It belongs to the larger joint null but
not to H0_U. This is the existing point A in the manuscript figure, not a
new simulated alternative. Our explicit contamination proof shows why even
tests of H0_U itself cannot have nontrivial power there.

Applying a variance-based construction directly to U(r) is a different
operation: a raw second-return-moment cap alone does not supply a variance
bound for the quadratic utility score. The already proved above-two-moment
route supplies a utility p-moment contract instead. There is no new numerical
comparison against the cited procedures, and no power ranking is inferred.

There is also a simple reason not to transplant the particular one-step score
`E0=(Y_+)²/nu²` without checking the contract. If the same raw-score cap
`E(Y²|past)<=nu²` holds under an alternative, then `E(E0|past)<=1` there,
regardless of the sign of `E(Y|past)`. A product of factors
`1-lambda_t+lambda_t*E0_t`, with predictable shares in [0,1], remains a
supermartingale under that alternative. This observation concerns that specific
transplant and cap, not every procedure in the cited paper. It makes no
numerical or general efficiency comparison.

## Why the finite-prefix order matters

The manuscript constructs genuine admissible nulls Q_epsilon and couples the
first n returns so TV(P^n,Q_epsilon^n)<=n*epsilon. Common independent test
randomization does not alter that bound. For fixed n, first let epsilon go to
zero; then let n increase to infinity in P(tau<=n). This proves the stated
ever-rejection bound for all measurable stopping tests. It does not claim
that the infinite-product distributions converge in total variation.

This is a utility-specific construction within an established null-density
framework. The exact raw-return-cap frontier and its attaining surrogate
remain the manuscript's explicit specialization; no general impossibility,
mixture, mean/variance testing or topology principle is claimed as new.
Broader novelty validation and complete final-study evidence remain open.
