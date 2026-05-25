"""Monte Carlo forward projections."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from ..config import TRADING_DAYS


@dataclass
class MCResult:
    terminal_values: np.ndarray   # shape (sims,)
    paths_sample: np.ndarray      # shape (min(sims, 200), horizon+1)
    horizon_days: int
    initial_value: float

    def percentiles(self, qs=(0.05, 0.25, 0.5, 0.75, 0.95)) -> pd.Series:
        return pd.Series(
            {f"P{int(q*100)}": float(np.quantile(self.terminal_values, q)) for q in qs}
        )

    def prob_loss(self) -> float:
        return float((self.terminal_values < self.initial_value).mean())


def simulate(
    returns: pd.Series,
    initial_value: float,
    horizon_days: int = TRADING_DAYS,
    sims: int = 5000,
    method: Literal["parametric", "bootstrap"] = "bootstrap",
    seed: int | None = 42,
) -> MCResult:
    rng = np.random.default_rng(seed)
    r = returns.dropna().values
    if r.size == 0 or initial_value <= 0:
        return MCResult(np.array([initial_value]), np.array([[initial_value]]), horizon_days, initial_value)

    if method == "parametric":
        mu = r.mean()
        sigma = r.std(ddof=1)
        shocks = rng.normal(mu, sigma, size=(sims, horizon_days))
    else:
        idx = rng.integers(0, r.size, size=(sims, horizon_days))
        shocks = r[idx]

    growth = np.cumprod(1.0 + shocks, axis=1)
    paths = np.concatenate([np.ones((sims, 1)), growth], axis=1) * initial_value
    terminal = paths[:, -1]
    sample_n = min(sims, 200)
    sample_idx = rng.choice(sims, size=sample_n, replace=False)
    return MCResult(terminal, paths[sample_idx], horizon_days, initial_value)
