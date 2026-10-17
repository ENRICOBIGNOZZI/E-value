"""Prepare a new manuscript packet only from the complete frozen final study.

No simulation, pilot mode, outcome gate or direct manuscript replacement.
"""
import argparse
from collections import Counter
import csv
import json
import math
from pathlib import Path
import shutil
import statistics
import tempfile

from assess_final_study import assess
from continue_full_study import validate_freezes
from seal_full_snapshot import sha256, validate_snapshot

ROOT = Path(__file__).resolve().parents[1]
SEARCH = ('Greedy', 'HAC', 'Catoni', 'Tail')
REQUIRED = {'metrics_by_seed.csv', 'method_summary.csv', 'paired_comparisons.csv',
            'decisions.csv', 'deployments.csv', 'opportunity_rates.csv',
            'holdings_diagnostics.csv', 'market_move_incidence.csv',
            'arithmetic_verification.json', 'config_frozen.json', 'source_manifest.json',
            'study_manifest.json', 'full_strategy_paths.png', 'full_strategy_evidence.png'}


def read_json(path):
    return json.loads(Path(path).read_text())


def read_csv(path):
    with Path(path).open(newline='') as stream:
        return list(csv.DictReader(stream))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_bundle(root, snapshot, output, numeric_path, event_path, assessment_path):
    plan, freeze, _ = validate_freezes(root)
    seal_path = snapshot/'snapshot_seal.json'
    seal = read_json(seal_path)
    seeds = plan['final_seeds']
    require(seal.get('complete') is True and seal.get('kind') == 'final'
            and seal.get('stage') == 'main' and seal.get('seeds') == seeds
            and len(seeds) == 500 and seal.get('frozen_pool_size') == 500,
            'Manuscript final packet requires all 500 frozen final markets')
    require(REQUIRED <= set(seal['files_sha256']), 'Missing required sealed manuscript input')

    def verify_files():
        require(sha256(seal_path) == seal_hash, 'Snapshot seal changed during preparation')
        for name, expected in seal['files_sha256'].items():
            path = (snapshot/name).resolve()
            require(path.is_relative_to(snapshot.resolve()), 'Sealed path leaves the snapshot')
            require(sha256(path) == expected, f'Changed sealed manuscript input: {name}')

    seal_hash = sha256(seal_path)
    verify_files()
    numeric, event = read_json(numeric_path), read_json(event_path)

    def audit_binding(record, source):
        require(record.get('complete') is True and record.get('kind') == 'final'
                and record.get('seeds') == seeds
                and record.get('snapshot_seal_sha256') == seal_hash
                and record.get('audit_source_sha256') == sha256(root/'scripts'/source),
                f'Missing, stale or wrong-sample final audit: {source}')

    audit_binding(numeric, 'audit_full_snapshot.py')
    require(numeric.get('scalar_reporting_checks', 0) > 0
            and numeric.get('all_sealed_report_file_hashes_match') is True,
            'Final numeric reporting audit is unresolved')
    audit_binding(event, 'audit_full_event_adjudication.py')
    audit_binding(event['reporting_audit'], 'audit_full_event_snapshot.py')
    require(event.get('reporting_auditor_source_sha256') == sha256(root/'scripts/audit_full_event_snapshot.py'),
            'Event reconstruction uses a stale report auditor')
    assessment = read_json(assessment_path)
    require(assessment == assess(snapshot, root/'reports/final_analysis_plan.json'),
            'Final assessment differs from the frozen complete-sample analysis')
    require(assessment['kind'] == 'complete_final_assessment' and assessment['markets'] == 500,
            'Pilot evidence cannot supply a final manuscript packet')
    records = validate_snapshot(output, seeds, freeze['scientific_source_hash'],
                                freeze['final_config'], root/'scripts/verify_full_strategy.py')
    require({str(row['seed']): row['input_digest'] for row in records} == seal['input_digests']
            and sum(row['checks'] for row in records) == seal['scalar_replay_checks']
            and sum(row['ghost_pairs_checked'] for row in records) == seal['ghost_pairs_checked'],
            'Byte-current raw replay differs from the sealed final evidence')
    verify_files()
    inputs = {str(path.resolve()): sha256(path) for path in
              (seal_path, numeric_path, event_path, assessment_path,
               root/'reports/final_analysis_plan.json')}
    return dict(plan=plan, seal=seal, assessment=assessment, inputs=inputs,
                metrics=read_csv(snapshot/'metrics_by_seed.csv'),
                decisions=read_csv(snapshot/'decisions.csv'),
                deployments=read_csv(snapshot/'deployments.csv'),
                rates=read_csv(snapshot/'opportunity_rates.csv'))


def mean(values):
    return math.fsum(values)/len(values)


def render(bundle):
    """Pure formatting of complete-sample results; no performance-dependent arms."""
    plan, assessment = bundle['plan'], bundle['assessment']
    metrics, decisions, deployments = bundle['metrics'], bundle['decisions'], bundle['deployments']
    lines = [r'\subsection{Complete final economic evaluation}',
        'The final evaluation contains all 500 declared fresh markets, seeds '
        '60001--60500. Each '
        'market has 500 stocks, 100 candidate signals, one training year and '
        '14 out-of-sample years of 252 dates. Every market is complete and '
        'independently replayed. Pilot markets and repeated same-seed numerical '
        'implementations are not added to this sample.',
        r'\begin{table}[H]\centering\small', r'\begin{tabular}{lrrrr}\toprule',
        r'Method & $h\bar U$ (MC SE) & Mean wealth & Inactive & Mean moves \\\midrule']
    for method in plan['methods']:
        rows = [row for row in metrics if row['method'] == method]
        require(len(rows) == 500, f'Wrong final method membership: {method}')
        utility = [float(row['annual_scaled_utility']) for row in rows]
        lines.append(f'{method} & {mean(utility):.5f} ({statistics.stdev(utility)/math.sqrt(500):.5f}) & '
                     f'{mean([float(row["final_equity"]) for row in rows]):.3f} & '
                     f'{mean([float(row["inactive_fraction"]) for row in rows]):.3f} & '
                     f'{mean([float(row["moves"]) for row in rows]):.2f} '+r'\\')
    lines += [r'\bottomrule\end{tabular}',
        r'\caption{Complete final-study fund outcomes. Utility includes all waiting '
        r'dates and actual modeled trading costs and is scaled by $h=252$, not '
        r'an annual return or certainty equivalent. MC SE uses 500 independent '
        r'markets. Mean moves include terminal choices, which create no subsequent '
        r'fund return.}\label{tab:final-funds}\end{table}',
        r'\begin{table}[H]\centering\small', r'\begin{tabular}{llrrr}\toprule',
        r'Role & Tail minus & Mean difference & MC SE & 95\% MC interval \\\midrule']
    for row in assessment['all_contrasts']:
        lines.append(f'{row["role"].capitalize()} & {row["reference"]} & '
                     f'{row["mean_difference"]:+.5f} & {row["standard_error"]:.5f} & '
                     f'[{row["ci_low"]:+.5f}, {row["ci_high"]:+.5f}] '+r'\\')
    lines += [r'\bottomrule\end{tabular}',
        r'\caption{The frozen paired analysis on all 500 final markets. Tail minus '
        r'All Signals is primary; all other contrasts are secondary and unadjusted. '
        r'Intervals are two-sided approximate Student Monte Carlo intervals with '
        r'499 degrees of freedom under the fixed DGP and signal library. '
        r'Comparator priority was fixed after pilot inspection, before final '
        r'output.}\label{tab:final-contrasts}\end{table}',
        'Every declared contrast is retained regardless of its sign. Zero '
        'observed Monte Carlo standard error does not establish zero population '
        'uncertainty. These portfolio differences do not causally isolate waiting '
        'costs: allocation paths, support choices and trading states also differ.',
        r'\begin{table}[H]\centering\small',
        r'\begin{tabular}{lrrrrrr}\toprule',
        r'Method & ENTRY & PARK & REVIVE & SWAP & Choices & Executed \\\midrule']
    for method in SEARCH:
        choices = [row for row in decisions if row['method'] == method]
        counts = Counter(row['lifecycle'] for row in choices)
        require(set(counts) <= {'ENTRY', 'PARK', 'REVIVE', 'SWAP'}, 'Unknown lifecycle')
        executed = sum(row['method'] == method for row in deployments)
        lines.append(f'{method} & '+ ' & '.join(str(counts[key]) for key in ('ENTRY','PARK','REVIVE','SWAP'))
                     + f' & {len(choices)} & {executed} '+r'\\')
    lines += [r'\bottomrule\end{tabular}',
        r'\caption{Final-study lifecycle choices and executed deployments. '
        r'Terminal choices are retained in choices and excluded from executed '
        r'deployments. No absence of moves is interpreted as zero population '
        r'probability.}\label{tab:final-lifecycles}\end{table}',
        r'\begin{table}[H]\centering\small',r'\begin{tabular}{lrrrr}\toprule',
        r'Method & Executed & Positive gain & Mean gain (bp) & Entry cost (bp) \\\midrule']
    for method in SEARCH:
        rows = [row for row in deployments if row['method'] == method]
        if not rows:
            lines.append(f'{method} & 0 & -- & -- & -- '+r'\\')
            continue
        gains = [float(row['conditional_gain']) for row in rows]
        lines.append(f'{method} & {len(rows)} & {sum(value > 1e-8 for value in gains)/len(rows):.3f} & '
                     f'{1e4*mean(gains):+.3f} & {1e4*mean([float(row["actual_entry_cost"]) for row in rows]):.3f} '+r'\\')
    lines += [r'\bottomrule\end{tabular}',
        r'\caption{Descriptive evaluator-only next-period gains from the actual '
        r'previous fund allocation, including transition costs and excluding '
        r'terminal choices. Positive means exceeding the unchanged $10^{-8}$ '
        r'daily-utility tolerance. The historical test does not certify these '
        r'gains, and a one-day gain is not lifetime trade value. Empty groups '
        r'have undefined summaries.}\label{tab:final-deployments}\end{table}',
        r'\begin{table}[H]\centering\small', r'\begin{tabular}{lrrrr}\toprule',
        r'Method & Follow-up (years) & Eligible events & Criterion within & Selected within \\\midrule']
    selected_rates = [row for row in bundle['rates']
                      if row['lifecycle'] == 'ALL' and row['event_kind'] == 'ALL']
    rates = {(row['method'], int(row['followup_years'])): row for row in selected_rates}
    require(len(selected_rates) == len(rates) == 12, 'Missing or duplicated final follow-up cohort')
    for method in SEARCH:
        for years in (1, 3, 5):
            row = rates[method, years]
            lines.append(f'{method} & {years} & {int(row["eligible_events"])} & '
                         f'{int(row["criterion_within"])} & {int(row["selected_within"])} '+r'\\')
    lines += [r'\bottomrule\end{tabular}',
        r'\caption{Complete final-study stable-event counts with the stated '
        r'calendar follow-up, retaining early responses through evaluator-only '
        r'continuations. Each method has its own endogenous reference policies '
        r'and event population. Dependent events are not independent replications; '
        r'raw rates do not identify causal cross-method detection performance.}'
        r'\label{tab:final-events}\end{table}']
    for name, caption in [
        ('paths', 'Final actual net wealth and selected support size. Wealth bands are descriptive 10th and 90th market percentiles, not confidence intervals.'),
        ('evidence', 'Final mean across markets of the largest currently open annual log capital. Closed comparisons are not carried forward. The individual threshold does not protect the entire search.')]:
        lines += [r'\begin{figure}[H]\centering',
                  f'\\includegraphics[width=.96\\linewidth]{{figures/final_strategy_{name}.png}}',
                  f'\\caption{{{caption}}}'+r'\end{figure}']
    lines.append(r'\FloatBarrier')
    return '\n\n'.join(lines)+'\n'


def build(root, snapshot, output, numeric_path, event_path, assessment_path, destination):
    require(not destination.exists(), 'Refusing to overwrite a manuscript packet')
    require(not destination.resolve().is_relative_to(snapshot.resolve())
            and not destination.resolve().is_relative_to(output.resolve()),
            'Manuscript packet cannot be written inside scientific evidence')
    bundle = validate_bundle(root, snapshot, output, numeric_path, event_path, assessment_path)
    text = render(bundle)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.final-packet-', dir=destination.parent))
    try:
        (temporary/'generated_final_results.tex').write_text(text)
        (temporary/'figures').mkdir()
        for name in ('paths', 'evidence'):
            shutil.copyfile(snapshot/f'full_strategy_{name}.png', temporary/f'figures/final_strategy_{name}.png')
            require(sha256(temporary/f'figures/final_strategy_{name}.png') ==
                    bundle['seal']['files_sha256'][f'full_strategy_{name}.png'],
                    'Copied final figure differs from sealed figure')
        after = validate_bundle(root, snapshot, output, numeric_path, event_path, assessment_path)
        require(bundle == after, 'Final evidence changed while preparing manuscript packet')
        verification = dict(complete=True, kind='complete_final_manuscript_packet', markets=500,
            scientific_source_hash=bundle['seal']['source_hash'], inputs_sha256=bundle['inputs'],
            builder_source_sha256=sha256(Path(__file__)),
            outputs_sha256={str(path.relative_to(temporary)): sha256(path)
                            for path in sorted(temporary.rglob('*')) if path.is_file()},
            scope='Verified complete-final reporting packet only. No simulations, outcome selection, new inferential endpoint, manuscript replacement, PDF visual review or overall-goal completion.')
        (temporary/'verification.json').write_text(json.dumps(verification, indent=2)+'\n')
        temporary.rename(destination)
        return verification
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, default=ROOT/'reports/full_v3_snapshots/main_500')
    parser.add_argument('--output', type=Path, default=ROOT/'outputs/park_revive_full_v3/main')
    parser.add_argument('--numeric-audit', type=Path, default=ROOT/'reports/full_v3_snapshots/main_500_numeric_audit.json')
    parser.add_argument('--event-audit', type=Path, default=ROOT/'reports/full_v3_snapshots/main_500_event_adjudication_audit.json')
    parser.add_argument('--assessment', type=Path, default=ROOT/'reports/full_final_assessment.json')
    parser.add_argument('--destination', type=Path, default=ROOT/'reports/final_manuscript_packet')
    args = parser.parse_args()
    print(json.dumps(build(ROOT, args.snapshot, args.output, args.numeric_audit,
                           args.event_audit, args.assessment, args.destination), indent=2))
