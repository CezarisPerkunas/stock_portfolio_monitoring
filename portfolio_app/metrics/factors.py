"""Fama-French factor exposure via pandas-datareader."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd


@dataclass
class FactorResult:
    alpha_annual: float
    coefficients: pd.Series  # index = factor name (excluding alpha)
    tstats: pd.Series
    r_squared: float
    n_obs: int


def _load_factors(model: Literal["3", "5"], start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Load Ken French daily factors. Returns decimals (not %)."""
    from pandas_datareader import data as pdr

    dataset = "F-F_Research_Data_Factors_daily" if model == "3" else "F-F_Research_Data_5_Factors_2x3_daily"
    raw = pdr.DataReader(dataset, "famafrench", start=start, end=end)[0] / 100.0
    raw.index = pd.to_datetime(raw.index).tz_localize(None)
    return raw


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
