#!/usr/bin/env python3
"""Replay scores, costs, evidence and ghost labels without checkpoint/process state."""
import argparse
import json
from math import comb,factorial
from pathlib import Path
import sys
import numpy as np
import pandas as pd
from scipy.special import logsumexp
from scipy.stats import norm

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'research')]
from park_revive.config import Config
from park_revive.dgp import Market
from park_revive.costs import utility
from park_revive.eprocess import public_envelope
from park_revive.features import evaluate
from park_revive.sleeves import sleeve_weights


def expand(compact,order,key):
    dense=np.zeros((len(order),100))
    for j,item in enumerate(order):dense[j,item[key]]=compact[j,:len(item[key])]
    return dense


def costs(w,b,cfg):
    change=w-b
    square=change@change if change.ndim==1 else np.sum(change*change,axis=1)
    return cfg.proportional*np.sum(np.abs(change),axis=-1)+cfg.impact*square/2


def values(w,cost,truth,cfg):
    return w@truth.mean-cfg.gamma*np.sum((w@truth.second)*w,axis=1)/2-cost


def replay_caps(d,s,features,dc,cfg):
    """Separate arithmetic implementation of the public certificate formulas."""
    cap=cfg.base_theta*cfg.theta_cap_multiple;budget=cap*(15+10/4+10+10)
    allocation=np.clip(budget-cap*np.arange(cfg.n_signals),0,cap)
    maximum=max(1.,cfg.stress_multiplier)
    scales=maximum*np.array(cfg.factor_scales)
    def mean_bound(q):
        coefficients=features.T@q
        positive=np.sort(np.maximum(coefficients,0),axis=0)[::-1]
        negative=np.sort(np.maximum(-coefficients,0),axis=0)[::-1]
        return np.maximum(allocation@positive,allocation@negative)
    def variance_bound(q):
        net=np.abs(np.sum(q,axis=0));gross=np.sum(np.abs(q),axis=0)
        return scales[0]**2*(net+.5*gross)**2+np.sum(scales[1:]**2)*gross**2+(maximum*cfg.idio_scale)**2*np.sum(q*q,axis=0)
    def moment(m,v,n):
        return sum(comb(n,2*k)*m**(n-2*k)*factorial(2*k)*(v/2)**k for k in range(n//2+1))
    md=mean_bound(d);ms=mean_bound(s);vd=variance_bound(d);vs=variance_bound(s)
    d2=moment(md,vd,2);d4=moment(md,vd,4);s4=moment(ms,vs,4)
    d8=moment(md,vd,8);s8=moment(ms,vs,8)
    return ((np.sqrt(d2)+cfg.gamma/2*(d4*s4)**.25+np.abs(dc))**2,
            (d4**.25+cfg.gamma/2*(d8*s8)**.125+np.abs(dc))**4)


def verify_seed(directory,allow_incomplete=False):
    directory=Path(directory);cfg=Config.read(directory/'config_frozen.json')
    status=json.loads((directory/'status.json').read_text());seed=status['seed']
    stable_arithmetic=json.loads((directory/'protocol.json').read_text()).get('paired_arithmetic')=='difference-first'
    if not status['complete'] and not allow_incomplete:raise ValueError('Incomplete seed')
    market=Market(cfg,seed)
    for _ in range(cfg.block):market.step()
    previous_actual={n:np.zeros(100) for n in ('All Signals','Greedy','HAC','Catoni','Tail','Oracle')}
    equity={n:1. for n in previous_actual};absorbed={n:False for n in previous_actual}
    previous_candidates={};previous_references={};pair_references={};catoni={};tail={};score_history={}
    ghost_previous_candidates={};ghost_previous_references={}
    max_error={};checks=0
    def check(key,a,b,atol=1e-12,rtol=1e-9):
        nonlocal checks
        a,b=np.asarray(a),np.asarray(b)
        np.testing.assert_allclose(a,b,atol=atol,rtol=rtol,err_msg=key)
        max_error[key]=max(max_error.get(key,0.),float(np.max(np.abs(a-b),initial=0.)))
        checks+=a.size
    nu2=public_envelope(cfg)['nu2']
    ghost_means={}
    for block in sorted(directory.glob('block_*')):
        if int(block.name.split('_')[-1])>status['completed_blocks']:continue
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
                if absorbed[n]:cost=0.;gross=0.
                check('fund_gross',gross,row.gross);check('fund_net',gross-cost,row.net)
                check('fund_utility',utility(gross,cost,cfg.gamma),row.utility)
                if gross-cost<=-1:equity[n]=0.;absorbed[n]=True
                else:equity[n]*=1+gross-cost
                check('fund_equity',equity[n],row.equity)
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
                utility_difference=utility(wb@obs.returns,cc,cfg.gamma)-utility(rw@obs.returns,rc,cfg.gamma)
                y=((wb-rw)@obs.returns)*(1-cfg.gamma*((wb+rw)@obs.returns)/2)-dc if stable_arithmetic else utility_difference
                check('score_utility_identity',y,utility_difference)
                check('score',y,archive['y'][offset],atol=1e-300 if stable_arithmetic else 1e-12)
                check('cost_difference',dc,archive['cost_difference'][offset])
                mean=values(wb,cc,truth,cfg)-values(rw[None,:],np.array([rc]),truth,cfg)[0]
                check('conditional_score_mean',mean,archive['true_mean'][offset],atol=1e-13)
                if n=='Tail':
                    d=p@(wb-rw).T if stable_arithmetic else p@wb.T-p@rw[:,None]
                    s=p@(wb+rw).T if stable_arithmetic else p@wb.T+p@rw[:,None]
                    v2,v4=replay_caps(d,s,public_values,dc,cfg)
                    check('second_cap',v2,archive['second_cap'][offset],atol=1e-300 if stable_arithmetic else 1e-18)
                    check('fourth_cap',v4,archive['fourth_cap'][offset],atol=1e-300 if stable_arithmetic else 1e-24)
                    levels=np.array([s for s in (2.,4.,8.) for _ in range(3)])[:,None]*v4[None,:]**.25
                    levels=np.where(v4[None,:]>0,levels,1.)
                    bias=np.minimum(v2[None,:]/(4*levels),27*v4[None,:]/(256*levels**3))
                    fractions=np.tile([.25,.5,.75],3)[:,None]
                    lam=np.where(v4[None,:]>0,fractions/(levels+bias),0.)
                    increments=np.log1p(lam*(np.maximum(y[None,:],-levels)-bias))
                    components=np.column_stack([tail.get(item['comparison_id'],np.zeros(9)) for item in items])+increments
                    tail_logs=logsumexp(components,axis=0)-np.log(9)
                if n=='Catoni':
                    check('catoni_predictable_bet',[bets[item['comparison_id']] for item in items],archive['bet'][offset])
                logs=[]
                for j,item in enumerate(items):
                    cid=item['comparison_id'];score_history.setdefault(cid,[]).append(float(y[j]))
                    if n=='Catoni':
                        lam=bets[cid];x=lam*y[j]
                        inc=np.sign(x)*np.log1p(abs(x)+x*x/2)-lam*lam*nu2/2
                        catoni[cid]=catoni.get(cid,0.)+inc;logs.append(catoni[cid])
                    elif n=='Tail':
                        tail[cid]=components[:,j].copy();logs.append(tail_logs[j])
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
        annual=pd.read_parquet(block/'comparison_events.parquet')
        for n,items in order.items():
            eligible=[]
            for event in annual[annual.method.eq(n)].itertuples():
                scores=np.array(score_history[event.comparison_id]);average=float(scores.mean())
                check('annual_episode_mean',average,event.mean_y)
                check('annual_block_mean',scores[-cfg.block:].mean(),event.block_mean_y)
                gate=average>1e-8
                if n in ('Catoni','Tail'):gate=gate and event.log_e>=np.log(1/cfg.alpha)
                elif n=='HAC':
                    x=scores-average;length=len(scores);bandwidth=min(length-1,int(np.floor(4*(length/100)**(2/9))))
                    variance=np.sum(x*x)/length
                    for lag in range(1,bandwidth+1):variance+=2*(1-lag/(bandwidth+1))*np.sum(x[lag:]*x[:-lag])/length
                    variance=max(0.,variance)
                    pvalue=float(norm.sf(average*np.sqrt(length/variance))) if variance>1e-30 else (0. if average>0 else 1.)
                    check('hac_pvalue',pvalue,event.pvalue)
                    gate=gate and pvalue<=cfg.alpha
                if bool(event.eligible)!=gate:raise AssertionError('Annual eligibility mismatch')
                if gate:eligible.append((event,average))
            chosen=None
            if not absorbed[n]:
                for move in ('forward','backward','swap'):
                    candidates=[(e,v) for e,v in eligible if e.move==move]
                    if not candidates:continue
                    best=max(v for e,v in candidates)
                    tied=[e for e,v in candidates if best-v<=1e-9]
                    chosen=min(tied,key=lambda e:(market.ids[e.added] if e.added>=0 else '',market.ids[e.removed] if e.removed>=0 else '')).comparison_id
                    break
            selected=annual[annual.method.eq(n)&annual.selected].comparison_id.tolist()
            if selected!=([chosen] if chosen else []):raise AssertionError('Annual priority/ranking selection mismatch')
        for archive in arrays.values():archive.close()
        if ga is not None:ga.close()
        print(f'verified seed={seed} {block.name}',file=sys.stderr,flush=True)
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
