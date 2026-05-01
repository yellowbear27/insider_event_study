# config/settings.py
from pathlib import Path
import os

# Project root
ROOT_DIR = Path(__file__).parent.parent

# Data paths
RAW_DIR = ROOT_DIR / "data" / "raw"
CACHE_DIR = ROOT_DIR / "data" / "cache"
OUTPUT_DIR = ROOT_DIR / "data" / "output"
EVENTS_DIR = ROOT_DIR / "data" / "events"

# Create dirs if missing
for d in [RAW_DIR, CACHE_DIR, OUTPUT_DIR, EVENTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# External sources
# Capitol Trades public API (free, no auth)
SENATE_API_URL = None  # Local-only mode for development
# Or for historical sample data, use a direct raw JSON link:
# SENATE_API_URL = None  # Local-only mode for development
BENCHMARK_TICKER = "SPY"

# Defaults
DEFAULT_START_DATE = "2016-01-01"
DEFAULT_END_DATE = "2020-12-31"
