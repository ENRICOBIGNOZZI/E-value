#!/usr/bin/env python3
"""Recalculate sealed event cohorts and deployment summaries from seed JSONs.

Uses csv/counters rather than the report builder's dataframe aggregation.
No simulator, selector, optimizer or original report builder is imported.
This is a reporting audit, not a new market or a replay of event adjudication.
"""
import argparse
import ast
from collections import Counter, defaultdict
import csv
from functools import lru_cache
import gzip
import hashlib
import json
import math
from pathlib import Path

METHODS = ('Greedy', 'HAC', 'Catoni', 'Tail')
ALL_METHODS = ('All Signals', *METHODS, 'Oracle')
LIFECYCLES = ('ALL', 'ENTRY', 'PARK', 'REVIVE', 'SWAP')
KINDS = ('ALL', 'inception_positive', 'sign_change_positive')
FOLLOWUP = (1, 3, 5)


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def input_digest(directory):
    return canonical_hash({str(p.relative_to(directory)): sha256(p)
                           for p in sorted(directory.rglob('*'))
                           if p.is_file() and not p.name.startswith('checkpoint')})


def read_rows(path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt', newline='') as stream:
        yield from csv.DictReader(stream)


def audit(snapshot, output):
    snapshot, output = Path(snapshot), Path(output)
    seal_path = snapshot/'snapshot_seal.json'
    seal = json.loads(seal_path.read_text())
    seeds = seal['seeds']
    if seal.get('complete') is not True or not seeds or len(seeds) != len(set(seeds)):
        raise ValueError('Incomplete seal or duplicate market membership')
    if seal['kind'] == 'final' and len(seeds) != seal['frozen_pool_size']:
        raise ValueError('Partial final snapshot')
    bound_files = {seal_path: sha256(seal_path)}
    for name, digest in seal['files_sha256'].items():
        path = snapshot/name
        if sha256(path) != digest:
            raise ValueError(f'Changed sealed artifact: {name}')
        bound_files[path] = digest
    config = json.loads((snapshot/'config_frozen.json').read_text())
    if canonical_hash(config) != seal['config_hash']:
        raise ValueError('Sealed configuration fingerprint mismatch')
    block, horizon = config['block'], config['block']*config['years']
    tolerance = config['economic_tolerance']
    replay = json.loads((snapshot/'arithmetic_verification.json').read_text())
    replay_by_seed = {r['seed']: r for r in replay}
    if len(replay_by_seed) != len(replay):
        raise ValueError('Duplicate replay record')
    counters = Counter()
    maximum_error = 0.

    def require(condition, message):
        if not condition:
            raise ValueError(message)
        counters['structural_checks'] += 1

    def number(observed, expected, label):
        nonlocal maximum_error
        a = math.nan if observed in ('', None) else float(observed)
        b = math.nan if expected is None else float(expected)
        if math.isnan(a) and math.isnan(b):
            counters['numeric_checks'] += 1
            return
        if not (math.isfinite(a) and math.isfinite(b) and
                math.isclose(a, b, rel_tol=2e-10, abs_tol=2e-12)):
            raise ArithmeticError(f'{label}: {a} != {b}')
        maximum_error = max(maximum_error, abs(a-b))
        counters['numeric_checks'] += 1

    def record(observed, expected, label):
        require(set(observed) == set(expected), f'{label}: field membership differs')
        for field, value in expected.items():
            actual = observed[field]
            if isinstance(value, bool):
                require(actual == str(value), f'{label}: boolean {field} differs')
            elif isinstance(value, list):
                require(ast.literal_eval(actual) == value, f'{label}: list {field} differs')
            elif isinstance(value, str):
                require(actual == value, f'{label}: text {field} differs')
            else:
                number(actual, value, f'{label}/{field}')

    keys = [(m, l, k, y) for m in METHODS for l in LIFECYCLES
            for k in KINDS for y in FOLLOWUP]
    counts = {key: Counter() for key in keys}
    contributors = defaultdict(set)
    per_seed = defaultdict(Counter)
    original_counts = {}
    deployments_by_method = defaultdict(list)
    maximum_gain_identity_residual = 0.

    @lru_cache(maxsize=2)
    def source_rows(seed, filename):
        path = output/f'seed_{seed}'/filename
        digest = sha256(path)
        require(path not in bound_files or bound_files[path] == digest,
                f'Source JSON changed during event audit: {seed}/{filename}')
        bound_files.setdefault(path, digest)
        return json.loads(path.read_text())

    for seed in seeds:
        directory = output/f'seed_{seed}'
        status = json.loads((directory/'status.json').read_text())
        require(status['seed'] == seed and status['complete'] is True and
                status['completed_blocks'] == status['total_blocks'] == config['years']-1,
                f'Incomplete source market: {seed}')
        require(status['source_hash'] == seal['source_hash'] and
                canonical_hash(json.loads((directory/'source_manifest.json').read_text())) == seal['source_hash'],
                f'Wrong source fingerprint: {seed}')
        require(json.loads((directory/'config_frozen.json').read_text()) == config,
                f'Wrong configuration: {seed}')
        digest = input_digest(directory)
        row = replay_by_seed.get(seed, {})
        require(row.get('complete') is True and row.get('input_digest') == digest == seal['input_digests'][str(seed)] and
                row.get('scientific_source_hash') == seal['source_hash'] and
                row.get('config_hash') == seal['config_hash'] and
                row.get('verifier_sha256') == seal['reporting_source_sha256']['verify_full_strategy.py'],
                f'Stale or missing independent replay: {seed}')
        registry = source_rows(seed, 'opportunity_registry.json')
        by_id = {(r['method'], r['comparison_id']): r for r in registry}
        require(len(by_id) == len(registry), f'Duplicate comparison registry: {seed}')
        events = source_rows(seed, 'economic_opportunities.json')
        stable_by_id = Counter()
        for event in events:
            m, life, kind = event['method'], event['lifecycle'], event['event_kind']
            require(event['seed'] == seed and m in METHODS and life in LIFECYCLES[1:] and kind in KINDS[1:],
                    f'Wrong event population: {seed}')
            original = by_id.get((m, event['comparison_id']))
            require(original is not None and all(event[k] == original[k] for k in original
                    if k not in ('stable_events', 'unstable_runs')), f'Event/registry metadata mismatch: {seed}')
            onset, confirmation, termination = event['onset_day'], event['confirmation_day'], event['termination_day']
            require(event['start'] < onset <= termination <= horizon and
                    confirmation == onset+block and all(d % block == 0 for d in (onset, confirmation, termination)),
                    f'Invalid stable-event calendar: {seed}')
            for flag, day, delay in [('selected', 'selected_day', 'selection_delay_days'),
                                     ('criterion_detected', 'criterion_day', 'criterion_delay_days')]:
                require(event[flag] == (event[day] >= 0) and
                        event[delay] == (event[day]-onset if event[flag] else -1) and
                        (not event[flag] or onset <= event[day] <= termination),
                        f'Invalid event delay: {seed}')
            stable_by_id[m, event['comparison_id']] += 1
            for lifecycle in ('ALL', life):
                for event_kind in ('ALL', kind):
                    for years in FOLLOWUP:
                        key = (m, lifecycle, event_kind, years)
                        counts[key]['stable_events'] += 1
                        window = years*block
                        if onset+window > horizon:
                            continue
                        target = per_seed[key+(seed,)]
                        for name, value in [('eligible_events', 1),
                            ('selected_within', int(event['selected_day'] >= 0 and event['selected_day']-onset <= window)),
                            ('criterion_within', int(event['criterion_day'] >= 0 and event['criterion_day']-onset <= window))]:
                            counts[key][name] += value
                            target[name] += value
                        contributors[key].add(seed)
        for registry_row in registry:
            require(registry_row['seed'] == seed and registry_row['method'] in METHODS and
                    registry_row['stable_events'] == stable_by_id[registry_row['method'], registry_row['comparison_id']] and
                    registry_row['unstable_runs'] >= 0, f'Invalid registry event count: {seed}')
        require(status['stable_opportunities'] == len(events) and
                status['unstable_runs'] == sum(r['unstable_runs'] for r in registry),
                f'Wrong status event totals: {seed}')
        decisions = source_rows(seed, 'decisions.json')
        decision_key = lambda r: (r['method'], r['day'], r['comparison_id'])
        selected = {decision_key(r): r for r in decisions}
        require(len(selected) == len(decisions) == len({(r['method'], r['day']) for r in decisions}),
                f'Duplicate decision or multiple annual choices: {seed}')
        for decision in decisions:
            require(decision['seed'] == seed and decision['method'] in METHODS and
                    2*block <= decision['day'] <= horizon and decision['day'] % block == 0 and
                    decision['executed'] == (decision['day'] < horizon), f'Invalid decision calendar: {seed}')
            original = by_id.get((decision['method'], decision['comparison_id']))
            require(original is not None and
                    decision['support_before'] == original['reference_support'] and
                    decision['support_after'] == original['candidate_support'] and
                    all(decision[k] == original[k] for k in ('move','lifecycle','added','removed')),
                    f'Decision/registry policy metadata differs: {seed}')
        for event in events:
            if event['selected']:
                require((event['method'], event['selected_day'], event['comparison_id']) in selected,
                        f'Selected event has no recorded decision: {seed}')
        deployed = source_rows(seed, 'deployments.json')
        require({decision_key(r) for r in deployed} == {k for k, r in selected.items() if r['executed']} and
                len({decision_key(r) for r in deployed}) == len(deployed),
                f'Executed/terminal deployment membership differs: {seed}')
        for deployment in deployed:
            decision = selected[decision_key(deployment)]
            require(all(deployment[k] == v for k, v in decision.items()) and
                    deployment['deployment_day'] == decision['day'] and deployment['actual_entry_cost'] >= 0 and
                    all(math.isfinite(deployment[k]) for k in
                        ('conditional_gain', 'new_conditional_utility', 'old_conditional_utility', 'actual_entry_cost')),
                    f'Invalid deployment record: {seed}')
            residual = abs(deployment['conditional_gain'] -
                           (deployment['new_conditional_utility']-deployment['old_conditional_utility']))
            require(residual <= tolerance, f'Inconsistent retained deployment gain: {seed}')
            maximum_gain_identity_residual = max(maximum_gain_identity_residual, residual)
            deployments_by_method[deployment['method']].append(deployment)
        metric_rows = list(read_rows(directory/'metrics_by_seed.csv'))
        metrics = {r['method']: r for r in metric_rows}
        require(len(metrics) == len(metric_rows) == len(ALL_METHODS) and set(metrics) == set(ALL_METHODS) and
                all(int(r['seed']) == seed for r in metric_rows), f'Invalid metric membership: {seed}')
        for method in METHODS:
            chosen = [r for r in decisions if r['method'] == method]
            executed = [r for r in deployed if r['method'] == method]
            for field, value in dict(moves=len(chosen), executed_moves=len(executed),
                economic_precision=sum(r['true_block_mean'] > tolerance for r in chosen)/len(chosen) if chosen else math.nan,
                deployment_positive_fraction=sum(r['conditional_gain'] > tolerance for r in executed)/len(executed) if executed else math.nan).items():
                number(metrics[method][field], value, f'{seed}/{method}/{field}')
        for filename, rows in [('economic_opportunities.json', events), ('opportunity_registry.json', registry),
                               ('decisions.json', decisions), ('deployments.json', deployed)]:
            original_counts[seed, filename] = len(rows)

    @lru_cache(maxsize=2)
    def indexed_source(seed, filename, identity):
        rows = source_rows(seed, filename)
        keyed = {tuple(r[k] for k in identity): r for r in rows}
        require(len(keyed) == len(rows), f'Duplicate source row: {seed}/{filename}')
        return keyed

    for filename, table, identity in [
        ('economic_opportunities.json', 'details/economic_opportunities.csv.gz', ('seed', 'method', 'comparison_id', 'event_index')),
        ('opportunity_registry.json', 'details/opportunity_registry.csv.gz', ('seed', 'method', 'comparison_id')),
        ('decisions.json', 'decisions.csv', ('seed', 'method', 'day', 'comparison_id')),
        ('deployments.json', 'deployments.csv', ('seed', 'method', 'day', 'comparison_id'))]:
        seen = set(); observed_counts = Counter()
        for row in read_rows(snapshot/table):
            seed = int(row['seed'])
            require(seed in seeds, f'Unexpected market in {table}')
            key = tuple(int(row[k]) if k in ('seed', 'day', 'event_index') else row[k] for k in identity)
            require(key not in seen, f'Duplicate report row in {table}')
            seen.add(key); observed_counts[seed] += 1
            original = indexed_source(seed, filename, identity).get(key)
            require(original is not None, f'Unknown report row in {table}')
            record(row, original, table)
        require(all(observed_counts[seed] == original_counts[seed, filename] for seed in seeds),
                f'Missing report membership in {table}')
        counters[f'{filename[:-5]}_rows'] = sum(observed_counts.values())

    def check_table(table, identity, expected):
        seen = set()
        for row in read_rows(snapshot/table):
            key = tuple(int(row[k]) if k in ('followup_years', 'seed') else row[k] for k in identity)
            require(key in expected and key not in seen, f'Wrong or duplicate cohort key in {table}')
            seen.add(key)
            require(set(row) == set(identity) | set(expected[key]), f'Wrong columns in {table}')
            for field, value in expected[key].items():
                number(row[field], value, f'{table}/{key}/{field}')
        require(seen == set(expected), f'Missing cohort rows in {table}')
        counters[f'{table[:-4]}_rows'] = len(seen)

    expected_rates = {}
    for key, values in counts.items():
        n = values['eligible_events']
        expected_rates[key] = dict(stable_events=values['stable_events'], eligible_events=n,
            selected_within=values['selected_within'], criterion_within=values['criterion_within'],
            selection_fraction=values['selected_within']/n if n else math.nan,
            criterion_fraction=values['criterion_within']/n if n else math.nan,
            contributing_seeds=len(contributors[key]))
    identity = ('method', 'lifecycle', 'event_kind', 'followup_years')
    check_table('opportunity_rates.csv', identity, expected_rates)
    check_table('opportunity_seed_counts.csv', identity+('seed',), dict(per_seed))
    # Recheck the report and the JSON files actually read, preventing a stale
    # success record if any input changes while this audit is running.
    require(all(input_digest(output/f'seed_{seed}') == seal['input_digests'][str(seed)] for seed in seeds),
            'Source data changed during event audit')
    require(all(sha256(p) == digest for p, digest in bound_files.items()), 'Inputs changed during event audit')
    summary = {}
    for method in METHODS:
        rows = deployments_by_method[method];n = len(rows)
        summary[method] = dict(executed=n,
            positive_gain_fraction=sum(r['conditional_gain'] > tolerance for r in rows)/n if n else None,
            mean_gain_basis_points=1e4*math.fsum(r['conditional_gain'] for r in rows)/n if n else None,
            mean_entry_cost_basis_points=1e4*math.fsum(r['actual_entry_cost'] for r in rows)/n if n else None)
    return dict(complete=True, snapshot=str(snapshot), kind=seal['kind'], seeds=seeds,
        counts=dict(counters), maximum_numeric_copy_or_aggregation_error=maximum_error,
        maximum_retained_deployment_gain_identity_residual=maximum_gain_identity_residual,
        gain_identity_absolute_tolerance=tolerance,
        deployment_summary=summary, snapshot_seal_sha256=sha256(seal_path),
        audit_source_sha256=sha256(Path(__file__)),
        scope='Independent JSON-to-report transcription, exact cohort/deployment membership, all 1/3/5-year event and market-specific rates, registry consistency and four per-market decision metrics. No new market, optimizer or score replay; stable-event adjudication and underlying conditional utility are not recomputed. Event populations remain method-specific and do not identify causal cross-method delay or waiting-cost effects. Serialized gain-field identity uses the stated economic tolerance, not machine precision.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if any(args.report.resolve().is_relative_to(p.resolve()) for p in (args.snapshot, args.output)):
        parser.error('Audit report must lie outside the sealed snapshot and raw output tree')
    result = audit(args.snapshot, args.output)
    args.report.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('seeds','deployment_summary')}, indent=2))
