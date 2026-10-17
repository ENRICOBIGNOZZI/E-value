# Gaussian deadline-power envelope — post-hoc diagnostic

This diagnostic was specified after inspecting both controlled lambda studies.
It changes no protocol, creates no study arm, calibrates no thresholds and
draws no paths. Only the fresh seed-450001 companion is used; original and
companion observations are not pooled. The twelve existing DP/constant rules
(two grids, three deadlines, two classes) and all three positive actual means
are retained, including numerical refinement and misspecification alternatives.

## Classical bound and scope

Let Q0 be iid N(0,sigma²) and Qdelta be iid N(delta,sigma²), delta>0.
For any possibly randomized test psi in [0,1] based on H scores, with
E_Q0 psi <= s, the classical Neyman--Pearson bound is

    E_Qdelta psi <= B_H(s)
                   = Phi(delta*sqrt(H)/sigma + Phi^{-1}(s)).

Use B_H(0)=0 and B_H(1)=1. If tau is an early rejection time, psi=1{tau<=H}
is such a test: its mathematical decision is a function of a potential full
H-prefix even when collection stops at rejection. Common independent
randomization does not change the bound. Neither predictable bets nor several
reviews evade this information bound for rejection by H.

For completeness, the likelihood ratio is

    L_H = exp(delta*sum(Y_i)/sigma² - H*delta²/(2*sigma²)).

Choose psi*=1{sum(Y_i)/(sigma*sqrt(H)) > Phi^{-1}(1-s)}. Its Q0 expectation
is s and its Qdelta expectation is B_H(s). For its likelihood-ratio cutoff c,
(psi-psi*)*(L_H-c)<=0 pointwise. Integrating gives
E_Qdelta(psi-psi*) <= c*E_Q0(psi-psi*) <=0. The endpoints follow from absolute
continuity. This specializes established testing theory; it is not a new
Catoni or composite-null optimality theorem.

The [scanned original paper](https://www.joelvelasco.net/teaching/249/Neyman%20Pearson%201933.pdf)
is J. Neyman and E. S. Pearson (1933), *On the Problem of the Most Efficient
Tests of Statistical Hypotheses*, Philosophical Transactions A 231, 289--337,
DOI [10.1098/rsta.1933.0009](https://doi.org/10.1098/rsta.1933.0009).
Its simple-hypothesis likelihood-ratio argument is the antecedent; the Gaussian
formula and application above are derived here.

The terminal Gaussian test attains the envelope only in the simple-law class.
It need not be valid over the full heavy-tailed moment null, and no claim of
validity under unrestricted monitoring is made for that terminal test.
The nominal-size .05 envelope is an oracle upper bound, not a competing
uniformly valid rule or proof of attainable power for any lambda policy.

## Monte Carlo uncertainty and reporting

The output gives nominal-size envelopes and descriptive envelopes formed by
plugging in observed null fractions. A plug-in is not an upper confidence
bound and supplies no matched-actual-size comparison. No threshold, policy
or sample is modified to equalize size. The observed power gap cannot be
causally allocated between different sizes and rejection regions here.

For uncertainty, use one exact-binomial upper limit for each of twelve null
rates and one exact-binomial lower limit for each of thirty-six alternative
powers. Each one-sided noncoverage probability is .05/48. A union bound gives
joint coverage at least .95, allowing within-law paired dependence between
rules. Monotonicity of B_H puts each true power below B_H(the null upper
limit). Compatibility of the lower power limit with this upper envelope is
a coarse diagnostic, not independent verification of a rule or the Gaussian
generator. Zero/all-crossing endpoints are retained exactly; these particular
bounds use neither Wilson nor normal approximations.

Eighteen direct Gaussian-density quadratures check the closed-form formula;
finite agreement is not the optimality proof. Software controls cover
exact-binomial inversion, endpoints, malformed panels and changed inputs.
Original stake/first-crossing audits and limited direct score replays remain
the evidence for the underlying counts.

Reproduce without generating or changing a scientific path:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/gaussian_power_envelope.py
```
