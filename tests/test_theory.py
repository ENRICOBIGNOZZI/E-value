from dataclasses import replace
import numpy as np
import pytest
from scipy.optimize import minimize
from park_revive.config import Config
from park_revive.costs import cost_components,utility,expected_utility
from park_revive.eprocess import Evidence,phi,public_envelope
from park_revive.optimizer import Optimizer
from park_revive.oracle import score_moments
from park_revive.dgp import Truth
from park_revive.pvalues import hac_pvalue,hac_variance
from park_revive.experiments import wilson


def test_phi_envelope_odd_precision_and_extremes():
    x=np.r_[-np.logspace(-16,3,300),0,np.logspace(-16,3,300)]
    assert np.allclose(phi(-x),-phi(x),atol=0)
    assert phi(0)==0
    # Log formulation avoids exponent overflow at test extremes.
    assert np.all(phi(x)<=np.log1p(x+x*x/2)+1e-12)
    assert np.all(-phi(x)<=np.log1p(-x+x*x/2)+1e-12)
    assert np.all(phi(x)>=x-x*x/2-1e-11)
    assert phi(1e-15)==pytest.approx(1e-15,rel=1e-14)
    with np.errstate(over='raise',invalid='raise'):
        assert np.isfinite(phi(np.array([-1e300,1e300]))).all()


def test_daily_block_and_constant_scaling():
    y=np.random.default_rng(7).normal(.1,.8,400)
    a=Evidence(1.,.1);a.start_block()
    b=Evidence(1/9,.1/3);b.start_block()
    for t,value in enumerate(y):
        if t%100==0 and t:
            a.start_block();b.start_block()
        a.update(value);b.update(value/3)
    assert a.log_e==pytest.approx(b.log_e,abs=1e-12)
    c=Evidence(1.,.1);c.start_block();bet=c.bet
    for v in y:c.update(v)
    assert c.log_e==pytest.approx(np.sum(phi(bet*y)-bet*bet/2),abs=1e-12)


def test_T1_conditional_multiplier_and_predictable_null():
    # Independent Monte Carlo null law; stochastic scale is past-measurable.
    rng=np.random.default_rng(12);r=12000
    loge=np.zeros(r);past=np.zeros(r);ever=np.zeros(r,bool)
    for t in range(500):
        lam=np.clip(np.maximum(past,0)/max(t,1)/2,0,.5) if t else np.full(r,.15)
        scale=np.where(past>0,1.,.5)
        y=scale*rng.laplace(0,1/np.sqrt(2),r)
        loge+=phi(lam*y)-lam*lam/2;past+=y;ever|=loge>=np.log(20)
    lo,hi=wilson(int(ever.sum()),r)
    assert lo<=.05  # Statistical bound checked with its sampling uncertainty.
    assert np.exp(loge).mean()<1.05
    # Exact two-point conditional multiplier checks, without simulation noise.
    for lam in (0,.1,1.,5.):
        assert np.mean(np.exp(phi(lam*np.array([-1.,1.]))-lam*lam/2))<=1+1e-12


def test_T2_quadratic_certificate_and_plugin_MSE():
    delta=.2;nu2=1.;star=delta/(2*nu2)
    lam=np.linspace(0,1,1001)
    assert np.allclose(lam*delta-lam*lam*nu2,delta*delta/(4*nu2)-nu2*(lam-star)**2)
    assert lam[np.argmax(lam*delta-lam*lam*nu2)]==pytest.approx(star)
    rng=np.random.default_rng(18);r=6000;h=50;kmax=12
    total=np.zeros(r);regret=np.zeros(r);initial=.05
    for k in range(1,kmax+1):
        bet=np.full(r,initial) if k==1 else np.clip(total/(h*(k-1))/2,0,.5)
        regret+=h*(bet-star)**2
        total+=rng.normal(delta,np.sqrt(1-delta*delta),(h,r)).sum(axis=0)
    bound=h*(initial-star)**2+sum(1/k for k in range(1,kmax))/4
    assert regret.mean()<=bound+4*regret.std()/np.sqrt(r)


def independent_unconstrained(mu,m,b,cfg,support):
    idx=np.array(support);w0=np.zeros(len(mu))
    def objective(x):
        w=w0.copy();w[idx]=x
        return -expected_utility(w,b,mu,m,cfg)
    # Powell is independent of the OSQP epigraph formulation and supports nonsmooth cost.
    result=minimize(objective,np.zeros(len(idx)),method='Powell',options={'xtol':1e-10,'ftol':1e-12,'maxiter':10000})
    assert result.success
    return -result.fun


@pytest.mark.parametrize('c',[0.,.04,.2])
def test_T3_schur_and_nonsmooth_bounds(c):
    cfg=replace(Config(),gamma=1.,proportional=c,impact=.1,leverage=100.)
    mu=np.array([.4,.3,.1]);m=np.array([[1.,.3,.1],[.3,.8,.1],[.1,.1,.6]])
    b=np.array([.1,0.,0.]);s=(0,);j=1
    opt=Optimizer(cfg,mu,m);w=opt.solve(s,b).weights
    value0=independent_unconstrained(mu,m,b,cfg,s)
    value1=independent_unconstrained(mu,m,b,cfg,(0,j))
    h=cfg.gamma*m+cfg.impact*np.eye(3);a=mu+cfg.impact*b
    q=a[j]-h[j,0]*w[0];d=h[j,j]-h[j,0]**2/h[0,0]
    lower=max(abs(q)-c,0)**2/(2*h[j,j]);upper=max(abs(q)-c,0)**2/(2*d)
    assert lower-1e-7<=value1-value0<=upper+1e-7
    if c==0:assert value1-value0==pytest.approx(upper,abs=1e-9)


def test_T3_leverage_invalidates_unconstrained_formula():
    cfg=replace(Config(),gamma=1.,proportional=0.,impact=0.,leverage=.1)
    opt=Optimizer(cfg,np.array([1.]),np.array([[1.]]))
    sol=opt.solve((0,),np.zeros(1))
    assert sol.weights[0]==pytest.approx(.1,abs=1e-7)
    assert sol.value < .5  # Unconstrained Schur value.
    assert sol.primal_residual<1e-6 and sol.dual_residual<1e-6


def test_T4_moment_perturbations_and_different_states():
    cfg=replace(Config(),gamma=1.,proportional=.01,impact=.02)
    mu=np.array([.2,.1,.05]);m=np.diag([.6,.5,.4]);muh=mu+np.array([.005,-.002,.001]);mh=m+np.eye(3)*.002
    eps=cfg.leverage*np.linalg.norm(muh-mu)+cfg.gamma*cfg.leverage**2*np.linalg.norm(mh-m,2)/2
    oracle=Optimizer(cfg,mu,m);estimated=Optimizer(cfg,muh,mh)
    regrets=[]
    for s,b in [((0,),np.array([.1,0,0])),((0,1),np.array([.2,.1,0]))]:
        best=oracle.solve(s,b);hat=estimated.solve(s,b)
        regret=best.value-expected_utility(hat.weights,b,mu,m,cfg)
        assert -1e-8<=regret<=2*eps+1e-8
        regrets.append(regret)
    assert abs(regrets[0]-regrets[1])<=2*eps


def test_cost_liquidation_empty_and_raw_second_moment():
    cfg=Config();b=np.array([.5,-.2]);zero=np.zeros(2)
    costs=cost_components(zero,b,cfg)
    assert sum(costs)>0
    opt=Optimizer(cfg,np.array([.1,.2]),np.eye(2)*.1)
    assert opt.solve((),b).value==pytest.approx(-sum(costs))
    assert opt.solve((),zero).value==0
    assert utility(.1,.01,5)==pytest.approx(.1-5*.1**2/2-.01)
    mu=np.array([.1,.2]);cov=np.eye(2)*.1;m=cov+np.outer(mu,mu)
    assert expected_utility(b,zero,mu,m,cfg)<expected_utility(b,zero,mu,cov,cfg)


def test_laplace_conditional_moments_independent_MC():
    rng=np.random.default_rng(81001);cfg=replace(Config(),gamma=3.,proportional=.01,impact=.02)
    mean=np.array([.03,-.01]);load=np.array([[.1,.04,.03],[.02,-.08,.04]])
    truth=Truth(0,mean,load,np.outer(mean,mean)+load@load.T,np.zeros(2),0,False)
    wb=np.array([.3,.2]);ws=np.array([-.1,.4]);bb=np.zeros(2);bs=np.array([0.,.2])
    ey,ey2=score_moments(wb,ws,bb,bs,truth,cfg)
    shocks=rng.laplace(0,1/np.sqrt(2),(300000,3));a=mean+shocks@load.T
    x=a@wb;y=a@ws
    scores=utility(x,sum(cost_components(wb,bb,cfg)),cfg.gamma)-utility(y,sum(cost_components(ws,bs,cfg)),cfg.gamma)
    assert abs(scores.mean()-ey)<5*scores.std()/np.sqrt(len(scores))
    assert abs(np.mean(scores*scores)-ey2)<5*np.std(scores*scores)/np.sqrt(len(scores))
    assert score_moments(wb,wb,bb,bb,truth,cfg)==pytest.approx((0.,0.),abs=1e-15)


def test_hac_degenerate_and_past_dependence():
    assert hac_pvalue(np.zeros(10))==1
    assert hac_pvalue(np.ones(10))==0
    x=np.repeat(np.array([-1.,1.,-1.,1.]),20)
    assert hac_variance(x)>np.var(x)


def test_invalid_moments_fail_explicitly():
    with pytest.raises(ValueError):Optimizer(Config(),np.zeros(2),np.diag([1.,-1.]))
    with pytest.raises(ValueError):Config(proportional=-.1)


def test_rejection_does_not_certify_current_sign():
    scores=np.r_[np.full(200,.5),np.full(52,-.5)]
    loge=np.sum(phi(.1*scores)-.1**2/2)
    assert loge>np.log(20) and scores.mean()>0 and scores[-1]<0


def test_no_trade_with_active_leverage_uses_normal_cone():
    cfg=replace(Config(),gamma=1.,proportional=.1,impact=.1,leverage=1.)
    m=np.array([[.1]]);b=np.array([1.])
    positive=Optimizer(cfg,np.array([1.]),m).solve((0,),b)
    np.testing.assert_array_equal(positive.weights,b)
    negative=Optimizer(cfg,np.array([-1.]),m).solve((0,),b)
    assert negative.weights[0]<0
