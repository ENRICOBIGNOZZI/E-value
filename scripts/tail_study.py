"""Controlled skew-null diagnostics and reporting for the declared first-entry audit."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from park_revive_extensions.tail_betting import TailMixture
from park_revive.experiments import wilson
from park_revive.backtest import atomic_json


def controlled(directory,replications=10000,steps=2000):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(420001);rows=[]
    for delta in (0.,.02,.05):
        corrected=TailMixture(replications)
        naive_log=np.zeros(replications);past=np.zeros(replications)
        crossed=np.zeros(replications,bool);naive_crossed=crossed.copy()
        for t in range(steps):
            probability=np.where(past>=0,.005,.02)
            negative=np.full(replications,-4/3)+delta
            positive=probability*(4/3)/(1-probability)+delta
            second=probability*negative**2+(1-probability)*positive**2
            fourth=probability*negative**4+(1-probability)*positive**4
            prepared=corrected.prepare(second,fourth)
            if delta==0:
                levels,biases,bets,_=prepared
                expected=probability[None,:]*np.maximum(negative[None,:],-levels)+(1-probability[None,:])*np.maximum(positive[None,:],-levels)-biases
                assert np.max(1+bets*expected)<=1+1e-12
            y=np.where(rng.random(replications)<probability,negative,positive)
            corrected.update(y,prepared)
            # Deliberately invalid negative control, never an investment-method arm.
            level=fourth**.25
            naive_log+=np.log1p(.75*np.maximum(y,-level)/level)
            past+=y
            if (t+1)%100==0:
                crossed|=corrected.log_e>=np.log(20)
                naive_crossed|=naive_log>=np.log(20)
                lo,hi=wilson(int(crossed.sum()),replications)
                rows.append(dict(delta=delta,observations=t+1,replications=replications,
                    corrected_crossing=float(crossed.mean()),ci_low=lo,ci_high=hi,
                    naive_uncorrected_crossing=float(naive_crossed.mean()),seed=420001))
        print(f'controlled delta={delta:g}: corrected={crossed.mean():.5f}; invalid negative control={naive_crossed.mean():.5f}',flush=True)
    pd.DataFrame(rows).to_csv(directory/'controlled_tail_study.csv',index=False)
    atomic_json(directory/'controlled_protocol.json',dict(seed=420001,replications=replications,
        steps=steps,looks_every=100,deltas=[0.,.02,.05],individual_alpha=.05,
        null='predictable skewed two-point law with conditional mean zero',
        negative_control='lower-winsorized linear bettor WITHOUT bias correction: intentionally invalid',
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))


def report(directory):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    directory=Path(directory);protocol=json.loads((directory/'protocol_frozen.json').read_text())
    complete=[p for p in sorted(directory.glob('seed_*')) if p.is_dir() and (p/'summary.csv').exists()]
    if not complete:raise ValueError('No completed mechanism markets')
    summary=pd.concat([pd.read_csv(p/'summary.csv') for p in complete],ignore_index=True)
    events=pd.concat([pd.read_csv(p/'annual_events.csv') for p in complete],ignore_index=True)
    summary.to_csv(directory/'summary_by_seed.csv',index=False)
    events.to_csv(directory/'annual_events.csv',index=False)
    selected=[]
    for row in summary.itertuples():
        if row.first_entry_day<0:continue
        candidates=events[events.seed.eq(row.seed)&events.arm.eq(row.arm)&events.day.eq(row.first_entry_day)&events.eligible]
        candidate=candidates.sort_values(['mean_score','signal'],ascending=[False,True]).iloc[0]
        selected.append(dict(seed=row.seed,arm=row.arm,day=row.first_entry_day,signal=candidate.signal,
            true_current_mean=candidate.true_current_mean,true_block_mean=candidate.true_block_mean,
            episode_mean_score=candidate.mean_score,log_e=candidate.log_e))
    pd.DataFrame(selected,columns=['seed','arm','day','signal','true_current_mean','true_block_mean','episode_mean_score','log_e']).to_csv(directory/'first_entries.csv',index=False)
    figures=directory/'figures';figures.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.right':False,'axes.spines.top':False,'figure.dpi':160,'savefig.bbox':'tight'})
    cfg=protocol['config'];n=summary.seed.nunique();arms=protocol['arms']
    figure,axes=plt.subplots(1,2,figsize=(11,4))
    result=[]
    for arm in arms:
        g=summary[summary.arm.eq(arm)];success=g.first_entry_day>=0
        lo,hi=wilson(int(success.sum()),n)
        result.append(dict(arm=arm,seeds=n,markets_with_entry=int(success.sum()),
            entry_rate=float(success.mean()),wilson_low=lo,wilson_high=hi,
            median_first_entry_oos_year=float(np.median((g.loc[success,'first_entry_day']-cfg['block'])/cfg['block'])) if success.any() else np.nan,
            max_annual_log_e=float(g.max_annual_log_e.max())))
        years=np.arange(1,cfg['years'])
        rates=[np.mean((g.first_entry_day>=0)&(g.first_entry_day<=(year+1)*cfg['block'])) for year in years]
        axes[0].step(years,rates,where='post',label=arm)
        evidence=events[events.arm.eq(arm)].groupby('day').log_e.max()
        axes[1].plot((evidence.index-cfg['block'])/cfg['block'],evidence.values,label=arm)
    axes[0].set(xlabel='OOS years',ylabel='Fraction of markets with at least one eligible entry',ylim=(-.02,1.02))
    axes[1].axhline(np.log(20),ls='--',color='black',lw=1)
    axes[1].set(xlabel='OOS years',ylabel='Largest current annual log evidence')
    for ax in axes:ax.legend(fontsize=7)
    figure.tight_layout();figure.savefig(figures/'first_entry_feasibility.png');plt.close(figure)
    result=pd.DataFrame(result);result.to_csv(directory/'entry_summary.csv',index=False)
    controls=directory/'controlled_tail_study.csv'
    if controls.exists():
        frame=pd.read_csv(controls);figure,axes=plt.subplots(1,2,figsize=(10,3.8))
        null=frame[frame.delta.eq(0)]
        axes[0].plot(null.observations,null.corrected_crossing,label='Corrected mixture')
        axes[0].plot(null.observations,null.naive_uncorrected_crossing,label='Invalid: correction omitted')
        axes[0].axhline(.05,color='black',ls='--',label='Individual 5%')
        axes[0].set(xlabel='Observations',ylabel='Controlled null crossing rate')
        for delta,g in frame[frame.delta>0].groupby('delta'):
            line=axes[1].plot(g.observations,g.corrected_crossing,label=f'delta={delta:g}')[0]
            axes[1].fill_between(g.observations,g.ci_low,g.ci_high,color=line.get_color(),alpha=.15)
        axes[1].set(xlabel='Observations',ylabel='Corrected-mixture crossing rate')
        for ax in axes:ax.legend(fontsize=7)
        figure.tight_layout();figure.savefig(figures/'controlled_tail_calibration.png');plt.close(figure)
    text=['# Corrected-tail first-entry mechanism study','',
        f'Completed fresh full-size markets: **{n}**. N={cfg["n_assets"]}, p=100, h={cfg["block"]}, {cfg["years"]} years.',
        'The policies and realized scores are identical across all test arms. No post-entry trading is simulated.','',
        '| Arm | Markets with entry | Denominator | Rate | Wilson 95% interval | Maximum annual log E |',
        '|---|---:|---:|---:|---|---:|']
    for row in result.itertuples():
        text.append(f'| {row.arm} | {row.markets_with_entry} | {row.seeds} | {row.entry_rate:.3f} | [{row.wilson_low:.3f}, {row.wilson_high:.3f}] | {row.max_annual_log_e:.5g} |')
    text+=['','The entry fraction is a search outcome across 100 individual tests. It is **not** an individual-test power estimate or a globally controlled rejection probability.',
        'The tail method uses certified fourth score moments (eighth return moments); baseline Catoni needs only second score moments.',
        'Geometric certificates use public function values and holdings plus aggregate coefficient/loading bounds, never hidden individual coefficients or regimes.',
        'Current economic signs and block-average signs for the selected first candidate are in first_entries.csv. They are descriptive, not null labels.',
        'New test design and seed pool were declared after the old pilot but before these markets. This is exploratory mechanism evidence, not a full-strategy final study.']
    (directory/'report.md').write_text('\n'.join(text)+'\n')
    print(result.to_string(index=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['controlled','report'])
    p.add_argument('--output',default='outputs/park_revive_tail_v1/first_entry')
    p.add_argument('--replications',type=int,default=10000);p.add_argument('--steps',type=int,default=2000)
    args=p.parse_args()
    with threadpool_limits(limits=1):
        if args.command=='controlled':controlled(args.output,args.replications,args.steps)
        else:report(args.output)
