"""One economic objective shared by every policy and evaluator."""
import numpy as np


def cost_components(w, b, cfg, liquidity=None):
    d = np.asarray(w) - b
    linear = cfg.proportional * np.abs(d).sum()
    quadratic = cfg.impact * float(d @ d if liquidity is None else d @ liquidity @ d) / 2
    return float(linear), float(quadratic)


def utility(gross, cost, gamma):
    return gross - gamma * gross**2 / 2 - cost


def expected_utility(w, b, mu, second, cfg):
    return float(w @ mu - cfg.gamma * (w @ second @ w) / 2 - sum(cost_components(w, b, cfg)))
