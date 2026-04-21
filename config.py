# config.py
# Central configuration. All URLs, constants, and parameters live here.
# Import this file in any module that needs these values.

# --- DATA SOURCES ---

# Senate Stock Watcher API: pre-parsed JSON, free, no auth required.
# Replaces direct Senate EFD portal scraping (efdsearch.senate.gov)
# which is JS-rendered and not parseable with BeautifulSoup.
SENATE_API_URL = "https://raw.githubusercontent.com/timothycarambat/senate-stock-watcher-data/master/aggregate/all_transactions.json"
# senatestockwatcher.com is dead as of 2026.
# Using the underlying GitHub data repository directly instead.
# Same data, more reliable source.
# Original Senate EFD URL — abandoned. JS-rendered. Kept for reference.
# BASE_URL = "https://efdsearch.senate.gov/search/"

# --- REQUEST SETTINGS ---

# Polite delay between requests. Avoids hammering the server.
REQUEST_DELAY_SECONDS = 1

# Browser-like header. Some servers reject requests without a User-Agent.
HEADERS = {
    "User-Agent": "insider-event-study/0.1"
}

# --- STOCK UNIVERSE ---

# Three AI infrastructure bellwethers. See RESEARCHLOG.md for rationale.
TICKERS = ["NVDA", "CDNS", "SNPS"]

# --- FILE PATHS ---

RAW_DATA_DIR = "data/raw"
OUTPUT_DATA_DIR = "data/output"   # Fixed typo from OUTOUT_DATA_DIR
OUTPUT_CSV_FILE = "data/output/senate_trades.csv"
