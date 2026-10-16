# Research note: ENTRY and cash-PARK need different information

This historical derivation note is **not a frozen financial method**. The
current stronger result and full proofs are integrated in
`paper/sections/13_directional_information.tex` and
`paper/sections/14_directional_proofs.tex`; see
`directional_frontier_proof_audit.md`. In particular, a common second-return-
moment cap alone still leaves an exact region of untestable positive utility.
The conservative surrogate below attains the complementary region. The older
moment-existence argument is retained as background.
It records a useful structural implication of the chosen quadratic utility,
not a claim of a new general impossibility theorem. The construction is in
the classical Bahadur–Savage contamination tradition. The original article
is [Bahadur and Savage (1956)](https://doi.org/10.1214/aoms/1177728077);
its full text was not accessible in the current tool session. A primary modern
treatment of null-set density and trivial power is
[Bertanha and Moreira](https://arxiv.org/abs/1612.02024). The argument below is
given explicitly and does not rely on an unread theorem statement.

## Exact cash-PARK score

At zero costs let U(r)=r-gamma*r²/2, gamma>0. Comparing cash to any predictable
risky reference gives Y=-U(r)>=-B, B=1/(2 gamma). Ordinary linear betting
with lambda=gamma/2 has factors at least 3/4 and is valid under the datewise
nonpositive conditional-mean null without a supplied return-moment cap.
The score expectation must still exist. Costs require the stated predictable
bound adjustment in `vanishing_gain_proof_audit.md`. This does not describe
an arbitrary separately optimized removal of one signal.

## Why moment existence alone cannot validate ENTRY uniformly

Already consider a **fixed, nonzero** scalar target w and cash reference,
with iid returns and ENTRY score X=U(w A). Let the null include all iid return
laws with E X<=0 and finite moments of every order, with **no common numerical
moment bound**. Let any possibly randomized sequential test satisfy
Q(tau<infinity)<=alpha for every such null law.

For any alternative iid law P with all return moments finite, take epsilon>0.
Since X<=B, choose a finite return a_epsilon such that
U(w*a_epsilon)=-B/epsilon. It exists because w!=0 and the quadratic tends
to minus infinity. The iid mixture

    Q_epsilon = (1-epsilon) P + epsilon point_mass(a_epsilon)

has all moments finite and E_Q X <= (1-epsilon)B-B = -epsilon B < 0.
At any fixed N the first-N return laws have total variation at most N*epsilon.
Hence P(tau<=N)<=alpha+N*epsilon. Let epsilon decrease to zero, then N
increase to infinity: **P(tau<infinity)<=alpha**. The test cannot have power
above size even at an iid alternative. Randomization is coupled identically.

This is a standard contamination impossibility specialized to an ENTRY score
bounded above and unbounded below. It does not say that all entry tests fail
under the paper's public moment contract or its fixed Laplace DGP. The
contamination's moments become arbitrarily large as epsilon decreases, so a
valid common moment envelope or other tail/distribution restriction can rule
it out. Finiteness of moments without common bounds cannot do so. The claim
does **not** show that fourth or eighth return moments are necessary.

The basic fixed-policy statement is enough to rule out a general moment-free
ENTRY guarantee. An arbitrary adaptive-policy extension would require a
careful specification of conditional versus unconditional moment existence;
it is not silently claimed here.

## A conservative ENTRY route with a public second-return-moment bound

The exact paired utility score is not the only statistic that can test its
conditional null. If a predictable, valid public K_t bounds
E[r_t²|past], then for predictable cost difference D_t define

    X_t = r_t - gamma*r_t²/2 - D_t,
    Z_t = r_t - gamma*K_t/2 - D_t.

Then E Z_t <= E X_t. In particular the original utility null E X_t<=0
implies the surrogate null E Z_t<=0. With a_t=gamma*K_t/2+D_t,

    E Z_t² <= (sqrt(K_t)+abs(a_t))².

Thus the established Catoni construction applied to Z_t yields an e-process
valid for the **original utility null**, using only a second return moment.
It may lose power because its conservative mean is strictly below the actual
utility gain. A sample risk estimate is not a certified K_t without additional
arguments. Rejection still concerns the historical conditional-null episode,
not current deployment gain or search-wide safety.

For a general pair, write d=r_B-r_S, s=r_B+r_S, and let public D2,S2 bound
E d² and E s². Conditional Cauchy–Schwarz gives E(ds)<=sqrt(D2*S2). Therefore

    Z = d - gamma*sqrt(D2*S2)/2 - D

has E Z<=E Y for Y=d-gamma*ds/2-D, and its raw second moment is at most
[sqrt(D2)+abs(gamma*sqrt(D2*S2)/2+D)]². This is another sufficient
second-return-moment route to the same null. Public information that bounds
E(ds) more tightly can improve the conservative shift. The bound can discard
all useful PARK power because it ignores a negative quadratic contrast;
cash-PARK's exact one-sided factor should be distinguished from this generic
surrogate.

These are standard expectation domination, Cauchy–Schwarz and Catoni arguments.
They clarify that the manuscript's fourth/eighth-return-moment constructions
are **sufficient information choices, not a minimal-moment theorem**. No
surrogate financial arm is run or substituted after observing the pilot.
