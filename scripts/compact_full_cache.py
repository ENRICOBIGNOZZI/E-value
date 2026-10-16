#!/usr/bin/env python3
"""Discard only regenerable checkpoints of fully replay-verified completed seeds."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
from verify_full_strategy import input_digest


def compact(output,apply=False):
    verified={r['seed']:r for r in json.loads((output/'arithmetic_verification.json').read_text())}
    verifier_hash=hashlib.sha256(Path(__file__).with_name('verify_full_strategy.py').read_bytes()).hexdigest()
    freed=0;seeds=[]
    for directory in sorted(output.glob('seed_*')):
        seed=int(directory.name.split('_')[-1]);record=verified.get(seed,{})
        if not record.get('complete') or record.get('verifier_sha256')!=verifier_hash:continue
        if record.get('input_digest')!=input_digest(directory):raise ValueError(f'Input bytes changed after replay: {seed}')
        metadata=directory/'checkpoint_archive.json'
        if not metadata.exists():continue
        audit=json.loads(metadata.read_text())
        paths=[p for p in (directory/'checkpoint.pkl',directory/'checkpoint.pkl.gz') if p.exists()]
        for path in paths:
            if path.suffix=='.gz':
                if hashlib.sha256(path.read_bytes()).hexdigest()!=audit['compressed_sha256']:raise ValueError('Archive digest mismatch')
                with gzip.open(path,'rb') as f:digest=hashlib.sha256(f.read()).hexdigest()
            else:digest=hashlib.sha256(path.read_bytes()).hexdigest()
            if digest!=audit['uncompressed_sha256']:raise ValueError('Checkpoint content digest mismatch')
        size=sum(p.stat().st_size for p in paths)
        if paths and apply:
            (directory/'checkpoint_cache_discarded.json').write_text(json.dumps(dict(seed=seed,
                reason='Completed seed fully verified by independent arithmetic replay; all ledgers and provenance retained.',
                removed_bytes=size,input_digest=record['input_digest'],checkpoint_sha256=audit['uncompressed_sha256']),indent=2)+'\n')
            for path in paths:path.unlink()
        if paths:freed+=size;seeds.append(seed)
    return dict(applied=apply,seeds=seeds,checkpoint_bytes=freed,
                preserved='All input data, market/score/weight/event ledgers, numeric results and source/configuration manifests.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args();print(json.dumps(compact(args.output,args.apply),indent=2))
