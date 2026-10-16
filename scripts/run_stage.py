"""Tracked, resumable batches; no unmonitored background process."""
import argparse
import subprocess
import sys
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('stage',choices=['pilot','main'])
p.add_argument('--count',type=int)
p.add_argument('--start',type=int,default=0)
p.add_argument('--output',type=Path)
args=p.parse_args()
size=100 if args.stage=='pilot' else 500
count=args.count if args.count is not None else size-args.start
if count<1 or args.start<0 or args.start+count>size:raise ValueError('Invalid batch range')
first=20001 if args.stage=='pilot' else 30001
output=args.output or Path('outputs/park_revive_v1')/('frozen_'+args.stage)
for seed in range(first+args.start,first+args.start+count):
    command='resume' if (output/f'seed_{seed}/checkpoint.pkl').exists() else 'simulate'
    subprocess.run([sys.executable,'-m','park_revive.cli',command,'--stage',args.stage,
        '--config',f'configs/{args.stage}.json','--seeds',str(seed),'--output',str(output)],check=True)
subprocess.run([sys.executable,'-m','park_revive.cli','report','--output',str(output)],check=True)
