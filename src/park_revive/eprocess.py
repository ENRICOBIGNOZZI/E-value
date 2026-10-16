"""Single-episode Catoni supermartingale. Never certify a sample variance."""
from dataclasses import dataclass
import numpy as np


def phi(x):
    x = np.asarray(x, dtype=float)
    a = np.abs(x)
    # Small branch retains first-order precision; large branch never squares x.
    out = np.empty_like(a)
    small = a <= 1
    out[small] = np.log1p(a[small] + a[small] ** 2 / 2)
    q = a[~small]
    out[~small] = 2 * np.log(q) - np.log(2.) + np.log1p(2 / q + 2 * (1 / q)**2)
    out *= np.sign(x)
    return float(out) if out.ndim == 0 else out


def public_envelope(cfg):
    """Uniform bound, using only declared risk caps, sleeve leverage and costs.

    |mu_stock| <= sum theta_caps; variance <= sum(beta_cap*sigma)^2 + sigma_e^2.
    Portfolio stock leverage <= L, so these imply mean/variance bounds L*m,L²*v.
    Independent standardized Laplace shocks have fourth cumulant 3.
    """
    caps = cfg.base_theta * cfg.theta_cap_multiple * (15 + 10 / 4 + 10 + 10)
    m = cfg.leverage * caps
    v = cfg.leverage**2 * cfg.stress_multiplier**2 * (
        sum((a * b)**2 for a, b in zip(cfg.factor_scales, cfg.beta_bounds)) + cfg.idio_scale**2)
    m2 = m*m + v
    m4 = m**4 + 6*m*m*v + 6*v*v
    cmax = 2*cfg.proportional*cfg.leverage + 2*cfg.impact*cfg.leverage**2
    nu2 = 12*(m2 + cfg.gamma**2*m4/4 + cmax**2)
    if cfg.delta0 > np.sqrt(nu2):
        raise ValueError("Design effect must not exceed sqrt(moment bound)")
    return dict(mean_cap=m, variance_cap=v, m2=m2, m4=m4, cost_cap=cmax, nu2=nu2)


@dataclass
class Evidence:
    nu2: float
    delta0: float
    log_e: float = 0.0
    total: float = 0.0
    n: int = 0
    bet: float = 0.0

    def start_block(self):
        effect = self.delta0 if self.n == 0 else max(0., self.total/self.n)
        self.bet = min(effect/(2*self.nu2), 1/(2*np.sqrt(self.nu2)))

    def update(self, y):
        self.log_e += phi(self.bet*y) - self.bet**2*self.nu2/2
        self.total += y
        self.n += 1

    @property
    def mean(self):
        return self.total/self.n if self.n else 0.
