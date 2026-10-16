"""Controlled mathematical diagnostics, not extra financial-market DGPs."""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import ndtr
from .eprocess import phi


def wilson(successes,n,z=1.96):
    p=successes/n; den=1+z*z/n
    center=(p+z*z/(2*n))/den
    half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return center-half,center+half


def statistical_study(directory,replications=10000,seed=910001,blocks=16,h=100):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(seed)
    rows=[]
    for delta in (0.,.1,.2,.3):
        # Unit raw second moment: variance is 1-delta².
        e=np.zeros(replications);fixed=np.zeros(replications);total=np.zeros(replications)
        regret=np.zeros(replications);ever=np.zeros(replications,bool);ever_fixed=ever.copy()
        repeated=ever.copy();sumsq=np.zeros(replications)
        repeated_hac=ever.copy()
        maxlag=int(np.floor(4*((blocks*h)/100)**(2/9)))
        lag_products=np.zeros((maxlag,replications))
        history=np.empty((blocks*h,replications))
        lamstar=delta/2;nu2=1.;delta0=.1
        for k in range(1,blocks+1):
            bet=np.full(replications,delta0/2) if k==1 else np.clip(total/(h*(k-1))/2,0,.5)
            regret+=h*(bet-lamstar)**2
            for t in range(h):
                # Predictable stochastic scale under null creates dependence while retaining bound.
                scale=np.where(total>=0,1.,.5) if delta==0 else np.ones(replications)
                y=delta+np.sqrt(1-delta*delta)*scale*rng.laplace(0,1/np.sqrt(2),replications)
                index=h*(k-1)+t
                for lag in range(1,min(index,maxlag)+1):
                    lag_products[lag-1]+=y*history[index-lag]
                history[index]=y
                total+=y;sumsq+=y*y
                e+=phi(bet*y)-bet*bet/2
                fixed_bet=.1 if delta==0 else lamstar
                fixed+=phi(fixed_bet*y)-fixed_bet**2/2
            ever|=e>=np.log(20);ever_fixed|=fixed>=np.log(20)
            n=h*k
            variance=np.maximum(sumsq/n-(total/n)**2,0)
            p=ndtr(-(total/n)*np.sqrt(n/np.maximum(variance,1e-30)))
            repeated|=p<=.05
            lrv=variance.copy();mean=total/n
            bandwidth=int(np.floor(4*(n/100)**(2/9)))
            for lag in range(1,bandwidth+1):
                left=total-history[:lag].sum(axis=0)
                right=total-history[n-lag:n].sum(axis=0)
                cov=(lag_products[lag-1]-mean*(left+right)+(n-lag)*mean*mean)/n
                lrv+=2*(1-lag/(bandwidth+1))*cov
            repeated_hac|=ndtr(-mean*np.sqrt(n/np.maximum(lrv,1e-30)))<=.05
            ck=h*(delta0/2-lamstar)**2+sum(1/j for j in range(1,k))/4
            ak=n*delta*delta/4
            adaptive_bound=max(0.,1-2*ck/ak-20*np.exp(-ak/2)) if ak else 0.
            fixed_bound=max(0.,1-20*np.exp(-ak))
            lo,hi=wilson(int(ever.sum()),replications)
            rows.append(dict(delta=delta,block=k,n=n,replications=replications,seed=seed,
                adaptive_crossing=ever.mean(),fixed_crossing=ever_fixed.mean(),
                repeated_p_crossing=repeated.mean(),ci_low=lo,ci_high=hi,
                repeated_hac_crossing=repeated_hac.mean(),
                adaptive_bound=adaptive_bound,fixed_bound=fixed_bound,
                mean_certificate_regret=regret.mean(),regret_bound=ck,
                mean_log_e=e.mean(),growth_lower=ak-ck))
    frame=pd.DataFrame(rows);frame.to_csv(directory/'statistical_study.csv',index=False)
    return frame
