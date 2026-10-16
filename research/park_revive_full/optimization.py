"""Exact scalar shortcut; the same constrained QP for larger supports."""
import numpy as np
from park_revive.optimizer import Optimizer,Solution
from park_revive.costs import cost_components


class StudyOptimizer(Optimizer):
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
            result=super().solve(idx,b)
        # Enforce literal support zeros, including tiny remnants in a no-trade shortcut.
        outside=np.ones(len(b),dtype=bool);outside[list(idx)]=False
        if np.any(result.weights[outside]!=0):
            w=result.weights.copy();w[outside]=0.
            value=float(w@self.mu-self.cfg.gamma*(w@self.second@w)/2-sum(cost_components(w,b,self.cfg)))
            result=Solution(w,value,result.primal_residual,result.dual_residual,result.gap)
            self.memo[key]=result
        return result
