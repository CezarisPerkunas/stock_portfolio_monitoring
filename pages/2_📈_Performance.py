"""Performance page: cumulative return vs benchmark."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from portfolio_app.config import BENCHMARK_TICKER
from portfolio_app.metrics.returns import cagr, cumulative_returns, total_return
from portfolio_app.ui.common import (
    get_portfolio_context,
    init_session_state,
    pct,
    sidebar_controls,
)

st.set_page_config(page_title="Performance", page_icon="📈", layout="wide")
init_session_state()
sidebar_controls()

st.title("📈 Performance")

holdings, prices, bench_returns, _, port_returns, _ = get_portfolio_context()
if holdings.empty or prices.empty or port_returns.empty:
    st.info("No data. Add holdings first.")
    st.stop()

# Align portfolio and benchmark
df = pd.concat([port_returns.rename("Portfolio"),
                bench_returns.rename(BENCHMARK_TICKER)], axis=1).dropna()

if df.empty:
    st.warning("Insufficient overlapping data.")
    st.stop()

cum = df.apply(cumulative_returns)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Portfolio total return", pct(total_return(df["Portfolio"])))
c2.metric(f"{BENCHMARK_TICKER} total return", pct(total_return(df[BENCHMARK_TICKER])))
c3.metric("Portfolio CAGR", pct(cagr(df["Portfolio"])))
c4.metric(f"{BENCHMARK_TICKER} CAGR", pct(cagr(df[BENCHMARK_TICKER])))

fig = go.Figure()
for col in cum.columns:
    fig.add_trace(go.Scatter(x=cum.index, y=cum[col] * 100, mode="lines", name=col))
fig.update_layout(
    title="Cumulative return (%)",
    xaxis_title="Date", yaxis_title="Cumulative return (%)",
    legend=dict(orientation="h", y=-0.2),
)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Period returns")
periods = {
    "1M": 21, "3M": 63, "6M": 126, "YTD": None,
    "1Y": 252, "3Y": 252 * 3, "5Y": 252 * 5,
}
rows = []
for label, n in periods.items():
    if label == "YTD":
        ytd_start = pd.Timestamp(df.index[-1].year, 1, 1)
        sub = df.loc[df.index >= ytd_start]
    else:
        if n is None or n >= len(df):
            sub = df
        else:
            sub = df.iloc[-n:]
    if sub.empty:
        continue
    rows.append({
        "Period": label,
        "Portfolio": total_return(sub["Portfolio"]),
        BENCHMARK_TICKER: total_return(sub[BENCHMARK_TICKER]),
    })
per_df = pd.DataFrame(rows).set_index("Period")
st.dataframe(per_df.style.format("{:.2%}"), use_container_width=True)
