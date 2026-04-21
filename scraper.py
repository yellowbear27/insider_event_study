# fetcher.py
# Responsibility: fetch raw trade data from Senate Stock Watcher API.
# Returns: raw JSON as a Python dictionary.
# Does NOT parse or filter. That is parser.py's job.
# One responsibility per file. This one fetches. Nothing else.

import requests  # third-party library for making HTTP requests
import time      # built-in Python library for adding delays

from config import SENATE_API_URL, HEADERS, REQUEST_DELAY_SECONDS


def fetch_senate_trades() -> dict:
    """
    Fetch all Senate trade disclosures from Stock Watcher API.
    Returns raw JSON as a Python dictionary.
    Raises an exception if the request fails.
    """

    print(f"Fetching Senate trades from: {SENATE_API_URL}")

    # requests.get() sends an HTTP GET request to the URL.
    # headers= tells the server who we are.
    response = requests.get(SENATE_API_URL, headers=HEADERS)

    # raise_for_status() checks if the request succeeded.
    # If the server returns an error (404, 500 etc), this raises an exception.
    # Better to fail loudly than silently continue with bad data.
    response.raise_for_status()

    # Polite delay after the request.
    time.sleep(REQUEST_DELAY_SECONDS)

    # .json() converts the raw response text into a Python dictionary.
    # This only works if the server actually returned valid JSON.
    data = response.json()

    print(f"Fetch successful. Records received: {len(data)}")

    return data

