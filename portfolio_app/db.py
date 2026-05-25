"""SQLite persistence: holdings, price cache, metadata."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Iterable, Iterator

import pandas as pd

from .config import DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS holdings (
    ticker      TEXT PRIMARY KEY,
    shares      REAL NOT NULL,
    cost_basis  REAL NOT NULL,
    added_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS price_cache (
    ticker  TEXT NOT NULL,
    date    TEXT NOT NULL,
    close   REAL NOT NULL,
    PRIMARY KEY (ticker, date)
);
CREATE INDEX IF NOT EXISTS idx_price_ticker_date ON price_cache(ticker, date);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as c:
        c.executescript(SCHEMA)


# ---------- holdings ----------

def list_holdings() -> pd.DataFrame:
    with connect() as c:
        df = pd.read_sql_query(
            "SELECT ticker, shares, cost_basis, added_at FROM holdings ORDER BY ticker",
            c,
        )
    return df


def upsert_holding(ticker: str, shares: float, cost_basis: float) -> None:
    ticker = ticker.upper().strip()
    if not ticker:
        raise ValueError("ticker required")
    if shares <= 0:
        raise ValueError("shares must be > 0")
    if cost_basis < 0:
        raise ValueError("cost_basis must be >= 0")
    now = datetime.utcnow().isoformat(timespec="seconds")
    with connect() as c:
        c.execute(
            """
            INSERT INTO holdings(ticker, shares, cost_basis, added_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                shares     = excluded.shares,
                cost_basis = excluded.cost_basis
            """,
            (ticker, float(shares), float(cost_basis), now),
        )


def delete_holding(ticker: str) -> None:
    with connect() as c:
        c.execute("DELETE FROM holdings WHERE ticker = ?", (ticker.upper().strip(),))


def replace_holdings(rows: Iterable[dict]) -> None:
    """Replace the entire holdings table from an iterable of dict rows."""
    now = datetime.utcnow().isoformat(timespec="seconds")
    cleaned = []
    for r in rows:
        t = str(r.get("ticker", "")).upper().strip()
        if not t:
            continue
        shares = float(r.get("shares", 0) or 0)
        cost = float(r.get("cost_basis", 0) or 0)
        if shares <= 0:
            continue
        cleaned.append((t, shares, cost, r.get("added_at") or now))
    with connect() as c:
        c.execute("DELETE FROM holdings")
        c.executemany(
            "INSERT INTO holdings(ticker, shares, cost_basis, added_at) VALUES (?,?,?,?)",
            cleaned,
        )


# ---------- price cache ----------

def get_cached_prices(ticker: str) -> pd.Series:
    with connect() as c:
        df = pd.read_sql_query(
            "SELECT date, close FROM price_cache WHERE ticker = ? ORDER BY date",
            c,
            params=(ticker,),
        )
    if df.empty:
        return pd.Series(dtype=float, name=ticker)
    s = pd.Series(df["close"].values, index=pd.to_datetime(df["date"]), name=ticker)
    return s


def upsert_prices(ticker: str, series: pd.Series) -> None:
    if series is None or series.empty:
        return
    rows = [
        (ticker, pd.Timestamp(idx).strftime("%Y-%m-%d"), float(val))
        for idx, val in series.dropna().items()
    ]
    with connect() as c:
        c.executemany(
            """
            INSERT INTO price_cache(ticker, date, close)
            VALUES (?, ?, ?)
            ON CONFLICT(ticker, date) DO UPDATE SET close = excluded.close
            """,
            rows,
        )


# ---------- meta ----------

def get_meta(key: str) -> str | None:
    with connect() as c:
        row = c.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_meta(key: str, value: str) -> None:
    with connect() as c:
        c.execute(
            "INSERT INTO meta(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
