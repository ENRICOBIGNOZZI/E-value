# Proof audit: costless cash-PARK with vanishing estimation error

Status: the costless scalar theorem, uniform plug-in separation and complete
proof are now integrated in `paper/sections/11_vanishing_gains.tex` and
`paper/sections/12_vanishing_proofs.tex`. The controlled study's very low
finite-horizon power is reported alongside them. Historical notes remain
excluded. Sixty-six deterministic quadrature checks support the identities;
they do not prove the asymptotics or stopping-time statements. No claim of a
first general betting, likelihood-optimality or prequential-regret theorem is made.
The financial configuration and its positive comparison-mean floor are unchanged.

## 1. Validity requires no separately certified high return moment

Let U(r)=r-gamma*r²/2, gamma>0, and let the risky reference have an arbitrary
predictable target w_t. For cash versus that reference, at zero costs,
Y_t=-w_t A_t+gamma*w_t² A_t²/2 >= -1/(2 gamma). Thus lambda=gamma/2 gives
1+lambda Y_t>=3/4. Under every law with meaningful finite conditional score
expectations delta_t<=0, the product G_n of these factors is a nonnegative
supermartingale starting at one. This is ordinary linear betting with an
economic lower bound. It requires no supplied fourth/eighth return-moment cap.
The null's integrability condition remains essential. With predictable cost
difference D_t<=Cmax, replace lambda by gamma/[2(1+2 gamma Cmax)].

For a fixed nonnegative contraction w_B=k w_S, 0<=k<1, the same completion of
the square gives Y>=-(1-k)/[2 gamma(1+k)]-D. This is a different policy question
for each k; it does not establish power dominance under a common null. It does
not apply to an arbitrary separately reoptimized single-signal deletion.

For fixed lambda, the same product is also an e-process under the weaker null
sum_{t<=n} delta_t<=0 at every n. Indeed H_n=G_n exp(-lambda sum delta_t) is a
supermartingale because (1+lambda delta_t) exp(-lambda delta_t)<=1, and H>=G
under that weak null. Integrability follows by truncation/localization if the
dominating multiplier is unbounded. This argument does **not** justify the
reported variable-bet financial tests under that weaker null.

## 2. A precise stationary estimated-policy alternative

Under P let all returns, including n0>=5 training observations, be iid
N(0,sigma²). At each evaluated date take

    w_t = clip[ historical mean / (gamma*(historical raw second moment+r)), -L,L ],

with fixed L>0, r>=0, m=sigma²+r, and no minimum-effect filter. The raw moment
estimate tends to m, and w_t tends to zero. Write S_n=sum w_t². Then

    S_n/log n -> sigma²/(gamma²*m²)    P-almost surely.

Self-contained quadratic strong law: if B_i is the sum of i iid centered
returns with finite fourth moment, for i<=j,
Cov(B_i²,B_j²)=2 i² sigma^4+i*kappa4. For T_n=sum B_i²/i², E T_n is
sigma² log n+O(1), and Var(T_n)=O(log n). Chebyshev and Borel--Cantelli at
floor(exp(k²)) give T_n/log n->sigma² on that subsequence. Monotonicity and
log n_{k+1}/log n_k->1 interpolate all n. Clipping is eventually inactive.
Convergence of the raw risk denominator and weighted Cesaro prove the claim.
Deleting a fixed initial prefix does not alter the limit.

For k past Gaussian observations, radial/angular independence gives

    E(mean/rawM)² = 1/[sigma²(k-2)],
    E|mean/rawM|³ = 2 sqrt(2) k^(3/2) /
                    [sqrt(pi) sigma³ (k-3)(k-1)(k+1)],
    E(mean/rawM)^4 = 3k/[sigma^4(k-4)(k-2)(k+2)].

Clipping and r>=0 reduce absolute targets. Consequently sum E|w_t|³ and
sum E w_t^4 are finite, and E w_t²=O(1/t).

## 3. An admissible dependent null gives the information upper bound

Put h=gamma/2 and a_t=h*sigma*w_t. Define Q to match P during training and,
thereafter, conditionally on the observed past, to have Gaussian mean
a_t*sigma/(1+a_t²) and variance sigma²/(1+a_t²)². This defines a probability
law by sequential Gaussian kernels, and each finite-horizon P and Q are
mutually absolutely continuous. No small-leverage restriction is required.

Under Q the raw second moment is sigma²/(1+a_t²) and the mean equals
h*w_t times that raw moment. Therefore E_Q[Y_t|past]=0 at every date. Its raw
fourth moment is sigma^4*(3+6a_t²+a_t^4)/(1+a_t²)^4<=3 sigma^4. Q belongs
both to the no-certified-moment cash-PARK null and to the narrower public
moment contract M2=sigma², M4>=3 sigma^4. The null permits dependence; it is
not restricted to iid laws.

For R_n=dP/dQ through evaluated date n, the exact log increment under P, with
Z_t=A_t/sigma, is

    ell_t=-log(1+a_t²)+.5*{[(1+a_t²)Z_t-a_t]²-Z_t²}.

Its conditional mean is -log(1+a_t²)+1.5 a_t²+.5 a_t^4
=.5 a_t²+O(a_t^4). Its conditional variance is O(w_t²), uniformly for bounded
targets. A martingale strong law yields the following normalization: if the
conditional variances are at most C w_t², sum of the variances divided by
(1+S_t)² is finite because sum w_t²/(1+S_t)²<=1. Martingale convergence and
Kronecker give the centered sum/S_n->0. Weighted Cesaro then implies

    log R_n/log n -> c = sigma^4/(8 m²) > 0    P-almost surely.

For **any fixed Q-valid e-process F**, change of measure at bounded stopping
times gives E_P[F_tau/R_tau]=E_Q[F_tau]<=1. Thus F/R is a P-valid e-process,
whose path supremum is finite P-almost surely by Ville. Consequently
limsup log F_n/log n<=c. This uses one admissible null to bound every test of
the entire conditional-null class. It does not assert that Q is the exact
finite-horizon information projection.

## 4. Standard linear betting attains the rate with bounded log discrepancy

The economic factor equals 1-a_t Z_t+a_t² Z_t². Uniformly over real x,

    log(1-x+x²) = -x+x²/2 + remainder, |remainder|<=C|x|³.

Such a finite C exists by Taylor expansion at zero, positivity of the
quadratic, and quadratic domination at infinity. Expanding the exact ratio,

    log G_n-log R_n = -.5 sum a_t²(Z_t²-1) + summable remainder.

The centered sum is L2 bounded because sum E a_t^4<infinity. The remainders
have a finite sum of absolute expectations by the bounds in section 2 and
Gaussian moments. Hence log G_n-log R_n converges to a finite real random
variable P-almost surely and sup_n E_P|log G_n-log R_n|<infinity. In particular
log G_n/log n->c. This is a specialization of likelihood/betting comparisons,
not a new general numeraire principle.

Catoni with fixed lambda=gamma/2 and predictable certificate
v_t²=w_t²*(sigma+gamma*|w_t|*sqrt(M4)/2)² attains the same rate under the
public contract M2=sigma². Here phi(x)-x=O(|x|³) globally and
v_t²-sigma² w_t²=O(|w_t|³+w_t^4). The absolute expected remainders are
summable; the leading log increment is exactly that of log R above. High
moment information is needed by this certificate, even though the linear
economic factor needs none. A loose M2 changes Catoni's leading coefficient;
do not attribute this sharp coefficient to an arbitrary public envelope.

## 5. Sharp confidence exponent and waiting utility, without expected-time claims

For tau_alpha=inf{n:G_n>=1/alpha}, the pathwise log-growth limit implies

    log tau_alpha/log(1/alpha) -> 1/c = 8 m²/sigma^4 almost surely.

For any family of tests with Q(tau_alpha<infinity)<=alpha, including a
different test for every alpha, let N_alpha=floor(alpha^(-d)), d<1/c, and
choose eta>0 with c*d<1-eta. Bounded-time change of measure gives

    P(tau_alpha<=N_alpha) <= alpha^eta
      + P(max_{t<=N_alpha} log R_t > (1-eta)log(1/alpha)) -> 0.

The maximum term vanishes because log R_n/log n->c also implies
max_{t<=N} log R_t/log N->c almost surely. This is a sharp exponent for this
particular estimated-policy instance and conditional-null class. It is not
a minimax theorem over all investment DGPs or an expected stopping-time law.

The cumulative conditional benefit of immediate cash over continuing the
reference is C_n=gamma*sigma²*S_n/2, so for the linear stopping time

    C_tau_alpha/log(1/alpha) -> 4/gamma almost surely.

For arbitrary valid test families the same coefficient is a lower bound in
probability, using monotonicity of C_n and the preceding time lower bound.
It does not mean E C_tau_alpha is asymptotically that value. Uniform
integrability and finite expected stopping times have not been established.
Fixed annual review spacing leaves the exponent unchanged by the same growth
sandwich on the review grid; a daily crossing need not persist until the next
review, so one must **not** claim the delay differs by at most one block.

## 6. Why the uniform past-mean bet can stop accumulating information

Let nu² be the uniform geometric certificate obtained at |w|=L. Use any finite
initial bet, then the original positive historical score mean/(2 nu²), capped
as in the software and held for blocks of fixed length. Under P, martingale
normalization gives sum Y_t/S_n->gamma*sigma²/2. Thus the bet is
O(log t/t) almost surely and sum lambda_t²<infinity. Also
sum (log(t+1)/t) w_t²<infinity almost surely, by E w_t²=O(1/t). The transformed
conditional drift is absolutely summable, since |phi(x)-x|<=x²/2 and
sum lambda_t*delta_t<infinity. The centered transformed increments have
summable predictable variance, so their martingale converges by localization.
The resulting uniform plug-in log capital converges to a **finite real**
random limit. Its supremum is finite almost surely. Therefore its eventual
crossing probability tends to zero as alpha decreases to zero, whereas
linear and fixed geometric betting cross almost surely at every fixed alpha.
No zero-power claim is made at an individual fixed level.

A fixed positive minimum-effect floor eventually excludes these vanishing
opportunities. Costs, episode closures, multiple signals and changing regimes
also fall outside this example. It cannot establish PARK/REVIVE adaptation or
superior full-fund performance in the main financial simulation.

## 7. Primary-source overlap and remaining presentation decision

- [Choe and Ramdas](https://arxiv.org/html/2110.00115), sections 4.4 and F:
  sequential paired-score inference, weak versus strong nulls, and predictable
  bounds are established. Our economic factor is a specialization, not a new
  general forecast-comparison framework.
- [Waudby-Smith, Sandoval and Jordan, v2](https://arxiv.org/html/2504.02818v2),
  sections 1.1, 3 and Appendix E: portfolio betting and sharp rejection-time
  comparisons are established. Their stated growth results use iid input
  e-value tuples, including the abstract Appendix E setup; the present
  estimated-policy factors have vanishing nonidentically distributed signal,
  an adaptive dependent null and log(n) information growth. This distinction
  does not make the likelihood-ratio proof principle new.
- [Fan, Jiao and Wang](https://arxiv.org/html/2301.12480v7), sections 2–4:
  conditional mean/variance testing, one-observation e-values and their
  standard linear combination products are established. Their iid consistency
  proposition does not directly establish the estimated-policy confidence
  exponent above. No novelty is claimed for multiplying safe factors.
- [Grünwald and de Rooij](https://arxiv.org/abs/cs/0502004) and
  [Grünwald and Kotłowski](https://arxiv.org/abs/1002.0757): logarithmic losses
  of prequential plug-in predictions are established. Quadratic strong laws
  and Gaussian mean-estimation log losses must be treated as known tools.
- [Clark and McCracken, author version](https://www.kansascityfed.org/documents/5266/pdf-rwp99-11.pdf)
  and [Clark and West, author version](https://www.kansascityfed.org/documents/5368/pdf-RWP05-05.pdf):
  nested forecast comparison already accounts for estimated extra coefficients
  producing noise and smaller-model prediction advantages. Our cash-PARK
  comparison retains the implemented policy's estimation loss in its utility
  target; it does not introduce the general phenomenon of nested-model noise
  or replace their predictive-content tests.

The potentially useful contribution is the explicit cash-PARK example:
vanishing estimation-error gains, failure of a particular uniform-bound
plug-in rule, an attainable conditional-null confidence exponent, and its
economic waiting-utility coefficient. The controlled experiment is a check
of finite-horizon behavior, not a substitute for these proofs. A broader
publication-level novelty assessment remains necessary. The current manuscript
presents the explicit example and proofs without an unqualified priority claim.
