"""Portfolio page: holdings editor + summary."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from portfolio_app import db
from portfolio_app.ui.common import (
    get_portfolio_context,
    init_session_state,
    invalidate_holdings_cache,
    num,
    pct,
    sidebar_controls,
)

st.set_page_config(page_title="Portfolio", page_icon="💼", layout="wide")
init_session_state()
sidebar_controls()

st.title("💼 Portfolio")

holdings = db.list_holdings()
if holdings.empty:
    st.info("No holdings yet. Add some below.")
    editor_df = pd.DataFrame(
        [{"ticker": "", "shares": 0.0, "cost_basis": 0.0}]
    )
else:
    editor_df = holdings[["ticker", "shares", "cost_basis"]].copy()

st.subheader("Edit holdings")
edited = st.data_editor(
    editor_df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "ticker": st.column_config.TextColumn("Ticker", required=True),
        "shares": st.column_config.NumberColumn("Shares", min_value=0.0, step=1.0),
        "cost_basis": st.column_config.NumberColumn("Cost basis (per share)",
                                                    min_value=0.0, step=0.01),
    },
    key="holdings_editor",
)

col_save, col_clear = st.columns([1, 1])
if col_save.button("💾 Save holdings", type="primary"):
    rows = edited.to_dict(orient="records")
    db.replace_holdings(rows)
    invalidate_holdings_cache()
    st.success("Saved.")
    st.rerun()
if col_clear.button("🗑 Clear all"):
    with db.connect() as c:
        c.execute("DELETE FROM holdings")
    invalidate_holdings_cache()
    st.rerun()

st.divider()

# --- summary ---
holdings, prices, _, _, _, valued = get_portfolio_context()
if holdings.empty or prices.empty:
    st.stop()

st.subheader("Summary")
total_mv = float(valued["market_value"].sum())
total_cost = float(valued["cost_value"].sum())
total_pnl = total_mv - total_cost
total_pnl_pct = (total_pnl / total_cost) if total_cost > 0 else 0.0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Market value", f"${num(total_mv)}")
c2.metric("Cost basis", f"${num(total_cost)}")
c3.metric("P&L", f"${num(total_pnl)}", pct(total_pnl_pct))
c4.metric("# positions", len(valued))

st.subheader("Positions")
show = valued[["ticker", "shares", "cost_basis", "price", "market_value",
               "cost_value", "pnl", "pnl_pct", "weight"]].copy()
show = show.rename(columns={
    "cost_basis": "cost/share", "price": "last price",
    "market_value": "market value", "cost_value": "cost value",
    "pnl_pct": "P&L %",
})
st.dataframe(
    show.style.format({
        "shares": "{:,.4f}",
        "cost/share": "${:,.2f}",
        "last price": "${:,.2f}",
        "market value": "${:,.2f}",
        "cost value": "${:,.2f}",
        "pnl": "${:,.2f}",
        "P&L %": "{:.2%}",
        "weight": "{:.2%}",
    }),
    use_container_width=True,
)

st.subheader("Allocation")
fig = px.pie(valued, names="ticker", values="market_value", hole=0.4)
st.plotly_chart(fig, use_container_width=True)

csv = show.to_csv(index=False).encode("utf-8")
st.download_button("Download holdings as CSV", csv, "holdings.csv", "text/csv")
