"""Native compression of byte-current completed final-market Parquet files.

Uses the existing checked atomic filesystem copier; logical Parquet bytes,
scientific sources and replay counts are unchanged.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import tempfile

from compress_verified_json_storage import compress_file
from continue_full_study import validate_freezes
from seal_full_snapshot import sha256, validate_snapshot

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--count', type=int, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'darwin':
        raise RuntimeError('Native filesystem compression requires macOS')
    _, freeze, _ = validate_freezes(ROOT)
    low, high = freeze['final_pool']
    if not 1 <= args.count <= high-low+1:
        raise ValueError('Prefix outside frozen final pool')
    output = ROOT/'outputs/park_revive_full_v3/main'
    report = args.report.resolve()
    if report.exists() or any(report.is_relative_to(p.resolve()) for p in
                             (ROOT/'outputs', ROOT/'paper', ROOT/'data')):
        raise ValueError('New report must be outside evidence/manuscript/data')
    seeds = list(range(low, low+args.count))
    verifier = ROOT/'scripts/verify_full_strategy.py'
    before = validate_snapshot(output, seeds, freeze['scientific_source_hash'],
                               freeze['final_config'], verifier)
    fingerprints = {str(r['seed']): r['input_digest'] for r in before}
    free_before = shutil.disk_usage(output).free
    changed = []
    candidates = 0
    with tempfile.TemporaryDirectory(prefix='.parquet-compression-', dir=output.parent) as temporary:
        for seed in seeds:
            directory = output/f'seed_{seed}'
            if directory.is_symlink() or not directory.resolve().is_relative_to(output.resolve()):
                raise ValueError('Market directory leaves verified stage')
            for path in sorted(directory.rglob('*.parquet')):
                if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()):
                    raise ValueError('Parquet path leaves verified market')
                if path.stat().st_size < 16384 or getattr(path.stat(), 'st_flags', 0) & 32:
                    continue
                candidates += 1
                row = compress_file(path, Path(temporary))
                if row:
                    row['path'] = str(path.relative_to(ROOT))
                    changed.append(row)
            print(f'completed native Parquet compression seed={seed}', flush=True)
    after = validate_snapshot(output, seeds, freeze['scientific_source_hash'],
                              freeze['final_config'], verifier)
    if fingerprints != {str(r['seed']): r['input_digest'] for r in after}:
        raise ValueError('Scientific bytes changed during native compression')
    validate_freezes(ROOT)
    result = dict(complete=True, applied=True, captured_at=datetime.now(timezone.utc).isoformat(),
                  stage='main', seeds=seeds, source_sha256=sha256(Path(__file__)),
                  copier_source_sha256=sha256(ROOT/'scripts/compress_verified_json_storage.py'),
                  scientific_source_hash=freeze['scientific_source_hash'], input_digests=fingerprints,
                  all_current_input_digests_preserved=True, candidate_files=candidates,
                  changed_files=changed,
                  allocated_bytes_reduction=sum(r['allocated_before']-r['allocated_after'] for r in changed),
                  filesystem_free_before=free_before, filesystem_free_after=shutil.disk_usage(output).free,
                  scope='Native filesystem compression only, using the existing checked atomic copier. '
                  'All logical Parquet bytes and replay input digests preserved. Only the explicit completed, '
                  'independently replayed prefix is touched. No active market, empirical input, statistical '
                  'setting, new market or arithmetic replay. Allocation savings do not guarantee future capacity.')
    report.parent.mkdir(parents=True, exist_ok=True)
    with report.open('x') as stream:
        stream.write(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in
                      ('seeds','input_digests','changed_files')}, indent=2))


if __name__ == '__main__':
    main()
