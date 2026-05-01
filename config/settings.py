# config/settings.py
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent

RAW_DIR    = ROOT_DIR / "data" / "raw"
CACHE_DIR  = ROOT_DIR / "data" / "cache"
OUTPUT_DIR = ROOT_DIR / "data" / "output"
EVENTS_DIR = ROOT_DIR / "data" / "events"

for d in [RAW_DIR, CACHE_DIR, OUTPUT_DIR, EVENTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

SENATE_API_URL   = None  # Set to a URL to enable live fetch
BENCHMARK_TICKER = "SPY"

DEFAULT_START_DATE = "2016-01-01"
DEFAULT_END_DATE   = "2020-12-31"
