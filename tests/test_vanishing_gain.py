import importlib.util
import json
from pathlib import Path
import numpy as np
from numpy.polynomial.hermite import hermgauss
from scipy.stats import norm

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('vanishing',ROOT/'scripts/vanishing_gain_study.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def test_feedback_null_by_independent_gaussian_quadrature():
    cfg=json.loads((ROOT/'configs/vanishing_gain.json').read_text())
    points,weights=hermgauss(48);weights/=np.sqrt(np.pi)
    for w in np.linspace(-.5,.5,21):
        mean,sd=module.null_parameters(w,cfg);a=mean+sd*np.sqrt(2)*points
        score=-w*a+cfg['gamma']*w*w*a*a/2
        assert abs(weights@score)<1e-14
        assert weights@(a*a)<=cfg['public_second']+1e-14
        assert weights@(a**4)<=cfg['public_fourth']+1e-14
        factor=1+cfg['gamma']*score/2
        assert np.min(factor)>=.75
        np.testing.assert_allclose(weights@factor,1.,atol=1e-14)


def test_controlled_path_matches_independent_scalar_accounting():
    cfg=json.loads((ROOT/'configs/vanishing_gain.json').read_text())
    cfg.update(replications=3,observations=8,training=8,review_block=3)
    # Disjoint software stream: the declared scientific seed is not consumed.
    seed=940001;result=module.simulate(cfg,'gaussian_alternative',seed)
    rng=np.random.default_rng(seed);training=rng.normal(0,cfg['sigma'],(cfg['training'],cfg['replications']))
    draws=rng.normal(size=(cfg['observations'],cfg['replications']))*cfg['sigma']
    bound=cfg['leverage']**2*(np.sqrt(cfg['public_second'])+cfg['gamma']*cfg['leverage']*np.sqrt(cfg['public_fourth'])/2)**2
    for j in range(cfg['replications']):
        history=list(training[:,j]);scores=[];logs=np.zeros(4);lr=0.;integrated=0.
        for t,observation in enumerate(draws[:,j]):
            target=np.clip(np.mean(history)/(cfg['gamma']*(np.mean(np.square(history))+cfg['ridge'])),-cfg['leverage'],cfg['leverage'])
            if t%cfg['review_block']==0:
                signal=cfg['initial_gain'] if not scores else max(0.,np.mean(scores))
                bet=min(signal/(2*bound),1/(2*np.sqrt(bound)))
            y=cfg['gamma']*target**2*observation**2/2-target*observation;fixed=cfg['gamma']/2
            def transform(x):return np.sign(x)*np.log(1+abs(x)+x*x/2)
            local=target**2*(np.sqrt(cfg['public_second'])+cfg['gamma']*abs(target)*np.sqrt(cfg['public_fourth'])/2)**2
            logs+=[np.log(1+fixed*y),transform(fixed*y)-fixed**2*local/2,
                   transform(fixed*y)-fixed**2*bound/2,transform(bet*y)-bet**2*bound/2]
            mean,sd=module.null_parameters(target,cfg)
            lr+=norm.logpdf(observation,0,cfg['sigma'])-norm.logpdf(observation,mean,sd)
            integrated+=target*target;scores.append(y);history.append(observation)
        np.testing.assert_allclose(result['log_capital'][-1,:,j],logs,atol=1e-14)
        np.testing.assert_allclose(result['log_likelihood_ratio'][-1,j],lr,atol=1e-14)
        np.testing.assert_allclose(result['sum_w2'][-1,j],integrated,atol=1e-14)
