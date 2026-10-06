"""Positive-semidefinite factor DGPs with known conditional moments."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

SCENARIOS = ('permanent_death','revival','negative_hedge','positive_redundant',
             'correlation_revival','gradual','repeated')
NOISES = ('gaussian','student','garch','ar')

@dataclass
class Sample:
    returns: np.ndarray
    means: np.ndarray          # predictable conditional means, [B,T,M+1]
    rho: np.ndarray            # [T,M]
    scale2: np.ndarray         # conditional base variance, [B,T]
    common_var: float
    phase: np.ndarray


def simulate(scenario: str, noise: str, reps: int, periods: int, m: int, seed: int,
             strength: float=1.) -> Sample:
    if scenario not in SCENARIOS or noise not in NOISES:
        raise ValueError('Unknown scenario/noise.')
    rng=np.random.default_rng(seed)
    phase=np.minimum(2,3*np.arange(periods)//periods)
    rho=np.full((periods,m),-.75)
    mu=np.full((periods,m),-.003)
    bad=phase==1
    if scenario=='permanent_death':
        mu[:]=.045*strength; mu[phase>=1]=-.045*strength; rho[:]=.2
    elif scenario=='revival':
        mu[:]=.045*strength; mu[bad]=-.045*strength; rho[:]=.2
    elif scenario=='negative_hedge':
        mu[:]=-.003; rho[:]=-.75*strength
    elif scenario=='positive_redundant':
        mu[:]=.006; rho[:]=.9*strength
    elif scenario=='correlation_revival':
        mu[:]=.003; rho[:]=-.8*strength; rho[bad]=.8*strength
    elif scenario=='gradual':
        mu[:]=.003
        rho[:]=(-.8*np.cos(2*np.pi*np.arange(periods)/periods))[:,None]*strength
    elif scenario=='repeated':
        phase=(np.arange(periods)//max(1,periods//6))%2
        mu[:]=.003; rho[:]=np.where(phase[:,None]==0,-.8,.8)*strength
    if m>1:
        # Heterogeneous phase schedules: no perfectly synchronous alpha zoo.
        for j in range(m):
            shift=(j%4)*periods//12
            rho[:,j]=np.roll(rho[:,j],shift)
            mu[:,j]=np.roll(mu[:,j],shift)
    rho=np.clip(rho,-.98,.98)
    if noise=='student':
        eps=rng.standard_t(5,size=(reps,periods,m+1))*np.sqrt(3/5)
    else:
        eps=rng.normal(size=(reps,periods,m+1))
    out=np.empty_like(eps); means=np.empty_like(eps)
    scale2=np.empty((reps,periods))
    h=np.ones(reps); last=np.zeros(reps)
    phi=.25 if noise=='ar' else 0.
    for t in range(periods):
        s=.08*np.sqrt(h)
        pred=phi*last
        innovation=np.sqrt(1-phi*phi)*eps[:,t,0]
        factor=pred+innovation
        means[:,t,0]=.006+s*pred
        means[:,t,1:]=mu[t]+s[:,None]*rho[t]*pred[:,None]
        out[:,t,0]=.006+s*factor
        out[:,t,1:]=mu[t]+s[:,None]*(rho[t]*factor[:,None]+np.sqrt(1-rho[t]**2)*eps[:,t,1:])
        scale2[:,t]=s*s
        if noise=='garch':
            h=.05+.08*h*eps[:,t,0]**2+.87*h
        last=factor
    return Sample(out,means,rho,scale2,1-phi*phi,phase)


def conditional_value(active, mean, rho, scale2, common_var, cfg, previous=None):
    """Exact E[u(R_net)|past] for the implemented quadratic objective."""
    q=cfg.satellite_weight/active.shape[1]
    w=active*q
    cost=np.sum(w,axis=1)*cfg.fee
    if previous is not None:
        cost=cost+q*cfg.switch_cost*np.sum(active!=previous,axis=1)
    m=cfg.core_weight*mean[:,0]+np.sum(w*mean[:,1:],axis=1)-cost
    loading=cfg.core_weight+np.sum(w*rho,axis=1)
    variance=scale2*(common_var*loading**2+np.sum(w*w*(1-rho*rho),axis=1))
    return m-.5*cfg.gamma*(variance+m*m)


def marginal_mean(active,mean,rho,scale2,common_var,cfg):
    q=cfg.satellite_weight/active.shape[1]
    w=active*q
    totalmean=cfg.core_weight*mean[:,0]+np.sum(w*(mean[:,1:]-cfg.fee),axis=1)
    total_load=cfg.core_weight+np.sum(w*rho,axis=1)
    bmean=totalmean[:,None]-w*(mean[:,1:]-cfg.fee)
    bload=total_load[:,None]-w*rho
    dm=q*(mean[:,1:]-cfg.fee)
    cov=q*scale2[:,None]*common_var*rho*bload
    dv=q*q*scale2[:,None]*(common_var*rho*rho+1-rho*rho)
    return dm-cfg.gamma*(bmean*dm+cov+.5*(dv+dm*dm))
