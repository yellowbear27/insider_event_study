# price_fetcher.py
# Responsibility: fetch historical price data for target tickers.
# Uses yfinance. Returns a DataFrame of daily closing prices.
# Does NOT load trade data. Does NOT calculate returns. Only fetches prices.

import yfinance as yf
import pandas as pd

from config import TICKERS


def fetch_prices(start_date: str, end_date: str) -> pd.DataFrame:

    print(f"Fetching price data for: {TICKERS}")

    # yf.download() fetches historical OHLCV data from Yahoo Finance.
    # group_by="ticker" organises columns by ticker symbol.
    # auto_adjust=True adjusts for splits and dividends automatically.
    df = yf.download(
        tickers=TICKERS,
        start=start_date,
        end=end_date,
        group_by="ticker",
        auto_adjust=True
    )

    print(f"Price data fetched. Shape: {df.shape}")

    return df


if __name__ == "__main__":
    # Quick test: fetch prices covering our trade data period
    prices = fetch_prices("2016-01-01", "2020-12-31")
    print(prices.tail())
