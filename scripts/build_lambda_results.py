"""Build manuscript tables/figure from the audited, corrected lambda experiment."""
import json
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
import shutil
import numpy as np
import pandas as pd


def generate(root):
    results=root/'reports/lambda_power_v2_results';paper=root/'paper'
    audit=json.loads((results/'verification.json').read_text())
    if not audit['all_model_calibrations_pass']:raise ValueError('Unresolved working-model power discrepancy')
    data=pd.read_csv(results/'summary.csv');cfg=json.loads((results/'status.json').read_text())['config']
    methods=[('Past-mean certificate','Past-mean certificate'),('Fixed certificate','Fixed certificate'),
             ('Fixed log growth','Fixed log growth'),('One-block power','One-block power'),
             ('DP primary','Horizon DP'),('DP refinement','Refined horizon DP')]
    def row(name,mean,horizon):
        selected=f'{name} H={horizon}' if name.startswith('DP ') else name
        return data[data.method.eq(selected)&data['mean'].eq(mean)&data.observations.eq(horizon)].iloc[0]
    horizons=[h*cfg['block'] for h in cfg['horizon_blocks']]
    def percent(r):
        return str((Decimal(int(r.crossings))*100/Decimal(int(r.replications))).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
    lines=[r'\begin{table}[H]\centering\small',r'\begin{tabular}{lrrrrrr}',r'\toprule',
        r'& \multicolumn{3}{c}{Null rejection (\%)} & \multicolumn{3}{c}{Design power (\%)} \\',
        r'Rule & 400 & 800 & 1600 & 400 & 800 & 1600 \\',r'\midrule']
    for name,label in methods:
        numbers=[percent(row(name,mean,horizon)) for mean in (0.,cfg['design_mean']) for horizon in horizons]
        lines.append(label+' & '+' & '.join(numbers)+r' \\')
    lines += [r'\bottomrule\end{tabular}',
        r'\caption{Review-time rejection fractions from 20,000 paths per law. The null has mean zero and the design alternative mean .1, both with variance one. Every rule has the same individual nominal 5\% bound, public moment cap and bet/review calendar; observed null rates differ. Each horizon-DP entry uses a separate policy targeting that deadline.}\label{tab:lambda-power}\end{table}']
    paired=pd.read_csv(results/'paired_comparisons.csv')
    comparison=paired[paired['mean'].eq(.1)&paired.observations.eq(400)&paired.model.eq('primary')&paired.reference.eq('Past-mean certificate')].iloc[0]
    early=row('DP primary',.1,400);base=row('Past-mean certificate',.1,400)
    lines.append(f'At 400 observations the horizon rule crosses on {early.crossings:.0f}/20000 paths '
        f'({percent(early)}\\%) versus {base.crossings:.0f}/20000 ({percent(base)}\\%) for the past-mean rule. '
        f'The paired difference is {(Decimal(int(early.crossings)-int(base.crossings))*100/Decimal(int(early.replications))).quantize(Decimal(".01"),rounding=ROUND_HALF_UP)} percentage points '
        f'(Monte Carlo 95\\% interval [{100*comparison.ci_low:.2f}, {100*comparison.ci_high:.2f}]). '
        'This compares a common nominal level, not matched actual null-crossing probabilities. '
        'At the longest deadline the fixed log-growth rule does not outperform the fixed certificate rule, '
        'illustrating that the objectives differ. The repeatedly greedy one-block rule also falls short '
        'of the deadline-specific policy.')
    lines.append('The refined-grid powers closely agree with the primary implementation, and all six '
        'predicted-versus-observed design-power checks pass the declared numerical-plus-Monte-Carlo audit. '
        'All pre-block horizon-policy and fixed stakes, every first crossing, and the complete summary '
        f'are independently reconstructed ({audit["scalar_checks"]:,} scalar checks). Direct multiplicative '
        'score replay covers the first sixteen paths under each law; it is not a replay of every score path. '
        f'Its maximum log-capital discrepancy is {audit["max_prefix_log_capital_error"]:.2e}. '
        'The stronger alternatives .2 and .3 are retained in the numeric report. '
        'No result supplies a power optimum for a changing financial score law or improved fund performance.')
    plot(data,cfg,results,methods,row)
    shutil.copyfile(results/'lambda_power.png',paper/'figures/lambda_power.png')
    lines += [r'\begin{figure}[H]\centering',r'\includegraphics[width=.97\linewidth]{figures/lambda_power.png}',
        r'\caption{Top: observed design-power and null-crossing fractions with pointwise Wilson 95\% intervals. Each DP point uses its own target horizon; the connected points are not one policy monitored at three dates. Bottom: the primary working-model bet as a function of pre-block log capital and remaining blocks. Bets and decisions share the 100-observation calendar.}\label{fig:lambda-power}\end{figure}']
    (paper/'generated_lambda_results.tex').write_text('\n\n'.join(lines)+'\n')


def plot(data,cfg,destination,methods,row):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    with matplotlib.rc_context():
        matplotlib.rcdefaults()
        _plot(data,cfg,destination,methods,row,plt)


def _plot(data,cfg,destination,methods,row,plt):
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig=plt.figure(figsize=(8.3,7.2));grid=fig.add_gridspec(2,2,height_ratios=[1,1.1])
    axes=[fig.add_subplot(grid[0,0]),fig.add_subplot(grid[0,1])];heat=fig.add_subplot(grid[1,:])
    horizons=[h*cfg['block'] for h in cfg['horizon_blocks']]
    short=['Past-mean','Fixed certificate','Fixed log growth','One-block power','Horizon DP','DP refined']
    for j,(name,label) in enumerate(methods):
        for ax,mean in zip(axes,[cfg['design_mean'],0.]):
            rows=[row(name,mean,h) for h in horizons]
            y=np.array([r.power for r in rows]);low=np.array([r.wilson_low for r in rows]);high=np.array([r.wilson_high for r in rows])
            ax.errorbar(horizons,y,yerr=np.array([y-low,high-y]),marker='o',markersize=3,
                color=f'C{j}',linewidth=1.1,label=short[j],capsize=2)
    axes[0].set(title='Design alternative: mean .1',ylabel='Crossing fraction',ylim=(0,1.03))
    axes[1].axhline(cfg['alpha'],color='black',linestyle='--',linewidth=.9)
    axes[1].set(title='Boundary null: mean 0',ylim=(0,.055))
    for ax in axes:ax.set(xlabel='Target observations',xticks=horizons)
    axes[0].legend(fontsize=7,loc='lower right')
    with np.load(destination/'model_primary.npz') as model:
        states=model['states'];select=(states>=-5)&(states<np.log(1/cfg['alpha']))
        bets=model['actions'][model['policy'][1:,select]]
        mesh=heat.pcolormesh(states[select],np.arange(1,len(bets)+1),bets,shading='nearest',cmap='viridis')
    heat.axvline(0,color='white',linestyle='--',linewidth=.8)
    heat.set(xlabel='Current log capital (0 corresponds to initial E = 1)',ylabel='Remaining blocks',title='Predictable horizon-power bet')
    fig.colorbar(mesh,ax=heat,label='Lambda',pad=.025)
    fig.tight_layout();fig.savefig(destination/'lambda_power.png',dpi=180);plt.close(fig)


if __name__=='__main__':generate(Path(__file__).resolve().parents[1])
