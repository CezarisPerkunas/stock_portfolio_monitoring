"""What-if engine: simulate adding a new ticker, suggest optimal weights."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from .metrics.optimize import optimize
from .metrics.ratios import sharpe_ratio
from .portfolio import portfolio_return_series
from .summary import MetricBundle, summarize


@dataclass
class WhatIfResult:
    current: MetricBundle
    hypothetical: MetricBundle
    deltas: dict
    new_weights: pd.Series


def _delta(a: MetricBundle, b: MetricBundle) -> dict:
    out = {}
    for k, va in a.as_dict().items():
        vb = b.as_dict()[k]
        try:
            out[k] = float(vb - va)
        except (TypeError, ValueError):
            out[k] = None
    return out


def simulate_addition(
    current_weights: pd.Series,
    prices_with_new: pd.DataFrame,
    new_ticker: str,
    new_weight: float,
    benchmark_returns: pd.Series | None = None,
    rf_annual: float = 0.0,
) -> WhatIfResult:
    """Build a hypothetical portfolio that adds `new_ticker` at `new_weight`,
    keeping the *relative* weights of existing holdings unchanged.

    prices_with_new: wide price frame including existing tickers + new_ticker.
    """
    new_ticker = new_ticker.upper().strip()
    w = current_weights.copy().astype(float)
    w = w[w > 0]
    if not w.empty:
        w = w / w.sum()

    # Current portfolio
    current_prices = prices_with_new[w.index].dropna(how="all")
    current_rets = portfolio_return_series(current_prices, w)
    current_bundle = summarize(current_rets, benchmark_returns, rf_annual)

    # Hypothetical
    new_weight = float(max(0.0, min(1.0, new_weight)))
    hyp_w = (w * (1.0 - new_weight)).copy()
    hyp_w[new_ticker] = hyp_w.get(new_ticker, 0.0) + new_weight
    hyp_w = hyp_w[hyp_w > 0]
    hyp_w = hyp_w / hyp_w.sum()
    hyp_prices = prices_with_new[hyp_w.index].dropna(how="all")
    hyp_rets = portfolio_return_series(hyp_prices, hyp_w)
    hyp_bundle = summarize(hyp_rets, benchmark_returns, rf_annual)

    return WhatIfResult(
        current=current_bundle,
        hypothetical=hyp_bundle,
        deltas=_delta(current_bundle, hyp_bundle),
        new_weights=hyp_w,
    )


def suggest_weight(
    current_weights: pd.Series,
    prices_with_new: pd.DataFrame,
    new_ticker: str,
    objective: Literal["max_sharpe", "min_vol"] = "max_sharpe",
    rf_annual: float = 0.0,
    scope: Literal["new_only", "full"] = "new_only",
    grid: int = 51,
) -> dict:
    """Suggest a weight for the new ticker.

    scope="new_only": hold existing relative weights fixed, scan w_new in [0,1].
    scope="full": re-optimize all weights (existing + new) via PyPortfolioOpt.
    """
    new_ticker = new_ticker.upper().strip()
    w = current_weights[current_weights > 0].astype(float)
    if not w.empty:
        w = w / w.sum()

    if scope == "full":
        tickers = list(w.index)
        if new_ticker not in tickers:
            tickers.append(new_ticker)
        prices = prices_with_new[tickers].dropna(how="all")
        res = optimize(prices, objective=objective, rf_annual=rf_annual)
        return {
            "scope": "full",
            "objective": objective,
            "weights": res.weights,
            "new_weight": float(res.weights.get(new_ticker, 0.0)),
            "expected_return": res.expected_return,
            "volatility": res.volatility,
            "sharpe": res.sharpe,
        }

    # new_only: 1-D scan
    weights_grid = np.linspace(0.0, 1.0, grid)
    best = None
    best_val = -np.inf if objective == "max_sharpe" else np.inf
    for wn in weights_grid:
        r = simulate_addition(w, prices_with_new, new_ticker, float(wn),
                              rf_annual=rf_annual)
        val = r.hypothetical.sharpe if objective == "max_sharpe" else r.hypothetical.volatility
        better = val > best_val if objective == "max_sharpe" else val < best_val
        if better:
            best_val = val
            best = (float(wn), r)
    wn, r = best
    return {
        "scope": "new_only",
        "objective": objective,
        "weights": r.new_weights,
        "new_weight": wn,
        "expected_return": r.hypothetical.cagr,
        "volatility": r.hypothetical.volatility,
        "sharpe": r.hypothetical.sharpe,
    }
