#!/usr/bin/env python3
"""Predictable Catoni bets targeting a declared finite review horizon.

Bellman optimality is for a discretized working Gaussian score model; validity
uses the public moment contract, not the correctness of that working model.
No financial configuration or running scientific package is modified.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import pandas as pd
from scipy.fft import rfft,irfft,next_fast_len
from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.stats import norm


def phi(x):
    return np.sign(x)*np.log1p(np.abs(x)+x*x/2)


def inverse_phi(x):
    return np.sign(x)*np.expm1(np.log(2*np.exp(np.abs(x))-1)/2)


def log_growth_bet(cfg):
    mean=cfg['design_mean'];sd=cfg['score_sd'];bound=cfg['public_second']
    cap=cfg['cap_multiplier']/np.sqrt(bound)
    def gradient(lam):
        def integrand(z):
            y=mean+sd*z;x=lam*abs(y)
            return y*(1+x)/(1+x+x*x/2)*norm.pdf(z)
        return quad(integrand,-12,12,epsabs=1e-12,epsrel=1e-12)[0]-lam*bound
    if gradient(0)<=0:return 0.
    return cap if gradient(cap)>=0 else brentq(gradient,0,cap,xtol=1e-13)


def block_kernels(cfg,actions,step):
    """Exact Gaussian CDF bins, then FFT convolution of a full constant-bet block."""
    bound=cfg['public_second'];mean=cfg['design_mean'];sd=cfg['score_sd'];block=cfg['block']
    tail=cfg['gaussian_tail_sd']
    extremes=np.array([mean-tail*sd,mean+tail*sd])
    changes=phi(actions[:,None]*extremes)-actions[:,None]**2*bound/2
    radius=int(np.ceil(np.max(np.abs(changes))/step))+2
    edges=(np.arange(-radius,radius+2)-.5)*step
    full_length=2*radius*block+1;size=next_fast_len(full_length)
    keep_radius=min(int(np.ceil(cfg['increment_range']/step)),radius*block)
    kernels=[];max_daily_tail=0.;max_block_tail=0.;max_mass_error=0.
    for lam in actions:
        if lam==0:
            row=np.zeros(2*keep_radius+1);row[keep_radius]=1.;kernels.append(row);continue
        scores=inverse_phi(edges+lam*lam*bound/2)/lam
        cdf=norm.cdf((scores-mean)/sd)
        daily=np.diff(cdf);outside=float(cdf[0]+1-cdf[-1]);max_daily_tail=max(max_daily_tail,outside)
        daily[0]+=cdf[0];daily[-1]+=1-cdf[-1]
        convolved=irfft(rfft(daily,size)**block,size)[:full_length]
        max_mass_error=max(max_mass_error,abs(float(convolved.sum())-1))
        # Roundoff can create tiny negative Fourier masses; quantify, then normalize.
        if np.min(convolved)<-1e-12:raise ArithmeticError('Negative convolution mass')
        convolved=np.maximum(0.,convolved);convolved/=convolved.sum()
        center=radius*block;start=center-keep_radius;stop=center+keep_radius+1
        block_tail=float(convolved[:start].sum()+convolved[stop:].sum())
        max_block_tail=max(max_block_tail,block_tail)
        row=convolved[start:stop].copy();row[0]+=convolved[:start].sum();row[-1]+=convolved[stop:].sum()
        kernels.append(row)
    if max_daily_tail>1e-12 or max_block_tail>1e-10 or max_mass_error>1e-8:
        raise ArithmeticError('Transition truncation or Fourier mass audit failed')
    return np.array(kernels),dict(daily_radius=radius,block_radius=keep_radius,
        maximum_daily_tail=max_daily_tail,maximum_block_tail=max_block_tail,maximum_mass_error=max_mass_error)


def build_model(cfg,settings):
    step=settings['step'];boundary=np.log(1/cfg['alpha']);cap=cfg['cap_multiplier']/np.sqrt(cfg['public_second'])
    certificate=cfg['design_mean']/(2*cfg['public_second']);growth=log_growth_bet(cfg)
    actions=np.unique(np.r_[np.linspace(0,cap,settings['actions']),certificate,growth])
    intervals=int(np.ceil((boundary-settings['lower'])/step))
    states=boundary+step*np.arange(-intervals,1)
    kernels,audit=block_kernels(cfg,actions,step);radius=(kernels.shape[1]-1)//2
    length=len(states);padded_length=length+2*radius
    fft_length=next_fast_len(padded_length+2*radius)
    kernel_transform=rfft(kernels[:,::-1],fft_length,axis=1)
    blocks=max(cfg['horizon_blocks']);values=np.zeros((blocks+1,length));values[:,-1]=1.
    policy=np.zeros((blocks+1,length),dtype=np.uint16)
    for remaining in range(1,blocks+1):
        padded=np.r_[np.zeros(radius),values[remaining-1],np.ones(radius)]
        transformed=rfft(padded,fft_length)
        expectation=irfft(kernel_transform*transformed[None,:],fft_length,axis=1)[:,2*radius:2*radius+length]
        expectation=np.clip(expectation,0.,1.);expectation[:,-1]=1.
        choices=np.argmax(expectation,axis=0)
        values[remaining]=expectation[choices,np.arange(length)];policy[remaining]=choices
        if np.any(values[remaining]<values[remaining-1]-1e-10):raise ArithmeticError('Bellman horizon monotonicity failed')
        if np.any(np.diff(values[remaining])<-1e-10):raise ArithmeticError('Bellman state monotonicity failed')
    return dict(states=states,actions=actions,values=values,policy=policy,step=np.array(step)),audit


def choose(model,remaining,capital):
    position=np.rint((capital-model['states'][0])/float(model['step'])).astype(int)
    position=np.clip(position,0,len(model['states'])-1)
    lam=model['actions'][model['policy'][remaining,position]]
    # The computational lower boundary is absorbing, rather than silently extrapolated.
    return np.where(capital<model['states'][0],0.,lam)


def simulate(cfg,mean,stream,models):
    reps=cfg['replications'];block=cfg['block'];maximum=max(cfg['horizon_blocks'])
    names=['Past-mean certificate','Fixed certificate','Fixed log growth','One-block power']
    for model_name in models:
        names.extend(f'DP {model_name} H={h*block}' for h in cfg['horizon_blocks'])
    rng=np.random.default_rng(stream);capital=np.zeros((len(names),reps));first=np.full_like(capital,-1,dtype=int)
    score_total=np.zeros(reps);logs=[capital.copy()];stakes=[];prefix=[];rows=[]
    bound=cfg['public_second'];cap=cfg['cap_multiplier']/np.sqrt(bound);boundary=np.log(1/cfg['alpha'])
    fixed=cfg['design_mean']/(2*bound);growth=log_growth_bet(cfg)
    for k in range(maximum):
        bets=np.zeros_like(capital)
        signal=np.full(reps,cfg['initial_gain']) if k==0 else np.maximum(0.,score_total/(k*block))
        bets[0]=np.minimum(signal/(2*bound),cap);bets[1]=fixed;bets[2]=growth
        bets[3]=choose(models['primary'],1,capital[3])
        index=4
        for model in models.values():
            for horizon in cfg['horizon_blocks']:
                if k<horizon:bets[index]=choose(model,horizon-k,capital[index])
                index+=1
        bets=np.where(first>0,0.,bets)
        # All target-dependent choices precede the next score block.
        y=mean+cfg['score_sd']*rng.normal(size=(block,reps))
        prefix.append(y[:,:cfg['audit_path_prefix']].copy());stakes.append(bets.copy())
        for j,lam in enumerate(bets):
            increment=phi(y*lam[None,:]).sum(axis=0)-block*lam*lam*bound/2
            capital[j]+=increment
            hit=(first[j]<0)&(capital[j]>=boundary);first[j,hit]=(k+1)*block
        score_total+=y.sum(axis=0);logs.append(capital.copy())
        if k+1 in cfg['horizon_blocks']:
            for j,name in enumerate(names):
                if name.startswith('DP ') and not name.endswith(f'H={(k+1)*block}'):continue
                success=first[j]>0;p=float(success.mean());z=1.959963984540054
                center=(p+z*z/(2*reps))/(1+z*z/reps)
                radius=z*np.sqrt(p*(1-p)/reps+z*z/(4*reps**2))/(1+z*z/reps)
                rows.append(dict(mean=mean,method=name,observations=(k+1)*block,replications=reps,
                    crossings=int(success.sum()),power=p,wilson_low=max(0.,center-radius),wilson_high=min(1.,center+radius),
                    mean_log_capital=float(capital[j].mean())))
    arrays=dict(methods=np.array(names),log_capital=np.stack(logs),stakes=np.stack(stakes),
                first_crossings=first,audit_scores=np.concatenate(prefix),mean=np.array(mean))
    return arrays,rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('build','evaluate'))
    parser.add_argument('--config',type=Path,default=Path('configs/lambda_power.json'))
    parser.add_argument('--output',type=Path,default=Path('outputs/lambda_power_v1'))
    args=parser.parse_args();cfg=json.loads(args.config.read_text());args.output.mkdir(parents=True,exist_ok=True)
    source_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();started=time.perf_counter()
    if args.stage=='build':
        audits={};initial={}
        for name,settings in cfg['models'].items():
            model,audit=build_model(cfg,settings);np.savez_compressed(args.output/f'model_{name}.npz',**model)
            audits[name]=audit;initial[name]={str(h*cfg['block']):float(np.interp(0,model['states'],model['values'][h])) for h in cfg['horizon_blocks']}
            print(name,initial[name],audit,flush=True)
        difference=max(abs(initial['primary'][h]-initial['refinement'][h]) for h in initial['primary'])
        if difference>cfg['numerical_power_tolerance']:raise ArithmeticError('Bellman refinement needs greater numerical resolution before evaluation')
        (args.output/'model_manifest.json').write_text(json.dumps(dict(config=cfg,source_sha256=source_hash,
            audits=audits,initial_power=initial,max_refinement_difference=difference,log_growth_bet=log_growth_bet(cfg)),indent=2)+'\n')
    else:
        if (args.output/'status.json').exists():raise FileExistsError('Completed study retained; use a new version')
        manifest=json.loads((args.output/'model_manifest.json').read_text())
        if manifest['source_sha256']!=source_hash or manifest['config']!=cfg:raise ValueError('Working-model source/configuration mismatch')
        models={}
        for name in cfg['models']:
            with np.load(args.output/f'model_{name}.npz') as file:models[name]={key:file[key] for key in file.files}
        rows=[];streams=np.random.SeedSequence(cfg['seed']).spawn(len(cfg['score_means']))
        for mean,stream in zip(cfg['score_means'],streams):
            arrays,summary=simulate(cfg,mean,stream,models);rows.extend(summary)
            np.savez_compressed(args.output/f'mean_{mean:g}.npz',**arrays)
            pd.DataFrame(rows).to_csv(args.output/'summary.csv',index=False)
            print('mean',mean,'complete',flush=True)
        if hashlib.sha256(Path(__file__).read_bytes()).hexdigest()!=source_hash:raise RuntimeError('Scientific study source changed during execution')
        (args.output/'status.json').write_text(json.dumps(dict(complete=True,config=cfg,source_sha256=source_hash,
            seconds=time.perf_counter()-started,scope='Controlled Gaussian score study. Each bet uses a predeclared working alternative and pre-block capital/past scores. Bellman optimization is for the declared discretized model, not globally optimal power under every law or financial outperformance.'),indent=2)+'\n')


if __name__=='__main__':main()
