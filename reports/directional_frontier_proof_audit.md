# A sharp iid ENTRY frontier under only a second-return-moment cap

This is a mathematical specialization of classical contamination arguments,
not a new general impossibility principle. It concerns a fixed costless scalar
policy against cash, not the full financial DGP, adaptive support search, or
arbitrary reoptimized PARK moves. No financial source or parameter changes.
The result and complete proofs are integrated in manuscript sections
`13_directional_information.tex` and `14_directional_proofs.tex`. A deterministic
audit checks 302 finite identities/envelopes, including the boundary and an
explicit return representation of the earlier score-based rare-loss bound.
These checks do not establish the sequential or asymptotic assertions; the
proofs below do. No additional random paths or financial arms are introduced.

## 1. The exact class and rejection guarantee

Fix gamma>0 and a known K>0. The observed fixed policy return is r, with
U(r)=r-gamma*r²/2. Let P_K contain all iid return laws with M2=E r²<=K.
The null is H0={P in P_K: E U(r)<=0}. A possibly randomized sequential test
must have Q(tau<infinity)<=alpha for every Q in H0. It may observe the full
return sequence, not just its utility score. Its randomization is independent
and coupled identically in the argument below.

For any P in P_K, put mu=E_P r. Then:

1. If mu<=gamma*K/2, every such uniformly valid test has
   P(tau<infinity)<=alpha, even when E_P U(r)>0.
2. If mu>gamma*K/2, a single test using only K and gamma can have eventual
   power one for every such P. It does not require knowledge of mu or M2.

The boundary is included in the impossibility region. It is a frontier for
uniformly valid sequential testing over this moment class, not a statement
that the expected utility is unidentified from an infinite iid sequence.

## 2. Explicit null sequence proves necessity

For every epsilon in (0,1), define

    a_epsilon = -sqrt{[K-(1-epsilon)*M2]/epsilon},
    Q_epsilon = (1-epsilon) P + epsilon point_mass(a_epsilon).

The radicand is nonnegative because M2<=K. Direct calculation gives

    E_Q r² = K,
    E_Q U(r) = (1-epsilon)*mu
                -sqrt{epsilon*[K-(1-epsilon)*M2]} - gamma*K/2.

If mu<=gamma*K/2, this is at most -epsilon*gamma*K/2<0. Thus Q_epsilon is
an admissible iid null while its first-N return law differs from P's by total
variation at most N*epsilon, using the mixture coupling. Therefore

    P(tau<=N) <= alpha+N*epsilon.

Let epsilon decrease to zero at fixed N, then N increase to infinity. This
gives P(tau<infinity)<=alpha. Training observations can be included in N.
If P has all absolute moments finite, every Q_epsilon also does, so mere
existence of arbitrarily high moments without numerical caps does not help.

If E_P U>0 in this region, M2<K necessarily. For finite M4,

    E_Q r^4 = (1-epsilon)*M4 + [K-(1-epsilon)*M2]^2/epsilon -> infinity.

A fixed numerical higher-moment cap can therefore exclude this sequence.
The known second-moment cap alone does not imply uniform integrability of
r². Without any common second-moment cap, choose K large enough for any fixed
P: no positive-utility alternative in this class is uniformly testable above
size. The same conclusion persists if all laws have all moments finite.

## 3. A conservative statistic attains the frontier

Let Z=r-gamma*K/2. Since M2<=K,

    E Z = mu-gamma*K/2 <= E U(r),
    E Z² <= [sqrt(K)+gamma*K/2]² = nu_Z².

The original utility null implies the surrogate mean null. Applying T1's
Catoni process to Z with this public raw-second bound is consequently valid
for the original utility null. More generally the domination holds datewise
with a valid predictable conditional second-return bound.

Under any iid P with mu>gamma*K/2, Z has constant positive mean and this
second-moment bound. T2's capped past-only positive mean bet, with any allowed
predeclared initial gain, has crossing probability tending to one as the
evaluation horizon increases. One process, not an alternative-specific
oracle, therefore attains eventual power one throughout the stated region.
No finite expected rejection-time result is inferred here.

The surrogate's inability to certify positive utility when mu<=gamma*K/2 is
therefore unavoidable for all uniformly valid tests in this class, not merely
an avoidable defect of that sufficient statistic. If gamma*sqrt(K)>=2, the
detectable region is empty because mu<=sqrt(K).

## 4. Any known return moment strictly above two is sufficient for general iid consistency

This does not prove fourth or eighth return moments are necessary. Suppose
instead E|r|^(2+xi)<=M is known, xi>0. Put p=1+xi/2. Minkowski and Lyapunov
give the public utility moment bound

    E|U(r)|^p <= [M^(1/(2p)) + (gamma/2)*M^(1/p)]^p = M_U.

Choose fixed B_i=B0*2^i for i>=0, B0>0, and
b_i=kappa_p*M_U/B_i^(p-1), kappa_p=(p-1)^(p-1)/p^p. The corrected score
X_i=max{U,-B_i}-b_i has null mean nonpositive and lower bound -B_i-b_i.
For rho_j=2^(-j-1), use lambda_ij=rho_j/(B_i+b_i). Each product of
1+lambda_ij*X_i is a valid test supermartingale. Mix them with weights
2^(-i-j-2). Conditional Tonelli proves validity; all finite-time values are
finite because lambda_ij<=1/(2 B0).

At any iid E U=delta>0, choose i with b_i<delta/2, giving E X_i>0. For
lambda decreasing to zero,

    E log(1+lambda*X_i)/lambda -> E X_i>0.

Dominated convergence follows from the fixed lower bound and integrability:
the positive log is at most lambda*X_i,+ and the negative log divided by
lambda is bounded by 2*|X_i,-| when lambda*(B_i+b_i)<=1/2. Some j has positive
expected log growth, and the iid strong law makes that component diverge
almost surely. Its fixed positive mixture weight gives eventual rejection at
every fixed level. This countable construction is not the finite nine-member
financial implementation and has no asserted uniform delay bound.

## 5. Cash-PARK has a different one-sided geometry

The opposite score Y=-U(r)>=-1/(2 gamma) admits safe linear factors without
supplied numerical return-moment caps, provided its conditional expectation
exists. A countable mixture of stakes lambda_j=gamma*2^(-j-1), weights
2^(-j-1), is valid and eventually rejects every iid E Y>0 law with E|Y|<infinity.
The same small-stake log-growth argument proves this claim. The single fixed
stake gamma/2 is not asserted to have this universal consistency; its sharp
Gaussian behavior is established separately in the existing theorem.

This is specifically cash versus one risky reference. The quadratic contrast
of arbitrary reoptimized portfolios need not be bounded on either side.

## 6. Economic embedding of the earlier rare-loss corollary

Its deterministic positive utility delta is feasible for quadratic utility
only when 0<delta<=1/(2 gamma). Choose

    r_plus = 2*delta/[1+sqrt(1-2 gamma delta)],
    loss = delta*(1-epsilon)/epsilon,
    r_minus = -2*loss/[1+sqrt(1+2 gamma loss)].

Then U(r_plus)=delta and U(r_minus)=-loss. The rare-loss score null therefore
has a concrete fixed-entry return representation. It need not obey other
public return-moment caps or the fixed Laplace DGP. It is not an admissible
arbitrarily large negative cash-PARK score, whose economic lower bound would
exclude it. These distinctions delimit the earlier moment-only lower bound.

## Primary-source context

[Bertanha and Moreira](https://arxiv.org/html/1612.02024), Section 2, develop
the established null-density and trivial-power framework, including total
variation and classical Bahadur–Savage impossibility. The iid mixture argument
above is given in full rather than attributed as a new general theorem.
[Fan, Jiao and Wang](https://sas.uwaterloo.ca/~wang/papers/2024Fan-Jiao-Wang-Biom.pdf)
study existing e-process constructions for conditional mean and variance.
Our claim is the explicit utility frontier and directional specialization;
expectation domination, small-stake mixtures and safe mean testing are known
tools. No unqualified priority claim is made.

The targeted comparison in `directional_prior_art_audit.md` gives the explicit
hypothesis inclusion and distinguishes the total-variation corollary from
the weak-topology result that requires continuity. The proof above uses finite
prefixes and then a monotone horizon limit, not total-variation convergence of
the infinite product laws. This changes attribution and exposition only.
