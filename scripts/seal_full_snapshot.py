#!/usr/bin/env python3
"""Seal a complete, replay-verified financial snapshot without changing the paper.

The pilot may use an explicitly named prefix. The final study requires its
entire frozen pool. No missing or failed requested market can be dropped.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from build_full_results import summarize
from verify_full_strategy import input_digest

ROOT = Path(__file__).resolve().parents[1]
METHODS = {'All Signals', 'Greedy', 'HAC', 'Catoni', 'Tail', 'Oracle'}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def requested_seeds(freeze, stage, count=None):
    low, high = freeze['pilot_pool' if stage == 'pilot' else 'final_pool']
    maximum = high - low + 1
    count = maximum if count is None else count
    if not 1 <= count <= maximum:
        raise ValueError('Count outside the frozen pool')
    if stage == 'main' and count != maximum:
        raise ValueError('Final reporting requires the entire frozen final pool')
    return list(range(low, low + count))


def validate_snapshot(output, seeds, expected_source, expected_config, verifier):
    """Check exact requested membership and current replay evidence, read-only."""
    import pandas as pd

    seeds = list(seeds)
    if not seeds or len(seeds) != len(set(seeds)):
        raise ValueError('Requested seeds must be nonempty and unique')
    records = json.loads((output / 'arithmetic_verification.json').read_text())
    audits = {}
    for row in records:
        if row['seed'] in audits:
            raise ValueError('Duplicate replay record')
        audits[row['seed']] = row
    verifier_hash = sha256(verifier)
    config_hash = canonical_hash(expected_config)
    selected = []
    for seed in seeds:
        directory = output / f'seed_{seed}'
        status_path = directory / 'status.json'
        if not status_path.exists():
            raise ValueError(f'Requested market has not finished: {seed}')
        status = json.loads(status_path.read_text())
        blocks = expected_config['years'] - 1
        if (status.get('seed') != seed or status.get('complete') is not True
                or status.get('completed_blocks') != blocks
                or status.get('total_blocks') != blocks):
            raise ValueError(f'Requested market is incomplete: {seed}')
        if (directory / 'execution_error.txt').exists():
            raise ValueError(f'Unresolved execution error: {seed}')
        if status.get('source_hash') != expected_source:
            raise ValueError(f'Wrong scientific source: {seed}')
        source = json.loads((directory / 'source_manifest.json').read_text())
        if canonical_hash(source) != expected_source:
            raise ValueError(f'Source manifest does not match its fingerprint: {seed}')
        config = json.loads((directory / 'config_frozen.json').read_text())
        if config != expected_config:
            raise ValueError(f'Configuration differs from the frozen stage: {seed}')
        record = audits.get(seed, {})
        if (record.get('complete') is not True or record.get('checks', 0) <= 0
                or record.get('scientific_source_hash') != expected_source
                or record.get('config_hash') != config_hash
                or record.get('verifier_sha256') != verifier_hash):
            raise ValueError(f'Independent replay is missing or stale: {seed}')
        if record.get('input_digest') != input_digest(directory):
            raise ValueError(f'Artifacts changed after independent replay: {seed}')
        metrics = pd.read_csv(directory / 'metrics_by_seed.csv')
        if (len(metrics) != len(METHODS) or set(metrics.method) != METHODS
                or not metrics.seed.eq(seed).all()):
            raise ValueError(f'Incomplete or duplicated method/market metrics: {seed}')
        selected.append(record)
    return selected


def seal(output, destination, freeze_path, stage, count=None):
    """Validate before writing; publish a new directory only after rechecking."""
    if destination.exists():
        raise FileExistsError(f'Refusing to overwrite a sealed snapshot: {destination}')
    freeze = json.loads(freeze_path.read_text())
    seeds = requested_seeds(freeze, stage, count)
    config = freeze['pilot_config' if stage == 'pilot' else 'final_config']
    source_hash = freeze['scientific_source_hash']
    verifier = Path(__file__).with_name('verify_full_strategy.py')
    records = validate_snapshot(output, seeds, source_hash, config, verifier)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.snapshot-', dir=destination.parent))
    try:
        manifest = summarize(output, temporary, seeds=seeds, details=temporary / 'details')
        if (sorted(manifest['seeds']) != seeds or manifest['incomplete']
                or manifest['completed_seeds_with_arithmetic_audit'] != len(seeds)):
            raise ValueError('Summary membership differs from verified snapshot')
        # The older summarizer copies the whole accumulating replay ledger.
        # This sealed artifact deliberately retains only the requested markets.
        (temporary / 'arithmetic_verification.json').write_text(
            json.dumps(records, indent=2) + '\n')
        after = validate_snapshot(output, seeds, source_hash, config, verifier)
        if records != after:
            raise ValueError('Replay evidence changed while building the snapshot')
        full_count = len(requested_seeds(freeze, stage))
        kind = 'final' if stage == 'main' else (
            'complete_pilot' if len(seeds) == full_count else 'interim_pilot')
        seal_record = dict(
            complete=True, kind=kind, stage=stage, seeds=seeds,
            frozen_pool_size=full_count, source_hash=source_hash,
            config_hash=canonical_hash(config), protocol_freeze_sha256=sha256(freeze_path),
            scalar_replay_checks=sum(r['checks'] for r in records),
            ghost_pairs_checked=sum(r['ghost_pairs_checked'] for r in records),
            input_digests={str(r['seed']): r['input_digest'] for r in records},
            reporting_source_sha256={p.name: sha256(p) for p in (
                Path(__file__), Path(__file__).with_name('build_full_results.py'), verifier)},
            files_sha256={str(p.relative_to(temporary)): sha256(p)
                          for p in sorted(temporary.rglob('*')) if p.is_file()},
            limits=[
                'Completeness and arithmetic consistency do not establish scientific superiority.',
                'Interim pilot snapshots do not complete either the pilot or the final pool.',
                'Same-seed version replays are not independent market replications.',
                'Event populations are method-specific; intervals are pointwise Monte Carlo summaries.',
                'The current manuscript is unchanged by sealing this directory.'])
        (temporary / 'snapshot_seal.json').write_text(json.dumps(seal_record, indent=2) + '\n')
        temporary.rename(destination)
        return {k: v for k, v in seal_record.items()
                if k not in ('files_sha256', 'input_digests', 'reporting_source_sha256')}
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('pilot', 'main'))
    parser.add_argument('--count', type=int)
    parser.add_argument('--destination', type=Path)
    args = parser.parse_args()
    freeze = ROOT / 'reports/full_v3_results/protocol_frozen.json'
    seeds = requested_seeds(json.loads(freeze.read_text()), args.stage, args.count)
    destination = args.destination or ROOT / 'reports/full_v3_snapshots' / (
        f'{args.stage}_{len(seeds):03d}')
    print(json.dumps(seal(ROOT / 'outputs/park_revive_full_v3' / args.stage,
                          destination, freeze, args.stage, args.count), indent=2))


if __name__ == '__main__':
    main()
