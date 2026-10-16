"""Causal annual protocol; atomic annual checkpoints and immutable OOS score files."""
import hashlib
import json
import os
import pickle
import time
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
from .config import Config
from .costs import expected_utility
from .dgp import Market
from .eprocess import public_envelope
from .features import serialize_library
from .optimizer import Optimizer, fit_moments
from .policies import Policy
from .selection import Selector
from .oracle import score_moments, true_utility
from .pvalues import hac_pvalue
from .metrics import path_metrics, detection_table

METHODS = ('All Signals','Greedy','Repeated-HAC-p','E-process','Oracle')


def atomic_json(path, obj):
    path=Path(path)
    with tempfile.NamedTemporaryFile(mode='w',dir=path.parent,prefix=path.name+'.',suffix='.tmp',delete=False) as f:
        temp=Path(f.name)
        f.write(json.dumps(obj,indent=2,allow_nan=False)+'\n')
        f.flush();os.fsync(f.fileno())
    temp.replace(path)


def source_fingerprint():
    paths=sorted(Path(__file__).parent.glob('*.py'))
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    return hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest(),files


def checkpoint(path, state):
    # Local generated pickle only: never load an external or downloaded checkpoint.
    temp=path.with_suffix('.tmp')
    with temp.open('wb') as f:
        pickle.dump(state,f,pickle.HIGHEST_PROTOCOL); f.flush(); os.fsync(f.fileno())
    temp.replace(path)


def simulate_seed(cfg, seed, directory, resume=False, stop_after_blocks=None, market_factory=Market):
    directory=Path(directory); directory.mkdir(parents=True,exist_ok=True)
    ckpt=directory/'checkpoint.pkl'
    started=time.perf_counter()
    implementation_hash,source_hashes=source_fingerprint()
    if resume and ckpt.exists():
        with ckpt.open('rb') as f:state=pickle.load(f)
        if state['config_hash']!=cfg.digest or state['seed']!=seed:
            raise ValueError('Checkpoint configuration/seed mismatch')
        if state.get('implementation_hash')!=implementation_hash:
            raise ValueError('Implementation changed since checkpoint; use a new versioned output directory')
    elif ckpt.exists():
        raise FileExistsError('Existing checkpoint: use resume or a new output directory')
    else:
        market=market_factory(cfg,seed)
        history=[]
        for _ in range(cfg.block):
            obs,_=market.step(); history.append(obs.returns.copy())
        bound=public_envelope(cfg)
        selectors={name:Selector(name,cfg,market.ids,bound['nu2'],Policy((),np.zeros(cfg.n_signals)))
                   for name in METHODS[1:4]}
        all_support=tuple(range(cfg.n_signals))
        policies={'All Signals':Policy(all_support,np.zeros(cfg.n_signals)),
                  'Oracle':Policy(all_support,np.zeros(cfg.n_signals))}
        state=dict(config_hash=cfg.digest,implementation_hash=implementation_hash,seed=seed,market=market,history=history,
                   selectors=selectors,policies=policies,reset={n:True for n in selectors},
                   next_year=1,equity={n:1. for n in METHODS},insolvent={n:False for n in METHODS},
                   elapsed=0.,block_runtimes=[])
        atomic_json(directory/'feature_library.json',serialize_library(market.library))
        atomic_json(directory/'moment_envelope.json',bound)
        atomic_json(directory/'source_manifest.json',source_hashes)
        checkpoint(ckpt,state)
    count=0
    while state['next_year']<cfg.years:
        block_start=time.perf_counter()
        year=state['next_year']; day0=year*cfg.block
        market=state['market']; history=state['history']
        selectors=state['selectors']; policies=state['policies']
        mu,second=fit_moments(history,cfg)
        estimated=Optimizer(cfg,mu,second)
        lists=[]; closed=[]
        for name,selector in selectors.items():
            shortlist,cl=selector.refresh(day0,estimated,state['reset'][name])
            lists.append(dict(seed=seed,method=name,day=day0,shortlist=json.dumps([selector.ids[j] for j in shortlist])))
            closed += [dict(comparison_id=cid,day=day0,reason='reference_changed' if state['reset'][name] else 'shortlist_exit') for cid in cl]
            state['reset'][name]=False
        ledger=[]; scores=[]; events=[]; decisions=[]
        block_truth={}
        for _ in range(cfg.block):
            # Prepare every investible weight before receiving the new observation.
            estimated.new_day()
            for policy in policies.values():
                if policy is not policies['Oracle']:policy.prepare(estimated)
            for selector in selectors.values():
                selector.actual.prepare(estimated)
                selector.reference.prepare(estimated)
                for comp in selector.comparisons.values():comp.shadow.prepare(estimated)
            obs,truth=market.step()
            exact=Optimizer(cfg,truth.mean,truth.second)
            policies['Oracle'].prepare(exact)  # true current moments, no realized shock enters solver
            all_actual={**policies,**{n:s.actual for n,s in selectors.items()}}
            for name,policy in all_actual.items():
                b=policy.previous.copy()
                if state['insolvent'][name]:
                    policy.weights=np.zeros(cfg.n_signals)
                conditional=true_utility(policy.weights,b,truth,cfg)
                if cfg.state_matched_oracle and not state['insolvent'][name]:
                    matched=exact.solve(tuple(range(cfg.n_signals)),b)
                    regret=max(0.,matched.value-conditional)
                else:regret=np.nan
                w=policy.weights.copy(); result=policy.realize(obs.returns,cfg)
                if state['insolvent'][name]:
                    # Fund is absorbed at zero; shadow experiments continue for audit.
                    result={k:0. for k in result}
                elif 1+result['net']<=0:
                    state['equity'][name]=0.; state['insolvent'][name]=True
                else:state['equity'][name]*=1+result['net']
                support=policy.support; denom=len(support)
                nonzero=truth.theta>0
                active_true=sum(nonzero[j] for j in support)
                ledger.append(dict(seed=seed,method=name,day=obs.day,**result,
                    equity=state['equity'][name],insolvent=state['insolvent'][name],
                    leverage=float(np.abs(w).sum()),n_active=denom,support=json.dumps(list(support)),weights=w.tolist(),
                    conditional_utility=conditional,state_matched_regret=regret,
                    structural_precision=active_true/denom if denom else np.nan,
                    structural_recall=active_true/max(1,int(nonzero.sum())),
                    noise_fraction=sum(45<=j<85 for j in support)/denom if denom else np.nan,
                    proxy_fraction=sum(j>=85 for j in support)/denom if denom else np.nan,
                    regime=truth.regime,primal_residual=policy.certificate[0],dual_residual=policy.certificate[1],
                    solver_gap=policy.certificate[2]))
            for name,selector in selectors.items():
                ref=selector.reference
                rb=ref.previous.copy(); rw=ref.weights.copy()
                ref_result=ref.realize(obs.returns,cfg)
                for comp in selector.comparisons.values():
                    cb=comp.shadow.previous.copy(); cw=comp.shadow.weights.copy()
                    mean,true_second=score_moments(cw,rw,cb,rb,truth,cfg)
                    if true_second>selector.nu2*(1+1e-10):
                        raise AssertionError('Public moment envelope violated')
                    cr=comp.shadow.realize(obs.returns,cfg)
                    y=cr['utility']-ref_result['utility']
                    comp.append(obs.day,y)
                    block_truth.setdefault(comp.comparison_id,[]).append(mean)
                    scores.append(dict(seed=seed,method=name,day=obs.day,comparison_id=comp.comparison_id,
                        y=y,lambda_value=comp.evidence.bet,log_e=comp.evidence.log_e,
                        candidate_cost=cr['linear_cost']+cr['impact_cost'],reference_cost=ref_result['linear_cost']+ref_result['impact_cost'],
                        true_mean=mean,true_second=true_second))
            history.append(obs.returns.copy())
        end=(year+1)*cfg.block
        for name,selector in selectors.items():
            chosen=None if state['insolvent'][name] else selector.choose()
            for comp in selector.comparisons.values():
                ts=np.asarray(block_truth[comp.comparison_id])
                events.append(dict(seed=seed,method=name,day=end,comparison_id=comp.comparison_id,
                    start=comp.start,reference=json.dumps(comp.reference),candidate=json.dumps(comp.candidate),
                    move=comp.move,added=comp.added,removed=comp.removed,n=comp.evidence.n,
                    mean_y=comp.evidence.mean,block_mean_y=float(np.mean(comp.scores[-cfg.block:])),
                    log_e=comp.evidence.log_e,pvalue=hac_pvalue(comp.scores),lambda_value=comp.evidence.bet,
                    nu2=comp.evidence.nu2,true_block_mean=float(ts.mean()),true_current_mean=float(ts[-1]),
                    selected=comp is chosen,terminal=(year+1==cfg.years)))
            if chosen is not None:
                before=selector.actual.support
                revived=selector.apply(chosen)
                state['reset'][name]=True
                decisions.append(dict(seed=seed,method=name,day=end,comparison_id=chosen.comparison_id,
                    move=chosen.move,added=chosen.added,removed=chosen.removed,revived=revived,
                    support_before=json.dumps(before),support_after=json.dumps(chosen.candidate),
                    mean_y=chosen.evidence.mean,log_e=chosen.evidence.log_e,
                    true_current_mean=block_truth[chosen.comparison_id][-1],
                    true_block_mean=float(np.mean(block_truth[chosen.comparison_id]))))
        blockdir=directory/f'block_{year:02d}';blockdir.mkdir(exist_ok=True)
        pd.DataFrame(ledger).to_parquet(blockdir/'daily_ledger.parquet',index=False)
        pd.DataFrame(scores).to_parquet(blockdir/'score_ledger.parquet',index=False)
        pd.DataFrame(events).to_parquet(blockdir/'comparison_events.parquet',index=False)
        pd.DataFrame(decisions,columns=['seed','method','day','comparison_id','move','added','removed','revived','support_before','support_after','mean_y','log_e','true_current_mean','true_block_mean']).to_csv(blockdir/'decisions.csv',index=False)
        pd.DataFrame(lists).to_csv(blockdir/'shortlists.csv',index=False)
        atomic_json(blockdir/'closed_episodes.json',closed)
        state['next_year']+=1
        state['block_runtimes'].append(dict(seed=seed,year=year,seconds=time.perf_counter()-block_start))
        state['elapsed']+=time.perf_counter()-block_start
        checkpoint(ckpt,state)
        atomic_json(directory/'status.json',dict(seed=seed,config_hash=cfg.digest,completed_blocks=year,
                    total_blocks=cfg.years-1,status='complete' if state['next_year']==cfg.years else 'running'))
        print(f'seed={seed} block={year}/{cfg.years-1} seconds={state["block_runtimes"][-1]["seconds"]:.2f}',flush=True)
        count+=1
        if stop_after_blocks is not None and count>=stop_after_blocks:break
    complete=state['next_year']==cfg.years
    if complete:finalize_seed(cfg,seed,directory,state)
    return dict(seed=seed,complete=complete,elapsed=time.perf_counter()-started)


def finalize_seed(cfg,seed,directory,state):
    blocks=sorted(directory.glob('block_*'))
    frames={name:pd.concat([pd.read_parquet(b/(name+'.parquet')) for b in blocks],ignore_index=True)
            for name in ('daily_ledger','comparison_events')}
    for name,frame in frames.items():frame.to_parquet(directory/(name+'.parquet'),index=False)
    decisions=pd.concat([pd.read_csv(b/'decisions.csv') for b in blocks],ignore_index=True)
    decisions.to_csv(directory/'decisions.csv',index=False)
    events=frames['comparison_events']
    metrics=[]
    for name,g in frames['daily_ledger'].groupby('method',sort=False):
        selected=decisions[decisions.method==name]
        metrics.append(dict(seed=seed,method=name,**path_metrics(g,cfg.block),moves=len(selected),
            economic_precision=float((selected.true_block_mean>cfg.economic_tolerance).mean()) if len(selected) else np.nan,
            current_sign_error_rate=float((selected.true_current_mean < -cfg.economic_tolerance).mean()) if len(selected) else np.nan))
    pd.DataFrame(metrics).to_csv(directory/'metrics_by_seed.csv',index=False)
    detection_table(events,decisions,cfg).to_csv(directory/'detection.csv',index=False)
    pd.DataFrame(state['block_runtimes']).to_csv(directory/'runtime.csv',index=False)
