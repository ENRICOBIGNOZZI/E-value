import importlib.util
import json
from pathlib import Path
import numpy as np
from scipy.stats import norm

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('lambda_power',ROOT/'scripts/lambda_power_study.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def small_config():
    cfg=json.loads((ROOT/'configs/lambda_power.json').read_text())
    cfg.update(block=3,horizon_blocks=[1,2],replications=5,audit_path_prefix=5)
    cfg['models']={'primary':dict(step=.1,lower=-4.,actions=5)}
    return cfg


def test_log_growth_choice_beats_certificate_and_respects_curvature_bounds():
    cfg=small_config();lam=module.log_growth_bet(cfg);bound=cfg['public_second'];delta=cfg['design_mean']
    assert 4*delta/(5*bound)<=lam<=4*delta/(3*bound)
    from scipy.integrate import quad
    def value(stake):
        return quad(lambda z:float(module.phi(stake*(delta+z)))*norm.pdf(z),-12,12,epsabs=1e-12)[0]-stake**2*bound/2
    assert value(lam)>value(delta/(2*bound))
    assert value(lam)>value(lam*.9) and value(lam)>value(lam*1.1)
    x=np.array([-100.,-2.,-.01,0.,.01,2.,100.])
    np.testing.assert_allclose(module.inverse_phi(module.phi(x)),x,atol=1e-12)


def test_fft_bellman_recursion_matches_direct_discrete_expectation():
    cfg=small_config();settings=cfg['models']['primary'];model,_=module.build_model(cfg,settings)
    kernels,_=module.block_kernels(cfg,model['actions'],settings['step'])
    radius=(kernels.shape[1]-1)//2;increments=np.arange(-radius,radius+1)*settings['step']
    for h in [1,2]:
        for j,state in enumerate(model['states'][:-1]):
            expected=[]
            for kernel in kernels:
                next_value=np.interp(state+increments,model['states'],model['values'][h-1],left=0.,right=1.)
                expected.append(kernel@next_value)
            np.testing.assert_allclose(model['values'][h,j],max(expected),atol=2e-13)
            chosen=int(model['policy'][h,j])
            assert expected[chosen]>=max(expected)-2e-13


def test_bets_precede_scores_and_do_not_use_actual_alternative_mean():
    cfg=small_config();model,_=module.build_model(cfg,cfg['models']['primary']);models={'primary':model}
    a,_=module.simulate(cfg,0.,950001,models);b,_=module.simulate(cfg,.3,950001,models)
    np.testing.assert_array_equal(a['stakes'][0],b['stakes'][0])
    for result in [a,b]:
        assert np.all(result['stakes']>=0)
        assert np.all(result['stakes']<=cfg['cap_multiplier']/np.sqrt(cfg['public_second'])+1e-15)
        # Independent multiplicative replay of every small software path.
        capital=np.zeros((len(result['methods']),cfg['replications']))
        for k in range(2):
            for j,lam in enumerate(result['stakes'][k]):
                factors=[]
                for y in result['audit_scores'][k*3:(k+1)*3]:
                    x=lam*y;base=1+abs(x)+x*x/2
                    factors.append(np.where(x>=0,base,1/base)*np.exp(-lam*lam*cfg['public_second']/2))
                capital[j]+=np.log(np.prod(factors,axis=0))
            np.testing.assert_allclose(capital,result['log_capital'][k+1],atol=1e-13)


def test_nearest_grid_rounding_cannot_absorb_a_subthreshold_capital():
    model=dict(states=np.array([-1.,0.,1.]),actions=np.array([0.,.1,.2]),
               policy=np.array([[0,0,0],[2,1,0]],dtype=int),step=np.array(1.))
    bets=module.choose(model,1,np.array([.50001,.999999999,1.]))
    np.testing.assert_array_equal(bets,np.array([.1,.1,0.]))
