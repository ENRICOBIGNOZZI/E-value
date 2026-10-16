#!/usr/bin/env python3
"""Run predeclared full-strategy markets; this never downloads empirical data."""
import argparse
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'research')]
from park_revive.config import Config
from park_revive_full.engine import run_seed


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--seeds',type=int,nargs='+',required=True)
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--stop-after-blocks',type=int)
    args=parser.parse_args()
    cfg=Config.read(args.config)
    for seed in args.seeds:
        print(run_seed(cfg,seed,args.output/f'seed_{seed}',args.resume,args.stop_after_blocks),flush=True)


if __name__=='__main__':main()
