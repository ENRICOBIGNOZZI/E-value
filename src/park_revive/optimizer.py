"""Convex QP with exact L1 epigraphs and primal/dual certificates."""
from dataclasses import dataclass
import numpy as np
import scipy.sparse as sp
import osqp
from .costs import expected_utility


@dataclass(frozen=True)
class Solution:
    weights: np.ndarray
    value: float
    primal_residual: float
    dual_residual: float
    gap: float


class Optimizer:
    def __init__(self, cfg, mu, second):
        self.cfg = cfg
        self.mu = np.asarray(mu, dtype=float)
        self.second = np.asarray(second, dtype=float)
        if not np.isfinite(self.mu).all() or not np.isfinite(self.second).all():
            raise ValueError('Non-finite moments')
        if not np.allclose(self.second, self.second.T, atol=1e-12):
            raise ValueError('Second moment must be symmetric')
        if np.linalg.eigvalsh(self.second).min() < -1e-10:
            raise ValueError('Second moment must be PSD')
        self.cache = {}
        self.memo = {}

    def new_day(self):
        self.memo.clear()

    def solve(self, support, previous):
        cfg = self.cfg
        b = np.asarray(previous)
        idx = tuple(sorted(support))
        key = (idx,b.tobytes())
        if key in self.memo:
            return self.memo[key]
        w = np.zeros_like(self.mu)
        if not idx:
            return Solution(w, expected_utility(w,b,self.mu,self.second,cfg),0.,0.,0.)
        ix = np.array(idx)
        # Unchanged target is optimal if the smooth marginal lies inside the L1 band.
        outside = np.ones(len(w), dtype=bool); outside[ix] = False
        if np.max(np.abs(b[outside]), initial=0.) <= 1e-14 and np.abs(b).sum() <= cfg.leverage+1e-12:
            gradient = self.mu[ix]-cfg.gamma*self.second[np.ix_(ix,ix)]@b[ix]
            no_trade = np.max(np.abs(gradient), initial=0.) <= cfg.proportional
            if not no_trade and abs(np.abs(b).sum()-cfg.leverage)<1e-13:
                nz=np.abs(b[ix])>1e-14
                signed=gradient[nz]*np.sign(b[ix][nz])
                low=max(0.,np.max(np.abs(gradient[~nz])-cfg.proportional,initial=0.),
                        np.max(signed-cfg.proportional,initial=0.))
                high=np.min(signed+cfg.proportional,initial=np.inf)
                no_trade=low<=high
            if no_trade:
                return Solution(b.copy(), expected_utility(b,b,self.mu,self.second,cfg),0.,0.,0.)
        n = len(idx)
        h = cfg.gamma*self.second[np.ix_(ix,ix)]+cfg.impact*np.eye(n)
        q = np.r_[-self.mu[ix]-cfg.impact*b[ix], np.full(n,cfg.proportional), np.zeros(n)]
        lower = np.r_[np.full(4*n,-np.inf), -np.inf]
        upper = np.r_[b[ix], -b[ix], np.zeros(2*n), cfg.leverage]
        if idx not in self.cache:
            eye = sp.eye(n,format='csc'); zero = sp.csc_matrix((n,n))
            a = sp.vstack([sp.hstack([eye,-eye,zero]), sp.hstack([-eye,-eye,zero]),
                           sp.hstack([eye,zero,-eye]), sp.hstack([-eye,zero,-eye]),
                           sp.csc_matrix(np.r_[np.zeros(2*n),np.ones(n)][None,:])],format='csc')
            p = sp.block_diag([sp.csc_matrix(h),sp.csc_matrix((2*n,2*n))],format='csc')
            solver = osqp.OSQP()
            solver.setup(P=sp.triu(p,format='csc'), q=q, A=a, l=lower,u=upper,
                         eps_abs=cfg.solver_tolerance,eps_rel=cfg.solver_tolerance,
                         max_iter=30000,verbose=False,polishing=False,adaptive_rho=True)
            self.cache[idx] = solver
        solver = self.cache[idx]
        solver.update(q=q, u=upper)
        result = solver.solve(raise_error=False)
        if result.info.status_val != 1:
            raise RuntimeError(f'QP failed: {result.info.status}')
        w[ix] = result.x[:n]
        # Restore feasibility at the numerical tolerance only; report certificate.
        leverage = np.abs(w).sum()
        if leverage > cfg.leverage:
            w *= cfg.leverage/leverage
        threshold = max(2e-6, 100*cfg.solver_tolerance)
        if max(result.info.prim_res,result.info.dual_res) > threshold:
            raise RuntimeError('Solver residual exceeds declared tolerance')
        solution = Solution(w,expected_utility(w,b,self.mu,self.second,cfg),
                            result.info.prim_res,result.info.dual_res,abs(result.info.duality_gap))
        self.memo[key] = solution
        return solution


def fit_moments(history, cfg):
    a = np.asarray(history)
    mu = a.mean(axis=0)
    m = a.T@a/len(a)
    m = (1-cfg.shrinkage)*m+cfg.shrinkage*np.diag(np.diag(m))+cfg.ridge*np.eye(a.shape[1])
    return mu,m
