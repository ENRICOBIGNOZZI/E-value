"""Synthetic reporting fixtures only; no financial markets or new replications."""
import copy
import csv
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import build_final_manuscript_results as packet
from assess_final_study import assess
from seal_full_snapshot import canonical_hash, sha256


def save(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')


def write_csv(path, rows, fields=None):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    """500 identifiers exercise exact sample gates, not a generated market DGP."""
    plan = packet.read_json(ROOT/'reports/final_analysis_plan.json')
    freeze = packet.read_json(ROOT/'reports/full_v3_results/protocol_frozen.json')
    snapshot = tmp_path/'synthetic-final'; snapshot.mkdir()
    output = tmp_path/'synthetic-raw'; output.mkdir()
    rows = []
    for j, seed in enumerate(plan['final_seeds']):
        for method in plan['methods']:
            value = .04 + j*1e-6 - (.01 if method == 'Tail' else 0)
            rows.append(dict(seed=seed, method=method, annual_scaled_utility=value,
                             final_equity=1.1, inactive_fraction=.2, moves=1))
    write_csv(snapshot/'metrics_by_seed.csv', rows)
    write_csv(snapshot/'decisions.csv', [dict(seed=60001,method='Tail',lifecycle='ENTRY',executed='False')])
    write_csv(snapshot/'deployments.csv', [], ['seed','method','conditional_gain','actual_entry_cost'])
    rates = [dict(method=method,lifecycle='ALL',event_kind='ALL',followup_years=h,
                  eligible_events=0,criterion_within=0,selected_within=0)
             for method in packet.SEARCH for h in (1,3,5)]
    write_csv(snapshot/'opportunity_rates.csv', rates)
    for name in packet.REQUIRED - {'metrics_by_seed.csv','decisions.csv','deployments.csv','opportunity_rates.csv'}:
        (snapshot/name).write_text('synthetic immutable reporting fixture\n')
    records = [dict(seed=seed,input_digest=f'synthetic-{seed}',checks=1,ghost_pairs_checked=0)
               for seed in plan['final_seeds']]
    seal = dict(complete=True,kind='final',stage='main',seeds=plan['final_seeds'],frozen_pool_size=500,
                source_hash=freeze['scientific_source_hash'],config_hash=canonical_hash(freeze['final_config']),
                protocol_freeze_sha256=plan['scientific_protocol_sha256'],
                input_digests={str(row['seed']):row['input_digest'] for row in records},
                scalar_replay_checks=500,ghost_pairs_checked=0,
                files_sha256={p.name:sha256(p) for p in snapshot.iterdir()})
    save(snapshot/'snapshot_seal.json',seal)
    numeric_path, event_path, assessment_path = [tmp_path/name for name in ('numeric.json','events.json','assessment.json')]
    common = dict(complete=True,kind='final',seeds=plan['final_seeds'],
                  snapshot_seal_sha256=sha256(snapshot/'snapshot_seal.json'))
    numeric = dict(common,scalar_reporting_checks=1,all_sealed_report_file_hashes_match=True,
                   audit_source_sha256=sha256(ROOT/'scripts/audit_full_snapshot.py'))
    report = dict(common,audit_source_sha256=sha256(ROOT/'scripts/audit_full_event_snapshot.py'))
    event = dict(common,reporting_audit=report,
                 audit_source_sha256=sha256(ROOT/'scripts/audit_full_event_adjudication.py'),
                 reporting_auditor_source_sha256=report['audit_source_sha256'])
    save(numeric_path,numeric); save(event_path,event)
    save(assessment_path,assess(snapshot,ROOT/'reports/final_analysis_plan.json'))
    calls = []

    def raw_validation(path, seeds, source, config, verifier):
        assert path == output and seeds == plan['final_seeds']
        assert source == freeze['scientific_source_hash'] and config == freeze['final_config']
        assert verifier == ROOT/'scripts/verify_full_strategy.py'
        calls.append(list(seeds))
        return copy.deepcopy(records)

    monkeypatch.setattr(packet,'validate_snapshot',raw_validation)
    return dict(snapshot=snapshot,output=output,numeric_path=numeric_path,event_path=event_path,
                assessment_path=assessment_path,destination=tmp_path/'packet',calls=calls,
                records=records,plan=plan,paper_before=sha256(ROOT/'paper/generated_full_results.tex'))


def arguments(e):
    return [ROOT,e['snapshot'],e['output'],e['numeric_path'],e['event_path'],e['assessment_path']]


def test_packet_preserves_negative_primary_all_contrasts_and_empty_groups(evidence):
    e=evidence
    result=packet.build(*arguments(e),e['destination'])
    text=(e['destination']/'generated_final_results.tex').read_text()
    assert result['markets']==500 and len(e['calls'])==2
    assert 'Primary & All Signals & -0.01000' in text
    assert all(f'Secondary & {name}' in text for name in ('Greedy','HAC','Catoni','Oracle'))
    assert 'Catoni & 0 & -- & -- & --' in text
    assert 'Tail & 1 & 0 & 0 & 0 & 1 & 0' in text  # terminal choice, zero executed
    assert '500 declared fresh markets' in text and '499 degrees of freedom' in text
    assert 'completed full-strategy pilot' not in text
    assert 'causally isolate' in text and 'not lifetime trade value' in text
    for name,expected in result['outputs_sha256'].items():assert sha256(e['destination']/name)==expected
    assert sha256(ROOT/'paper/generated_full_results.tex')==e['paper_before']


@pytest.mark.parametrize('change',['pilot','subset','wrong_order','incomplete','wrong_config'])
def test_wrong_stage_membership_or_freeze_never_publishes(evidence,change):
    e=evidence;path=e['snapshot']/'snapshot_seal.json';seal=packet.read_json(path)
    if change=='pilot':seal.update(kind='complete_pilot',stage='pilot')
    elif change=='subset':seal['seeds']=seal['seeds'][:-1]
    elif change=='wrong_order':seal['seeds']=list(reversed(seal['seeds']))
    elif change=='incomplete':seal['complete']=False
    else:seal['config_hash']='wrong frozen config'
    save(path,seal)
    with pytest.raises(ValueError):packet.build(*arguments(e),e['destination'])
    assert not e['destination'].exists()


@pytest.mark.parametrize('which,field,value',[
    ('numeric_path','complete',False),('numeric_path','audit_source_sha256','stale'),
    ('numeric_path','scalar_reporting_checks',0),('event_path','complete',False),
    ('event_path','snapshot_seal_sha256','another seal'),
    ('event_path','reporting_auditor_source_sha256','stale'),
    ('event_path','seeds',[]),('assessment_path','kind','pilot_diagnostic'),
    ('assessment_path','analysis_plan_sha256','changed')])
def test_missing_or_stale_final_evidence_never_publishes(evidence,which,field,value):
    e=evidence;path=e[which];record=packet.read_json(path);record[field]=value;save(path,record)
    with pytest.raises(ValueError):packet.build(*arguments(e),e['destination'])
    assert not e['destination'].exists()


def test_changed_sealed_data_is_rejected(evidence):
    e=evidence;(e['snapshot']/'metrics_by_seed.csv').write_text('changed\n')
    with pytest.raises(ValueError,match='Changed sealed'):
        packet.build(*arguments(e),e['destination'])
    assert not e['destination'].exists()


def test_complete_looking_reports_without_actual_raw_replay_are_rejected(evidence,monkeypatch):
    from seal_full_snapshot import validate_snapshot
    e=evidence;monkeypatch.setattr(packet,'validate_snapshot',validate_snapshot)
    with pytest.raises(FileNotFoundError):packet.build(*arguments(e),e['destination'])
    assert not e['destination'].exists()


def test_raw_digest_drift_and_mid_preparation_changes_are_rejected(evidence,monkeypatch):
    e=evidence;original=packet.validate_snapshot
    def drift(*args):
        rows=original(*args)
        if len(e['calls'])==2:rows[0]['input_digest']='changed after first pass'
        return rows
    monkeypatch.setattr(packet,'validate_snapshot',drift)
    with pytest.raises(ValueError,match='raw replay differs'):
        packet.build(*arguments(e),e['destination'])
    assert not e['destination'].exists()
    assert not list(e['destination'].parent.glob('.final-packet-*'))


def test_existing_destination_is_never_overwritten(evidence):
    e=evidence;e['destination'].mkdir();sentinel=e['destination']/'keep';sentinel.write_text('retain')
    with pytest.raises(ValueError,match='overwrite'):packet.build(*arguments(e),e['destination'])
    assert sentinel.read_text()=='retain' and not e['calls']


@pytest.mark.parametrize('parent',['snapshot','output'])
def test_outputs_cannot_be_written_inside_scientific_evidence(evidence,parent):
    e=evidence
    with pytest.raises(ValueError,match='inside scientific'):
        packet.build(*arguments(e),e[parent]/'manuscript-packet')


def test_duplicate_followup_cohort_is_not_silently_collapsed(evidence):
    bundle=packet.validate_bundle(*arguments(evidence))
    bundle['rates'].append(copy.deepcopy(bundle['rates'][0]))
    with pytest.raises(ValueError,match='duplicated'):packet.render(bundle)


def test_nested_event_report_must_be_current(evidence):
    e=evidence;record=packet.read_json(e['event_path'])
    record['reporting_audit']['complete']=False;save(e['event_path'],record)
    with pytest.raises(ValueError,match='audit_full_event_snapshot'):
        packet.build(*arguments(e),e['destination'])
    assert not e['destination'].exists()


def test_corrupted_copied_figure_is_rejected_without_publishing(evidence,monkeypatch):
    e=evidence
    def corrupt(source,destination):Path(destination).write_text('changed during copy')
    monkeypatch.setattr(packet.shutil,'copyfile',corrupt)
    with pytest.raises(ValueError,match='Copied final figure'):
        packet.build(*arguments(e),e['destination'])
    assert not e['destination'].exists()
    assert not list(e['destination'].parent.glob('.final-packet-*'))
