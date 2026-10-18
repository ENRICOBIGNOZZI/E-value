"""An explicit numerical initialization for one preserved failed final-study QP.

This post-freeze computational amendment changes only the starting iterates of
the exact recorded problem. The original optimizer, objective, constraints,
tolerances, iteration budget and original-unit KKT guards remain in force.
It is supplementary execution provenance, not part of the original source
fingerprint and not a pre-final recovery rule. It reuses a successful primal
and dual iterate from a separately solved identical recorded QP; no market
truth or future return enters that numerical cache.
"""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import numpy as np
import scipy.sparse as sp
import osqp


def problem_fingerprint(problem):
    digest=hashlib.sha256()
    for name in ['P','q','A','l','u']:
        value=problem[name]
        digest.update(name.encode())
        if sp.issparse(value):
            value=value.tocsc(copy=True)
            value.sum_duplicates();value.sort_indices()
            digest.update(np.asarray(value.shape,dtype='<i8').tobytes())
            for array,dtype in [(value.indptr,'<i8'),(value.indices,'<i8'),(value.data,'<f8')]:
                digest.update(np.asarray(array,dtype=dtype).tobytes())
        else:
            value=np.asarray(value,dtype='<f8')
            digest.update(np.asarray(value.shape,dtype='<i8').tobytes())
            digest.update(value.tobytes())
    return digest.hexdigest()


def captured_problem(capture,cfg):
    ix=capture['support'];n=len(ix);b=capture['previous'][ix]
    h=cfg.gamma*capture['second'][np.ix_(ix,ix)]+cfg.impact*np.eye(n)
    q=np.r_[-capture['mean'][ix]-cfg.impact*b,np.full(n,cfg.proportional),np.zeros(n)]
    eye=sp.eye(n,format='csc');zero=sp.csc_matrix((n,n))
    a=sp.vstack([sp.hstack([eye,-eye,zero]),sp.hstack([-eye,-eye,zero]),
                 sp.hstack([eye,zero,-eye]),sp.hstack([-eye,zero,-eye]),
                 sp.csc_matrix(np.r_[np.zeros(2*n),np.ones(n)][None,:])],format='csc')
    p=sp.block_diag([sp.csc_matrix(h),sp.csc_matrix((2*n,2*n))],format='csc')
    return dict(P=sp.triu(p*10000.,format='csc'),q=q*10000.,A=a,
                l=np.full(4*n+1,-np.inf),u=np.r_[b,-b,np.zeros(2*n),cfg.leverage])


def validate_iterates(problem,profile):
    x=np.asarray(profile['initial_x'],dtype=float)
    y=np.asarray(profile['initial_y'],dtype=float)
    assert x.shape==np.asarray(problem['q']).shape
    assert y.shape==np.asarray(problem['u']).shape
    assert np.isfinite(x).all() and np.isfinite(y).all()
    upper=problem['P'].tocsc()
    p=upper+upper.T-sp.diags(upper.diagonal())
    ax=problem['A']@x
    stationarity=np.max(np.abs(p@x+problem['q']+problem['A'].T@y))
    primal=max(0.,float(np.max(ax-problem['u'])),float(np.max(problem['l']-ax)))
    finite=np.isfinite(problem['u'])
    complementarity=float(np.max(np.abs(y[finite]*(ax[finite]-problem['u'][finite]))))
    dual_sign=max(0.,float(-np.min(y)))/10000.
    gap=abs(float(x@(p@x)+problem['q']@x+problem['u']@y))/10000.
    if max(stationarity/10000.,primal,complementarity/10000.,dual_sign,gap)>1e-12:
        raise RuntimeError('Saved iterate fails independent original-unit KKT checks')
    return x,y,dict(primal=primal,stationarity=stationarity/10000.,
                    complementarity=complementarity/10000.,dual_sign=dual_sign,duality_gap=gap)


@contextmanager
def initialize_known_problem(profile):
    original=osqp.OSQP.setup
    calls=[]
    def setup(solver,*args,**kwargs):
        original(solver,*args,**kwargs)
        if args or not all(k in kwargs for k in ['P','q','A','l','u']):
            return
        signature=problem_fingerprint(kwargs)
        if signature!=profile['known_problem_sha256']:
            return
        expected=dict(eps_abs=1e-10,eps_rel=1e-10,max_iter=300000,
                      polishing=True,adaptive_rho=True)
        if any(kwargs.get(key)!=value for key,value in expected.items()):
            raise RuntimeError('Known QP has different solver settings; initialization refused')
        x,y,kkt=validate_iterates(kwargs,profile)
        solver.warm_start(x=x,y=y)
        calls.append(dict(problem_sha256=signature,initial_x=x.tolist(),initial_y=y.tolist(),
                          initial_original_unit_kkt=kkt,unchanged_solver_settings=expected))
    osqp.OSQP.setup=setup
    try:
        yield calls
    finally:
        osqp.OSQP.setup=original
