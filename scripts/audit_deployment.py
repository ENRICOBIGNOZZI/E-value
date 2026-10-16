"""Post-hoc conditional valuation of the immutable first-entry decisions.

Replays observed histories exactly, then values a hypothetical next-period
entry from the fund's real zero state. No next return is drawn. This is not
post-entry fund performance and never feeds the test or selection rule.
"""
import argparse
import hashlib
import json
import pickle
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from park_revive.config import Config
from park_revive.dgp import Market
from park_revive.features import evaluate
from park_revive.sleeves import sleeve_weights


def target(mean,second,b,cfg):
    gradient=mean-cfg.gamma*second*b
    return float(np.clip(b+np.sign(gradient)*max(abs(gradient)-cfg.proportional,0)/(cfg.gamma*second+cfg.impact),-cfg.leverage,cfg.leverage))


def value(w,b,mean,second,cfg):
    cost=cfg.proportional*abs(w-b)+cfg.impact*(w-b)**2/2
    return float(w*mean-cfg.gamma*w*w*second/2-cost),float(cost)


def audit(root):
    root=Path(root);protocol=json.loads((root/'protocol_frozen.json').read_text())
    cfg=Config(**protocol['config']);entries=pd.read_csv(root/'first_entries.csv')
    rows=[]
    for entry in entries.itertuples():
        seed=int(entry.seed);day=int(entry.day);j=int(entry.signal[1:])
        path=root/f'seed_{seed}'
        # Only this pipeline's own local generated checkpoints are loaded.
        with (path/'checkpoint.pkl').open('rb') as f:state=pickle.load(f)
        market=Market(cfg,seed)
        for t in range(day):
            observed,_=market.step()
            np.testing.assert_array_equal(observed.returns,state['history'][t])
        assert market.day==day
        # Current state is already available before the next return. No step()
        # call is made for that return, and no realized next-period shock is used.
        functions=evaluate(np.tanh(market.latent),market.library)
        p=sleeve_weights(functions)[:,j]
        mult=cfg.stress_multiplier if market.regime else 1.
        factor_loading=(p@market.beta)*np.array(cfg.factor_scales)*mult
        mu=float(p@(functions@market.theta))
        variance=float(factor_loading@factor_loading+(cfg.idio_scale*mult)**2*(p@p))
        second=mu*mu+variance
        history=np.asarray(state['history'][:day])[:,j]
        estimated_mu=float(history.mean());estimated_second=float(np.mean(history*history)+cfg.ridge)
        previous_block=day//cfg.block-1
        last=pd.read_parquet(path/f'block_{previous_block:02d}/score_ledger.parquet',columns=['weights']).iloc[-1,0]
        shadow_previous=float(last[j])
        actual_weight=target(estimated_mu,estimated_second,0.,cfg)
        shadow_weight=target(estimated_mu,estimated_second,shadow_previous,cfg)
        oracle_weight=target(mu,second,0.,cfg)
        actual_utility,actual_cost=value(actual_weight,0.,mu,second,cfg)
        shadow_utility,shadow_cost=value(shadow_weight,shadow_previous,mu,second,cfg)
        oracle_utility,_=value(oracle_weight,0.,mu,second,cfg)
        rows.append(dict(seed=seed,arm=entry.arm,day=day,signal=entry.signal,
            terminal=day==cfg.years*cfg.block,own_coefficient=float(market.theta[j]),
            last_evaluated_shadow_gain=entry.true_current_mean,
            next_shadow_weight=shadow_weight,actual_entry_weight=actual_weight,
            next_shadow_conditional_gain=shadow_utility,actual_entry_conditional_gain=actual_utility,
            actual_entry_cost=actual_cost,shadow_cost=shadow_cost,
            state_matched_oracle_entry_gain=oracle_utility,
            actual_entry_gain_positive=actual_utility>cfg.economic_tolerance))
        print(f'seed={seed}: full pre-decision return history replayed; hypothetical deployment valued',flush=True)
    frame=pd.DataFrame(rows);frame.to_csv(root/'deployment_audit.csv',index=False)
    metadata=dict(kind='post-hoc descriptive conditional action valuation',
        inputs_sha256=hashlib.sha256((root/'first_entries.csv').read_bytes()).hexdigest(),
        future_returns_drawn=False,full_fund_path_simulated=False,
        terminal_rows_excluded_from_within_horizon_summaries=True,
        real_fund_previous_state='zero allocation',
        original_true_current_mean_semantics='conditional gain of last evaluated pre-return shadow pair, not next-period deployment gain',
        all_reported_entries_included=len(frame),source_commit='b9edb2c for the frozen simulator',
        evaluator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (root/'deployment_audit_protocol.json').write_text(json.dumps(metadata,indent=2)+'\n')
    within=frame[~frame.terminal]
    print(within[['actual_entry_conditional_gain','next_shadow_conditional_gain','actual_entry_cost']].agg(['min','mean','max']).to_string())
    print('Positive hypothetical entries within horizon:',int(within.actual_entry_gain_positive.sum()),'/',len(within))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='outputs/park_revive_tail_v1/first_entry')
    args=p.parse_args()
    with threadpool_limits(limits=1):audit(args.output)
