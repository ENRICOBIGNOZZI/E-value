"""Deterministic quadrature checks of the cash-PARK proof's identities.

These finite numerical checks support the algebraic audit, not the almost-sure
or stopping-time proofs. No simulation seeds or financial code are involved.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.integrate import quad
from scipy.special import betaln, lambertw
from scipy.optimize import brentq
from scipy.stats import chi, norm


def main():
    checks = []
    root = Path(__file__).resolve().parents[1]

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

    # The realized-minus-conditional utility is a martingale. Integrate its
    # mean and variance independently of the proof's Gaussian moment formula.
    for gamma in (.5, 1., 5.):
        for sigma in (.5, 1., 2.):
            for weight in (-.5, -.05, 0., .05, .5):
                delta = gamma*sigma*sigma*weight*weight/2
                def score(z):
                    return -weight*sigma*z+gamma*weight*weight*sigma*sigma*z*z/2
                mean = quad(lambda z: score(z)*norm.pdf(z), -12, 12,
                            epsabs=1e-12, epsrel=1e-11)[0]
                variance = quad(lambda z: (score(z)-delta)**2*norm.pdf(z), -12, 12,
                                epsabs=1e-12, epsrel=1e-11)[0]
                compare(f'P cash utility mean gamma={gamma} sigma={sigma} w={weight}',
                        mean, delta)
                compare(f'P centered utility variance gamma={gamma} sigma={sigma} w={weight}',
                        variance, sigma*sigma*weight*weight+gamma*gamma*sigma**4*weight**4/2)

    def inverse_risk_sum(n):
        return (1/(n-4)+1/(n-3))/3+sum(1/j for j in range(n-2,n+2))/12

    # A finite partial sum checks the telescoping identity; the limiting
    # series and the Ville argument themselves are established in the proof.
    for n in (5,8,32,128):
        k = np.arange(n,10001,dtype=float)
        observed = float(np.sum(k/((k-4)*(k-2)*(k+2))))
        compare(f'Inverse-risk fourth-moment telescoping n0={n}',observed,
                inverse_risk_sum(n)-inverse_risk_sum(10001))

    # Integrate actual one-step factors under P. These finite inequalities
    # support, but do not prove, the policy-uniform sequential upper bound.
    for gamma,sigma,limit in ((1.,1.,.5),(5.,.2,1.),(.5,2.,.25)):
        for multiplier in (3.,6.):
            fourth = multiplier*sigma**4
            nu2 = limit**2*(sigma+gamma*limit*np.sqrt(fourth)/2)**2
            gap = nu2-(sigma*sigma*limit*limit+.75*gamma*gamma*sigma**4*limit**4)
            expected_gap = gamma*sigma*limit**3*np.sqrt(fourth)+gamma*gamma*limit**4*(fourth-3*sigma**4)/4
            assert gap > 0
            compare(f'Positive constant-certificate gap gamma={gamma} sigma={sigma} L={limit} M4={multiplier}',gap,expected_gap)
            cap = 1/(2*np.sqrt(nu2))
            for weight in (-limit,-limit/4,0.,limit/4,limit):
                delta = gamma*sigma*sigma*weight*weight/2
                bound = float(np.exp(delta*delta/(2*gap)))
                for stake in sorted({0.,float(delta/gap),float(cap),float(4*cap)}):
                    def factor(z):
                        score = -weight*sigma*z+gamma*weight*weight*sigma*sigma*z*z/2
                        x = stake*score
                        phi = np.sign(x)*np.log1p(abs(x)+x*x/2)
                        return np.exp(phi-stake*stake*nu2/2)
                    actual = quad(lambda z: factor(z)*norm.pdf(z),-12,12,epsabs=1e-11,epsrel=1e-11)[0]
                    if actual > bound+2e-10:
                        raise ArithmeticError('Compensating factor bound fails')
                    checks.append(dict(identity=f'P factor bound gamma={gamma} sigma={sigma} L={limit} M4={multiplier} w={weight} lambda={stake}',
                        observed=float(actual),expected_upper_bound=bound,numerical_slack=float(bound-actual)))

    cfg_path = root/'reports/vanishing_gain_results/config_frozen.json'
    cfg = json.loads(cfg_path.read_text())
    gamma,sigma,limit,fourth = cfg['gamma'],cfg['sigma'],cfg['leverage'],cfg['public_fourth']
    assert cfg['public_second']==sigma*sigma and fourth>=3*sigma**4 and cfg['training']>=5
    nu2 = limit**2*(sigma+gamma*limit*np.sqrt(fourth)/2)**2
    gap = nu2-(sigma*sigma*limit*limit+.75*gamma*gamma*sigma**4*limit**4)
    budget = 3/(8*gamma*gamma*gap)*inverse_risk_sum(cfg['training'])
    bounds = []
    for alpha in cfg['levels']:
        r = float(2*lambertw(.5*np.sqrt(budget/alpha)).real)
        root_r = brentq(lambda x: alpha*np.exp(x)-budget/(x*x),1e-8,50)
        compare(f'Uniform-family r optimizer alpha={alpha}',r,root_r)
        compare(f'Uniform-family derivative at optimum alpha={alpha}',alpha*np.exp(r)-budget/(r*r),0.)
        bounds.append(dict(alpha=alpha,compensator_cutoff_optimizer=r,
                           ever_power_upper_bound=float(min(1.,alpha*np.exp(r)+budget/r))))

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

    sources = ['paper/sections/11_vanishing_gains.tex', 'paper/sections/12_vanishing_proofs.tex',
               'paper/sections/13_directional_information.tex',
               'scripts/audit_vanishing_theory.py']
    report = {'complete': True, 'deterministic_scalar_checks': len(checks),
              'deterministic_inequality_checks':sum('expected_upper_bound' in c for c in checks),
              'maximum_identity_error_excluding_local_rate_approximations': max(c['absolute_error'] for c in checks[:-2] if 'absolute_error' in c),
              'checks': checks,
              'source_sha256': {p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in sources},
              'scope': 'Finite deterministic identities and one-step inequalities for Gaussian null/alternative moments, log-density ratios, inverse-risk moments, local growth and the uniform constant-certificate family bound. Checks do not prove the sequential, asymptotic or stopping-time statements.'}
    (root/'reports/vanishing_gain_results/theory_quadrature.json').write_text(json.dumps(report,indent=2)+'\n')
    family = dict(complete=True,nu2=float(nu2),uniform_second_moment_gap=float(gap),
        expected_compensator_budget_upper_bound=float(budget),bounds=bounds,
        config_sha256=hashlib.sha256(cfg_path.read_bytes()).hexdigest(),
        source_sha256=report['source_sha256'],
        scope='Deterministic upper bounds, not observed powers, for all finite nonnegative predictable Catoni bets with the fixed constant certificate in the costless Gaussian estimated-policy instance. Supremum of ever-crossing probabilities, including alpha-dependent rules. No new paths or financial-DGP claim.')
    (root/'reports/vanishing_gain_results/uniform_family_bound.json').write_text(json.dumps(family,indent=2)+'\n')
    print(json.dumps({k: v for k,v in report.items() if k not in ('checks','source_sha256')},indent=2))


if __name__ == '__main__':
    main()
