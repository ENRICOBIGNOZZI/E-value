from pathlib import Path
import sys
import json
import numpy as np
import osqp
import scipy.sparse as sp
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src'),str(ROOT/'research')]
from qp_initialization_60469 import captured_problem,problem_fingerprint,validate_iterates,initialize_known_problem
from park_revive.config import Config
from park_revive_full.optimization import StudyOptimizer

FOLDER=ROOT/'reports/full_v3_recovery_20261018/qp_60469'


def inputs():
    cfg=Config.read(ROOT/'configs/full_main.json')
    capture=dict(np.load(FOLDER/'failed_problem.npz'))
    profile=json.loads((FOLDER/'profile.json').read_text())
    problem=captured_problem(capture,cfg)
    return cfg,capture,profile,problem


def test_signature_binds_every_problem_coefficient():
    _,_,profile,p=inputs()
    assert problem_fingerprint(p)==profile['known_problem_sha256']
    for name in ['q','u','l']:
        q=dict(p);q[name]=p[name].copy()
        finite=np.flatnonzero(np.isfinite(q[name]))
        if not len(finite):
            q[name][0]=0.
        else:q[name][finite[0]]+=1e-12
        assert problem_fingerprint(q)!=profile['known_problem_sha256']


def test_starting_iterate_is_feasible_for_original_epigraph_problem():
    _,_,profile,p=inputs();x,y,kkt=validate_iterates(p,profile)
    assert np.max(p['A']@x-p['u'])<2e-15
    assert max(kkt.values())<1e-12


def test_original_failed_solver_now_passes_its_original_kkt_guard():
    cfg,capture,profile,_=inputs()
    optimizer=StudyOptimizer(cfg,capture['mean'],capture['second'])
    with initialize_known_problem(profile) as calls:
        result=optimizer.solve_in_basis_points(tuple(capture['support']),capture['previous'])
    assert len(calls)==1
    assert optimizer.recoveries[-1]['iterations']<=300000
    assert max(result.primal_residual,result.dual_residual,result.gap)<1e-9
    assert np.abs(result.weights).sum()<=cfg.leverage+1e-15


def test_unrecognized_problem_does_not_receive_initialization():
    _,_,profile,_=inputs()
    original=osqp.OSQP.setup
    with initialize_known_problem(profile) as calls:
        solver=osqp.OSQP()
        solver.setup(P=sp.eye(2,format='csc'),q=np.zeros(2),A=sp.eye(2,format='csc'),
                     l=-np.ones(2),u=np.ones(2),verbose=False)
        assert solver.solve(raise_error=False).info.status_val==1
        assert calls==[]
    assert osqp.OSQP.setup is original


def test_known_problem_with_changed_tolerance_is_refused():
    _,_,profile,p=inputs()
    with initialize_known_problem(profile):
        solver=osqp.OSQP()
        with pytest.raises(RuntimeError,match='different solver settings'):
            solver.setup(**p,eps_abs=1e-9,eps_rel=1e-10,max_iter=300000,
                         verbose=False,polishing=True,adaptive_rho=True)


def test_invalid_cached_solution_is_refused():
    _,_,profile,p=inputs()
    altered=dict(profile,initial_x=list(profile['initial_x']))
    altered['initial_x'][0]+=.01
    with pytest.raises(RuntimeError,match='KKT'):
        validate_iterates(p,altered)
