"""Position math: market value, weights, P&L."""
from __future__ import annotations

import pandas as pd


def compute_position_values(holdings: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """Augment holdings with current price, market value, cost, P&L.

    holdings: columns [ticker, shares, cost_basis]  (cost_basis is per-share)
    prices: wide DataFrame, columns = tickers
    """
    if holdings.empty or prices.empty:
        return holdings.assign(price=0.0, market_value=0.0, cost_value=0.0,
                               pnl=0.0, pnl_pct=0.0, weight=0.0)
    last = prices.ffill().iloc[-1]
    df = holdings.copy()
    df["price"] = df["ticker"].map(last).astype(float)
    df["market_value"] = df["shares"] * df["price"]
    df["cost_value"] = df["shares"] * df["cost_basis"]
    df["pnl"] = df["market_value"] - df["cost_value"]
    df["pnl_pct"] = (df["pnl"] / df["cost_value"]).where(df["cost_value"] > 0, 0.0)
    total = df["market_value"].sum()
    df["weight"] = df["market_value"] / total if total > 0 else 0.0
    return df


def compute_weights(holdings: pd.DataFrame, prices: pd.DataFrame) -> pd.Series:
    """Current portfolio weights indexed by ticker."""
    valued = compute_position_values(holdings, prices)
    return valued.set_index("ticker")["weight"]


def portfolio_value(holdings: pd.DataFrame, prices: pd.DataFrame) -> float:
    valued = compute_position_values(holdings, prices)
    return float(valued["market_value"].sum())


def portfolio_return_series(prices: pd.DataFrame, weights: pd.Series) -> pd.Series:
    """Daily portfolio simple returns from prices and static weights."""
    if prices.empty:
        return pd.Series(dtype=float)
    rets = prices.pct_change().dropna(how="all")
    # Align weights to columns
    w = weights.reindex(rets.columns).fillna(0.0)
    s = w.sum()
    if s > 0:
        w = w / s
    port = (rets * w).sum(axis=1)
    port.name = "portfolio"
    return port
