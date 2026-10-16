#!/usr/bin/env python3
"""Independently recalculate market-level summaries from original seed CSVs.

Uses csv/statistics rather than the reporting builder's dataframe aggregation.
This checks reporting arithmetic; it adds no simulated markets or score replay.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

from scipy.stats import t


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def numeric(value):
    if value in ('True', 'False'):
        return float(value == 'True')
    return float(value) if value not in ('', None) else math.nan


def audit(snapshot, output):
    seal = json.loads((snapshot / 'snapshot_seal.json').read_text())
    if seal.get('complete') is not True:
        raise ValueError('Incomplete snapshot seal')
    for name, digest in seal['files_sha256'].items():
        if sha256(snapshot / name) != digest:
            raise ValueError(f'Changed report artifact: {name}')
    raw = []
    for seed in seal['seeds']:
        raw.extend(read_csv(output / f'seed_{seed}' / 'metrics_by_seed.csv'))
    keyed = {(int(r['seed']), r['method']): r for r in raw}
    if len(keyed) != len(raw):
        raise ValueError('Duplicate source metric row')
    checks = 0
    maximum = 0.

    def check(observed, expected):
        nonlocal checks, maximum
        observed, expected = float(observed), float(expected)
        if math.isnan(observed) and math.isnan(expected):
            checks += 1
            return
        if not math.isclose(observed, expected, rel_tol=2e-10, abs_tol=2e-12):
            raise ArithmeticError((observed, expected))
        checks += 1
        maximum = max(maximum, abs(observed - expected))

    reported = read_csv(snapshot / 'metrics_by_seed.csv')
    if {(int(r['seed']), r['method']) for r in reported} != set(keyed) or len(reported) != len(raw):
        raise ValueError('Reported market/method membership differs from original CSVs')
    for row in reported:
        original = keyed[int(row['seed']), row['method']]
        if set(row) != set(original):
            raise ValueError('Reported metric columns differ from original CSVs')
        for name in row:
            if name != 'method':
                check(numeric(row[name]), numeric(original[name]))

    def summary(values):
        values = [v for v in values if not math.isnan(v)]
        n = len(values)
        mean = math.fsum(values) / n if n else math.nan
        se = statistics.stdev(values) / math.sqrt(n) if n > 1 else math.nan
        radius = float(t.ppf(.975, n - 1)) * se if n > 1 else math.nan
        return dict(n=n, mean=mean, median=statistics.median(values) if n else math.nan,
                    standard_error=se, ci_low=mean-radius, ci_high=mean+radius)

    for row in read_csv(snapshot / 'method_summary.csv'):
        values = [numeric(r[row['metric']]) for r in raw if r['method'] == row['method']]
        for name, value in summary(values).items():
            check(numeric(row[name]), value)
    for row in read_csv(snapshot / 'paired_comparisons.csv'):
        differences = [numeric(keyed[seed, 'Tail'][row['metric']])
                       - numeric(keyed[seed, row['reference']][row['metric']])
                       for seed in seal['seeds']]
        values = summary(differences)
        values['mean_difference'] = values.pop('mean')
        values.pop('median')
        for name, value in values.items():
            check(numeric(row[name]), value)
    for row in read_csv(snapshot / 'market_move_incidence.csv'):
        values = [numeric(r[row['endpoint']]) > 0 for r in raw if r['method'] == row['method']]
        n, successes = len(values), sum(values)
        rate = successes / n
        z = 1.959963984540054
        denominator = 1 + z*z/n
        center = (rate + z*z/(2*n)) / denominator
        radius = z * math.sqrt(rate*(1-rate)/n + z*z/(4*n*n)) / denominator
        expected = dict(seeds=n, markets_with_move=successes, fraction=rate,
                        wilson_low=max(0., center-radius), wilson_high=min(1., center+radius))
        for name, value in expected.items():
            check(numeric(row[name]), value)
    return dict(complete=True, snapshot=str(snapshot), kind=seal['kind'], seeds=seal['seeds'],
                scalar_reporting_checks=checks, maximum_absolute_error=maximum,
                all_sealed_report_file_hashes_match=True,
                snapshot_seal_sha256=sha256(snapshot / 'snapshot_seal.json'),
                audit_source_sha256=sha256(Path(__file__)),
                scope='Original seed metrics, all method means/medians/SE/Student intervals, all paired contrasts and market-level Wilson incidence. No new markets, optimization or pathwise score replay. Event-rate and deployment tables are covered by seal hashes, not independently recalculated here.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.snapshot, args.output)
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'seeds'}, indent=2))
