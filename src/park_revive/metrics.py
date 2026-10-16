import numpy as np
import pandas as pd
from .pvalues import hac_variance


def path_metrics(frame, block):
    r = frame.net.to_numpy()
    sd = np.std(r,ddof=1) if len(r)>1 else np.nan
    lrv = hac_variance(r)
    equity = np.r_[1.,frame.equity.to_numpy()]
    drawdown = 1-equity/np.maximum.accumulate(equity)
    return dict(mean_utility=float(frame.utility.mean()),annual_scaled_utility=float(block*frame.utility.mean()),
                mean_net=float(r.mean()),sharpe=float(np.sqrt(block)*r.mean()/sd) if sd>1e-15 else np.nan,
                sharpe_hac=float(np.sqrt(block)*r.mean()/np.sqrt(lrv)) if lrv>1e-30 else np.nan,
                final_equity=float(equity[-1]),geometric_return=float(equity[-1]**(block/len(r))-1),
                max_drawdown=float(drawdown.max()),turnover=float(frame.turnover.sum()),
                linear_cost=float(frame.linear_cost.sum()),impact_cost=float(frame.impact_cost.sum()),
                inactive_fraction=float((frame.leverage<=1e-10).mean()),mean_active=float(frame.n_active.mean()),
                structural_precision=float(frame.structural_precision.mean()),structural_recall=float(frame.structural_recall.mean()),
                noise_fraction=float(frame.noise_fraction.mean()),proxy_fraction=float(frame.proxy_fraction.mean()),
                state_matched_regret=float(frame.state_matched_regret.mean()),insolvent=bool(frame.insolvent.any()))


def paired_table(metrics):
    rows=[]
    for metric in ('mean_utility','sharpe','sharpe_hac','final_equity'):
        pivot=metrics.pivot(index='seed',columns='method',values=metric)
        for other in pivot.columns:
            if other=='E-process':continue
            delta=(pivot['E-process']-pivot[other]).dropna()
            n=len(delta)
            se=float(delta.std(ddof=1)/np.sqrt(n)) if n>1 else np.nan
            rows.append(dict(metric=metric,reference=other,n=n,mean_difference=delta.mean(),
                             standard_error=se,ci_low=delta.mean()-1.96*se,ci_high=delta.mean()+1.96*se))
    return pd.DataFrame(rows)


def detection_table(events, decisions, cfg):
    """Two consecutive annual signs on existing remove/revive comparisons.

    This is evaluator-defined, path-dependent economic detection, never a T1 null label.
    First event per method/signal/direction; undetected events are right-censored.
    """
    cols=['seed','method','signal','direction','event_day','detected','delay_days','censor_day']
    rows=[]
    if events.empty:return pd.DataFrame(columns=cols)
    horizon=cfg.block*cfg.years
    for (method,move,add,remove),g in events.groupby(['method','move','added','removed']):
        if move not in ('forward','backward'):continue
        g=g.sort_values('day')
        positive=g.true_block_mean.to_numpy()>cfg.economic_tolerance
        for k in range(1,len(g)):
            # Comparisons with a changed reference are distinct economic objects.
            if positive[k] and positive[k-1] and g.iloc[k].comparison_id==g.iloc[k-1].comparison_id:
                start=int(g.iloc[k-1].day)
                signal=int(remove if move=='backward' else add)
                relevant=decisions[(decisions.method==method)&(decisions.day>=start)]
                relevant=relevant[relevant.removed.eq(signal) if move=='backward' else relevant.added.eq(signal)]
                found=not relevant.empty
                end=int(relevant.day.min()) if found else horizon
                rows.append(dict(seed=int(g.iloc[0].seed),method=method,signal=signal,
                    direction='PARK' if move=='backward' else 'entry_or_REVIVE',event_day=start,
                    detected=found,delay_days=end-start,censor_day=horizon))
                break
    return pd.DataFrame(rows,columns=cols)
