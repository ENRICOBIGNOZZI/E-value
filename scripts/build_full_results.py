#!/usr/bin/env python3
"""Summarize completed full-strategy seeds, retaining failures and competing events."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np
import pandas as pd
from scipy.stats import t


def summarize(output,destination,paper=None,seeds=None,*,details=None):
    destination.mkdir(parents=True,exist_ok=True)
    complete=[];incomplete=[]
    selected=set(seeds) if seeds is not None else None
    if selected is not None:
        incomplete=[f'seed_{seed} (not started)' for seed in sorted(selected) if not (output/f'seed_{seed}').exists()]
    for seed in sorted(output.glob('seed_*')):
        if selected is not None and int(seed.name.split('_')[-1]) not in selected:continue
        path=seed/'status.json'
        if not path.exists():incomplete.append(seed.name);continue
        status=json.loads(path.read_text())
        (complete if status['complete'] else incomplete).append(seed)
    if not complete:raise ValueError('No completed full-strategy seeds')
    configs={(p/'config_frozen.json').read_text() for p in complete}
    sources={json.loads((p/'status.json').read_text())['source_hash'] for p in complete}
    if len(configs)!=1 or len(sources)!=1:raise ValueError('Mixed source/configuration fingerprints')
    cfg=json.loads(next(iter(configs)));block=cfg['block'];horizon=block*cfg['years']
    metrics=pd.concat([pd.read_csv(p/'metrics_by_seed.csv') for p in complete],ignore_index=True)
    decisions=pd.DataFrame([x for p in complete for x in json.loads((p/'decisions.json').read_text())])
    deployments=pd.DataFrame([x for p in complete for x in json.loads((p/'deployments.json').read_text())])
    opportunities=pd.DataFrame([x for p in complete for x in json.loads((p/'economic_opportunities.json').read_text())])
    registry=pd.DataFrame([x for p in complete for x in json.loads((p/'opportunity_registry.json').read_text())])
    holdings=[]
    for directory in complete:
        daily=pd.read_parquet(directory/'daily_ledger.parquet',columns=['seed','method','weights','n_active','leverage'])
        for method,g in daily.groupby('method',sort=False):
            weights=np.stack(g.weights);effective=(np.abs(weights)>1e-6).sum(axis=1)
            holdings.append(dict(seed=int(g.seed.iloc[0]),method=method,mean_permitted_support=g.n_active.mean(),
                mean_effective_sleeves=float(effective.mean()),median_effective_sleeves=float(np.median(effective)),
                mean_leverage=g.leverage.mean(),position_count_threshold=1e-6))
    incidence=[]
    for method,g in metrics.groupby('method',sort=False):
        for endpoint in ('moves','executed_moves'):
            n=len(g);successes=int((g[endpoint]>0).sum());rate=successes/n;z=1.959963984540054
            center=(rate+z*z/(2*n))/(1+z*z/n)
            radius=z*np.sqrt(rate*(1-rate)/n+z*z/(4*n*n))/(1+z*z/n)
            incidence.append(dict(method=method,endpoint=endpoint,seeds=n,markets_with_move=successes,
                fraction=rate,wilson_low=max(0.,center-radius),wilson_high=min(1.,center+radius)))
    summaries=[];paired=[]
    for method,g in metrics.groupby('method',sort=False):
        for metric in ('annual_scaled_utility','sharpe','sharpe_hac','final_equity','max_drawdown','inactive_fraction','mean_active','moves','executed_moves','state_matched_regret'):
            values=g[metric].dropna();n=len(values);se=values.std(ddof=1)/np.sqrt(n) if n>1 else np.nan
            radius=t.ppf(.975,n-1)*se if n>1 else np.nan
            summaries.append(dict(method=method,metric=metric,n=n,mean=values.mean(),median=values.median(),
                standard_error=se,ci_low=values.mean()-radius,ci_high=values.mean()+radius))
    for metric in ('annual_scaled_utility','final_equity','sharpe_hac','inactive_fraction','state_matched_regret'):
        pivot=metrics.pivot(index='seed',columns='method',values=metric)
        for other in pivot.columns:
            if other=='Tail':continue
            delta=(pivot.Tail-pivot[other]).dropna();n=len(delta)
            se=delta.std(ddof=1)/np.sqrt(n) if n>1 else np.nan
            radius=t.ppf(.975,n-1)*se if n>1 else np.nan
            paired.append(dict(metric=metric,reference=other,n=n,mean_difference=delta.mean(),standard_error=se,
                ci_low=delta.mean()-radius,ci_high=delta.mean()+radius))
    risksets=[];seed_rates=[]
    if not opportunities.empty:
        for method in ('Greedy','HAC','Catoni','Tail'):
            for lifecycle in ('ALL','ENTRY','PARK','REVIVE','SWAP'):
                for kind in ('ALL','inception_positive','sign_change_positive'):
                    g=opportunities[opportunities.method.eq(method)]
                    if lifecycle!='ALL':g=g[g.lifecycle.eq(lifecycle)]
                    if kind!='ALL':g=g[g.event_kind.eq(kind)]
                    for years in (1,3,5):
                        cohort=g[g.onset_day+years*block<=horizon].copy()
                        selected_events=cohort.selected & cohort.selection_delay_days.le(years*block)
                        detected=cohort.criterion_detected & cohort.criterion_delay_days.le(years*block)
                        key=dict(method=method,lifecycle=lifecycle,event_kind=kind,followup_years=years)
                        risksets.append(dict(**key,stable_events=len(g),eligible_events=len(cohort),
                            selected_within=int(selected_events.sum()),criterion_within=int(detected.sum()),
                            selection_fraction=float(selected_events.mean()) if len(cohort) else np.nan,
                            criterion_fraction=float(detected.mean()) if len(cohort) else np.nan,
                            contributing_seeds=cohort.seed.nunique()))
                        for seed,sg in cohort.groupby('seed'):
                            seed_rates.append(dict(**key,seed=int(seed),eligible_events=len(sg),
                                selected_within=int((sg.selected & sg.selection_delay_days.le(years*block)).sum()),
                                criterion_within=int((sg.criterion_detected & sg.criterion_delay_days.le(years*block)).sum())))
    details=output/'aggregate' if details is None else details
    details.mkdir(parents=True,exist_ok=True)
    for name,frame in [('metrics_by_seed',metrics),('method_summary',pd.DataFrame(summaries)),
        ('paired_comparisons',pd.DataFrame(paired)),('decisions',decisions),('deployments',deployments),
        ('economic_opportunities',opportunities),('opportunity_registry',registry),
        ('holdings_diagnostics',pd.DataFrame(holdings)),('market_move_incidence',pd.DataFrame(incidence)),
        ('opportunity_rates',pd.DataFrame(risksets)),('opportunity_seed_counts',pd.DataFrame(seed_rates))]:
        if name in ('economic_opportunities','opportunity_registry'):
            frame.to_csv(details/f'{name}.csv.gz',index=False,compression={'method':'gzip','mtime':0})
        else:frame.to_csv(destination/f'{name}.csv',index=False)
    shutil.copyfile(complete[0]/'config_frozen.json',destination/'config_frozen.json')
    shutil.copyfile(complete[0]/'source_manifest.json',destination/'source_manifest.json')
    verification=output/'arithmetic_verification.json'
    verified={}
    if verification.exists():
        shutil.copyfile(verification,destination/'arithmetic_verification.json')
        verified={r['seed']:r for r in json.loads(verification.read_text()) if r.get('complete') and r.get('scientific_source_hash')==next(iter(sources))}
    from verify_full_strategy import input_digest
    audited=sum(verified.get(int(p.name.split('_')[-1]),{}).get('input_digest')==input_digest(p) for p in complete)
    manifest=dict(seeds=metrics.seed.unique().tolist(),requested_snapshot_seeds=sorted(selected) if selected is not None else None,n_complete=len(complete),
        incomplete=[str(p) for p in incomplete],source_hash=next(iter(sources)),
        config_sha256=hashlib.sha256(next(iter(configs)).encode()).hexdigest(),completed_seeds_with_arithmetic_audit=audited,
        detailed_tables=str(details.relative_to(destination)) if details.is_relative_to(destination) else str(details),
        limits=['Pilot uncertainty intervals use independent markets, not dependent episode counts.',
                'Opportunity populations depend on each method; fractions are descriptive.',
                'No multiple-comparison correction; HAC and e-tests have unmatched global error.',
                'Terminal decisions have no executed fund performance.'])
    (destination/'study_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    plot_paths(complete,destination,block)
    if paper is not None:generate_tex(destination,paper,metrics,decisions,deployments,pd.DataFrame(risksets),len(complete),len(incomplete),audited,cfg)
    return manifest


def generate_tex(results,paper,metrics,decisions,deployments,rates,count,pending,audited,cfg):
    paper.mkdir(exist_ok=True)
    interpretation=[]
    lines=[f'The reported full-strategy pilot snapshot contains {count} completed independent markets '
        f'({pending} requested snapshot markets remain incomplete). Each has {cfg["n_assets"]} stocks, {cfg["n_signals"]} signals, '
        f'one training block and {cfg["years"]-1} out-of-sample blocks of {cfg["block"]} days. '
        f'Independent arithmetic replay covers {audited} of these completed markets. These are pilot observations; '
        'the separate 500-market final study is not asserted to be complete. '
        'Earlier baseline and fixed-reference markets, and later markets outside the specified snapshot, are not added to this count.',
        r'\begin{table}[H]\centering\small',r'\begin{tabular}{lrrrr}',r'\toprule',
        r'Method & $h\bar U$ (MC SE) & Mean wealth & Inactive & Mean moves \\',r'\midrule']
    for method in ('All Signals','Greedy','HAC','Catoni','Tail','Oracle'):
        g=metrics[metrics.method.eq(method)]
        u=g.annual_scaled_utility;se=u.std(ddof=1)/np.sqrt(len(g)) if len(g)>1 else np.nan
        error=f'{se:.5f}' if np.isfinite(se) else '--'
        lines.append(f'{method} & {u.mean():.5f} ({error}) & {g.final_equity.mean():.3f} & '
                     f'{g.inactive_fraction.mean():.3f} & {g.moves.mean():.2f} '+r'\\')
    lines.extend([r'\bottomrule\end{tabular}',
        f'\\caption{{Full-strategy pilot means. Utility is daily utility rescaled by $h={cfg["block"]}$, not an annual certainty equivalent. MC SE uses independent markets. Wealth includes waiting in cash and all modeled actual fund costs. Moves include terminal choices, which create no post-choice fund return.}}'+r'\end{table}'])
    if count>1:
        paired=pd.read_csv(results/'paired_comparisons.csv')
        comparisons=[]
        for reference in ('All Signals','Greedy'):
            row=paired[paired.metric.eq('annual_scaled_utility')&paired.reference.eq(reference)].iloc[0]
            comparisons.append(f'{reference}: {row.mean_difference:.5f} [{row.ci_low:.5f}, {row.ci_high:.5f}]')
        interpretation.append('Paired Tail-minus-reference differences in $h\\bar U$ (95\\% Student MC intervals) are '
            +'; '.join(comparisons)+'. These exploratory intervals use independent paired markets and '
            'are unadjusted across comparisons; they do not give guarantees for a new financial law. '
            'The reproducibility tables retain every benchmark contrast.')
    tail_moves=decisions[decisions.method.eq('Tail')] if not decisions.empty else decisions
    tail_deployed=deployments[deployments.method.eq('Tail')] if not deployments.empty else deployments
    tail_metrics=metrics[metrics.method.eq('Tail')]
    lifecycle=tail_moves.lifecycle.value_counts().to_dict() if not tail_moves.empty else {}
    counts=', '.join(f'{name}: {lifecycle.get(name,0)}' for name in ('ENTRY','PARK','REVIVE','SWAP'))
    lines.append(f'Tail makes {len(tail_moves)} choices ({counts}), of which {len(tail_deployed)} '
        f'are executed before the horizon. Its mean inactive fraction is {tail_metrics.inactive_fraction.mean():.3f}. '
        'Successful initial certification therefore must be assessed alongside the returns foregone during waiting. '
        'The lifecycle counts delimit what this pilot can say about parking and revival.')
    holdings=pd.read_csv(results/'holdings_diagnostics.csv')
    all_counts=holdings[holdings.method.eq('All Signals')].mean_effective_sleeves
    interpretation.append(f'All Signals permits every candidate but does not hold all of them: '
        f'its mean number of positions exceeding $10^{{-6}}$ in absolute sleeve weight is {all_counts.mean():.2f}. '
        'This descriptive count is computed after the run and changes no allocation or test. '
        'The optimizer already produces a sparse portfolio, so it is a substantive baseline for '
        'the value of an additional statistical support filter. No fixed per-signal research cost '
        'is charged in this design.')
    incidence=pd.read_csv(results/'market_move_incidence.csv')
    c=incidence[incidence.method.eq('Catoni')&incidence.endpoint.eq('executed_moves')].iloc[0]
    interpretation.append(f'Catoni executes a move in {int(c.markets_with_move)} of {int(c.seeds)} markets '
        f'(Wilson 95\\% interval for the market-level fraction [{c.wilson_low:.3f}, {c.wilson_high:.3f}]). '
        'A zero observed fraction does not establish zero probability of future entry.')
    if not rates.empty:
        lines.extend([r'\begin{table}[H]\centering\small',r'\begin{tabular}{lrrr}',r'\toprule',
            r'Method & Eligible stable events & Criterion within year & Selected within year \\',r'\midrule'])
        selected_rates=rates[rates.lifecycle.eq('ALL')&rates.event_kind.eq('ALL')&rates.followup_years.eq(1)]
        for row in selected_rates.itertuples():
            lines.append(f'{row.method} & {row.eligible_events} & {row.criterion_within} & {row.selected_within} '+r'\\')
        lines.extend([r'\bottomrule\end{tabular}',
            r'\caption{Response-independent stable-event cohorts with a full year of calendar follow-up. Each row has its own endogenous reference policies and event population; raw counts do not identify causal cross-method detection performance. Dependent events are not treated as independent replications.}\end{table}'])
    if not deployments.empty:
        lines.extend([r'\begin{table}[H]\centering\small',r'\begin{tabular}{lrrrr}',r'\toprule',
            r'Method & Executed & Positive gain & Mean gain (bp) & Entry cost (bp) \\',r'\midrule'])
        for method,g in deployments.groupby('method',sort=False):
            lines.append(f'{method} & {len(g)} & {(g.conditional_gain>1e-8).mean():.3f} & '
                         f'{1e4*g.conditional_gain.mean():.3f} & {1e4*g.actual_entry_cost.mean():.3f} '+r'\\')
        lines.extend([r'\bottomrule\end{tabular}',
            r'\caption{Evaluator-only next-period gains from the actual previous allocation, including modeled transition costs. These descriptive outcomes concern executed decisions, exclude terminal certifications, and are not quantities certified by a historical episode rejection.}\end{table}'])
    figures=paper/'figures';figures.mkdir(exist_ok=True)
    for name,caption in [('full_strategy_paths','Actual net wealth and selected support size in the completed full-strategy pilot. Wealth bands are the 10th and 90th market percentiles; they are descriptive quantiles, not confidence intervals.'),
                         ('full_strategy_evidence','Mean across completed markets of the largest currently open annual log capital. Closed comparisons are not carried forward. The dashed line is the individual threshold; it does not protect the entire search.')]:
        shutil.copyfile(results/f'{name}.png',figures/f'{name}.png')
        lines.extend([r'\begin{figure}[H]\centering',f'\\includegraphics[width=.96\\linewidth]{{figures/{name}.png}}',
                      f'\\caption{{{caption}}}',r'\end{figure}'])
    lines.extend(interpretation)
    (paper/'generated_full_results.tex').write_text('\n\n'.join(lines)+'\n')


def plot_paths(seeds,destination,block):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    paths=pd.concat([pd.read_parquet(p/'daily_ledger.parquet',columns=['seed','method','day','equity','n_active']) for p in seeds])
    fig,axes=plt.subplots(2,1,figsize=(8,6.3),sharex=True)
    for method in ('All Signals','Greedy','HAC','Catoni','Tail','Oracle'):
        g=paths[paths.method.eq(method)].groupby('day')
        median=g.equity.median();line=axes[0].plot(median.index/block,median,label=method)[0]
        axes[0].fill_between(median.index/block,g.equity.quantile(.1),g.equity.quantile(.9),alpha=.07,color=line.get_color())
        if method not in ('All Signals','Oracle'):
            active=g.n_active.mean();axes[1].plot(active.index/block,active,label=method,color=line.get_color())
    axes[0].set(ylabel='Net wealth (median; 10–90% band)');axes[0].legend(ncol=3,fontsize=8)
    axes[1].set(xlabel='Simulation year',ylabel='Mean selected support size');axes[1].legend(ncol=4,fontsize=8)
    fig.tight_layout();fig.savefig(destination/'full_strategy_paths.png',dpi=180);plt.close(fig)
    events=pd.concat([pd.read_parquet(p/'comparison_events.parquet',columns=['seed','method','day','log_e']) for p in seeds])
    fig,ax=plt.subplots(figsize=(8,3.2))
    for method in ('Catoni','Tail'):
        maxima=events[events.method.eq(method)].groupby(['seed','day']).log_e.max().reset_index()
        g=maxima.groupby('day').log_e
        ax.plot(g.mean().index/block,g.mean(),marker='o',label=method)
    ax.axhline(np.log(20),color='black',linestyle='--',label='Individual threshold')
    ax.set(xlabel='Simulation year',ylabel='Mean of largest current log E')
    ax.legend(fontsize=8);fig.tight_layout();fig.savefig(destination/'full_strategy_evidence.png',dpi=180);plt.close(fig)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('outputs/park_revive_full_v2/pilot'))
    parser.add_argument('--destination',type=Path,default=Path('reports/full_results'))
    parser.add_argument('--paper',action='store_true')
    parser.add_argument('--seeds',type=int,nargs='+')
    args=parser.parse_args();print(json.dumps(summarize(args.output,args.destination,Path(__file__).resolve().parents[1]/'paper' if args.paper else None,args.seeds),indent=2))
