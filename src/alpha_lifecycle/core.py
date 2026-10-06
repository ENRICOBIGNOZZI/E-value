"""Predictable paired-book monitoring. No live order submission.

The certified target is the CONDITIONAL MEAN OF A CLIPPED UTILITY DIFFERENCE,
not the current sign of an unrestricted expected return. See paper Appendix A.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from numpy.typing import NDArray

Array = NDArray[np.float64]

@dataclass(frozen=True)
class Settings:
    delta: float = .05
    gamma: float = 8.0
    core_weight: float = .8
    satellite_weight: float = .2
    fee: float = .0005            # recurring return deduction per unit exposure/period
    switch_cost: float = .001    # per unit exposure changed
    hysteresis: float = .02      # normalized, clipped score units
    stride: int = 24
    max_age: int = 720
    window: int = 60
    scale_mult: float = 1.0
    warmup: int = 60
    bets: tuple[float, ...] = (.03125, .0625, .125, .25, .5, .75, .9)

    def __post_init__(self):
        if not (0 < self.delta < 1 and 0 <= self.hysteresis < 1):
            raise ValueError('Invalid error budget or hysteresis.')
        if min(self.stride,self.max_age,self.window,self.warmup) < 1:
            raise ValueError('Window lengths must be positive.')
        if self.max_age % self.stride:
            raise ValueError('max_age must be a multiple of stride.')
        if not self.bets or not all(0 < x < 1 for x in self.bets):
            raise ValueError('All betting fractions must be in (0,1).')
        if self.scale_mult <= 0 or self.satellite_weight <= 0:
            raise ValueError('Invalid exposure or normalization.')

class RestartMixture:
    """Unit-initial-capital mixture, with dormant mass and safe expiry.

    Local start k has mass 1/(k(k+1)). Unstarted mass is 1/(k+1).
    Expiring a component discards wealth; it NEVER renormalizes survivors.
    A reset advances the episode counter and spends a smaller error budget.
    """
    def __init__(self, shape: tuple[int,int], cfg: Settings, restart: bool = True):
        self.cfg, self.shape, self.restart = cfg, shape, restart
        self.slots = cfg.max_age // cfg.stride if restart else 1
        self.capital = np.zeros((*shape,self.slots,len(cfg.bets)), dtype=float)
        self.age = np.zeros(shape, dtype=np.int64)
        self.starts = np.zeros(shape,dtype=np.int64)
        self.episode = np.ones(shape,dtype=np.int64)
        self.bets = np.asarray(cfg.bets)

    def reset(self, mask: NDArray[np.bool_]) -> None:
        self.capital[mask] = 0
        self.age[mask] = 0
        self.starts[mask] = 0
        self.episode[mask] += 1

    def update(self, x: Array) -> Array:
        if x.shape != self.shape or not np.all(np.isfinite(x)) or np.max(np.abs(x)) > 1+1e-10:
            raise ValueError('The test input must be finite and in [-1,1].')
        launch = (self.age % self.cfg.stride == 0) if self.restart else (self.age == 0)
        rr,cc = np.nonzero(launch)
        if len(rr):
            k = self.starts[rr,cc] + 1
            slot = (k-1) % self.slots
            mass = 1/(k*(k+1)) if self.restart else np.ones_like(k,dtype=float)
            self.capital[rr,cc,slot,:] = mass[:,None] / len(self.bets)
            self.starts[rr,cc] = k
        self.capital *= 1 + x[...,None,None] * self.bets
        # Saturation is a downward jump and cannot invalidate a supermartingale.
        np.minimum(self.capital,1e100,out=self.capital)
        self.age += 1
        dormant = 1/(self.starts+1) if self.restart else 0.
        return self.capital.sum(axis=(-2,-1)) + dormant

    def threshold(self) -> Array:
        k = self.episode.astype(float)
        return self.shape[1]*k*(k+1)/self.cfg.delta


def utility(r: Array, gamma: float) -> Array:
    return r - .5*gamma*r*r


def paired_scores(returns: Array, active: NDArray[np.bool_], cfg: Settings,
                  scale: Array) -> tuple[Array,Array,Array]:
    """Returns include core in column 0. All weights are chosen before returns.

    Off allocations go to cash (zero excess return), not to remaining funds.
    Recurring costs enter both shadow books. Actual switching costs are logged
    separately; hysteresis is NOT claimed to solve an optimal stopping problem.
    """
    m = active.shape[1]
    q = cfg.satellite_weight/m
    legs = q*(returns[:,1:] - cfg.fee)
    book = cfg.core_weight*returns[:,0] + np.sum(active*legs,axis=1)
    minus = book[:,None] - active*legs
    raw = utility(minus+legs,cfg.gamma) - utility(minus,cfg.gamma)
    score = np.clip(raw/np.maximum(scale,1e-12),-1,1)
    return score,raw,book

class Controller:
    """One accepted switch per portfolio/period prevents simultaneous deletions.

    Test claims concern predictable, possibly changing reference books over an
    episode. They are not guarantees of an instantaneous state classification.
    """
    def __init__(self, shape: tuple[int,int], method: str, cfg: Settings):
        self.cfg,self.method,self.shape = cfg,method,shape
        self.active = np.ones(shape,dtype=bool)
        self.test = RestartMixture(shape,cfg,restart=method!='e_cumulative')
        self.buffer = np.zeros((*shape,cfg.window))
        self.t = 0
        self.cusum = np.zeros(shape)
        self.posterior = np.full(shape,.8)

    def step(self, score: Array, standalone: Array) -> tuple[NDArray[np.bool_],Array]:
        self.t += 1
        if self.method == 'always_on':
            return np.zeros(self.shape,dtype=bool), np.ones(self.shape)
        x = np.where(self.active,-score,score)
        x = (x-self.cfg.hysteresis)/(1+self.cfg.hysteresis)
        e = np.ones(self.shape)
        if self.method.startswith('e_'):
            e = self.test.update(x)
            strength = e/self.test.threshold()
            eligible = strength >= 1
            if self.method == 'e_kill_only':
                eligible &= self.active
        elif self.method in ('rolling_portfolio','rolling_standalone'):
            v = score if self.method=='rolling_portfolio' else standalone
            self.buffer[..., (self.t-1)%self.cfg.window] = v
            avg = self.buffer[...,:min(self.t,self.cfg.window)].mean(axis=-1)
            strength = np.where(self.active,-avg,avg)
            eligible = (strength > self.cfg.hysteresis) & (self.t>=self.cfg.window)
        elif self.method == 'cusum':
            self.cusum = np.maximum(0,self.cusum+x-.05)
            strength = self.cusum/8.
            eligible = strength>=1
        elif self.method == 'hmm':
            # Fixed two-state Gaussian score-emission filter, not a fitted oracle.
            prior = .98*self.posterior+.02*(1-self.posterior)
            odds = np.log(prior/(1-prior)) + 2*.20*score/(.60**2)
            self.posterior = 1/(1+np.exp(-np.clip(odds,-40,40)))
            strength = np.where(self.active,1-self.posterior,self.posterior)
            eligible = strength>.95
        else:
            raise ValueError(f'Unknown method: {self.method}')
        accepted = np.zeros(self.shape,dtype=bool)
        best = np.argmax(np.where(eligible,strength,-np.inf),axis=1)
        rows = np.flatnonzero(np.any(eligible,axis=1))
        accepted[rows,best[rows]] = True
        self.active[accepted] = ~self.active[accepted]
        self.test.reset(accepted)
        self.cusum[accepted] = 0
        return accepted,e
