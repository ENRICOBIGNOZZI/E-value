"""Compare a fresh repeated market with the canonical final market.

Production requires the complete audited 500-market bundle. This is an exact
scientific-file comparison, not additional market evidence or a new replay.
Runtime values and checkpoint caches are operational; their scopes are explicit.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def scientific_files(directory):
    ignored = {'status.json', 'runtime.csv', 'numerical_initialization.json'}
    files = {}
    for path in directory.rglob('*'):
        if path.is_symlink():
            raise ValueError('Symlink in market evidence')
        relative = str(path.relative_to(directory))
        if not path.is_file() or path.name.startswith('checkpoint') or relative in ignored:
            continue
        if path.suffix not in {'.json', '.csv', '.npz', '.parquet'}:
            raise ValueError('Unexpected market artifact: '+str(path))
        files[relative] = path
    required = {'config_frozen.json', 'source_manifest.json', 'feature_library.json',
                'protocol.json', 'daily_ledger.parquet', 'comparison_events.parquet',
                'decisions.json', 'deployments.json', 'economic_opportunities.json',
                'opportunity_registry.json', 'metrics_by_seed.csv'}
    annual = ['daily_ledger.parquet', 'comparison_events.parquet', 'decisions.json',
              'deployments.json', 'comparison_order.json', 'shortlists.json',
              'closed_episodes.json', 'ghost_order.json', 'solver_recoveries.json',
              'scores_Greedy.npz', 'scores_HAC.npz', 'scores_Catoni.npz', 'scores_Tail.npz']
    required |= {f'block_{year:02d}/{name}' for year in range(1,15) for name in annual}
    if not required <= set(files):
        raise ValueError('Incomplete scientific artifact membership')
    return files


def compare_seed(original, fresh):
    """Pure exact comparison; production provenance/replay gates run separately."""
    left, right = scientific_files(original), scientific_files(fresh)
    if left.keys() != right.keys():
        raise ValueError('Scientific file membership differs')
    hashes = {}
    for name in sorted(left):
        digest = sha(left[name])
        if digest != sha(right[name]):
            raise ValueError('Scientific artifact differs: '+name)
        hashes[name] = digest
    statuses = [read_json(p/'status.json') for p in (original,fresh)]
    for status in statuses:
        if (status.get('seed') != 60469 or status.get('complete') is not True
                or status.get('completed_blocks') != 14 or status.get('total_blocks') != 14):
            raise ValueError('Wrong or incomplete market status')
    if ({k:v for k,v in statuses[0].items() if k != 'elapsed_seconds'}
            != {k:v for k,v in statuses[1].items() if k != 'elapsed_seconds'}):
        raise ValueError('Scientific status fields differ')
    for directory in (original,fresh):
        with (directory/'runtime.csv').open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        if (len(rows) != 14 or [int(r['year']) for r in rows] != list(range(1,15))
                or any(int(r['seed']) != 60469 or not math.isfinite(float(r['seconds']))
                       or float(r['seconds']) < 0 for r in rows)):
            raise ValueError('Runtime calendar or measurement invalid')
    old = read_json(original/'numerical_initialization.json')
    new = read_json(fresh/'numerical_initialization.json')
    if (not old.get('calls') or old['calls'] != new.get('calls')
            or not old.get('initializer_profile_sha256')
            or old['initializer_profile_sha256'] != new.get('profile_sha256')):
        raise ValueError('Numerical initialization differs')
    return dict(complete=True, byte_identical_scientific_file_pairs=len(hashes),
                scientific_files_sha256=hashes, scientific_status_fields_equal=True,
                all_fourteen_runtime_calendar_rows_valid=True,
                numerical_initialization_calls_equal=True,
                exclusions=['elapsed_seconds in status.json', 'runtime seconds values',
                            'checkpoint caches', 'distinct reproduction-driver provenance'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fresh-output', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    destination = args.report.resolve()
    if (destination.exists() or not any(destination.is_relative_to((ROOT/p).resolve())
                                       for p in ['tmp','reports'])):
        raise ValueError('Comparison report requires a new tmp/ or reports/ destination')
    snapshot = ROOT/'reports/full_v3_snapshots/main_500'
    if not (snapshot/'snapshot_seal.json').exists():
        raise ValueError('Complete audited final study required before production comparison')
    fresh_output = args.fresh_output.resolve()
    if not fresh_output.is_relative_to((ROOT/'tmp').resolve()):
        raise ValueError('Fresh output must be the isolated tmp/ reproduction')
    source_hash = sha(__file__)
    sys.path.insert(0,str(ROOT/'scripts'))
    from build_final_manuscript_results import validate_bundle
    from continue_full_study import validate_freezes
    from reproduce_final_60469 import approved_profile, PROFILE_SHA256
    from seal_full_snapshot import validate_snapshot
    from verify_full_strategy import input_digest
    output = ROOT/'outputs/park_revive_full_v3/main'
    bundle = validate_bundle(ROOT, snapshot, output,
        ROOT/'reports/full_v3_snapshots/main_500_numeric_audit.json',
        ROOT/'reports/full_v3_snapshots/main_500_event_adjudication_audit.json',
        ROOT/'reports/full_final_assessment.json')
    _, freeze, _ = validate_freezes(ROOT)
    profile = approved_profile(ROOT)
    receipt = read_json(fresh_output/'reproduction_verification.json')
    if (receipt.get('complete') is not True or receipt.get('seed') != 60469
            or receipt.get('checkpoint_loaded') is not False
            or receipt.get('profile_sha256') != PROFILE_SHA256
            or receipt.get('driver_sha256') != sha(ROOT/'scripts/reproduce_final_60469.py')
            or receipt.get('original_scientific_source_hash') != freeze['scientific_source_hash']
            or len(receipt.get('calls',[])) != 1
            or receipt['calls'][0]['problem_sha256'] != profile['known_problem_sha256']):
        raise ValueError('Fresh-from-training receipt differs from declared reproduction')
    record = validate_snapshot(fresh_output, [60469], freeze['scientific_source_hash'],
                               freeze['final_config'], ROOT/'scripts/verify_full_strategy.py')[0]
    if record != receipt['independent_replay']:
        raise ValueError('Fresh replay differs from its production receipt')
    original, fresh = output/'seed_60469', fresh_output/'seed_60469'
    result = compare_seed(original,fresh)
    if (input_digest(original) != bundle['seal']['input_digests']['60469']
            or input_digest(fresh) != record['input_digest'] or sha(__file__) != source_hash):
        raise ValueError('Comparison inputs or source changed during comparison')
    result.update(source_sha256=source_hash, seed=60469, original_final_markets=500,
                  snapshot_seal_sha256=sha(snapshot/'snapshot_seal.json'),
                  fresh_receipt_sha256=sha(fresh_output/'reproduction_verification.json'),
                  original_input_digest=bundle['seal']['input_digests']['60469'],
                  fresh_input_digest=record['input_digest'],
                  scope='Exact equality of every scientific artifact, status counts and initialization calls '
                  'for the same final-market seed regenerated without a checkpoint. All original 500 markets '
                  'and their complete audits required before comparison. Runtime values, checkpoint caches '
                  'and distinct driver provenance excluded explicitly. No new financial replication or replay count.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('x') as stream:
        stream.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'scientific_files_sha256'},indent=2))


if __name__ == '__main__':
    main()
