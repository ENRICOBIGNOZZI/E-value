# V4 total-loss theorem and proof

This is an upper bound for a precisely specified model, not a proof of global minimax portfolio regret. All eight results and all proofs appear in Appendix A of the full 31-page V4 manuscript delivered with the conversation.

## Model

There are M fully observed exogenous shadow gain streams G[j,t] in [-B,B]. Their joint-past conditional means theta[j,t] have magnitudes in [g,Gbar], where 0<g<=Gbar<=B. Their signs follow a deterministic piecewise-constant schedule with at most S total sign changes. Let I0 bound initial mismatches. Set epsilon=g/B>h.

The binary learner uses Z=G/B, the directional input X=((1-2a)Z-h)/(1+h), fixed-bet e-CUSUM mixtures, full-batch e-detector BH at every observation, and resets all capital in each selected stream. Accepted changes take effect at the next observation. Switching cost is at most kappa utility units per implemented flip.

For component k, define

```
u=(1-h)/(1+h)
d_k=(1+epsilon)/2*log(1+lambda_k*u)+(1-epsilon)/2*log(1-lambda_k)
b_k=log(1+lambda_k*u)
D*=min_{k:d_k>0} [log(A*M/w_k)+b_k]/d_k.
```

The expected frictionless-oracle loss, including learner switching charges, satisfies

```
Rbar_T <= Gbar*D* (I0+2*S+M*T/A)
          + kappa (I0+3*S+2*M*T/A).
```

It can be capped by MT(Gbar+kappa). It also upper-bounds regret versus the clairvoyant cost-aware oracle because that oracle cannot exceed the frictionless sign oracle. No minimum dwell length is required for this upper bound, although short regimes and weak gaps can make it loose or vacuous.

## Proof

1. During a correct-state interval the directional conditional null holds. A fresh such interval starts with zero detector wealth. The e-CUSUM mixture has conditional expected wealth increment at most one: E[C_t|past] <= C_{t-1}+1.

2. Every selected detector has wealth at least AM/r >= A. At a false exit this capital is discarded by the actual reset. At a true boundary or the final horizon we can discard residual nonnegative wealth virtually for the accounting. Summing drift inequalities across all disjoint fresh correct-state intervals and all streams yields E[F_fresh] <= MT/A. No independence across streams is needed.

3. A true sign change may make a previously wrong action correct while retaining alternative evidence. Charge the first false exit from that contaminated correct interval to the true sign change. After an actual correcting switch the detector resets and later correct intervals in that regime are fresh. Thus F_total <= F_fresh+S, pathwise.

4. Split wrong-state spells at every true sign boundary. Each spell starts at initialization, a true boundary, or a false switch, so the number of spells is at most I0+S+F_total.

5. During a wrong spell, the signed score has conditional mean at least epsilon. Concavity of log(1+lambda X) gives conditional log growth at least d_k. A CUSUM component dominates a fresh product started at any date. A detector value at least AM must be selected by full-batch e-d-BH; before correction, its component product therefore has log value below log(AM/w_k). The final increment is at most b_k. Stopped conditional-drift summation bounds expected truncated spell length by D*. This bound holds conditionally at the random start of each spell.

6. Expected wrong-state occupancy is consequently at most D*(I0+2*S+MT/A). Each wrong observation loses at most Gbar.

7. Binary-state accounting bounds correcting switches by I0+S+F_total. Total switches are at most I0+S+2*F_total, hence their expectation is at most I0+3*S+2*MT/A. Multiplying by kappa and adding the occupancy loss proves the bound.

## Crucial limitations

- The proof does not pretend that an episode-level EOP theorem controls every repeated current-state false discovery.
- The gains and their sign-change budget are exogenous. Local marginal scores in an evolving multi-factor book need not have that property.
- A clipped raw financial score is a different conditional-mean target. Raw-dollar transfer needs tail and shadow-bias bounds and preservation of the mean margin.
- Continuous screening and reset rules are part of the theorem. A month-end-only implementation needs a separate delay argument.
- There is no matching total-regret lower bound here. The single-stream first-order information benchmark is inherited from quickest-detection theory, not a proof of full policy optimality.

## Interaction certificate

For conditional binary-book utility F(a)=F0+ell'a-gamma/2*a'Q*a and d=b-a, with Q the conditional second-moment matrix,

```
F(b)-F(a)=sum_j d_j theta_j(a_-j)-gamma*sum_{j<k}d_j*d_k*Q_jk.
```

Hence global opportunity loss is bounded by the sum of positive local toggle opportunities plus gamma*sum_{j<k}|Q_jk|. This remainder may be large. With ell=(.001,.001), gamma=8, and Q=[[.0004,-.00036],[-.00036,.0004]], each strategy alone has value -.0006, whereas the pair has value .00168. A local all-parked gate can miss the jointly useful hedge.

## Attribution

The e-detector machinery is due to Shin, Ramdas and Rinaldo (2024). Multi-stream e-d-BH/EOP is developed by Dandapanthula and Ramdas (arXiv:2501.04130). The sharp bounded-mean information benchmark is in Ram and Ramdas (arXiv:2602.05272). Portfolio-relative relevance and mean-variance spanning are existing financial ideas; see also Liao, Wang and Zhou (arXiv:2501.19213). This work uses those tools and derives the stated reversible accounting bound; it does not claim to have invented them.
