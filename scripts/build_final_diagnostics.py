"""Build supplementary diagnostics from the complete verified final study.

Uses the final-manuscript evidence gate. No simulation or direct paper writes.
"""
import argparse
import json
from pathlib import Path
import shutil
import tempfile
import textwrap

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

import build_final_manuscript_results as packet
from seal_full_snapshot import sha256

ROOT = Path(__file__).resolve().parents[1]
METHODS = ('All Signals', 'Greedy', 'HAC', 'Catoni', 'Tail', 'Oracle')
SEARCH = packet.SEARCH
REPRESENTATIVE_FINAL_SEED = 60001
METRICS = ('annual_scaled_utility', 'sharpe', 'sharpe_hac', 'linear_cost',
           'impact_cost', 'turnover', 'inactive_fraction', 'max_drawdown')
TERMINATIONS = ('competing_move', 'sign_reversal', 'shortlist_withdrawal', 'administrative_end')
FIGURES = (
    ('representative', 'Fixed representative market: actual net wealth and permitted support'),
    ('sharpe', 'Market distributions of conventional and HAC Sharpe ratios'),
    ('paired_utility', 'Paired utility differences: Tail minus every declared comparator'),
    ('utility_costs', 'Market distributions of utility, actual costs and turnover'),
    ('deployment', 'Executed decisions: next-period economic gains and errors'),
    ('membership', 'Selected and previously selected signals in the fixed representative market'),
    ('followup', 'Stable economic events: fixed-calendar response and competing terminations'),
    ('runtime', 'Measured computation time: market totals and annual blocks'),
)


def require(condition, message):
    packet.require(condition, message)


def prepare(metrics, deployments, opportunities, rates, daily, runtime, seeds, config):
    """Pure diagnostics; explicit samples also allow labeled software/pilot previews."""
    seeds = list(seeds)
    block, years = config['block'], config['years']
    last = block*years
    require(len(seeds) == len(set(seeds)) > 0, 'Duplicate or empty diagnostic seed list')
    metrics = metrics.copy()
    require(set(METRICS) <= set(metrics), 'Missing diagnostic metric columns')
    expected = {(seed, method) for seed in seeds for method in METHODS}
    require(len(metrics) == len(expected) and
            set(zip(metrics.seed, metrics.method)) == expected, 'Wrong diagnostic market membership')
    summaries = []
    for method in METHODS:
        group = metrics[metrics.method.eq(method)]
        for metric in METRICS:
            values = group[metric].to_numpy(dtype=float)
            require(not np.isinf(values).any(), 'Infinite diagnostic metric')
            finite = values[np.isfinite(values)]
            require(metric in ('sharpe', 'sharpe_hac') or len(finite) == len(seeds),
                    'Undefined non-Sharpe diagnostic metric')
            row = dict(method=method, metric=metric, markets=len(seeds), defined=len(finite))
            for key, value in [('mean', np.mean), ('median', np.median),
                               ('q10', lambda x: np.quantile(x, .1)),
                               ('q90', lambda x: np.quantile(x, .9))]:
                row[key] = float(value(finite)) if len(finite) else np.nan
            summaries.append(row)
    pivot = metrics.pivot(index='seed', columns='method', values='annual_scaled_utility')
    paired = pd.DataFrame([
        dict(seed=seed, reference=method, difference=float(pivot.loc[seed, 'Tail']-pivot.loc[seed, method]))
        for method in METHODS if method != 'Tail' for seed in seeds
    ])
    require(set(deployments.method) <= set(SEARCH) and set(deployments.seed) <= set(seeds),
            'Unknown deployment market or method')
    if len(deployments):
        require(np.isfinite(deployments.conditional_gain.to_numpy(dtype=float)).all(),
                'Nonfinite deployment gain')
        require((deployments.day < last).all(), 'Terminal choice is not an executed deployment')
    deployment_counts = []
    for method in SEARCH:
        values = deployments.loc[deployments.method.eq(method), 'conditional_gain'].to_numpy(dtype=float)
        deployment_counts.append(dict(method=method, executed=len(values),
            positive=int((values > 1e-8).sum()), negative=int((values < -1e-8).sum()),
            near_zero=int((np.abs(values) <= 1e-8).sum())))

    # Administrative censoring is not substituted for competing terminations.
    require(set(opportunities.method) <= set(SEARCH) and set(opportunities.seed) <= set(seeds),
            'Unknown event market or method')
    require(set(opportunities.termination_reason) <= set(TERMINATIONS+('selected',)),
            'Unknown opportunity termination')
    followup = []
    for method in SEARCH:
        events = opportunities[opportunities.method.eq(method)]
        for horizon in (1, 3, 5):
            cohort = events[events.onset_day+horizon*block <= last].copy()
            deadline = cohort.onset_day+horizon*block
            chosen = (cohort.selected_day >= cohort.onset_day) & (cohort.selected_day <= deadline)
            criterion = (cohort.criterion_day >= cohort.onset_day) & (cohort.criterion_day <= deadline)
            row = dict(method=method, followup_years=horizon, eligible_events=len(cohort),
                       selected_within=int(chosen.sum()), criterion_within=int(criterion.sum()))
            ended = (~chosen) & (cohort.termination_day <= deadline)
            for reason in TERMINATIONS:
                row[reason] = int((ended & cohort.termination_reason.eq(reason)).sum())
            row['still_unselected'] = len(cohort)-row['selected_within']-sum(row[k] for k in TERMINATIONS)
            require(row['still_unselected'] >= 0, 'Overlapping event dispositions')
            match = rates[rates.method.eq(method) & rates.lifecycle.eq('ALL')
                          & rates.event_kind.eq('ALL') & rates.followup_years.eq(horizon)]
            require(len(match) == 1, 'Missing or duplicate follow-up summary')
            require(all(int(match.iloc[0][key]) == row[key] for key in
                        ('eligible_events', 'selected_within', 'criterion_within')),
                    'Event follow-up differs from sealed aggregate')
            followup.append(row)

    expected_days = list(range(block, last))
    require(len(daily.seed.unique()) == 1 and int(daily.seed.iloc[0]) in seeds,
            'Wrong representative market')
    for method in METHODS:
        group = daily[daily.method.eq(method)].sort_values('day')
        require(group.day.tolist() == expected_days, 'Incomplete or duplicate representative calendar')
        require(np.isfinite(group.equity.to_numpy(dtype=float)).all(), 'Nonfinite representative wealth')
        for row in group[group.day % block == 0].itertuples():
            values = np.asarray(row.support)
            require(values.ndim == 1, 'Malformed support')
            require(not len(values) or np.issubdtype(values.dtype, np.integer), 'Noninteger support ID')
            support = set(map(int, values))
            require(all(0 <= signal < config['n_signals'] for signal in support), 'Unknown support ID')
            require(len(support) == len(row.support) == int(row.n_active), 'Support size mismatch')
    require(set(daily.method) == set(METHODS), 'Unknown representative method')
    membership = []
    for method in SEARCH:
        seen = set()
        for row in daily[daily.method.eq(method) & (daily.day % block == 0)].sort_values('day').itertuples():
            support = set(map(int, row.support))
            require(all(0 <= signal < config['n_signals'] for signal in support), 'Unknown support ID')
            require(len(support) == int(row.n_active), 'Support size mismatch')
            seen |= support
            membership.extend(dict(method=method, day=int(row.day), signal=signal,
                state=1 if signal in support else 2 if signal in seen else 0)
                for signal in range(config['n_signals']))
    expected_runtime = {(seed, year) for seed in seeds for year in range(1, years)}
    require(len(runtime) == len(expected_runtime) and
            set(zip(runtime.seed, runtime.year)) == expected_runtime, 'Wrong runtime calendar or membership')
    require(np.isfinite(runtime.seconds.to_numpy(dtype=float)).all() and (runtime.seconds >= 0).all(),
            'Invalid measured runtime')
    totals = runtime.groupby('seed', as_index=False).seconds.sum()
    return dict(metrics=metrics, summary=pd.DataFrame(summaries), paired=paired,
                deployments=deployments, deployment_counts=pd.DataFrame(deployment_counts),
                followup=pd.DataFrame(followup), daily=daily, membership=pd.DataFrame(membership),
                runtime=runtime, runtime_totals=totals, seeds=seeds, config=config)


def ecdf(axis, values, label):
    values = np.asarray(values, dtype=float)
    values = np.sort(values[np.isfinite(values)])
    if len(values):
        axis.step(values, np.arange(1, len(values)+1)/len(values), where='post',
                  label=f'{label} (n={len(values)})')
    else:
        axis.plot([], [], label=f'{label} (n=0; undefined)')
    axis.set_ylabel('Fraction of defined markets')


def render(data, destination, context):
    """Plots only; context is explicit and appears on every page."""
    destination.mkdir()
    metrics, cfg = data['metrics'], data['config']
    n = len(data['seeds'])
    colors = plt.get_cmap('tab10').colors
    outputs = []
    with plt.rc_context({'font.size': 9, 'axes.spines.top': False,
                         'axes.spines.right': False, 'legend.fontsize': 7}), \
         PdfPages(destination/'diagnostics.pdf') as pdf:
        def finish(fig, name, caption, bottom=.035):
            fig.suptitle(context+'\n'+textwrap.fill(caption, width=100), fontsize=11)
            fig.tight_layout(rect=(0, bottom, 1, .92))
            fig.text(.02, .012, 'Descriptive diagnostics; no new inferential endpoint or causal delay comparison.',
                     fontsize=7)
            fig.savefig(destination/f'{name}.png', dpi=160)
            pdf.savefig(fig)
            plt.close(fig)
            outputs.append(name)

        fig, axes = plt.subplots(2, 1, figsize=(10, 7))
        daily = data['daily']
        for method in METHODS:
            group = daily[daily.method.eq(method)].sort_values('day')
            dates = (group.day.to_numpy()-cfg['block']+1)/cfg['block']
            axes[0].plot(np.r_[0, dates], np.r_[1., group.equity.to_numpy()], label=method)
            axes[1].step(dates, group.n_active, where='post', label=method)
        axes[0].set_ylabel('Actual net wealth'); axes[0].legend(ncol=3)
        axes[1].set(xlabel='Out-of-sample year', ylabel='Permitted signals')
        finish(fig, 'representative', f'Fixed seed {int(daily.seed.iloc[0])}; includes waiting in cash')

        fig, axes = plt.subplots(1, 2, figsize=(10, 6))
        for axis, metric, title in zip(axes, ('sharpe', 'sharpe_hac'), ('Conventional Sharpe', 'HAC Sharpe')):
            for method in METHODS:
                ecdf(axis, metrics.loc[metrics.method.eq(method), metric], method)
            axis.set_xlabel(title); axis.legend()
        finish(fig, 'sharpe', 'Undefined Sharpe ratios are excluded with their defined denominators shown')

        fig, axis = plt.subplots(figsize=(10, 6))
        for reference, group in data['paired'].groupby('reference', sort=False):
            ecdf(axis, group.difference, 'Tail minus '+reference)
        axis.axvline(0, color='black', linestyle='--', linewidth=.8)
        axis.set_xlabel('Difference in mean daily quadratic utility scaled by 252')
        axis.legend()
        finish(fig, 'paired_utility', f'All {n} paired markets retained for every contrast')

        fig, axes = plt.subplots(2, 2, figsize=(10, 7))
        for axis, metric, title in zip(axes.flat,
                ('annual_scaled_utility', 'linear_cost', 'impact_cost', 'turnover'),
                ('Mean daily utility ×252', 'Cumulative proportional costs',
                 'Cumulative impact costs', 'Cumulative target turnover')):
            axis.boxplot([metrics.loc[metrics.method.eq(m), metric].to_numpy() for m in METHODS],
                         tick_labels=METHODS, showfliers=True)
            axis.tick_params(axis='x', rotation=30); axis.set_ylabel(title)
        finish(fig, 'utility_costs', f'Fund outcomes in {n} markets; costs are in decimal return units')

        fig, axes = plt.subplots(1, 2, figsize=(10, 6))
        counts = data['deployment_counts'].set_index('method').loc[list(SEARCH)]
        bottom = np.zeros(len(SEARCH))
        for category, color in zip(('positive', 'near_zero', 'negative'), ('#229954', '#aab7b8', '#c0392b')):
            axes[0].bar(SEARCH, counts[category], bottom=bottom, label=category, color=color)
            bottom += counts[category].to_numpy()
        axes[0].set_ylabel('Executed deployments'); axes[0].legend()
        for method in SEARCH:
            values = data['deployments'].loc[data['deployments'].method.eq(method), 'conditional_gain']
            ecdf(axes[1], 1e4*values.to_numpy(dtype=float), method)
        axes[1].set(xlabel='Next-period conditional gain (bp)', ylabel='Fraction of executed deployments')
        axes[1].axvline(0, color='black', linestyle='--', linewidth=.8); axes[1].legend()
        finish(fig, 'deployment', 'Actual-state evaluator gains; ±1e-8 tolerance; terminal choices excluded')

        fig, axes = plt.subplots(2, 2, figsize=(10, 7))
        state_colors = ('#eeeeee', '#2166ac', '#d98b39')
        for axis, method in zip(axes.flat, SEARCH):
            grid = data['membership'][data['membership'].method.eq(method)].pivot(
                index='signal', columns='day', values='state')
            axis.imshow(grid.to_numpy(), origin='lower', aspect='auto', vmin=0, vmax=2,
                        cmap=ListedColormap(state_colors), interpolation='nearest')
            axis.set(title=method, xlabel='Out-of-sample annual block', ylabel='Stable signal ID')
            axis.set_xticks(np.arange(len(grid.columns))[::2],
                            [str(i+1) for i in range(len(grid.columns))][::2])
        fig.legend(handles=[Patch(facecolor=c, label=t) for c,t in zip(state_colors,
            ('Never selected', 'Selected support', 'Previously selected, now inactive'))],
            loc='lower center', bbox_to_anchor=(.5, .035), ncol=3, fontsize=8)
        finish(fig, 'membership', 'Realized annual support; inactive history includes removal by swap', bottom=.1)

        fig, axes = plt.subplots(1, 2, figsize=(11, 7))
        followup = data['followup']
        for i, method in enumerate(SEARCH):
            group = followup[followup.method.eq(method)]
            eligible = group.eligible_events.to_numpy()
            for column, style in [('selected_within','-'), ('criterion_within','--')]:
                fraction = np.divide(group[column].to_numpy(), eligible,
                                     out=np.full(3, np.nan), where=eligible > 0)
                axes[0].plot(group.followup_years, fraction, style, marker='o',
                             color=colors[i], label=method+(' selected' if style=='-' else ' criterion'))
        axes[0].set(xlabel='Calendar follow-up (years)', ylabel='Fraction of eligible stable events',
                    xticks=[1,3,5], ylim=(-.02,1.02))
        axes[0].legend(loc='upper center', bbox_to_anchor=(.5,-.15), ncol=2)
        group = followup[followup.followup_years.eq(3)].set_index('method').loc[list(SEARCH)]
        categories = ('selected_within',)+TERMINATIONS+('still_unselected',)
        bottom = np.zeros(len(SEARCH))
        for i, category in enumerate(categories):
            axes[1].bar(SEARCH, group[category], bottom=bottom,
                        label=category.replace('_',' '), color=colors[i])
            bottom += group[category].to_numpy()
        axes[1].set_ylabel('Events with full three-year follow-up')
        axes[1].legend(loc='upper center', bbox_to_anchor=(.5,-.15), ncol=2)
        finish(fig, 'followup', 'Method-specific populations; competing endings kept distinct from administrative censoring',
               bottom=.12)

        fig, axes = plt.subplots(1, 2, figsize=(10, 6))
        ecdf(axes[0], data['runtime_totals'].seconds.to_numpy()/60, 'All markets')
        axes[0].set_xlabel('Sum of measured annual simulation blocks (minutes)'); axes[0].legend()
        grouped = data['runtime'].groupby('year').seconds
        years = np.array(sorted(data['runtime'].year.unique()))
        axes[1].plot(years, grouped.median().loc[years], marker='o', label='Median')
        axes[1].fill_between(years, grouped.quantile(.1).loc[years], grouped.quantile(.9).loc[years],
                             alpha=.2, label='10th–90th percentiles')
        axes[1].set(xlabel='Annual simulation block', ylabel='Measured seconds'); axes[1].legend()
        finish(fig, 'runtime', 'All methods combined; excludes independent replay and is not parallel job wall time')
    require(outputs == [name for name,_ in FIGURES], 'Incomplete diagnostic figure set')
    tables = {'metric_summary':data['summary'], 'market_metrics':metrics,
              'deployment_gains':data['deployments'], 'paired_utility':data['paired'],
              'deployment_counts':data['deployment_counts'], 'event_followup':data['followup'],
              'representative_paths':daily.drop(columns='support'),
              'membership':data['membership'], 'runtime_by_market':data['runtime_totals'],
              'runtime_by_block':data['runtime']}
    for name, table in tables.items():
        table.to_csv(destination/f'{name}.csv', index=False)
    return outputs


def load_data(bundle, snapshot, output):
    seeds, config = bundle['plan']['final_seeds'], packet.read_json(snapshot/'config_frozen.json')
    require('details/economic_opportunities.csv.gz' in bundle['seal']['files_sha256'],
            'Unsealed detailed event input')
    daily = pd.read_parquet(output/f'seed_{REPRESENTATIVE_FINAL_SEED}'/'daily_ledger.parquet',
                            columns=['seed','method','day','equity','n_active','support'])
    runtime = pd.concat([pd.read_csv(output/f'seed_{seed}'/'runtime.csv') for seed in seeds],
                        ignore_index=True)
    data = prepare(pd.read_csv(snapshot/'metrics_by_seed.csv'), pd.read_csv(snapshot/'deployments.csv'),
        pd.read_csv(snapshot/'details/economic_opportunities.csv.gz'), pd.read_csv(snapshot/'opportunity_rates.csv'),
        daily, runtime, seeds, config)
    require(int(daily.seed.iloc[0]) == REPRESENTATIVE_FINAL_SEED, 'Changed fixed representative seed')
    return data


def build(root, snapshot, output, numeric_path, event_path, assessment_path, destination):
    require(not destination.exists(), 'Refusing to overwrite diagnostics')
    require(not any(destination.resolve().is_relative_to(path.resolve())
                    for path in (snapshot, output, root/'paper')),
            'Diagnostics cannot be written inside evidence or the manuscript')
    bundle = packet.validate_bundle(root, snapshot, output, numeric_path, event_path, assessment_path)
    data = load_data(bundle, snapshot, output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.final-diagnostics-', dir=destination.parent))
    try:
        names = render(data, temporary/'graphics', 'Complete final study — 500 markets')
        after = packet.validate_bundle(root, snapshot, output, numeric_path, event_path, assessment_path)
        require(bundle == after, 'Final evidence changed during diagnostic preparation')
        record = dict(complete=True, kind='complete_final_diagnostics', markets=500,
            representative_seed=REPRESENTATIVE_FINAL_SEED, figures=names,
            inputs_sha256=bundle['inputs'], builder_source_sha256=sha256(Path(__file__)),
            evidence_gate_source_sha256=sha256(root/'scripts/build_final_manuscript_results.py'),
            protocol_sha256=sha256(root/'reports/final_diagnostics_protocol.md'),
            outputs_sha256={str(p.relative_to(temporary)):sha256(p)
                            for p in sorted(temporary.rglob('*')) if p.is_file()},
            scope='Descriptive complete-final diagnostics only. No new markets, policy/analysis changes, '
                  'inferential endpoints, causal delay ranking, direct paper replacement or PDF visual QA.')
        (temporary/'verification.json').write_text(json.dumps(record, indent=2)+'\n')
        temporary.rename(destination)
        return record
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,default=ROOT/'reports/full_v3_snapshots/main_500')
    parser.add_argument('--output',type=Path,default=ROOT/'outputs/park_revive_full_v3/main')
    parser.add_argument('--numeric-audit',type=Path,default=ROOT/'reports/full_v3_snapshots/main_500_numeric_audit.json')
    parser.add_argument('--event-audit',type=Path,default=ROOT/'reports/full_v3_snapshots/main_500_event_adjudication_audit.json')
    parser.add_argument('--assessment',type=Path,default=ROOT/'reports/full_final_assessment.json')
    parser.add_argument('--destination',type=Path,default=ROOT/'reports/final_diagnostics')
    args = parser.parse_args()
    print(json.dumps(build(ROOT,args.snapshot,args.output,args.numeric_audit,args.event_audit,
                           args.assessment,args.destination),indent=2))
