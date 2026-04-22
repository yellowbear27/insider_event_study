# event_study.py
# Responsibility: merge trade events with price data, calculate abnormal returns.
# This is the core analysis file. Everything else feeds into this.
# Output: DataFrame with abnormal returns per trade event.

import pandas as pd
import numpy as np

from price_fetcher import fetch_prices
from config import OUTPUT_CSV_FILE


def load_trades(filepath: str) -> pd.DataFrame:
    # Load the saved senate trades CSV into a DataFrame.
    # Parse transaction_date as an actual date object, not a string.
    # This allows date arithmetic later — adding 30 days, comparing dates etc.
    df = pd.read_csv(filepath, parse_dates=["transaction_date"])
    print(f"Loaded {len(df)} trade events from {filepath}")
    return df

def get_price_window(prices: pd.DataFrame, ticker: str, 
                     event_date: pd.Timestamp, window: int = 30) -> pd.DataFrame:
    # Extract prices for one ticker around one event date.
    # window = number of trading days after event date to include.
    
    # Filter to just this ticker's close prices
    ticker_prices = prices[ticker]["Close"]
    
    # Find prices from event date onwards
    mask = ticker_prices.index >= event_date
    window_prices = ticker_prices[mask].head(window + 1)
    
    return window_prices

def calculate_abnormal_returns(trade_prices: pd.DataFrame, 
                                spy_prices: pd.DataFrame) -> pd.Series:
    # Calculate abnormal return = stock return minus SPY return
    # for each day in the event window.
    
    # Percentage change day over day
    stock_returns = trade_prices.pct_change().dropna()
    spy_returns = spy_prices.pct_change().dropna()
    
    # Align by date — only keep dates that exist in both
    stock_returns, spy_returns = stock_returns.align(spy_returns, join="inner")
    
    # Abnormal return = what the stock did minus what the market did
    abnormal_returns = stock_returns - spy_returns
    
    return abnormal_returns


def main():
    # Step 1: Load trade events
    trades = load_trades(OUTPUT_CSV_FILE)
    
    # Step 2: Get date range from trades for price fetching
    start = trades["transaction_date"].min() - pd.Timedelta(days=5)
    end = trades["transaction_date"].max() + pd.Timedelta(days=45)
    
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    # Step 3: Fetch stock prices for our three tickers
    prices = fetch_prices(
        start_date=start_str,
        end_date=end_str
    )

    # Step 4: Fetch SPY separately as benchmark
    spy_prices = fetch_prices(
        start_date=start_str,
        end_date=end_str,
        tickers=["SPY"]
    )
    
    # Step 5: Loop through each trade event
    results = []
    
    for _, row in trades.iterrows():
        ticker = row["ticker"]
        event_date = row["transaction_date"]
        
        try:
            # Get price window for this trade
            trade_prices = get_price_window(prices, ticker, event_date)
            spy_window = get_price_window(spy_prices, "SPY", event_date)
            
            # Calculate abnormal returns
            ar = calculate_abnormal_returns(trade_prices, spy_window)
            
            # Cumulative abnormal return over window
            car = ar.sum()
            
            results.append({
                "senator": row["senator"],
                "ticker": ticker,
                "event_date": event_date,
                "type": row["type"],
                "amount": row["amount"],
                "CAR_30day": round(car * 100, 2)
            })
            
        except Exception as e:
            print(f"Skipped {ticker} on {event_date}: {e}")
            continue
    
    # Step 6: Results DataFrame
    results_df = pd.DataFrame(results)
    
    print("\n--- Event Study Results ---")
    print(results_df.to_string())
    
    # Step 7: Summary by trade type
    print("\n--- Average CAR by Trade Type ---")
    print(results_df.groupby("type")["CAR_30day"].mean())


if __name__ == "__main__":
    main()
