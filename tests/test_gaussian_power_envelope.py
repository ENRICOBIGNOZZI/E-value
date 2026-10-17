import copy
import csv
import importlib.util
import json
from pathlib import Path
import shutil

import numpy as np
import pytest
from scipy.stats import binom, norm

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('power_envelope', ROOT/'scripts/gaussian_power_envelope.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def panel():
    cfg = json.loads((ROOT/'reports/lambda_constant_results/model_manifest.json').read_text())['config']
    with (ROOT/'reports/lambda_constant_results/summary.csv').open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    return rows, cfg


def test_bound_is_attained_by_terminal_gaussian_sum_and_has_correct_limits():
    for shift in (0., .5, 2., 4.):
        assert module.envelope(0., shift) == 0.
        assert module.envelope(1., shift) == 1.
        for size in (.001, .01, .05, .5, .99):
            np.testing.assert_allclose(module.envelope(size, shift), norm.sf(norm.isf(size)-shift), atol=2e-15)
    np.testing.assert_allclose(module.envelope(.05, 0.), .05, atol=1e-15)
    np.testing.assert_allclose(module.envelope(.05, 2.), .638760031312335, atol=1e-14)


@pytest.mark.parametrize('size,shift', [(-.1, 1.), (1.1, 1.), (float('nan'), 1.),
                                       (.05, -.1), (.05, float('inf'))])
def test_invalid_gaussian_parameters_rejected(size, shift):
    with pytest.raises(ValueError):
        module.envelope(size, shift)


def test_exact_binomial_limits_invert_tails_and_cover_each_tail():
    total, tail = 12, .01
    lower, upper = [], []
    for count in range(total+1):
        lo, hi = module.binomial_bounds(count, total, tail)
        lower.append(lo); upper.append(hi)
        if count:
            np.testing.assert_allclose(binom.sf(count-1, total, lo), tail, atol=2e-14)
        else:
            assert lo == 0.
        if count < total:
            np.testing.assert_allclose(binom.cdf(count, total, hi), tail, atol=2e-14)
        else:
            assert hi == 1.
    for probability in np.linspace(0., 1., 101):
        weights = binom.pmf(np.arange(total+1), total, probability)
        assert sum(weights[k] for k in range(total+1) if lower[k] > probability) <= tail+1e-13
        assert sum(weights[k] for k in range(total+1) if upper[k] < probability) <= tail+1e-13


@pytest.mark.parametrize('count,total,tail', [(-1, 10, .01), (11, 10, .01), (0, 0, .01),
                                           (1.5, 10, .01), (True, 10, .01),
                                           (1, 10, 0.), (1, 10, 1.)])
def test_invalid_binomial_inputs_rejected(count, total, tail):
    with pytest.raises(ValueError):
        module.binomial_bounds(count, total, tail)


def test_complete_panel_and_simultaneous_family_use_each_null_once():
    rows, cfg = panel()
    report = module.calculate(rows, cfg)
    assert len(report['rows']) == 36
    assert report['one_sided_binomial_bounds_in_family'] == 48
    assert report['per_bound_noncoverage'] == .05/48
    assert all(row['compatible_with_simultaneous_envelope'] for row in report['rows'])
    assert {row['alternative_mean'] for row in report['rows']} == {.1, .2, .3}
    assert len({row['method'] for row in report['rows']}) == 12
    for row in report['rows']:
        assert row['simultaneous_null_size_upper'] >= row['observed_null_fraction']
        assert row['simultaneous_power_lower'] <= row['observed_power']
        assert row['simultaneous_power_envelope_upper'] >= row['empirical_size_plugin_envelope']


def test_statistically_incompatible_panel_is_retained_and_flagged():
    rows, cfg = panel()
    for row in rows:
        count = 0 if float(row['mean']) == 0. else cfg['replications']
        row['crossings'] = str(count)
        row['power'] = str(count/cfg['replications'])
    report = module.calculate(rows, cfg)
    assert len(report['rows']) == 36
    assert any(not row['compatible_with_simultaneous_envelope'] for row in report['rows'])


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'wrong_count', 'wrong_total',
                                   'inconsistent_power', 'wrong_horizon'])
def test_corrupt_or_incomplete_target_panel_rejected(change):
    rows, cfg = panel()
    target = next(row for row in rows if row['method'] == 'DP primary H=400' and float(row['mean']) == 0.)
    if change == 'missing':
        rows.remove(target)
    elif change == 'duplicate':
        rows.append(copy.deepcopy(target))
    elif change == 'wrong_count':
        target['crossings'] = '20001'
    elif change == 'wrong_total':
        target['replications'] = '10000'
    elif change == 'inconsistent_power':
        target['power'] = '.99'
    else:
        target['observations'] = '800'
    with pytest.raises(ValueError):
        module.calculate(rows, cfg)


@pytest.mark.parametrize('path', ['reports/lambda_constant_results/summary.csv',
                                 'scripts/lambda_constant_study.py',
                                 'scripts/audit_lambda_constant.py'])
def test_changed_audited_input_scientific_source_or_auditor_rejected(tmp_path, path):
    directory = ROOT/'reports/lambda_constant_results'
    freeze = json.loads((directory/'protocol_frozen.json').read_text())
    audit = json.loads((directory/'verification.json').read_text())
    files = {f'reports/lambda_constant_results/{name}' for name in
             ('verification.json', 'protocol_frozen.json', 'model_manifest.json', 'summary.csv', 'status.json')}
    files.update(freeze['source_files']); files.update(audit['audit_sources'])
    for relative in files:
        dest = tmp_path/relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, dest)
    changed = tmp_path/path
    changed.write_bytes(changed.read_bytes()+b'\n')
    with pytest.raises(ValueError, match='Changed'):
        module.run(tmp_path)
    assert not (tmp_path/'reports/lambda_constant_results/gaussian_power_envelope.json').exists()
