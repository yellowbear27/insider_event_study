# events/event_builder.py
"""Enrich parsed events with derived fields: event_type, direction, cluster signals."""
import pandas as pd
import logging
from typing import Optional, List
from pathlib import Path

from config.settings import DEFAULT_START_DATE, DEFAULT_END_DATE

logger = logging.getLogger(__name__)

def enrich_events(events_df: pd.DataFrame, config_path: Optional[Path] = None) -> pd.DataFrame:
    if events_df.empty:
        logger.warning("No events to enrich")
        return events_df
    
    df = events_df.copy()
    required = ['ticker', 'event_date', 'transaction_type', 'shares_after']
    missing = [c for c in required if c not in df.columns]
    if missing:
        logger.error(f"Missing required columns: {missing}")
        return events_df
    
    df['event_type'] = df.apply(_classify_event_type, axis=1)
    df['direction'] = df['event_type'].map({
        'insider_buy': 'bullish', 'partial_insider_sale': 'bearish',
        'full_exit_sale': 'bearish', 'cluster_buy': 'bullish', 'unknown': 'neutral'
    })
    df = _add_cluster_signals(df, min_cluster_size=2, window_days=7)
    logger.info(f"✅ Enriched {len(df)} events")
    return df

def _classify_event_type(row: pd.Series) -> str:
    ttype = str(row.get('transaction_type', '')).strip().upper()
    shares_after = row.get('shares_after')
    if pd.isna(shares_after): shares_after = None
    if ttype in ['PURCHASE', 'BUY', 'P', 'ACQUISITION']: return 'insider_buy'
    elif ttype in ['SALE', 'SELL', 'S', 'DISPOSITION']:
        return 'full_exit_sale' if shares_after is not None and shares_after <= 0 else 'partial_insider_sale'
    return 'unknown'

def _add_cluster_signals(df: pd.DataFrame, min_cluster_size: int = 2, window_days: int = 7) -> pd.DataFrame:
    df = df.copy()
    df['event_date'] = pd.to_datetime(df['event_date'])
    df['cluster_flag'] = False
    df['cluster_size'] = 0
    buys = df[df['direction'] == 'bullish'].copy()
    if len(buys) < min_cluster_size: return df
    for idx, row in buys.iterrows():
        ticker, event_date = row['ticker'], row['event_date']
        window = pd.Timedelta(days=window_days)
        nearby = buys[(buys['ticker'] == ticker) & (buys['event_date'] >= event_date - window) & (buys['event_date'] <= event_date + window)]
        if len(nearby) >= min_cluster_size:
            df.at[idx, 'cluster_flag'] = True
            df.at[idx, 'cluster_size'] = len(nearby)
    df.loc[df['cluster_flag'], 'event_type'] = 'cluster_buy'
    return df

def filter_by_hypothesis(events_df: pd.DataFrame, hypothesis: dict) -> pd.DataFrame:
    """Filter events to match a specific hypothesis config.
    
    BEST PRACTICE: Filter by signal characteristics ONLY.
    expected_direction is for EVALUATION, not filtering.
    """
    df = events_df.copy()
    
    # Filter by event_type ONLY (signal detection)
    if 'event_type' in hypothesis:
        df = df[df['event_type'] == hypothesis['event_type']]
    
    # ⚠️ DO NOT filter by expected_direction here
    # That belongs in the evaluation/reporting phase (_make_decision)
    
    # Warn if sample too small
    min_n = hypothesis.get('min_sample_size', 1)
    if len(df) < min_n:
        logger.warning(f"Sample size {len(df)} < min {min_n} for hypothesis.")
    
    logger.info(f"✅ Filtered to {len(df)} events matching hypothesis")
    return df
