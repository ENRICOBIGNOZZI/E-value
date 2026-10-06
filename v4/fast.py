"""Reversible portfolio monitoring. Research only; no order submission.

The FAST rule controls detector patience, not lifetime false-discovery probability.
A clipped score certifies its own conditional mean, not an unrestricted raw mean.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from numpy.typing import NDArray

Float = NDArray[np.float64]
Bool = NDArray[np.bool_]

def utility(x: Float, gamma: float = 8.) -> Float:
    return x - gamma * x * x / 2.

def paired_value(book_without: Float, leg: Float, gamma: float = 8.) -> Float:
    """Exact, cancellation-resistant quadratic utility increment."""
    return leg * (1. - gamma * book_without) - gamma * leg * leg / 2.

def economic_mean(mu_leg: Float, mu_base: Float, cov: Float,
                  second_moment_leg: Float, gamma: float = 8.) -> Float:
    return mu_leg * (1. - gamma * mu_base) - gamma * cov - gamma * second_moment_leg / 2.

def binary_utility(a: Float, linear: Float, second: Float, gamma: float) -> Float:
    return a @ linear - gamma * np.einsum('...i,ij,...j->...', a, second, a)/2

def local_marginals(a: Float, linear: Float, second: Float, gamma: float) -> Float:
    return linear - gamma*(a @ second - a*np.diag(second)) - gamma*np.diag(second)/2

def kl_bernoulli(p: float, q: float) -> float:
    if not 0 < p < 1 or not 0 < q < 1:
        raise ValueError('Interior Bernoulli means required.')
    return p*np.log(p/q)+(1-p)*np.log((1-p)/(1-q))

def delay_bound(patience: float, gap: float, bets: Float, weights: Float | None = None,
                family: int = 1, hysteresis: float = 0.) -> float:
    """Worst-case bounded-score delay. gap is the conditional mean of |signed score|.

    A sufficient threshold for one stream in e-d-BH is patience*family.
    The bound is for continuous screening, and no blackout/minimum dwell period.
    """
    bets=np.asarray(bets,float)
    if not 0 <= hysteresis < gap < 1 or patience < 1 or family < 1:
        raise ValueError('Need 0 <= hysteresis < gap < 1, A>=1, and M>=1.')
    w=np.ones(len(bets))/len(bets) if weights is None else np.asarray(weights,float)
    # x=(signed_score-h)/(1+h) has endpoints -1 and (1-h)/(1+h).
    high=(1-hysteresis)/(1+hysteresis)
    drift=(1+gap)/2*np.log1p(bets*high)+(1-gap)/2*np.log1p(-bets)
    valid=drift>0
    if not valid.any(): return float('inf')
    numer=np.log(patience*family/w[valid])+np.log1p(bets[valid]*high)
    return float(np.min(numer/drift[valid]))

@dataclass(frozen=True)
class DetectorConfig:
    patience: float = 252.
    components: int = 31
    hysteresis: float = .02
    kind: str = 'cusum'
    batch: str = 'edbh'
    lambda_min: float = .01
    lambda_max: float = .95
    kill_only: bool = False
    adaptive: bool = False
    memory: int = 60
    def __post_init__(self):
        if self.patience < 1 or self.components < 1 or not 0<=self.hysteresis<1:
            raise ValueError('Invalid detector configuration.')
        if not 0 < self.lambda_min <= self.lambda_max < 1:
            raise ValueError('Bets must be inside (0,1).')
        if self.kind not in {'cusum','sr'} or self.batch not in {'edbh','single','bonferroni'}:
            raise ValueError('Unknown detector or batching rule.')
        if self.memory < 1: raise ValueError('Positive memory required.')

class Evidence:
    def __init__(self, shape: tuple[int,int], cfg: DetectorConfig):
        if len(shape)!=2 or min(shape)<1: raise ValueError('Shape must be paths x streams.')
        self.shape,self.cfg=shape,cfg
        self.bets=np.geomspace(cfg.lambda_min,cfg.lambda_max,cfg.components)
        self.weights=np.full(cfg.components,1/cfg.components)
        self.capital=np.zeros((*shape,cfg.components))
        self.s1=np.zeros(shape);self.s2=np.zeros(shape)
    def reset(self, selected: Bool) -> None:
        self.capital[selected]=0.;self.s1[selected]=0.;self.s2[selected]=0.
    def update(self, x: Float) -> Float:
        x=np.asarray(x,float)
        if x.shape != self.shape or not np.isfinite(x).all() or (np.abs(x)>1+1e-10).any():
            raise ValueError('Finite bounded inputs with the configured shape required.')
        if self.cfg.adaptive:
            # Uses only earlier observations: no same-round estimation of the bet.
            b=np.clip(self.s1/(self.s2+.1),self.cfg.lambda_min,self.cfg.lambda_max)[...,None]
        else: b=self.bets
        factors=1+x[...,None]*b
        if self.cfg.kind=='cusum': self.capital=np.maximum(1.,self.capital)*factors
        else: self.capital=(1.+self.capital)*factors
        # Downward saturation preserves detector inequalities.
        np.minimum(self.capital,1e100,out=self.capital)
        rate=1-1/self.cfg.memory
        self.s1=rate*self.s1+x;self.s2=rate*self.s2+x*x
        return self.capital @ self.weights

def edbh(evidence: Float, patience: float) -> Bool:
    """e-detector BH self-consistency; NOT ordinary lifetime e-value FDR."""
    e=np.asarray(evidence,float)
    if e.ndim!=2 or patience<1 or not np.isfinite(e).all() or (e<0).any():
        raise ValueError('Finite nonnegative paths x streams evidence required.')
    m=e.shape[1]; ordered=np.sort(e,axis=1)[:,::-1]
    ranks=np.arange(1,m+1)
    r=np.max(np.where(ordered >= patience*m/ranks,ranks,0),axis=1)
    threshold=np.divide(patience*m,r,out=np.full(len(r),np.inf),where=r>0)
    return e>=threshold[:,None]

class Controller:
    """The caller earns this period's return BEFORE calling step.

    All accepted state changes are effective next period. Every accepted stream
    discards all its detector wealth; unselected streams are not renormalized.
    """
    def __init__(self, shape: tuple[int,int], cfg: DetectorConfig):
        self.cfg,self.shape=cfg,shape
        self.active=np.ones(shape,bool);self.test=Evidence(shape,cfg)
    def step(self, score: Float, standalone: Float | None=None, allow: bool=True):
        h=self.cfg.hysteresis
        x=(np.where(self.active,-score,score)-h)/(1+h)
        values=self.test.update(x)
        if self.cfg.batch=='edbh': eligible=edbh(values,self.cfg.patience)
        else:
            factor=self.shape[1] if self.cfg.batch=='bonferroni' else 1
            eligible=values >= self.cfg.patience*factor
        if self.cfg.kill_only: eligible &= self.active
        if not allow: eligible[:]=False
        self.active ^= eligible
        self.test.reset(eligible)
        return eligible,values

class Rolling:
    def __init__(self, shape, window=60, threshold=.02, standalone=False, z_stat=False):
        self.active=np.ones(shape,bool);self.buffer=np.zeros((*shape,window));self.t=0
        self.window=window;self.threshold=threshold;self.standalone=standalone;self.z_stat=z_stat
    def step(self,score,standalone=None,allow=True):
        value=standalone if self.standalone else score
        self.buffer[...,self.t%self.window]=value;self.t+=1
        mean=self.buffer[...,:min(self.t,self.window)].mean(-1)
        if self.z_stat:
            sd=self.buffer[...,:min(self.t,self.window)].std(-1,ddof=1) if self.t>1 else np.ones_like(mean)
            mean=mean*np.sqrt(min(self.t,self.window))/np.maximum(sd,1e-6)
        sign=np.where(self.active,-1.,1.)
        flip=(sign*mean>self.threshold) & (self.t>=self.window)
        if not allow: flip[:]=False
        self.active^=flip
        return flip,np.ones_like(score)

class FixedShare:
    """Two experts (on/off) with fixed-share posterior; a transparent heuristic gate."""
    def __init__(self, shape, eta=.5, share=.02):
        self.active=np.ones(shape,bool);self.p=np.full(shape,.5);self.eta=eta;self.share=share
    def step(self,score,standalone=None,allow=True):
        prior=np.clip(self.p,1e-12,1-1e-12)
        logit=np.log(prior/(1-prior))+self.eta*score
        p=1/(1+np.exp(-np.clip(logit,-40,40)))
        self.p=(1-self.share)*p+self.share/2
        next_on=np.where(self.active,self.p>=.35,self.p>.65)
        flip=next_on!=self.active
        if not allow: flip[:]=False
        self.active^=flip
        return flip,np.ones_like(score)

class AlwaysOn:
    def __init__(self,shape): self.active=np.ones(shape,bool)
    def step(self,score,standalone=None,allow=True): return np.zeros_like(self.active),np.ones_like(score)

def oracle_value(theta: Float, switch_cost: float, initial: int = 1) -> Float:
    """Exact dynamic program for exogenous two-action expected increments.

    theta has shape paths x time. Oracle knows the complete conditional-mean
    schedule, not realized future payoffs. Cash has zero incremental utility.
    """
    a=np.asarray(theta,float)
    if a.ndim!=2 or switch_cost<0: raise ValueError('Invalid oracle input.')
    v=np.full((len(a),2),-np.inf);v[:,initial]=0.
    for t in range(a.shape[1]):
        off=np.maximum(v[:,0],v[:,1]-switch_cost)
        on=np.maximum(v[:,1],v[:,0]-switch_cost)+a[:,t]
        v=np.c_[off,on]
    return v.max(1)
