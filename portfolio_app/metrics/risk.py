"""Risk metrics: volatility, beta, correlation, VaR/CVaR."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from ..config import TRADING_DAYS


def annualized_volatility(returns: pd.Series, periods_per_year: int = TRADING_DAYS) -> float:
    if returns.empty:
        return 0.0
    return float(returns.std(ddof=1) * np.sqrt(periods_per_year))


def beta(returns: pd.Series, benchmark: pd.Series) -> float:
    aligned = pd.concat([returns, benchmark], axis=1, join="inner").dropna()
    if len(aligned) < 2:
        return float("nan")
    cov = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1], ddof=1)
    var_b = cov[1, 1]
    if var_b <= 0:
        return float("nan")
    return float(cov[0, 1] / var_b)


def correlation_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    return returns.corr()


def historical_var(returns: pd.Series, alpha: float = 0.05) -> float:
    """Historical VaR as a positive loss fraction (e.g. 0.03 = lose 3%)."""
    if returns.empty:
        return 0.0
    q = float(np.quantile(returns.dropna(), alpha))
    return float(-q)


def historical_cvar(returns: pd.Series, alpha: float = 0.05) -> float:
    if returns.empty:
        return 0.0
    r = returns.dropna()
    q = np.quantile(r, alpha)
    tail = r[r <= q]
    if tail.empty:
        return float(-q)
    return float(-tail.mean())


def parametric_var(returns: pd.Series, alpha: float = 0.05) -> float:
    if returns.empty:
        return 0.0
    mu = returns.mean()
    sigma = returns.std(ddof=1)
    z = stats.norm.ppf(alpha)
    return float(-(mu + z * sigma))
