# price_fetcher.py
# Responsibility: fetch historical price data for target tickers.
# Uses yfinance. Returns a DataFrame of daily closing prices.
# Does NOT load trade data. Does NOT calculate returns. Only fetches prices.

import yfinance as yf
import pandas as pd

from config import TICKERS


def fetch_prices(start_date: str, end_date: str, tickers: list = None) -> pd.DataFrame:

    if tickers is None:
        tickers = TICKERS

    print(f"Fetching price data for: {tickers}")

    df = yf.download(
        tickers=tickers,
        start=start_date,
        end=end_date,
        group_by="ticker",
        auto_adjust=True
    )

    print(f"Price data fetched. Shape: {df.shape}")

    return df


if __name__ == "__main__":
    prices = fetch_prices("2016-01-01", "2020-12-31")
    print(prices.tail())
