"""Deterministic quadrature checks of the cash-PARK proof's identities.

These finite numerical checks support the algebraic audit, not the almost-sure
or stopping-time proofs. No simulation seeds or financial code are involved.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.integrate import quad
from scipy.special import betaln
from scipy.stats import chi, norm


def main():
    checks = []

    def compare(name, observed, expected, atol=2e-10, rtol=2e-9):
        if not np.isclose(observed, expected, atol=atol, rtol=rtol):
            raise ArithmeticError((name, observed, expected))
        checks.append({'identity': name, 'observed': float(observed),
                       'expected': float(expected), 'absolute_error': float(abs(observed-expected))})

    # Gaussian density integration is independent of the study's polynomial
    # log-density formula. Opposite signs test the symmetry of the null kernel.
    for a in (-3., -.5, -.01, 0., .01, .5, 3.):
        mean = a/(1+a*a)
        sd = 1/(1+a*a)
        def under_q(function):
            return quad(lambda z: function(mean+sd*z)*norm.pdf(z), -12, 12,
                        epsabs=1e-11, epsrel=1e-11)[0]
        raw2 = under_q(lambda z: z*z)
        raw4 = under_q(lambda z: z**4)
        compare(f'Q second moment a={a}', raw2, 1/(1+a*a))
        compare(f'Q fourth moment a={a}', raw4, (3+6*a*a+a**4)/(1+a*a)**4)
        compare(f'Q linear factor mean a={a}', under_q(lambda z: 1-a*z+a*a*z*z), 1.)
        if raw2 > 1+1e-10 or raw4 > 3+1e-10:
            raise ArithmeticError('The constructed null breaches its public moments')
        kl = quad(lambda z: (norm.logpdf(z)-norm.logpdf(z,loc=mean,scale=sd))*norm.pdf(z),
                  -12,12,epsabs=1e-11,epsrel=1e-11)[0]
        compare(f'P/Q expected log ratio a={a}', kl, -np.log1p(a*a)+1.5*a*a+.5*a**4)

    # Integrate length and direction separately; compare against the rational
    # inverse raw-moment formulas used to bound fitted-target moments.
    for k in (5,8,32,128):
        for p in (2,3,4):
            radial = quad(lambda x: x**(-p)*chi.pdf(x,k),0,np.inf,
                          epsabs=1e-11,epsrel=1e-11)[0]
            angular = quad(lambda u: np.exp((p/2-.5)*np.log(u)+
                          ((k-1)/2-1)*np.log1p(-u)-betaln(.5,(k-1)/2)),
                          0,1,epsabs=1e-11,epsrel=1e-11)[0]
            for sigma in (.5,1.,2.):
                moment = k**(p/2)*radial*angular/sigma**p
                if p == 2:
                    exact = 1/(sigma**2*(k-2))
                elif p == 3:
                    exact = 2*np.sqrt(2)*k**1.5/(np.sqrt(np.pi)*sigma**3*(k-3)*(k-1)*(k+1))
                else:
                    exact = 3*k/(sigma**4*(k-4)*(k-2)*(k+2))
                compare(f'Inverse-risk moment k={k} p={p} sigma={sigma}', moment, exact)

    # Second-order rates via symmetric quadrature, avoiding cancellation of
    # odd terms. These are local numerical checks, not asymptotic proofs.
    a = 1e-4
    linear = quad(lambda z: .5*(np.log1p(-a*z+a*a*z*z)+np.log1p(a*z+a*a*z*z))*norm.pdf(z),
                  -12,12,epsabs=1e-16,epsrel=1e-11)[0]/(a*a)
    compare('Local linear growth / a^2',linear,.5,atol=1e-6,rtol=0)
    def catoni(x):
        return np.sign(x)*np.log1p(abs(x)+x*x/2)
    transformed = quad(lambda z: .5*(catoni(-a*z+a*a*z*z)+catoni(a*z+a*a*z*z))*norm.pdf(z),
                       -12,12,epsabs=1e-16,epsrel=1e-11)[0]
    catoni_rate = transformed/(a*a)-.5*(1+abs(a)*np.sqrt(6))**2
    compare('Local geometric Catoni growth / a^2',catoni_rate,.5,atol=3e-4,rtol=0)

    root = Path(__file__).resolve().parents[1]
    sources = ['paper/sections/11_vanishing_gains.tex', 'paper/sections/12_vanishing_proofs.tex',
               'scripts/audit_vanishing_theory.py']
    report = {'complete': True, 'deterministic_scalar_checks': len(checks),
              'maximum_identity_error_excluding_local_rate_approximations': max(c['absolute_error'] for c in checks[:-2]),
              'checks': checks,
              'source_sha256': {p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in sources},
              'scope': 'Deterministic quadrature of Gaussian null moments, log-density ratios, inverse-risk moments and local growth coefficients. Finite numerical checks do not prove asymptotics, optimality or stopping-time claims.'}
    (root/'reports/vanishing_gain_results/theory_quadrature.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k: v for k,v in report.items() if k not in ('checks','source_sha256')},indent=2))


if __name__ == '__main__':
    main()
