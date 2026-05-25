"""Drawdown analysis."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class DrawdownInfo:
    max_drawdown: float        # negative number, e.g. -0.34
    peak_date: pd.Timestamp | None
    trough_date: pd.Timestamp | None
    recovery_date: pd.Timestamp | None
    duration_days: int | None  # peak -> recovery, None if not recovered


def drawdown_series(returns: pd.Series) -> pd.Series:
    if returns.empty:
        return pd.Series(dtype=float)
    wealth = (1.0 + returns.fillna(0.0)).cumprod()
    peak = wealth.cummax()
    dd = wealth / peak - 1.0
    dd.name = "drawdown"
    return dd


def drawdown_info(returns: pd.Series) -> DrawdownInfo:
    if returns.empty:
        return DrawdownInfo(0.0, None, None, None, None)
    dd = drawdown_series(returns)
    trough = dd.idxmin()
    max_dd = float(dd.loc[trough])
    wealth = (1.0 + returns.fillna(0.0)).cumprod()
    peak_val = wealth.loc[:trough].cummax().iloc[-1]
    peak = wealth.loc[:trough][wealth.loc[:trough] == peak_val].index[0]
    after = wealth.loc[trough:]
    recovered = after[after >= peak_val]
    recovery = recovered.index[0] if not recovered.empty else None
    duration = (recovery - peak).days if recovery is not None else None
    return DrawdownInfo(max_dd, peak, trough, recovery, duration)
