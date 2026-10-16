from dataclasses import replace
from math import comb,factorial
import numpy as np
import pytest
from scipy.optimize import linprog
from park_revive.config import Config
from park_revive.optimizer import Optimizer
from park_revive_extensions.certificates import PublicRisk,laplace_even_moment,paired_score_caps
from park_revive_extensions.tail_betting import TailMixture,tail_bias
from park_revive.dgp import Market,Observed


class FutureMarket(Market):
    def step(self):
        obs,truth=super().step()
        if obs.day>=2*self.cfg.block:
            obs=Observed(obs.day,obs.returns+np.linspace(-.01,.01,100),obs.signal_ids)
        return obs,truth


def test_support_function_matches_independent_linear_program():
    risk=PublicRisk(.2,.73,(0.,),(1.,),(.1,),.02)
    rng=np.random.default_rng(72001)
    for _ in range(10):
        a=rng.normal(size=12)
        result=linprog(-a,A_ub=np.ones((1,12)),b_ub=[.73],bounds=[(0,.2)]*12,method='highs')
        assert result.success
        assert risk.support(a)==pytest.approx(-result.fun,abs=1e-12)
        perm=rng.permutation(12)
        assert risk.support(a[perm])==pytest.approx(risk.support(a),abs=1e-15)


def test_laplace_even_envelope_single_shock_exact_and_sums():
    m=.13;v=.07
    for order in (2,4,6,8):
        exact=sum(comb(order,k)*m**(order-k)*factorial(k)*(v/2)**(k/2) for k in range(0,order+1,2))
        assert laplace_even_moment(m,v,order)==pytest.approx(exact)
    # Convolve exact independent centered Laplace moments, then add a shift.
    h=np.array([.1,-.2,.03]);mom=np.zeros(9);mom[0]=1
    for value in h:
        right=np.array([factorial(k)*(abs(value)/np.sqrt(2))**k if k%2==0 else 0 for k in range(9)])
        mom=np.array([sum(comb(n,k)*mom[k]*right[n-k] for k in range(n+1)) for n in range(9)])
    for n in (2,4,6,8):
        true=sum(comb(n,k)*m**(n-k)*mom[k] for k in range(n+1))
        assert true<=laplace_even_moment(m,np.sum(h*h),n)*(1+1e-12)


@pytest.mark.parametrize('order,constant',[(2,1/4),(4,27/256)])
def test_tail_bound_sharpness(order,constant):
    b=.07;x=np.r_[0.,np.logspace(-7,3,1000),order*b/(order-1)]
    assert np.all(np.maximum(x-b,0)<=constant*x**order/b**(order-1)+1e-12)
    at=order*b/(order-1)
    assert at-b==pytest.approx(constant*at**order/b**(order-1))


def test_corrected_factors_valid_on_asymmetric_conditional_null():
    # Mean-zero rare negative tail: lower clipping WITHOUT correction is invalid.
    for probability in (.001,.01,.1,.3):
        negative=-4/3;positive=-probability*negative/(1-probability)
        points=np.array([negative,positive]);probs=np.array([probability,1-probability])
        second=probs@(points**2);fourth=probs@(points**4)
        mixture=TailMixture(1);levels,biases,bets,_=mixture.prepare(second,fourth)
        for i in range(len(mixture.grid)):
            transformed=np.maximum(points,-levels[i,0])-biases[i,0]
            factors=1+bets[i,0]*transformed
            assert np.min(factors)>0
            assert probs@factors<=1+1e-14
        assert probs@np.maximum(points,-1.)>0


def test_mixture_identity_zero_score_and_scaling():
    y=np.array([-.01,.02,.003]);a=TailMixture(3);b=TailMixture(3)
    for _ in range(5):
        a.update(y,a.prepare(.01,.001))
        b.update(100*y,b.prepare(100**2*.01,100**4*.001))
    np.testing.assert_allclose(a.log_e,b.log_e,atol=1e-14)
    c=TailMixture(1);c.update(0.,c.prepare(0.,0.))
    assert c.log_e[0]==0
    with pytest.raises(ValueError):c.update(.1,c.prepare(0.,0.))


def test_public_caps_use_no_realized_coefficients_and_cover_both_regimes():
    cfg=replace(Config(),stress_multiplier=.5)
    risk=PublicRisk.from_market_contract(cfg)
    assert risk.factor_scales_max==cfg.factor_scales
    assert risk.idio_scale_max==cfg.idio_scale
    assert not hasattr(risk,'theta') and not hasattr(risk,'regime')
    q=np.array([.5,-.5]);values=np.array([[.2,.4,-.1],[-.3,.1,.7]])
    second,fourth=paired_score_caps(q,q,values,.01,cfg.gamma,risk)
    assert second==pytest.approx(.01**2)
    assert fourth==pytest.approx(.01**4)


def test_single_coordinate_update_matches_independent_QP():
    cfg=replace(Config(),gamma=3.,proportional=.001,impact=.002)
    for mu,m,b in ((.003,.0002,0.),(-.002,.0001,.5),(.002,.0001,1.),(.0001,.1,-.3)):
        gradient=mu-cfg.gamma*m*b
        exact=np.clip(b+np.sign(gradient)*max(abs(gradient)-cfg.proportional,0)/(cfg.gamma*m+cfg.impact),-cfg.leverage,cfg.leverage)
        sol=Optimizer(cfg,np.array([mu]),np.array([[m]])).solve((0,),np.array([b]))
        assert sol.weights[0]==pytest.approx(exact,abs=1e-6)


def test_exact_score_fourth_moment_against_independent_monte_carlo():
    from park_revive.dgp import Truth
    from park_revive_extensions.first_entry import exact_forward_truth
    rng=np.random.default_rng(72002)
    mu=np.array([.02,-.01]);h=np.array([[.07,.02],[-.03,.06]])
    truth=Truth(0,mu,h,np.outer(mu,mu)+h@h.T,np.zeros(2),0,False)
    w=np.array([.5,-.3]);cost=np.array([.002,.001])
    first,second,fourth=exact_forward_truth(w,cost,truth,3.)
    z=rng.laplace(0,1/np.sqrt(2),(400000,2));r=(mu+z@h.T)*w
    y=r-3*r*r/2-cost
    for order,expected in ((1,first),(2,second),(4,fourth)):
        values=y**order
        assert np.all(np.abs(values.mean(axis=0)-expected)<6*values.std(axis=0)/np.sqrt(len(y)))


def test_first_entry_replay_and_checkpoint_are_identical(tmp_path):
    from park_revive_extensions.first_entry import run_seed
    import pandas as pd
    cfg=replace(Config(),n_assets=12,block=4,years=3)
    run_seed(cfg,72003,tmp_path/'full')
    run_seed(cfg,72003,tmp_path/'resumed',stop_after_blocks=1)
    run_seed(cfg,72003,tmp_path/'resumed',resume=True)
    for filename in ('annual_events.csv','summary.csv'):
        a=pd.read_csv(tmp_path/'full'/filename);b=pd.read_csv(tmp_path/'resumed'/filename)
        # Wall-clock measurements are intentionally not replay invariants.
        if 'elapsed_seconds' in a:a=a.drop(columns='elapsed_seconds');b=b.drop(columns='elapsed_seconds')
        pd.testing.assert_frame_equal(a,b)


def test_first_entry_evidence_certificates_and_weights_are_causal(tmp_path,monkeypatch):
    import pandas as pd
    import park_revive_extensions.first_entry as driver
    cfg=replace(Config(),n_assets=12,block=4,years=3)
    driver.run_seed(cfg,72004,tmp_path/'original')
    monkeypatch.setattr(driver,'Market',FutureMarket)
    driver.run_seed(cfg,72004,tmp_path/'future_changed')
    pd.testing.assert_frame_equal(
        pd.read_parquet(tmp_path/'original/block_01/score_ledger.parquet'),
        pd.read_parquet(tmp_path/'future_changed/block_01/score_ledger.parquet'))
    pd.testing.assert_frame_equal(
        pd.read_csv(tmp_path/'original/block_01/annual_events.csv'),
        pd.read_csv(tmp_path/'future_changed/block_01/annual_events.csv'))
