"""Finite deterministic checks for the matrix cash-PARK derivation.

No random paths, optimizer retuning or verification of asymptotic convergence.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.integrate import quad
from scipy.optimize import minimize_scalar
from scipy.stats import multivariate_normal

ROOT = Path(__file__).resolve().parents[1]


def gaussian_ratio_integral(a, b):
    """Deterministic Gaussian-Laplace integral, restricted to B's range."""
    eigenvalues, vectors = np.linalg.eigh(b)
    positive = eigenvalues > 1e-12*max(1., float(eigenvalues.max()))
    basis = vectors[:, positive]
    values = eigenvalues[positive]
    rotated = basis.T@a@basis
    if not len(values) or np.linalg.norm(a-basis@rotated@basis.T) > 1e-10*max(1., np.linalg.norm(a)):
        raise ArithmeticError('Unresolved matrix-ratio support')
    def integrand(t):
        inverse = 1/(1+2*t*values)
        trace = float(np.diag(rotated)@inverse)
        trace_square = float(np.sum(rotated*rotated*inverse[:, None]*inverse[None, :]))
        return (2*trace_square+trace*trace)*np.exp(-.5*np.log1p(2*t*values).sum())
    return quad(integrand, 0., np.inf, epsabs=1e-11, epsrel=1e-11, limit=300)


def audit(root):
    identities, inequalities, optimizers, ratio_cases = [], [], [], []

    def equal(name, observed, expected, tolerance=2e-10):
        error = float(np.max(np.abs(np.asarray(observed)-np.asarray(expected))))
        scale = max(1., float(np.max(np.abs(np.asarray(expected)))))
        if not np.isfinite(error) or error > tolerance*scale:
            raise ArithmeticError((name, error, scale))
        identities.append(dict(name=name, absolute_error=error, scaled_error=error/scale))

    def nonnegative(name, value, tolerance=2e-10):
        value = float(value)
        if not np.isfinite(value) or value < -tolerance:
            raise ArithmeticError((name, value))
        inequalities.append(dict(name=name, minimum_gap=value))

    cases = {
        'scalar': np.array([[1.3]]),
        'correlated': np.array([[1.2, .3], [.3, .7]]),
        'rank_one': np.ones((3, 3)),
        'singular_diagonal': np.diag([1., 0., 2.]),
        'toeplitz': .4**np.abs(np.arange(5)[:, None]-np.arange(5)[None, :]),
    }
    for name, sigma in cases.items():
        p = len(sigma)
        eigenvalues, vectors = np.linalg.eigh(sigma)
        square_root = (vectors*np.sqrt(np.maximum(eigenvalues, 0)))@vectors.T
        for rho in (0., .35, 1.):
            for ridge in (.1, .6):
                h = (1-rho)*sigma+rho*np.diag(np.diag(sigma))+ridge*np.eye(p)
                inverse = np.linalg.inv(h)
                b = square_root@inverse@sigma@inverse@square_root
                chi = float(np.trace(inverse@sigma@inverse@sigma))
                equal(f'{name} trace factor rho={rho} r={ridge}', chi, np.trace(b))
                equal(f'{name} Frobenius factor rho={rho} r={ridge}', chi,
                      np.linalg.norm(square_root@inverse@square_root, 'fro')**2)
                nonnegative(f'{name} positive learning factor rho={rho} r={ridge}', chi)
                # Expand the cross-covariance pairing independently by indices.
                for i, j in ((1, 1), (2, 7)):
                    cross = i*np.eye(p)
                    pairings = sum(b[a, c]*b[d, e]*(cross[a, d]*cross[c, e]+cross[a, e]*cross[c, d])
                                   for a in range(p) for c in range(p)
                                   for d in range(p) for e in range(p))
                    equal(f'{name} Gaussian quadratic covariance {i},{j} rho={rho} r={ridge}',
                          pairings, 2*i*i*np.trace(b@b))
                for gamma in (.7, 2.):
                    kappa = chi/8
                    equal(f'{name} stopped utility coefficient gamma={gamma} rho={rho} r={ridge}',
                          (chi/(2*gamma))/kappa, 4/gamma)

        gamma = 1.3
        base = np.arange(1., p+1); base *= .5/base.sum()
        weights = [np.zeros(p), base, base*((-1.)**np.arange(p))]
        if name == 'rank_one':
            weights.append(np.array([.5, -.5, 0.]))
        if name == 'singular_diagonal':
            weights.append(np.array([0., .5, 0.]))
        probes = [*np.eye(p), np.ones(p), (-1.)**np.arange(p)]
        points = [np.zeros(p), *np.eye(p), np.arange(1., p+1)/p]
        for index, w in enumerate(weights):
            v = float(w@sigma@w)
            a = gamma*np.sqrt(v)/2
            if v == 0:
                mu = np.zeros(p); covariance = sigma.copy()
            else:
                projection = np.outer(sigma@w, sigma@w)/v
                mu = gamma*sigma@w/(2*(1+a*a))
                covariance = sigma-(1-(1+a*a)**-2)*projection
            raw = covariance+np.outer(mu, mu)
            equal(f'{name} null raw matrix w={index}', raw,
                  sigma if v == 0 else sigma-a*a/(1+a*a)*projection)
            equal(f'{name} boundary utility w={index}', -w@mu+gamma/2*(w@raw@w), 0.)
            nonnegative(f'{name} null covariance PSD w={index}', np.linalg.eigvalsh(covariance).min())
            nonnegative(f'{name} raw-moment Loewner gap w={index}', np.linalg.eigvalsh(sigma-raw).min())
            for j, direction in enumerate(probes):
                mean = float(direction@mu); variance = float(direction@covariance@direction)
                second = float(direction@raw@direction)
                fourth = mean**4+6*mean*mean*variance+3*variance*variance
                equal(f'{name} fourth-moment identity w={index} b={j}', fourth, 3*second*second-2*mean**4)
                nonnegative(f'{name} directional fourth cap w={index} b={j}',
                            3*float(direction@sigma@direction)**2-fourth)
            p_law = multivariate_normal(np.zeros(p), sigma, allow_singular=True)
            q_law = multivariate_normal(mu, covariance, allow_singular=True)
            for j, point in enumerate(points):
                x = square_root@point
                z = 0. if v == 0 else float(w@x/np.sqrt(v))
                scalar_lr = -np.log1p(a*a)+(a*a+a**4/2)*z*z-a*(1+a*a)*z+a*a/2
                equal(f'{name} full Gaussian density ratio w={index} x={j}',
                      p_law.logpdf(x)-q_law.logpdf(x), scalar_lr)
                factor = 1-gamma*(w@x)/2+gamma*gamma*(w@x)**2/4
                equal(f'{name} linear projection factor w={index} x={j}', factor, 1-a*z+a*a*z*z)
                nonnegative(f'{name} safe factor w={index} x={j}', factor-.75)
            equal(f'{name} score conditional variance w={index}',
                  v+3*gamma*gamma*v*v/4-(gamma*v/2)**2, v+gamma*gamma*v*v/2)

        for m in (1, 32, 252):
            component_sum = sum(sigma[i, i]*sigma[j, j]+2*sigma[i, j]**2
                                for i in range(p) for j in range(p))/m**2
            equal(f'{name} Gaussian mean fourth norm m={m}', component_sum,
                  (np.trace(sigma)**2+2*np.trace(sigma@sigma))/m**2)

        # A general anisotropic cap, with an independently evaluated Gaussian
        # ratio and a scalar optimizer for the entire constant-stake class.
        h = .65*sigma+.35*np.diag(np.diag(sigma))+.3*np.eye(p)
        inverse = np.linalg.inv(h)
        a_matrix = square_root@inverse@sigma@inverse@square_root
        cap = sigma+np.diag(np.linspace(.3, 1.5, p))
        b_matrix = square_root@inverse@cap@inverse@square_root
        chi, chi_cap = float(np.trace(a_matrix)), float(np.trace(b_matrix))
        psi, error_estimate = gaussian_ratio_integral(a_matrix, b_matrix)
        nonnegative(f'{name} adaptive improvement over best constant', psi-chi*chi/chi_cap)
        nonnegative(f'{name} geometric information-rate ceiling', chi-psi)
        objective = lambda lam: -(chi*lam/(2*gamma)-chi_cap*lam*lam/(2*gamma*gamma))
        optimum = minimize_scalar(objective, bounds=(0., gamma), method='bounded',
                                  options={'xatol':1e-12})
        location_error = abs(float(optimum.x)-gamma*chi/(2*chi_cap))
        if not optimum.success or location_error > 1e-7:
            raise ArithmeticError(('anisotropic constant optimizer', name))
        optimizers.append(dict(case=name, optimizer_location_error=location_error))
        equal(f'{name} best constant rate', -objective(gamma*chi/(2*chi_cap)), chi*chi/(8*chi_cap))
        if p == 2:
            def angular(theta):
                unit = np.array([np.cos(theta), np.sin(theta)])
                return float(unit@a_matrix@unit)**2/float(unit@b_matrix@unit)/np.pi
            direct, _ = quad(angular, 0., 2*np.pi, epsabs=1e-12, epsrel=1e-12)
            equal(f'{name} Gaussian integral versus angular integration', psi, direct)
        for q in (1., 1.5, 3.):
            value, _ = gaussian_ratio_integral(a_matrix, q*a_matrix)
            equal(f'{name} proportional-cap ratio q={q}', value, chi/q)
        rank = int(np.count_nonzero(eigenvalues > 1e-10))
        projection = vectors[:, eigenvalues > 1e-10]@vectors[:, eigenvalues > 1e-10].T
        spherical = 1+float(np.linalg.eigvalsh(a_matrix).max())
        value, _ = gaussian_ratio_integral(a_matrix, spherical*projection)
        equal(f'{name} spherical-cap exact fourth-ratio rank={rank}', value,
              (chi*chi+2*np.trace(a_matrix@a_matrix))/(spherical*(rank+2)))
        ratio_cases.append(dict(case=name, chi=chi, chi_cap=chi_cap, psi=psi,
                                quadrature_error_estimate=error_estimate,
                                adaptive_rate=psi/8, best_constant_rate=chi*chi/(8*chi_cap)))

    a = (1/1.25)**2
    a_matrix = a*np.eye(2); b_matrix = a*np.diag([1., 9.])
    psi, _ = gaussian_ratio_integral(a_matrix, b_matrix)
    equal('two-signal geometric-mean ratio', psi, 2*a/3)
    equal('two-signal adaptive coefficient times gamma', 4*(2*a)/psi, 12.)
    equal('two-signal best constant coefficient times gamma', 4*(10*a)/(2*a), 20.)

    for p in (1, 5, 20, 100):
        sigma2, ridge, gamma = 1.4, .25, 2.
        chi = p*(sigma2/(sigma2+ridge))**2
        equal(f'isotropic dimension factor p={p}', chi,
              np.trace((sigma2/(sigma2+ridge))**2*np.eye(p)))
        for q in (1., 1.5, 3.):
            kappa = chi/8
            objective = lambda lam: -kappa*(4*lam/gamma-4*q*lam*lam/gamma**2)
            optimum = minimize_scalar(objective, bounds=(0., gamma), method='bounded',
                                      options={'xatol':1e-12})
            location_error = abs(float(optimum.x)-gamma/(2*q))
            if not optimum.success or location_error > 1e-7:
                raise ArithmeticError(('geometric bet optimizer', p, q, optimum))
            optimizers.append(dict(dimension=p, q=q, optimizer_location_error=location_error))
            equal(f'isotropic optimal rate p={p} q={q}', -objective(gamma/(2*q)), kappa/q)
            equal(f'isotropic geometric utility coefficient p={p} q={q}',
                  (chi/(2*gamma))*(q/kappa), 4*q/gamma)
            v = .2; s = q*v
            certificate = s*(1+gamma*np.sqrt(3*s)/2)**2
            equal(f'geometric Minkowski certificate p={p} q={q}', certificate,
                  (np.sqrt(s)+gamma*np.sqrt(3*s*s)/2)**2)
            gap = certificate-s-3*gamma*gamma*s*s/4
            equal(f'constant-certificate strict gap p={p} q={q}', gap, gamma*np.sqrt(3)*s**1.5)
            nonnegative(f'constant-certificate positive gap p={p} q={q}', gap)

    sources = ['scripts/audit_multivariate_waiting.py', 'paper/sections/16_multivariate_waiting.tex',
               'paper/sections/17_multivariate_proofs.tex', 'paper/sections/12_vanishing_proofs.tex']
    return dict(complete=True, deterministic_identity_checks=len(identities),
                deterministic_inequality_checks=len(inequalities), optimizer_checks=len(optimizers),
                maximum_identity_error=max(row['absolute_error'] for row in identities),
                maximum_scaled_identity_error=max(row['scaled_error'] for row in identities),
                minimum_inequality_gap=min(row['minimum_gap'] for row in inequalities),
                maximum_optimizer_location_error=max(row['optimizer_location_error'] for row in optimizers),
                identities=identities, inequalities=inequalities, optimizers=optimizers,
                anisotropic_ratio_cases=ratio_cases,
                source_sha256={path:hashlib.sha256((root/path).read_bytes()).hexdigest() for path in sources},
                scope='Finite deterministic matrix identities, Gaussian density comparisons, moment inequalities and scalar quadratic optimization. No random paths, asymptotic proof by computation, observed power, expected stopped costs, growing-dimensional result or financial-strategy performance claim.')


if __name__ == '__main__':
    result = audit(ROOT)
    destination = ROOT/'reports/multivariate_waiting_checks.json'
    destination.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key:value for key,value in result.items()
                      if key not in ('identities','inequalities','optimizers','source_sha256')}, indent=2))
