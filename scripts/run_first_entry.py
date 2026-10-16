"""Resume the locally frozen first-entry seed pool and render its numeric report."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

p=argparse.ArgumentParser()
p.add_argument('--count',type=int,default=20);p.add_argument('--start',type=int,default=0)
p.add_argument('--output',default='outputs/park_revive_tail_v1/first_entry')
args=p.parse_args()
if args.count<1 or args.start<0 or args.start+args.count>20:raise ValueError('Only the declared twenty-seed pool is available')
root=Path(__file__).resolve().parents[1]
env=dict(os.environ,PYTHONPATH=str(root/'src'))
seeds=list(range(40001+args.start,40001+args.start+args.count))
subprocess.run([sys.executable,'-m','park_revive_extensions.first_entry','--config','configs/main.json',
    '--seeds',*map(str,seeds),'--output',args.output,'--resume'],cwd=root,env=env,check=True)
subprocess.run([sys.executable,'scripts/tail_study.py','report','--output',args.output],cwd=root,env=env,check=True)
