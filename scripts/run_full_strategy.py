#!/usr/bin/env python3
"""Run predeclared full-strategy markets; this never downloads empirical data."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import shutil
import traceback

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'research')]
from park_revive.config import Config
from park_revive_full.engine import run_seed,source_fingerprint


def compress_checkpoint(directory):
    original=directory/'checkpoint.pkl'
    if not original.exists():return
    target=directory/'checkpoint.pkl.gz';temporary=directory/'checkpoint.pkl.gz.tmp'
    digest=hashlib.sha256(original.read_bytes()).hexdigest()
    with original.open('rb') as source,gzip.open(temporary,'wb',compresslevel=6) as dest:shutil.copyfileobj(source,dest)
    with gzip.open(temporary,'rb') as source:
        if hashlib.sha256(source.read()).hexdigest()!=digest:raise IOError('Checkpoint archive verification failed')
    temporary.replace(target)
    (directory/'checkpoint_archive.json').write_text(json.dumps(dict(uncompressed_sha256=digest,
        compressed_sha256=hashlib.sha256(target.read_bytes()).hexdigest()),indent=2)+'\n')
    original.unlink()


def run_one(job):
    cfg,seed,output,resume,stop,compress,reserve=job
    directory=output/f'seed_{seed}'
    try:
        status=directory/'status.json'
        if resume and status.exists() and json.loads(status.read_text())['complete']:
            if Config.read(directory/'config_frozen.json').digest!=cfg.digest:raise ValueError('Completed configuration mismatch')
            if json.loads(status.read_text())['source_hash']!=source_fingerprint()[0]:raise ValueError('Completed source mismatch')
            if compress:compress_checkpoint(directory)
            result=dict(seed=seed,complete=True,already_complete=True)
        else:
            if shutil.disk_usage(output.parent).free<reserve*2**30:raise OSError('Insufficient free disk reserve')
            result=run_seed(cfg,seed,directory,resume,stop)
            if result['complete'] and compress:compress_checkpoint(directory)
        print(json.dumps(result),flush=True);return result
    except Exception:
        directory.mkdir(parents=True,exist_ok=True)
        error=traceback.format_exc();(directory/'execution_error.txt').write_text(error)
        result=dict(seed=seed,complete=False,error=error)
        print(json.dumps(result),flush=True);return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--seeds',type=int,nargs='+')
    group.add_argument('--start-seed',type=int)
    parser.add_argument('--count',type=int,default=1)
    parser.add_argument('--workers',type=int,default=1)
    parser.add_argument('--keep-checkpoint-uncompressed',action='store_true')
    parser.add_argument('--reserve-gb',type=float,default=2.)
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--stop-after-blocks',type=int)
    args=parser.parse_args()
    cfg=Config.read(args.config)
    if args.workers<1 or args.count<1 or args.reserve_gb<0:parser.error('Positive worker/count and nonnegative disk reserve required')
    seeds=args.seeds if args.seeds is not None else list(range(args.start_seed,args.start_seed+args.count))
    if len(set(seeds))!=len(seeds):parser.error('Duplicate seeds would share output files')
    args.output.mkdir(parents=True,exist_ok=True)
    jobs=[(cfg,seed,args.output,args.resume,args.stop_after_blocks,not args.keep_checkpoint_uncompressed,args.reserve_gb) for seed in seeds]
    if args.workers==1:results=[run_one(job) for job in jobs]
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:results=list(pool.map(run_one,jobs))
    if any('error' in result for result in results):raise SystemExit(1)


if __name__=='__main__':main()
