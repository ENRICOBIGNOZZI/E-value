"""State-adaptation latency, including censored paths and already-correct states."""
from pathlib import Path
import sys,json,time
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from alpha_lifecycle.core import Settings,Controller,paired_scores
from alpha_lifecycle.dgp import simulate,marginal_mean

def main():
    B,T=500,1800;cfg=Settings();records=[];out=ROOT/'results/delay';out.mkdir(exist_ok=True)
    for i,scenario in enumerate(['permanent_death','revival','correlation_revival']):
        sample=simulate(scenario,'gaussian',B,T,1,800000+i)
        r=sample.returns; sigma=np.maximum(r[:,:cfg.warmup,1:].std(1,ddof=1),.005);scale=cfg.satellite_weight*sigma
        for method in ['always_on','rolling_standalone','rolling_portfolio','e_kill_only','e_restart']:
            ctrl=Controller((B,1),method,cfg); states=np.ones((B,T),bool)
            for t in range(cfg.warmup,T):
                states[:,t]=ctrl.active[:,0]
                z,raw,book=paired_scores(r[:,t],ctrl.active,cfg,scale)
                ctrl.step(z,np.clip((r[:,t,1:]-cfg.fee)/sigma,-1,1))
            for onset,end in [(600,1200),(1200,1800)]:
                if scenario=='permanent_death' and onset==1200:continue
                desired=(marginal_mean(np.ones((B,1),bool),sample.means[:,onset],sample.rho[onset],sample.scale2[:,onset],sample.common_var,cfg)[:,0]>0)
                matches=states[:,onset:end]==desired[:,None]; detected=matches.any(1)
                latency=np.where(detected,np.argmax(matches,axis=1),end-onset)
                # A correct state at onset has latency zero; this is adaptation,
                # not a guarantee that a particular detector caused the decision.
                for b in range(B):
                    records.append(dict(scenario=scenario,method=method,onset=onset,rep=b,
                       direction='revive' if desired[b] else 'park',wrong_at_onset=not bool(matches[b,0]),
                       adapted_by_end=bool(detected[b]),latency_capped=int(latency[b]),
                       censor_horizon=end-onset,correct_fraction=float(matches[b].mean())))
    d=pd.DataFrame(records);d.to_csv(out/'replications.csv',index=False)
    rows=[]
    for keys,g in d.groupby(['scenario','method','onset','direction']):
        risk=g[g.wrong_at_onset];v=g.latency_capped
        rows.append(dict(zip(['scenario','method','onset','direction'],keys))|dict(n=len(g),
            wrong_at_onset=int(len(risk)),adapted_fraction=g.adapted_by_end.mean(),
            capped_delay_mean=v.mean(),capped_delay_se=v.std(ddof=1)/np.sqrt(len(v)),
            adapted_given_wrong=risk.adapted_by_end.mean(),correct_fraction=g.correct_fraction.mean()))
    pd.DataFrame(rows).to_csv(out/'summary.csv',index=False)
    (out/'manifest.json').write_text(json.dumps({'executed':True,'reps':B,'periods':T,
        'seed_base':800000,'definition':'First correct state following regime onset; zero if already correct; censored at next regime end','instantaneous_false_decision_guarantee':False},indent=2))
    print(pd.DataFrame(rows).to_string(index=False))
if __name__=='__main__':main()
