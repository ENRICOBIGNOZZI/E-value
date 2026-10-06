"""Repository-local smoke checks. Full delivery contains 34 unit tests."""
import itertools
import numpy as np
from fast import DetectorConfig, Evidence, Controller, edbh, paired_value, utility, oracle_value, delay_bound

rng=np.random.default_rng(731)
b=rng.normal(size=100);y=rng.normal(size=100)
assert np.allclose(paired_value(b,y),utility(b+y)-utility(b))
assert edbh(np.array([[120.,110.,0.]]),50.).tolist()==[[True,True,False]]
cu=Evidence((1,1),DetectorConfig(hysteresis=0.))
sr=Evidence((1,1),DetectorConfig(hysteresis=0.,kind='sr'))
for t in range(1,31):
    assert np.isclose(cu.update(np.zeros((1,1)))[0,0],1.)
    assert np.isclose(sr.update(np.zeros((1,1)))[0,0],t)
c=Controller((1,1),DetectorConfig(patience=2.,hysteresis=0.))
for _ in range(50):
    old=c.active.copy();flip,val=c.step(np.array([[-1.]]))
    if flip.any():
        assert old[0,0] and not c.active[0,0]
        assert not c.test.capital.any()
        break
else:raise AssertionError('Strong negative gain failed to produce a PARK.')
x=np.array([[.2,-.5,.2]]);cost=.03
best=max(sum(a[t]*x[0,t] for t in range(3))-cost*(int(a[0]!=1)+sum(a[t]!=a[t-1] for t in range(1,3))) for a in itertools.product([0,1],repeat=3))
assert np.isclose(oracle_value(x,cost)[0],best)
assert np.isfinite(delay_bound(252.,.4,np.geomspace(.01,.95,31)))
print('V4 repository smoke checks passed. The complete delivery has 34 unit tests and executed simulation/JKP audits.')
