#!/usr/bin/env python3
"""Finite deterministic checks of the estimated-policy geometry/bet expansion.

No random paths are generated. These checks do not prove the martingale,
weighted-Cesaro, first-crossing or almost-sure statements in Proposition 19.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.integrate import quad
from scipy.optimize import minimize_scalar
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]


def main():
    checks = []
    local = []

    def check(name, observed, expected, atol=2e-10):
        if not np.isclose(observed, expected, atol=atol, rtol=2e-9):
            raise ArithmeticError((name, observed, expected))
        checks.append(dict(identity=name, numerical_optimizer=name.startswith('quadratic optimizer'), observed=float(observed),
                           expected=float(expected), absolute_error=float(abs(observed-expected))))

    for gamma, sigma, ridge in ((1., 1., 0.), (5., .2, .1), (.5, 2., 1.)):
        risk = sigma*sigma+ridge
        integrated_rate = sigma*sigma/(gamma*gamma*risk*risk)
        kappa = sigma**4/(8*risk*risk)
        benefit_rate = gamma*sigma*sigma*integrated_rate/2
        for q in (1., 1.5, 2., 4.):
            second = q*sigma*sigma
            fourth = 6*sigma**4
            oracle = gamma/(2*q)

            def coefficient(stake):
                return gamma*sigma*sigma*stake/2-second*stake*stake/2

            numeric = minimize_scalar(lambda stake: -coefficient(stake),
                                      bounds=(0., gamma), method='bounded',
                                      options={'xatol': 1e-12})
            assert numeric.success
            # A flat quadratic objective cannot locate its optimizer beyond
            # O(sqrt(machine epsilon)) even with a smaller xatol. Its attained
            # objective is checked separately at the identity tolerance.
            check(f'quadratic optimizer gamma={gamma} sigma={sigma} ridge={ridge} q={q}',
                  numeric.x, oracle, atol=1e-7*max(1., gamma))
            check(f'optimal log rate gamma={gamma} sigma={sigma} ridge={ridge} q={q}',
                  coefficient(numeric.x)*integrated_rate, kappa/q)
            check(f'unadjusted log rate gamma={gamma} sigma={sigma} ridge={ridge} q={q}',
                  coefficient(gamma/2)*integrated_rate, kappa*(2-q))
            check(f'attained utility coefficient gamma={gamma} sigma={sigma} ridge={ridge} q={q}',
                  benefit_rate/(kappa/q), 4*q/gamma)
            check(f'past-second-moment limit gamma={gamma} sigma={sigma} q={q}',
                  gamma*min(sigma*sigma/second, 1.)/2, oracle)

            # Symmetric quadrature cancels the leading odd term without
            # subtracting two nearly equal full normal integrals.
            weight = 1e-4
            variance_bound = weight*weight*(np.sqrt(second)+gamma*abs(weight)*np.sqrt(fourth)/2)**2
            for stake in sorted({0., oracle, gamma/2, 1.5*oracle}):
                def influence(z):
                    score = -weight*sigma*z+gamma*weight*weight*sigma*sigma*z*z/2
                    x = stake*score
                    return np.sign(x)*np.log1p(abs(x)+x*x/2)

                transformed = quad(lambda z: (influence(z)+influence(-z))*norm.pdf(z),
                                   0., 12., epsabs=1e-16, epsrel=1e-11)[0]
                observed = (transformed-stake*stake*variance_bound/2)/(weight*weight)
                # At this finite weight the known penalty has an explicit
                # O(|w|) correction; compare to that finite-weight prediction.
                predicted = coefficient(stake)-stake*stake*(variance_bound/(weight*weight)-second)/2
                error = abs(observed-predicted)
                if error > 2e-6*(1+abs(predicted)):
                    raise ArithmeticError(('local Catoni expansion', gamma, sigma, q, stake, observed, predicted))
                local.append(dict(gamma=gamma, sigma=sigma, public_second_ratio=q,
                                  stake=float(stake), weight=weight,
                                  observed_log_factor_per_weight_squared=float(observed),
                                  finite_weight_prediction=float(predicted),
                                  absolute_local_approximation_error=float(error)))

    sources = ['scripts/audit_geometric_bet_theory.py',
               'paper/sections/11_vanishing_gains.tex',
               'paper/sections/12_vanishing_proofs.tex']
    examples = [dict(public_second_ratio=q, oracle_stake=1/(2*q),
                     optimized_log_rate=.125/q, unadjusted_log_rate=.125*(2-q),
                     attained_confidence_time_exponent=8*q,
                     attained_cumulative_utility_coefficient=4*q)
                for q in (1., 1.5, 2., 4.)]
    identities = [x for x in checks if not x['numerical_optimizer']]
    optimizers = [x for x in checks if x['numerical_optimizer']]
    report = dict(complete=True, deterministic_identity_checks=len(identities),
                  deterministic_optimizer_checks=len(optimizers),
                  deterministic_local_quadrature_checks=len(local),
                  maximum_identity_error=max(x['absolute_error'] for x in identities),
                  maximum_optimizer_location_error=max(x['absolute_error'] for x in optimizers),
                  maximum_local_approximation_error=max(x['absolute_local_approximation_error'] for x in local),
                  optimizer_location_tolerance='1e-7 * max(1, gamma), plus rtol=2e-9; attained objective checked separately at the identity tolerance',
                  local_approximation_tolerance='2e-6 * (1 + abs(finite_weight_prediction))',
                  checks=checks, local_quadrature=local,
                  analytic_examples_gamma_sigma_one_ridge_zero=examples,
                  source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},
                  scope='Finite deterministic identities, scalar quadratic optimization and local Gaussian quadrature only. No new random paths, observed power, proof of asymptotics, expected stopped costs or financial-DGP result. The optimum is an asymptotic log-rate criterion, not deadline power.')
    destination = ROOT/'reports/vanishing_gain_results/geometric_bet_theory.json'
    destination.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in
                      ('checks','local_quadrature','source_sha256')}, indent=2))


if __name__ == '__main__':
    main()
