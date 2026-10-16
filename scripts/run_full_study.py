#!/usr/bin/env python3
"""Run a declared stage, stop on failure, replay every seed, then summarize."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('pilot','main'))
    parser.add_argument('--count',type=int)
    parser.add_argument('--workers',type=int,default=2)
    parser.add_argument('--batch-size',type=int,default=10)
    parser.add_argument('--compact-verified-checkpoints',action='store_true')
    args=parser.parse_args()
    first,maximum=(50001,100) if args.stage=='pilot' else (60001,500)
    count=maximum if args.count is None else args.count
    if not 1<=count<=maximum:parser.error('Count must remain inside the declared seed pool')
    if args.batch_size<1:parser.error('Positive batch size required')
    output=ROOT/'outputs/park_revive_full_v3'/args.stage
    config=ROOT/'configs'/('full_pilot.json' if args.stage=='pilot' else 'full_main.json')
    destination=ROOT/'reports'/('full_v3_results' if args.stage=='pilot' else 'full_final_results')
    environment=os.environ.copy();environment.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    def run(script,*arguments):
        subprocess.run([sys.executable,str(ROOT/'scripts'/script),*map(str,arguments)],cwd=ROOT,env=environment,check=True)
    for offset in range(0,count,args.batch_size):
        start=first+offset;size=min(args.batch_size,count-offset)
        run('run_full_strategy.py','--config',config,'--output',output,'--start-seed',start,'--count',size,
            '--workers',args.workers,'--resume')
        for seed in range(start,start+size):
            status=json.loads((output/f'seed_{seed}'/'status.json').read_text())
            if not status['complete']:raise RuntimeError(f'Incomplete batch, not summarized: {seed}')
        run('verify_full_strategy.py','--output',output,'--seeds',*range(start,start+size),'--resume')
        if args.compact_verified_checkpoints:run('compact_full_cache.py','--output',output,'--apply')
        (output/'stage_progress.json').write_text(json.dumps(dict(stage=args.stage,requested_count=count,
            prefix_completed_and_replayed=offset+size,batch_size=args.batch_size),indent=2)+'\n')
    for seed in range(first,first+count):
        status=json.loads((output/f'seed_{seed}'/'status.json').read_text())
        if not status['complete']:raise RuntimeError(f'Incomplete stage, not summarized: {seed}')
    run('build_full_results.py','--output',output,'--destination',destination,'--seeds',*range(first,first+count))
    (output/'stage_completion.json').write_text(json.dumps(dict(stage=args.stage,
        requested_seeds=list(range(first,first+count)),all_complete=True,arithmetic_replay_complete=True),indent=2)+'\n')


if __name__=='__main__':main()
