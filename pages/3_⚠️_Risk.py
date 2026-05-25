"""Risk page: vol, beta, correlation, VaR/CVaR, ratios."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from portfolio_app.config import BENCHMARK_TICKER
from portfolio_app.summary import summarize
from portfolio_app.ui.common import get_portfolio_context, init_session_state, pct, sidebar_controls

st.set_page_config(page_title="Risk", page_icon="⚠️", layout="wide")
init_session_state()
sidebar_controls()

st.title("⚠️ Risk")

holdings, prices, bench_returns, rf, port_returns, _ = get_portfolio_context()
if holdings.empty or port_returns.empty:
    st.info("No data. Add holdings first.")
    st.stop()

alpha = float(st.session_state.get("var_alpha", 0.05))
bundle = summarize(port_returns, bench_returns, rf_annual=rf, var_alpha=alpha)

c1, c2, c3 = st.columns(3)
c1.metric("Annualized volatility", pct(bundle.volatility))
c2.metric(f"Beta vs {BENCHMARK_TICKER}", f"{bundle.beta:.3f}" if pd.notna(bundle.beta) else "—")
c3.metric("Risk-free (annual)", pct(rf))

c1, c2, c3 = st.columns(3)
c1.metric("Sharpe", f"{bundle.sharpe:.3f}")
c2.metric("Sortino", f"{bundle.sortino:.3f}")
c3.metric("Calmar", f"{bundle.calmar:.3f}")

c1, c2 = st.columns(2)
c1.metric(f"Historical VaR ({int(alpha*100)}%)", pct(bundle.var_95))
c2.metric(f"Historical CVaR ({int(alpha*100)}%)", pct(bundle.cvar_95))

st.subheader("Correlation matrix (daily returns)")
rets = prices.pct_change().dropna(how="all")
if rets.shape[1] >= 2:
    corr = rets.corr()
    fig = px.imshow(corr, text_auto=".2f", aspect="auto", zmin=-1, zmax=1,
                    color_continuous_scale="RdBu_r")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.caption("Need at least 2 holdings for a correlation matrix.")

st.subheader("Return distribution")
fig = px.histogram(port_returns * 100, nbins=60, title="Daily portfolio returns (%)")
fig.update_layout(showlegend=False, xaxis_title="Return (%)", yaxis_title="Count")
st.plotly_chart(fig, use_container_width=True)
