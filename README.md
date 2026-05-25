# Stock Portfolio Monitoring App

A local Streamlit app for monitoring a stock portfolio: returns, risk, drawdowns, factor exposure, Monte Carlo projections, optimization, and a **what-if** tool that shows how adding a new stock would change your portfolio's metrics.

Built with: Streamlit + Plotly UI, **yfinance** for prices, SQLite for holdings/price cache, **PyPortfolioOpt** for optimization, **pandas-datareader** (Ken French library) for Fama–French factors.

Benchmark: `^GSPC` (S&P 500). Base currency: USD.

---

## Features

- **Portfolio** — add/edit holdings inline; live market value, P&L vs cost basis, weight allocation pie chart, CSV export.
- **Performance** — cumulative return chart vs benchmark, period returns table (1M / 3M / 6M / YTD / 1Y / 3Y / 5Y).
- **Risk** — annualized volatility, beta vs benchmark, correlation heatmap, Historical VaR/CVaR, return distribution.
- **Drawdown** — underwater chart, max drawdown, peak / trough / recovery dates, recovery duration.
- **Ratios** — Sharpe, Sortino, Calmar (using a live risk-free rate from `^IRX` or a user override).
- **Factor Exposure** — Fama–French 3- or 5-factor regression with annualized α, factor loadings, *t*-stats, R².
- **Monte Carlo** — parametric (multivariate normal) or bootstrap forward simulation; fan chart, terminal-value distribution, probability of loss.
- **What-If** — add a hypothetical ticker at any weight; side-by-side before/after metric comparison with deltas; option to **suggest** the weight that maximizes Sharpe or minimizes volatility (either tuning only the new position or re-optimizing the whole portfolio via PyPortfolioOpt).
- **Optimization** — max-Sharpe and min-vol portfolios; efficient frontier plot.

All settings (lookback window, VaR α, Monte Carlo sims/horizon, risk-free override, clear-cache) live in the sidebar.

## Run

### Windows (easy)

```
run.bat
```

`run.bat` resolves a Python environment in this order:

1. Existing local `.venv/` (reused if present).
2. Existing conda env named `stockmon` under `C:\Miniforge3\envs\` (reused if present).
3. `python` on PATH → creates `.venv/` and installs `requirements.txt` via pip.
4. Fallback: if pip is blocked by group policy and Miniforge is available, creates a conda env `stockmon` from conda-forge.

On any failure the cmd window stays open via `pause`.

### Manual (any OS)

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

The app opens at http://localhost:8501.

## Project layout

```
app.py                          Streamlit entry point
run.bat                         Windows launcher (auto venv / pip / conda fallback)
requirements.txt
.streamlit/config.toml          Disables telemetry banner

portfolio_app/
  config.py                     Paths and analytics defaults
  db.py                         SQLite: holdings, price cache, metadata
  data.py                       yfinance fetch with cache-first daily refresh
  portfolio.py                  Position math: value, weight, P&L, return series
  summary.py                    MetricBundle + summarize()
  whatif.py                     simulate_addition(), suggest_weight()
  metrics/
    returns.py                  total return, CAGR, TWR, annualized mean
    risk.py                     volatility, beta, correlation, VaR / CVaR
    drawdown.py                 drawdown series, max DD, recovery
    ratios.py                   Sharpe, Sortino, Calmar
    factors.py                  Fama-French 3/5-factor regression
    montecarlo.py               parametric + bootstrap simulation
    optimize.py                 PyPortfolioOpt: max Sharpe, min vol, frontier
  ui/
    common.py                   Cached loaders, sidebar, formatters

pages/                          Streamlit multi-page UI
  1_💼_Portfolio.py
  2_📈_Performance.py
  3_⚠️_Risk.py
  4_📉_Drawdown.py
  5_🧬_Factors.py
  6_🎲_Monte_Carlo.py
  7_🔮_What_If.py
  8_🧠_Optimization.py
```

## Data

- **Prices** come from `yfinance` (Yahoo Finance, no API key). They are cached in a local SQLite file (`data/portfolio.db`); subsequent runs within 24h reuse the cache.
- **Risk-free rate** uses the most recent `^IRX` (13-week T-bill yield) divided by 100; overridable in the sidebar.
- **Fama–French factors** are fetched from Ken French's data library via `pandas-datareader` on demand.

## Notes / out of scope (v1)

- USD only (no FX conversion).
- No options, derivatives, or lot-level tax accounting.
- No live intraday quotes or broker sync.
- No auth / multi-user (this is a single-user local app).
