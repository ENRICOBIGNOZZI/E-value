"""Software fixtures only: no generated financial markets or new replications."""
import csv
import json
import math
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from assess_final_study import assess, calculate, canonical_hash, sha256


@pytest.fixture
def plan():
    return json.loads((ROOT/'reports/final_analysis_plan.json').read_text())


def software_rows(plan, sign=1):
    rows = []
    for index, seed in enumerate(plan['final_seeds']):
        for method in plan['methods']:
            value = .1 + sign*(.01 if index % 2 == 0 else .03) if method == 'Tail' else .1
            rows.append(dict(seed=seed, method=method, annual_scaled_utility=value))
    return rows


@pytest.mark.parametrize('sign', [1, -1])
def test_paired_effect_uses_all_markets_and_preserves_either_direction(plan, sign):
    contrasts = calculate(software_rows(plan, sign), plan['final_seeds'], plan)
    assert len(contrasts) == 5
    primary = next(r for r in contrasts if r['role'] == 'primary')
    assert primary['reference'] == 'All Signals' and primary['n'] == 500
    assert primary['mean_difference'] == pytest.approx(sign*.02)
    # Alternating differences have mean +/- .02 and squared deviations .0001.
    assert primary['standard_error'] == pytest.approx(.01/math.sqrt(499))
    radius = (primary['ci_high'] - primary['ci_low'])/2
    assert 1.96 < radius/primary['standard_error'] < 1.97


@pytest.fixture
def snapshot(tmp_path, plan):
    directory = tmp_path/'synthetic-report'
    directory.mkdir()
    metrics = directory/'metrics_by_seed.csv'
    with metrics.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['seed','method','annual_scaled_utility'])
        writer.writeheader(); writer.writerows(software_rows(plan))
    freeze = json.loads((ROOT/plan['scientific_protocol']).read_text())
    seal = dict(complete=True, kind='final', stage='main', seeds=plan['final_seeds'],
        source_hash=freeze['scientific_source_hash'],
        config_hash=canonical_hash(freeze['final_config']),
        protocol_freeze_sha256=plan['scientific_protocol_sha256'],
        files_sha256={'metrics_by_seed.csv':sha256(metrics)})
    (directory/'snapshot_seal.json').write_text(json.dumps(seal))
    return directory


def test_complete_synthetic_final_is_distinct_from_pilot(snapshot):
    result = assess(snapshot, ROOT/'reports/final_analysis_plan.json')
    assert result['kind'] == 'complete_final_assessment'
    assert result['markets'] == 500


@pytest.mark.parametrize('change', ['partial','duplicate_seed','wrong_source','wrong_config'])
def test_bad_final_membership_or_stage_is_rejected(snapshot, change):
    path = snapshot/'snapshot_seal.json'; seal = json.loads(path.read_text())
    if change == 'partial':seal['seeds'].pop()
    elif change == 'duplicate_seed':seal['seeds'][-1] = seal['seeds'][0]
    elif change == 'wrong_source':seal['source_hash'] = 'different scientific version'
    else:seal['config_hash'] = 'pilot configuration'
    path.write_text(json.dumps(seal))
    with pytest.raises(ValueError):assess(snapshot, ROOT/'reports/final_analysis_plan.json')


@pytest.mark.parametrize('change', ['missing_method','duplicate_row','missing_utility'])
def test_primary_outcomes_are_never_silently_dropped(plan, change):
    rows = software_rows(plan)
    if change == 'missing_method':rows.pop()
    elif change == 'duplicate_row':rows.append(rows[0])
    else:rows[0]['annual_scaled_utility'] = float('nan')
    with pytest.raises(ValueError):calculate(rows, plan['final_seeds'], plan)


def test_observed_pilot_cannot_be_labeled_final():
    directory = ROOT/'reports/full_v3_snapshots/pilot_020'
    plan_path = ROOT/'reports/final_analysis_plan.json'
    with pytest.raises(ValueError, match='all 500'):
        assess(directory, plan_path)
    result = assess(directory, plan_path, pilot_diagnostic=True)
    assert result['kind'] == 'pilot_diagnostic' and result['markets'] == 20
    assert result['primary']['mean_difference'] < 0


def test_changed_outcomes_after_sealing_cannot_be_assessed(snapshot):
    with (snapshot/'metrics_by_seed.csv').open('a') as stream:stream.write('\n')
    with pytest.raises(ValueError, match='artifact changed'):
        assess(snapshot, ROOT/'reports/final_analysis_plan.json')
