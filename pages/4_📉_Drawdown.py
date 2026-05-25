"""Drawdown page."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from portfolio_app.metrics.drawdown import drawdown_info, drawdown_series
from portfolio_app.ui.common import get_portfolio_context, init_session_state, pct, sidebar_controls

st.set_page_config(page_title="Drawdown", page_icon="📉", layout="wide")
init_session_state()
sidebar_controls()

st.title("📉 Drawdown")

holdings, _, _, _, port_returns, _ = get_portfolio_context()
if holdings.empty or port_returns.empty:
    st.info("No data. Add holdings first.")
    st.stop()

dd = drawdown_series(port_returns)
info = drawdown_info(port_returns)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Max drawdown", pct(info.max_drawdown))
c2.metric("Peak", str(info.peak_date.date()) if info.peak_date is not None else "—")
c3.metric("Trough", str(info.trough_date.date()) if info.trough_date is not None else "—")
c4.metric("Recovery",
          str(info.recovery_date.date()) if info.recovery_date is not None else "not recovered")

fig = go.Figure()
fig.add_trace(go.Scatter(x=dd.index, y=dd * 100, fill="tozeroy", name="Drawdown",
                         line=dict(color="crimson")))
fig.update_layout(title="Underwater chart (%)",
                  xaxis_title="Date", yaxis_title="Drawdown (%)")
st.plotly_chart(fig, use_container_width=True)

if info.duration_days is not None:
    st.caption(f"Peak → recovery duration: **{info.duration_days} days**.")
