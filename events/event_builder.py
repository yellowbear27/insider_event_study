# events/event_builder.py
"""Enrich parsed events with derived fields and cluster signals."""
import pandas as pd
import logging
from typing import Optional

from events.insider_parser import classify_event_type, DIRECTION_MAP

logger = logging.getLogger(__name__)


def enrich_events(events_df: pd.DataFrame) -> pd.DataFrame:
    if events_df.empty:
        logger.warning("No events to enrich")
        return events_df

    df = events_df.copy()
    required = ['ticker', 'event_date', 'transaction_type', 'shares_after']
    missing = [c for c in required if c not in df.columns]
    if missing:
        logger.error(f"Missing required columns: {missing}")
        return events_df

    df['event_type'] = df.apply(
        lambda r: classify_event_type(r['transaction_type'], r.get('shares_after')), axis=1
    )
    df['direction'] = df['event_type'].map(DIRECTION_MAP)
    df = _add_cluster_signals(df)
    logger.info(f"✅ Enriched {len(df)} events")
    return df


def _add_cluster_signals(df: pd.DataFrame, min_cluster_size: int = 2, window_days: int = 7) -> pd.DataFrame:
    df = df.copy()
    df['event_date'] = pd.to_datetime(df['event_date'])
    df['cluster_flag'] = False
    df['cluster_size'] = 0

    buys = df[df['direction'] == 'bullish'].copy()
    if len(buys) < min_cluster_size:
        return df

    window = pd.Timedelta(days=window_days)
    for idx, row in buys.iterrows():
        nearby = buys[
            (buys['ticker'] == row['ticker']) &
            (buys['event_date'] >= row['event_date'] - window) &
            (buys['event_date'] <= row['event_date'] + window)
        ]
        if len(nearby) >= min_cluster_size:
            df.at[idx, 'cluster_flag'] = True
            df.at[idx, 'cluster_size'] = len(nearby)

    df.loc[df['cluster_flag'], 'event_type'] = 'cluster_buy'
    return df


def filter_by_hypothesis(events_df: pd.DataFrame, hypothesis: dict) -> pd.DataFrame:
    df = events_df.copy()
    if 'event_type' in hypothesis:
        df = df[df['event_type'] == hypothesis['event_type']]
    min_n = hypothesis.get('min_sample_size', 1)
    if len(df) < min_n:
        logger.warning(f"Sample size {len(df)} < minimum {min_n}")
    logger.info(f"✅ Filtered to {len(df)} events matching hypothesis")
    return df
