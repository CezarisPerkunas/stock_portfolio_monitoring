"""Risk-adjusted performance ratios."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..config import TRADING_DAYS
from .drawdown import drawdown_info
from .returns import cagr


def sharpe_ratio(returns: pd.Series, rf_annual: float = 0.0,
                 periods_per_year: int = TRADING_DAYS) -> float:
    if returns.empty:
        return 0.0
    rf_per = rf_annual / periods_per_year
    excess = returns - rf_per
    sd = excess.std(ddof=1)
    if sd <= 0 or np.isnan(sd):
        return 0.0
    return float(excess.mean() / sd * np.sqrt(periods_per_year))


def sortino_ratio(returns: pd.Series, rf_annual: float = 0.0,
                  periods_per_year: int = TRADING_DAYS) -> float:
    if returns.empty:
        return 0.0
    rf_per = rf_annual / periods_per_year
    excess = returns - rf_per
    downside = excess[excess < 0]
    dd_std = downside.std(ddof=1) if len(downside) > 1 else 0.0
    if not dd_std or np.isnan(dd_std):
        return 0.0
    return float(excess.mean() / dd_std * np.sqrt(periods_per_year))


def calmar_ratio(returns: pd.Series, periods_per_year: int = TRADING_DAYS) -> float:
    if returns.empty:
        return 0.0
    info = drawdown_info(returns)
    if info.max_drawdown == 0:
        return 0.0
    return float(cagr(returns, periods_per_year) / abs(info.max_drawdown))
