# events/event_builder.py
"""Enrich parsed events with derived fields and cluster signals.

This module may create additional factual flags such as cluster_flag and
cluster_size. It does NOT decide whether an event is bullish or bearish.
"""

import logging
from typing import Optional

import pandas as pd

from events.congress_parser import classify_event_type

logger = logging.getLogger(__name__)


def enrich_events(events_df: pd.DataFrame) -> pd.DataFrame:
    """Add derived event fields without assigning investment direction."""
    if events_df.empty:
        logger.warning("No events to enrich")
        return events_df

    df = events_df.copy()

    required = ["ticker", "event_date", "transaction_type", "shares_after"]
    missing = [col for col in required if col not in df.columns]

    if missing:
        logger.error("Missing required columns: %s", missing)
        return events_df

    df["event_type"] = df.apply(
        lambda row: classify_event_type(
            row["transaction_type"],
            row.get("shares_after"),
        ),
        axis=1,
    )

    # Direction belongs in the hypothesis layer, not the event builder.
    if "direction" not in df.columns:
        df["direction"] = None
    else:
        df["direction"] = None

    df = _add_cluster_signals(df)

    logger.info("Enriched %s events", len(df))
    return df


def _add_cluster_signals(
    df: pd.DataFrame,
    min_cluster_size: int = 2,
    window_days: int = 7,
) -> pd.DataFrame:
    """Add cluster flags based on factual purchase events.

    A cluster is currently defined as at least `min_cluster_size` purchase events
    for the same ticker within +/- `window_days`.

    This does not label the cluster as bullish. It only marks that a purchase
    cluster occurred.
    """
    df = df.copy()

    df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
    df["cluster_flag"] = False
    df["cluster_size"] = 0

    purchases = df[df["event_type"] == "purchase"].copy()

    if len(purchases) < min_cluster_size:
        return df

    window = pd.Timedelta(days=window_days)

    for idx, row in purchases.iterrows():
        nearby = purchases[
            (purchases["ticker"] == row["ticker"])
            & (purchases["event_date"] >= row["event_date"] - window)
            & (purchases["event_date"] <= row["event_date"] + window)
        ]

        if len(nearby) >= min_cluster_size:
            df.at[idx, "cluster_flag"] = True
            df.at[idx, "cluster_size"] = len(nearby)

    return df


def filter_by_hypothesis(events_df: pd.DataFrame, hypothesis: dict) -> pd.DataFrame:
    """Filter events according to hypothesis config."""
    df = events_df.copy()

    if "event_type" in hypothesis:
        df = df[df["event_type"] == hypothesis["event_type"]]

    if hypothesis.get("cluster_required", False):
        df = df[df.get("cluster_flag", False) == True]

    min_n = hypothesis.get("min_sample_size", 1)

    if len(df) < min_n:
        logger.warning("Sample size %s < minimum %s", len(df), min_n)

    logger.info("Filtered to %s events matching hypothesis", len(df))
    return df
