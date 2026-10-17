"""Independent event-report controls; synthetic fixtures are not market evidence."""
import csv
import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import audit_full_event_snapshot as event_audit
from audit_full_event_snapshot import (ALL_METHODS, FOLLOWUP, KINDS, LIFECYCLES, METHODS,
    audit, canonical_hash, input_digest, sha256)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')


def write_csv(path, rows, columns=None):
    import gzip
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'wt', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns or list(rows[0]))
        writer.writeheader();writer.writerows(rows)


def read_csv(path):
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def reseal(snapshot):
    path = snapshot/'snapshot_seal.json'
    seal = json.loads(path.read_text())
    seal['files_sha256'] = {str(p.relative_to(snapshot)): sha256(p)
        for p in sorted(snapshot.rglob('*')) if p.is_file() and p != path}
    write_json(path, seal)


def rebind_fixture(snapshot, output):
    """Bind deliberately malformed fixture records to exercise semantic gates."""
    path = snapshot/'snapshot_seal.json'
    seal = json.loads(path.read_text());seed = seal['seeds'][0]
    digest = input_digest(output/f'seed_{seed}')
    records = json.loads((snapshot/'arithmetic_verification.json').read_text())
    records[0]['input_digest'] = digest
    write_json(snapshot/'arithmetic_verification.json', records)
    seal['input_digests'][str(seed)] = digest
    write_json(path, seal);reseal(snapshot)


@pytest.fixture
def evidence(tmp_path):
    output = tmp_path/'pilot';directory = output/'seed_50001';directory.mkdir(parents=True)
    snapshot = tmp_path/'snapshot';(snapshot/'details').mkdir(parents=True)
    config = dict(block=10, years=5, economic_tolerance=1e-8, label='software fixture')
    source = {'src/frozen.py': 'fixture fingerprint'}
    fingerprint = canonical_hash(source)
    registry = []
    for method, start in [('Tail',10),('Greedy',30),('HAC',40),('Catoni',10)]:
        registry.append(dict(seed=50001,method=method,comparison_id=method+':one',
            start=start,move='forward',lifecycle='ENTRY',added=0,removed=-1,
            reference_support=[],candidate_support=[0],
            stable_events=0 if method=='Catoni' else 1,unstable_runs=0))
    events=[];decisions=[]
    for method, onset, chosen in [('Tail',20,20),('Greedy',40,50),('HAC',50,50)]:
        meta=next(r for r in registry if r['method']==method)
        events.append(dict(**{k:v for k,v in meta.items() if k not in ('stable_events','unstable_runs')},
            event_index=1,onset_day=onset,event_kind='inception_positive',
            confirmation_day=onset+10,criterion_day=onset,selected_day=chosen,
            termination_day=chosen,termination_reason='selected',criterion_detected=True,
            selected=True,criterion_delay_days=0,selection_delay_days=chosen-onset))
        decisions.append(dict(seed=50001,method=method,day=chosen,comparison_id=method+':one',
            support_before=[],support_after=[0],move='forward',lifecycle='ENTRY',
            added=0,removed=-1,mean_y=.02,log_e=4.,true_block_mean=.02,
            last_pre_return_mean=.02,executed=chosen<50))
    deployment=dict(**decisions[0],deployment_day=20,conditional_gain=.01,
        new_conditional_utility=.02,old_conditional_utility=.01,actual_entry_cost=.001)
    originals={'opportunity_registry':registry,'economic_opportunities':events,
               'decisions':decisions,'deployments':[deployment]}
    for name, rows in originals.items():
        write_json(directory/f'{name}.json',rows)
        dest=snapshot/'details'/f'{name}.csv.gz' if name in ('economic_opportunities','opportunity_registry') else snapshot/f'{name}.csv'
        write_csv(dest,rows)
    write_json(directory/'config_frozen.json',config)
    write_json(directory/'source_manifest.json',source)
    write_json(directory/'status.json',dict(seed=50001,complete=True,completed_blocks=4,
        total_blocks=4,source_hash=fingerprint,stable_opportunities=3,unstable_runs=0))
    metrics=[dict(seed=50001,method=method,moves=int(method in ('Greedy','HAC','Tail')),
        executed_moves=int(method=='Tail'),economic_precision=1. if method in ('Greedy','HAC','Tail') else '',
        deployment_positive_fraction=1. if method=='Tail' else '') for method in ALL_METHODS]
    write_csv(directory/'metrics_by_seed.csv',metrics)
    rates=[];seed_counts=[]
    # Hand-specified risk set: prompt Tail response, a Greedy terminal choice,
    # and an HAC onset with no calendar follow-up. No response is excluded for
    # being too fast, and a terminal choice never becomes an executed trade.
    eligible_windows={('Tail',1),('Tail',3),('Greedy',1)}
    for method in METHODS:
        for lifecycle in LIFECYCLES:
            for kind in KINDS:
                for years in FOLLOWUP:
                    stable=int(method!='Catoni' and lifecycle in ('ALL','ENTRY') and kind in ('ALL','inception_positive'))
                    n=int(stable and (method,years) in eligible_windows)
                    key=dict(method=method,lifecycle=lifecycle,event_kind=kind,followup_years=years)
                    rates.append(dict(**key,stable_events=stable,eligible_events=n,selected_within=n,
                        criterion_within=n,selection_fraction=1. if n else '',
                        criterion_fraction=1. if n else '',contributing_seeds=n))
                    if n:seed_counts.append(dict(**key,seed=50001,eligible_events=1,selected_within=1,criterion_within=1))
    write_csv(snapshot/'opportunity_rates.csv',rates)
    write_csv(snapshot/'opportunity_seed_counts.csv',seed_counts)
    write_json(snapshot/'config_frozen.json',config)
    digest=input_digest(directory)
    write_json(snapshot/'arithmetic_verification.json',[dict(seed=50001,complete=True,
        checks=10,input_digest=digest,scientific_source_hash=fingerprint,
        config_hash=canonical_hash(config),verifier_sha256='fixture verifier')])
    write_json(snapshot/'snapshot_seal.json',dict(complete=True,kind='interim_pilot',
        seeds=[50001],frozen_pool_size=100,source_hash=fingerprint,
        config_hash=canonical_hash(config),input_digests={'50001':digest},
        reporting_source_sha256={'verify_full_strategy.py':'fixture verifier'},files_sha256={}))
    reseal(snapshot)
    return snapshot,output


def test_fast_responses_terminal_choices_and_empty_cohorts(evidence):
    result=audit(*evidence)
    assert result['complete']
    assert result['counts']['economic_opportunities_rows']==3
    assert result['counts']['decisions_rows']==3
    assert result['counts']['deployments_rows']==1
    assert result['counts']['opportunity_rates_rows']==180
    assert result['counts']['opportunity_seed_counts_rows']==12
    assert result['deployment_summary']['Tail']['positive_gain_fraction']==1.
    assert result['deployment_summary']['Greedy']['executed']==0
    assert result['deployment_summary']['Greedy']['positive_gain_fraction'] is None


@pytest.mark.parametrize('change', ['eligible_events','contributing_seeds','selection_fraction',
    'empty_fraction','missing_cohort','duplicate_cohort','duplicate_decision','missing_deployment'])
def test_wrong_resealed_reports_are_still_rejected(evidence,change):
    snapshot,output=evidence
    path=snapshot/('decisions.csv' if change=='duplicate_decision' else
                   'deployments.csv' if change=='missing_deployment' else 'opportunity_rates.csv')
    columns,rows=read_csv(path)
    if change in ('eligible_events','contributing_seeds'):
        row=next(r for r in rows if int(r['eligible_events'])>0);row[change]=str(int(row[change])+1)
    elif change=='selection_fraction':
        next(r for r in rows if r['selection_fraction']=='1.0')['selection_fraction']='0.5'
    elif change=='empty_fraction':
        next(r for r in rows if r['selection_fraction']=='')['selection_fraction']='0.0'
    elif change in ('missing_cohort','missing_deployment'):rows.pop()
    else:rows.append(dict(rows[0]))
    write_csv(path,rows,columns);reseal(snapshot)
    with pytest.raises((ArithmeticError,ValueError)):
        audit(snapshot,output)


def test_changed_source_bytes_require_a_current_replay(evidence):
    snapshot,output=evidence
    path=output/'seed_50001'/'deployments.json'
    path.write_text(path.read_text()+'\n')
    with pytest.raises(ValueError,match='Stale or missing'):
        audit(snapshot,output)


@pytest.mark.parametrize('change,reason',[('bad_delay','Invalid event delay'),
    ('bad_confirmation','Invalid stable-event calendar'),('terminal_execution','Invalid decision calendar'),
    ('duplicate_registry','Duplicate comparison registry'),('gain_identity','Inconsistent retained deployment gain')])
def test_inconsistent_bound_source_metadata_is_rejected(evidence,change,reason):
    snapshot,output=evidence
    name='deployments' if change=='gain_identity' else 'decisions' if change=='terminal_execution' else 'opportunity_registry' if change=='duplicate_registry' else 'economic_opportunities'
    path=output/'seed_50001'/f'{name}.json';rows=json.loads(path.read_text())
    if change=='bad_delay':rows[0]['selection_delay_days']=10
    elif change=='bad_confirmation':rows[0]['confirmation_day']=40
    elif change=='terminal_execution':rows[1]['executed']=True
    elif change=='gain_identity':rows[0]['conditional_gain']+=.001
    else:rows.append(dict(rows[0]))
    write_json(path,rows);rebind_fixture(snapshot,output)
    with pytest.raises(ValueError,match=reason):audit(snapshot,output)


def test_checkpoint_cache_compaction_does_not_invalidate_preserved_evidence(evidence):
    snapshot,output=evidence
    write_json(output/'seed_50001'/'checkpoint_cache_discarded.json',{'fixture':True})
    assert audit(snapshot,output)['complete']


def test_partial_final_cannot_be_labeled_complete(evidence):
    snapshot,output=evidence
    path=snapshot/'snapshot_seal.json';seal=json.loads(path.read_text())
    seal.update(kind='final',frozen_pool_size=500);write_json(path,seal)
    with pytest.raises(ValueError,match='Partial final'):audit(snapshot,output)


def test_changed_sealed_artifact_is_rejected_before_reaggregation(evidence):
    snapshot,output=evidence
    path=snapshot/'opportunity_rates.csv';path.write_text(path.read_text()+'\n')
    with pytest.raises(ValueError,match='Changed sealed artifact'):audit(snapshot,output)


def test_duplicate_source_metric_is_not_silently_overwritten(evidence):
    snapshot,output=evidence
    path=output/'seed_50001'/'metrics_by_seed.csv';columns,rows=read_csv(path)
    rows.append(dict(rows[0]));write_csv(path,rows,columns);rebind_fixture(snapshot,output)
    with pytest.raises(ValueError,match='Invalid metric membership'):audit(snapshot,output)


def test_source_addition_during_audit_invalidates_success(evidence,monkeypatch):
    snapshot,output=evidence
    original=event_audit.read_rows
    def mutate_after_read(path):
        yield from original(path)
        if path.name=='opportunity_rates.csv':
            (output/'seed_50001'/'late.dat').write_text('changed input membership')
    monkeypatch.setattr(event_audit,'read_rows',mutate_after_read)
    with pytest.raises(ValueError,match='Source data changed during event audit'):audit(snapshot,output)


@pytest.mark.parametrize('destination', ['snapshot','output'])
def test_cli_cannot_write_its_report_into_immutable_inputs(evidence,destination):
    snapshot,output=evidence
    report=(snapshot if destination=='snapshot' else output)/'new_audit.json'
    result=subprocess.run([sys.executable,event_audit.__file__,'--snapshot',str(snapshot),
        '--output',str(output),'--report',str(report)],capture_output=True,text=True)
    assert result.returncode==2 and 'must lie outside' in result.stderr
    assert not report.exists()
