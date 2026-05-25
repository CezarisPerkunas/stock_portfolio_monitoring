"""Unified metric summaries used by UI pages."""
from __future__ import annotations

from dataclasses import dataclass, asdict

import pandas as pd

from .metrics.drawdown import drawdown_info
from .metrics.ratios import calmar_ratio, sharpe_ratio, sortino_ratio
from .metrics.returns import cagr, total_return
from .metrics.risk import (
    annualized_volatility,
    beta,
    historical_cvar,
    historical_var,
)


@dataclass
class MetricBundle:
    total_return: float
    cagr: float
    volatility: float
    sharpe: float
    sortino: float
    calmar: float
    max_drawdown: float
    var_95: float
    cvar_95: float
    beta: float

    def as_dict(self) -> dict:
        return asdict(self)


def summarize(
    returns: pd.Series,
    benchmark_returns: pd.Series | None = None,
    rf_annual: float = 0.0,
    var_alpha: float = 0.05,
) -> MetricBundle:
    dd = drawdown_info(returns)
    b = beta(returns, benchmark_returns) if benchmark_returns is not None else float("nan")
    return MetricBundle(
        total_return=total_return(returns),
        cagr=cagr(returns),
        volatility=annualized_volatility(returns),
        sharpe=sharpe_ratio(returns, rf_annual),
        sortino=sortino_ratio(returns, rf_annual),
        calmar=calmar_ratio(returns),
        max_drawdown=dd.max_drawdown,
        var_95=historical_var(returns, var_alpha),
        cvar_95=historical_cvar(returns, var_alpha),
        beta=b,
    )
