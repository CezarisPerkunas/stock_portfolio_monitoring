"""Monte Carlo page."""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from portfolio_app.metrics.montecarlo import simulate
from portfolio_app.portfolio import portfolio_value
from portfolio_app.ui.common import get_portfolio_context, init_session_state, num, pct, sidebar_controls

st.set_page_config(page_title="Monte Carlo", page_icon="🎲", layout="wide")
init_session_state()
sidebar_controls()

st.title("🎲 Monte Carlo Projection")

holdings, prices, _, _, port_returns, _ = get_portfolio_context()
if holdings.empty or port_returns.empty:
    st.info("No data. Add holdings first.")
    st.stop()

method = st.radio("Model", ["bootstrap", "parametric"], horizontal=True,
                  help="Bootstrap preserves historical tail behaviour; parametric assumes normality.")
horizon = int(st.session_state.get("mc_horizon_days", 252))
sims = int(st.session_state.get("mc_sims", 5000))
v0 = portfolio_value(holdings, prices)

st.caption(f"Horizon: **{horizon} trading days** • Sims: **{sims}** • Start value: **${num(v0)}**")

if st.button("Run simulation", type="primary"):
    with st.spinner("Simulating..."):
        res = simulate(port_returns, initial_value=v0, horizon_days=horizon,
                       sims=sims, method=method)

    pcts = res.percentiles()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("P5",  f"${num(pcts['P5'])}")
    c2.metric("P25", f"${num(pcts['P25'])}")
    c3.metric("Median", f"${num(pcts['P50'])}")
    c4.metric("P75", f"${num(pcts['P75'])}")
    c5.metric("P95", f"${num(pcts['P95'])}")
    st.metric("Probability of loss", pct(res.prob_loss()))

    # Fan chart
    paths = res.paths_sample
    x = np.arange(paths.shape[1])
    fig = go.Figure()
    for p in paths:
        fig.add_trace(go.Scatter(x=x, y=p, mode="lines",
                                 line=dict(color="rgba(70,130,180,0.08)", width=1),
                                 showlegend=False, hoverinfo="skip"))
    # Median line
    fig.add_trace(go.Scatter(x=x, y=np.median(paths, axis=0),
                             mode="lines", name="Median sample",
                             line=dict(color="black", width=2)))
    fig.update_layout(title="Monte Carlo paths (sample of 200)",
                      xaxis_title="Trading days", yaxis_title="Portfolio value")
    st.plotly_chart(fig, use_container_width=True)

    fig2 = go.Figure(data=[go.Histogram(x=res.terminal_values, nbinsx=60)])
    fig2.update_layout(title="Terminal value distribution",
                       xaxis_title="Portfolio value at horizon", yaxis_title="Count")
    st.plotly_chart(fig2, use_container_width=True)
