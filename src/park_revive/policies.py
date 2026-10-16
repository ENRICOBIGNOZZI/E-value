from dataclasses import dataclass, field
import numpy as np
from .costs import cost_components, utility


@dataclass
class Policy:
    support: tuple
    previous: np.ndarray
    weights: np.ndarray = field(default=None)
    certificate: tuple = (0.,0.,0.)

    def prepare(self, optimizer):
        solution = optimizer.solve(self.support,self.previous)
        self.weights = solution.weights
        self.certificate = (solution.primal_residual,solution.dual_residual,solution.gap)

    def realize(self, returns, cfg):
        linear, quadratic = cost_components(self.weights,self.previous,cfg)
        turnover = float(np.abs(self.weights-self.previous).sum())
        gross = float(self.weights@returns)
        u = float(utility(gross,linear+quadratic,cfg.gamma))
        self.previous = self.weights.copy()
        return dict(gross=gross,net=gross-linear-quadratic,utility=u,
                    linear_cost=linear,impact_cost=quadratic,turnover=turnover)
