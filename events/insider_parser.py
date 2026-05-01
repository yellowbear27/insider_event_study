# events/insider_parser.py
"""Parse raw Senate trade JSON into standard event schema."""
import pandas as pd
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from config.settings import DEFAULT_START_DATE, DEFAULT_END_DATE, EVENTS_DIR

logger = logging.getLogger(__name__)

def _get_standard_schema() -> List[str]:
    return ['ticker', 'event_date', 'filing_date', 'transaction_type',
            'shares_before', 'shares_after', 'event_type', 'direction', 'source']

def parse_raw_trades(
    raw_data: List[Dict[str, Any]],
    target_tickers: Optional[List[str]] = None,
    start_date: str = DEFAULT_START_DATE,
    end_date: str = DEFAULT_END_DATE
) -> pd.DataFrame:
    if not raw_data:
        logger.warning("No raw data to parse")
        return pd.DataFrame(columns=_get_standard_schema())
    
    df = pd.DataFrame(raw_data)
    df = _standardize_columns(df)
    
    if target_tickers:
        df = df[df['ticker'].isin(target_tickers)].copy()
        logger.info(f"Filtered to {len(df)} records for tickers: {target_tickers}")
    
    df['filing_date'] = pd.to_datetime(df['filing_date'], errors='coerce')
    df = df[(df['filing_date'] >= start_date) & (df['filing_date'] <= end_date)].copy()
    df = _derive_event_fields(df)
    
    df = df[_get_standard_schema()].copy()
    df = df.drop_duplicates(subset=['ticker', 'event_date', 'transaction_type'])
    
    logger.info(f"✅ Parsed {len(df)} events with standard schema")
    return df

def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    column_mapping = {
        'symbol': 'ticker', 'stock_symbol': 'ticker', 'ticker_symbol': 'ticker',
        'transaction_date': 'event_date', 'date': 'event_date',
        'type': 'transaction_type', 'shares': 'shares_after', 'amount': 'shares_after',
    }
    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
    for col in ['ticker', 'event_date', 'filing_date', 'transaction_type']:
        if col not in df.columns:
            df[col] = None
    return df

def _derive_event_fields(df: pd.DataFrame) -> pd.DataFrame:
    df['transaction_type'] = df['transaction_type'].astype(str).str.strip().str.title()
    if 'shares_before' not in df.columns:
        df['shares_before'] = None
    
    def classify_event(row):
        ttype = str(row.get('transaction_type', '')).upper()
        shares_after = row.get('shares_after')
        if pd.isna(shares_after): shares_after = None
        if ttype in ['PURCHASE', 'BUY', 'P']:
            return 'insider_buy'
        elif ttype in ['SALE', 'SELL', 'S']:
            return 'full_exit_sale' if shares_after is not None and shares_after <= 0 else 'partial_insider_sale'
        return 'unknown'
    
    df['event_type'] = df.apply(classify_event, axis=1)
    df['direction'] = df['event_type'].map({
        'insider_buy': 'bullish', 'partial_insider_sale': 'bearish',
        'full_exit_sale': 'bearish', 'unknown': 'neutral'
    })
    df['source'] = 'senate_disclosure'
    return df

def save_events(df: pd.DataFrame, filename: str = "events.csv") -> str:
    output_path = EVENTS_DIR / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info(f"💾 Saved {len(df)} events to: {output_path}")
    return str(output_path)
