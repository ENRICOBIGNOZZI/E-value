"""Observable policy geometry and analytic Laplace moment envelopes.

No true coefficients, regimes, structural labels or oracle moments enter this API.
The public coefficient set is a relaxation over ALL signal identifiers.
"""
from dataclasses import dataclass
from math import comb, factorial
import numpy as np


@dataclass(frozen=True)
class PublicRisk:
    coefficient_cap: float
    coefficient_budget: float
    beta_centers: tuple[float, ...]
    beta_radii: tuple[float, ...]
    factor_scales_max: tuple[float, ...]
    idio_scale_max: float

    def __post_init__(self):
        numbers=(self.coefficient_cap,self.coefficient_budget,self.idio_scale_max,
                 *self.beta_radii,*self.factor_scales_max,*self.beta_centers)
        if not np.isfinite(numbers).all():
            raise ValueError('Finite public risk parameters required')
        if min(self.coefficient_cap,self.coefficient_budget,self.idio_scale_max)<=0:
            raise ValueError('Positive coefficient and idiosyncratic caps required')
        if min(*self.beta_radii,*self.factor_scales_max)<0:
            raise ValueError('Nonnegative loading radii and factor scales required')
        if not len(self.beta_centers)==len(self.beta_radii)==len(self.factor_scales_max):
            raise ValueError('Risk factor dimensions differ')

    @classmethod
    def from_market_contract(cls,cfg):
        """DGP-wide restrictions, never an individual realized beta vector.

        The generator fixes beta_1=1+.5*tanh(X_i,0) and beta_2:4=tanh(X_i,1:4).
        Their public intervals are [.5,1.5] and [-1,1]. Scaling uses the larger
        of NORMAL and STRESS volatility, including stress multipliers below one.
        """
        maximum=max(1.,cfg.stress_multiplier)
        return cls(cfg.base_theta*cfg.theta_cap_multiple,
                   cfg.base_theta*cfg.theta_cap_multiple*(15+10/4+10+10),
                   (1.,0.,0.,0.),(.5,1.,1.,1.),
                   tuple(maximum*s for s in cfg.factor_scales),maximum*cfg.idio_scale)

    def support(self,coefficients):
        """Support function of {theta: 0<=theta_j<=cap, sum theta<=budget}.

        Coefficients have signals along axis zero, any number of portfolios.
        Greedy fractional-knapsack solution, invariant to signal permutation.
        """
        a=np.asarray(coefficients,dtype=float)
        if a.ndim==0 or not np.isfinite(a).all():raise ValueError('Finite coefficient arrays required')
        top=np.sort(np.maximum(a,0.),axis=0)[::-1]
        full=min(len(top),int(np.floor(self.coefficient_budget/self.coefficient_cap)))
        result=self.coefficient_cap*top[:full].sum(axis=0)
        if full<len(top):
            result=result+(self.coefficient_budget-full*self.coefficient_cap)*top[full]
        return result

    def mean_cap(self,values,stock_weights):
        a=np.asarray(values).T@np.asarray(stock_weights)
        return np.maximum(self.support(a),self.support(-a))

    def variance_cap(self,stock_weights):
        q=np.asarray(stock_weights,dtype=float)
        net=q.sum(axis=0);gross=np.abs(q).sum(axis=0)
        cap=np.zeros_like(gross)
        for center,radius,scale in zip(self.beta_centers,self.beta_radii,self.factor_scales_max):
            cap+=scale**2*(np.abs(center*net)+radius*gross)**2
        return cap+self.idio_scale_max**2*np.sum(q*q,axis=0)


def laplace_even_moment(mean_cap,variance_cap,order):
    """For |mu|<=m, x=mu+h'zeta, ||h||²<=v and standardized Laplace zeta.

    E[(h'zeta)^(2k)] <= (2k)! (v/2)^k. Noncentral even moments follow
    by binomial expansion. Valid also at v=0 and for vectorized portfolios.
    """
    if order not in (2,4,6,8):raise ValueError('Supported even orders: 2,4,6,8')
    m=np.asarray(mean_cap);v=np.asarray(variance_cap)
    if np.any(m<0) or np.any(v<0) or not np.isfinite(m).all() or not np.isfinite(v).all():
        raise ValueError('Finite nonnegative mean and variance caps required')
    result=np.zeros(np.broadcast_shapes(m.shape,v.shape))
    for k in range(order//2+1):
        result+=comb(order,2*k)*m**(order-2*k)*factorial(2*k)*(v/2)**k
    return result


def paired_score_caps(qb,qs,values,cost_difference,gamma,risk):
    """Conditional raw second/fourth moment envelopes for U(B)-U(S).

    Columns may contain multiple portfolio pairs. Only pre-return public
    functions, stock weights and exact predictable costs are used.
    """
    d=np.asarray(qb)-np.asarray(qs);s=np.asarray(qb)+np.asarray(qs)
    md,ms=risk.mean_cap(values,d),risk.mean_cap(values,s)
    vd,vs=risk.variance_cap(d),risk.variance_cap(s)
    m2d=laplace_even_moment(md,vd,2)
    m4d=laplace_even_moment(md,vd,4);m4s=laplace_even_moment(ms,vs,4)
    m8d=laplace_even_moment(md,vd,8);m8s=laplace_even_moment(ms,vs,8)
    dc=np.abs(cost_difference)
    second=(np.sqrt(m2d)+gamma/2*(m4d*m4s)**.25+dc)**2
    fourth=(m4d**.25+gamma/2*(m8d*m8s)**.125+dc)**4
    return second,fourth


def forward_score_caps(weights,previous,values,sleeves,cfg,risk):
    """Fast vectorized S=empty comparisons, one sleeve per candidate.

    Each of the 100 shadow policies keeps its own scalar previous target.
    This is a mechanism audit of FIRST ENTRY, not an adaptive portfolio backtest.
    """
    w=np.asarray(weights);b=np.asarray(previous)
    q=sleeves*w
    m=risk.mean_cap(values,q);v=risk.variance_cap(q)
    m2=laplace_even_moment(m,v,2);m4=laplace_even_moment(m,v,4);m8=laplace_even_moment(m,v,8)
    costs=cfg.proportional*np.abs(w-b)+cfg.impact*(w-b)**2/2
    second=(np.sqrt(m2)+cfg.gamma/2*np.sqrt(m4)+costs)**2
    fourth=(m4**.25+cfg.gamma/2*m8**.25+costs)**4
    return second,fourth


def uniform_forward_caps(cfg,risk):
    """Uniform envelope for one candidate vs an identically zero reference.

    Uses no feature geometry or dollar-neutrality improvements; it remains a
    separate ablation from the frozen two-policy constant Catoni certificate.
    """
    m=cfg.leverage*risk.coefficient_budget
    gross=cfg.leverage
    v=sum((s*(abs(c)+r)*gross)**2 for c,r,s in zip(
        risk.beta_centers,risk.beta_radii,risk.factor_scales_max))+risk.idio_scale_max**2*gross**2
    m2=laplace_even_moment(m,v,2);m4=laplace_even_moment(m,v,4);m8=laplace_even_moment(m,v,8)
    cost=2*cfg.proportional*cfg.leverage+2*cfg.impact*cfg.leverage**2
    return float((np.sqrt(m2)+cfg.gamma/2*np.sqrt(m4)+cost)**2),float((m4**.25+cfg.gamma/2*m8**.25+cost)**4)
