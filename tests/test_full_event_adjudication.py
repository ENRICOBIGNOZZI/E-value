"""Batch reconstruction controls; all fixture paths are synthetic software data."""
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_full_event_adjudication import METHODS, reconstruct, reconstruct_seed


def meta(method='Tail',start=0,cid=None):
    return dict(seed=50001,method=method,comparison_id=cid or method+':one',start=start,
        move='forward',lifecycle='ENTRY',added=0,removed=-1,reference_support=[],candidate_support=[0])


def reviews(values,eligible=(),selected=()):
    return [dict(day=10*(i+1),mean=value,eligible=i in eligible,selected=i in selected)
            for i,value in enumerate(values)]


def test_fast_selected_response_is_confirmed_after_closure():
    rows=reviews([.1],eligible=(0,),selected=(0,))
    events,unstable=reconstruct(meta(),rows,dict(day=10,reason='selected'),10,1e-8,
                                dict(day=20,mean=.2))
    assert unstable==0
    assert events==[dict(**meta(),event_index=1,onset_day=10,event_kind='inception_positive',
        confirmation_day=20,criterion_day=10,selected_day=10,termination_day=10,
        termination_reason='selected',criterion_detected=True,selected=True,
        criterion_delay_days=0,selection_delay_days=0)]


@pytest.mark.parametrize('values,ghost,starts,ends,unstable',[
    ([.1,-.1],None,[],[],1),
    ([.1,.2,-.1],None,[10],[30],0),
    ([.1,-.1,.2,.3,0.],None,[30],[50],1),
    ([.1,.1,0.,.1,.1],None,[10,40],[30,50],0),
    ([0.,1e-8,0.],None,[],[],0),
    ([.1],dict(day=20,mean=-.1),[],[],1),
    ([0.,.1],dict(day=30,mean=.2),[20],[20],0),
])
def test_maximal_runs_threshold_and_unstable_counts(values,ghost,starts,ends,unstable):
    rows=reviews(values)
    events,count=reconstruct(meta(),rows,dict(day=rows[-1]['day'],reason='administrative_end'),10,1e-8,ghost)
    assert count==unstable
    assert [e['onset_day'] for e in events]==starts
    assert [e['termination_day'] for e in events]==ends
    assert [e['event_index'] for e in events]==list(range(1,len(events)+1))
    assert all(e['event_kind']==('inception_positive' if e['onset_day']==10 else 'sign_change_positive') for e in events)


def test_criterion_before_positive_run_does_not_enter_its_delay():
    rows=reviews([-.1,.1],eligible=(0,1),selected=(1,))
    events,_=reconstruct(meta(),rows,dict(day=20,reason='selected'),10,1e-8,dict(day=30,mean=.1))
    assert events[0]['criterion_day']==events[0]['selected_day']==20
    assert events[0]['criterion_delay_days']==0


def test_selection_at_negative_block_is_not_a_response_to_old_positive_run():
    rows=reviews([.1,.1,-.1],eligible=(2,),selected=(2,))
    events,_=reconstruct(meta(),rows,dict(day=30,reason='selected'),10,1e-8)
    assert events[0]['termination_reason']=='sign_reversal'
    assert events[0]['selected'] is False and events[0]['selected_day']==-1


@pytest.mark.parametrize('change,reason',[
    ('missing_ghost','Missing or mistimed'),('mistimed_ghost','Missing or mistimed'),
    ('spurious_ghost','Unexpected ghost'),('nonfinite_ghost','Missing or mistimed'),
    ('missing_review','Annual observations'),('wrong_closure','Closure is not'),
    ('selected_ineligible','Invalid annual'),('nonfinite_mean','Invalid annual'),
    ('selected_before_last','Selection and episode closure'),('selected_label_without_choice','Selected closure')])
def test_invalid_pending_runs_and_calendars_are_rejected(change,reason):
    rows=reviews([.1]);closure=dict(day=10,reason='administrative_end');ghost=None
    if change=='mistimed_ghost':ghost=dict(day=30,mean=.1)
    elif change=='nonfinite_ghost':ghost=dict(day=20,mean=float('nan'))
    elif change=='spurious_ghost':rows=reviews([.1,.1]);closure['day']=20;ghost=dict(day=30,mean=.1)
    elif change=='missing_review':rows=reviews([.1,.1]);rows[1]['day']=30;closure['day']=30
    elif change=='wrong_closure':closure['day']=20
    elif change=='selected_ineligible':rows[0]['selected']=True
    elif change=='nonfinite_mean':rows[0]['mean']=float('nan')
    elif change=='selected_before_last':rows=reviews([.1,.1],eligible=(0,),selected=(0,));closure=dict(day=20,reason='selected')
    elif change=='selected_label_without_choice':closure['reason']='selected'
    with pytest.raises(ValueError,match=reason):reconstruct(meta(),rows,closure,10,1e-8,ghost)


def write_json(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n')


def event(metadata,onset,confirmation,termination,selected=False):
    return dict(**metadata,event_index=1,onset_day=onset,event_kind='inception_positive',
        confirmation_day=confirmation,criterion_day=onset if selected else -1,
        selected_day=onset if selected else -1,termination_day=termination,
        termination_reason='selected' if selected else 'administrative_end',
        criterion_detected=selected,selected=selected,criterion_delay_days=0 if selected else -1,
        selection_delay_days=0 if selected else -1)


@pytest.fixture
def archived_seed(tmp_path):
    """Five comparison episodes, with hand-specified labels, not a simulation."""
    cfg=dict(block=10,years=3,economic_tolerance=1e-8)
    write_json(tmp_path/'config_frozen.json',cfg)
    first={m:meta(m,10) for m in METHODS}
    second=meta('Tail',20,'Tail:two')
    registry=[dict(**x,stable_events=int(m in ('Greedy','Tail')),unstable_runs=int(m=='Catoni')) for m,x in first.items()]
    registry.append(dict(**second,stable_events=0,unstable_runs=0))
    write_json(tmp_path/'opportunity_registry.json',registry)
    write_json(tmp_path/'economic_opportunities.json',[
        event(first['Tail'],20,30,20,True),event(first['Greedy'],20,30,30)])
    for year in (1,2):
        folder=tmp_path/f'block_{year:02d}';folder.mkdir()
        rows=[];orders={}
        for method in METHODS:
            metadata=second if year==2 and method=='Tail' else first[method]
            value=2e-8 if method=='Greedy' or (year==1 and method in ('Tail','Catoni')) else 0.
            chosen=year==1 and method=='Tail'
            rows.append(dict(**metadata,day=(year+1)*10,true_block_mean=value,eligible=chosen,selected=chosen))
            orders[method]=[dict(comparison_id=metadata['comparison_id'],candidate=[0],reference=[])]
            np.savez_compressed(folder/f'scores_{method}.npz',true_mean=np.full((10,1),value))
        pd.DataFrame(rows).to_parquet(folder/'comparison_events.parquet',index=False)
        write_json(folder/'comparison_order.json',orders)
        closed=[dict(comparison_id=first['Tail']['comparison_id'],day=20,reason='selected')] if year==1 else [
            dict(comparison_id=(second if m=='Tail' else first[m])['comparison_id'],day=30,reason='administrative_end') for m in METHODS]
        write_json(folder/'closed_episodes.json',closed)
        order=[] if year==1 else [dict(comparison_id=first['Tail']['comparison_id'],candidate=[0],reference=[])]
        write_json(folder/'ghost_order.json',order)
        if year==2:np.savez_compressed(folder/'ghosts.npz',true_mean=np.full((10,1),2e-8))
    return tmp_path


def test_annual_archive_loader_reconstructs_hand_specified_labels(archived_seed):
    result=reconstruct_seed(archived_seed)
    assert result['counts']['comparisons_reconstructed']==5
    assert result['counts']['stable_events_reconstructed']==2
    assert result['counts']['unstable_runs_reconstructed']==1
    assert result['counts']['selected_events_confirmed_after_closure']==1
    assert result['counts']['ghost_mean_columns']==1


@pytest.mark.parametrize('change,reason',[
    ('drop_fast_response','Wrong stable events membership'),
    ('wrong_unstable_count','comparison registry reconstruction differs'),
    ('wrong_mean','Annual mean differs'),('negative_ghost','Wrong stable events membership'),
    ('duplicate_closure','Duplicate episode closure'),('changed_policy','metadata changed within'),
])
def test_wrong_labels_and_bound_archives_are_rejected(archived_seed,change,reason):
    p=archived_seed
    if change=='drop_fast_response':
        path=p/'economic_opportunities.json';rows=json.loads(path.read_text());rows=[r for r in rows if r['method']!='Tail'];write_json(path,rows)
        path=p/'opportunity_registry.json';rows=json.loads(path.read_text());next(r for r in rows if r['method']=='Tail')['stable_events']=0;write_json(path,rows)
    elif change=='wrong_unstable_count':
        path=p/'opportunity_registry.json';rows=json.loads(path.read_text());next(r for r in rows if r['method']=='Catoni')['unstable_runs']=0;write_json(path,rows)
    elif change=='wrong_mean':
        path=p/'block_01/comparison_events.parquet';df=pd.read_parquet(path);df.loc[df.method.eq('Greedy'),'true_block_mean']=-2e-8;df.to_parquet(path,index=False)
    elif change=='negative_ghost':np.savez_compressed(p/'block_02/ghosts.npz',true_mean=np.full((10,1),-2e-8))
    elif change=='duplicate_closure':
        path=p/'block_02/closed_episodes.json';rows=json.loads(path.read_text());rows.append(dict(rows[0]));write_json(path,rows)
    else:
        path=p/'block_02/comparison_events.parquet';df=pd.read_parquet(path);df.loc[df.method.eq('Greedy'),'added']=2;df.to_parquet(path,index=False)
    with pytest.raises(ValueError,match=reason):reconstruct_seed(p)
