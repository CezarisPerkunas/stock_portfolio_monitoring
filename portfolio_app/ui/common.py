"""Shared Streamlit helpers: cached data loaders, session state, formatting."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import data as data_mod
from .. import db
from ..config import (
    DEFAULT_LOOKBACK_YEARS,
    DEFAULT_MC_HORIZON_DAYS,
    DEFAULT_MC_SIMS,
    DEFAULT_VAR_ALPHA,
)
from ..portfolio import compute_position_values, portfolio_return_series


def init_session_state() -> None:
    db.init_db()
    ss = st.session_state
    ss.setdefault("lookback_years", DEFAULT_LOOKBACK_YEARS)
    ss.setdefault("var_alpha", DEFAULT_VAR_ALPHA)
    ss.setdefault("mc_sims", DEFAULT_MC_SIMS)
    ss.setdefault("mc_horizon_days", DEFAULT_MC_HORIZON_DAYS)
    ss.setdefault("rf_override", None)  # None = auto from ^IRX


def sidebar_controls() -> None:
    st.sidebar.header("Settings")
    st.session_state["lookback_years"] = st.sidebar.slider(
        "Lookback (years)", min_value=1, max_value=15,
        value=int(st.session_state.get("lookback_years", DEFAULT_LOOKBACK_YEARS)),
    )
    st.session_state["var_alpha"] = st.sidebar.slider(
        "VaR / CVaR alpha", min_value=0.01, max_value=0.20,
        value=float(st.session_state.get("var_alpha", DEFAULT_VAR_ALPHA)),
        step=0.01,
    )
    st.session_state["mc_sims"] = st.sidebar.number_input(
        "MC simulations", 500, 50_000,
        value=int(st.session_state.get("mc_sims", DEFAULT_MC_SIMS)), step=500,
    )
    st.session_state["mc_horizon_days"] = st.sidebar.number_input(
        "MC horizon (trading days)", 21, 252 * 10,
        value=int(st.session_state.get("mc_horizon_days", DEFAULT_MC_HORIZON_DAYS)), step=21,
    )
    rf_in = st.sidebar.text_input(
        "Risk-free rate override (decimal, blank = auto)",
        value="" if st.session_state.get("rf_override") is None
              else str(st.session_state["rf_override"]),
    )
    try:
        st.session_state["rf_override"] = float(rf_in) if rf_in.strip() else None
    except ValueError:
        st.sidebar.warning("Invalid rate; using auto.")
        st.session_state["rf_override"] = None

    if st.sidebar.button("Clear price cache", help="Forces a fresh yfinance fetch."):
        with db.connect() as c:
            c.execute("DELETE FROM price_cache")
            c.execute("DELETE FROM meta WHERE key LIKE 'last_fetch:%'")
        st.cache_data.clear()
        st.sidebar.success("Cache cleared.")


# ---------- cached loaders ----------

@st.cache_data(show_spinner=False)
def load_holdings() -> pd.DataFrame:
    return db.list_holdings()


@st.cache_data(show_spinner="Fetching prices...")
def load_prices(tickers: tuple[str, ...], lookback_years: int) -> pd.DataFrame:
    start, end = data_mod.default_date_range(lookback_years)
    return data_mod.get_prices(tickers, start, end)


@st.cache_data(show_spinner="Fetching benchmark...")
def load_benchmark(lookback_years: int) -> pd.Series:
    start, end = data_mod.default_date_range(lookback_years)
    return data_mod.get_benchmark(start, end)


@st.cache_data(show_spinner=False)
def load_rf(override: float | None) -> float:
    if override is not None:
        return float(override)
    return data_mod.get_risk_free_rate()


def invalidate_holdings_cache() -> None:
    load_holdings.clear()


# ---------- assembled portfolio context ----------

def get_portfolio_context():
    """Return (holdings, prices, benchmark_returns, rf, port_returns, valued)."""
    holdings = load_holdings()
    if holdings.empty:
        return holdings, pd.DataFrame(), pd.Series(dtype=float), 0.0, pd.Series(dtype=float), holdings

    tickers = tuple(sorted(holdings["ticker"].unique()))
    lookback = int(st.session_state.get("lookback_years", DEFAULT_LOOKBACK_YEARS))
    prices = load_prices(tickers, lookback)
    bench = load_benchmark(lookback)
    rf = load_rf(st.session_state.get("rf_override"))

    bench_returns = bench.pct_change().dropna()
    valued = compute_position_values(holdings, prices)
    weights = valued.set_index("ticker")["weight"]
    port_returns = portfolio_return_series(prices, weights)
    return holdings, prices, bench_returns, rf, port_returns, valued


# ---------- formatters ----------

def pct(x, digits=2) -> str:
    if x is None or (isinstance(x, float) and (pd.isna(x))):
        return "—"
    return f"{x * 100:.{digits}f}%"


def num(x, digits=2) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "—"
    return f"{x:,.{digits}f}"
