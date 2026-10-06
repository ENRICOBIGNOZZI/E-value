"""JKP-only historical replay; not a publication-date/vintage point-in-time test."""
from __future__ import annotations
import sys, json, zipfile, hashlib, argparse
from pathlib import Path
from dataclasses import asdict, replace
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from alpha_lifecycle.core import Settings, Controller, paired_scores, utility
METHODS=['always_on','rolling_standalone','rolling_portfolio','cusum','hmm','e_cumulative','e_kill_only','e_restart']

def read_official(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as z:
        names=[n for n in z.namelist() if n.endswith('.csv')]
        if len(names)!=1: raise ValueError('Expected one official CSV in archive.')
        d=pd.read_csv(z.open(names[0]),parse_dates=['date'])
    required={'location','name','freq','weighting','date','ret'}
    if not required.issubset(d): raise ValueError('Unexpected JKP schema.')
    if not (d.location.eq('usa').all() and d.freq.eq('monthly').all() and d.weighting.eq('vw_cap').all()):
        raise ValueError('Wrong geography, frequency, or weighting.')
    if d.duplicated(['date','name']).any(): raise ValueError('Duplicate factor-months.')
    # Ret is already the source's signed decimal return. Do not flip direction again.
    return d.pivot(index='date',columns='name',values='ret').sort_index()

def prepare(raw: Path, start='2000-01-01', end='2025-12-31'):
    manifest=json.loads((raw/'source_manifest.json').read_text())
    for entry in manifest['files']:
        if 'sha256' in entry and (raw/entry['name']).exists():
            if hashlib.sha256((raw/entry['name']).read_bytes()).hexdigest()!=entry['sha256']:
                raise ValueError('Raw source hash mismatch.')
    factors=read_official(raw/'all_factors.zip'); market=read_official(raw/'mkt.zip')
    cutoff=pd.Timestamp(start); pre=factors.loc[factors.index<cutoff].tail(60)
    if len(pre)!=60: raise ValueError('A full 60-month burn-in is required.')
    names=sorted(pre.columns[pre.notna().all()].tolist())
    panel=factors.loc[(factors.index>=pre.index[0])&(factors.index<=pd.Timestamp(end)),names]
    panel.insert(0,'core',market.reindex(panel.index)['mkt'])
    if panel.isna().any().any():
        raise ValueError('Post-launch missing returns: do not silently drop future-incomplete factors or fill zeros.')
    if (panel.index.to_period('M').asi8[1:]-panel.index.to_period('M').asi8[:-1]!=1).any():
        raise ValueError('Missing calendar month.')
    audit={'source':'JKP official public monthly USA vw_cap','launch':str(cutoff.date()),
       'train_start':str(pre.index.min().date()),'train_end':str(pre.index.max().date()),
       'evaluation_end':str(panel.index.max().date()),'library_size':int(factors.shape[1]),
       'eligible_size':len(names),'eligible_names':names,'excluded_names':sorted(set(factors.columns)-set(names)),
       'selection':'Complete 60-month history before launch only; no post-launch performance filtering',
       'units':'Decimal returns, signed as supplied; no additional direction multiplication',
       'vintage':'Downloaded October 6, 2026; retrospective library and revised history',
       'interpretation':'Historical out-of-sample-in-time replay, NOT publication/vintage point-in-time',
       'costs':'Assumed recurring and switching return deductions, NOT underlying stock execution estimates',
       'raw_manifest':manifest}
    return panel,audit

def evaluate(panel: pd.DataFrame, cfg: Settings, fee: float, cost: float):
    cfg=replace(cfg,fee=fee,switch_cost=cost); m=panel.shape[1]-1
    r=panel.to_numpy(float); q=cfg.satellite_weight/m
    sd=np.maximum(r[:cfg.warmup,1:].std(0,ddof=1),.005)
    scale=(cfg.scale_mult*q*sd)[None,:]; records=[]; actions=[]; summaries=[]
    for method in METHODS:
        controller=Controller((1,m),method,cfg); previous=controller.active.copy(); logs=[]
        for t in range(cfg.warmup,len(r)):
            active=controller.active.copy(); changes=(active!=previous).sum()
            z,raw,gross=paired_scores(r[t:t+1],active,cfg,scale)
            net=float(gross[0]-cost*q*changes)
            standalone=np.clip((r[t:t+1,1:]-fee)/sd[None,:],-1,1)
            accepted,e=controller.step(z,standalone)
            row={'date':panel.index[t].date().isoformat(),'method':method,'fee':fee,'switch_cost':cost,
                'return_proxy':net,'utility':float(utility(net,cfg.gamma)),
                'active_count':int(active.sum()),'decisions':int(accepted.sum()),
                'implemented_changes':int(changes),'max_evidence':float(e.max()),
                'clipped_fraction':float((np.abs(raw)>=scale).mean())}
            logs.append(row);records.append(row)
            for j in np.flatnonzero(accepted[0]):
                actions.append({'date_observed':row['date'],'effective':'next available month',
                    'method':method,'fee':fee,'switch_cost':cost,'factor':panel.columns[j+1],
                    'action':'REVIVE' if controller.active[0,j] else 'PARK',
                    'evidence':float(e[0,j]),'episode_after_action':int(controller.test.episode[0,j])})
            previous=active
        d=pd.DataFrame(logs); x=d.return_proxy.to_numpy(); u=d.utility.to_numpy()
        wealth=np.cumprod(1+x); peak=np.maximum.accumulate(np.r_[1,wealth])[1:]
        summaries.append({'method':method,'fee':fee,'switch_cost':cost,'months':len(x),'m':m,
            'ann_mean_proxy':12*x.mean(),'ann_vol_proxy':np.sqrt(12)*x.std(ddof=1),
            'ann_sharpe_proxy':np.sqrt(12)*x.mean()/x.std(ddof=1),
            'ann_utility':12*u.mean(),'ann_ce':12*(x.mean()-.5*cfg.gamma*x.var(ddof=0)),
            'max_drawdown_excess_wealth_proxy':float(np.max(1-wealth/peak)),
            'decisions':int(d.decisions.sum()),'implemented_changes':int(d.implemented_changes.sum()),
            'average_active':float(d.active_count.mean()),'clipped_fraction':float(d.clipped_fraction.mean())})
    return records,actions,summaries

def bootstrap_differences(records:pd.DataFrame, reps=2000, block=12):
    """Paired circular blocks of realized policy utilities, not rerun research selection."""
    p=records.pivot(index='date',columns='method',values='utility'); n=len(p); rng=np.random.default_rng(916271)
    starts=rng.integers(0,n,size=(reps,int(np.ceil(n/block))))
    ix=((starts[...,None]+np.arange(block))%n).reshape(reps,-1)[:,:n]
    out=[]
    for method in p.columns:
        x=(p[method]-p.always_on).to_numpy()*12
        b=x[ix].mean(1)
        out.append({'method':method,'ann_delta_utility':x.mean(),'ci025':np.quantile(b,.025),
                    'ci975':np.quantile(b,.975),'block_months':block,'bootstrap_reps':reps})
    return pd.DataFrame(out)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--raw',type=Path,default=ROOT/'data/raw'); args=ap.parse_args()
    out=ROOT/'results/jkp';out.mkdir(parents=True,exist_ok=True)
    panel,audit=prepare(args.raw); cfg=Settings(); allr=[]; alla=[]; alls=[]
    for fee,cost in [(.0005,.001),(0.,0.),(.001,.0025)]:
        r,a,s=evaluate(panel,cfg,fee,cost);allr+=r;alla+=a;alls+=s
    records=pd.DataFrame(allr); summary=pd.DataFrame(alls)
    records.to_csv(out/'monthly.csv',index=False);pd.DataFrame(alla).to_csv(out/'actions.csv',index=False)
    summary.to_csv(out/'summary.csv',index=False)
    mainr=records[(records.fee==cfg.fee)&(records.switch_cost==cfg.switch_cost)]
    bootstrap_differences(mainr).to_csv(out/'paired_bootstrap.csv',index=False)
    audit.update({'executed':True,'simulated':False,'settings':asdict(cfg),'evaluated_methods':METHODS,
                  'test_periods':len(panel)-cfg.warmup,'raw_data_redistributed_in_repo':False})
    (out/'manifest.json').write_text(json.dumps(audit,indent=2))
    print(summary.to_string(index=False));print('JKP_REPLAY_COMPLETED',len(panel)-cfg.warmup,'months',panel.shape[1]-1,'factors')
if __name__=='__main__':main()
