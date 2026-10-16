"""Repeated fixed-time HAC p-values: no anytime-valid claim."""
import numpy as np
from scipy.special import ndtr


def hac_variance(y):
    y = np.asarray(y, dtype=float)
    n = len(y)
    if n < 2:
        return np.nan
    bandwidth = min(n-1, int(np.floor(4*(n/100)**(2/9))))
    x = y - y.mean()
    v = x@x/n
    for lag in range(1, bandwidth+1):
        v += 2*(1-lag/(bandwidth+1))*(x[lag:]@x[:-lag])/n
    return max(0., float(v))


def hac_pvalue(y):
    y = np.asarray(y, dtype=float)
    v = hac_variance(y)
    if len(y) < 2:
        return 1.
    if v <= 1e-30:
        return 0. if y.mean() > 0 else 1.
    return float(ndtr(-y.mean()*np.sqrt(len(y)/v)))
