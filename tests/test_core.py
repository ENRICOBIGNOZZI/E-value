import numpy as np
import pytest
from alpha_lifecycle.core import Settings,RestartMixture,Controller,paired_scores,utility
from alpha_lifecycle.dgp import simulate,conditional_value,marginal_mean

def test_initial_dormant_mass():
    c=Settings(stride=2,max_age=4)
    e=RestartMixture((1,1),c)
    assert e.update(np.zeros((1,1)))[0,0]==pytest.approx(1.)
    assert e.update(np.zeros((1,1)))[0,0]==pytest.approx(1.)
    assert e.update(np.zeros((1,1)))[0,0]==pytest.approx(1.)
    e.update(np.zeros((1,1)))
    assert e.update(np.zeros((1,1)))[0,0] <=1

def test_symmetry_null_one_step():
    cfg=Settings()
    a=RestartMixture((1,1),cfg); b=RestartMixture((1,1),cfg)
    assert ((a.update(np.ones((1,1)))+b.update(-np.ones((1,1))))/2)[0,0]==pytest.approx(1.)

def test_reset_spends_not_reuses_budget():
    e=RestartMixture((2,3),Settings())
    before=e.threshold().copy(); mask=np.zeros((2,3),bool);mask[0,1]=True
    e.reset(mask)
    assert e.threshold()[0,1]>before[0,1]
    assert e.threshold()[1,1]==before[1,1]

def test_lifetime_budget():
    cfg=Settings();k=np.arange(1,100001,dtype=float)
    assert np.sum(cfg.delta/(k*(k+1)))<=cfg.delta

def test_score_uses_current_book_and_costs():
    cfg=Settings();r=np.array([[.01,-.02,.03]])
    a=np.array([[True,False]]); s,raw,book=paired_scores(r,a,cfg,np.ones((1,2)))
    q=.1;b=.8*.01
    assert raw[0,0]==pytest.approx(utility(b+q*(-.02-cfg.fee),cfg.gamma)-utility(b,cfg.gamma))
    assert book[0]==pytest.approx(b+q*(-.02-cfg.fee))

def test_predictability_no_future_leakage():
    cfg=Settings(window=3)
    x=np.array([.1,-.9,-.8,.2,.4])
    def run(v):
        c=Controller((1,1),'rolling_portfolio',cfg);a=[]
        for t in v:
            a.append(c.active.copy());c.step(np.array([[t]]),np.array([[t]]))
        return np.array(a)
    y=x.copy();y[3:]=1
    assert np.array_equal(run(x)[:4],run(y)[:4])

def test_one_atomic_switch_per_period():
    cfg=Settings(window=1)
    c=Controller((2,10),'rolling_portfolio',cfg)
    accepted,_=c.step(-np.ones((2,10)),-np.ones((2,10)))
    assert np.all(accepted.sum(axis=1)==1)

def test_conditional_marginal_matches_difference():
    cfg=Settings();s=simulate('negative_hedge','gaussian',3,6,2,42)
    active=np.ones((3,2),bool)
    d=marginal_mean(active,s.means[:,0],s.rho[0],s.scale2[:,0],s.common_var,cfg)
    for j in range(2):
        off=active.copy();off[:,j]=False
        diff=conditional_value(active,s.means[:,0],s.rho[0],s.scale2[:,0],s.common_var,cfg)-conditional_value(off,s.means[:,0],s.rho[0],s.scale2[:,0],s.common_var,cfg)
        np.testing.assert_allclose(d[:,j],diff,atol=1e-14)

def test_psd_covariance_and_negative_mean_hedge():
    cfg=Settings();s=simulate('negative_hedge','gaussian',1,10,4,7)
    r=s.rho[0];v=np.r_[1,r]
    cov=np.outer(v,v)+np.diag(np.r_[0,1-r*r])
    assert np.linalg.eigvalsh(cov).min()>0
    assert np.all(s.means[:,0,1:]<0)
    assert np.all(marginal_mean(np.ones((1,4),bool),s.means[:,0],r,s.scale2[:,0],1,cfg)>0)

def test_positive_redundant_has_negative_policy_value():
    cfg=Settings();s=simulate('positive_redundant','gaussian',1,10,1,7)
    assert s.means[0,0,1]>0
    assert marginal_mean(np.ones((1,1),bool),s.means[:,0],s.rho[0],s.scale2[:,0],1,cfg)[0,0]<0

def test_input_validation():
    with pytest.raises(ValueError):Settings(delta=2)
    with pytest.raises(ValueError):RestartMixture((1,1),Settings()).update(np.array([[1.1]]))

def test_constant_positive_evidence_accumulates():
    e=RestartMixture((1,1),Settings())
    for _ in range(30):v=e.update(np.ones((1,1)))
    assert v[0,0]>e.threshold()[0,0]
