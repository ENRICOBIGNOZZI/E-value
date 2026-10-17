#!/usr/bin/env python3
"""Reconstruct stable and unstable opportunities from annual runs and ghosts.

Uses maximal positive runs rather than the simulator's online EventTracker.
Stored daily conditional-score arrays are averaged with math.fsum. The DGP,
conditional score formulas and optimizers are not replayed by this program.
"""
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd

from audit_full_event_snapshot import METHODS, audit as audit_reports, input_digest, sha256

META = ('seed','method','comparison_id','start','move','lifecycle','added','removed',
        'reference_support','candidate_support')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def reconstruct(metadata, rows, closure, block, tolerance, ghost=None):
    """Batch maximal-run calculation; consumes no previously classified labels."""
    require(bool(rows), 'Comparison has no annual observations')
    require(rows[0]['day'] == metadata['start']+block and
            all(b['day']-a['day'] == block for a,b in zip(rows,rows[1:])),
            'Annual observations are missing, duplicated or out of order')
    require(closure['day'] == rows[-1]['day'], 'Closure is not at the last observed review')
    require(all(math.isfinite(r['mean']) and (not r['selected'] or r['eligible']) for r in rows),
            'Invalid annual mean or selected eligibility')
    selected = [r for r in rows if r['selected']]
    require(not selected or (len(selected) == 1 and selected[0] is rows[-1] and closure['reason'] == 'selected'),
            'Selection and episode closure disagree')
    require(closure['reason'] != 'selected' or bool(selected), 'Selected closure has no selected review')
    positive = [r['mean'] > tolerance for r in rows]
    events=[];unstable=0;used_ghost=False;i=0
    while i < len(rows):
        if not positive[i]:
            i+=1;continue
        j=i+1
        while j < len(rows) and positive[j]:
            j+=1
        run=rows[i:j]
        if len(run) >= 2:
            confirmation=run[1]['day']
        elif j < len(rows):
            unstable+=1;i=j;continue
        else:
            require(ghost is not None and ghost['day'] == closure['day']+block and
                    math.isfinite(ghost['mean']), 'Missing or mistimed pending-run ghost')
            used_ghost=True
            if ghost['mean'] <= tolerance:
                unstable+=1;i=j;continue
            confirmation=ghost['day']
        onset=run[0]['day']
        criterion=next((r['day'] for r in run if r['eligible']),-1)
        chosen=next((r['day'] for r in run if r['selected']),-1)
        events.append(dict(**metadata,event_index=len(events)+1,onset_day=onset,
            event_kind='inception_positive' if i==0 else 'sign_change_positive',
            confirmation_day=confirmation,criterion_day=criterion,selected_day=chosen,
            termination_day=rows[j]['day'] if j<len(rows) else closure['day'],
            termination_reason='sign_reversal' if j<len(rows) else closure['reason'],
            criterion_detected=criterion>=0,selected=chosen>=0,
            criterion_delay_days=criterion-onset if criterion>=0 else -1,
            selection_delay_days=chosen-onset if chosen>=0 else -1))
        i=j
    require((ghost is not None) == used_ghost, 'Unexpected ghost for a nonpending run')
    return events,unstable


def reconstruct_seed(directory):
    directory=Path(directory)
    config=json.loads((directory/'config_frozen.json').read_text())
    block=config['block'];horizon=block*config['years'];tolerance=config['economic_tolerance']
    observations=defaultdict(list);metadata={};closures={};ghosts={};chosen_reviews=set()
    counts=Counter();maximum_mean_error=0.

    def mean_column(values, stored=None):
        nonlocal maximum_mean_error
        require(len(values)==block and np.isfinite(values).all(), 'Wrong or nonfinite daily mean column')
        mean=math.fsum(float(v) for v in values)/block
        if stored is not None:
            error=abs(mean-stored);maximum_mean_error=max(maximum_mean_error,error)
            require(math.isclose(mean,stored,abs_tol=1e-13,rel_tol=2e-10), 'Annual mean differs from daily score archive')
            require((mean>tolerance)==(stored>tolerance), 'Positive classification differs at the fixed threshold')
            counts['annual_mean_checks']+=1
        return mean

    def load_ghosts(order_path, archive_path, day):
        order=json.loads(order_path.read_text())
        if not order:
            require(not archive_path.exists(), 'Unexpected ghost archive with empty order')
            return
        with np.load(archive_path,allow_pickle=False) as archive:
            means=archive['true_mean']
            require(means.shape==(block,len(order)), 'Ghost order/array shape mismatch')
            for j,item in enumerate(order):
                cid=item['comparison_id']
                require(cid not in ghosts, 'Duplicate ghost comparison')
                ghosts[cid]=dict(day=day,mean=mean_column(means[:,j]),
                    candidate=item['candidate'],reference=item['reference'])
                counts['ghost_mean_columns']+=1

    blocks=sorted(directory.glob('block_*'))
    require([p.name for p in blocks]==[f'block_{i:02d}' for i in range(1,config['years'])],
            'Incomplete annual block membership')
    for year,folder in enumerate(blocks,1):
        day=(year+1)*block
        frame=pd.read_parquet(folder/'comparison_events.parquet',columns=[*META,'day','true_block_mean','eligible','selected'])
        rows={r.comparison_id:r for r in frame.itertuples(index=False)}
        require(len(rows)==len(frame), 'Duplicate annual comparison row')
        order=json.loads((folder/'comparison_order.json').read_text())
        require(set(order)==set(METHODS), 'Wrong annual method membership')
        expected_ids=[]
        for method,items in order.items():
            with np.load(folder/f'scores_{method}.npz',allow_pickle=False) as archive:
                means=archive['true_mean']
                require(means.shape==(block,len(items)), 'Score order/array shape mismatch')
                for j,item in enumerate(items):
                    cid=item['comparison_id'];expected_ids.append(cid)
                    require(cid in rows, 'Missing annual comparison row')
                    row=rows[cid]
                    require(row.method==method and int(row.day)==day and
                            list(row.candidate_support)==item['candidate'] and
                            list(row.reference_support)==item['reference'], 'Annual policy/order metadata mismatch')
                    meta={k:getattr(row,k) for k in META}
                    for k in ('seed','start','added','removed'):meta[k]=int(meta[k])
                    for k in ('reference_support','candidate_support'):meta[k]=[int(v) for v in meta[k]]
                    require(cid not in metadata or metadata[cid]==meta, 'Comparison policy metadata changed within an episode')
                    metadata[cid]=meta
                    if row.selected:
                        require((method,day) not in chosen_reviews, 'Multiple selected comparisons in one annual review')
                        chosen_reviews.add((method,day))
                    observations[cid].append(dict(day=day,mean=mean_column(means[:,j],float(row.true_block_mean)),
                        eligible=bool(row.eligible),selected=bool(row.selected)))
        require(len(expected_ids)==len(set(expected_ids)) and set(expected_ids)==set(rows),
                'Annual comparison membership differs from archive order')
        for item in json.loads((folder/'closed_episodes.json').read_text()):
            cid=item['comparison_id'];require(cid not in closures,'Duplicate episode closure')
            closures[cid]=item
        load_ghosts(folder/'ghost_order.json',folder/'ghosts.npz',day)
    terminal_order=directory/'terminal_ghost_order.json'
    if terminal_order.exists():
        load_ghosts(terminal_order,directory/'terminal_ghosts.npz',horizon+block)
        declared=json.loads((directory/'terminal_adjudication.json').read_text())
        terminal_ids={cid for cid,g in ghosts.items() if g['day']==horizon+block}
        require(len(declared)==len(terminal_ids) and {r['comparison_id'] for r in declared}==terminal_ids,
                'Terminal adjudication membership differs from its archive')
        for row in declared:
            g=ghosts[row['comparison_id']]
            require(row['adjudication_day']==g['day'] and
                    math.isclose(row['future_block_mean'],g['mean'],abs_tol=1e-13,rel_tol=2e-10) and
                    (row['future_block_mean']>tolerance)==(g['mean']>tolerance),
                    'Terminal adjudication differs from daily ghost means')
            counts['terminal_mean_checks']+=1
    require(set(metadata)==set(closures), 'Missing or unknown closed episode')
    require(set(ghosts)<=set(metadata), 'Ghost has no observed parent comparison')
    expected_events=[];expected_registry=[]
    for cid,meta in metadata.items():
        closure=closures[cid];reason=closure['reason'];day=closure['day']
        chosen=(meta['method'],day) in chosen_reviews
        require(reason in ('selected','competing_move','shortlist_withdrawal','administrative_end'),
                'Unknown comparison closure reason')
        if reason=='competing_move':require(chosen and not observations[cid][-1]['selected'],'Competing closure has no competing selection')
        if reason=='administrative_end':require(day==horizon and not chosen,'Wrong administrative closure')
        if reason=='shortlist_withdrawal':require(meta['move']=='swap' and not chosen,'Invalid shortlist withdrawal')
        ghost=ghosts.get(cid)
        if ghost is not None:
            require(ghost['candidate']==meta['candidate_support'] and ghost['reference']==meta['reference_support'],
                    'Ghost policy supports differ from its closed comparison')
        events,unstable=reconstruct(meta,observations[cid],closure,block,tolerance,ghost)
        expected_events.extend(events)
        expected_registry.append(dict(**meta,stable_events=len(events),unstable_runs=unstable))
        counts['comparisons_reconstructed']+=1
        counts['stable_events_reconstructed']+=len(events)
        counts['unstable_runs_reconstructed']+=unstable
        counts['events_confirmed_after_closure']+=sum(e['confirmation_day']>e['termination_day'] for e in events)
        counts['selected_events_confirmed_after_closure']+=sum(e['selected'] and e['confirmation_day']>e['termination_day'] for e in events)
        counts['events_selected_at_onset']+=sum(e['selected'] and e['selected_day']==e['onset_day'] for e in events)
    actual_events=json.loads((directory/'economic_opportunities.json').read_text())
    actual_registry=json.loads((directory/'opportunity_registry.json').read_text())
    for expected,actual,identity,name in [
        (expected_events,actual_events,lambda r:(r['comparison_id'],r['event_index']),'stable events'),
        (expected_registry,actual_registry,lambda r:r['comparison_id'],'comparison registry')]:
        a={identity(r):r for r in actual};e={identity(r):r for r in expected}
        require(len(a)==len(actual) and len(e)==len(expected) and a.keys()==e.keys(), f'Wrong {name} membership')
        for key,value in e.items():
            require(a[key]==value, f'{name} reconstruction differs: {key}')
    return dict(counts=dict(counts),maximum_annual_mean_error=maximum_mean_error)


def audit(snapshot,output):
    snapshot,output=Path(snapshot),Path(output)
    report=audit_reports(snapshot,output)
    seal=json.loads((snapshot/'snapshot_seal.json').read_text())
    totals=Counter();maximum=0.;per_seed=[]
    for seed in report['seeds']:
        result=reconstruct_seed(output/f'seed_{seed}')
        require(input_digest(output/f'seed_{seed}')==seal['input_digests'][str(seed)],
                'Source inputs changed during event reconstruction')
        totals.update(result['counts']);maximum=max(maximum,result['maximum_annual_mean_error'])
        per_seed.append(dict(seed=seed,**result))
        print(f'reconstructed stable/unstable opportunities seed={seed}',file=sys.stderr,flush=True)
    require(sha256(snapshot/'snapshot_seal.json')==report['snapshot_seal_sha256'] and
            all(sha256(snapshot/name)==h for name,h in seal['files_sha256'].items()),
            'Sealed snapshot changed during event reconstruction')
    return dict(complete=True,snapshot=str(snapshot),kind=seal['kind'],seeds=report['seeds'],
        counts=dict(totals),maximum_annual_mean_error=maximum,per_seed=per_seed,
        reporting_audit=report,snapshot_seal_sha256=report['snapshot_seal_sha256'],
        audit_source_sha256=sha256(Path(__file__)),
        reporting_auditor_source_sha256=sha256(Path(__file__).with_name('audit_full_event_snapshot.py')),
        scope='Independent batch reconstruction of all stable and unstable event labels, confirmations, delays and closure reasons from ordered annual conditional-score arrays, annual eligibility/selection flags, closure logs and one-block ghost continuations. Includes the separate JSON/CSV aggregation audit. No DGP resimulation, optimizer rerun or new market; the stored conditional-score formulas and selector decisions rely on their separately recorded arithmetic replay. Method-specific event populations do not identify causal cross-method delay or waiting-cost effects.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    if any(args.report.resolve().is_relative_to(p.resolve()) for p in (args.snapshot,args.output)):
        parser.error('Audit report must lie outside the sealed snapshot and raw output tree')
    result=audit(args.snapshot,args.output)
    args.report.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('per_seed','reporting_audit','seeds')},indent=2))
