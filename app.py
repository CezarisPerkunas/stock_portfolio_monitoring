"""Streamlit entry point. Run with: streamlit run app.py"""
from __future__ import annotations

import streamlit as st

from portfolio_app.ui.common import init_session_state, sidebar_controls

st.set_page_config(
    page_title="Portfolio Monitor",
    page_icon="📈",
    layout="wide",
)

init_session_state()
sidebar_controls()

st.title("📈 Portfolio Monitor")
st.markdown(
    """
Use the sidebar to navigate between pages:

- **Portfolio** — enter and view holdings, P&L, allocation.
- **Performance** — returns vs benchmark over time.
- **Risk** — volatility, beta, correlation, VaR / CVaR, ratios.
- **Drawdown** — underwater chart and worst drawdowns.
- **Factor Exposure** — Fama-French regression.
- **Monte Carlo** — forward-looking simulations.
- **What-If** — see how adding a stock would change your portfolio.
- **Optimization** — efficient frontier and optimal weights.

Settings (lookback window, VaR alpha, Monte Carlo parameters, risk-free rate) live in the sidebar.
"""
)
