"""Form differences before multiplication, preserving tiny policy contrasts."""
import numpy as np
from park_revive_extensions.certificates import laplace_even_moment


def paired_scores(wb,ws,cost_difference,returns,gamma):
    difference=(np.atleast_2d(wb)-ws)@returns
    total=(np.atleast_2d(wb)+ws)@returns
    return difference*(1-gamma*total/2)-cost_difference


def paired_caps(wb,ws,design,cost_difference,gamma,risk):
    # P@wb - P@ws can erase a real contrast when both include a large
    # common position. Its fourth-moment bound can then round falsely to zero.
    d=design.sleeves@(np.atleast_2d(wb)-ws).T
    s=design.sleeves@(np.atleast_2d(wb)+ws).T
    md,ms=risk.mean_cap(design.values,d),risk.mean_cap(design.values,s)
    vd,vs=risk.variance_cap(d),risk.variance_cap(s)
    d2=laplace_even_moment(md,vd,2)
    d4=laplace_even_moment(md,vd,4);s4=laplace_even_moment(ms,vs,4)
    d8=laplace_even_moment(md,vd,8);s8=laplace_even_moment(ms,vs,8)
    dc=np.abs(cost_difference)
    return ((np.sqrt(d2)+gamma/2*(d4*s4)**.25+dc)**2,
            (d4**.25+gamma/2*(d8*s8)**.125+dc)**4)
