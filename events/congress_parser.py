# events/congress_parser.py
"""Parse raw congressional trade JSON into a standard event schema.

This parser identifies what happened. It does NOT decide whether an event is
bullish or bearish. Direction belongs in the hypothesis layer.
"""

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from config.settings import DEFAULT_END_DATE, DEFAULT_START_DATE, EVENTS_DIR

logger = logging.getLogger(__name__)

SCHEMA = [
    "ticker",
    "event_date",
    "filing_date",
    "transaction_type",
    "shares_before",
    "shares_after",
    "event_type",
    "direction",
    "source",
]

COLUMN_MAP = {
    "symbol": "ticker",
    "stock_symbol": "ticker",
    "ticker_symbol": "ticker",
    "transaction_date": "event_date",
    "date": "event_date",
    "type": "transaction_type",
    "shares": "shares_after",
    "amount": "shares_after",
}


def classify_event_type(transaction_type: str, shares_after: Any) -> str:
    """Classify the raw transaction into a factual event type."""
    ttype = str(transaction_type).strip().upper()

    if ttype in ["PURCHASE", "BUY", "P", "ACQUISITION"]:
        return "purchase"

    if ttype in ["SALE", "SELL", "S", "DISPOSITION"]:
        if shares_after is not None and not pd.isna(shares_after):
            try:
                if float(shares_after) <= 0:
                    return "full_exit_sale"
            except (TypeError, ValueError):
                pass
        return "partial_sale"

    return "unknown"


def parse_raw_trades(
    raw_data: List[Dict[str, Any]],
    target_tickers: Optional[List[str]] = None,
    start_date: str = DEFAULT_START_DATE,
    end_date: str = DEFAULT_END_DATE,
) -> pd.DataFrame:
    """Convert raw congressional trade records into the standard event schema."""
    if not raw_data:
        logger.warning("No raw data to parse")
        return pd.DataFrame(columns=SCHEMA)

    df = pd.DataFrame(raw_data)
    df = df.rename(columns={k: v for k, v in COLUMN_MAP.items() if k in df.columns})

    for col in ["ticker", "event_date", "filing_date", "transaction_type"]:
        if col not in df.columns:
            df[col] = None

    if "shares_before" not in df.columns:
        df["shares_before"] = None
    if "shares_after" not in df.columns:
        df["shares_after"] = None

    if target_tickers:
        target_tickers = [ticker.upper() for ticker in target_tickers]
        df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
        df = df[df["ticker"].isin(target_tickers)].copy()
        logger.info("Filtered to %s records for tickers: %s", len(df), target_tickers)

    df["filing_date"] = pd.to_datetime(df["filing_date"], errors="coerce")
    df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")

    # Important:
    # For valid backtesting, event_date should eventually be the public disclosure
    # date. For now, we preserve existing event_date behavior but keep filing_date
    # explicit so the next cleanup step can enforce disclosure-date logic.
    df = df[(df["filing_date"] >= start_date) & (df["filing_date"] <= end_date)].copy()

    df["transaction_type"] = df["transaction_type"].astype(str).str.strip().str.title()

    df["event_type"] = df.apply(
        lambda row: classify_event_type(
            row["transaction_type"],
            row.get("shares_after"),
        ),
        axis=1,
    )

    # Direction is intentionally not decided here.
    # Hypotheses decide whether purchase / partial_sale / full_exit_sale is bullish or bearish.
    df["direction"] = None
    df["source"] = "congressional_disclosure"

    df = df[SCHEMA].drop_duplicates(
        subset=["ticker", "event_date", "transaction_type", "event_type"]
    )

    logger.info("Parsed %s events with standard schema", len(df))
    return df


def save_events(df: pd.DataFrame, filename: str = "events.csv") -> str:
    """Save parsed events to the configured events directory."""
    output_path = EVENTS_DIR / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info("Saved %s events to: %s", len(df), output_path)
    return str(output_path)
