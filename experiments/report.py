"""Generate manuscript tables and individual figures from executed CSV outputs."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]; FIG=ROOT/'figures';TAB=ROOT/'paper/tables'
FIG.mkdir(exist_ok=True);TAB.mkdir(parents=True,exist_ok=True)
LABEL={'always_on':'Always on','rolling_standalone':'Standalone rolling','rolling_portfolio':'Portfolio rolling','cusum':'CUSUM heuristic','hmm':'HMM heuristic','e_cumulative':'Cumulative e','e_kill_only':'Retire only','e_restart':'Retire + revive'}
SL={'permanent_death':'Permanent death','revival':'Mean revival','negative_hedge':'Negative-return hedge','positive_redundant':'Positive redundant','correlation_revival':'Correlation revival','gradual':'Gradual correlation','repeated':'Repeated correlation'}

def save(fig,name):
    fig.tight_layout();fig.savefig(FIG/(name+'.pdf'),bbox_inches='tight');fig.savefig(FIG/(name+'.png'),dpi=170,bbox_inches='tight');plt.close(fig)
def table(name,headers,rows,align=None):
    align=align or ('l'+'r'*(len(headers)-1));text='\\begin{tabular}{'+align+'}\n\\toprule\n'+' & '.join(headers)+' \\\\\n\\midrule\n'
    text+='\n'.join(' & '.join(map(str,row))+' \\\\' for row in rows)+'\n\\bottomrule\n\\end{tabular}\n'
    (TAB/(name+'.tex')).write_text(text)

def main():
    d=pd.read_csv(ROOT/'results/main/summary.csv'); g=d[d.noise=='gaussian']; methods=['rolling_standalone','rolling_portfolio','e_kill_only','e_restart']
    rows=[]
    for s in SL:
        row=[SL[s]]
        for m in methods:
            x=g[(g.scenario==s)&(g.method==m)].iloc[0]
            row.append(f'{1e4*x.delta_utility:.2f} ({1e4*x.delta_utility_se:.2f})')
        rows.append(row)
    table('main_gaussian',['Scenario','Standalone','Portfolio','Retire only','Retire + revive'],rows)
    fig,ax=plt.subplots(figsize=(9,4.8)); x=np.arange(len(SL));width=.25
    for k,m in enumerate(['rolling_portfolio','e_kill_only','e_restart']):
        v=g[g.method==m].set_index('scenario').loc[list(SL)]
        ax.bar(x+(k-1)*width,v.delta_utility*1e4,width,yerr=1.96*v.delta_utility_se*1e4,label=LABEL[m],capsize=2)
    ax.axhline(0,linewidth=.8);ax.set_xticks(x,list(SL.values()),rotation=23,ha='right');ax.set_ylabel('Utility gain over always on (10,000 x per-period utility)');ax.legend();save(fig,'simulation_utility')
    n=pd.read_csv(ROOT/'results/null/null_validation.csv');n=n[n.method=='e_restart']
    rows=[[r.noise.replace('_',' '),int(r.reps),int(r.lifetime_any_switch),f'{100*r.rate:.2f}',f'[{100*r.lo:.2f}, {100*r.hi:.2f}]'] for r in n.itertuples()]
    table('null',['Null experiment','Paths','Any switch','Rate (\\%)','95\\% interval'],rows)
    fig,ax=plt.subplots(figsize=(7,3.8));x=np.arange(len(n));ax.errorbar(x,n.rate*100,yerr=np.vstack(((n.rate-n.lo)*100,(n.hi-n.rate)*100)),fmt='o',capsize=5)
    ax.axhline(5,linestyle='--',label='Lifetime upper bound: 5%');ax.set_xticks(x,['Bounded independent','Predictable volatility']);ax.set_ylabel('Paths with any switch (%)');ax.set_ylim(0,5.8);ax.legend();save(fig,'null_control')
    j=pd.read_csv(ROOT/'results/jkp/summary.csv'); j=j[(j.fee==.0005)&(j.switch_cost==.001)]
    base=j[j.method=='always_on'].ann_utility.iloc[0]
    rows=[[LABEL[r.method],f'{100*r.ann_mean_proxy:.2f}',f'{100*r.ann_vol_proxy:.2f}',f'{r.ann_sharpe_proxy:.3f}',f'{1e4*(r.ann_utility-base):.2f}',int(r.implemented_changes)] for r in j.itertuples()]
    table('jkp',['Method','Mean (\\%)','Vol. (\\%)','Sharpe','Utility gain (bp/yr)','Switches'],rows)
    b=pd.read_csv(ROOT/'results/jkp/paired_bootstrap.csv')
    table('jkp_ci',['Method','Utility gain (bp/yr)','95\\% paired-block interval'],[[LABEL[r.method],f'{1e4*r.ann_delta_utility:.2f}',f'[{1e4*r.ci025:.2f}, {1e4*r.ci975:.2f}]'] for r in b.itertuples()])
    mr=pd.read_csv(ROOT/'results/jkp/monthly.csv',parse_dates=['date']);mr=mr[(mr.fee==.0005)&(mr.switch_cost==.001)]
    p=mr.pivot(index='date',columns='method',values='utility');fig,ax=plt.subplots(figsize=(8,4))
    for m in ['rolling_portfolio','cusum','e_restart']:ax.plot(p.index,1e4*(p[m]-p.always_on).cumsum(),label=LABEL[m])
    ax.set_ylabel('Cumulative utility difference (x10,000)');ax.set_xlabel('Calendar year');ax.legend();save(fig,'jkp_utility')
    p=mr.pivot(index='date',columns='method',values='active_count');fig,ax=plt.subplots(figsize=(8,4))
    for m in ['rolling_portfolio','hmm','e_restart']:ax.plot(p.index,p[m],label=LABEL[m])
    ax.set_ylabel('Active factors out of 153');ax.set_xlabel('Calendar year');ax.legend();save(fig,'jkp_activity')
    delay=pd.read_csv(ROOT/'results/delay/summary.csv');rows=[]
    for r in delay[(delay.scenario=='correlation_revival')&delay.method.isin(['rolling_portfolio','e_kill_only','e_restart'])].itertuples():
        rows.append([LABEL[r.method],r.direction,int(r.n),f'{100*r.adapted_fraction:.1f}',f'{r.capped_delay_mean:.1f}',f'{r.capped_delay_se:.1f}'])
    table('delay',['Method','Direction','Paths','Adapted (\\%)','Capped delay','MC SE'],rows)
    s=pd.concat([pd.read_csv(ROOT/f'results/scale_{m}/summary.csv') for m in [20,50,100,150]])
    table('scaling',['$M$','Method','Utility gain','MC SE','Switches','Active fraction'],[[int(r.m),LABEL[r.method],f'{1e4*r.delta_utility:.2f}',f'{1e4*r.delta_utility_se:.2f}',f'{r.switches:.2f}',f'{r.active_fraction:.3f}'] for r in s[s.method!='always_on'].itertuples()])
    dep=pd.read_csv(ROOT/'results/dependence/summary.csv');table('dependence',['Scenario','Noise','Method','Utility gain','MC SE'],[[SL[r.scenario],r.noise.upper(),LABEL[r.method],f'{1e4*r.delta_utility:.2f}',f'{1e4*r.delta_utility_se:.2f}'] for r in dep[dep.method.isin(['rolling_portfolio','e_restart'])].itertuples()])
    dg=pd.read_csv(ROOT/'results/jkp_diagnostics/summary.csv');rows=[]
    for design in dg.design.unique():
        v=dg[dg.design==design];base=v[v.method=='always_on'].ann_utility.iloc[0]
        for r in v[v.method.isin(['always_on','rolling_portfolio','e_restart'])].itertuples():rows.append([design.replace('_',' '),LABEL[r.method],int(r.m),f'{r.ann_sharpe_proxy:.3f}',f'{1e4*(r.ann_utility-base):.2f}',int(r.implemented_changes)])
    table('diagnostics',['Book','Method','$M$','Sharpe','Utility gain (bp/yr)','Switches'],rows)
    traces=pd.read_csv(ROOT/'results/main/first_path.csv');fig,ax=plt.subplots(figsize=(8,4))
    for m in ['rolling_portfolio','e_kill_only','e_restart']:
        v=traces[(traces.scenario=='correlation_revival')&(traces.noise=='gaussian')&(traces.method==m)]
        # Offset is explicitly displayed; each series is binary, not allocation size.
        k=['rolling_portfolio','e_kill_only','e_restart'].index(m)
        ax.step(v.t,v.active_fraction+1.3*k,where='post',label=LABEL[m])
    ax.axvline(600,linestyle=':');ax.axvline(1200,linestyle=':');ax.set_yticks([.5,1.8,3.1],[LABEL[m] for m in ['rolling_portfolio','e_kill_only','e_restart']]);ax.set_xlabel('Simulation period');ax.set_title('Replication 0, fixed in advance: lower level parked, upper active');save(fig,'correlation_path')
    print('REPORT_COMPLETED',len(list(FIG.glob('*.pdf'))),'figures',len(list(TAB.glob('*.tex'))),'tables')
if __name__=='__main__':main()
