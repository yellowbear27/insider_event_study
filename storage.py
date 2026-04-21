# storage.py
# Responsibility: save cleaned DataFrame to CSV.
# Does NOT fetch. Does NOT parse. Only saves.

import os
import pandas as pd

from config import OUTPUT_DATA_DIR, OUTPUT_CSV_FILE


def save_to_csv(df: pd.DataFrame) -> None:

    # Create output directory if it does not exist.
    # exist_ok=True means no error if folder already exists.
    os.makedirs(OUTPUT_DATA_DIR, exist_ok=True)

    # to_csv() saves the DataFrame as a CSV file.
    # index=False means do not write row numbers as a column.
    df.to_csv(OUTPUT_CSV_FILE, index=False)

    print(f"Saved {len(df)} records to {OUTPUT_CSV_FILE}")
