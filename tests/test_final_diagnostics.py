"""Synthetic graphics/reporting controls, not independent financial markets."""
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import build_final_diagnostics as diagnostics
import build_final_manuscript_results as packet
from test_final_manuscript_packet import evidence


def inputs(seeds=(60001,60002,60003), block=2, years=8, n_signals=4):
    cfg = dict(block=block, years=years, n_signals=n_signals)
    metrics = []
    for j, seed in enumerate(seeds):
        for i, method in enumerate(diagnostics.METHODS):
            row = dict(seed=seed, method=method)
            row.update({key:.01*(j+1)+i*.001 for key in diagnostics.METRICS})
            row['annual_scaled_utility'] -= .03 if method == 'Tail' else 0
            if method == 'Catoni':
                row['sharpe'] = row['sharpe_hac'] = np.nan
            metrics.append(row)
    deployments = pd.DataFrame([
        dict(seed=seeds[0],method='Tail',day=2*block,conditional_gain=value)
        for value in (-2e-8,-1e-8,0,1e-8,2e-8)
    ])
    events = []
    last = years*block
    for method in diagnostics.SEARCH:
        for onset, criterion, selected, end, reason in [
            (2*block,2*block,2*block,2*block,'selected'),
            (2*block,2*block,-1,3*block,'competing_move'),
            (2*block,-1,-1,4*block,'sign_reversal'),
            (last-block,-1,-1,last,'administrative_end'),
        ]:
            events.append(dict(seed=seeds[0], method=method, onset_day=onset,
                criterion_day=criterion, selected_day=selected, termination_day=end, termination_reason=reason))
    rates = []
    for method in diagnostics.SEARCH:
        for horizon in (1,3,5):
            eligible = sum(row['method']==method and row['onset_day']+horizon*block<=last for row in events)
            rates.append(dict(method=method, lifecycle='ALL', event_kind='ALL',
                              followup_years=horizon,eligible_events=eligible,
                              selected_within=1,criterion_within=2))
    daily = []
    for method in diagnostics.METHODS:
        for day in range(block, last):
            support = [] if day < 2*block else [0] if day < 3*block else [] if day < 4*block else [1]
            daily.append(dict(seed=seeds[0],method=method,day=day,equity=1+.001*(day-block),
                              n_active=len(support),support=np.array(support,dtype=int)))
    runtime = pd.DataFrame([dict(seed=seed,year=year,seconds=10+year)
                            for seed in seeds for year in range(1,years)])
    return [pd.DataFrame(metrics),deployments,pd.DataFrame(events),pd.DataFrame(rates),
            pd.DataFrame(daily),runtime,list(seeds),cfg]


def test_paired_denominators_nan_sharpe_and_signed_deployment_tolerance():
    result = diagnostics.prepare(*inputs())
    assert len(result['paired']) == 3*5
    assert (result['paired'].difference < 0).all()
    row = result['summary'].query("method=='Catoni' and metric=='sharpe'").iloc[0]
    assert row.defined == 0 and row.markets == 3 and np.isnan(row['mean'])
    row = result['deployment_counts'].set_index('method').loc['Tail']
    assert (row.executed,row.positive,row.negative,row.near_zero)==(5,1,1,3)
    assert result['deployment_counts'].set_index('method').loc['Catoni','executed'] == 0


def test_followup_retains_competing_closures_and_censoring_denominators():
    result = diagnostics.prepare(*inputs())
    rows = result['followup'].query("method=='Tail'").set_index('followup_years')
    assert rows.loc[1,'eligible_events']==4
    assert rows.loc[1,'administrative_end']==1
    assert rows.loc[1,'still_unselected']==1  # sign reversal occurs after the one-year horizon
    assert rows.loc[3,'eligible_events']==3
    assert rows.loc[3,'competing_move']==1 and rows.loc[3,'sign_reversal']==1
    assert rows.loc[5,'selected_within']==1


def test_membership_separates_never_selected_from_removed_and_excludes_terminal():
    result = diagnostics.prepare(*inputs())
    states = result['membership'].query("method=='Tail'").pivot(index='signal',columns='day',values='state')
    assert states.loc[0,2]==0 and states.loc[0,4]==1 and states.loc[0,6]==2
    assert (states.loc[2]==0).all() and max(states.columns)==14
    assert len(result['runtime_totals'])==3
    assert np.all(result['runtime_totals'].seconds==sum(10+year for year in range(1,8)))


@pytest.mark.parametrize('change',[
    'duplicate_metric','missing_metric','infinite_sharpe','undefined_utility',
    'terminal_deployment','unknown_event','wrong_followup','duplicate_runtime',
    'negative_runtime','missing_day','unknown_signal'
])
def test_invalid_diagnostic_inputs_fail(change):
    args=inputs()
    if change=='duplicate_metric':args[0]=pd.concat([args[0],args[0].iloc[:1]])
    elif change=='missing_metric':args[0]=args[0].drop(columns='turnover')
    elif change=='infinite_sharpe':args[0].loc[0,'sharpe']=np.inf
    elif change=='undefined_utility':args[0].loc[0,'annual_scaled_utility']=np.nan
    elif change=='terminal_deployment':args[1].loc[0,'day']=16
    elif change=='unknown_event':args[2].loc[0,'termination_reason']='ignored'
    elif change=='wrong_followup':args[3].loc[0,'eligible_events']+=1
    elif change=='duplicate_runtime':args[5]=pd.concat([args[5],args[5].iloc[:1]])
    elif change=='negative_runtime':args[5].loc[0,'seconds']=-1
    elif change=='missing_day':args[4]=args[4].iloc[1:]
    else:args[4].at[2,'support']=[99]
    with pytest.raises(ValueError):diagnostics.prepare(*args)


def test_all_graphics_and_numeric_tables_render_with_explicit_fixture_label(tmp_path):
    data=diagnostics.prepare(*inputs())
    path=tmp_path/'graphics'
    names=diagnostics.render(data,path,'SOFTWARE FIXTURE — three identifiers, no financial evidence')
    assert names==[name for name,_ in diagnostics.FIGURES]
    assert len(list(path.glob('*.png')))==8 and len(list(path.glob('*.csv')))==10
    assert (path/'diagnostics.pdf').read_bytes().startswith(b'%PDF')
    summary=pd.read_csv(path/'metric_summary.csv')
    assert summary.query("method=='Catoni' and metric=='sharpe'").defined.iloc[0]==0
    assert len(pd.read_csv(path/'paired_utility.csv'))==15


def test_no_events_or_deployments_remain_empty_with_zero_eligible_denominators():
    args=inputs();args[1]=args[1].iloc[:0];args[2]=args[2].iloc[:0]
    args[3][['eligible_events','selected_within','criterion_within']]=0
    data=diagnostics.prepare(*args)
    assert not data['followup'].eligible_events.any()
    assert not data['deployment_counts'].executed.any()
    assert len(data['deployments'])==0


def enrich_final_fixture(e):
    """Fictional 500 identifiers; the inherited raw gate is stubbed explicitly."""
    snapshot, output=e['snapshot'],e['output']
    config=packet.read_json(ROOT/'reports/full_v3_results/protocol_frozen.json')['final_config']
    (snapshot/'config_frozen.json').write_text(json.dumps(config))
    metrics=pd.read_csv(snapshot/'metrics_by_seed.csv')
    for key in diagnostics.METRICS:
        if key not in metrics:metrics[key]=np.nan if 'sharpe' in key else .001
    metrics.to_csv(snapshot/'metrics_by_seed.csv',index=False)
    events=pd.DataFrame([dict(seed=60001,method=method,onset_day=504,criterion_day=-1,
        selected_day=-1,termination_day=3780,termination_reason='administrative_end')
        for method in diagnostics.SEARCH])
    (snapshot/'details').mkdir();events.to_csv(snapshot/'details/economic_opportunities.csv.gz',index=False)
    rates=pd.read_csv(snapshot/'opportunity_rates.csv');rates.eligible_events=1
    rates.to_csv(snapshot/'opportunity_rates.csv',index=False)
    for seed in e['plan']['final_seeds']:
        directory=output/f'seed_{seed}';directory.mkdir()
        pd.DataFrame(dict(seed=seed,year=range(1,15),seconds=1.)).to_csv(directory/'runtime.csv',index=False)
    daily=pd.DataFrame([dict(seed=60001,method=method,day=day,equity=1.,n_active=0,
                            support=np.array([],dtype=int))
                       for method in diagnostics.METHODS for day in range(252,3780)])
    daily.to_parquet(output/'seed_60001/daily_ledger.parquet')
    seal=packet.read_json(snapshot/'snapshot_seal.json')
    seal['files_sha256']={str(p.relative_to(snapshot)):packet.sha256(p)
                         for p in snapshot.rglob('*') if p.is_file() and p.name!='snapshot_seal.json'}
    (snapshot/'snapshot_seal.json').write_text(json.dumps(seal))
    new_hash=packet.sha256(snapshot/'snapshot_seal.json')
    for key in ('numeric_path','event_path'):
        record=packet.read_json(e[key]);record['snapshot_seal_sha256']=new_hash
        if key=='event_path':record['reporting_audit']['snapshot_seal_sha256']=new_hash
        e[key].write_text(json.dumps(record))
    e['assessment_path'].write_text(json.dumps(packet.assess(snapshot,ROOT/'reports/final_analysis_plan.json')))
    return [ROOT,snapshot,output,e['numeric_path'],e['event_path'],e['assessment_path']]


def test_complete_fixture_uses_real_render_and_two_evidence_validations(evidence):
    args=enrich_final_fixture(evidence);destination=evidence['destination']
    record=diagnostics.build(*args,destination)
    assert record['markets']==500 and record['representative_seed']==60001
    assert len(record['figures'])==8 and len(evidence['calls'])==2
    assert all(packet.sha256(destination/name)==expected for name,expected in record['outputs_sha256'].items())
    assert packet.sha256(ROOT/'paper/generated_full_results.tex')==evidence['paper_before']


def test_incomplete_final_never_reaches_plotting(evidence,monkeypatch):
    e=evidence;seal=packet.read_json(e['snapshot']/'snapshot_seal.json');seal['complete']=False
    (e['snapshot']/'snapshot_seal.json').write_text(json.dumps(seal))
    def unexpected(*args):raise AssertionError('Incomplete evidence reached plotting')
    monkeypatch.setattr(diagnostics,'render',unexpected)
    with pytest.raises(ValueError,match='500 frozen'):
        diagnostics.build(ROOT,e['snapshot'],e['output'],e['numeric_path'],e['event_path'],
                          e['assessment_path'],e['destination'])
    assert not e['destination'].exists()


@pytest.mark.parametrize('location',['existing','raw','snapshot','paper'])
def test_destinations_cannot_overwrite_existing_or_protected_inputs(evidence,location):
    e=evidence
    destination = e['destination']
    if location=='existing':destination.mkdir()
    elif location=='raw':destination=e['output']/'new'
    elif location=='snapshot':destination=e['snapshot']/'new'
    else:destination=ROOT/'paper'/'forbidden'
    with pytest.raises(ValueError):
        diagnostics.build(ROOT,e['snapshot'],e['output'],e['numeric_path'],e['event_path'],
                          e['assessment_path'],destination)
    if location!='existing':assert not destination.exists()


def test_mid_plot_evidence_change_leaves_no_packet(evidence,monkeypatch):
    args=enrich_final_fixture(evidence)
    def change(data,destination,context):
        destination.mkdir()
        with (evidence['snapshot']/'metrics_by_seed.csv').open('a') as stream:stream.write('changed\n')
        return []
    monkeypatch.setattr(diagnostics,'render',change)
    with pytest.raises(ValueError,match='Changed sealed'):
        diagnostics.build(*args,evidence['destination'])
    assert not evidence['destination'].exists()
    assert not list(evidence['destination'].parent.glob('.final-diagnostics-*'))
