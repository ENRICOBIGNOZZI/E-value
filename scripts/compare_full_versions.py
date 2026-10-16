#!/usr/bin/env python3
"""Compare retained economic/statistical artifact bytes across financial versions.

Only sealed blocks are compared. Root aggregates require both seeds complete.
Source/status/runtime/checkpoint/recovery metadata are deliberately separate.
This is a cross-version equality audit, not another arithmetic replay or proof
of optimizer optimality, type-I error, or independent market replication.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_DATA = (
    'feature_library.json', 'daily_ledger.parquet',
    'comparison_events.parquet', 'metrics_by_seed.csv', 'decisions.json',
    'deployments.json', 'economic_opportunities.json', 'opportunity_registry.json',
    'terminal_adjudication.json', 'terminal_ghost_order.json', 'terminal_ghosts.npz',
)
OPTIONAL_ROOT = {'terminal_adjudication.json', 'terminal_ghost_order.json', 'terminal_ghosts.npz'}
BLOCK_DATA = (
    'daily_ledger.parquet', 'comparison_events.parquet', 'comparison_order.json',
    'ghost_order.json', 'shortlists.json', 'closed_episodes.json', 'decisions.json',
    'deployments.json',
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare_seed(old, new):
    statuses = [json.loads((directory/'status.json').read_text()) for directory in (old,new)]
    if statuses[0]['seed'] != statuses[1]['seed']:
        raise ValueError('Different market seeds')
    blocks = min(status['completed_blocks'] for status in statuses)
    both_complete = all(status.get('complete') for status in statuses)
    configs = [json.loads((directory/'config_frozen.json').read_text()) for directory in (old,new)]
    config_differences = [key for key in sorted(set(configs[0]) | set(configs[1]))
                          if key != 'label' and (key not in configs[0] or key not in configs[1]
                                                or configs[0][key] != configs[1][key])]
    names = list(ROOT_DATA) if both_complete else ['feature_library.json']
    for block in range(1, blocks+1):
        relative = Path(f'block_{block:02d}')
        names.extend(str(relative/name) for name in BLOCK_DATA)
        old_npz = {p.name for p in (old/relative).glob('*.npz')}
        new_npz = {p.name for p in (new/relative).glob('*.npz')}
        names.extend(str(relative/name) for name in sorted(old_npz | new_npz))
    files = {}; differences = []; both_absent_optional = []; bytes_per_version = 0
    for name in names:
        a = old/name; b = new/name
        hashes = [digest(path) if path.exists() else None for path in (a,b)]
        if hashes == [None,None] and name in OPTIONAL_ROOT:
            both_absent_optional.append(name)
            continue
        equal = hashes[0] is not None and hashes[0] == hashes[1]
        files[name] = dict(old_sha256=hashes[0], new_sha256=hashes[1], bitwise_identical=equal)
        if equal:
            bytes_per_version += a.stat().st_size
        else:
            differences.append(name)
    return dict(seed=statuses[0]['seed'], old_source_hash=statuses[0]['source_hash'],
        new_source_hash=statuses[1]['source_hash'], complete_in_both=both_complete,
        configuration_fields_equal_except_label=not config_differences,
        differing_configuration_fields=config_differences,
        configuration_labels=[config.get('label') for config in configs],
        configuration_file_sha256=[digest(directory/'config_frozen.json') for directory in (old,new)],
        optional_terminal_files_absent_in_both=both_absent_optional,
        sealed_blocks_compared=blocks, old_completed_blocks=statuses[0]['completed_blocks'],
        new_completed_blocks=statuses[1]['completed_blocks'],
        root_aggregates_compared=both_complete, files_compared=len(files),
        equal_artifact_bytes_per_version=bytes_per_version,
        all_compared_artifacts_bitwise_identical=not differences,
        all_scientific_data_equal=not differences and not config_differences,
        differences=differences, files=files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--old', type=Path, default=ROOT/'outputs/park_revive_full_v2/pilot')
    parser.add_argument('--new', type=Path, default=ROOT/'outputs/park_revive_full_v3/pilot')
    parser.add_argument('--seeds', type=int, nargs='+', default=list(range(50001,50021)))
    parser.add_argument('--destination', type=Path, default=ROOT/'reports/full_v3_results/cross_version_equality.json')
    args = parser.parse_args(); comparisons = []; unavailable = []
    for seed in sorted(set(args.seeds)):
        old = args.old/f'seed_{seed}'; new = args.new/f'seed_{seed}'
        if not all((p/'status.json').exists() for p in (old,new)):
            unavailable.append(seed); continue
        result = compare_seed(old,new); comparisons.append(result)
        print(json.dumps({k:v for k,v in result.items() if k != 'files'}), flush=True)
    report = dict(captured_at=datetime.now().astimezone().isoformat(),
        script_sha256=digest(Path(__file__)), requested_seeds=sorted(set(args.seeds)),
        unavailable_seeds=unavailable,
        complete_markets_compared=sum(c['complete_in_both'] for c in comparisons),
        sealed_blocks_compared=sum(c['sealed_blocks_compared'] for c in comparisons),
        artifact_file_pairs_compared=sum(c['files_compared'] for c in comparisons),
        equal_artifact_bytes_per_version=sum(c['equal_artifact_bytes_per_version'] for c in comparisons),
        all_compared_artifacts_bitwise_identical=bool(comparisons) and all(c['all_compared_artifacts_bitwise_identical'] for c in comparisons),
        configuration_fields_equal_except_labels=all(c['configuration_fields_equal_except_label'] for c in comparisons),
        all_scientific_data_equal=bool(comparisons) and all(c['all_scientific_data_equal'] for c in comparisons),
        comparisons=comparisons,
        exclusions=['Source manifests and version metadata', 'Runtime measurements',
                    'The version label in config_frozen.json; every other parsed field is compared separately',
                    'Resumable/regenerable checkpoints and their compaction records',
                    'Numerical-recovery diagnostics, which exist only in v3',
                    'Unsealed blocks and root aggregates of an incomplete seed'],
        scope='Economic/statistical artifact byte equality on the same seeds. Not another arithmetic replay, independent replication, optimizer proof or inference guarantee. Incomplete seed prefixes are explicitly separate.')
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('comparisons','exclusions')},indent=2),flush=True)
    if not report['all_scientific_data_equal'] or unavailable:
        raise SystemExit('Cross-version differences or unavailable requested seeds are retained in the report')


if __name__ == '__main__':
    main()
