"""Render the complete independently replayed economic authorization study."""
from pathlib import Path
import hashlib
import json
import subprocess
import numpy as np
import pandas as pd
from scipy.stats import t
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
REPORT=ROOT/'reports/economic_authorization_v1'
OUTPUT=ROOT/'outputs/economic_authorization_v1'
ARMS=['Wait','EconomicQuarter','Hybrid','EconomicFull']
LABELS=['Wait for evidence','Economic 25%','Hybrid 25% then full','Economic full']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    status=json.loads((REPORT/'status.json').read_text())
    verification=json.loads((REPORT/'replay_verification.json').read_text())
    protocol=json.loads((OUTPUT/'protocol_frozen.json').read_text())
    assert status['complete'] and not status['independent_replay_pending']
    assert verification['complete'] and verification['arithmetic_replayed_markets']==100
    assert status['independent_replay_sha256']==sha(REPORT/'replay_verification.json')
    assert status['seed_pool']==list(range(70001,70101))
    assert verification['protocol_sha256']==sha(OUTPUT/'protocol_frozen.json')
    data=pd.read_csv(REPORT/'per_market.csv')
    methods=pd.read_csv(REPORT/'methods.csv').set_index('method')
    contrasts=pd.read_csv(REPORT/'paired_contrasts.csv')
    primary=contrasts.loc[contrasts.primary].iloc[0]
    wealth=[];components=[];initial=[];representative=None
    gamma=protocol['base_config']['gamma'];block=protocol['base_config']['block']
    for record in verification['records']:
        directory=OUTPUT/f"seed_{record['seed']}"
        assert all(sha(directory/name)==digest for name,digest in record['files'].items())
        d=dict(np.load(directory/'ledger.npz'))
        wealth.append(np.vstack([np.ones(4),d['arm_wealth']]))
        w=d['arm_weight'];r=d['returns'];c=d['arm_cost']
        comp=np.array([(w[:,2]-w[:,0])*r,
                       -gamma/2*(w[:,2]**2-w[:,0]**2)*r*r,
                       -(c[:,2]-c[:,0])])*block
        value=comp.mean(axis=1)
        observed=float(data.loc[(data.seed==record['seed'])&(data.method=='Hybrid'),'annual_scaled_utility'].iloc[0]
                       -data.loc[(data.seed==record['seed'])&(data.method=='Wait'),'annual_scaled_utility'].iloc[0])
        assert abs(value.sum()-observed)<1e-12
        components.append(dict(seed=record['seed'],gross=value[0],quadratic_risk=value[1],trading_cost=value[2],total=value.sum()))
        annual=json.loads((directory/'annual_decisions.json').read_text())
        initial.append(annual[0]['provisional_fraction']>0)
        if record['seed']==70001:
            representative=pd.DataFrame(dict(oos_day=np.arange(len(r)),candidate_return=r,shadow_target=d['shadow_weight'],log_e=d['log_e']))
            for a,name in enumerate(ARMS):
                representative[name+'_weight']=w[:,a]
                representative[name+'_wealth']=d['arm_wealth'][:,a]
                representative[name+'_utility']=d['arm_utility'][:,a]
    components=pd.DataFrame(components)
    components.to_csv(REPORT/'utility_decomposition.csv',index=False)
    representative.to_csv(REPORT/'representative_70001.csv',index=False)
    hybrid=data.loc[data.method=='Hybrid'].set_index('seed')
    counts=dict(markets=100,initial_provisional_entries=int(np.sum(initial)),
                evidence_crossings=int(np.sum(hybrid.first_cross_review>=0)),
                executed_full_exposure_authorizations=int(np.sum(hybrid.deployment_day>=0)),
                terminal_first_crossings=int(np.sum(hybrid.first_cross_review==3528)),
                hybrid_negative_pre_deployment_utility_markets=int(np.sum(hybrid.pre_deployment_utility<0)),
                hybrid_negative_conditional_pre_deployment_days=int(hybrid.pre_deployment_negative_conditional_days.sum()))
    (REPORT/'lifecycle_counts.json').write_text(json.dumps(counts,indent=2)+'\n')
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(2,2,figsize=(11,7.4),constrained_layout=True)
    wealth=np.asarray(wealth)
    years=np.arange(wealth.shape[1])/block
    colors=['#606870','#a46805','#00778b','#a63d53']
    for a,(name,label,color) in enumerate(zip(ARMS,LABELS,colors)):
        lo,median,hi=np.quantile(wealth[:,:,a],[.1,.5,.9],axis=0)
        axes[0,0].plot(years,median,label=label,color=color,lw=1.5)
        axes[0,0].fill_between(years,lo,hi,color=color,alpha=.09)
        x=np.sort(data.loc[data.method==name,'annual_scaled_utility'])
        axes[0,1].step(x,np.arange(1,101)/100,where='post',label=label,color=color)
    axes[0,0].set(title='A  Wealth: median and 10--90% market quantiles',xlabel='Out-of-sample years',ylabel='Wealth from 1')
    axes[0,0].legend(fontsize=8)
    axes[0,1].set(title='B  Utility across all 100 markets',xlabel='Mean daily net utility x 252',ylabel='Empirical CDF')
    wide=data.pivot(index='seed',columns='method',values='annual_scaled_utility')
    difference=np.sort(wide.Hybrid-wide.Wait)
    axes[1,0].step(difference,np.arange(1,101)/100,where='post',color=colors[2],lw=1.6)
    axes[1,0].axvline(0,color='black',lw=.7,ls='--')
    axes[1,0].set(title='C  Paired Hybrid minus Wait',xlabel='Difference in mean daily net utility x 252',ylabel='Empirical CDF')
    names=['Gross return','Quadratic risk','Trading costs']
    means=components[['gross','quadratic_risk','trading_cost']].mean().to_numpy()
    ses=components[['gross','quadratic_risk','trading_cost']].std(ddof=1).to_numpy()/10
    axes[1,1].bar(names,means,color=[colors[2],colors[3],colors[0]],yerr=t.ppf(.975,99)*ses,capsize=4)
    axes[1,1].axhline(0,color='black',lw=.7)
    axes[1,1].set(title='D  Mean paired utility components',ylabel='Daily component x 252; pointwise 95% intervals')
    fig.savefig(REPORT/'economic_authorization.png',dpi=190)
    plt.close(fig)
    table=[]
    for name,label in zip(ARMS,LABELS):
        row=methods.loc[name]
        label=label.replace('%',r'\%')
        table.append(f"{label} & {row.mean_utility:.6f} & {row.se_utility:.6f} & {row.mean_wealth:.3f} & {100*row.mean_drawdown:.2f}\\% "+r"\\")
    contrast_rows=[]
    for _,row in contrasts.iterrows():
        name=row['contrast'].replace('EconomicQuarter','Economic 25\\%').replace('EconomicFull','Economic full')
        contrast_rows.append(f"{name} & {row['mean']:.6f} & [{row.lower:.6f}, {row.upper:.6f}] "+r"\\")
    nboost=counts['executed_full_exposure_authorizations']
    qualification=(
        'No full-exposure authorization was executed. Hybrid and the provisional economic method therefore coincide; this experiment supplies no observed evidence-mediated increase.'
        if nboost==0 else
        f'{nboost} markets executed the common full-exposure authorization. This crossing concerns the shadow candidate versus cash, not statistical certification of the increase from a provisional position.')
    tex=r"""\documentclass[10pt,a4paper]{article}
\usepackage[margin=23mm]{geometry}
\usepackage{amsmath,booktabs,graphicx}
\usepackage[hidelinks]{hyperref}
\title{Provisional investment before certification}
\author{PARK--REVIVE: controlled financial simulation}
\date{18 October 2026}
\begin{document}\maketitle
\noindent\textbf{Complete sample.} 100 new independent financial markets, seeds
70001--70100, with 500 assets, 100 candidate signals, one initial training year
and 14 out-of-sample years of 252 dates. Every market is retained.
The training rule selects one candidate initially; its fitted target is then
updated annually from past observed returns. This is a controlled first-candidate
timing experiment, not the full adaptive feature-selection fund.

\paragraph{Rules fixed before the new results.}
Provisional exposure is 25\% of the common target when its penalized training
forecast is positive. Training uncertainty uses a Bartlett HAC standard error
with at most 20 lags and a 1.64485 multiplier. This is a working penalty,
without a finite-sample or post-selection confidence guarantee. A 252-day
holding forecast amortizes entry costs; actual performance charges costs when
incurred. The four methods share the candidate and fitting calendar.
Wait holds cash until the shared evidence-and-economic gate; Hybrid invests
provisionally and subsequently uses the common full target. Economic 25\%
and Economic full do not require evidence. Each fund pays its own proportional
and quadratic impact costs; insolvency is absorbing.

\paragraph{Statistical scope.}
The shared nine-component corrected-tail e-process compares the common full
shadow policy with cash at individual level .05. Crossing 20, a positive
historical score mean and favorable current training forecasts are required
at an annual review; execution begins the following trading date.
The certificate does not establish that increasing an existing provisional
position is beneficial. The experiment follows prior pilot observations and
the user discussion; its numerical protocol was committed before these new
market outputs. It is not a pre-pilot registration.

\begin{center}\small
\begin{tabular}{lrrrr}\toprule
Method & Utility & MC SE & Mean wealth & Mean max DD\\\midrule
""" + '\n'.join(table) + r"""
\bottomrule\end{tabular}\end{center}
\noindent Utility denotes mean daily quadratic utility net of actual costs,
multiplied by 252. It is not annual return or certainty equivalent. Wealth
and drawdown are separate compounded outcomes. The primary comparison is
Hybrid minus Wait; all intervals below use the 100 paired markets and Student
$t_{99}$, with no simultaneous-coverage claim.
\begin{center}\small
\begin{tabular}{lrr}\toprule
Contrast & Mean & Pointwise 95\% interval\\\midrule
""" + '\n'.join(contrast_rows) + r"""
\bottomrule\end{tabular}\end{center}
\noindent Secondary contrasts are unadjusted and descriptive.

\clearpage
\begin{center}\includegraphics[width=\textwidth]{economic_authorization.png}\end{center}
\noindent All panels use all 100 declared markets. Shading in A shows market
quantiles, not confidence intervals. Panel D decomposes the primary realized
utility gap into gross return, quadratic risk and actual trading costs; its
components sum to that gap. Insolvency, if present, is retained using each
fund's actual executed allocation, so common target paths need not imply
equal positions after a fund fails.

\paragraph{Authorization and downside.}
""" + (
        f"Initial provisional entry occurred in {counts['initial_provisional_entries']} of 100 markets. "
        f"The shadow evidence crossed at an annual review in {counts['evidence_crossings']} markets; "
        f"{counts['terminal_first_crossings']} first crossed only at the terminal review. "
        + qualification +
        f" In {counts['hybrid_negative_pre_deployment_utility_markets']} markets, Hybrid accumulated "
        "negative realized utility before the common deployment date (or the full horizon when no deployment occurred). "
        f"The evaluator counted {counts['hybrid_negative_conditional_pre_deployment_days']} pre-deployment "
        "dates with negative conditional utility for Hybrid. These are descriptive downside measures, "
        "not type-I error guarantees or a causal claim about all adaptive selection policies."
    ) + r"""

\paragraph{Independent verification.}
Policy actions, annual information timing, each fund's costs and wealth,
shadow scores, all nine evidence components and summary metrics were
independently replayed for every market. Two fixed seed identifiers
(70001 and 70002) additionally received complete independent DGP and public
moment-certificate replays. Arithmetic consistency does not establish a
general performance or global multiple-testing guarantee.

\paragraph{Interpretation.}
The paired comparison isolates provisional exposure for the specified
common candidate path, evidence clock and economic gate. Its sign and size
apply to this DGP and rule. Extending conclusions to repeated feature
selection, different uncertainty calibration or other provisional limits
requires a separate evaluation. The ongoing original 500-market fund
study is a different experiment and its markets are not pooled here.
\end{document}
"""
    path=REPORT/'economic_authorization_results.tex';path.write_text(tex)
    output=ROOT/'output/pdf';output.mkdir(parents=True,exist_ok=True)
    subprocess.run(['tectonic',str(path),'--outdir',str(output),'--keep-logs'],cwd=REPORT,check=True)
    (REPORT/'interpretation.json').write_text(json.dumps(dict(
        complete=True,counts=counts,primary_contrast=primary.to_dict(),
        qualification=qualification,source_sha256=sha(__file__),
        replay_sha256=sha(REPORT/'replay_verification.json'),
        utility_decomposition_identity_checked_all_100=True,
        financial_scope=protocol['settings']['scope']),indent=2)+'\n')


if __name__=='__main__':
    main()
