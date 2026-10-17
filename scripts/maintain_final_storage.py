"""Observe the existing controller and compress only verified final prefixes.

No simulation launch, restart, threshold/analysis change or scientific-byte
change. Uses optional native filesystem compression in separate maintenance.
"""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import time

import compress_verified_json_storage as storage
from continue_full_study import (ObservationUnavailable,exclusive_controller,
                                 process_identity,validate_freezes)
from seal_full_snapshot import sha256,validate_snapshot

ROOT=Path(__file__).resolve().parents[1]


def ready_prefix(root):
    path=root/'outputs/park_revive_full_v3/main/stage_progress.json'
    if not path.exists():
        return 0
    row=json.loads(path.read_text())
    count=row.get('prefix_completed_and_replayed')
    if (row.get('stage')!='main' or row.get('requested_count')!=500
            or type(count) is not int or not 0<=count<=500):
        raise ValueError('Invalid complete-final prefix record')
    return count


def eligible_prefix(prefix,last):
    if type(prefix) is not int or type(last) is not int or not 0<=last<=prefix<=500:
        raise ValueError('Final prefix is invalid or moved backward')
    return prefix if prefix==500 and prefix>last or prefix-last>=50 else None


def maintain_prefix(root,prefix,directory):
    report=directory/f'main_{prefix:03d}.json'
    if not report.exists():
        return storage.compress(root,'main',prefix,report,True)
    _,freeze,_=validate_freezes(root)
    record=json.loads(report.read_text())
    seeds=list(range(60001,60001+prefix))
    if not (record.get('complete') is True and record.get('applied') is True
            and record.get('stage')=='main' and record.get('seeds')==seeds
            and record.get('source_sha256')==sha256(Path(storage.__file__))
            and record.get('scientific_source_hash')==freeze['scientific_source_hash']):
        raise ValueError('Existing storage record is incomplete or stale')
    rows=validate_snapshot(root/'outputs/park_revive_full_v3/main',seeds,
                           freeze['scientific_source_hash'],freeze['final_config'],
                           root/'scripts/verify_full_strategy.py')
    if record['input_digests']!={str(row['seed']):row['input_digest'] for row in rows}:
        raise ValueError('Existing storage record differs from current replay')
    return record


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--controller-pid',type=int,required=True)
    args=parser.parse_args()
    directory=ROOT/'outputs/park_revive_full_v3/storage_maintenance'
    directory.mkdir(exist_ok=True)
    initial=process_identity(args.controller_pid)
    if initial is None or 'continue_full_study.py' not in initial[-1]:
        raise ValueError('An actual existing continuation-controller handle is required')
    sources={str(path):sha256(path) for path in (Path(__file__),Path(storage.__file__))}
    state=dict(pid=os.getpid(),controller_pid=args.controller_pid,
               controller_identity=list(initial),source_sha256=sources,last_verified_prefix=0,reports=[])
    def update(phase,**values):
        state.update(phase=phase,updated_at=datetime.now(timezone.utc).isoformat(),**values)
        path=directory/'status.json';temporary=path.with_suffix('.tmp')
        temporary.write_text(json.dumps(state,indent=2)+'\n');temporary.replace(path)
    with exclusive_controller(directory/'.lock'):
        try:
            while True:
                if any(sha256(Path(path))!=expected for path,expected in sources.items()):
                    raise ValueError('Storage-maintenance source changed while loaded')
                try:
                    current=process_identity(args.controller_pid)
                    prefix=ready_prefix(ROOT)
                except (ObservationUnavailable,json.JSONDecodeError,OSError) as error:
                    update('observation_retry',observation_error=str(error))
                    time.sleep(45);continue
                target=eligible_prefix(prefix,state['last_verified_prefix'])
                if target is not None and (current==initial or prefix==500):
                    update('compressing_verified_prefix',prefix=target,observation_error=None)
                    record=maintain_prefix(ROOT,target,directory)
                    state['reports'].append(str(directory/f'main_{target:03d}.json'))
                    update('verified_prefix_compressed',last_verified_prefix=target,
                           allocated_bytes_reduction_this_prefix=record['allocated_bytes_reduction'])
                    print(json.dumps(dict(verified_prefix=target,
                          allocated_bytes_reduction=record['allocated_bytes_reduction'])),flush=True)
                if prefix==500 and state['last_verified_prefix']==500:
                    update('complete_final_storage_checked');return
                if current!=initial:
                    update('controller_ended_no_restart');return
                update('waiting_for_verified_final_prefix',observed_prefix=prefix)
                time.sleep(45)
        except BaseException as error:
            update('maintenance_stopped',error=f'{type(error).__name__}: {error}')
            raise


if __name__=='__main__':
    main()
