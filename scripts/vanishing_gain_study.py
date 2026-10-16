#!/usr/bin/env python3
"""Declared scalar diagnostics; not additional full financial market replications."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import pandas as pd

METHODS=('Linear cash-PARK','Catoni geometry fixed','Catoni uniform fixed','Catoni uniform past-mean')


def null_parameters(w,cfg):
    a=cfg['gamma']*cfg['sigma']*w/2
    denominator=1+a*a
    return a*cfg['sigma']/denominator,cfg['sigma']/denominator


def simulate(cfg,law,seed_sequence):
    rng=np.random.default_rng(seed_sequence);reps=cfg['replications'];steps=cfg['observations']
    gamma=cfg['gamma'];sigma=cfg['sigma'];limit=cfg['leverage'];lam=gamma/2
    m2=cfg['public_second'];m4=cfg['public_fourth'];block=cfg['review_block']
    nu2=limit**2*(np.sqrt(m2)+gamma*limit*np.sqrt(m4)/2)**2
    training=rng.normal(0,sigma,(cfg['training'],reps))
    total=training.sum(axis=0);squares=(training*training).sum(axis=0)
    capital=np.zeros((4,reps));score_sum=np.zeros(reps);bet=np.zeros(reps)
    sum_w2=np.zeros(reps);benefit=np.zeros(reps);log_lr=np.zeros(reps)
    levels=np.array(cfg['levels']);thresholds=np.log(1/levels)
    first=np.full((4,len(levels),reps),-1,dtype=np.int64);annual_first=first.copy()
    grid=np.unique(np.r_[1,2**np.arange(1,int(np.log2(steps))+1),
                         np.arange(block,steps+1,block),steps]).astype(int)
    snapshots=[];times=[];minimum_factor=1.;max_null_mean_error=0.
    for t in range(1,steps+1):
        n=cfg['training']+t-1
        w=np.clip((total/n)/(gamma*(squares/n+cfg['ridge'])),-limit,limit)
        # Bets, target and feedback-law moments are formed before drawing A_t.
        if (t-1)%block==0:
            average=np.full(reps,cfg['initial_gain']) if t==1 else np.maximum(0.,score_sum/(t-1))
            bet=np.minimum(average/(2*nu2),1/(2*np.sqrt(nu2)))
        null_mean,null_sd=null_parameters(w,cfg)
        if law=='gaussian_alternative':mean=np.zeros(reps);sd=sigma
        elif law=='gaussian_feedback_null':
            mean=null_mean;sd=null_sd
            raw_second=mean*mean+sd*sd
            max_null_mean_error=max(max_null_mean_error,float(np.max(np.abs(-w*mean+gamma*w*w*raw_second/2))))
        else:raise ValueError(law)
        a=mean+sd*rng.normal(size=reps)
        gain=-w*a+gamma*w*w*a*a/2
        geometry=w*w*(np.sqrt(m2)+gamma*np.abs(w)*np.sqrt(m4)/2)**2
        x=lam*gain;phi=np.sign(x)*np.log1p(np.abs(x)+x*x/2)
        factor=1+x
        minimum_factor=min(minimum_factor,float(factor.min()))
        if np.any(factor<.75-1e-14):raise ArithmeticError('Cash-PARK lower bound failed')
        capital[0]+=np.log1p(x)
        capital[1]+=phi-lam*lam*geometry/2
        capital[2]+=phi-lam*lam*nu2/2
        z=bet*gain
        capital[3]+=np.sign(z)*np.log1p(np.abs(z)+z*z/2)-bet*bet*nu2/2
        standardized=a/sigma;feedback=gamma*sigma*w/2
        f2=feedback*feedback
        log_lr+=-np.log1p(f2)+(f2+f2*f2/2)*standardized**2-feedback*(1+f2)*standardized+f2/2
        sum_w2+=w*w
        benefit+=-w*mean+gamma*w*w*(mean*mean+sd*sd)/2
        score_sum+=gain
        crossed=capital[:,None,:]>=thresholds[None,:,None]
        first[(first<0)&crossed]=t
        if t%block==0:annual_first[(annual_first<0)&crossed]=t
        if t in grid:
            times.append(t)
            snapshots.append(dict(log_capital=capital.copy(),log_likelihood_ratio=log_lr.copy(),
                sum_w2=sum_w2.copy(),conditional_benefit=benefit.copy(),realized_benefit=score_sum.copy(),
                past_mean_bet=bet.copy()))
        total+=a;squares+=a*a
    result={key:np.stack([s[key] for s in snapshots]) for key in snapshots[0]}
    result.update(times=np.array(times),first_crossings=first,annual_first_crossings=annual_first,
                  minimum_factor=np.array(minimum_factor),max_null_mean_error=np.array(max_null_mean_error))
    return result


def summarize(cfg,law,arrays):
    rows=[];reps=cfg['replications'];z=1.959963984540054
    for j,t in enumerate(arrays['times']):
        for method_index,method in enumerate(METHODS):
            logs=arrays['log_capital'][j,method_index]
            for level_index,alpha in enumerate(cfg['levels']):
                hit=arrays['first_crossings'][method_index,level_index]
                successes=int(((hit>0)&(hit<=t)).sum());p=successes/reps
                center=(p+z*z/(2*reps))/(1+z*z/reps)
                radius=z*np.sqrt(p*(1-p)/reps+z*z/(4*reps*reps))/(1+z*z/reps)
                annual=arrays['annual_first_crossings'][method_index,level_index]
                rows.append(dict(law=law,method=method,observations=int(t),replications=reps,alpha=alpha,
                    crossings=successes,crossing_fraction=p,wilson_low=max(0.,center-radius),wilson_high=min(1.,center+radius),
                    annual_crossings=int(((annual>0)&(annual<=t)).sum()),mean_log_capital=float(logs.mean()),
                    mc_se_log_capital=float(logs.std(ddof=1)/np.sqrt(reps)),
                    mean_sum_w2=float(arrays['sum_w2'][j].mean()),
                    mean_conditional_benefit=float(arrays['conditional_benefit'][j].mean()),
                    mean_log_lr=float(arrays['log_likelihood_ratio'][j].mean()),
                    mean_absolute_log_lr_difference=float(np.mean(np.abs(logs-arrays['log_likelihood_ratio'][j])))))
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=Path('configs/vanishing_gain.json'))
    parser.add_argument('--output',type=Path,default=Path('outputs/vanishing_gain_v1'))
    args=parser.parse_args();cfg=json.loads(args.config.read_text());args.output.mkdir(parents=True,exist_ok=True)
    if (args.output/'status.json').exists():raise FileExistsError('Use a new version for another run')
    script_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (args.output/'config_frozen.json').write_text(json.dumps(cfg,indent=2)+'\n')
    streams=np.random.SeedSequence(cfg['seed']).spawn(len(cfg['laws']));rows=[];checks={};started=time.perf_counter()
    for law,stream in zip(cfg['laws'],streams):
        arrays=simulate(cfg,law,stream);np.savez_compressed(args.output/f'{law}.npz',**arrays)
        rows.extend(summarize(cfg,law,arrays));checks[law]={key:float(arrays[key]) for key in ('minimum_factor','max_null_mean_error')}
        print(law,'complete',flush=True)
    pd.DataFrame(rows).to_csv(args.output/'summary.csv',index=False)
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest()!=script_hash:
        raise RuntimeError('Controlled-study source changed during execution')
    status=dict(complete=True,config=cfg,script_sha256=script_hash,seconds=time.perf_counter()-started,
        checks=checks,scope='Controlled scalar, single costless comparison without the financial minimum-effect floor; not extra financial markets or an expected stopping-time theorem.')
    (args.output/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(status),flush=True)


if __name__=='__main__':main()
