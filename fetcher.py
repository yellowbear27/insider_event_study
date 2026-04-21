# fetcher.py
# Responsibility: fetch raw trade data from Senate Stock Watcher API.
# Returns: raw JSON as a Python dictionary.
# Does NOT parse or filter. That is parser.py's job.

import requests
import time

from config import SENATE_API_URL, HEADERS, REQUEST_DELAY_SECONDS


def fetch_senate_trades() -> dict:

    print(f"Fetching from: {SENATE_API_URL}")

    response = requests.get(SENATE_API_URL, headers=HEADERS)
    response.raise_for_status()

    time.sleep(REQUEST_DELAY_SECONDS)

    data = response.json()

    print(f"Fetch successful. Records received: {len(data)}")

    return data
