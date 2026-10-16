#!/usr/bin/env python3
"""Post-hoc first-wave spending illustration, not an additional simulation arm."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',type=Path,default=Path('outputs/park_revive_tail_v1/first_entry'))
    parser.add_argument('--destination',type=Path,default=Path('reports/tail_results/search_budget_audit.json'))
    args=parser.parse_args();rows=[];sources={}
    for seed in sorted(args.results.glob('seed_*')):
        path=seed/'annual_events.csv'
        if not path.exists():continue
        sources[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        frame=pd.read_csv(path);g=frame[frame.arm.eq('Tail-geometry')]
        if len(g)!=1400 or g.signal.nunique()!=100 or g.day.nunique()!=14:raise ValueError('Incomplete first-entry horizon')
        rows.append(dict(seed=int(g.seed.iloc[0]),max_annual_log_e=float(g.log_e.max()),
            individual_crossing=bool((g.log_e>=np.log(20)).any()),
            first_wave_spending_crossing=bool((g.log_e>=np.log(4000)).any())))
    result=dict(post_hoc=True,original_protocol_unchanged=True,alpha=.05,initial_episodes=100,
        first_wave_total_budget=.025,first_wave_budget_per_episode=.00025,
        remaining_budget=.025,remaining_episode_rule='a_(100+l)=alpha/[2*l*(l+1)], l>=1',
        individual_threshold=20,spending_threshold=4000,spending_log_threshold=float(np.log(4000)),
        seeds=len(rows),individual_markets_with_crossing=sum(r['individual_crossing'] for r in rows),
        spending_markets_with_crossing=sum(r['first_wave_spending_crossing'] for r in rows),
        scope='Exact initial fixed-reference replay implication; no global error or optimal-spending empirical claim.',
        rows=rows,input_sha256=sources)
    args.destination.parent.mkdir(parents=True,exist_ok=True)
    args.destination.write_text(json.dumps(result,indent=2)+'\n')
    print({k:v for k,v in result.items() if k not in ('rows','input_sha256')})


if __name__=='__main__':main()
