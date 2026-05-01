# events/insider_parser.py
"""Parse raw Senate trade JSON into standard event schema."""
import pandas as pd
import logging
from typing import List, Dict, Any, Optional

from config.settings import DEFAULT_START_DATE, DEFAULT_END_DATE, EVENTS_DIR

logger = logging.getLogger(__name__)

SCHEMA = ['ticker', 'event_date', 'filing_date', 'transaction_type',
          'shares_before', 'shares_after', 'event_type', 'direction', 'source']

COLUMN_MAP = {
    'symbol': 'ticker', 'stock_symbol': 'ticker', 'ticker_symbol': 'ticker',
    'transaction_date': 'event_date', 'date': 'event_date',
    'type': 'transaction_type', 'shares': 'shares_after', 'amount': 'shares_after',
}


def classify_event_type(transaction_type: str, shares_after) -> str:
    ttype = str(transaction_type).strip().upper()
    if ttype in ['PURCHASE', 'BUY', 'P', 'ACQUISITION']:
        return 'insider_buy'
    if ttype in ['SALE', 'SELL', 'S', 'DISPOSITION']:
        if shares_after is not None and not pd.isna(shares_after) and shares_after <= 0:
            return 'full_exit_sale'
        return 'partial_insider_sale'
    return 'unknown'


DIRECTION_MAP = {
    'insider_buy': 'bullish',
    'partial_insider_sale': 'bearish',
    'full_exit_sale': 'bearish',
    'cluster_buy': 'bullish',
    'unknown': 'neutral',
}


def parse_raw_trades(
    raw_data: List[Dict[str, Any]],
    target_tickers: Optional[List[str]] = None,
    start_date: str = DEFAULT_START_DATE,
    end_date: str = DEFAULT_END_DATE
) -> pd.DataFrame:
    if not raw_data:
        logger.warning("No raw data to parse")
        return pd.DataFrame(columns=SCHEMA)

    df = pd.DataFrame(raw_data)
    df = df.rename(columns={k: v for k, v in COLUMN_MAP.items() if k in df.columns})

    for col in ['ticker', 'event_date', 'filing_date', 'transaction_type']:
        if col not in df.columns:
            df[col] = None

    if target_tickers:
        df = df[df['ticker'].isin(target_tickers)].copy()
        logger.info(f"Filtered to {len(df)} records for tickers: {target_tickers}")

    df['filing_date'] = pd.to_datetime(df['filing_date'], errors='coerce')
    df['event_date'] = pd.to_datetime(df.get('event_date', df['filing_date']), errors='coerce')
    df = df[(df['filing_date'] >= start_date) & (df['filing_date'] <= end_date)].copy()

    df['transaction_type'] = df['transaction_type'].astype(str).str.strip().str.title()
    if 'shares_before' not in df.columns:
        df['shares_before'] = None

    df['event_type'] = df.apply(
        lambda r: classify_event_type(r['transaction_type'], r.get('shares_after')), axis=1
    )
    df['direction'] = df['event_type'].map(DIRECTION_MAP)
    df['source'] = 'senate_disclosure'

    df = df[SCHEMA].drop_duplicates(subset=['ticker', 'event_date', 'transaction_type'])
    logger.info(f"✅ Parsed {len(df)} events with standard schema")
    return df


def save_events(df: pd.DataFrame, filename: str = "events.csv") -> str:
    output_path = EVENTS_DIR / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info(f"💾 Saved {len(df)} events to: {output_path}")
    return str(output_path)
