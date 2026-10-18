"""Resume every remaining final market after an archived disk-only stop.

Requires three GiB free and the entire preceding independently replayed prefix.
Refuses live duplicate generators and preserves every archived failure.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from continue_full_study import (exclusive_controller, refuse_existing_final_runner,
                                 sha256, validate_freezes, verified_seal, write_immutable)
from seal_full_snapshot import validate_snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', type=int, required=True)
    parser.add_argument('--failure-audit', type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.prefix < 500:
        parser.error('--prefix must be between 1 and 499')
    output = ROOT/'outputs/park_revive_full_v3/main'
    archive = args.failure_audit.resolve()
    state_path = output.parent/'remaining_recovery_status_20261018.json'
    state = dict(controller_pid=os.getpid(), source_sha256=sha256(Path(__file__)),
                 workers=1, original_guard_gib=2, startup_reserve_gib=3,
                 archived_failure_sha256=sha256(archive), verified_prefix=args.prefix,
                 archived_failure=str(archive))
    log = ROOT/'tmp/final-remaining-recovery-20261018.log'
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')

    def update(phase, **values):
        state.update(phase=phase, updated_at=datetime.now(timezone.utc).isoformat(), **values)
        temporary = state_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(state, indent=2)+'\n')
        temporary.replace(state_path)

    def run(script, *arguments):
        with log.open('a') as stream:
            child = subprocess.Popen([sys.executable, str(ROOT/'scripts'/script),
                                      *map(str, arguments)], cwd=ROOT, env=env,
                                     stdout=stream, stderr=subprocess.STDOUT)
            update('running_'+script, child_pid=child.pid, child_script=script)
            code = child.wait()
        if code:
            raise RuntimeError(f'{script} stopped with {code}; see {log}')

    with exclusive_controller(output.parent/'.continuation.lock'):
        try:
            update('validating_recovery_preconditions')
            _, freeze, protocol = validate_freezes(ROOT)
            refuse_existing_final_runner()
            free = shutil.disk_usage(ROOT).free
            if free < 3*2**30:
                raise OSError('At least 3 GiB free required before recovery; original 2 GiB per-seed guard retained')
            failure = json.loads(archive.read_text())
            remaining = list(range(60001+args.prefix,60501))
            if (failure.get('kind') != 'preserved_actual_disk_guard_stop'
                    or failure.get('complete') is not True
                    or failure.get('both_original_handles_terminal') is not True
                    or failure['remaining_generation_seeds'] != remaining
                    or failure['generated_final_markets'] != args.prefix
                    or failure['source_hash'] != freeze['scientific_source_hash']):
                raise ValueError('Archived failure differs from the declared remaining pool')
            known = {row['original']: row for row in failure['errors_archived']}
            actual = {str(p.relative_to(ROOT)) for p in output.glob('seed_*/execution_error.txt')}
            if actual != set(known):
                raise ValueError('Live failures differ from the preserved disk-only stop')
            for original, row in known.items():
                if (sha256(ROOT/original) != row['sha256']
                        or sha256(ROOT/row['archived']) != row['sha256']):
                    raise ValueError('Original failure or archived copy changed')
                if not (ROOT/original).read_text().endswith('OSError: Insufficient free disk reserve\n'):
                    raise ValueError('Refusing to clear a failure that is not the exact disk guard')
            records = validate_snapshot(output, list(range(60001,60001+args.prefix)),
                                        freeze['scientific_source_hash'], freeze['final_config'],
                                        ROOT/'scripts/verify_full_strategy.py')
            if shutil.disk_usage(ROOT).free < 3*2**30:
                raise OSError('Free capacity fell below startup reserve during validation')
            milestone = ROOT/f'reports/full_v3_results/final{args.prefix:03d}_replay_milestone.json'
            prior_capture = json.loads(milestone.read_text())['captured_at'] if milestone.exists() else datetime.now(timezone.utc).isoformat()
            write_immutable(milestone, dict(
                complete=True, kind='verified_final_execution_prefix',
                captured_at=prior_capture, stage='main',
                seeds=list(range(60001,60001+args.prefix)), complete_market_replays=args.prefix,
                declared_final_pool_size=500, scientific_source_hash=freeze['scientific_source_hash'],
                final_config_sha256=sha256(ROOT/'configs/full_main.json'),
                analysis_plan_sha256=sha256(ROOT/'reports/final_analysis_plan.json'),
                verifier_sha256=sha256(ROOT/'scripts/verify_full_strategy.py'),
                all_current_input_digests_match=True,
                input_digests={str(r['seed']):r['input_digest'] for r in records},
                scalar_checks_from_existing_replays=sum(r['checks'] for r in records),
                ghost_pairs_from_existing_replays=sum(r['ghost_pairs_checked'] for r in records),
                maximum_log_e_replay_error=max(r['max_absolute_errors']['log_e'] for r in records),
                numerical_amendment_sha256=sha256(ROOT/'reports/full_v3_recovery_20261018/qp_60469/executed_initialization.json'),
                storage_reports_sha256={name:sha256(ROOT/name) for name in [
                    'reports/full_v3_results/json_storage_compression_main480.json',
                    'reports/full_v3_results/parquet_storage_compression_main480.json']},
                scope='Completed/replayed execution prefix only; not final economic inference. '
                'All current raw digests match after physical compression and verified-cache compaction. '
                'Counts summarize existing independent replays, not new checks from this validation. '
                'The post-freeze QP initialization remains explicitly supplementary. All 500 markets required.'))
            update('recovering_archived_disk_stop', remaining_seeds=remaining)
            for original in known:
                (ROOT/original).unlink()
            for first in range(60001+args.prefix,60501,10):
                count = min(10,60501-first)
                validate_freezes(ROOT)
                run('run_full_strategy.py', '--config', ROOT/'configs/full_main.json',
                    '--output', output, '--start-seed', first, '--count', count,
                    '--workers', 1, '--resume')
                run('verify_full_strategy.py', '--output', output, '--seeds',
                    *range(first,first+count), '--resume')
                run('compact_full_cache.py', '--output', output, '--apply')
                (output/'stage_progress.json').write_text(json.dumps(dict(
                    stage='main', requested_count=500,
                    prefix_completed_and_replayed=first+count-1-60000), indent=2)+'\n')
            run('build_full_results.py', '--output', output,
                '--destination', ROOT/'reports/full_final_results', '--seeds', *range(60001,60501))
            (output/'stage_completion.json').write_text(json.dumps(dict(
                stage='main', requested_seeds=list(range(60001,60501)),
                all_complete=True, arithmetic_replay_complete=True), indent=2)+'\n')
            _, freeze, protocol = validate_freezes(ROOT)
            update('sealing_complete_final')
            snapshot = verified_seal(ROOT, 'main', freeze, protocol)
            from audit_full_snapshot import audit
            from assess_final_study import assess
            write_immutable(ROOT/'reports/full_v3_snapshots/main_500_numeric_audit.json', audit(snapshot,output))
            write_immutable(ROOT/'reports/full_final_assessment.json',
                            assess(snapshot, ROOT/'reports/final_analysis_plan.json'))
            run('audit_full_event_adjudication.py', '--snapshot', snapshot, '--output', output,
                '--report', ROOT/'reports/full_v3_snapshots/main_500_event_adjudication_audit.json')
            run('build_final_manuscript_results.py')
            run('build_final_diagnostics.py')
            update('final_audited_ready_for_manuscript')
        except Exception as error:
            update('stopped_on_error', error=f'{type(error).__name__}: {error}')
            raise


if __name__ == '__main__':
    main()
