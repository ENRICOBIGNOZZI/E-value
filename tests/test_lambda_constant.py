import importlib.util
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('lambda_constant', ROOT/'scripts/lambda_constant_study.py')
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


def small_configuration():
    cfg = json.loads((ROOT/'configs/lambda_power.json').read_text())
    cfg.update(block=3, horizon_blocks=[1, 2], replications=5, audit_path_prefix=5)
    cfg['models'] = {'primary': dict(step=.1, lower=-4., actions=5)}
    return cfg


def test_constant_hitting_power_matches_independent_discrete_dynamic_program():
    cfg = small_configuration()
    model, _ = study.base.build_model(cfg, cfg['models']['primary'])
    fixed, _ = study.fixed_model(cfg, model)
    kernels, _ = study.base.block_kernels(cfg, model['actions'], float(model['step']))
    radius = (kernels.shape[1]-1)//2
    changes = np.arange(-radius, radius+1)*float(model['step'])
    for j, kernel in enumerate(kernels):
        value = np.zeros(len(model['states'])); value[-1] = 1.
        for h in (1, 2):
            updated = np.array([kernel @ np.interp(state+changes, model['states'], value, left=0., right=1.)
                                for state in model['states']])
            updated[-1] = 1.; value = updated
            expected = np.interp(0., model['states'], value)
            np.testing.assert_allclose(fixed['power'][h-1, j], expected, atol=2e-13)
    np.testing.assert_array_equal(fixed['best_indices'], np.argmax(fixed['power'], axis=1))
    for j, h in enumerate(cfg['horizon_blocks']):
        assert fixed['initial_power'][j] <= np.interp(0., model['states'], model['values'][h])+1e-12


def test_companion_shares_score_paths_and_constant_stakes_ignore_evaluation_mean():
    cfg = small_configuration()
    model, _ = study.base.build_model(cfg, cfg['models']['primary'])
    constant, _ = study.fixed_model(cfg, model)
    models = {'primary': model}; fixed = {'primary': constant}
    stream = np.random.SeedSequence(960001)
    a, _ = study.simulate(cfg, 0., stream, models, fixed)
    b, _ = study.simulate(cfg, .3, stream, models, fixed)
    np.testing.assert_array_equal(a['stakes'][0], b['stakes'][0])
    original, _ = study.base.simulate(cfg, 0., stream, models)
    n = len(original['methods'])
    np.testing.assert_array_equal(a['audit_scores'], original['audit_scores'])
    np.testing.assert_array_equal(a['log_capital'][:, :n], original['log_capital'])
    capital = np.zeros((len(a['methods']), cfg['replications']))
    for k in range(2):
        for j, lam in enumerate(a['stakes'][k]):
            product = np.ones(cfg['replications'])
            for score in a['audit_scores'][k*3:(k+1)*3]:
                x = lam*score; envelope = 1+abs(x)+x*x/2
                product *= np.where(x >= 0, envelope, 1/envelope)*np.exp(-lam*lam*cfg['public_second']/2)
            capital[j] += np.log(product)
        np.testing.assert_allclose(capital, a['log_capital'][k+1], atol=1e-13)
    assert np.all(a['stakes'][1, n] == 0.)  # The one-block constant arm has expired.
