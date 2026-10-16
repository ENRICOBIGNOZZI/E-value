"""One financial DGP; material separation between observable and truth objects."""
from dataclasses import dataclass
import numpy as np
from .features import make_library, evaluate
from .sleeves import sleeve_weights


@dataclass(frozen=True)
class Observed:
    day: int
    returns: np.ndarray
    signal_ids: tuple


@dataclass(frozen=True)
class Truth:
    day: int
    mean: np.ndarray
    loadings: np.ndarray
    second: np.ndarray
    theta: np.ndarray
    regime: int
    deteriorated: bool


class Market:
    def __init__(self, cfg, seed):
        self.cfg = cfg
        self.rng = np.random.default_rng(np.random.SeedSequence([seed, 11]))
        self.library = make_library(cfg.design_seed)
        self.ids = tuple(f.signal_id for f in self.library)
        d = cfg.n_features
        corr = np.eye(d)
        for start, stop in ((0, 20), (20, 30)):
            for i in range(start, stop):
                for j in range(start, stop):
                    if i != j and i//5 == j//5:
                        corr[i,j] = cfg.feature_correlation
        self.chol = np.linalg.cholesky(corr)
        self.latent = self.rng.normal(size=(cfg.n_assets, d))@self.chol.T
        z = np.tanh(self.latent)
        self.beta = np.column_stack((1+.5*z[:,0], z[:,1:4]))
        self.base = cfg.base_theta*np.r_[np.ones(15), np.ones(10)/4, np.ones(20), np.zeros(55)]
        self.theta = self.base.copy()
        self.regime = 0
        self.deteriorated = False
        self.day = 0

    def step(self):
        cfg = self.cfg
        z = np.tanh(self.latent)
        values = evaluate(z, self.library)
        p = sleeve_weights(values)
        stock_mean = values@self.theta
        multiplier = cfg.stress_multiplier if self.regime else 1.
        factor_scale = np.array(cfg.factor_scales)*multiplier
        idio_scale = cfg.idio_scale*multiplier
        mu = p.T@stock_mean
        load = np.column_stack(((p.T@self.beta)*factor_scale, p.T*idio_scale))
        second = np.outer(mu, mu)+load@load.T
        shocks = self.rng.laplace(0, 1/np.sqrt(2), 4+cfg.n_assets)
        a = mu+load@shocks
        truth = Truth(self.day, mu, load, second, self.theta.copy(), self.regime, self.deteriorated)
        obs = Observed(self.day, a, self.ids)
        # Advance hidden state only after producing this day's previsible quantities.
        target = self.base.copy()
        if self.deteriorated:
            target[25:35] = 0
        if self.regime:
            target[35:45] *= cfg.revive_low_fraction
        rho = 2**(-1/cfg.coefficient_half_life)
        innovation = self.rng.uniform(-.01, .01, 100)*self.base
        self.theta = np.clip(rho*self.theta+(1-rho)*target+innovation, 0, cfg.theta_cap_multiple*self.base)
        if self.rng.random() < cfg.transition_probability:
            self.regime = 1-self.regime
        self.deteriorated |= bool(self.regime)
        self.latent = cfg.feature_rho*self.latent+np.sqrt(1-cfg.feature_rho**2)*(self.rng.normal(size=self.latent.shape)@self.chol.T)
        self.day += 1
        return obs, truth
