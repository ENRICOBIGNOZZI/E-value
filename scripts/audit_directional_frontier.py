#!/usr/bin/env python3
"""Deterministic checks of the utility frontier and its rare-loss embedding.

No random observations are generated. These finite identity checks do not
prove the total-variation, sequential validity, or asymptotic arguments.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.integrate import quad
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]


def main():
    checks = []; examples = []

    def check(name, observed, expected, atol=2e-10, rtol=2e-10):
        if not np.isclose(observed, expected, atol=atol, rtol=rtol):
            raise ArithmeticError((name, observed, expected))
        checks.append(dict(identity=name, observed=float(observed), expected=float(expected),
                           absolute_error=float(abs(observed-expected))))

    for gamma in (.5,1.,5.):
        for cap in (.1,1.,9.):
            threshold = gamma*cap/2
            mean = min(threshold/2, 1/(2*gamma), np.sqrt(cap)/4)
            variance = min(mean/gamma, (cap-mean**2)/2, mean**2/4)
            cases = [('below',mean,variance)]
            if threshold**2 < cap:
                cases.append(('boundary',threshold,(cap-threshold**2)/4))
                above = (threshold+np.sqrt(cap))/2
                cases.append(('above',above,(cap-above**2)/4))
            for kind, mu, variance in cases:
                sd = np.sqrt(variance)
                m2 = quad(lambda z: (mu+sd*z)**2*norm.pdf(z),-12,12,epsabs=1e-12)[0]
                m4 = quad(lambda z: (mu+sd*z)**4*norm.pdf(z),-12,12,epsabs=1e-12)[0]
                utility = mu-gamma*m2/2
                assert m2 <= cap+1e-12 and utility > 0
                for epsilon in (.1,.001,1e-6,1e-9,1e-12):
                    point = -np.sqrt((cap-(1-epsilon)*m2)/epsilon)
                    # Direct integrals under the mixture, separate from its
                    # compact moment/utility expressions in the proof.
                    q2 = (1-epsilon)*quad(lambda z: (mu+sd*z)**2*norm.pdf(z),-12,12)[0]+epsilon*point**2
                    qu = (1-epsilon)*quad(lambda z: ((mu+sd*z)-gamma*(mu+sd*z)**2/2)*norm.pdf(z),-12,12)[0]+epsilon*(point-gamma*point**2/2)
                    expected = (1-epsilon)*mu-np.sqrt(epsilon*(cap-(1-epsilon)*m2))-gamma*cap/2
                    check(f'second cap gamma={gamma} K={cap} case={kind} eps={epsilon}',q2,cap)
                    check(f'null utility gamma={gamma} K={cap} case={kind} eps={epsilon}',qu,expected)
                    if kind != 'above':
                        assert qu < 0
                    elif epsilon == 1e-12:
                        assert qu > 0  # This construction is not a null beyond the frontier.
                gap = cap-m2; epsilon = 1e-12
                q4 = (1-epsilon)*m4+(cap-(1-epsilon)*m2)**2/epsilon
                check(f'fourth-moment divergence coefficient gamma={gamma} K={cap} case={kind}',epsilon*q4,gap**2,rtol=1e-8)
                examples.append(dict(gamma=gamma,public_second=cap,region=kind,
                    mean=mu,raw_second=m2,positive_utility=utility,surrogate_mean=mu-threshold))

    # Check the utility-moment envelope for return moments strictly above two.
    points = np.array([-3.,-.4,0.,.5,2.]); probabilities = np.array([.03,.17,.25,.4,.15])
    for gamma in (.5,1.,5.):
        utility = points-gamma*points**2/2
        for p in (1.05,1.25,1.5,2.,3.):
            moment = float(probabilities @ abs(points)**(2*p))
            envelope = (moment**(1/(2*p))+gamma*moment**(1/p)/2)**p
            actual = float(probabilities @ abs(utility)**p)
            assert actual <= envelope+1e-12
            checks.append(dict(identity=f'utility p-moment bound gamma={gamma} p={p}',
                               observed=actual,upper_bound=envelope))

    # Explicit return representation of a deterministic positive utility and
    # of the rare negative utility used in the previous score-class bound.
    for gamma in (1.,5.):
        for fraction in (.01,.1,.5,1.):
            delta = fraction/(2*gamma)
            positive = 2*delta/(1+np.sqrt(1-2*gamma*delta))
            check(f'positive utility embedding gamma={gamma} fraction={fraction}',positive-gamma*positive**2/2,delta)
            for epsilon in (.1,.001,1e-6):
                loss = delta*(1-epsilon)/epsilon
                negative = -2*loss/(1+np.sqrt(1+2*gamma*loss))
                y = negative-gamma*negative**2/2
                check(f'negative utility embedding gamma={gamma} fraction={fraction} eps={epsilon}',y,-loss)
                check(f'zero null utility gamma={gamma} fraction={fraction} eps={epsilon}',(1-epsilon)*delta+epsilon*y,0.)

    scores = np.array([-.5,5.]); probability = np.array([.9,.1])
    assert probability @ scores > 0
    growth = [(float(2.**(-j-1)),float(probability @ np.log1p(2.**(-j-1)*scores))) for j in range(12)]
    assert growth[0][1] < 0 and any(value > 0 for _,value in growth)
    sources = ['scripts/audit_directional_frontier.py','reports/directional_frontier_proof_audit.md',
               'scripts/plot_directional_frontier.py',
               'paper/sections/13_directional_information.tex','paper/sections/14_directional_proofs.tex',
               'paper/sections/07_certified_tails.tex']
    report = dict(complete=True,deterministic_checks=len(checks),checks=checks,
        frontier_examples=examples,cash_positive_mean_fixed_bet_counterexample=dict(
            scores=scores.tolist(),probabilities=probability.tolist(),mean=float(probability@scores),growth_by_dyadic_stake=growth),
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},
        scope='Finite deterministic quadrature/identity checks only; no new simulation paths, test-size estimate or proof of sequential/asymptotic claims. Financial design unchanged.')
    (ROOT/'reports/directional_frontier_checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('checks','frontier_examples','source_sha256','cash_positive_mean_fixed_bet_counterexample')},indent=2))


if __name__ == '__main__':
    main()
