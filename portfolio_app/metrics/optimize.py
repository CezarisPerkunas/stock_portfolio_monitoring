"""Portfolio optimization via PyPortfolioOpt."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from ..config import TRADING_DAYS


@dataclass
class OptResult:
    weights: pd.Series           # index = ticker, sum to 1
    expected_return: float
    volatility: float
    sharpe: float


def _ef(prices: pd.DataFrame, rf_annual: float):
    from pypfopt import EfficientFrontier, expected_returns, risk_models

    mu = expected_returns.mean_historical_return(prices, frequency=TRADING_DAYS)
    S = risk_models.sample_cov(prices, frequency=TRADING_DAYS)
    ef = EfficientFrontier(mu, S, weight_bounds=(0, 1))
    ef.risk_free_rate = rf_annual
    return ef, mu, S


def _as_result(ef, rf_annual: float) -> OptResult:
    weights = pd.Series(ef.clean_weights())
    weights = weights[weights > 1e-6]
    weights = weights / weights.sum()
    perf = ef.portfolio_performance(risk_free_rate=rf_annual)
    return OptResult(weights, float(perf[0]), float(perf[1]), float(perf[2]))


def optimize(
    prices: pd.DataFrame,
    objective: Literal["max_sharpe", "min_vol"] = "max_sharpe",
    rf_annual: float = 0.0,
) -> OptResult:
    ef, _, _ = _ef(prices, rf_annual)
    if objective == "max_sharpe":
        ef.max_sharpe(risk_free_rate=rf_annual)
    else:
        ef.min_volatility()
    return _as_result(ef, rf_annual)


def efficient_frontier(prices: pd.DataFrame, points: int = 25,
                       rf_annual: float = 0.0) -> pd.DataFrame:
    from pypfopt import EfficientFrontier, expected_returns, risk_models

    mu = expected_returns.mean_historical_return(prices, frequency=TRADING_DAYS)
    S = risk_models.sample_cov(prices, frequency=TRADING_DAYS)
    lo, hi = float(mu.min()), float(mu.max())
    targets = np.linspace(lo + 1e-6, hi - 1e-6, points)
    rows = []
    for t in targets:
        try:
            ef = EfficientFrontier(mu, S, weight_bounds=(0, 1))
            ef.efficient_return(target_return=float(t))
            perf = ef.portfolio_performance(risk_free_rate=rf_annual)
            rows.append({"target_return": t, "expected_return": perf[0],
                         "volatility": perf[1], "sharpe": perf[2]})
        except Exception:
            continue
    return pd.DataFrame(rows)
