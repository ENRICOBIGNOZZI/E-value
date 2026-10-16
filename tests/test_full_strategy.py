from dataclasses import replace
import json
from math import comb,factorial
import numpy as np
import pandas as pd
import pytest
from park_revive.config import Config
from park_revive.dgp import Market,Truth
from park_revive.optimizer import Optimizer
from park_revive.oracle import score_moments
from park_revive_full.events import EventTracker
from park_revive_full.market import CausalMarket
from park_revive_full.moments import joint_moments,pair_moments
from park_revive_full.optimization import StudyOptimizer


def test_market_preparation_is_predictable_and_preserves_frozen_rng():
    cfg=replace(Config(),n_assets=8,block=3,years=3,transition_probability=.4)
    old=Market(cfg,51001);new=CausalMarket(cfg,51001)
    for _ in range(24):
        before=json.dumps(new.rng.bit_generator.state,sort_keys=True)
        design,prepared=new.prepare()
        assert new.prepare()[1] is prepared
        assert before==json.dumps(new.rng.bit_generator.state,sort_keys=True)
        a,ta=old.step();b,tb=new.step()
        assert tb is prepared
        np.testing.assert_array_equal(a.returns,b.returns)
        for field in ('mean','loadings','second','theta'):np.testing.assert_array_equal(getattr(ta,field),getattr(tb,field))
        assert (ta.regime,ta.deteriorated)==(tb.regime,tb.deteriorated)


def test_scalar_optimizer_matches_independent_qp_and_liquidation_cost():
    cfg=replace(Config(),solver_tolerance=1e-10)
    rng=np.random.default_rng(51001)
    for _ in range(15):
        h=rng.normal(size=(4,5))*.01;second=h@h.T;mu=rng.normal(size=4)*.001
        previous=rng.uniform(-.2,.2,4)
        exact=StudyOptimizer(cfg,mu,second);qp=Optimizer(replace(cfg,solver_tolerance=1e-8),mu,second)
        for support in ((),(0,),(2,)):
            a=exact.solve(support,previous);b=qp.solve(support,previous)
            np.testing.assert_allclose(a.weights,b.weights,atol=1e-6,rtol=0)
            assert a.value==pytest.approx(b.value,abs=1e-10)


def test_joint_moment_recurrence_independent_polynomial_convolution():
    # One common Laplace shock: expand (md+hd*z)^a(ms+hs*z)^b directly.
    md,ms,hd,hs=.03,-.02,.1,-.07
    moments=joint_moments(md,ms,np.array([[hd]]),np.array([[hs]]))
    for a in range(5):
        for b in range(5):
            exact=0.
            for i in range(a+1):
                for j in range(b+1):
                    k=i+j
                    if k%2==0:exact+=comb(a,i)*comb(b,j)*md**(a-i)*ms**(b-j)*hd**i*hs**j*factorial(k)/2**(k/2)
            assert moments[a,b][0]==pytest.approx(exact,rel=1e-12,abs=1e-20)


def test_general_pair_fourth_moment_against_mc_and_old_second():
    rng=np.random.default_rng(51002)
    mu=np.array([.02,-.01]);h=np.array([[.07,.02],[-.03,.06]])
    truth=Truth(0,mu,h,np.outer(mu,mu)+h@h.T,np.zeros(2),0,False)
    wb=np.array([.6,-.2]);ws=np.array([-.1,.4]);bb=np.array([.1,.2]);bs=np.array([-.2,.3])
    cfg=replace(Config(),gamma=3.,proportional=.001,impact=.002)
    from park_revive.costs import cost_components
    dc=sum(cost_components(wb,bb,cfg))-sum(cost_components(ws,bs,cfg))
    first,second,fourth=pair_moments(wb,ws,dc,truth,cfg.gamma)
    old_first,old_second=score_moments(wb,ws,bb,bs,truth,cfg)
    assert first[0]==pytest.approx(old_first,abs=1e-16)
    assert second[0]==pytest.approx(old_second,rel=1e-12)
    z=rng.laplace(0,1/np.sqrt(2),(600000,2));a=mu+z@h.T
    rb=a@wb;rs=a@ws;y=rb-rs-cfg.gamma*(rb*rb-rs*rs)/2-dc
    for order,expected in ((1,first[0]),(2,second[0]),(4,fourth[0])):
        sample=y**order
        assert abs(sample.mean()-expected)<6*sample.std()/np.sqrt(len(sample))
    _,second,fourth=pair_moments(wb,wb,.003,truth,cfg.gamma)
    assert second[0]==pytest.approx(.003**2)
    assert fourth[0]==pytest.approx(.003**4)


def test_fast_and_slow_responses_both_enter_stable_event_risk_set():
    fast=EventTracker({'method':'fast'},1e-8);slow=EventTracker({'method':'slow'},1e-8)
    fast.observe(10,.01,True,True)
    assert fast.close(10,'selected')
    fast.adjudicate(20,.01)
    slow.observe(10,.01)
    slow.observe(20,.01,True,True)
    assert not slow.close(20,'selected')
    assert len(fast.rows)==len(slow.rows)==1
    assert fast.rows[0]['selection_delay_days']==0
    assert slow.rows[0]['selection_delay_days']==10
    assert fast.rows[0]['confirmation_day']==slow.rows[0]['confirmation_day']==20


def test_ranking_loss_and_sign_reversal_are_distinct_competing_events():
    tracker=EventTracker({},0.)
    tracker.observe(10,-.1);tracker.observe(20,.1,True)
    tracker.observe(30,.1,True);tracker.observe(40,-.1)
    event=tracker.rows[0]
    assert event['event_kind']=='sign_change_positive'
    assert event['criterion_detected'] and not event['selected']
    assert event['termination_reason']=='sign_reversal'
    tracker.observe(50,.1,True,True);assert tracker.close(50,'selected')
    tracker.adjudicate(60,-.1)
    assert tracker.unstable_runs==1 and len(tracker.rows)==1


def test_shortlists_and_near_tied_choices_preserve_signal_ids_after_permutation():
    from park_revive_full.selection import Selector
    cfg=replace(Config(),solver_tolerance=1e-10)
    rng=np.random.default_rng(51001);ids=tuple(f's{j:03d}' for j in range(100))
    mu=rng.normal(size=100)*.0005;h=rng.normal(size=(100,8))*.003
    second=h@h.T+np.eye(100)*.00001;previous=np.zeros(100);previous[[3,7]]=[.2,-.3]
    permutation=rng.permutation(100)
    original=Selector('Greedy',cfg,ids);original.actual.support=(3,7);original.actual.previous=previous.copy()
    other=Selector('Greedy',cfg,tuple(ids[j] for j in permutation))
    other.actual.support=tuple(np.flatnonzero(np.isin(permutation,[3,7])))
    other.actual.previous=previous[permutation]
    a=original.refresh(0,StudyOptimizer(cfg,mu,second))[0]
    b=other.refresh(0,StudyOptimizer(cfg,mu[permutation],second[np.ix_(permutation,permutation)]))[0]
    assert [ids[j] for j in a]==[other.ids[j] for j in b]
    for selector in (original,other):
        for c in selector.comparisons.values():
            index=int(selector.ids[c.added][1:]) if c.added>=0 else 0
            value=1e-6+index*1e-12
            c.scores=[value,value];c.total=2*value
    ac=original.choose();bc=other.choose()
    assert ids[ac.added]==other.ids[bc.added]=='s000'


def test_general_pair_public_certificates_cover_true_laplace_moments():
    from park_revive_extensions.certificates import PublicRisk,paired_score_caps
    from park_revive.costs import cost_components
    cfg=replace(Config(),n_assets=12,block=3,years=3)
    rng=np.random.default_rng(51002);market=CausalMarket(cfg,51002);risk=PublicRisk.from_market_contract(cfg)
    for _ in range(3):
        design,truth=market.prepare()
        portfolios=rng.normal(size=(4,4,100));portfolios/=np.sum(np.abs(portfolios),axis=2,keepdims=True)
        wb,ws,bb,bs=portfolios
        dc=np.array([sum(cost_components(w,b,cfg))-sum(cost_components(v,c,cfg)) for w,b,v,c in zip(wb,bb,ws,bs)])
        _,second,fourth=pair_moments(wb,ws,dc,truth,cfg.gamma)
        bound2,bound4=paired_score_caps(design.sleeves@wb.T,design.sleeves@ws.T,design.values,dc,cfg.gamma,risk)
        assert np.all(second<=bound2*(1+1e-12))
        assert np.all(fourth<=bound4*(1+1e-12))
        market.step()


def test_tiny_contrast_survives_common_exposure_and_utility_cancellation():
    from types import SimpleNamespace
    from park_revive_extensions.certificates import PublicRisk,paired_score_caps
    from park_revive_full.paired import paired_caps,paired_scores
    cfg=Config();risk=PublicRisk.from_market_contract(cfg)
    tiny=1.6444509700466818e-18
    p=np.array([[.5,.5],[-.5,-.5],[0.,0.],[0.,0.]])
    design=SimpleNamespace(sleeves=p,values=np.array([[.3,.2],[-.3,-.2],[0.,0.],[0.,0.]]))
    wb=np.array([[1.,tiny]]);ws=np.array([1.,0.])
    old2,old4=paired_score_caps(p@wb.T,p@ws[:,None],design.values,0.,cfg.gamma,risk)
    new2,new4=paired_caps(wb,ws,design,0.,cfg.gamma,risk)
    assert old2[0]==old4[0]==0.  # The actual failure mechanism, not an exact-zero policy.
    assert new2[0]>0 and new4[0]>0
    a=np.array([.001,.001])
    expected=tiny*.001*(1-cfg.gamma*.001)
    assert paired_scores(wb,ws,0.,a,cfg.gamma)[0]==pytest.approx(expected,rel=1e-15,abs=0.)
    assert paired_scores(ws,ws,0.,a,cfg.gamma)[0]==0.
    mu=np.array([.0002,.0002]);h=np.array([[.002],[.002]])
    truth=Truth(0,mu,h,np.outer(mu,mu)+h@h.T,np.zeros(2),0,False)
    _,second,fourth=pair_moments(wb,ws,0.,truth,cfg.gamma)
    assert 0<second[0]<=new2[0] and 0<fourth[0]<=new4[0]


def test_full_engine_resume_and_evaluator_isolation(tmp_path,monkeypatch):
    from park_revive_full.engine import run_seed
    cfg=replace(Config(),n_assets=8,block=3,years=3,solver_tolerance=1e-10)
    run_seed(cfg,51003,tmp_path/'direct')
    run_seed(cfg,51003,tmp_path/'resumed',stop_after_blocks=1)
    run_seed(cfg,51003,tmp_path/'resumed',resume=True)
    for filename in ('daily_ledger.parquet','comparison_events.parquet'):
        pd.testing.assert_frame_equal(pd.read_parquet(tmp_path/'direct'/filename),pd.read_parquet(tmp_path/'resumed'/filename))
    for filename in ('economic_opportunities.json','decisions.json','deployments.json'):
        assert json.loads((tmp_path/'direct'/filename).read_text())==json.loads((tmp_path/'resumed'/filename).read_text())
    for year in (1,2):
        for name in ('Greedy','HAC','Catoni','Tail'):
            a=np.load(tmp_path/'direct'/f'block_{year:02d}'/f'scores_{name}.npz')
            b=np.load(tmp_path/'resumed'/f'block_{year:02d}'/f'scores_{name}.npz')
            for key in a.files:np.testing.assert_array_equal(a[key],b[key])
    # Disabling ghost adjudication can change only evaluator labels, never fund/evidence.
    monkeypatch.setattr(EventTracker,'close',lambda *args,**kwargs:False)
    run_seed(cfg,51003,tmp_path/'no_ghosts')
    pd.testing.assert_frame_equal(pd.read_parquet(tmp_path/'direct/daily_ledger.parquet'),pd.read_parquet(tmp_path/'no_ghosts/daily_ledger.parquet'))
    for year in (1,2):
        for name in ('Greedy','HAC','Catoni','Tail'):
            a=np.load(tmp_path/'direct'/f'block_{year:02d}'/f'scores_{name}.npz')
            b=np.load(tmp_path/'no_ghosts'/f'block_{year:02d}'/f'scores_{name}.npz')
            for key in a.files:np.testing.assert_array_equal(a[key],b[key])
