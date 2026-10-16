"""All figures and summaries are derived from completed numeric output files."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .metrics import paired_table


def report(directory):
    directory=Path(directory)
    seeds=sorted(p for p in directory.glob('seed_*') if (p/'metrics_by_seed.csv').exists())
    if not seeds:raise ValueError('No completed seeds to report')
    metrics=pd.concat([pd.read_csv(p/'metrics_by_seed.csv') for p in seeds],ignore_index=True)
    metrics.to_csv(directory/'metrics_by_seed.csv',index=False)
    paired_table(metrics).to_csv(directory/'paired_comparisons.csv',index=False)
    daily=pd.concat([pd.read_parquet(p/'daily_ledger.parquet') for p in seeds],ignore_index=True)
    events=pd.concat([pd.read_parquet(p/'comparison_events.parquet') for p in seeds],ignore_index=True)
    daily.to_parquet(directory/'daily_ledger.parquet',index=False)
    events.to_parquet(directory/'comparison_events.parquet',index=False)
    for name in ('decisions','runtime','detection'):
        pd.concat([pd.read_csv(p/(name+'.csv')) for p in seeds],ignore_index=True).to_csv(directory/(name+'.csv'),index=False)
    figures=directory/'figures';figures.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                         'figure.dpi':140,'savefig.bbox':'tight'})
    methods=list(metrics.method.unique())
    representative=int(json.loads((directory/'seed_manifest.json').read_text())['representative_seed'])
    if representative in daily.seed.unique():
        fig,ax=plt.subplots(figsize=(8,4.2))
        for name,g in daily[daily.seed==representative].groupby('method',sort=False):ax.plot(g.day,g.equity,label=name,lw=1.4)
        ax.set(xlabel='Simulation day',ylabel='Net wealth (initial = 1)',title=f'Predesignated seed {representative}');ax.legend(fontsize=8)
        fig.savefig(figures/'equity_representative.png');plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4.2))
    for name,g in daily.groupby('method',sort=False):
        grouped=g.groupby('day').equity
        median=grouped.median();lower=grouped.quantile(.1);upper=grouped.quantile(.9)
        line=ax.plot(median.index,median,label=name)[0]
        ax.fill_between(median.index,lower,upper,color=line.get_color(),alpha=.12)
    ax.set(xlabel='Simulation day',ylabel='Net wealth',title='Median and 10–90% quantiles across seeds');ax.legend(fontsize=8)
    fig.savefig(figures/'equity_quantiles.png');plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(12,3.5))
    for ax,column,label in zip(axes,('annual_scaled_utility','sharpe','linear_cost'),('Annual-scaled daily utility','Net conventional Sharpe','Total proportional cost')):
        arrays=[metrics.loc[metrics.method.eq(m),column].dropna().to_numpy() for m in methods]
        for j,values in enumerate(arrays):
            if len(values):ax.scatter(np.full(len(values),j),values,s=18,alpha=.65)
        ax.set_xticks(range(len(methods)),methods,rotation=35,ha='right',fontsize=8);ax.set_ylabel(label)
    fig.tight_layout();fig.savefig(figures/'performance.png');plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(8,6),sharex=True)
    for name,g in daily.groupby('method',sort=False):
        axes[0].plot(g.groupby('day').n_active.mean(),label=name)
    axes[0].set(ylabel='Mean active support size');axes[0].legend(fontsize=8)
    e=events[events.method.eq('E-process')]
    axes[1].plot(e.groupby('day').log_e.max(),marker='o',label='Largest current log E')
    axes[1].axhline(np.log(20),ls='--',color='black',label='Individual threshold')
    axes[1].set(xlabel='Simulation day',ylabel='Current log evidence');axes[1].legend(fontsize=8)
    fig.tight_layout();fig.savefig(figures/'activity_evidence.png');plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,3.5))
    for name,g in daily.groupby('method',sort=False):
        axes[0].plot(g.groupby('day').structural_recall.mean(),label=name)
        axes[1].plot(g.groupby('day').noise_fraction.mean(),label=name)
    axes[0].set(ylabel='Structural recall',xlabel='Simulation day');axes[1].set(ylabel='Independent noise fraction',xlabel='Simulation day')
    axes[0].legend(fontsize=7);fig.tight_layout();fig.savefig(figures/'selection_quality.png');plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,3.5))
    rt=pd.read_csv(directory/'runtime.csv')
    ax.plot(np.arange(len(rt)),rt.seconds,marker='o');ax.set(xlabel='Completed seed-block',ylabel='Wall-clock seconds')
    fig.tight_layout();fig.savefig(figures/'runtime.png');plt.close(fig)
    # Paired performance differences use independent markets, one dot per seed.
    pivot=metrics.pivot(index='seed',columns='method',values='annual_scaled_utility')
    fig,ax=plt.subplots(figsize=(8,3.5))
    others=[m for m in methods if m!='E-process']
    for j,name in enumerate(others):
        difference=(pivot['E-process']-pivot[name]).dropna()
        ax.scatter(np.full(len(difference),j),difference,s=22)
    ax.axhline(0,color='black',lw=.8);ax.set_xticks(range(len(others)),others,rotation=25,ha='right')
    ax.set_ylabel('Paired annual-scaled utility: E-process minus benchmark')
    fig.tight_layout();fig.savefig(figures/'paired_utility.png');plt.close(fig)
    if representative in daily.seed.unique():
        fig,axes=plt.subplots(3,1,figsize=(9,7),sharex=True)
        for ax,name in zip(axes,('Greedy','Repeated-HAC-p','E-process')):
            g=daily[daily.seed.eq(representative)&daily.method.eq(name)]
            image=np.zeros((100,len(g)))
            for k,support in enumerate(g.support):image[json.loads(support),k]=1
            ax.imshow(image,aspect='auto',origin='lower',interpolation='nearest',vmin=0,vmax=1,cmap='Blues',
                      extent=[g.day.min(),g.day.max()+1,0,100])
            ax.set(ylabel='Signal ID',title=name)
        axes[-1].set_xlabel('Simulation day; blue = selected, white = excluded / parked')
        fig.tight_layout();fig.savefig(figures/'active_park_states.png');plt.close(fig)
    detections=pd.read_csv(directory/'detection.csv')
    fig,ax=plt.subplots(figsize=(8,3.5))
    if len(detections):
        for name,g in detections.groupby('method'):
            observed=g[g.detected]
            ax.scatter(observed.event_day,observed.delay_days,label=f'{name}: detected',s=22)
            censored=g[~g.detected]
            ax.scatter(censored.event_day,censored.delay_days,label=f'{name}: censored',marker='x',s=24)
        ax.legend(fontsize=7)
    else:ax.text(.5,.5,'No eligible two-block economic detection event',ha='center',transform=ax.transAxes)
    ax.set(xlabel='Economic event day',ylabel='Delay / right-censoring time (days)')
    fig.tight_layout();fig.savefig(figures/'detection_censored.png');plt.close(fig)
    study_path=directory/'statistical_study.csv'
    if study_path.exists():
        study=pd.read_csv(study_path);fig,axes=plt.subplots(1,2,figsize=(10,3.6))
        for delta,g in study[study.delta>0].groupby('delta'):
            axes[0].plot(g.n,g.adaptive_crossing,label=f'delta={delta:g}')
            axes[0].plot(g.n,g.adaptive_bound,ls='--',alpha=.6)
            axes[1].plot(g.block,g.mean_certificate_regret,label=f'delta={delta:g}')
            axes[1].plot(g.block,g.regret_bound,ls='--',alpha=.6)
        axes[0].set(xlabel='Observations',ylabel='Crossing probability / lower bound');axes[1].set(xlabel='Annual block',ylabel='Certificate regret / upper bound')
        for ax in axes:ax.legend(fontsize=8)
        fig.tight_layout();fig.savefig(figures/'stationary_power.png');plt.close(fig)
    cfg=json.loads((directory/'config_frozen.json').read_text())
    summary=metrics.groupby('method',sort=False).agg(seeds=('seed','count'),utility=('annual_scaled_utility','mean'),
        sharpe=('sharpe','mean'),moves=('moves','mean'),inactive=('inactive_fraction','mean'))
    lines=['# Executed simulation report','',f'Design: {cfg["label"]}; N={cfg["n_assets"]}, p=100, h={cfg["block"]}, years={cfg["years"]}.',
        f'Completed independent seeds: {len(seeds)}. No empirical data used.','',
        'The E-process threshold is individual. No multiplicity correction is applied.','',
        '| Method | Seeds | Annual-scaled utility | Mean net Sharpe | Moves | Inactive fraction |',
        '|---|---:|---:|---:|---:|---:|']
    for name,row in summary.iterrows():
        lines.append(f'| {name} | {int(row.seeds)} | {row.utility:.6g} | {row.sharpe:.4g} | {row.moves:.3g} | {row.inactive:.3g} |')
    ratio=(events.nu2.iloc[0]/pd.concat([pd.read_parquet(b/'score_ledger.parquet',columns=['true_second']) for p in seeds for b in sorted(p.glob('block_*'))]).true_second.mean())
    lines+=['',f'Public nu²={events.nu2.iloc[0]:.8g}; ratio to mean true score second moment={ratio:.6g}.',
        f'Maximum recorded current E-process log evidence={e.log_e.max():.8g}; threshold={np.log(20):.8g}.','',
        'The one-move-per-year rule limits support growth. A null structural coefficient is not an economic null.',
        'Detection events require two consecutive favorable annual blocks within an unchanged comparison; undetected events are censored.',
        'A small pilot cannot establish method superiority. Conventional Sharpe is undefined for inactive paths; see sharpe_hac as a dependence-sensitive alternative.',
        'Intervals in paired_comparisons.csv use independent paired seeds and normal Monte Carlo standard errors; they are descriptive for small batches.','',
        'Figures are generated from the adjacent Parquet/CSV files. Pilot and final seed pools are disjoint.']
    (directory/'report.md').write_text('\n'.join(lines)+'\n')
    return summary
