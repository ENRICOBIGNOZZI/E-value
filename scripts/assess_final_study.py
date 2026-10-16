#!/usr/bin/env python3
"""Apply the frozen economic analysis to a sealed complete final sample.

An explicit pilot diagnostic mode exercises the analysis without promoting
pilot paths to final evidence. This script never simulates or selects markets.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

from scipy.stats import t

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def calculate(rows, seeds, plan):
    """Paired market-level contrasts; every method/outcome must be present."""
    expected = {(seed, method) for seed in seeds for method in plan['methods']}
    keyed = {(int(row['seed']), row['method']): row for row in rows}
    if len(rows) != len(keyed) or set(keyed) != expected:
        raise ValueError('Missing, extra or duplicate market/method outcome')
    metric = plan['primary_metric']
    for row in rows:
        if not math.isfinite(float(row[metric])):
            raise ValueError('Every requested primary utility outcome must be finite')
    level = plan['confidence_level']
    contrasts = []
    for reference in plan['references']:
        differences = [float(keyed[seed, plan['tested_method']][metric])
                       - float(keyed[seed, reference][metric]) for seed in seeds]
        n = len(differences)
        if n < 2:
            raise ValueError('At least two independent markets are required')
        mean = math.fsum(differences) / n
        se = statistics.stdev(differences) / math.sqrt(n)
        radius = float(t.ppf((1 + level)/2, n - 1)) * se
        contrasts.append(dict(reference=reference, n=n, mean_difference=mean,
            standard_error=se, ci_low=mean-radius, ci_high=mean+radius,
            zero_observed_standard_error=(se == 0),
            role='primary' if reference == plan['primary_reference'] else 'secondary'))
    return contrasts


def assess(snapshot, plan_path, pilot_diagnostic=False):
    plan = json.loads(plan_path.read_text())
    if plan['analysis_source_sha256'] != sha256(Path(__file__)):
        raise ValueError('Analysis code differs from its pre-final freeze')
    freeze_path = ROOT / plan['scientific_protocol']
    if sha256(freeze_path) != plan['scientific_protocol_sha256']:
        raise ValueError('Scientific protocol differs from the analysis freeze')
    freeze = json.loads(freeze_path.read_text())
    seal_path = snapshot / 'snapshot_seal.json'
    seal = json.loads(seal_path.read_text())
    seeds = seal['seeds']
    if pilot_diagnostic:
        low, high = freeze['pilot_pool']
        if (seal['kind'] not in ('interim_pilot', 'complete_pilot')
                or seal['stage'] != 'pilot' or not seeds
                or seeds != list(range(low, low+len(seeds))) or seeds[-1] > high):
            raise ValueError('Diagnostic mode requires an explicit frozen pilot prefix')
        expected_config = freeze['pilot_config']
    else:
        if (seal['kind'] != 'final' or seal['stage'] != 'main'
                or seeds != plan['final_seeds']):
            raise ValueError('Final assessment requires all 500 frozen final markets')
        expected_config = freeze['final_config']
    if (seal.get('complete') is not True
            or seal['source_hash'] != freeze['scientific_source_hash']
            or seal['config_hash'] != canonical_hash(expected_config)
            or seal['protocol_freeze_sha256'] != plan['scientific_protocol_sha256']):
        raise ValueError('Snapshot does not match the frozen scientific stage')
    for name, expected in seal['files_sha256'].items():
        if sha256(snapshot / name) != expected:
            raise ValueError(f'Sealed report artifact changed: {name}')
    with (snapshot / 'metrics_by_seed.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    contrasts = calculate(rows, seeds, plan)
    primary = next(r for r in contrasts if r['role'] == 'primary')
    return dict(complete=True,
        kind='pilot_diagnostic' if pilot_diagnostic else 'complete_final_assessment',
        markets=len(seeds), seeds=seeds, metric=plan['primary_metric'],
        tested_method=plan['tested_method'], primary=primary, all_contrasts=contrasts,
        confidence_level=plan['confidence_level'],
        analysis_plan_sha256=sha256(plan_path), snapshot_seal_sha256=sha256(seal_path),
        limits=plan['interpretation_limits'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--plan', type=Path, default=ROOT/'reports/final_analysis_plan.json')
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--pilot-diagnostic', action='store_true')
    args = parser.parse_args()
    if args.report.exists():
        raise FileExistsError('Refusing to overwrite an existing assessment')
    result = assess(args.snapshot, args.plan, args.pilot_diagnostic)
    args.report.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('seeds','all_contrasts')},indent=2))
