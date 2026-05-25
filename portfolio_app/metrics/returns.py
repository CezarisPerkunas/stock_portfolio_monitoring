"""Return calculations."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..config import TRADING_DAYS


def cumulative_returns(returns: pd.Series) -> pd.Series:
    return (1.0 + returns.fillna(0.0)).cumprod() - 1.0


def total_return(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    return float((1.0 + returns.fillna(0.0)).prod() - 1.0)


def cagr(returns: pd.Series, periods_per_year: int = TRADING_DAYS) -> float:
    if returns.empty:
        return 0.0
    tr = (1.0 + returns.fillna(0.0)).prod()
    n = len(returns)
    if n <= 0 or tr <= 0:
        return 0.0
    return float(tr ** (periods_per_year / n) - 1.0)


def time_weighted_return(returns: pd.Series) -> float:
    """Time-weighted return = compounded period returns. Equivalent to total_return
    for a buy-and-hold series with no external cash flows."""
    return total_return(returns)


def annualized_mean(returns: pd.Series, periods_per_year: int = TRADING_DAYS) -> float:
    if returns.empty:
        return 0.0
    return float(returns.mean() * periods_per_year)
