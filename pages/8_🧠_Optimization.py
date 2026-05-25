"""Optimization page: efficient frontier."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from portfolio_app.metrics.optimize import efficient_frontier, optimize
from portfolio_app.ui.common import get_portfolio_context, init_session_state, pct, sidebar_controls

st.set_page_config(page_title="Optimization", page_icon="🧠", layout="wide")
init_session_state()
sidebar_controls()

st.title("🧠 Optimization")

holdings, prices, _, rf, _, _ = get_portfolio_context()
if holdings.empty or prices.empty:
    st.info("Add holdings first.")
    st.stop()
if prices.shape[1] < 2:
    st.warning("Need at least 2 holdings for optimization.")
    st.stop()

clean_prices = prices.dropna(how="all").ffill().dropna()

c1, c2 = st.columns(2)
with c1:
    st.subheader("Max Sharpe")
    try:
        ms = optimize(clean_prices, objective="max_sharpe", rf_annual=rf)
        st.metric("Expected return", pct(ms.expected_return))
        st.metric("Volatility", pct(ms.volatility))
        st.metric("Sharpe", f"{ms.sharpe:.3f}")
        st.dataframe(ms.weights.rename("weight").to_frame()
                     .style.format({"weight": "{:.2%}"}), use_container_width=True)
    except Exception as e:
        st.error(f"Max Sharpe failed: {e}")

with c2:
    st.subheader("Min Volatility")
    try:
        mv = optimize(clean_prices, objective="min_vol", rf_annual=rf)
        st.metric("Expected return", pct(mv.expected_return))
        st.metric("Volatility", pct(mv.volatility))
        st.metric("Sharpe", f"{mv.sharpe:.3f}")
        st.dataframe(mv.weights.rename("weight").to_frame()
                     .style.format({"weight": "{:.2%}"}), use_container_width=True)
    except Exception as e:
        st.error(f"Min vol failed: {e}")

st.subheader("Efficient Frontier")
try:
    ef = efficient_frontier(clean_prices, points=30, rf_annual=rf)
    if ef.empty:
        st.caption("No frontier points produced.")
    else:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=ef["volatility"] * 100, y=ef["expected_return"] * 100,
            mode="lines+markers", name="Frontier",
        ))
        try:
            fig.add_trace(go.Scatter(
                x=[ms.volatility * 100], y=[ms.expected_return * 100],
                mode="markers", name="Max Sharpe",
                marker=dict(size=12, color="gold", symbol="star"),
            ))
        except NameError:
            pass
        try:
            fig.add_trace(go.Scatter(
                x=[mv.volatility * 100], y=[mv.expected_return * 100],
                mode="markers", name="Min Vol",
                marker=dict(size=12, color="green", symbol="diamond"),
            ))
        except NameError:
            pass
        fig.update_layout(xaxis_title="Volatility (%, ann.)",
                          yaxis_title="Expected return (%, ann.)")
        st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.error(f"Frontier failed: {e}")
