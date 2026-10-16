#!/usr/bin/env python3
"""Observe the live pilot, then run the frozen final pool and audit its reports.

No pilot is started/restarted here. Errors stop the continuation. Manuscript
promotion and scientific interpretation remain separate review tasks.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
# Exact plan bytes committed at c7f7275, before final observations. An amendment
# must be explicit; refreshing reporting metadata must not change this choice.
FROZEN_ANALYSIS_PLAN_SHA256 = 'e395d2f0be8d240b0c52d3bf41aa1d14850cdd23c9c1b76665e8fac216ee1609'


class ObservationUnavailable(RuntimeError):
    """A live or unconfirmed handle could not be inspected; retry it."""


def sha256(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            result.update(chunk)
    return result.hexdigest()


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def process_identity(pid):
    if pid < 1:
        raise ValueError('A positive process ID is required')
    try:
        result = subprocess.run(['ps', '-p', str(pid), '-o', 'lstart=', '-o', 'command='],
                                text=True, capture_output=True, timeout=5)
        parts = result.stdout.strip().split(None, 5)
        if result.returncode == 0 and len(parts) == 6:
            return tuple(parts)
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return None
    except PermissionError:
        pass
    raise ObservationUnavailable(f'PID {pid} is live or unconfirmed; process observation must be retried')


def require_stage_completion(output, stage, seeds):
    path = output/'stage_completion.json'
    if not path.exists():
        raise RuntimeError(f'{stage} process ended without a complete stage record')
    record = json.loads(path.read_text())
    if (record.get('stage') != stage or record.get('requested_seeds') != seeds
            or record.get('all_complete') is not True
            or record.get('arithmetic_replay_complete') is not True):
        raise ValueError(f'{stage} completion record does not cover the entire frozen pool')


def wait_for_pilot(pid, output, seeds, update, interval=30, *, identify=process_identity, pause=time.sleep):
    def observe():
        while True:
            try:
                return identify(pid)
            except ObservationUnavailable as error:
                update('waiting_for_pilot_observation_retry',pilot_pid=pid,
                       observation_error=str(error))
                pause(interval)
    original = observe()
    if original is not None and 'run_full_study.py pilot' not in original[-1]:
        raise ValueError('Supplied PID does not identify the pilot stage runner')
    while original is not None:
        current = observe()
        if current != original:
            break  # The original handle ended; do not follow a reused PID.
        update('waiting_for_pilot', pilot_pid=pid, pilot_identity=list(original),observation_error=None)
        pause(interval)
    # A dead/replaced/missing handle is never sufficient evidence of success.
    require_stage_completion(output, 'pilot', seeds)


def validate_freezes(root):
    plan_path = root/'reports/final_analysis_plan.json'
    if sha256(plan_path) != FROZEN_ANALYSIS_PLAN_SHA256:
        raise ValueError('Machine-readable final analysis differs from its committed freeze')
    plan = json.loads(plan_path.read_text())
    protocol = root/plan['scientific_protocol']
    if sha256(protocol) != plan['scientific_protocol_sha256']:
        raise ValueError('Scientific protocol changed after final-analysis freeze')
    if (sha256(root/'scripts/assess_final_study.py') != plan['analysis_source_sha256']
            or sha256(root/'reports/final_analysis_plan.md') != plan['human_readable_plan_sha256']):
        raise ValueError('Final analysis differs from its freeze')
    freeze = json.loads(protocol.read_text())
    paths = sorted([*root.joinpath('src').rglob('*.py'), *root.joinpath('research').rglob('*.py')])
    source = {str(p.relative_to(root)):sha256(p) for p in paths}
    if canonical_hash(source) != freeze['scientific_source_hash']:
        raise ValueError('Scientific implementation differs from v3 freeze')
    for name, key in [('full_pilot.json','pilot_config'), ('full_main.json','final_config')]:
        if json.loads((root/'configs'/name).read_text()) != freeze[key]:
            raise ValueError(f'Changed frozen configuration: {name}')
    low, high = freeze['final_pool']
    if plan['final_seeds'] != list(range(low, high+1)) or len(plan['final_seeds']) != 500:
        raise ValueError('Final analysis does not retain the declared 500 markets')
    return plan, freeze, protocol


@contextmanager
def exclusive_controller(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError('Another continuation controller holds the process lock') from error
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def write_immutable(path, record):
    if path.exists():
        if json.loads(path.read_text()) != record:
            raise ValueError(f'Refusing to overwrite a different assessment: {path}')
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        stream.write(json.dumps(record, indent=2)+'\n')


def verified_seal(root, stage, freeze, protocol):
    from seal_full_snapshot import seal, validate_snapshot
    output = root/'outputs/park_revive_full_v3'/stage
    low, high = freeze['pilot_pool' if stage == 'pilot' else 'final_pool']
    seeds = list(range(low, high+1))
    require_stage_completion(output, stage, seeds)
    destination = root/'reports/full_v3_snapshots'/f'{stage}_{len(seeds):03d}'
    if destination.exists():
        record = json.loads((destination/'snapshot_seal.json').read_text())
        config = freeze['pilot_config' if stage == 'pilot' else 'final_config']
        rows = validate_snapshot(output, seeds, freeze['scientific_source_hash'], config,
                                 root/'scripts/verify_full_strategy.py')
        if (record.get('complete') is not True or record['seeds'] != seeds
                or record['source_hash'] != freeze['scientific_source_hash']
                or record['config_hash'] != canonical_hash(config)
                or record['input_digests'] != {str(r['seed']):r['input_digest'] for r in rows}):
            raise ValueError('Existing seal differs from current complete stage inputs')
        for name, digest in record['files_sha256'].items():
            if sha256(destination/name) != digest:
                raise ValueError('Previously sealed report changed')
    else:
        seal(output, destination, protocol, stage)
    return destination


def refuse_existing_final_runner():
    result = subprocess.run(['ps', '-axo', 'pid=,command='],text=True,capture_output=True,check=True)
    for line in result.stdout.splitlines():
        if ('run_full_study.py main' in line
                or ('run_full_strategy.py' in line and 'full_main.json' in line)):
            raise RuntimeError('A final-stage runner already exists; do not launch a duplicate')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pilot-pid', type=int, required=True)
    parser.add_argument('--workers', type=int, default=2)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error('Positive worker count required')
    output = ROOT/'outputs/park_revive_full_v3'
    state_path = output/'continuation_status.json'
    state = dict(controller_pid=os.getpid(), pilot_pid=args.pilot_pid, workers=args.workers,
                 source_sha256=sha256(Path(__file__)))
    child = None

    def update(phase, **values):
        state.update(phase=phase, updated_at=datetime.now(timezone.utc).isoformat(), **values)
        temporary = state_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(state, indent=2)+'\n'); temporary.replace(state_path)

    with exclusive_controller(output/'.continuation.lock'):
        try:
            plan, freeze, protocol = validate_freezes(ROOT)
            state['analysis_plan_sha256'] = sha256(ROOT/'reports/final_analysis_plan.json')
            print('Observing existing pilot handle; no pilot restart.', flush=True)
            low, high = freeze['pilot_pool']
            wait_for_pilot(args.pilot_pid, output/'pilot', list(range(low,high+1)), update)
            validate_freezes(ROOT)
            # Load scientific/reporting libraries only after the long wait.
            from assess_final_study import assess
            from audit_full_snapshot import audit
            update('sealing_complete_pilot')
            pilot_snapshot = verified_seal(ROOT, 'pilot', freeze, protocol)
            write_immutable(ROOT/'reports/full_v3_snapshots/pilot_100_numeric_audit.json',
                            audit(pilot_snapshot, output/'pilot'))
            write_immutable(ROOT/'reports/full_v3_snapshots/pilot_100_planned_analysis_diagnostic.json',
                            assess(pilot_snapshot, ROOT/'reports/final_analysis_plan.json', True))
            # No condition on the observed economic sign or interval width.
            validate_freezes(ROOT)
            refuse_existing_final_runner()
            command = [sys.executable, str(ROOT/'scripts/run_full_study.py'), 'main',
                       '--count','500','--workers',str(args.workers),'--batch-size','10',
                       '--compact-verified-checkpoints']
            environment = os.environ.copy()
            environment.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
            logfile = ROOT/'tmp/full-v3-final500.log'; logfile.parent.mkdir(exist_ok=True)
            with logfile.open('a') as stream:
                child = subprocess.Popen(command,cwd=ROOT,env=environment,stdout=stream,stderr=subprocess.STDOUT)
                print(f'Final stage started: pid={child.pid}',flush=True)
                while child.poll() is None:
                    update('running_final', final_pid=child.pid, final_command=command,
                           final_log=str(logfile))
                    try:
                        child.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        pass  # Observation timeout is not process failure or a restart trigger.
                if child.returncode:
                    raise RuntimeError(f'Final stage stopped with exit code {child.returncode}; see {logfile}')
            validate_freezes(ROOT)
            update('sealing_complete_final', final_returncode=0)
            final_snapshot = verified_seal(ROOT, 'main', freeze, protocol)
            write_immutable(ROOT/'reports/full_v3_snapshots/main_500_numeric_audit.json',
                            audit(final_snapshot, output/'main'))
            write_immutable(ROOT/'reports/full_final_assessment.json',
                            assess(final_snapshot, ROOT/'reports/final_analysis_plan.json'))
            update('final_audited_ready_for_manuscript', final_snapshot=str(final_snapshot))
            print('All final evidence audited; manuscript synthesis remains.',flush=True)
        except Exception as error:
            phase = ('controller_error_final_handle_live'
                     if child is not None and child.poll() is None else 'stopped_on_error')
            update(phase, error=f'{type(error).__name__}: {error}')
            raise


if __name__ == '__main__':
    main()
