"""Frozen design. Returns and utility are in daily decimal units."""
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path


@dataclass(frozen=True)
class Config:
    n_assets: int = 500
    n_features: int = 30
    n_signals: int = 100
    block: int = 252
    years: int = 15
    gamma: float = 5.0
    proportional: float = 0.0001
    impact: float = 0.0001
    leverage: float = 1.0
    shrinkage: float = 0.1
    ridge: float = 1e-8
    alpha: float = 0.05
    delta0: float = 0.0001
    base_theta: float = 0.0002
    theta_cap_multiple: float = 2.0
    revive_low_fraction: float = 0.05
    feature_rho: float = 0.97
    feature_correlation: float = 0.6
    coefficient_half_life: float = 126.0
    transition_probability: float = 1 / 1008
    factor_scales: tuple = (0.009, 0.004, 0.004, 0.004)
    idio_scale: float = 0.012
    stress_multiplier: float = 1.5
    beta_bounds: tuple = (1.5, 1.0, 1.0, 1.0)
    design_seed: int = 74021
    swap_top: int = 10
    solver_tolerance: float = 1e-8
    economic_tolerance: float = 1e-8
    state_matched_oracle: bool = True
    label: str = "main-design"

    def __post_init__(self):
        if (self.n_features, self.n_signals) != (30, 100):
            raise ValueError("The public library has exactly 30 characteristics and 100 signals")
        if self.n_assets < 4 or self.block < 2 or self.years < 2:
            raise ValueError("Insufficient observations or assets")
        if min(self.gamma, self.leverage, self.ridge, self.delta0, self.base_theta) <= 0:
            raise ValueError("Positive economic and risk parameters required")
        if min(self.proportional, self.impact) < 0:
            raise ValueError("Costs must be nonnegative")
        if not 0 < self.alpha < 1 or not 0 <= self.shrinkage <= 1:
            raise ValueError("Invalid alpha or shrinkage")
        if not 0 <= self.feature_rho < 1 or not 0 <= self.feature_correlation < 1:
            raise ValueError("Invalid characteristic dynamics")
        if not 0 <= self.transition_probability <= 1 or self.theta_cap_multiple < 1:
            raise ValueError("Invalid regime dynamics")
        if not 0 <= self.revive_low_fraction <= 1 or self.coefficient_half_life <= 0:
            raise ValueError("Invalid coefficient dynamics")
        if len(self.factor_scales) != 4 or len(self.beta_bounds) != 4:
            raise ValueError("Exactly four factors required")
        if min(*self.factor_scales, *self.beta_bounds, self.idio_scale, self.stress_multiplier, self.solver_tolerance) <= 0:
            raise ValueError("Risk scales and solver tolerance must be positive")
        if not 0 <= self.swap_top <= 10:
            raise ValueError("Swap shortlist must be between zero and ten")

    def to_dict(self):
        return asdict(self)

    @property
    def digest(self):
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True).encode()).hexdigest()

    @classmethod
    def read(cls, path):
        return cls(**json.loads(Path(path).read_text()))
