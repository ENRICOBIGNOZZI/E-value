"""Exact scalar shortcut; the same constrained QP for larger supports."""
import numpy as np
import scipy.sparse as sp
import osqp
from park_revive.optimizer import Optimizer,Solution
from park_revive.costs import cost_components


class StudyOptimizer(Optimizer):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.recoveries=[]

    def solve(self,support,previous):
        idx=tuple(sorted(support));b=np.asarray(previous);key=(idx,b.tobytes())
        if key in self.memo:return self.memo[key]
        if len(idx)<=1:
            w=np.zeros_like(self.mu)
            if idx:
                j=idx[0];g=self.mu[j]-self.cfg.gamma*self.second[j,j]*b[j]
                step=np.sign(g)*max(abs(g)-self.cfg.proportional,0)/(self.cfg.gamma*self.second[j,j]+self.cfg.impact)
                w[j]=np.clip(b[j]+step,-self.cfg.leverage,self.cfg.leverage)
                gross_value=w[j]*self.mu[j]-self.cfg.gamma*w[j]**2*self.second[j,j]/2
            else:gross_value=0.
            value=float(gross_value-sum(cost_components(w,b,self.cfg)))
            result=Solution(w,value,0.,0.,0.);self.memo[key]=result
            return result
        try:result=super().solve(idx,b)
        except RuntimeError as error:
            if 'QP failed:' not in str(error) or idx not in self.cache:raise
            # Same QP and tolerances; permit a longer refinement from the solver's
            # current iterate when its first iteration budget is insufficient.
            self.cache[idx].update_settings(max_iter=300000,polishing=True)
            try:result=super().solve(idx,b)
            except RuntimeError as refined_error:
                if 'QP failed:' not in str(refined_error):raise
                result=self.solve_in_basis_points(idx,b)
                self.memo[key]=result
        # Enforce literal support zeros, including tiny remnants in a no-trade shortcut.
        outside=np.ones(len(b),dtype=bool);outside[list(idx)]=False
        if np.any(result.weights[outside]!=0):
            w=result.weights.copy();w[outside]=0.
            value=float(w@self.mu-self.cfg.gamma*(w@self.second@w)/2-sum(cost_components(w,b,self.cfg)))
            result=Solution(w,value,result.primal_residual,result.dual_residual,result.gap)
            self.memo[key]=result
        return result

    def solve_in_basis_points(self,idx,b):
        """Fresh same-tolerance QP, scaling the entire objective by 10,000.

        Objective units change, its optimizer does not. Original-unit KKT
        residuals are checked independently; inaccurate status is never accepted.
        """
        cfg=self.cfg;n=len(idx);ix=np.array(idx);scale=10000.
        h=cfg.gamma*self.second[np.ix_(ix,ix)]+cfg.impact*np.eye(n)
        q=np.r_[-self.mu[ix]-cfg.impact*b[ix],np.full(n,cfg.proportional),np.zeros(n)]
        eye=sp.eye(n,format='csc');zero=sp.csc_matrix((n,n))
        a=sp.vstack([sp.hstack([eye,-eye,zero]),sp.hstack([-eye,-eye,zero]),
                     sp.hstack([eye,zero,-eye]),sp.hstack([-eye,zero,-eye]),
                     sp.csc_matrix(np.r_[np.zeros(2*n),np.ones(n)][None,:])],format='csc')
        p=sp.block_diag([sp.csc_matrix(h),sp.csc_matrix((2*n,2*n))],format='csc')
        upper=np.r_[b[ix],-b[ix],np.zeros(2*n),cfg.leverage]
        solver=osqp.OSQP()
        solver.setup(P=sp.triu(p*scale,format='csc'),q=q*scale,A=a,
                     l=np.full(4*n+1,-np.inf),u=upper,
                     eps_abs=cfg.solver_tolerance,eps_rel=cfg.solver_tolerance,
                     max_iter=300000,verbose=False,polishing=True,adaptive_rho=True)
        result=solver.solve(raise_error=False)
        if result.info.status_val!=1:
            raise RuntimeError(f'Preconditioned QP failed: {result.info.status}')
        x=result.x;dual=result.y/scale;slack=a@x-upper
        primal=float(max(0.,np.max(slack)))
        stationarity=float(np.max(np.abs(p@x+q+a.T@dual)))
        complementarity=float(np.max(np.abs(dual*slack)))
        dual_sign=float(max(0.,-np.min(dual)))
        gap=abs(float(result.info.duality_gap/scale))
        bound=10*cfg.solver_tolerance
        if max(primal,stationarity,complementarity,dual_sign,gap)>bound:
            raise RuntimeError('Preconditioned QP original-unit KKT certificate failed')
        w=np.zeros_like(self.mu);w[ix]=x[:n]
        leverage=np.abs(w).sum()
        if leverage>cfg.leverage:w*=cfg.leverage/leverage
        value=float(w@self.mu-cfg.gamma*(w@self.second@w)/2-sum(cost_components(w,b,cfg)))
        self.recoveries.append(dict(support=[int(j) for j in idx],objective_scale=scale,iterations=result.info.iter,
            primal_residual=primal,dual_residual=stationarity,complementarity=complementarity,
            dual_sign_violation=dual_sign,duality_gap=gap))
        return Solution(w,value,primal,stationarity,gap)
