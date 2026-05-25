"""Application-wide configuration and defaults."""
from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "portfolio.db"

# Market defaults
BENCHMARK_TICKER = "^GSPC"
RISK_FREE_TICKER = "^IRX"  # 13-week T-bill, quoted in % annualized

# Analytics defaults
DEFAULT_LOOKBACK_YEARS = 5
TRADING_DAYS = 252
DEFAULT_VAR_ALPHA = 0.05
DEFAULT_MC_SIMS = 5000
DEFAULT_MC_HORIZON_DAYS = 252

# Cache freshness window (hours) before re-fetching
CACHE_REFRESH_HOURS = 24
