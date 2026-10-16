"""Evaluator-only conditional moments. Never imported by the selection layer."""
import numpy as np
from .costs import cost_components, expected_utility


def score_moments(wb, ws, bb, bs, truth, cfg):
    """Exact first two moments of Y under independent standardized Laplace shocks."""
    d = sum(cost_components(wb,bb,cfg))-sum(cost_components(ws,bs,cfg))
    if np.array_equal(wb,ws):
        return -float(d),float(d*d)
    mx, my = float(wb@truth.mean), float(ws@truth.mean)
    ix,iy=np.flatnonzero(wb),np.flatnonzero(ws)
    hx, hy = wb[ix]@truth.loadings[ix], ws[iy]@truth.loadings[iy]
    vx, vy, vxy = float(hx@hx), float(hy@hy), float(hx@hy)
    ex2, ey2 = mx*mx+vx, my*my+vy
    ex3, ey3 = mx**3+3*mx*vx, my**3+3*my*vy
    ex4 = mx**4+6*mx*mx*vx+3*vx*vx+3*np.sum(hx**4)
    ey4 = my**4+6*my*my*vy+3*vy*vy+3*np.sum(hy**4)
    ex2y = mx*mx*my+my*vx+2*mx*vxy
    exy2 = mx*my*my+mx*vy+2*my*vxy
    ex2y2 = (mx*mx*my*my+mx*mx*vy+my*my*vx+4*mx*my*vxy
              +vx*vy+2*vxy*vxy+3*np.sum(hx*hx*hy*hy))
    el, eq = mx-my, ex2-ey2
    el2 = el*el+vx+vy-2*vxy
    eq2 = ex4+ey4-2*ex2y2
    elq = ex3+ey3-exy2-ex2y
    mean = el-cfg.gamma*eq/2-d
    second = el2+cfg.gamma**2*eq2/4+d*d-cfg.gamma*elq-2*d*el+cfg.gamma*d*eq
    return float(mean), max(0.,float(second))


def true_utility(w, b, truth, cfg):
    return expected_utility(w,b,truth.mean,truth.second,cfg)
