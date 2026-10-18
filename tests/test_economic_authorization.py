"""Policy timing, information separation and accounting controls for the new study."""
from types import SimpleNamespace
from pathlib import Path
import importlib.util
import json
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
path = ROOT/'extensions/economic_authorization/study.py'
spec = importlib.util.spec_from_file_location('economic_study', path)
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)
Config = study.Config
SETTINGS = json.loads((ROOT/'configs/economic_authorization.json').read_text())


def test_training_mean_with_uncertainty_penalty_changes_exposure():
    cfg = Config(leverage=10)
    x = np.array([-.01,.012,-.008,.01,-.009,.011,-.007,.009])
    mean,m2,se,w = study.training_fit(x,cfg,SETTINGS)
    assert se[0] > 0 and m2[0] >= np.mean(x*x)
    unpenalized = dict(SETTINGS,uncertainty_z=0.)
    assert abs(w[0]) < abs(study.training_fit(x,cfg,unpenalized)[3][0])


def test_training_selects_using_penalized_value_not_future_returns():
    cfg=Config()
    x=np.tile([.02,.005],(252,1))
    mu,m2,se,w=study.training_fit(x,cfg,SETTINGS)
    assert np.argmax(study.forecast(w,0,mu,m2,se,cfg,SETTINGS))==0


def test_provisional_entry_precedes_any_evidence():
    fractions,full,details=study.review(.02,.0005,0.,1.,0.,0.,0.,False,Config(),SETTINGS)
    np.testing.assert_array_equal(fractions,[0.,.25,.25,1.])
    assert not full and not details['evidence']


def test_increase_needs_evidence_and_economic_forecast():
    cfg=Config()
    args=(.02,.0005,0.,1.,.25)
    assert study.review(*args,np.log(20)-1e-8,.01,False,cfg,SETTINGS)[1] is False
    assert study.review(*args,np.log(20),.01,False,cfg,SETTINGS)[1] is True
    # Full exposure is positive versus cash but inferior to a half position.
    s=dict(SETTINGS,provisional_fraction=.5,uncertainty_z=0.)
    _,full,d=study.review(.6,1.,0.,1.,.5,np.log(20),.1,False,
                          Config(gamma=1,proportional=0,impact=0),s)
    assert d['full_forecast']>0 and d['increase_forecast']<0 and not full


def test_costs_use_each_actual_previous_allocation():
    cfg=Config(proportional=.01,impact=.02)
    actions=np.array([1.,.25,1.,1.]); previous=np.array([0.,.25,.25,1.])
    result=study.realize(actions,previous,.03,np.ones(4,dtype=bool),np.ones(4),cfg)
    np.testing.assert_allclose(result[4],[.02,0.,.013125,0.])


def test_insolvency_is_absorbing_and_all_methods_account_for_losses():
    cfg=Config()
    result=study.realize(np.ones(4),np.ones(4),-2.,np.ones(4,dtype=bool),np.ones(4),cfg)
    assert not result[2].any() and np.all(result[3]==0)
    again=study.realize(np.ones(4),result[1],10.,result[2],result[3],cfg)
    np.testing.assert_array_equal(again[0],np.zeros(4))
    np.testing.assert_array_equal(again[6],np.zeros(4))
    assert np.all(result[6]<0)


@pytest.mark.parametrize('deployment',[0,2,8,None])
def test_exact_utility_decomposition_including_nonentry(deployment):
    cfg=Config();r=np.array([.02,-.01,.03,-.02,.01,.04,-.03,.01])
    t=len(r) if deployment is None else deployment
    w=np.array([.7,.7,.8,.8,.5,.5,.9,.9])
    theta=np.column_stack([np.r_[np.zeros(t),np.ones(len(r)-t)],
                           np.r_[np.full(t,.25),np.ones(len(r)-t)]])
    positions=theta*w[:,None]
    previous=np.vstack([np.zeros(2),positions[:-1]])
    costs=study.cost(positions,previous,cfg)
    gross=positions*r[:,None]
    u=gross-cfg.gamma*gross*gross/2-costs
    direct=np.sum(u[:,1]-u[:,0])
    decomposed=np.sum((positions[:,1]-positions[:,0])*r
        -cfg.gamma*(positions[:,1]**2-positions[:,0]**2)*r*r/2
        -(costs[:,1]-costs[:,0]))
    assert abs(direct-decomposed)<1e-16
    if t<len(r):
        np.testing.assert_allclose(costs[t+1:,0],costs[t+1:,1])


class ScriptedMarket:
    truth_offset=0.
    def __init__(self,cfg,seed):
        self.cfg=cfg;self.day=0;self.ids=tuple(f's{j:03}' for j in range(100))
    def prepare(self):
        p=np.zeros((self.cfg.n_assets,100));p[0,:]=.5;p[1,:]=-.5
        return SimpleNamespace(values=np.zeros_like(p),sleeves=p),None
    def step(self):
        r=np.full(100,.005);r[0]=.02+(.001 if self.day%2 else -.001)
        self.day+=1
        truth=SimpleNamespace(mean=np.full(100,.02+self.truth_offset),
                              second=np.full((100,100),.0005+self.truth_offset))
        return SimpleNamespace(returns=r),truth


def test_full_simulation_trades_are_invariant_to_evaluator_truth(tmp_path):
    cfg=Config(n_assets=4,block=4,years=3)
    protocol=dict(extension_source_sha256=study.sha(path),
                  original_scientific_source_hash=study.source_fingerprint()[0])
    a=tmp_path/'a';b=tmp_path/'b'
    study.run_seed(cfg,SETTINGS,protocol,'test',1,a,ScriptedMarket)
    class AlteredTruth(ScriptedMarket):
        truth_offset=10.
    study.run_seed(cfg,SETTINGS,protocol,'test',1,b,AlteredTruth)
    with np.load(a/'ledger.npz') as x,np.load(b/'ledger.npz') as y:
        for key in ['arm_weight','arm_cost','arm_utility','log_e','returns','initial_training']:
            np.testing.assert_array_equal(x[key],y[key])
        assert not np.array_equal(x['true_mean'],y['true_mean'])


def test_annual_decision_only_uses_previous_block_evidence(tmp_path):
    cfg=Config(n_assets=4,block=4,years=3)
    protocol=dict(extension_source_sha256=study.sha(path),
                  original_scientific_source_hash=study.source_fingerprint()[0])
    study.run_seed(cfg,SETTINGS,protocol,'test',1,tmp_path/'run',ScriptedMarket)
    decisions=json.loads((tmp_path/'run/annual_decisions.json').read_text())
    with np.load(tmp_path/'run/ledger.npz') as ledger:
        assert decisions[0]['evidence_log_e']==0
        assert decisions[1]['evidence_log_e']==ledger['log_e'][cfg.block-1]


def test_completed_seed_cannot_be_silently_modified(tmp_path):
    cfg=Config(n_assets=4,block=4,years=2)
    protocol=dict(extension_source_sha256=study.sha(path),
                  original_scientific_source_hash=study.source_fingerprint()[0])
    directory=tmp_path/'run'
    study.run_seed(cfg,SETTINGS,protocol,'test',1,directory,ScriptedMarket)
    (directory/'annual_decisions.json').write_text('[]')
    with pytest.raises(ValueError,match='altered'):
        study.run_seed(cfg,SETTINGS,protocol,'test',1,directory,ScriptedMarket)
