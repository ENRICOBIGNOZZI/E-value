from dataclasses import replace,fields
import json
import pickle
import numpy as np
import pandas as pd
import pytest
from park_revive.config import Config
from park_revive.dgp import Market,Observed
from park_revive.features import evaluate
from park_revive.eprocess import public_envelope,Evidence
from park_revive.optimizer import Optimizer,fit_moments
from park_revive.policies import Policy
from park_revive.selection import Selector
from park_revive.comparisons import Comparison
from park_revive.backtest import simulate_seed
from park_revive.metrics import path_metrics


def small():return replace(Config(),n_assets=20,block=4,years=4,swap_top=2)


class ChangedMarket(Market):
    def step(self):
        obs,truth=super().step()
        if obs.day>=2*self.cfg.block:
            obs=Observed(obs.day,obs.returns+np.linspace(-.1,.1,100),obs.signal_ids)
        return obs,truth


class DisasterMarket(Market):
    def step(self):
        obs,truth=super().step()
        if obs.day>=self.cfg.block:
            obs=Observed(obs.day,np.full(100,-1e5),obs.signal_ids)
        return obs,truth


def test_exact_structural_nulls_and_public_view():
    cfg=small();market=Market(cfg,31)
    values=evaluate(np.tanh(market.latent),market.library)
    assert values.shape==(20,100)
    assert np.std(values[:,45:85],axis=0).min()>1e-8
    for _ in range(10):
        obs,truth=market.step()
        assert np.count_nonzero(truth.theta[45:])==0
        assert np.max(np.abs(values))<=1+1e-12
    assert {f.name for f in fields(Observed)}=={'day','returns','signal_ids'}
    assert not hasattr(obs,'theta') and not hasattr(obs,'regime')
    # Structural noise is unaffected by signal-block characteristics.
    z=np.tanh(market.latent);changed=z.copy();changed[:,:20]*=-1
    np.testing.assert_array_equal(evaluate(z,market.library)[:,45:85],evaluate(changed,market.library)[:,45:85])


def test_sleeves_and_envelope_cover_truth():
    from park_revive.sleeves import sleeve_weights
    cfg=small();market=Market(cfg,32);bound=public_envelope(cfg)
    for _ in range(10):
        p=sleeve_weights(evaluate(np.tanh(market.latent),market.library))
        assert np.max(np.abs(p.sum(axis=0)))<1e-12
        assert np.max(np.abs(p).sum(axis=0))<=1+1e-12
        obs,truth=market.step()
        assert np.max(np.diag(truth.second))<=bound['m2']


def test_selection_permutation_and_predictable_shortlist():
    cfg=replace(small(),proportional=0.);rng=np.random.default_rng(3)
    a=rng.normal(size=(100,100));m=a.T@a/100+np.eye(100)
    mu=rng.normal(size=100)*.1;ids=tuple(f's{i:03}' for i in range(100));b=np.zeros(100)
    selector=Selector('Greedy',cfg,ids,1.,Policy((0,1),b.copy()))
    shortlist,_=selector.refresh(4,Optimizer(cfg,mu,m),True)
    assert len(selector.comparisons)==100+2*cfg.swap_top
    assert len(shortlist)==cfg.swap_top
    perm=rng.permutation(100);inverse=np.argsort(perm)
    other=Selector('Greedy',cfg,tuple(ids[j] for j in perm),1.,Policy(tuple(sorted(inverse[[0,1]])),b.copy()))
    shortlist2,_=other.refresh(4,Optimizer(cfg,mu[perm],m[np.ix_(perm,perm)]),True)
    assert [ids[j] for j in shortlist]==[other.ids[j] for j in shortlist2]


def test_score_immutability_no_double_count_and_episode_reset():
    cfg=small();m=np.eye(100);mu=np.zeros(100)
    selector=Selector('E-process',cfg,tuple(f's{j}' for j in range(100)),1.,Policy((),np.zeros(100)))
    opt=Optimizer(cfg,mu,m);selector.refresh(4,opt,True)
    comp=next(iter(selector.comparisons.values()));comp.append(4,.1)
    with pytest.raises(ValueError):comp.append(4,.1)
    with pytest.raises(ValueError):comp.append(6,.1)
    oldid=comp.comparison_id;old_scores=tuple(comp.scores)
    selector.refresh(5,opt,False)
    assert selector.comparisons[('forward',comp.added,-1)].comparison_id==oldid
    assert tuple(comp.scores)==old_scores
    selector.actual.support=(0,)
    selector.refresh(5,opt,True)
    assert all(c.comparison_id!=oldid and not c.scores for c in selector.comparisons.values())


def test_shadow_states_and_actual_transition_cost():
    cfg=replace(small(),gamma=1.,proportional=.01,impact=.01)
    opt=Optimizer(cfg,np.array([.2,.1]),np.eye(2))
    real=Policy((),np.zeros(2));shadow=Policy((0,),np.zeros(2))
    real.prepare(opt);shadow.prepare(opt)
    shadow.realize(np.array([.2,.1]),cfg)
    np.testing.assert_array_equal(real.previous,np.zeros(2))
    real.support=(0,);real.prepare(opt)
    result=real.realize(np.array([.2,.1]),cfg)
    assert result['linear_cost']>0
    assert not np.shares_memory(real.previous,shadow.previous)


def test_checkpoint_resume_and_future_perturbation(tmp_path):
    cfg=small();seed=777
    full=tmp_path/'full';resumed=tmp_path/'resumed'
    simulate_seed(cfg,seed,full)
    result=simulate_seed(cfg,seed,resumed,stop_after_blocks=1)
    assert not result['complete']
    simulate_seed(cfg,seed,resumed,resume=True)
    a=pd.read_parquet(full/'daily_ledger.parquet');b=pd.read_parquet(resumed/'daily_ledger.parquet')
    pd.testing.assert_frame_equal(a,b)
    pd.testing.assert_frame_equal(pd.read_parquet(full/'comparison_events.parquet'),pd.read_parquet(resumed/'comparison_events.parquet'))
    # Directly mutate only future observable returns: all previous weights, evidence,
    # shortlists and decisions must remain identical. Same truth and RNG evolution.
    changed=tmp_path/'changed';simulate_seed(cfg,seed,changed,market_factory=ChangedMarket)
    c=pd.read_parquet(changed/'daily_ledger.parquet')
    pd.testing.assert_frame_equal(a[a.day<2*cfg.block].reset_index(drop=True),c[c.day<2*cfg.block].reset_index(drop=True))
    for filename in ('shortlists.csv','decisions.csv'):
        pd.testing.assert_frame_equal(pd.read_csv(full/'block_01'/filename),pd.read_csv(changed/'block_01'/filename))
    pd.testing.assert_frame_equal(pd.read_parquet(full/'block_01/score_ledger.parquet'),
                                 pd.read_parquet(changed/'block_01/score_ledger.parquet'))
    scores=pd.read_parquet(full/'block_01/score_ledger.parquet')
    for method in ('E-process','Repeated-HAC-p'):
        values=scores[scores.method.eq(method)].sort_values(['comparison_id','day']).y.to_numpy()
        if method=='E-process':baseline=values
        else:np.testing.assert_array_equal(values,baseline)


def test_degenerate_inactive_metrics():
    frame=pd.DataFrame(dict(net=[0.,0.],equity=[1.,1.],utility=[0.,0.],turnover=[0.,0.],
        linear_cost=[0.,0.],impact_cost=[0.,0.],leverage=[0.,0.],n_active=[0,0],
        structural_precision=[np.nan,np.nan],structural_recall=[0.,0.],noise_fraction=[np.nan,np.nan],
        proxy_fraction=[np.nan,np.nan],state_matched_regret=[.01,.01],insolvent=[False,False]))
    metrics=path_metrics(frame,252)
    assert np.isnan(metrics['sharpe']) and metrics['final_equity']==1 and metrics['inactive_fraction']==1


def test_insolvency_is_absorbing_and_not_dropped(tmp_path):
    cfg=replace(small(),years=2);simulate_seed(cfg,788,tmp_path/'disaster',market_factory=DisasterMarket)
    ledger=pd.read_parquet(tmp_path/'disaster/daily_ledger.parquet')
    oracle=ledger[ledger.method.eq('Oracle')]
    assert oracle.insolvent.any()
    assert (oracle.equity==0).all()
    assert (oracle.iloc[1:].net==0).all()
    assert len(oracle)==cfg.block*(cfg.years-1)
