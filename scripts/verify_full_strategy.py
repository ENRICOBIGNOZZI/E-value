#!/usr/bin/env python3
"""Replay scores, costs, evidence and ghost labels without checkpoint/process state."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
from scipy.special import logsumexp

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'research')]
from park_revive.config import Config
from park_revive.dgp import Market
from park_revive.costs import utility
from park_revive.eprocess import public_envelope
from park_revive.features import evaluate
from park_revive.sleeves import sleeve_weights
from park_revive_extensions.certificates import PublicRisk,paired_score_caps


def expand(compact,order,key):
    dense=np.zeros((len(order),100))
    for j,item in enumerate(order):dense[j,item[key]]=compact[j,:len(item[key])]
    return dense


def costs(w,b,cfg):
    change=w-b
    return cfg.proportional*np.sum(np.abs(change),axis=-1)+cfg.impact*np.sum(change*change,axis=-1)/2


def values(w,cost,truth,cfg):
    return w@truth.mean-cfg.gamma*np.sum((w@truth.second)*w,axis=1)/2-cost


def verify_seed(directory,allow_incomplete=False):
    directory=Path(directory);cfg=Config.read(directory/'config_frozen.json')
    status=json.loads((directory/'status.json').read_text());seed=status['seed']
    if not status['complete'] and not allow_incomplete:raise ValueError('Incomplete seed')
    market=Market(cfg,seed)
    for _ in range(cfg.block):market.step()
    previous_actual={n:np.zeros(100) for n in ('All Signals','Greedy','HAC','Catoni','Tail','Oracle')}
    previous_candidates={};previous_references={};pair_references={};catoni={};tail={};score_history={}
    ghost_previous_candidates={};ghost_previous_references={}
    max_error={};checks=0
    def check(key,a,b,atol=1e-12,rtol=1e-9):
        nonlocal checks
        a,b=np.asarray(a),np.asarray(b)
        np.testing.assert_allclose(a,b,atol=atol,rtol=rtol,err_msg=key)
        max_error[key]=max(max_error.get(key,0.),float(np.max(np.abs(a-b),initial=0.)))
        checks+=a.size
    risk=PublicRisk.from_market_contract(cfg);nu2=public_envelope(cfg)['nu2']
    ghost_means={}
    for block in sorted(directory.glob('block_*')):
        order=json.loads((block/'comparison_order.json').read_text())
        arrays={n:np.load(block/f'scores_{n}.npz') for n in order}
        ledger=pd.read_parquet(block/'daily_ledger.parquet')
        ghosts=json.loads((block/'ghost_order.json').read_text())
        ga=np.load(block/'ghosts.npz') if ghosts else None
        bets={}
        for item in order['Catoni']:
            cid=item['comparison_id'];past=score_history.get(cid,[])
            bets[cid]=min((max(0.,sum(past)/len(past)) if past else cfg.delta0)/(2*nu2),1/(2*np.sqrt(nu2)))
        for offset in range(cfg.block):
            public_values=evaluate(np.tanh(market.latent),market.library);p=sleeve_weights(public_values)
            obs,truth=market.step()
            actual_before={n:w.copy() for n,w in previous_actual.items()}
            actual={row.method:row for row in ledger[ledger.day==obs.day].itertuples()}
            for n,row in actual.items():
                w=np.array(row.weights);cost=costs(w,previous_actual[n],cfg)
                gross=w@obs.returns
                check('fund_gross',gross,row.gross);check('fund_net',gross-cost,row.net)
                check('fund_utility',utility(gross,cost,cfg.gamma),row.utility)
                previous_actual[n]=w.copy()
            for n,items in order.items():
                archive=arrays[n];wb=expand(archive['weights'][offset],items,'candidate')
                rw=np.zeros(100);rw[items[0]['reference']]=archive['reference_weights'][offset]
                # New episodes begin at the real previous allocation. Within an
                # episode, both shadow policies keep their own last target.
                actual_previous=actual_before[n]
                bs=previous_references.get(n,actual_previous)
                # A reference support change starts from yesterday's actual fund state.
                ref_key=(n,tuple(items[0]['reference']))
                if offset==0 and ref_key!=previous_references.get((n,'support')):bs=actual_previous
                rc=costs(rw,bs,cfg)
                bb=np.array([previous_candidates.get(x['comparison_id'],actual_previous) for x in items])
                cc=costs(wb,bb,cfg);dc=cc-rc
                y=utility(wb@obs.returns,cc,cfg.gamma)-utility(rw@obs.returns,rc,cfg.gamma)
                check('score',y,archive['y'][offset]);check('cost_difference',dc,archive['cost_difference'][offset])
                mean=values(wb,cc,truth,cfg)-values(rw[None,:],np.array([rc]),truth,cfg)[0]
                check('conditional_score_mean',mean,archive['true_mean'][offset],atol=1e-13)
                if n=='Tail':
                    v2,v4=paired_score_caps(p@wb.T,p@rw[:,None],public_values,dc,cfg.gamma,risk)
                    check('second_cap',v2,archive['second_cap'][offset],atol=1e-18)
                    check('fourth_cap',v4,archive['fourth_cap'][offset],atol=1e-24)
                    levels=np.array([s for s in (2.,4.,8.) for _ in range(3)])[:,None]*v4[None,:]**.25
                    levels=np.where(v4[None,:]>0,levels,1.)
                    bias=np.minimum(v2[None,:]/(4*levels),27*v4[None,:]/(256*levels**3))
                    fractions=np.tile([.25,.5,.75],3)[:,None]
                    lam=np.where(v4[None,:]>0,fractions/(levels+bias),0.)
                    increments=np.log1p(lam*(np.maximum(y[None,:],-levels)-bias))
                logs=[]
                for j,item in enumerate(items):
                    cid=item['comparison_id'];score_history.setdefault(cid,[]).append(float(y[j]))
                    if n=='Catoni':
                        lam=bets[cid];x=lam*y[j]
                        inc=np.sign(x)*np.log1p(abs(x)+x*x/2)-lam*lam*nu2/2
                        catoni[cid]=catoni.get(cid,0.)+inc;logs.append(catoni[cid])
                        check('catoni_predictable_bet',lam,archive['bet'][offset,j])
                    elif n=='Tail':
                        tail[cid]=tail.get(cid,np.zeros(9))+increments[:,j]
                        logs.append(logsumexp(tail[cid])-np.log(9))
                    else:logs.append(0.)
                    previous_candidates[cid]=wb[j].copy()
                    pair_references[cid]=rw.copy()
                check('log_e',logs,archive['log_e'][offset],atol=1e-10)
                previous_references[n]=rw.copy();previous_references[n,'support']=ref_key
            if ghosts:
                gw=expand(ga['weights'][offset],ghosts,'candidate')
                gr=expand(ga['reference_weights'][offset],ghosts,'reference')
                gb=np.array([ghost_previous_candidates.get(g['comparison_id'],previous_candidates[g['comparison_id']]) for g in ghosts])
                gs=np.array([ghost_previous_references.get(g['comparison_id'],pair_references[g['comparison_id']]) for g in ghosts])
                dc=costs(gw,gb,cfg)-costs(gr,gs,cfg)
                check('ghost_cost_difference',dc,ga['cost_difference'][offset])
                mean=values(gw,dc,truth,cfg)-values(gr,np.zeros(len(ghosts)),truth,cfg)
                check('ghost_conditional_mean',mean,ga['true_mean'][offset],atol=1e-13)
                for j,g in enumerate(ghosts):
                    cid=g['comparison_id'];ghost_means.setdefault(cid,[]).append(mean[j])
                    ghost_previous_candidates[cid]=gw[j].copy();ghost_previous_references[cid]=gr[j].copy()
        for archive in arrays.values():archive.close()
        if ga is not None:ga.close()
    if status['complete'] and (directory/'terminal_ghost_order.json').exists():
        ghosts=json.loads((directory/'terminal_ghost_order.json').read_text());ga=np.load(directory/'terminal_ghosts.npz')
        for offset in range(cfg.block):
            _,truth=market.step()
            wb=expand(ga['weights'][offset],ghosts,'candidate');ws=expand(ga['reference_weights'][offset],ghosts,'reference')
            gb=np.array([ghost_previous_candidates.get(g['comparison_id'],previous_candidates[g['comparison_id']]) for g in ghosts])
            gs=np.array([ghost_previous_references.get(g['comparison_id'],pair_references[g['comparison_id']]) for g in ghosts])
            dc=costs(wb,gb,cfg)-costs(ws,gs,cfg)
            check('terminal_ghost_cost_difference',dc,ga['cost_difference'][offset])
            mean=values(wb,dc,truth,cfg)-values(ws,np.zeros(len(ghosts)),truth,cfg)
            check('terminal_ghost_conditional_mean',mean,ga['true_mean'][offset],atol=1e-13)
            for j,g in enumerate(ghosts):
                cid=g['comparison_id'];ghost_means.setdefault(cid,[]).append(mean[j])
                ghost_previous_candidates[cid]=wb[j].copy();ghost_previous_references[cid]=ws[j].copy()
        ga.close()
    if status['complete']:
        opportunities=json.loads((directory/'economic_opportunities.json').read_text())
        for event in opportunities:
            if event['confirmation_day']>event['termination_day']:
                mean=np.mean(ghost_means[event['comparison_id']])
                if mean<=cfg.economic_tolerance:raise AssertionError('Unstable ghost entered stable risk set')
    return dict(seed=seed,checks=checks,max_absolute_errors=max_error,
                ghost_pairs_checked=len(ghost_means),complete=status['complete'],
                scope='arithmetic replay; no optimizer optimality or global type-I claim')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--allow-incomplete',action='store_true')
    args=parser.parse_args()
    results=[]
    for directory in sorted(args.output.glob('seed_*')):
        result=verify_seed(directory,args.allow_incomplete);results.append(result)
        print(json.dumps(result),flush=True)
    (args.output/'arithmetic_verification.json').write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':main()
