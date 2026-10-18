"""Synthetic byte-comparison controls; no generated market or final inference."""
import json
from pathlib import Path
import sys
import shutil
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_fresh_final_60469 import compare_seed


def fixture(tmp_path):
    left = tmp_path/'original'
    left.mkdir()
    roots = ['config_frozen.json','source_manifest.json','feature_library.json','protocol.json',
             'daily_ledger.parquet','comparison_events.parquet','decisions.json','deployments.json',
             'economic_opportunities.json','opportunity_registry.json','metrics_by_seed.csv']
    annual = ['daily_ledger.parquet','comparison_events.parquet','decisions.json','deployments.json',
              'comparison_order.json','shortlists.json','closed_episodes.json','ghost_order.json',
              'solver_recoveries.json','scores_Greedy.npz','scores_HAC.npz','scores_Catoni.npz','scores_Tail.npz']
    for name in roots:
        (left/name).write_bytes(b'software fixture only')
    for year in range(1,15):
        folder = left/f'block_{year:02d}'
        folder.mkdir()
        for name in annual:
            (folder/name).write_bytes(b'software fixture only')
    status = dict(seed=60469,complete=True,completed_blocks=14,total_blocks=14,
                  source_hash='software-fixture',elapsed_seconds=1.,stable_opportunities=7)
    (left/'status.json').write_text(json.dumps(status))
    runtime = 'seed,year,seconds\n'+''.join(f'60469,{year},1.0\n' for year in range(1,15))
    (left/'runtime.csv').write_text(runtime)
    (left/'numerical_initialization.json').write_text(json.dumps(dict(
        initializer_profile_sha256='fixture',calls=[dict(problem_sha256='fixture')])))
    right = tmp_path/'fresh'
    shutil.copytree(left,right)
    (right/'numerical_initialization.json').write_text(json.dumps(dict(
        profile_sha256='fixture',calls=[dict(problem_sha256='fixture')])))
    return left,right


def test_equal_science_with_different_runtime_and_checkpoint_cache(tmp_path):
    left,right = fixture(tmp_path)
    status = json.loads((right/'status.json').read_text())
    status['elapsed_seconds'] = 500.
    (right/'status.json').write_text(json.dumps(status))
    (right/'runtime.csv').write_text((right/'runtime.csv').read_text().replace(',1.0\n',',2.0\n'))
    (right/'checkpoint.pkl.gz').write_bytes(b'regenerable software fixture')
    result = compare_seed(left,right)
    assert result['complete'] and result['byte_identical_scientific_file_pairs'] == 193


@pytest.mark.parametrize('name',['block_12/scores_Tail.npz','decisions.json','metrics_by_seed.csv'])
def test_changed_science_rejected(tmp_path,name):
    left,right = fixture(tmp_path)
    (right/name).write_bytes(b'changed software fixture')
    with pytest.raises(ValueError,match='Scientific artifact differs'):
        compare_seed(left,right)


def test_missing_file_on_both_sides_is_not_success(tmp_path):
    left,right = fixture(tmp_path)
    for folder in [left,right]:
        (folder/'block_14/scores_Catoni.npz').unlink()
    with pytest.raises(ValueError,match='Incomplete'):
        compare_seed(left,right)


def test_unexpected_block_file_cannot_hide_behind_root_timing_exclusion(tmp_path):
    left,right = fixture(tmp_path)
    (right/'block_01/runtime.csv').write_text('unexpected fixture artifact')
    with pytest.raises(ValueError,match='Scientific file membership'):
        compare_seed(left,right)


def test_changed_event_count_cannot_be_ignored_as_timing(tmp_path):
    left,right = fixture(tmp_path)
    status = json.loads((right/'status.json').read_text())
    status['stable_opportunities'] += 1
    (right/'status.json').write_text(json.dumps(status))
    with pytest.raises(ValueError,match='Scientific status'):
        compare_seed(left,right)


def test_runtime_calendar_cannot_be_changed(tmp_path):
    left,right = fixture(tmp_path)
    (right/'runtime.csv').write_text((right/'runtime.csv').read_text().replace('60469,14,','60469,15,'))
    with pytest.raises(ValueError,match='Runtime calendar'):
        compare_seed(left,right)


def test_different_numerical_initialization_is_rejected(tmp_path):
    left,right = fixture(tmp_path)
    (right/'numerical_initialization.json').write_text(json.dumps(dict(
        profile_sha256='changed',calls=[dict(problem_sha256='fixture')])))
    with pytest.raises(ValueError,match='Numerical initialization'):
        compare_seed(left,right)
