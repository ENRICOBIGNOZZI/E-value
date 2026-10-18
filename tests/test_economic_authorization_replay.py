from pathlib import Path
import importlib.util
import json
import numpy as np
import pytest
from test_economic_authorization import study, SETTINGS, Config, ScriptedMarket

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('economic_verifier',ROOT/'extensions/economic_authorization/verify.py')
verify=importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


@pytest.fixture
def completed(tmp_path):
    cfg=Config(n_assets=4,block=4,years=3)
    protocol=dict(extension_source_sha256=study.sha(study.__file__),
                  original_scientific_source_hash=study.source_fingerprint()[0])
    directory=tmp_path/'seed_1'
    study.run_seed(cfg,SETTINGS,protocol,'synthetic',1,directory,ScriptedMarket)
    return directory,cfg


def refresh_hash(directory,name):
    path=directory/'status.json';status=json.loads(path.read_text())
    status['files'][name]=verify.sha(directory/name)
    path.write_text(json.dumps(status))


def test_independent_replay_accepts_complete_fixture(completed):
    directory,cfg=completed;checks=verify.Checks()
    result=verify.replay_seed(directory,cfg,SETTINGS,'synthetic',checks)
    assert result['complete'] and checks.count>100


@pytest.mark.parametrize('field',['arm_utility','log_e','arm_cost'])
def test_independent_replay_rejects_arithmetic_tampering_even_with_new_digest(completed,field):
    directory,cfg=completed
    d=dict(np.load(directory/'ledger.npz'))
    d[field].flat[0]+=1e-4
    np.savez_compressed(directory/'ledger.npz',**d)
    refresh_hash(directory,'ledger.npz')
    with pytest.raises(AssertionError):
        verify.replay_seed(directory,cfg,SETTINGS,'synthetic',verify.Checks())


def test_independent_replay_rejects_premature_authorization(completed):
    directory,cfg=completed
    path=directory/'annual_decisions.json';rows=json.loads(path.read_text())
    rows[0]['full_authorized']=True;path.write_text(json.dumps(rows))
    refresh_hash(directory,'annual_decisions.json')
    with pytest.raises(AssertionError):
        verify.replay_seed(directory,cfg,SETTINGS,'synthetic',verify.Checks())
