"""Monte Carlo study with path-level records and paired Monte Carlo errors."""
from __future__ import annotations
import argparse,json,sys,time,platform
from pathlib import Path
from dataclasses import asdict
import numpy as np
import pandas as pd
from scipy.stats import beta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from alpha_lifecycle.core import Settings,Controller,paired_scores,utility
from alpha_lifecycle.dgp import simulate,conditional_value,marginal_mean,SCENARIOS,NOISES
METHODS=('always_on','rolling_standalone','rolling_portfolio','cusum','hmm','e_cumulative','e_kill_only','e_restart')
ROOT=Path(__file__).resolve().parents[1]

def evaluate(sample,method,cfg,keep_path=False):
    r=sample.returns;B,T,N=r.shape;M=N-1;q=cfg.satellite_weight/M
    ctrl=Controller((B,M),method,cfg);previous=ctrl.active.copy()
    sigma=np.maximum(r[:,:cfg.warmup,1:].std(axis=1,ddof=1),.005)
    scale=cfg.scale_mult*q*sigma
    pnl=[];values=[];wrong=[];activity=[];switches=np.zeros(B);parks=np.zeros(B);revives=np.zeros(B)
    trace=[];local_regret=[]
    for t in range(cfg.warmup,T):
        active=ctrl.active.copy();score,raw,book=paired_scores(r[:,t],active,cfg,scale)
        changed=active!=previous;net=book-cfg.switch_cost*q*changed.sum(axis=1)
        ce=conditional_value(active,sample.means[:,t],sample.rho[t],sample.scale2[:,t],sample.common_var,cfg,previous)
        d=marginal_mean(active,sample.means[:,t],sample.rho[t],sample.scale2[:,t],sample.common_var,cfg)
        if M==1:
            off=np.zeros_like(active);on=np.ones_like(active)
            oracle=np.maximum(conditional_value(off,sample.means[:,t],sample.rho[t],sample.scale2[:,t],sample.common_var,cfg,previous),conditional_value(on,sample.means[:,t],sample.rho[t],sample.scale2[:,t],sample.common_var,cfg,previous))
            local_regret.append(np.maximum(0,oracle-ce))
        switches+=changed.sum(axis=1);parks+=np.sum(previous & ~active,axis=1);revives+=np.sum(~previous & active,axis=1)
        pnl.append(net);values.append(ce);wrong.append(np.mean(np.where(active,d<0,d>0),axis=1));activity.append(active.mean(axis=1))
        previous=active
        accepted,e=ctrl.step(score,np.clip((r[:,t,1:]-cfg.fee)/sigma,-1,1))
        if keep_path:
            trace.append(dict(t=t,return_net=net[0],conditional_utility=ce[0],active_fraction=active[0].mean(),score=score[0,0],marginal_raw_mean=d[0,0],evidence=e[0,0],switched_next=int(accepted[0,0]),alpha_return=r[0,t,1]))
    pnl=np.stack(pnl,axis=1);vals=np.stack(values,axis=1);sd=pnl.std(axis=1,ddof=1)
    if np.any(pnl<=-1): mdd=np.full(B,np.nan)
    else:
        wealth=np.cumprod(1+pnl,axis=1);peaks=np.maximum.accumulate(np.c_[np.ones(B),wealth],axis=1)[:,1:];mdd=np.min(wealth/peaks-1,axis=1)
    out=pd.DataFrame(dict(rep=np.arange(B),method=method,utility=utility(pnl,cfg.gamma).mean(axis=1),conditional_utility=vals.mean(axis=1),mean_return=pnl.mean(axis=1),volatility=sd,sharpe_period=np.divide(pnl.mean(axis=1),sd,out=np.zeros(B),where=sd>0),max_drawdown=mdd,switches=switches,parks=parks,revivals=revives,active_fraction=np.stack(activity,axis=1).mean(axis=1),wrong_state_fraction=np.stack(wrong,axis=1).mean(axis=1),local_oracle_regret=np.stack(local_regret,axis=1).mean(axis=1) if local_regret else np.full(B,np.nan)))
    return out,pd.DataFrame(trace),pnl

def simulate_suite(args):
    cfg=Settings(warmup=args.warmup,max_age=args.max_age);outdir=ROOT/'results'/args.name;outdir.mkdir(parents=True,exist_ok=True)
    allrows=[];traces=[];start=time.time()
    scenarios=SCENARIOS if args.scenarios=='all' else tuple(args.scenarios.split(','))
    noises=NOISES if args.noises=='all' else tuple(args.noises.split(','))
    methods=METHODS if args.methods=='all' else tuple(args.methods.split(','))
    for scenario in scenarios:
        for noise in noises:
            seed=args.seed+1000*SCENARIOS.index(scenario)+10*NOISES.index(noise)
            sample=simulate(scenario,noise,args.reps,args.periods,args.m,seed,args.strength)
            base=evaluate(sample,'always_on',cfg)[0].set_index('rep')
            for method in methods:
                df,path,pnl=evaluate(sample,method,cfg,keep_path=True)
                df['delta_utility']=df['utility'].values-base['utility'].values
                df['delta_conditional_utility']=df['conditional_utility'].values-base['conditional_utility'].values
                df['scenario']=scenario;df['noise']=noise;df['m']=args.m;df['seed']=seed;allrows.append(df)
                path['scenario']=scenario;path['noise']=noise;path['method']=method;traces.append(path)
            print(scenario,noise,'completed',round(time.time()-start,1),'sec',flush=True)
            pd.concat(allrows,ignore_index=True).to_csv(outdir/'replications.csv',index=False)
    raw=pd.concat(allrows,ignore_index=True);rows=[]
    metrics=['utility','delta_utility','delta_conditional_utility','switches','parks','revivals','active_fraction','wrong_state_fraction','local_oracle_regret','sharpe_period']
    for keys,g in raw.groupby(['scenario','noise','m','method'],sort=False):
        row=dict(zip(['scenario','noise','m','method'],keys));row['n']=len(g)
        for metric in metrics:
            v=g[metric].dropna();row[metric]=v.mean();row[metric+'_se']=v.std(ddof=1)/np.sqrt(len(v)) if len(v)>1 else np.nan
        rows.append(row)
    pd.DataFrame(rows).to_csv(outdir/'summary.csv',index=False);pd.concat(traces,ignore_index=True).to_csv(outdir/'first_path.csv',index=False)
    manifest={'settings':asdict(cfg),'arguments':vars(args),'seconds':time.time()-start,'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'executed':True,'empirical':False,'calibrated_to_JKP':False}
    (outdir/'manifest.json').write_text(json.dumps(manifest,indent=2))

def null_suite(args):
    outdir=ROOT/'results'/args.name;outdir.mkdir(parents=True,exist_ok=True);cfg=Settings(warmup=args.warmup,max_age=args.max_age);rows=[]
    for noise in ('iid_bounded','volatility_martingale'):
        hits=0;naive=0
        for begin in range(0,args.reps,100):
            B=min(100,args.reps-begin);rng=np.random.default_rng(args.seed+begin+int(noise!='iid_bounded'));ctrl=Controller((B,args.m),'e_restart',cfg)
            anyswitch=np.zeros(B,bool);naiveswitch=np.zeros(B,bool);prev=np.ones((B,args.m));running=np.zeros((B,args.m));running2=np.zeros((B,args.m))
            for t in range(args.periods):
                common=rng.normal(size=(B,1));eps=.6*common+.8*rng.normal(size=(B,args.m))
                vol=np.clip(.4+.8*np.abs(prev),.25,2) if noise!='iid_bounded' else 1.
                x=np.tanh(eps*vol);accepted,_=ctrl.step(x,x);anyswitch|=accepted.any(axis=1);running+=x;running2+=x*x
                if t>=19:
                    stat=np.divide(running,np.sqrt(np.maximum(running2-running*running/(t+1),1e-12)));naiveswitch|=(np.abs(stat)>1.96).any(axis=1)
                prev=x
            hits+=int(anyswitch.sum());naive+=int(naiveswitch.sum())
        for method,count in [('e_restart',hits),('repeated_unadjusted_z',naive)]:
            lo=0. if count==0 else beta.ppf(.025,count,args.reps-count+1);hi=1. if count==args.reps else beta.ppf(.975,count+1,args.reps-count)
            rows.append(dict(noise=noise,method=method,reps=args.reps,m=args.m,periods=args.periods,lifetime_any_switch=count,args_delta=cfg.delta,rate=count/args.reps,lo=lo,hi=hi))
        print(noise,rows[-2:],flush=True)
    pd.DataFrame(rows).to_csv(outdir/'null_validation.csv',index=False)
    (outdir/'manifest.json').write_text(json.dumps({'arguments':vars(args),'settings':asdict(cfg),'executed':True},indent=2))

def main():
    p=argparse.ArgumentParser();p.add_argument('--task',choices=['simulation','null'],default='simulation');p.add_argument('--name',default='main');p.add_argument('--reps',type=int,default=200);p.add_argument('--periods',type=int,default=1800);p.add_argument('--m',type=int,default=1);p.add_argument('--seed',type=int,default=20261006);p.add_argument('--warmup',type=int,default=60);p.add_argument('--max-age',type=int,default=720);p.add_argument('--strength',type=float,default=1.);p.add_argument('--scenarios',default='all');p.add_argument('--noises',default='gaussian,student');p.add_argument('--methods',default='all');a=p.parse_args()
    if min(a.reps,a.m)<1 or a.periods<=a.warmup:p.error('Invalid dimensions.')
    (null_suite if a.task=='null' else simulate_suite)(a)
if __name__=='__main__':main()
