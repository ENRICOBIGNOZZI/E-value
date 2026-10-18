#!/usr/bin/env python3
"""Link the complete audited economic-authorization experiment to the paper."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    folder=ROOT/'reports/economic_authorization_v1'
    reporting=json.loads((folder/'reporting_verification.json').read_text())
    verification=json.loads((folder/'replay_verification.json').read_text())
    status=json.loads((folder/'status.json').read_text())
    assert reporting['complete'] and verification['complete']
    assert not status['independent_replay_pending']
    assert status['seed_pool']==list(range(70001,70101))
    assert verification['arithmetic_replayed_markets']==100
    assert reporting['replay_sha256']==sha(folder/'replay_verification.json')
    for name,digest in reporting['artifacts_sha256'].items():
        assert sha(ROOT/name)==digest,name
    records=verification['records']
    assert [r['seed'] for r in records]==list(range(70001,70101))
    wealth=[]
    for record in records:
        directory=ROOT/f"outputs/economic_authorization_v1/seed_{record['seed']}"
        assert all(sha(directory/name)==digest for name,digest in record['files'].items())
        with np.load(directory/'ledger.npz') as d:
            wealth.append(np.vstack([np.ones(4),d['arm_wealth']]))
    data=pd.read_csv(folder/'per_market.csv')
    means=pd.read_csv(folder/'methods.csv').set_index('method')
    contrasts=pd.read_csv(folder/'paired_contrasts.csv')
    counts=json.loads((folder/'lifecycle_counts.json').read_text())
    primary=contrasts.loc[contrasts.primary].iloc[0]
    other=contrasts.loc[contrasts['contrast'].eq('Hybrid minus EconomicFull')].iloc[0]
    arms=['Wait','EconomicQuarter','Hybrid','EconomicFull']
    labels=['Wait','Economic quarter','Hybrid','Economic full']
    colors=['#606870','#a46805','#00778b','#a63d53']
    wealth=np.asarray(wealth)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(7.2,3.35),constrained_layout=True)
    years=np.arange(wealth.shape[1])/252
    for a,label,color in zip(range(4),labels,colors):
        lo,median,hi=np.quantile(wealth[:,:,a],[.1,.5,.9],axis=0)
        axes[0].plot(years,median,label=label,color=color,lw=1.4)
        axes[0].fill_between(years,lo,hi,color=color,alpha=.08)
    axes[0].set(xlabel='OOS years',ylabel='Wealth from 1',title='Common-candidate fund paths')
    axes[0].legend(fontsize=8,frameon=False)
    wide=data.pivot(index='seed',columns='method',values='annual_scaled_utility')
    difference=np.sort(wide.Hybrid-wide.Wait)
    axes[1].step(difference,np.arange(1,101)/100,where='post',color=colors[2],lw=1.5)
    axes[1].axvline(0,color='black',ls='--',lw=.7)
    axes[1].set(xlabel='Paired net utility difference x 252',ylabel='Empirical CDF',
                title='Hybrid minus Wait')
    image=ROOT/'paper/figures/economic_authorization.png'
    fig.savefig(image,dpi=220);plt.close(fig)
    rows=[]
    for arm,label in zip(arms,labels):
        row=means.loc[arm]
        rows.append(f"{label} & {row.mean_utility:.6f} & {row.se_utility:.6f} & {row.mean_wealth:.3f} & {100*row.mean_drawdown:.2f}\\% "+r"\\")
    tex=r"""\begin{table}[H]\centering\small
\begin{tabular}{lrrrr}\toprule
Method & Net utility & MC SE & Mean wealth & Mean max DD\\\midrule
""" + '\n'.join(rows) + r"""
\bottomrule\end{tabular}
\caption{Controlled exposure timing on all 100 fresh markets. Utility is mean
daily realized quadratic utility net of actual costs, multiplied by 252;
it is not annual return or certainty equivalent. Wealth starts at one and
compounds over 14 OOS years. DD denotes each path's maximum drawdown,
averaged across markets. All four methods retain noncrossings and losses.}
\label{tab:economic-authorization}
\end{table}
""" + (
        "The primary paired Hybrid-minus-Wait utility difference is $" + f"{primary['mean']:.6f}" + "$, "
        f"with approximate pointwise 95\\% Monte Carlo interval $[{primary.lower:.6f},{primary.upper:.6f}]$. "
        "Hybrid-minus-Economic-full is $" + f"{other['mean']:.6f}" + "$ "
        f"with interval $[{other.lower:.6f},{other.upper:.6f}]$; this secondary contrast is unadjusted. "
        f"Evidence crosses at an annual review in {counts['evidence_crossings']} markets. "
        f"{counts['executed_full_exposure_authorizations']} full-exposure authorizations are executed; "
        f"{counts['terminal_first_crossings']} first crossings occur only at the terminal review. "
        "Intervals use the 100 paired markets and Student $t_{99}$, not daily observations.\n\n"
        f"All {counts['initial_provisional_entries']} markets initiate provisional exposure. "
        f"In {counts['hybrid_negative_pre_deployment_utility_markets']} markets the provisional period "
        "has negative cumulative realized utility, but the evaluator records "
        f"{counts['hybrid_negative_conditional_pre_deployment_days']} pre-deployment dates with "
        "negative conditional utility. These descriptive observations do not certify an absence "
        "of downside risk. "
        f"All {counts['annual_targets_at_leverage_cap']:,} annual target fits bind at the leverage cap; "
        f"{counts['markets_with_changing_target']} markets change their target. "
        "Consequently the experiment identifies exposure timing for selected positions, "
        "without validating the uncertainty calibration or adaptive target sizing.\n\n"
    ) + r"""\begin{figure}[H]\centering
\includegraphics[width=\linewidth]{figures/economic_authorization.png}
\caption{All 100 new markets. Left: median wealth with 10th--90th market
quantiles, not confidence bands. Right: paired Hybrid-minus-Wait utility
differences. The candidate and fitting schedule are common; each fund pays
its own actual costs.}
\label{fig:economic-authorization}
\end{figure}
\FloatBarrier
"""
    generated=ROOT/'paper/generated_economic_authorization_results.tex'
    if generated.exists() and generated.read_text()!=tex:
        raise ValueError('Existing economic manuscript numeric source differs')
    generated.write_text(tex)
    packet=ROOT/'reports/economic_authorization_manuscript_packet'
    packet.mkdir(exist_ok=True)
    record=dict(complete=True,markets=100,seeds=list(range(70001,70101)),
                script_sha256=sha(Path(__file__)),
                reporting_verification_sha256=sha(folder/'reporting_verification.json'),
                replay_verification_sha256=sha(folder/'replay_verification.json'),
                files_sha256={str(p.relative_to(ROOT)):sha(p) for p in [generated,image]},
                scope='Manuscript display of the same completed 100-market controlled experiment; no new markets or replay checks. Original final fund study remains separate.')
    (packet/'verification.json').write_text(json.dumps(record,indent=2)+'\n')


if __name__=='__main__':
    main()
