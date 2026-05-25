"""Price data access: yfinance with SQLite-backed cache."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

import pandas as pd
import yfinance as yf

from . import db
from .config import BENCHMARK_TICKER, CACHE_REFRESH_HOURS, RISK_FREE_TICKER, TRADING_DAYS


def _today() -> pd.Timestamp:
    return pd.Timestamp(datetime.utcnow().date())


def _refresh_due(ticker: str) -> bool:
    last = db.get_meta(f"last_fetch:{ticker}")
    if not last:
        return True
    try:
        ts = datetime.fromisoformat(last)
    except ValueError:
        return True
    return datetime.utcnow() - ts > timedelta(hours=CACHE_REFRESH_HOURS)


def _mark_fetched(ticker: str) -> None:
    db.set_meta(f"last_fetch:{ticker}", datetime.utcnow().isoformat(timespec="seconds"))


def _fetch_yf(ticker: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    """Fetch adjusted close prices for a single ticker."""
    df = yf.download(
        ticker,
        start=start.strftime("%Y-%m-%d"),
        end=(end + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
        progress=False,
        auto_adjust=True,
        threads=False,
    )
    if df is None or df.empty:
        return pd.Series(dtype=float, name=ticker)
    # yfinance may return multi-index columns for single ticker in some versions
    if isinstance(df.columns, pd.MultiIndex):
        try:
            close = df["Close"][ticker]
        except KeyError:
            close = df["Close"].iloc[:, 0]
    else:
        close = df["Close"]
    close = close.dropna()
    close.name = ticker
    close.index = pd.to_datetime(close.index).tz_localize(None)
    return close


def get_price_series(ticker: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    """Return adjusted-close series for ticker over [start, end], using cache."""
    ticker = ticker.upper().strip()
    cached = db.get_cached_prices(ticker)
    need_fetch = False

    if cached.empty:
        need_fetch = True
        fetch_start, fetch_end = start, end
    else:
        fetch_start = start
        fetch_end = end
        missing_left = start < cached.index.min()
        missing_right = end > cached.index.max()
        stale = _refresh_due(ticker) and end >= cached.index.max()
        if missing_left or missing_right or stale:
            need_fetch = True
            if missing_left and not missing_right and not stale:
                fetch_end = cached.index.min()
            elif missing_right and not missing_left:
                fetch_start = cached.index.max()

    if need_fetch:
        fetched = _fetch_yf(ticker, fetch_start, fetch_end)
        if not fetched.empty:
            db.upsert_prices(ticker, fetched)
        _mark_fetched(ticker)
        cached = db.get_cached_prices(ticker)

    if cached.empty:
        return cached
    return cached.loc[(cached.index >= start) & (cached.index <= end)]


def get_prices(tickers: Iterable[str], start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Return a wide DataFrame of adjusted closes (columns = tickers)."""
    series_list = []
    for t in tickers:
        s = get_price_series(t, start, end)
        if not s.empty:
            series_list.append(s)
    if not series_list:
        return pd.DataFrame()
    df = pd.concat(series_list, axis=1).sort_index()
    return df


def get_benchmark(start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    return get_price_series(BENCHMARK_TICKER, start, end)


def get_risk_free_rate(default: float = 0.04) -> float:
    """Return current annualized risk-free rate as a decimal (e.g. 0.05).

    Uses ^IRX (13-week T-bill yield, quoted in % annualized). Falls back to default.
    """
    try:
        end = _today()
        start = end - pd.Timedelta(days=30)
        s = _fetch_yf(RISK_FREE_TICKER, start, end)
        if not s.empty:
            return float(s.iloc[-1]) / 100.0
    except Exception:
        pass
    return default


def default_date_range(lookback_years: int) -> tuple[pd.Timestamp, pd.Timestamp]:
    end = _today()
    start = end - pd.DateOffset(years=lookback_years)
    return pd.Timestamp(start), end
