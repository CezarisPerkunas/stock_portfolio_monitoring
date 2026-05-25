"""What-If page: simulate adding a new stock."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from portfolio_app import data as data_mod
from portfolio_app.config import DEFAULT_LOOKBACK_YEARS
from portfolio_app.ui.common import (
    get_portfolio_context,
    init_session_state,
    num,
    pct,
    sidebar_controls,
)
from portfolio_app.whatif import simulate_addition, suggest_weight

st.set_page_config(page_title="What-If", page_icon="🔮", layout="wide")
init_session_state()
sidebar_controls()

st.title("🔮 What-If: Add a stock")

holdings, prices, bench_returns, rf, _, valued = get_portfolio_context()
if holdings.empty or prices.empty:
    st.info("Add holdings first.")
    st.stop()

col1, col2 = st.columns([1, 1])
new_ticker = col1.text_input("New ticker", value="").upper().strip()
new_weight = col2.slider("Weight for new ticker", 0.0, 0.5, 0.10, 0.01,
                         help="Fraction of portfolio reallocated to the new ticker; "
                              "existing positions are scaled down proportionally.")

scope = st.radio("Optimization scope",
                 ["new_only", "full"], horizontal=True,
                 format_func=lambda s: "Hold existing weights fixed" if s == "new_only"
                                       else "Re-optimize all weights",
                 help="`new_only` keeps your current relative weights and tunes only the new "
                      "position. `full` re-optimizes everything.")
objective = st.radio("Objective for 'Suggest weight'", ["max_sharpe", "min_vol"], horizontal=True)

compute = st.button("Compute", type="primary")
suggest = st.button("Suggest optimal weight")

if not (compute or suggest):
    st.stop()

if not new_ticker:
    st.warning("Enter a ticker.")
    st.stop()

# Fetch prices for the new ticker (cached)
lookback = int(st.session_state.get("lookback_years", DEFAULT_LOOKBACK_YEARS))
start, end = data_mod.default_date_range(lookback)
try:
    new_series = data_mod.get_price_series(new_ticker, start, end)
except Exception as e:
    st.error(f"Failed to fetch {new_ticker}: {e}")
    st.stop()
if new_series.empty:
    st.error(f"No data for {new_ticker}.")
    st.stop()

# Build combined price frame
if new_ticker in prices.columns:
    combined = prices
else:
    combined = pd.concat([prices, new_series], axis=1)

current_weights = valued.set_index("ticker")["weight"]

if suggest:
    try:
        with st.spinner("Optimizing..."):
            sug = suggest_weight(current_weights, combined, new_ticker,
                                 objective=objective, rf_annual=rf, scope=scope)
    except Exception as e:
        st.error(f"Optimization failed: {e}")
        st.stop()
    st.success(f"Suggested weight for **{new_ticker}**: **{pct(sug['new_weight'])}**")
    c1, c2, c3 = st.columns(3)
    c1.metric("Expected return (ann.)", pct(sug["expected_return"]))
    c2.metric("Volatility (ann.)", pct(sug["volatility"]))
    c3.metric("Sharpe", f"{sug['sharpe']:.3f}")
    st.subheader("Suggested weights")
    st.dataframe(sug["weights"].rename("weight").to_frame()
                 .style.format({"weight": "{:.2%}"}), use_container_width=True)
    # Use the suggested weight for the comparison below
    new_weight = float(sug["new_weight"])

with st.spinner("Computing..."):
    res = simulate_addition(current_weights, combined, new_ticker, new_weight,
                            benchmark_returns=bench_returns, rf_annual=rf)

st.subheader("Before vs After")
fmt = {
    "total_return": pct, "cagr": pct, "volatility": pct,
    "sharpe": lambda v: f"{v:.3f}", "sortino": lambda v: f"{v:.3f}",
    "calmar": lambda v: f"{v:.3f}",
    "max_drawdown": pct, "var_95": pct, "cvar_95": pct,
    "beta": lambda v: f"{v:.3f}" if pd.notna(v) else "—",
}
rows = []
cur_d = res.current.as_dict()
hyp_d = res.hypothetical.as_dict()
for k in cur_d:
    rows.append({
        "Metric": k,
        "Current": fmt[k](cur_d[k]),
        "Hypothetical": fmt[k](hyp_d[k]),
        "Δ": fmt[k](res.deltas[k]) if res.deltas[k] is not None else "—",
    })
st.dataframe(pd.DataFrame(rows).set_index("Metric"), use_container_width=True)

st.subheader("New weights")
st.dataframe(
    res.new_weights.rename("weight").to_frame().style.format({"weight": "{:.2%}"}),
    use_container_width=True,
)
