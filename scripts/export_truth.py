"""Replay completed simulated markets to export evaluator-only truth and diagnostics.

This reads only locally generated checkpoints. Truth files are never a learner input.
Every replayed return is checked exactly against the saved training/OOS history.
"""
import argparse
import json
import pickle
from pathlib import Path
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from park_revive.config import Config
from park_revive.dgp import Market
from park_revive.backtest import source_fingerprint


def export(directory):
    directory=Path(directory);cfg=Config.read(directory/'config_frozen.json')
    diagnostics=[]
    fingerprint,_=source_fingerprint()
    for path in sorted(p for p in directory.glob('seed_*') if p.is_dir()):
        status=json.loads((path/'status.json').read_text())
        if status['status']!='complete':continue
        with (path/'checkpoint.pkl').open('rb') as f:state=pickle.load(f)
        if state['implementation_hash']!=fingerprint:raise ValueError('Replay implementation differs from run')
        seed=state['seed'];market=Market(cfg,seed);rows=[]
        for day,expected in enumerate(state['history']):
            observed,truth=market.step()
            np.testing.assert_array_equal(observed.returns,expected)
            rows.append(dict(seed=seed,day=day,regime=truth.regime,deteriorated=truth.deteriorated,
                theta=truth.theta.tolist(),conditional_mean=truth.mean.tolist(),
                conditional_second_diagonal=np.diag(truth.second).tolist(),sleeve_returns=observed.returns.tolist()))
        pd.DataFrame(rows).to_parquet(path/'evaluator_truth.parquet',index=False)
        oos=np.asarray(state['history'][cfg.block:]);sd=oos.std(axis=0,ddof=1)
        sharpe=np.sqrt(cfg.block)*oos.mean(axis=0)/sd
        corr=np.corrcoef(oos.T)
        for j in range(100):
            group=('persistent' if j<15 else 'weak' if j<25 else 'decay' if j<35 else
                   'revive' if j<45 else 'independent_noise' if j<85 else 'proxy')
            diagnostics.append(dict(seed=seed,signal=f's{j:03}',group=group,mean_daily_return=oos[:,j].mean(),
                daily_volatility=sd[j],conventional_annual_sharpe=sharpe[j],
                max_absolute_correlation_with_predictors=np.max(np.abs(corr[j,:45][np.arange(45)!=j])) if j<45 else np.max(np.abs(corr[j,:45]))))
        print(f'seed={seed}: exact replay of {len(rows)} dates; evaluator truth exported',flush=True)
    pd.DataFrame(diagnostics).to_csv(directory/'market_diagnostics.csv',index=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='outputs/park_revive_v1/frozen_pilot')
    args=parser.parse_args()
    with threadpool_limits(limits=1):export(args.output)
