"""Same DGP, with an explicit pre-return preparation boundary."""
from dataclasses import dataclass
import numpy as np
from park_revive.dgp import Market,Observed,Truth
from park_revive.features import evaluate
from park_revive.sleeves import sleeve_weights


@dataclass(frozen=True)
class PublicDesign:
    day: int
    values: np.ndarray
    sleeves: np.ndarray


class CausalMarket(Market):
    def __init__(self,cfg,seed):
        super().__init__(cfg,seed)
        self._prepared=None

    def prepare(self):
        if self._prepared is None:
            values=evaluate(np.tanh(self.latent),self.library)
            p=sleeve_weights(values)
            stock_mean=values@self.theta
            multiplier=self.cfg.stress_multiplier if self.regime else 1.
            factor_scale=np.array(self.cfg.factor_scales)*multiplier
            idio_scale=self.cfg.idio_scale*multiplier
            mu=p.T@stock_mean
            load=np.column_stack(((p.T@self.beta)*factor_scale,p.T*idio_scale))
            second=np.outer(mu,mu)+load@load.T
            truth=Truth(self.day,mu,load,second,self.theta.copy(),self.regime,self.deteriorated)
            for a in (values,p,mu,load,second,truth.theta):a.setflags(write=False)
            self._prepared=(PublicDesign(self.day,values,p),truth)
        return self._prepared

    def step(self):
        _,truth=self.prepare();cfg=self.cfg
        shocks=self.rng.laplace(0,1/np.sqrt(2),4+cfg.n_assets)
        a=truth.mean+truth.loadings@shocks
        observed=Observed(self.day,a,self.ids)
        # Identical ordering and RNG consumption to the frozen Market.step.
        target=self.base.copy()
        if self.deteriorated:target[25:35]=0
        if self.regime:target[35:45]*=cfg.revive_low_fraction
        rho=2**(-1/cfg.coefficient_half_life)
        innovation=self.rng.uniform(-.01,.01,100)*self.base
        self.theta=np.clip(rho*self.theta+(1-rho)*target+innovation,0,cfg.theta_cap_multiple*self.base)
        if self.rng.random()<cfg.transition_probability:self.regime=1-self.regime
        self.deteriorated|=bool(self.regime)
        self.latent=cfg.feature_rho*self.latent+np.sqrt(1-cfg.feature_rho**2)*(self.rng.normal(size=self.latent.shape)@self.chol.T)
        self.day+=1;self._prepared=None
        return observed,truth
