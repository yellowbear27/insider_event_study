# parser.py
# Responsibility: convert raw Senate API JSON into a clean pandas DataFrame.
# Filters to target tickers only. Selects relevant columns.
# Does NOT fetch data. Does NOT save data. Only transforms.

import pandas as pd   # pandas: the standard Python library for data tables

from config import TICKERS


def parse_senate_trades(raw_data: dict) -> pd.DataFrame:
    """
    Convert raw Senate Stock Watcher JSON into a clean DataFrame.
    Filters rows to target tickers only (NVDA, CDNS, SNPS).
    Returns a pandas DataFrame with standardised columns.
    """

    # aggregate/all_transactions.json is a flat list, not a dict
    # So raw_data IS the list directly
    transactions = raw_data if isinstance(raw_data, list) else raw_data.get("data", [])

    # pd.DataFrame() converts a list of dictionaries into a table.
    # Each dictionary becomes one row. Each key becomes a column.
    df = pd.DataFrame(transactions)

    if df.empty:
        print("Warning: No data returned from API.")
        return df

    print(f"Total records before filtering: {len(df)}")

    # .str.upper() converts ticker column to uppercase.
    # .isin(TICKERS) keeps only rows where ticker is in our list.
    # The tickers list comes from config.py — ["NVDA", "CDNS", "SNPS"]
    df = df[df["ticker"].str.upper().isin(TICKERS)]

    print(f"Records after ticker filter: {len(df)}")

    # Select only the columns we care about.
    # Other columns exist in the raw data but are not needed yet.
    columns_to_keep = [
        "transaction_date",   # date of the actual trade
        "disclosure_date",    # date senator disclosed it — this is our T(0)
        "ticker",             # stock symbol
        "asset_description",  # company name
        "type",               # Purchase, Sale, Exchange
        "amount",             # dollar range e.g. "$1,001 - $15,000"
        "senator",            # senator's name
        "owner",              # Senator, Spouse, Joint
    ]

    # Only keep columns that actually exist in the data.
    # Protects against API changes breaking the code.
    existing_columns = [c for c in columns_to_keep if c in df.columns]
    df = df[existing_columns]

    # Reset the index so rows are numbered 0, 1, 2...
    # drop=True discards the old index rather than adding it as a column.
    df = df.reset_index(drop=True)

    return df


