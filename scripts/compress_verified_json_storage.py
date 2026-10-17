"""Reduce physical JSON storage without changing verified scientific bytes.

Optional macOS filesystem maintenance; no simulation/analysis configuration
change. Only explicitly requested complete, byte-current replay prefixes.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from continue_full_study import validate_freezes
from seal_full_snapshot import sha256, validate_snapshot

ROOT=Path(__file__).resolve().parents[1]


def physical_bytes(path):
    return path.stat().st_blocks*512


def ditto_copy(source, target):
    if sys.platform != 'darwin':
        raise RuntimeError('Applying filesystem compression requires macOS ditto')
    subprocess.run(['/usr/bin/ditto','--hfsCompression','--noclone',str(source),str(target)],
                   check=True,capture_output=True,text=True)


def compress_file(path, staging, *, copier=ditto_copy):
    """Copy, check both byte streams/identity, then atomically replace if smaller."""
    if path.is_symlink() or not path.is_file():
        raise ValueError('Refusing symlink or nonfile')
    original=path.stat()
    if original.st_dev != staging.stat().st_dev:
        raise ValueError('Staging must share the source filesystem')
    expected=sha256(path)
    before=physical_bytes(path)
    target=staging/'candidate'
    if target.exists():
        raise ValueError('Compression staging candidate already exists')
    try:
        copier(path,target)
        if target.is_symlink() or not target.is_file():
            raise ValueError('Copier did not create a regular staging file')
        current=path.stat()
        if (path.is_symlink() or current.st_ino != original.st_ino
                or current.st_dev != original.st_dev or current.st_size != original.st_size
                or current.st_mtime_ns != original.st_mtime_ns
                or sha256(path) != expected or sha256(target) != expected):
            raise ValueError('Byte or source-identity change during filesystem compression')
        after=physical_bytes(target)
        if after >= before:
            return None
        # ditto preserves filesystem metadata; timestamps/mode are checked
        # explicitly before replacement. ACLs/xattrs follow its native copy.
        copied=target.stat()
        if copied.st_mtime_ns != original.st_mtime_ns or copied.st_mode != original.st_mode:
            raise ValueError('Copy did not preserve timestamp or permissions')
        os.replace(target,path)
        if sha256(path) != expected:
            raise IOError('Post-replacement logical byte verification failed')
        return dict(path=str(path),logical_bytes=original.st_size,sha256=expected,
                    allocated_before=before,allocated_after=physical_bytes(path))
    finally:
        if target.exists():
            target.unlink()


def compress(root,stage,count,report,apply=False):
    if stage not in ('pilot','main'):
        raise ValueError('Unknown study stage')
    _,freeze,_=validate_freezes(root)
    low,high=freeze['pilot_pool' if stage=='pilot' else 'final_pool']
    if not 1 <= count <= high-low+1:
        raise ValueError('Requested prefix is outside the frozen pool')
    output=root/'outputs/park_revive_full_v3'/stage
    if report.exists() or any(report.resolve().is_relative_to(p.resolve())
                               for p in (output,root/'paper',root/'data')):
        raise ValueError('Report must be new and outside evidence/manuscript/data')
    if apply and sys.platform != 'darwin':
        raise RuntimeError('Filesystem compression is optional and macOS-only')
    seeds=list(range(low,low+count))
    config=freeze['pilot_config' if stage=='pilot' else 'final_config']
    verifier=root/'scripts/verify_full_strategy.py'
    before=validate_snapshot(output,seeds,freeze['scientific_source_hash'],config,verifier)
    fingerprints={str(row['seed']):row['input_digest'] for row in before}
    candidates=[]
    for seed in seeds:
        directory=output/f'seed_{seed}'
        if directory.is_symlink() or not directory.resolve().is_relative_to(output.resolve()):
            raise ValueError('Market directory leaves its stage')
        for path in sorted(directory.rglob('*.json')):
            if path.name.startswith('checkpoint'):
                continue
            if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()):
                raise ValueError('JSON path leaves its verified market')
            if path.stat().st_size >= 16384 and not getattr(path.stat(),'st_flags',0) & 32:
                candidates.append(path)
    free_before=shutil.disk_usage(output).free
    changed=[]
    if apply:
        with tempfile.TemporaryDirectory(prefix='.json-compression-',dir=output.parent) as folder:
            for path in candidates:
                row=compress_file(path,Path(folder))
                if row:
                    row['path']=str(path.relative_to(root))
                    changed.append(row)
    after=validate_snapshot(output,seeds,freeze['scientific_source_hash'],config,verifier)
    if fingerprints != {str(row['seed']):row['input_digest'] for row in after}:
        raise ValueError('Scientific byte fingerprints changed during compression')
    validate_freezes(root)
    result=dict(complete=True,applied=apply,captured_at=datetime.now(timezone.utc).isoformat(),
        stage=stage,seeds=seeds,source_sha256=sha256(Path(__file__)),
        scientific_source_hash=freeze['scientific_source_hash'],input_digests=fingerprints,
        all_current_input_digests_preserved=True,candidate_files=len(candidates),changed_files=changed,
        allocated_bytes_reduction=sum(row['allocated_before']-row['allocated_after'] for row in changed),
        filesystem_free_before=free_before,filesystem_free_after=shutil.disk_usage(output).free,
        scope='Native filesystem compression only. Logical file bytes/paths, replay counts, configurations, '
              'source and analysis are unchanged. Allocation reduction uses file st_blocks, not a guarantee '
              'about unrelated filesystem usage or remaining-study capacity. No active/unverified market '
              'or original empirical input is processed. macOS-specific compression is not needed for reproduction.')
    report.parent.mkdir(parents=True,exist_ok=True)
    with report.open('x') as stream:
        stream.write(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',choices=('pilot','main'),required=True)
    parser.add_argument('--count',type=int,required=True)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    result=compress(ROOT,args.stage,args.count,args.report,args.apply)
    print(json.dumps({k:v for k,v in result.items()
                      if k not in ('changed_files','input_digests','seeds')},indent=2))
