"""Evaluator-only joint Laplace moments for general policy pairs, through degree eight."""
from math import comb,factorial
import numpy as np


def joint_moments(md,ms,hd,hs):
    """Raw moments E[d^a s^b], 0<=a,b<=4, via joint cumulants.

    d and s are computed directly as portfolio difference/sum, which avoids
    subtracting large nearly equal fourth-score expressions.
    """
    md=np.atleast_1d(md);ms=np.atleast_1d(ms)
    dp=[np.ones_like(hd)];sp=[np.ones_like(hs)]
    for _ in range(4):dp.append(dp[-1]*hd);sp.append(sp[-1]*hs)
    cumulants={(1,0):md,(0,1):ms}
    for a in range(5):
        for b in range(5):
            order=a+b
            if order>=2 and order%2==0:
                cumulants[a,b]=factorial(order)/((order//2)*2**(order//2))*np.sum(dp[a]*sp[b],axis=1)
    moments={(0,0):np.ones_like(md)}
    for b in range(1,5):
        moments[0,b]=sum((comb(b-1,k-1)*cumulants[0,k]*moments[0,b-k]
                         for k in range(1,b+1) if (0,k) in cumulants),np.zeros_like(md))
    for a in range(1,5):
        for b in range(5):
            result=np.zeros_like(md)
            for i in range(a):
                for j in range(b+1):
                    if (i+1,j) in cumulants:
                        result+=comb(a-1,i)*comb(b,j)*cumulants[i+1,j]*moments[a-1-i,b-j]
            moments[a,b]=result
    return moments


def pair_moments(wb,ws,cost_difference,truth,gamma):
    wb=np.atleast_2d(wb);ws=np.atleast_2d(ws)
    d=wb-ws;s=wb+ws;dc=np.atleast_1d(cost_difference)
    m=joint_moments(d@truth.mean,s@truth.mean,d@truth.loadings,s@truth.loadings)
    mean=m[1,0]-gamma*m[1,1]/2-dc
    def score_power(order):
        result=np.zeros(len(wb))
        for i in range(order+1):
            for j in range(order+1-i):
                k=order-i-j
                result+=factorial(order)/(factorial(i)*factorial(j)*factorial(k))*(-gamma/2)**j*(-dc)**k*m[i+j,j]
        return np.maximum(result,0.)
    return mean,score_power(2),score_power(4)
