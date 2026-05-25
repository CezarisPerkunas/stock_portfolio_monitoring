"""Fama-French factor exposure page."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from portfolio_app.metrics.factors import factor_regression
from portfolio_app.ui.common import get_portfolio_context, init_session_state, pct, sidebar_controls

st.set_page_config(page_title="Factors", page_icon="🧬", layout="wide")
init_session_state()
sidebar_controls()

st.title("🧬 Factor Exposure (Fama-French)")

holdings, _, _, _, port_returns, _ = get_portfolio_context()
if holdings.empty or port_returns.empty:
    st.info("No data. Add holdings first.")
    st.stop()

model = st.radio("Model", ["3", "5"], horizontal=True,
                 help="3-factor: Mkt-RF, SMB, HML. 5-factor adds RMW, CMA.")

if st.button("Run regression", type="primary"):
    try:
        with st.spinner("Loading factors and fitting..."):
            res = factor_regression(port_returns, model=model)
    except Exception as e:
        st.error(f"Factor regression failed: {e}")
        st.stop()

    c1, c2, c3 = st.columns(3)
    c1.metric("Annualized α", pct(res.alpha_annual))
    c2.metric("R²", f"{res.r_squared:.3f}")
    c3.metric("Observations", f"{res.n_obs}")

    df = pd.DataFrame({"coefficient": res.coefficients, "t-stat": res.tstats})
    st.subheader("Factor loadings")
    st.dataframe(df.style.format({"coefficient": "{:.3f}", "t-stat": "{:.2f}"}),
                 use_container_width=True)
    st.caption("Mkt-RF = market excess; SMB = small-minus-big; HML = value; "
               "RMW = profitability; CMA = investment.")
