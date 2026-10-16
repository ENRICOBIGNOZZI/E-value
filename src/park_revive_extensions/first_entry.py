"""Fresh-seed mechanism audit: fixed empty reference, no post-entry performance claim."""
import argparse
from dataclasses import asdict
from math import comb,factorial
from pathlib import Path
import hashlib
import json
import pickle
import subprocess
import sys
import time
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from park_revive.config import Config
from park_revive.dgp import Market
from park_revive.features import evaluate
from park_revive.sleeves import sleeve_weights
from park_revive.eprocess import phi,public_envelope
from park_revive.backtest import atomic_json,checkpoint
from .certificates import PublicRisk,forward_score_caps,uniform_forward_caps
from .tail_betting import TailMixture

ARMS=('Catoni-baseline','Catoni-geometry','Tail-uniform','Tail-geometry')


def implementation_manifest():
    paths=sorted(Path('src').rglob('*.py'))
    manifest={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    return hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest(),manifest


def exact_forward_truth(weights,costs,truth,gamma):
    """Evaluator-only first, second and fourth score moments, with Laplace cumulants."""
    w=weights;mu=w*truth.mean;h=truth.loadings
    cumulants={2:np.sum(h*h,axis=1)*w**2,
               4:3*np.sum(h**4,axis=1)*w**4,
               6:30*np.sum(h**6,axis=1)*w**6,
               8:630*np.sum(h**8,axis=1)*w**8}
    centered=[np.ones_like(w)]
    for n in range(1,9):
        centered.append(sum((comb(n-1,k-1)*value*centered[n-k]
                             for k,value in cumulants.items() if k<=n),np.zeros_like(w)))
    raw=[sum((comb(n,k)*mu**(n-k)*centered[k] for k in range(n+1)),np.zeros_like(w)) for n in range(9)]
    first=raw[1]-gamma*raw[2]/2-costs
    second=raw[2]+gamma**2*raw[4]/4+costs**2-gamma*raw[3]-2*costs*raw[1]+gamma*costs*raw[2]
    fourth=np.zeros_like(w)
    for i in range(5):
        for j in range(5-i):
            k=4-i-j
            fourth+=factorial(4)/(factorial(i)*factorial(j)*factorial(k))*(-gamma/2)**j*(-costs)**k*raw[i+2*j]
    return first,np.maximum(second,0.),np.maximum(fourth,0.)


def run_seed(cfg,seed,root,resume=False,stop_after_blocks=None):
    if cfg.stress_multiplier<1 or np.any(np.asarray(cfg.beta_bounds)<np.array([1.5,1.,1.,1.])):
        raise ValueError('Frozen Catoni arm requires its original valid volatility and loading caps')
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    fingerprint,manifest=implementation_manifest();ckpt=root/'checkpoint.pkl'
    risk=PublicRisk.from_market_contract(cfg);uniform2,uniform4=uniform_forward_caps(cfg,risk)
    constant=public_envelope(cfg)['nu2']
    if ckpt.exists():
        if not resume:raise FileExistsError('Use --resume for an existing run')
        with ckpt.open('rb') as f:state=pickle.load(f)
        if state['implementation_hash']!=fingerprint or state['config_hash']!=cfg.digest:
            raise ValueError('Changed code or configuration: use a new named output directory')
    else:
        market=Market(cfg,seed);history=[]
        for _ in range(cfg.block):history.append(market.step()[0].returns.copy())
        state=dict(seed=seed,implementation_hash=fingerprint,config_hash=cfg.digest,
            market=market,history=history,previous=np.zeros(100),total=np.zeros(100),n=0,
            log_constant=np.zeros(100),log_geometry=np.zeros(100),
            tail_uniform=TailMixture(100),tail_geometry=TailMixture(100),next_year=1,
            first_cross={a:np.full(100,-1,dtype=int) for a in ARMS},elapsed=0.)
        atomic_json(root/'source_manifest.json',manifest)
        checkpoint(ckpt,state)
    blocks_done=0
    while state['next_year']<cfg.years:
        start=time.perf_counter();year=state['next_year'];market=state['market']
        history=np.asarray(state['history']);mu=history.mean(axis=0)
        diag=np.mean(history*history,axis=0)+cfg.ridge  # Shrinkage leaves diagonal unchanged.
        effect=np.full(100,cfg.delta0) if state['n']==0 else np.maximum(state['total']/state['n'],0.)
        constant_bet=np.minimum(effect/(2*constant),1/(2*np.sqrt(constant)))
        uniform_prepared=state['tail_uniform'].prepare(uniform2,uniform4)
        ledger=[];max_violation2=0.;max_violation4=0.
        for _ in range(cfg.block):
            # All below is public and prepared BEFORE the new return/shock.
            values=evaluate(np.tanh(market.latent),market.library)
            sleeves=sleeve_weights(values)
            previous=state['previous'];gradient=mu-cfg.gamma*diag*previous
            weight=np.clip(previous+np.sign(gradient)*np.maximum(np.abs(gradient)-cfg.proportional,0)/(cfg.gamma*diag+cfg.impact),-cfg.leverage,cfg.leverage)
            costs=cfg.proportional*np.abs(weight-previous)+cfg.impact*(weight-previous)**2/2
            geometric2,geometric4=forward_score_caps(weight,previous,values,sleeves,cfg,risk)
            geom_bet=np.zeros(100);positive=geometric2>0
            geom_bet[positive]=np.minimum(effect[positive]/(2*geometric2[positive]),1/(2*np.sqrt(geometric2[positive])))
            geometric_prepared=state['tail_geometry'].prepare(geometric2,geometric4)
            obs,truth=market.step()
            gross=weight*obs.returns;y=gross-cfg.gamma*gross*gross/2-costs
            state['log_constant']+=phi(constant_bet*y)-constant_bet*constant_bet*constant/2
            state['log_geometry']+=phi(geom_bet*y)-geom_bet*geom_bet*geometric2/2
            state['tail_uniform'].update(y,uniform_prepared)
            state['tail_geometry'].update(y,geometric_prepared)
            true_mean,true2,true4=exact_forward_truth(weight,costs,truth,cfg.gamma)
            # Oracle quantities are evaluated ONLY after all previsible test inputs.
            if np.any(true2>geometric2*(1+1e-9)+1e-22) or np.any(true4>geometric4*(1+1e-9)+1e-30):
                raise AssertionError('Geometric conditional-moment contract violated')
            max_violation2=max(max_violation2,float(np.max(np.divide(true2,geometric2,out=np.zeros(100),where=geometric2>0))))
            max_violation4=max(max_violation4,float(np.max(np.divide(true4,geometric4,out=np.zeros(100),where=geometric4>0))))
            state['total']+=y;state['n']+=1;state['previous']=weight.copy()
            state['history'].append(obs.returns.copy())
            ledger.append(dict(seed=seed,day=obs.day,score=y.tolist(),weights=weight.tolist(),
                geometric_second=geometric2.tolist(),geometric_fourth=geometric4.tolist(),
                true_mean=true_mean.tolist(),true_second=true2.tolist(),true_fourth=true4.tolist()))
        end=(year+1)*cfg.block;means=state['total']/state['n']
        logs={ARMS[0]:state['log_constant'],ARMS[1]:state['log_geometry'],
              ARMS[2]:state['tail_uniform'].log_e,ARMS[3]:state['tail_geometry'].log_e}
        events=[]
        for name,loge in logs.items():
            eligible=(loge>=np.log(1/cfg.alpha))&(means>0)
            newly=eligible&(state['first_cross'][name]<0)
            state['first_cross'][name][newly]=end
            for j in range(100):
                events.append(dict(seed=seed,arm=name,day=end,signal=f's{j:03}',log_e=loge[j],
                    mean_score=means[j],eligible=bool(eligible[j]),first_cross_day=int(state['first_cross'][name][j]),
                    true_current_mean=true_mean[j],true_block_mean=float(np.mean([row['true_mean'][j] for row in ledger]))))
        blockdir=root/f'block_{year:02}';blockdir.mkdir(exist_ok=True)
        pd.DataFrame(ledger).to_parquet(blockdir/'score_ledger.parquet',index=False)
        pd.DataFrame(events).to_csv(blockdir/'annual_events.csv',index=False)
        seconds=time.perf_counter()-start;state['elapsed']+=seconds;state['next_year']+=1
        atomic_json(blockdir/'audit.json',dict(max_true_second_over_certificate=max_violation2,
            max_true_fourth_over_certificate=max_violation4,seconds=seconds))
        checkpoint(ckpt,state)
        atomic_json(root/'status.json',dict(seed=seed,completed_blocks=year,total_blocks=cfg.years-1,
            status='complete' if state['next_year']==cfg.years else 'running'))
        print(f'first-entry seed={seed} block={year}/{cfg.years-1} seconds={seconds:.2f}',flush=True)
        blocks_done+=1
        if stop_after_blocks and blocks_done>=stop_after_blocks:break
    if state['next_year']==cfg.years:
        events=pd.concat([pd.read_csv(p/'annual_events.csv') for p in sorted(root.glob('block_*'))],ignore_index=True)
        events.to_csv(root/'annual_events.csv',index=False)
        summary=[]
        for name in ARMS:
            first=state['first_cross'][name];detected=first[first>=0]
            summary.append(dict(seed=seed,arm=name,first_entry_day=int(detected.min()) if len(detected) else -1,
                crossed_signals=len(detected),max_annual_log_e=float(events.loc[events.arm.eq(name),'log_e'].max()),
                right_censored=len(detected)==0,elapsed_seconds=state['elapsed']))
        pd.DataFrame(summary).to_csv(root/'summary.csv',index=False)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',default='configs/main.json');parser.add_argument('--output',required=True)
    parser.add_argument('--seeds',nargs='+',type=int,required=True);parser.add_argument('--resume',action='store_true')
    parser.add_argument('--stop-after-blocks',type=int)
    args=parser.parse_args()
    if not set(args.seeds)<=set(range(40001,40021)):raise ValueError('Use the registered fresh pool 40001–40020')
    cfg=Config.read(args.config);root=Path(args.output);root.mkdir(parents=True,exist_ok=True)
    protocol=dict(kind='first-entry-mechanism-only',arms=ARMS,mixture_scales=[2,4,8],fractions=[.25,.5,.75],
        representative_seed=40001,seed_pool=list(range(40001,40021)),risk=asdict(PublicRisk.from_market_contract(cfg)),
        baseline_commit='971510b',config=cfg.to_dict(),config_hash=cfg.digest,
        implementation_hash=implementation_manifest()[0],individual_alpha=cfg.alpha,
        no_global_multiple_testing_control=True,no_post_entry_performance=True)
    path=root/'protocol_frozen.json'
    if path.exists() and json.loads(path.read_text())!=json.loads(json.dumps(protocol)):
        raise ValueError('Frozen extension protocol differs; use a new output directory')
    atomic_json(path,protocol)
    (root/'environment.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze']).decode())
    with threadpool_limits(limits=1):
        for seed in args.seeds:run_seed(cfg,seed,root/f'seed_{seed}',args.resume,args.stop_after_blocks)


if __name__=='__main__':main()
