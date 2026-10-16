"""Bias-corrected lower winsorization and nonnegative betting factors.

Validity requires conditional moment envelopes, not estimated sample moments.
The fourth-moment option for a quadratic utility score requires eighth moments
of portfolio returns. This is a declared extension, not the baseline Catoni test.
"""
from dataclasses import dataclass
import numpy as np
from scipy.special import logsumexp


def tail_bias(bound,second,fourth):
    b=np.asarray(bound,dtype=float)
    if np.any(b<=0) or not np.isfinite(b).all():raise ValueError('Positive finite clipping levels required')
    if np.any(np.asarray(second)<0) or np.any(np.asarray(fourth)<0):raise ValueError('Nonnegative moments required')
    return np.minimum(np.asarray(second)/(4*b),27*np.asarray(fourth)/(256*b**3))


@dataclass
class TailMixture:
    n_signals: int
    scales: tuple[float,...]=(2.,4.,8.)
    fractions: tuple[float,...]=(.25,.5,.75)

    def __post_init__(self):
        if self.n_signals<1 or min(self.scales)<=0 or not 0<min(self.fractions)<=max(self.fractions)<1:
            raise ValueError('Positive scales and betting fractions strictly between zero and one required')
        self.grid=tuple((s,f) for s in self.scales for f in self.fractions)
        self.log_capitals=np.zeros((len(self.grid),self.n_signals))
        self.n=0

    def prepare(self,second,fourth):
        second=np.broadcast_to(second,(self.n_signals,)).astype(float,copy=True)
        fourth=np.broadcast_to(fourth,(self.n_signals,)).astype(float,copy=True)
        if not np.isfinite(second).all() or not np.isfinite(fourth).all() or min(second.min(),fourth.min())<0:
            raise ValueError('Finite nonnegative certified moments required')
        if np.any((fourth==0)&(second!=0)):
            raise ValueError('Zero fourth moment requires zero second moment')
        levels=np.array([s for s,_ in self.grid])[:,None]*fourth[None,:]**.25
        # Moment-zero scores are identically zero. Betting is disabled exactly.
        levels=np.where(fourth[None,:]>0,levels,1.)
        biases=tail_bias(levels,second[None,:],fourth[None,:])
        fractions=np.array([f for _,f in self.grid])[:,None]
        bets=np.where(fourth[None,:]>0,fractions/(levels+biases),0.)
        return levels,biases,bets,fourth.copy()

    def update(self,score,prepared):
        levels,biases,bets,fourth=prepared
        y=np.broadcast_to(np.asarray(score,dtype=float),(self.n_signals,))
        if not np.isfinite(y).all():raise ValueError('Finite utility scores required')
        if np.any((fourth==0)&(y!=0)):raise ValueError('Moment-zero contract violated')
        corrected=np.maximum(y[None,:],-levels)-biases
        increments=np.log1p(bets*corrected)
        if not np.isfinite(increments).all():raise ArithmeticError('Nonfinite betting factor')
        self.log_capitals+=increments;self.n+=1

    @property
    def log_e(self):
        return logsumexp(self.log_capitals,axis=0)-np.log(len(self.grid))
