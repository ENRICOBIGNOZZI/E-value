"""Full fund study with pre-shock choices and evaluator-only continuations."""
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import pickle
import time
import numpy as np
import pandas as pd
from park_revive.backtest import atomic_json,checkpoint
from park_revive.costs import cost_components,expected_utility,utility
from park_revive.eprocess import phi,public_envelope
from park_revive.features import serialize_library
from park_revive.metrics import path_metrics
from park_revive.optimizer import fit_moments
from park_revive.policies import Policy
from park_revive.pvalues import hac_pvalue
from park_revive_extensions.certificates import PublicRisk,paired_score_caps
from park_revive_extensions.tail_betting import TailMixture
from .events import EventTracker
from .market import CausalMarket
from .moments import pair_moments
from .optimization import StudyOptimizer
from .selection import Selector

METHODS=('All Signals','Greedy','HAC','Catoni','Tail','Oracle')


def source_fingerprint():
    root=Path(__file__).resolve().parents[2]
    paths=sorted([*root.joinpath('src').rglob('*.py'),*root.joinpath('research').rglob('*.py')])
    files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    digest=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()
    return digest,files


@dataclass
class Ghost:
    tracker: EventTracker
    reference: Policy
    candidate: Policy
    means: list


def close_comparison(state,c,reference,day,reason):
    tracker=state['trackers'][c.comparison_id]
    if tracker.close(day,reason):
        state['ghosts'].append(Ghost(tracker,deepcopy(reference),deepcopy(c.shadow),[]))
    state['closures'].append(dict(comparison_id=c.comparison_id,day=day,reason=reason))


def batch_cost(weights,previous,cfg):
    change=weights-previous
    return cfg.proportional*np.abs(change).sum(axis=1)+cfg.impact*np.sum(change*change,axis=1)/2


def conditional_values(weights,costs,truth,cfg):
    means=weights@truth.mean
    seconds=np.sum((weights@truth.second)*weights,axis=1)
    return means-cfg.gamma*seconds/2-costs


def prepare_shadows(selector,estimated,cfg):
    selector.reference.prepare(estimated)
    comps=list(selector.comparisons.values())
    for c in comps:c.shadow.prepare(estimated)
    wb=np.array([c.shadow.weights for c in comps])
    previous=np.array([c.shadow.previous for c in comps])
    return comps,wb,batch_cost(wb,previous,cfg)


def ghost_order(ghosts):
    return [dict(comparison_id=g.tracker.metadata['comparison_id'],candidate=list(g.candidate.support),
                 reference=list(g.reference.support)) for g in ghosts]


def record_ghosts(archive,ghosts,means,cfg):
    if not ghosts:return
    maxb=max(len(g.candidate.support) for g in ghosts)
    maxs=max(len(g.reference.support) for g in ghosts)
    wb=np.zeros((len(ghosts),maxb));ws=np.zeros((len(ghosts),maxs));dc=[]
    for j,g in enumerate(ghosts):
        wb[j,:len(g.candidate.support)]=g.candidate.weights[list(g.candidate.support)]
        ws[j,:len(g.reference.support)]=g.reference.weights[list(g.reference.support)]
        dc.append(sum(cost_components(g.candidate.weights,g.candidate.previous,cfg))
                  -sum(cost_components(g.reference.weights,g.reference.previous,cfg)))
    for key,value in [('weights',wb),('reference_weights',ws),('cost_difference',dc),('true_mean',means)]:
        archive.setdefault(key,[]).append(np.asarray(value))


def run_seed(cfg,seed,directory,resume=False,stop_after_blocks=None,market_factory=CausalMarket):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    ckpt=directory/'checkpoint.pkl';fingerprint,files=source_fingerprint()
    if resume and ckpt.exists():
        # Only locally generated checkpoints are accepted by this CLI.
        with ckpt.open('rb') as f:state=pickle.load(f)
        if (state['seed'],state['config_hash'],state['source_hash'])!=(seed,cfg.digest,fingerprint):
            raise ValueError('Checkpoint seed/configuration/source mismatch; use a new output version')
    elif ckpt.exists():raise FileExistsError('Checkpoint exists: resume or use a new output version')
    else:
        market=market_factory(cfg,seed);history=[]
        for _ in range(cfg.block):history.append(market.step()[0].returns.copy())
        state=dict(seed=seed,config_hash=cfg.digest,source_hash=fingerprint,market=market,history=history,
            selectors={n:Selector(n,cfg,market.ids) for n in METHODS[1:5]},
            policies={n:Policy(tuple(range(100)),np.zeros(100)) for n in ('All Signals','Oracle')},
            trackers={},ghosts=[],closures=[],pending_deployments={},next_year=1,
            equity={n:1. for n in METHODS},insolvent={n:False for n in METHODS},runtimes=[],elapsed=0.)
        atomic_json(directory/'source_manifest.json',files)
        atomic_json(directory/'config_frozen.json',cfg.to_dict())
        atomic_json(directory/'feature_library.json',serialize_library(market.library))
        atomic_json(directory/'protocol.json',dict(methods=METHODS,numerical_margin=1e-8,
            rank_tolerance=1e-9,catoni=public_envelope(cfg),public_risk=PublicRisk.from_market_contract(cfg).__dict__,
            evaluator_extra_blocks=1,score_format='compressed per-block arrays; order in comparison_order.json'))
        checkpoint(ckpt,state)
    completed=0
    while state['next_year']<cfg.years:
        started=time.perf_counter();year=state['next_year'];day0=year*cfg.block
        market=state['market'];selectors=state['selectors'];policies=state['policies']
        mu,second=fit_moments(state['history'],cfg)
        estimated=StudyOptimizer(cfg,mu,second)
        ghost_optimizer=StudyOptimizer(cfg,mu,second)
        deployment_optimizer=StudyOptimizer(cfg,mu,second)
        shortlists=[];state['closures']=[]
        for name,selector in selectors.items():
            old_reference=selector.reference
            shortlist,opened,withdrawn=selector.refresh(day0,estimated)
            for c in withdrawn:close_comparison(state,c,old_reference,day0,'shortlist_withdrawal')
            for c in opened:
                state['trackers'][c.comparison_id]=EventTracker(dict(seed=seed,method=name,
                    comparison_id=c.comparison_id,start=c.start,move=c.move,lifecycle=c.lifecycle,
                    added=c.added,removed=c.removed,reference_support=list(c.reference_support),
                    candidate_support=list(c.candidate)),cfg.economic_tolerance)
            shortlists.append(dict(method=name,day=day0,signals=[market.ids[j] for j in shortlist]))
        # All ghosts here have precisely one future annual block to complete.
        ghosts=list(state['ghosts']);state['ghosts']=[]
        archives={n:dict(y=[],cost_difference=[],true_mean=[],log_e=[],weights=[],reference_weights=[],
                          second_cap=[],fourth_cap=[],true_second=[],true_fourth=[],bet=[]) for n in selectors}
        orders={n:[dict(comparison_id=c.comparison_id,candidate=list(c.candidate),
                        reference=list(c.reference_support)) for c in s.comparisons.values()]
                for n,s in selectors.items()}
        ledger=[];deployments=[];events=[];decisions=[];ghost_archive={}
        block_means={c.comparison_id:[] for s in selectors.values() for c in s.comparisons.values()}
        bets={c.comparison_id:min((cfg.delta0 if not c.scores else max(0.,c.mean))/(2*public_envelope(cfg)['nu2']),
                                 1/(2*np.sqrt(public_envelope(cfg)['nu2'])))
              for c in selectors['Catoni'].comparisons.values()}
        risk=PublicRisk.from_market_contract(cfg);nu2=public_envelope(cfg)['nu2']
        for offset in range(cfg.block):
            estimated.new_day();ghost_optimizer.new_day();deployment_optimizer.new_day()
            design,truth=market.prepare()
            for n,p in policies.items():
                if n!='Oracle':p.prepare(estimated)
            for s in selectors.values():s.actual.prepare(estimated)
            prepared={n:prepare_shadows(s,estimated,cfg) for n,s in selectors.items()}
            exact=StudyOptimizer(cfg,truth.mean,truth.second)
            policies['Oracle'].prepare(exact)  # strictly before market.step/shock draw
            all_actual={**policies,**{n:s.actual for n,s in selectors.items()}}
            # Evaluator calls use their own estimated optimizer, never learner warm starts.
            if offset==0:
                for n,decision in state['pending_deployments'].items():
                    p=all_actual[n];old=deployment_optimizer.solve(tuple(decision['support_before']),p.previous)
                    old_value=expected_utility(old.weights,p.previous,truth.mean,truth.second,cfg)
                    new_value=expected_utility(p.weights,p.previous,truth.mean,truth.second,cfg)
                    deployments.append(dict(**decision,deployment_day=design.day,
                        conditional_gain=new_value-old_value,new_conditional_utility=new_value,
                        old_conditional_utility=old_value,actual_entry_cost=sum(cost_components(p.weights,p.previous,cfg))))
                state['pending_deployments']={}
            # Tail choices depend only on public geometry, weights and known turnover costs.
            comps,wb,costs=prepared['Tail'];ref=selectors['Tail'].reference
            reference_cost=sum(cost_components(ref.weights,ref.previous,cfg));dc=costs-reference_cost
            v2,v4=paired_score_caps(design.sleeves@wb.T,design.sleeves@ref.weights[:,None],
                                   design.values,dc,cfg.gamma,risk)
            tail=TailMixture(len(comps));tail.log_capitals=np.column_stack([c.components for c in comps])
            tail_prepared=tail.prepare(v2,v4)
            # Exact moments below are audit outputs only; no evidence preparation reads them.
            true_mean,true_second,true_fourth=pair_moments(wb,ref.weights,dc,truth,cfg.gamma)
            if np.any(true_second>v2*(1+1e-8)+1e-24) or np.any(true_fourth>v4*(1+1e-8)+1e-32):
                raise AssertionError('Predictable public geometry certificate violated')
            ghost_values=[]
            for ghost in ghosts:
                ghost.reference.prepare(ghost_optimizer);ghost.candidate.prepare(ghost_optimizer)
                cv=expected_utility(ghost.candidate.weights,ghost.candidate.previous,truth.mean,truth.second,cfg)
                rv=expected_utility(ghost.reference.weights,ghost.reference.previous,truth.mean,truth.second,cfg)
                ghost_values.append(cv-rv)
            record_ghosts(ghost_archive,ghosts,ghost_values,cfg)
            actual_audits={}
            for n,p in all_actual.items():
                if state['insolvent'][n]:actual_audits[n]=(0.,np.nan);continue
                value=expected_utility(p.weights,p.previous,truth.mean,truth.second,cfg)
                matched=exact.solve(tuple(range(100)),p.previous)
                gap=matched.value-value
                if gap < -1e-7:raise ArithmeticError('State-matched regret is negative beyond QP tolerance')
                actual_audits[n]=(value,max(0.,gap))
            obs,realized_truth=market.step()
            if realized_truth is not truth:raise AssertionError('Prepared truth boundary changed')
            for n,p in all_actual.items():
                if state['insolvent'][n]:
                    p.weights=np.zeros(100);p.previous=np.zeros(100)
                w=p.weights.copy();result=p.realize(obs.returns,cfg)
                if state['insolvent'][n]:result={k:0. for k in result}
                elif result['net']<=-1:state['equity'][n]=0.;state['insolvent'][n]=True
                else:state['equity'][n]*=1+result['net']
                support=p.support;denom=len(support);nonzero=truth.theta>0
                active=sum(nonzero[j] for j in support)
                ledger.append(dict(seed=seed,method=n,day=obs.day,**result,equity=state['equity'][n],
                    insolvent=state['insolvent'][n],weights=w.tolist(),support=list(support),
                    n_active=denom,leverage=float(np.abs(w).sum()),conditional_utility=actual_audits[n][0],
                    state_matched_regret=actual_audits[n][1],regime=truth.regime,
                    structural_precision=active/denom if denom else np.nan,
                    structural_recall=active/max(1,int(nonzero.sum())),
                    noise_fraction=sum(45<=j<85 for j in support)/denom if denom else np.nan,
                    proxy_fraction=sum(j>=85 for j in support)/denom if denom else np.nan,
                    primal_residual=p.certificate[0],dual_residual=p.certificate[1],solver_gap=p.certificate[2]))
            for n,s in selectors.items():
                comps,wb,costs=prepared[n];ref=s.reference
                rc=sum(cost_components(ref.weights,ref.previous,cfg))
                rw=ref.weights.copy();rr=ref.realize(obs.returns,cfg)
                returns=wb@obs.returns;y=utility(returns,costs,cfg.gamma)-rr['utility']
                means=conditional_values(wb,costs,truth,cfg)-(rw@truth.mean-cfg.gamma*(rw@truth.second@rw)/2-rc)
                if n=='Tail':
                    np.testing.assert_allclose(means,true_mean,rtol=1e-7,atol=1e-14)
                    tail.update(y,tail_prepared)
                    tail_log_e=tail.log_e
                for j,c in enumerate(comps):
                    c.scores.append(float(y[j]));c.total+=float(y[j]);block_means[c.comparison_id].append(float(means[j]))
                    if n=='Catoni':c.log_e+=phi(bets[c.comparison_id]*y[j])-bets[c.comparison_id]**2*nu2/2
                    if n=='Tail':c.components=tail.log_capitals[:,j].copy();c.log_e=float(tail_log_e[j])
                    c.shadow.previous=c.shadow.weights.copy()
                arc=archives[n];arc['y'].append(y);arc['cost_difference'].append(costs-rc)
                arc['true_mean'].append(means);arc['log_e'].append(np.array([c.log_e for c in comps]))
                maxsize=max(map(lambda c:len(c.candidate),comps),default=0)
                compact=np.zeros((len(comps),maxsize))
                for j,c in enumerate(comps):compact[j,:len(c.candidate)]=wb[j,list(c.candidate)]
                arc['weights'].append(compact);arc['reference_weights'].append(rw[list(s.actual.support)])
                if n=='Tail':
                    for key,value in [('second_cap',v2),('fourth_cap',v4),('true_second',true_second),('true_fourth',true_fourth)]:arc[key].append(value)
                if n=='Catoni':arc['bet'].append(np.array([bets[c.comparison_id] for c in comps]))
            for ghost,value in zip(ghosts,ghost_values):
                ghost.means.append(value);ghost.reference.realize(obs.returns,cfg);ghost.candidate.realize(obs.returns,cfg)
            state['history'].append(obs.returns.copy())
        end=(year+1)*cfg.block;terminal=year+1==cfg.years
        for ghost in ghosts:ghost.tracker.adjudicate(end,float(np.mean(ghost.means)))
        ghost_optimizer=None
        for n,s in selectors.items():
            chosen=None if state['insolvent'][n] else s.choose()
            for c in list(s.comparisons.values()):
                means=np.asarray(block_means[c.comparison_id]);eligible=s.eligible(c)
                state['trackers'][c.comparison_id].observe(end,float(means.mean()),eligible,c is chosen)
                events.append(dict(seed=seed,method=n,day=end,comparison_id=c.comparison_id,start=c.start,
                    reference_support=list(c.reference_support),candidate_support=list(c.candidate),
                    move=c.move,lifecycle=c.lifecycle,added=c.added,removed=c.removed,n=len(c.scores),
                    mean_y=c.mean,block_mean_y=float(np.mean(c.scores[-cfg.block:])),
                    log_e=c.log_e,pvalue=hac_pvalue(c.scores),true_block_mean=float(means.mean()),
                    last_pre_return_mean=float(means[-1]),eligible=eligible,selected=c is chosen,terminal=terminal))
            if chosen is not None:
                decision=dict(seed=seed,method=n,day=end,comparison_id=chosen.comparison_id,
                    support_before=list(s.actual.support),support_after=list(chosen.candidate),move=chosen.move,
                    lifecycle=chosen.lifecycle,added=chosen.added,removed=chosen.removed,mean_y=chosen.mean,
                    log_e=chosen.log_e,true_block_mean=float(np.mean(block_means[chosen.comparison_id])),
                    last_pre_return_mean=block_means[chosen.comparison_id][-1],executed=not terminal)
                decisions.append(decision)
                if not terminal:state['pending_deployments'][n]=decision.copy()
                for c in list(s.comparisons.values()):
                    close_comparison(state,c,s.reference,end,'selected' if c is chosen else 'competing_move')
                s.apply(chosen)
            elif terminal:
                for c in s.comparisons.values():close_comparison(state,c,s.reference,end,'administrative_end')
        blockdir=directory/f'block_{year:02d}';blockdir.mkdir(exist_ok=True)
        pd.DataFrame(ledger).to_parquet(blockdir/'daily_ledger.parquet',index=False)
        pd.DataFrame(events).to_parquet(blockdir/'comparison_events.parquet',index=False)
        pd.DataFrame(decisions).to_json(blockdir/'decisions.json',orient='records',indent=2)
        pd.DataFrame(deployments).to_json(blockdir/'deployments.json',orient='records',indent=2)
        atomic_json(blockdir/'comparison_order.json',orders)
        atomic_json(blockdir/'shortlists.json',shortlists)
        atomic_json(blockdir/'closed_episodes.json',state['closures'])
        atomic_json(blockdir/'ghost_order.json',ghost_order(ghosts))
        if ghost_archive:np.savez_compressed(blockdir/'ghosts.npz',**{k:np.asarray(v) for k,v in ghost_archive.items()})
        for n,archive in archives.items():
            np.savez_compressed(blockdir/f'scores_{n}.npz',**{k:np.asarray(v) for k,v in archive.items() if len(v)})
        seconds=time.perf_counter()-started
        state['runtimes'].append(dict(seed=seed,year=year,seconds=seconds));state['elapsed']+=seconds;state['next_year']+=1
        checkpoint(ckpt,state)
        atomic_json(directory/'status.json',dict(seed=seed,completed_blocks=year,total_blocks=cfg.years-1,
            complete=False,source_hash=fingerprint,elapsed_seconds=state['elapsed']))
        print(f'seed={seed} block={year}/{cfg.years-1} seconds={seconds:.2f}',flush=True)
        completed+=1
        if stop_after_blocks is not None and completed>=stop_after_blocks:break
    complete=state['next_year']==cfg.years
    if complete:
        if state['ghosts']:adjudicate_terminal(cfg,state,directory)
        finalize(cfg,state,directory)
    return dict(seed=seed,complete=complete,elapsed_seconds=state['elapsed'])


def adjudicate_terminal(cfg,state,directory):
    """One extra outcome year for pending event labels; the main checkpoint is unchanged."""
    ghosts=deepcopy(state['ghosts']);market=deepcopy(state['market']);archive={}
    mu,second=fit_moments(state['history'],cfg);estimated=StudyOptimizer(cfg,mu,second)
    for _ in range(cfg.block):
        estimated.new_day();_,truth=market.prepare()
        for ghost in ghosts:
            ghost.reference.prepare(estimated);ghost.candidate.prepare(estimated)
            ghost.means.append(expected_utility(ghost.candidate.weights,ghost.candidate.previous,truth.mean,truth.second,cfg)
                -expected_utility(ghost.reference.weights,ghost.reference.previous,truth.mean,truth.second,cfg))
        record_ghosts(archive,ghosts,[g.means[-1] for g in ghosts],cfg)
        obs,_=market.step()
        for ghost in ghosts:ghost.reference.realize(obs.returns,cfg);ghost.candidate.realize(obs.returns,cfg)
    rows=[]
    for ghost in ghosts:
        mean=float(np.mean(ghost.means));ghost.tracker.adjudicate((cfg.years+1)*cfg.block,mean)
        tracker=state['trackers'][ghost.tracker.metadata['comparison_id']]
        tracker.rows=ghost.tracker.rows;tracker.unstable_runs=ghost.tracker.unstable_runs;tracker.run=None
        rows.append(dict(comparison_id=tracker.metadata['comparison_id'],future_block_mean=mean,
                         adjudication_day=(cfg.years+1)*cfg.block))
    atomic_json(directory/'terminal_adjudication.json',rows)
    atomic_json(directory/'terminal_ghost_order.json',ghost_order(ghosts))
    np.savez_compressed(directory/'terminal_ghosts.npz',**{k:np.asarray(v) for k,v in archive.items()})


def finalize(cfg,state,directory):
    blocks=sorted(directory.glob('block_*'))
    daily=pd.concat([pd.read_parquet(b/'daily_ledger.parquet') for b in blocks],ignore_index=True)
    events=pd.concat([pd.read_parquet(b/'comparison_events.parquet') for b in blocks],ignore_index=True)
    decisions=[x for b in blocks for x in json.loads((b/'decisions.json').read_text())]
    deployments=[x for b in blocks for x in json.loads((b/'deployments.json').read_text())]
    daily.to_parquet(directory/'daily_ledger.parquet',index=False)
    events.to_parquet(directory/'comparison_events.parquet',index=False)
    atomic_json(directory/'decisions.json',decisions);atomic_json(directory/'deployments.json',deployments)
    opportunities=[x for tracker in state['trackers'].values() for x in tracker.rows]
    atomic_json(directory/'economic_opportunities.json',opportunities)
    atomic_json(directory/'opportunity_registry.json',[dict(**t.metadata,
        stable_events=len(t.rows),unstable_runs=t.unstable_runs) for t in state['trackers'].values()])
    metrics=[]
    for n,g in daily.groupby('method',sort=False):
        selected=[d for d in decisions if d['method']==n]
        deployed=[d for d in deployments if d['method']==n]
        metrics.append(dict(seed=state['seed'],method=n,**path_metrics(g,cfg.block),
            moves=len(selected),executed_moves=len(deployed),
            economic_precision=np.mean([d['true_block_mean']>cfg.economic_tolerance for d in selected]) if selected else np.nan,
            deployment_positive_fraction=np.mean([d['conditional_gain']>cfg.economic_tolerance for d in deployed]) if deployed else np.nan))
    pd.DataFrame(metrics).to_csv(directory/'metrics_by_seed.csv',index=False)
    pd.DataFrame(state['runtimes']).to_csv(directory/'runtime.csv',index=False)
    atomic_json(directory/'status.json',dict(seed=state['seed'],completed_blocks=cfg.years-1,
        total_blocks=cfg.years-1,complete=True,source_hash=state['source_hash'],elapsed_seconds=state['elapsed'],
        stable_opportunities=len(opportunities),unstable_runs=sum(t.unstable_runs for t in state['trackers'].values())))
