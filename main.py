# main.py
# Entry point. Run this file to execute the full pipeline.
# Usage: python main.py
# Pipeline: fetch → parse → display
# Storage to CSV is in storage.py (next step).

from fetcher import fetch_senate_trades
from parser import parse_senate_trades


def main():
    # Step 1: Fetch raw data from Senate Stock Watcher API
    raw_data = fetch_senate_trades()

    # Step 2: Parse and filter to target tickers
    df = parse_senate_trades(raw_data)

    if df.empty:
        print("No trades found for target tickers.")
        return

    # Step 3: Display results in terminal
    print("\n--- Senate Trades: NVDA / CDNS / SNPS ---")
    print(df.to_string())   # to_string() prints the full table without truncation

    print(f"\nTotal trades found: {len(df)}")
    print(f"Tickers represented: {df['ticker'].unique()}")


# This block runs only when you execute main.py directly.
# It does NOT run if another file imports main.py.
# Standard Python pattern — always include this.
if __name__ == "__main__":
    main()
