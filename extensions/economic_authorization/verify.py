"""Independent arithmetic replay plus two complete market/certificate replays."""
from pathlib import Path
from math import comb, factorial
import argparse
import hashlib
import json
import sys
import numpy as np
import pandas as pd
from scipy.special import logsumexp
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'research')]
from park_revive.config import Config
from park_revive_full.market import CausalMarket
from park_revive_full.engine import source_fingerprint

ARMS=('Wait','EconomicQuarter','Hybrid','EconomicFull')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Checks:
    def __init__(self):
        self.count=0
        self.errors={}
    def equal(self,actual,expected,name,atol=1e-12,rtol=1e-11):
        a,b=np.asarray(actual),np.asarray(expected)
        if a.shape!=b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
            raise AssertionError(f'{name}: shape or finiteness')
        error=float(np.max(np.abs(a-b),initial=0))
        self.count+=a.size
        self.errors[name]=max(self.errors.get(name,0.),error)
        if not np.allclose(a,b,atol=atol,rtol=rtol):
            raise AssertionError(f'{name}: error {error}')


def fit(x,cfg,s):
    x=np.asarray(x,float)
    if x.ndim==1:x=x[:,None]
    n=len(x);mu=np.mean(x,axis=0);m2=np.mean(x**2,axis=0)+cfg.ridge
    z=x-mu
    longvar=np.sum(z*z,axis=0)/n
    bw=min(s['hac_bandwidth'],n-1)
    for k in range(1,bw+1):
        longvar+=2*(bw+1-k)/(bw+1)*np.sum(z[k:]*z[:-k],axis=0)/n
    se=np.sqrt(np.maximum(longvar,0)/n)
    adjusted=np.abs(mu)-s['uncertainty_z']*se-cfg.proportional/s['forecast_holding_days']
    w=np.sign(mu)*np.maximum(adjusted,0)/(cfg.gamma*m2+cfg.impact/s['forecast_holding_days'])
    return mu,m2,se,np.minimum(np.maximum(w,-cfg.leverage),cfg.leverage)


def replay_seed(directory,cfg,s,protocol_hash,checks):
    status=json.loads((directory/'status.json').read_text())
    assert status['complete'] and status['protocol_sha256']==protocol_hash
    assert all(sha(directory/name)==digest for name,digest in status['files'].items())
    d=dict(np.load(directory/'ledger.npz',allow_pickle=False))
    annual=json.loads((directory/'annual_decisions.json').read_text())
    horizon=(cfg.years-1)*cfg.block
    assert len(d['returns'])==horizon and len(annual)==cfg.years-1
    assert d['initial_training'].shape==(cfg.block,100)
    h=s['forecast_holding_days'];q=s['provisional_fraction'];z=s['uncertainty_z']
    def costs(w,b):
        change=np.asarray(w)-b
        return cfg.proportional*np.abs(change)+cfg.impact/2*change**2
    def value(w,b,mu,m2,se):
        return h*(w*mu-z*np.abs(w)*se-cfg.gamma/2*w**2*m2)-costs(w,b)
    mu,m2,se,w=fit(d['initial_training'],cfg,s)
    selected=int(np.argmax(value(w,0,mu,m2,se)))
    checks.equal(d['selected'],selected,'training_candidate')
    history=list(d['initial_training'][:,selected])
    component=np.zeros(9);loge=0.;total=0.;n=0
    previous=np.zeros(4);wealth=np.ones(4);alive=np.ones(4,bool)
    shadow_previous=0.;full=False;deployment=-1;cross=-1
    expected={k:[] for k in ['arm_weight','arm_cost','arm_utility','arm_wealth',
                              'shadow_weight','shadow_cost','log_e']}
    for year in range(cfg.years-1):
        mu,m2,se,w=(float(a[0]) for a in fit(history,cfg,s))
        floor=h*s['effect_floor_daily']
        provisional=q if value(q*w,0,mu,m2,se)>floor else 0.
        full_value=value(w,0,mu,m2,se)
        increase=value(w,previous[2],mu,m2,se)-value(provisional*w,previous[2],mu,m2,se)
        has_evidence=loge>=np.log(1/s['individual_alpha'])
        full=full or bool(has_evidence and total/max(1,n)>s['effect_floor_daily']
                          and full_value>floor and increase>floor)
        if full and deployment<0:deployment=year*cfg.block
        fractions=np.array([float(full),provisional,1. if full else provisional,float(full_value>floor)])
        a=annual[year]
        for key,val in dict(training_n=len(history),mean=mu,second=m2,standard_error=se,target=w,
                            evidence_log_e=loge,mean_score=total/max(1,n),
                            previous_hybrid=previous[2],provisional_fraction=provisional,
                            full_forecast=full_value,increase_forecast=increase).items():
            checks.equal(a[key],val,'annual_'+key)
        assert a['full_authorized']==full and a['evidence']==has_evidence
        for day in range(year*cfg.block,(year+1)*cfg.block):
            r=d['returns'][day]
            actual=np.where(alive,fractions*w,0.)
            c=np.where(alive,costs(actual,previous),0.)
            gross=actual*r
            u=np.where(alive,gross-cfg.gamma/2*gross**2-c,0.)
            net=gross-c
            wealth=np.where(alive,wealth*np.maximum(1+net,0),0.)
            alive=alive & (net>-1)
            previous=np.where(alive,actual,0.)
            shadow_cost=float(costs(w,shadow_previous));shadow_previous=w
            y=w*r-cfg.gamma/2*(w*r)**2-shadow_cost
            second,fourth=d['cap2'][day],d['cap4'][day]
            assert np.isfinite([second,fourth]).all() and min(second,fourth)>=0
            increments=[]
            for scale in (2.,4.,8.):
                bound=scale*fourth**.25 if fourth>0 else 1.
                bias=min(second/(4*bound),27*fourth/(256*bound**3))
                for fraction in (.25,.5,.75):
                    stake=fraction/(bound+bias) if fourth>0 else 0.
                    if fourth==0:assert second==0 and y==0
                    factor=1+stake*(max(y,-bound)-bias)
                    assert factor>0
                    increments.append(np.log(factor))
            component+=increments
            loge=float(logsumexp(component)-np.log(9))
            total+=y;n+=1;history.append(float(r))
            for key,val in dict(arm_weight=actual.copy(),arm_cost=c.copy(),arm_utility=u.copy(),
                                arm_wealth=wealth.copy(),shadow_weight=w,shadow_cost=shadow_cost,
                                log_e=loge).items():expected[key].append(val)
        if cross<0 and loge>=np.log(1/s['individual_alpha']):cross=(year+1)*cfg.block
    for key,values in expected.items():checks.equal(d[key],np.asarray(values),key)
    before=deployment if deployment>=0 else horizon
    summary=pd.read_csv(directory/'summary.csv').set_index('method')
    assert set(summary.index)==set(ARMS) and len(summary)==4
    for i,name in enumerate(ARMS):
        w=d['arm_weight'][:,i];c=d['arm_cost'][:,i];u=d['arm_utility'][:,i]
        wealth=np.r_[1.,d['arm_wealth'][:,i]]
        conditional=w*d['true_mean']-cfg.gamma/2*w*w*d['true_second']-c
        values=dict(selected_index=selected,annual_scaled_utility=cfg.block*u.mean(),
                    terminal_wealth=wealth[-1],maximum_drawdown=np.max(1-wealth/np.maximum.accumulate(wealth)),
                    annual_scaled_cost=cfg.block*c.mean(),cash_fraction=np.mean(w==0),
                    insolvent=float(wealth[-1]==0),deployment_day=deployment,first_cross_review=cross,
                    pre_deployment_utility=u[:before].sum(),pre_deployment_expected_utility=conditional[:before].sum(),
                    pre_deployment_negative_days=np.sum(u[:before]<0),
                    pre_deployment_negative_conditional_days=np.sum(conditional[:before]<0))
        for key,val in values.items():checks.equal(summary.loc[name,key],val,'summary_'+key)
    weights=d['arm_weight'];r=d['returns'];c=d['arm_cost']
    decomposition=(weights[:,2]-weights[:,0])*r-cfg.gamma/2*(weights[:,2]**2-weights[:,0]**2)*r*r-(c[:,2]-c[:,0])
    checks.equal(d['arm_utility'][:,2]-d['arm_utility'][:,0],decomposition,'paired_decomposition')
    return dict(seed=status['seed'],selected_index=selected,files=status['files'],complete=True)


def market_replay(directory,cfg,checks):
    seed=int(directory.name.split('_')[-1])
    d=dict(np.load(directory/'ledger.npz',allow_pickle=False));j=int(d['selected'])
    market=CausalMarket(cfg,seed)
    for day in range(cfg.block):
        obs,_=market.step()
        checks.equal(d['initial_training'][day],obs.returns,'market_initial_training',atol=0,rtol=0)
    maximum2=maximum4=0.
    previous=0.
    for day,w in enumerate(d['shadow_weight']):
        design,_=market.prepare()
        stock=design.sleeves[:,j]*w
        coefficients=design.values.T@stock
        cap=cfg.base_theta*cfg.theta_cap_multiple
        units=15+10/4+10+10
        full=int(units)
        def support(a):
            a=np.sort(np.maximum(a,0))[::-1]
            return cap*(a[:full].sum()+(units-full)*a[full])
        m=max(support(coefficients),support(-coefficients))
        net=stock.sum();gross=np.abs(stock).sum();maximum=max(1.,cfg.stress_multiplier)
        v=0.
        for center,radius,scale in zip([1,0,0,0],[.5,1,1,1],cfg.factor_scales):
            v+=(scale*maximum)**2*(abs(center*net)+radius*gross)**2
        v+=(cfg.idio_scale*maximum)**2*(stock@stock)
        raw2=m*m+v
        raw4=m**4+6*m*m*v+6*v*v
        raw8=m**8+28*m**6*v+420*m**4*v*v+2520*m*m*v**3+2520*v**4
        c=cfg.proportional*abs(w-previous)+cfg.impact/2*(w-previous)**2;previous=w
        second=(np.sqrt(raw2)+cfg.gamma/2*np.sqrt(raw4)+c)**2
        fourth=(raw4**.25+cfg.gamma/2*raw8**.25+c)**4
        checks.equal(d['cap2'][day],second,'independent_public_second',atol=1e-28)
        checks.equal(d['cap4'][day],fourth,'independent_public_fourth',atol=1e-40)
        obs,truth=market.step()
        checks.equal(d['returns'][day],obs.returns[j],'market_selected_return',atol=0,rtol=0)
        checks.equal(d['true_mean'][day],truth.mean[j],'market_conditional_mean',atol=0,rtol=0)
        checks.equal(d['true_second'][day],truth.second[j,j],'market_conditional_second',atol=0,rtol=0)
        loads=w*truth.loadings[j];mu=w*truth.mean[j]
        cumulants={2:float(loads@loads),4:float(3*np.sum(loads**4)),
                   6:float(30*np.sum(loads**6)),8:float(630*np.sum(loads**8))}
        centered=[1.]
        for order in range(1,9):
            centered.append(sum(comb(order-1,k-1)*value*centered[order-k]
                                for k,value in cumulants.items() if k<=order))
        raw=[sum(comb(order,k)*mu**(order-k)*centered[k] for k in range(order+1))
             for order in range(9)]
        polynomial=np.polynomial.polynomial.polypow(np.array([-c,1.,-cfg.gamma/2]),4)
        true4=float(polynomial@raw)
        true2=raw[2]-cfg.gamma*raw[3]+cfg.gamma**2/4*raw[4]-2*c*raw[1]+cfg.gamma*c*raw[2]+c*c
        assert true2<=second*(1+1e-9)+1e-28 and true4<=fourth*(1+1e-9)+1e-40
        maximum2=max(maximum2,true2/second if second else 0.)
        maximum4=max(maximum4,true4/fourth if fourth else 0.)
    return dict(seed=seed,days=len(d['returns']),maximum_second_ratio=maximum2,maximum_fourth_ratio=maximum4)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,default=ROOT/'outputs/economic_authorization_v1')
    p.add_argument('--destination',type=Path,default=ROOT/'reports/economic_authorization_v1')
    args=p.parse_args()
    protocol_path=args.output/'protocol_frozen.json';protocol=json.loads(protocol_path.read_text())
    digest=sha(protocol_path)
    assert (ROOT/'reports/economic_authorization_v1_protocol.json').read_bytes()==protocol_path.read_bytes()
    assert sha(ROOT/'extensions/economic_authorization/study.py')==protocol['extension_source_sha256']
    assert source_fingerprint()[0]==protocol['original_scientific_source_hash']
    cfg=Config(**protocol['base_config']);s=protocol['settings'];checks=Checks()
    records=[]
    with threadpool_limits(limits=1):
        for seed in protocol['seed_pool']:
            records.append(replay_seed(args.output/f'seed_{seed}',cfg,s,digest,checks))
            print(f'replayed economic seed={seed}',flush=True)
        market_records=[market_replay(args.output/f'seed_{seed}',cfg,checks) for seed in [70001,70002]]
    report=dict(complete=True,protocol_sha256=digest,verifier_sha256=sha(__file__),
                arithmetic_replayed_markets=len(records),scalar_checks=checks.count,
                maximum_absolute_errors=checks.errors,market_replays=market_records,records=records,
                scope='Independent policy/cost/evidence arithmetic replay for all 100 markets. Independent complete DGP and public-certificate replay for the first two deterministic seed identifiers; no new financial observations and no claim of replaying all 100 DGP paths.')
    path=args.destination/'replay_verification.json'
    path.write_text(json.dumps(report,indent=2)+'\n')
    status_path=args.destination/'status.json';status=json.loads(status_path.read_text())
    status.update(independent_replay_pending=False,independent_replay_sha256=sha(path))
    status_path.write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['arithmetic_replayed_markets','scalar_checks','market_replays']},indent=2))


if __name__=='__main__':
    main()
