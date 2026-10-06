# Theory V4 — portfolio-aware retirement, revival, and economic regret

## Scope

The statistical primitives (e-detectors, e-d-BH/EOP, and sharp bounded-mean quickest-detection bounds) are not claimed as new. The finance-specific object is conditional marginal portfolio utility, together with reversible PARK/REVIVE decisions, an economic indifference region, and the translation of detection information into unavoidable portfolio regret.

All slot sizes, scales, hurdle levels, and reference books used at time t must be measurable with respect to the global F_{t-1} filtration.

## T1 — Portfolio value

For a reference book B, strategy return R, predictable slot q, recurring hurdle c, and quadratic utility u(x)=x-gamma*x^2/2,

D = u(B+qR)-u(B)-c.

Its conditional value is theta=E[D|F_{t-1}], and exactly

theta = q*mu_R*(1-gamma*mu_B)
        - gamma*q*Cov(B,R)
        - (gamma/2)*q^2*(Var(R)+mu_R^2)
        - c.

Thus a negative-mean sleeve can be useful because it hedges the book, while a positive-mean sleeve can be harmful at a specified allocation because it is redundant, risky, or costly.

## Economic indifference band

For h>=0, define one-period material regret

r_h(A,theta)
 = (theta-h)_+ 1{A=PARKED}
 + (-theta-h)_+ 1{A=ACTIVE}.

ACTIVE is materially preferred for theta>h, PARKED for theta<-h, and either state is acceptable inside [-h,h]. This separation is economically and statistically necessary: under local Gaussian changes, delay is O(g^{-2}) and accumulated economic delay regret is O(g^{-1}) as the material gap g approaches zero.

## T2 — e-CUSUM validity

Normalize the portfolio score to Z_t in [-1,1]. During ACTIVE use Y_t=(1-Z_t)/2; during PARKED use Y_t=(1+Z_t)/2. Under the corresponding continuation null,

E[Y_t|F_{t-1}] <= m0.

For lambda in (0,1), define

L_t(lambda)=1+lambda*(Y_t/m0-1),

and

M_t(lambda)=L_t(lambda)*max(M_{t-1}(lambda),1), M_0=0.

For every stopping time tau under the conditional-mean null,

E[M_tau(lambda)] <= E[tau].

Any fixed convex mixture over lambda remains an e-detector. FAST uses a deterministic 31-point logit grid and equal weights.

## T3 — many alphas and EOP

FAST uses e-d-BH cross-sectionally: after sorting M_(1)>=...>=M_(K), choose the largest r satisfying

M_(r) >= K/(alpha*r).

Under global-filtration e-detector validity, the e-d-BH theorem gives EOP-FDR control. The use of EOP is essential: finite ARL and nontrivial worst-case lifetime FDR/FWER/PFER are incompatible in general.

## T4 — finite-sample power

Suppose after a material change E[Y_t|F_{t-1}]>=m1>m0. The tuned bet is

lambda*=(m1-m0)/(1-m0).

For f(y)=log(1+lambda*(y/m0-1)), concavity and the endpoint chord imply

E[f(Y_t)|F_{t-1}] >= kl(m1||m0) = I.

If tau_A is the tuned CUSUM crossing time at threshold A, positive log overshoot is bounded by b=log(m1/m0), so, conditional on no earlier intervention,

E[(tau_A-nu+1)^+] <= [log A + b]/I.

For a mixture component with weight w_k, replace A by A/w_k. Thus unknown effect size adds log(1/w_k), equal to log K under equal K-component weights.

## T5 — sharp information lower bound

Existing bounded-mean quickest-detection theory gives, for post-change law Q and null class P0,

inf_{tau: ARL(tau)>=A} J_Q(tau)
 >= (1-o(1))*log(A)/KL_inf(Q,P0),

with matching first-order achievability for the canonical bounded-mean problem. Therefore the underlying single-alpha detector can be first-order minimax optimal. The complete reversible multi-alpha controller is not claimed to be globally minimax.

## T6 — first-order economic delay regret

If the stale allocation loses c_Q units of material portfolio utility per delayed observation,

R_Q(tau)=c_Q*J_Q(tau).

Hence every ARL-A detector satisfies

liminf R_Q(tau_A)/log(A) >= c_Q/KL_inf(Q,P0),

and a first-order optimal detector attains

R_Q^*(A)=(1+o(1))*c_Q*log(A)/KL_inf(Q,P0).

In the local Gaussian benchmark with post-change mean -g and variance sigma^2,

KL = g^2/(2*sigma^2)

and, with c_Q=g,

R^*(A)=(1+o(1))*[2*sigma^2/g]*log(A).

## T7 — repeated PARK/REVIVE

For S genuine material transitions separated by regimes long enough for the previous correction to complete, and episode-specific material losses c_s and information numbers I_s,

R_true=(1+o(1))*log(A)*sum_s c_s/I_s,

conditional on no intervening false allocation change. False interventions and switching costs are separate terms; ARL alone does not control their repeated economic cost.

## T8 — cost-weighted economic error over patience

Let c_j>0 denote the normalized economic cost of a false intervention and w_j>0, sum_j w_j=1, pre-specified risk-budget weights. Declare j if

M_{j,t} >= c_j/(beta*w_j).

Then for any stopping time tau,

E[sum_j c_j 1{false declaration j at tau}] <= beta*E[tau],

under the global-filtration e-detector assumptions. This is a cost-weighted specialization of e-detector Bonferroni/EOP logic.

## What is and is not new

New finance framing:
- portfolio-relative alpha value rather than standalone mean;
- reversible funded/shadow lifecycle;
- explicit economic indifference region;
- information-to-portfolio-regret translation and governance interpretation.

Borrowed statistical frontier:
- e-detectors/e-CUSUM;
- e-d-BH and EOP;
- sharp bounded-mean first-order information bounds.

The paper should be sold as a rigorous finance/statistics application and framework, not as the invention of e-CUSUM or e-BH.
