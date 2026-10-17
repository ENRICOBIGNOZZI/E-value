"""Format the complete sealed pilot in a NEW directory; never write the paper."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from build_full_results import generate_tex
from continue_full_study import validate_freezes
from seal_full_snapshot import sha256, validate_snapshot


def reproduce(destination):
    snapshot = ROOT/'reports/full_v3_snapshots/pilot_100'
    output = ROOT/'outputs/park_revive_full_v3/pilot'
    if destination.exists() or any(destination.resolve().is_relative_to(p.resolve())
                                  for p in (snapshot, output, ROOT/'paper')):
        raise ValueError('A new destination outside evidence and manuscript is required')
    _, freeze, _ = validate_freezes(ROOT)
    seeds = list(range(50001, 50101))
    seal_path = snapshot/'snapshot_seal.json'
    seal = json.loads(seal_path.read_text())
    if not (seal['complete'] and seal['kind'] == 'complete_pilot' and seal['seeds'] == seeds):
        raise ValueError('Complete hundred-market pilot required')
    seal_hash = sha256(seal_path)
    audit_paths = [snapshot.parent/'pilot_100_numeric_audit.json',
                   snapshot.parent/'pilot_100_event_adjudication_audit.json']
    for path, source in zip(audit_paths, ('audit_full_snapshot.py', 'audit_full_event_adjudication.py')):
        audit = json.loads(path.read_text())
        if not (audit['complete'] and audit['kind'] == 'complete_pilot' and audit['seeds'] == seeds
                and audit['snapshot_seal_sha256'] == seal_hash
                and audit['audit_source_sha256'] == sha256(ROOT/'scripts'/source)):
            raise ValueError('Missing or stale complete-pilot audit')
    inputs = {str(p.relative_to(ROOT)): sha256(p) for p in [seal_path, *audit_paths]}

    def check():
        if any(sha256(ROOT/name) != value for name, value in inputs.items()):
            raise ValueError('Audit/seal bytes changed')
        for name, value in seal['files_sha256'].items():
            path = (snapshot/name).resolve()
            if not path.is_relative_to(snapshot.resolve()) or sha256(path) != value:
                raise ValueError('Sealed input changed')
        rows = validate_snapshot(output, seeds, freeze['scientific_source_hash'],
                                 freeze['pilot_config'], ROOT/'scripts/verify_full_strategy.py')
        if {str(r['seed']): r['input_digest'] for r in rows} != seal['input_digests']:
            raise ValueError('Raw replay differs from complete-pilot seal')
        return rows

    before = check()
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.pilot100-', dir=destination.parent))
    try:
        frames = [pd.read_csv(snapshot/name) for name in
                  ('metrics_by_seed.csv', 'decisions.csv', 'deployments.csv', 'opportunity_rates.csv')]
        generate_tex(snapshot, staging, *frames, 100, 0, 100, freeze['pilot_config'])
        if check() != before:
            raise ValueError('Replay records changed while formatting')
        record = dict(complete=True, kind='complete_pilot_manuscript_packet', seeds=seeds,
            snapshot_seal_sha256=seal_hash, inputs_sha256=inputs,
            sources_sha256={str(p.relative_to(ROOT)): sha256(p) for p in
                           (Path(__file__), ROOT/'scripts/build_full_results.py')},
            outputs_sha256={str(p.relative_to(staging)): sha256(p)
                            for p in staging.rglob('*') if p.is_file()},
            scope='Formatting of existing complete pilot only. No new markets, numerical replay counts, final results or direct manuscript writes.')
        (staging/'verification.json').write_text(json.dumps(record, indent=2)+'\n')
        staging.rename(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, required=True)
    reproduce(parser.parse_args().destination)
