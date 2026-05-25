"""Optimization page: efficient frontier.

Optimisation is gated behind an explicit button and the result is cached, so
moving sliders on the sidebar does not re-run the solver (which is the most
common cause of the page appearing to "freeze").
"""
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
if clean_prices.shape[0] < 30:
    st.warning("Need at least ~30 overlapping daily observations across all tickers.")
    st.stop()

points = st.slider("Frontier points", min_value=10, max_value=40, value=20, step=5,
                   help="More points = smoother curve but slower.")
run = st.button("Run optimization", type="primary")

cache_key = (
    tuple(clean_prices.columns),
    int(clean_prices.shape[0]),
    float(round(rf, 6)),
    int(points),
    float(clean_prices.iloc[-1].sum()),  # cheap fingerprint of latest prices
)

if run:
    st.session_state["_opt_key"] = cache_key
    st.session_state.pop("_opt_result", None)

if st.session_state.get("_opt_key") != cache_key:
    st.info("Click **Run optimization** to compute the efficient frontier.")
    st.stop()


@st.cache_data(show_spinner=False)
def _compute(key, _prices, _rf, _points):
    ms = mv = None
    ms_err = mv_err = ef_err = None
    try:
        ms = optimize(_prices, objective="max_sharpe", rf_annual=_rf)
    except Exception as e:  # noqa: BLE001
        ms_err = str(e)
    try:
        mv = optimize(_prices, objective="min_vol", rf_annual=_rf)
    except Exception as e:  # noqa: BLE001
        mv_err = str(e)
    try:
        ef = efficient_frontier(_prices, points=_points, rf_annual=_rf)
    except Exception as e:  # noqa: BLE001
        ef, ef_err = pd.DataFrame(), str(e)
    return ms, mv, ef, ms_err, mv_err, ef_err


with st.spinner("Solving optimisation problems…"):
    ms, mv, ef_df, ms_err, mv_err, ef_err = _compute(cache_key, clean_prices, rf, points)

c1, c2 = st.columns(2)
with c1:
    st.subheader("Max Sharpe")
    if ms is not None:
        st.metric("Expected return", pct(ms.expected_return))
        st.metric("Volatility", pct(ms.volatility))
        st.metric("Sharpe", f"{ms.sharpe:.3f}")
        st.dataframe(ms.weights.rename("weight").to_frame()
                     .style.format({"weight": "{:.2%}"}), use_container_width=True)
    else:
        st.error(f"Max Sharpe failed: {ms_err}")

with c2:
    st.subheader("Min Volatility")
    if mv is not None:
        st.metric("Expected return", pct(mv.expected_return))
        st.metric("Volatility", pct(mv.volatility))
        st.metric("Sharpe", f"{mv.sharpe:.3f}")
        st.dataframe(mv.weights.rename("weight").to_frame()
                     .style.format({"weight": "{:.2%}"}), use_container_width=True)
    else:
        st.error(f"Min vol failed: {mv_err}")

st.subheader("Efficient Frontier")
if ef_err:
    st.error(f"Frontier failed: {ef_err}")
elif ef_df.empty:
    st.caption("No frontier points produced (solver could not find feasible portfolios).")
else:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=ef_df["volatility"] * 100, y=ef_df["expected_return"] * 100,
        mode="lines+markers", name="Frontier",
    ))
    if ms is not None:
        fig.add_trace(go.Scatter(
            x=[ms.volatility * 100], y=[ms.expected_return * 100],
            mode="markers", name="Max Sharpe",
            marker=dict(size=12, color="gold", symbol="star"),
        ))
    if mv is not None:
        fig.add_trace(go.Scatter(
            x=[mv.volatility * 100], y=[mv.expected_return * 100],
            mode="markers", name="Min Vol",
            marker=dict(size=12, color="green", symbol="diamond"),
        ))
    fig.update_layout(xaxis_title="Volatility (%, ann.)",
                      yaxis_title="Expected return (%, ann.)")
    st.plotly_chart(fig, use_container_width=True)
