"""Operational software controls; these create no simulated market paths."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import continue_full_study as workflow


def write_json(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record)+'\n')


def completion(output, seeds, **changes):
    record = dict(stage='pilot',requested_seeds=seeds,all_complete=True,
                  arithmetic_replay_complete=True)
    write_json(output/'stage_completion.json', {**record,**changes})


@pytest.fixture
def frozen_root(tmp_path,monkeypatch):
    for name in ('src','research','scripts','reports','configs'):
        (tmp_path/name).mkdir()
    (tmp_path/'src/scientific.py').write_text('# software fixture\n')
    (tmp_path/'scripts/assess_final_study.py').write_text('# assessment fixture\n')
    (tmp_path/'reports/final_analysis_plan.md').write_text('Fixture plan.\n')
    freeze = dict(pilot_pool=[50001,50100],final_pool=[60001,60500],
        pilot_config={'label':'pilot'},final_config={'label':'final'},
        scientific_source_hash=workflow.canonical_hash({
            'src/scientific.py':workflow.sha256(tmp_path/'src/scientific.py')}))
    write_json(tmp_path/'reports/protocol.json',freeze)
    write_json(tmp_path/'configs/full_pilot.json',freeze['pilot_config'])
    write_json(tmp_path/'configs/full_main.json',freeze['final_config'])
    plan = dict(scientific_protocol='reports/protocol.json',
        scientific_protocol_sha256=workflow.sha256(tmp_path/'reports/protocol.json'),
        analysis_source_sha256=workflow.sha256(tmp_path/'scripts/assess_final_study.py'),
        human_readable_plan_sha256=workflow.sha256(tmp_path/'reports/final_analysis_plan.md'),
        final_seeds=list(range(60001,60501)))
    write_json(tmp_path/'reports/final_analysis_plan.json',plan)
    monkeypatch.setattr(workflow,'FROZEN_ANALYSIS_PLAN_SHA256',
                        workflow.sha256(tmp_path/'reports/final_analysis_plan.json'))
    return tmp_path


def test_actual_frozen_science_and_plan_pass_read_only_preflight():
    plan, freeze, _ = workflow.validate_freezes(ROOT)
    assert len(plan['final_seeds']) == 500
    assert freeze['scientific_source_hash'] == '0f599867fd34f2aac11b29c3bddca4689045ed2ff114d964636c49ee936ef6d3'


@pytest.mark.parametrize('name', ['src/scientific.py','scripts/assess_final_study.py',
                                  'reports/final_analysis_plan.md','configs/full_main.json'])
def test_changed_source_plan_or_economics_prevent_continuation(frozen_root, name):
    workflow.validate_freezes(frozen_root)
    path = frozen_root/name
    if path.suffix == '.json':write_json(path, {'label':'changed'})
    else:path.write_text(path.read_text()+'changed\n')
    with pytest.raises(ValueError):workflow.validate_freezes(frozen_root)


def test_primary_comparator_cannot_change_while_other_freeze_fields_match(frozen_root):
    workflow.validate_freezes(frozen_root)
    path=frozen_root/'reports/final_analysis_plan.json'
    plan=json.loads(path.read_text());plan['primary_reference']='Catoni'
    write_json(path,plan)
    with pytest.raises(ValueError,match='Machine-readable final analysis'):
        workflow.validate_freezes(frozen_root)


@pytest.mark.parametrize('changes', [dict(requested_seeds=[50001]),
    dict(all_complete=False),dict(arithmetic_replay_complete=False),dict(stage='main')])
def test_completion_metadata_must_cover_exact_stage(tmp_path, changes):
    seeds = list(range(50001,50101));completion(tmp_path,seeds,**changes)
    with pytest.raises(ValueError):workflow.require_stage_completion(tmp_path,'pilot',seeds)


def test_live_handle_is_observed_until_it_ends_without_restarting(tmp_path, monkeypatch):
    seeds = list(range(50001,50101));completion(tmp_path,seeds)
    signature = ('Fri','Oct','16','22:56:50','2026','python run_full_study.py pilot --count 100')
    identities = iter([signature,signature,None]);updates=[];pauses=[]
    def forbidden(*args,**kwargs):raise AssertionError('Observer must not start a process')
    monkeypatch.setattr(workflow.subprocess,'Popen',forbidden)
    workflow.wait_for_pilot(123,tmp_path,seeds,lambda *a,**kw:updates.append((a,kw)),
                            identify=lambda _:next(identities),pause=pauses.append)
    assert len(updates)==1 and pauses==[30]


def test_missing_handle_without_completed_pilot_is_not_success(tmp_path):
    with pytest.raises(RuntimeError,match='without a complete'):
        workflow.wait_for_pilot(123,tmp_path,[50001],lambda *a,**kw:None,
                                identify=lambda _:None,pause=lambda _:None)


@pytest.mark.parametrize('alive',[True,False])
def test_failed_ps_observation_checks_actual_handle_before_declaring_absence(monkeypatch,alive):
    monkeypatch.setattr(workflow.subprocess,'run',lambda *a,**kw:
                        subprocess.CompletedProcess(a,1,stdout='',stderr=''))
    def check_handle(*args):
        if not alive:raise ProcessLookupError()
    monkeypatch.setattr(workflow.os,'kill',check_handle)
    if alive:
        with pytest.raises(workflow.ObservationUnavailable):workflow.process_identity(123)
    else:
        assert workflow.process_identity(123) is None


def test_transient_observation_retries_same_handle_without_process_restart(tmp_path,monkeypatch):
    seeds=list(range(50001,50101));completion(tmp_path,seeds)
    signature=('Fri','Oct','16','22:56:50','2026','python run_full_study.py pilot')
    observations=iter([signature,workflow.ObservationUnavailable('transient'),signature,None])
    updates=[];pauses=[]
    def identify(pid):
        assert pid==123
        value=next(observations)
        if isinstance(value,Exception):raise value
        return value
    def forbidden(*args,**kwargs):raise AssertionError('Observation retry must not start a process')
    monkeypatch.setattr(workflow.subprocess,'Popen',forbidden)
    workflow.wait_for_pilot(123,tmp_path,seeds,lambda phase,**kw:updates.append(phase),
                            identify=identify,pause=pauses.append)
    assert updates==['waiting_for_pilot_observation_retry','waiting_for_pilot']
    assert pauses==[30,30]


def test_reused_pid_is_not_followed_as_the_original_process(tmp_path):
    original = ('Fri','Oct','16','22:56:50','2026','python run_full_study.py pilot')
    replacement = ('Sat','Oct','17','01:00:00','2026','python unrelated.py')
    identities=iter([original,replacement])
    with pytest.raises(RuntimeError,match='without a complete'):
        workflow.wait_for_pilot(123,tmp_path,[50001],lambda *a,**kw:None,
                                identify=lambda _:next(identities),pause=lambda _:None)


def test_completion_file_alone_cannot_publish_a_verified_snapshot(frozen_root):
    _,freeze,protocol=workflow.validate_freezes(frozen_root)
    output=frozen_root/'outputs/park_revive_full_v3/pilot'
    completion(output,list(range(50001,50101)))
    with pytest.raises(FileNotFoundError):
        workflow.verified_seal(frozen_root,'pilot',freeze,protocol)
    assert not (frozen_root/'reports/full_v3_snapshots/pilot_100').exists()


def test_assessments_are_reused_exactly_and_never_overwritten(tmp_path):
    path=tmp_path/'assessment.json';workflow.write_immutable(path,{'result':-1})
    before=path.read_bytes();workflow.write_immutable(path,{'result':-1})
    with pytest.raises(ValueError,match='Refusing to overwrite'):
        workflow.write_immutable(path,{'result':1})
    assert path.read_bytes()==before


def test_actual_process_lock_excludes_another_controller(tmp_path):
    lock=tmp_path/'controller.lock';marker=tmp_path/'entered'
    code=('import sys; from pathlib import Path; '
          f'sys.path.insert(0,{str(ROOT/"scripts")!r}); '
          'from continue_full_study import exclusive_controller;\n'
          'with exclusive_controller(Path(sys.argv[1])):\n'
          ' Path(sys.argv[2]).write_text("entered")\n')
    with workflow.exclusive_controller(lock):
        result=subprocess.run([sys.executable,'-c',code,str(lock),str(marker)],
                              capture_output=True,text=True,timeout=10)
        assert result.returncode!=0 and not marker.exists()
        assert 'holds the process lock' in result.stderr
    result=subprocess.run([sys.executable,'-c',code,str(lock),str(marker)],
                          capture_output=True,text=True,timeout=10)
    assert result.returncode==0 and marker.read_text()=='entered'
