#!/usr/bin/env python3
"""Check analytic horizon examples against the independent scalar QP."""
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from park_revive.config import Config
from park_revive.optimizer import Optimizer


def main():
    cfg=Config();horizon=252;b=.5;variance=.002**2
    reference=Optimizer(cfg,np.zeros(1),np.array([[variance]])).solve((0,),np.array([b]))
    parked=Optimizer(cfg,np.zeros(1),np.array([[variance]])).solve((),np.array([b]))
    assert reference.weights[0]==b
    daily_risk=cfg.gamma*variance*b*b/2;cost=cfg.proportional*b+cfg.impact*b*b/2
    first=parked.value-reference.value;holding=horizon*daily_risk-cost
    assert abs(first-(daily_risk-cost))<1e-16
    mu=.00005;second=.01**2+mu*mu
    one=Optimizer(cfg,np.array([mu]),np.array([[second]])).solve((0,),np.zeros(1))
    # Scaling both linear and raw-second-moment coefficients represents the
    # SUM of H daily utilities, not utility applied to the cumulative return.
    committed=Optimizer(cfg,np.array([horizon*mu]),np.array([[horizon*second]])).solve((0,),np.zeros(1))
    exact=min(cfg.leverage,(horizon*mu-cfg.proportional)/(horizon*cfg.gamma*second+cfg.impact))
    value=(horizon*mu-cfg.proportional)*exact-(horizon*cfg.gamma*second+cfg.impact)*exact*exact/2
    assert one.weights[0]==0 and abs(committed.weights[0]-exact)<1e-7
    assert abs(committed.value-value)<1e-12
    result=dict(financial_replications=0,kind='analytic interpretation examples; no empirical application',
        parameters=dict(gamma=cfg.gamma,c=cfg.proportional,eta=cfg.impact,H=horizon),
        parking=dict(sigma=.002,initial_weight=b,reference_target=float(reference.weights[0]),
            first_period_gain=first,holding_period_gain=holding,break_even_horizon=cost/daily_risk,
            cumulative_state_matched_regret_reference=0.,cumulative_state_matched_regret_parked=-first),
        entry=dict(mu=mu,sigma=.01,raw_second_moment=second,myopic_target=float(one.weights[0]),
            horizon_constant_target=exact,horizon_constant_value=value,qp_target=float(committed.weights[0])),
        limits=['No terminal liquidation charge.','Constant-position entry value is not the general dynamic optimum.',
                'Known stationary moments, not a claim that episode evidence certifies future returns.'])
    (ROOT/'reports/horizon_examples.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
