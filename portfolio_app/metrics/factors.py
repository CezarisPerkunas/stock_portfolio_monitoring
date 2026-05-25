"""Fama-French factor exposure.

Fetches Ken French daily factor CSVs directly (bypasses pandas-datareader,
which is incompatible with newer pandas versions due to a deprecated
``deprecate_kwarg`` signature).
"""
from __future__ import annotations

import io
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
import requests

from ..config import DATA_DIR

_FF_BASE = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp"
_DATASETS = {
    "3": "F-F_Research_Data_Factors_daily",
    "5": "F-F_Research_Data_5_Factors_2x3_daily",
}
_CACHE_TTL_SECONDS = 24 * 3600  # refresh once per day


@dataclass
class FactorResult:
    alpha_annual: float
    coefficients: pd.Series  # index = factor name (excluding alpha)
    tstats: pd.Series
    r_squared: float
    n_obs: int


def _cache_path(model: Literal["3", "5"]) -> Path:
    return DATA_DIR / f"ff_{model}_factors_daily.parquet"


def _download_ff_zip(dataset: str) -> bytes:
    """Download a Ken French factor zip. Uses `requests` so HTTP(S)_PROXY env
    vars and system proxy settings are honoured."""
    url = f"{_FF_BASE}/{dataset}_CSV.zip"
    headers = {"User-Agent": "stock-portfolio-monitor/1.0"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.content


def _parse_ff_csv(raw_bytes: bytes) -> pd.DataFrame:
    """Parse a Ken French daily-factors CSV from the contents of the ZIP."""
    with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
        name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
        text = zf.read(name).decode("utf-8", errors="replace")

    # Find the header line (starts with empty cell then factor names like "Mkt-RF,SMB,HML,RF")
    lines = text.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if "Mkt-RF" in line and "RF" in line:
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("Could not locate FF header line in CSV")

    # Daily data is one continuous block; stop at first blank line after data starts.
    data_lines = [lines[header_idx]]
    for line in lines[header_idx + 1:]:
        if not line.strip():
            break
        # data rows start with an 8-digit date
        first = line.split(",", 1)[0].strip()
        if not (first.isdigit() and len(first) == 8):
            break
        data_lines.append(line)

    df = pd.read_csv(io.StringIO("\n".join(data_lines)))
    df = df.rename(columns={df.columns[0]: "Date"})
    df["Date"] = pd.to_datetime(df["Date"], format="%Y%m%d")
    df = df.set_index("Date").sort_index()
    # Values are in percent — convert to decimals.
    df = df.astype(float) / 100.0
    return df


def _load_factors(model: Literal["3", "5"],
                  start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    cache = _cache_path(model)
    fresh = (cache.exists()
             and time.time() - cache.stat().st_mtime < _CACHE_TTL_SECONDS)
    if not fresh:
        raw = _download_ff_zip(_DATASETS[model])
        df = _parse_ff_csv(raw)
        df.to_parquet(cache)
    else:
        df = pd.read_parquet(cache)

    df.index = pd.to_datetime(df.index).tz_localize(None)
    mask = (df.index >= pd.Timestamp(start)) & (df.index <= pd.Timestamp(end))
    return df.loc[mask]


def factor_regression(returns: pd.Series, model: Literal["3", "5"] = "3") -> FactorResult:
    """Regress portfolio excess returns on FF factors. `returns` are simple daily returns."""
    import statsmodels.api as sm

    if returns.empty:
        return FactorResult(0.0, pd.Series(dtype=float), pd.Series(dtype=float), 0.0, 0)
    start = returns.index.min()
    end = returns.index.max()
    factors = _load_factors(model, start, end)
    df = pd.concat([returns.rename("port"), factors], axis=1, join="inner").dropna()
    if df.empty or "RF" not in df.columns:
        return FactorResult(0.0, pd.Series(dtype=float), pd.Series(dtype=float), 0.0, 0)

    y = df["port"] - df["RF"]
    factor_cols = [c for c in df.columns if c not in ("port", "RF")]
    X = sm.add_constant(df[factor_cols])
    res = sm.OLS(y, X).fit()

    alpha_daily = float(res.params.get("const", 0.0))
    alpha_annual = (1.0 + alpha_daily) ** 252 - 1.0
    coefs = res.params.drop("const")
    tstats = res.tvalues.drop("const")
    return FactorResult(
        alpha_annual=float(alpha_annual),
        coefficients=coefs,
        tstats=tstats,
        r_squared=float(res.rsquared),
        n_obs=int(res.nobs),
    )
