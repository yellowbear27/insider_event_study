# backtest/engine.py
"""Backtesting utilities for event-driven hypothesis tests.

Core principles:
- Event returns are calculated from the first trading day on/after event_date.
- Baseline returns are deterministic.
- Baseline excludes known event dates for the same ticker.
- CAR is aligned by actual dates, not row position.
"""

import logging
from typing import Dict, Iterable, List, Optional, Set

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_HORIZONS = [5, 20, 60]


def calculate_returns(
    events_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    benchmark_df: Optional[pd.DataFrame] = None,
    horizons: Optional[List[int]] = None,
    price_col: str = "Close",
) -> pd.DataFrame:
    """Calculate forward returns and optional CAR for each event."""
    horizons = horizons or DEFAULT_HORIZONS

    if events_df.empty or prices_df.empty:
        logger.warning("Cannot calculate returns: empty input")
        return events_df.copy()

    events = events_df.copy()
    prices = prepare_prices(prices_df)

    events["event_date"] = normalize_dates(events["event_date"])

    benchmark = None
    if benchmark_df is not None and not benchmark_df.empty:
        benchmark = prepare_benchmark(benchmark_df)

    for horizon in horizons:
        ret_col = f"ret_{horizon}d"
        car_col = f"car_{horizon}d"

        events[ret_col] = events.apply(
            lambda row: forward_return(
                ticker=row["ticker"],
                event_date=row["event_date"],
                horizon=horizon,
                prices_df=prices,
                price_col=price_col,
            ),
            axis=1,
        )

        if benchmark is not None:
            events[car_col] = calculate_car_for_events(
                events_df=events,
                prices_df=prices,
                benchmark_df=benchmark,
                horizon=horizon,
                price_col=price_col,
            )

        valid_count = events[ret_col].notna().sum()

        logger.info(
            "Horizon %sd: %s/%s returns calculated",
            horizon,
            valid_count,
            len(events),
        )

    return events


def calculate_baseline(
    prices_df: pd.DataFrame,
    ticker: str,
    event_dates: Optional[Iterable[pd.Timestamp]] = None,
    horizons: Optional[List[int]] = None,
    price_col: str = "Close",
) -> Dict[str, float]:
    """Calculate deterministic non-event baseline returns.

    Baseline = average forward return across all valid start dates,
    excluding known event dates for that ticker.

    This replaces random baseline sampling.
    """
    horizons = horizons or DEFAULT_HORIZONS

    prices = prepare_prices(prices_df)
    ticker_prices = prices[prices["ticker"] == ticker].reset_index(drop=True)

    if ticker_prices.empty:
        logger.warning("No price data for baseline ticker: %s", ticker)
        return {}

    max_start = len(ticker_prices) - max(horizons) - 1

    if max_start <= 0:
        logger.warning("Not enough price data for baseline ticker: %s", ticker)
        return {}

    excluded_dates = date_set(event_dates)

    results: Dict[str, float] = {}

    for horizon in horizons:
        returns = []

        for start_idx in range(max_start):
            start_date = ticker_prices.iloc[start_idx]["Date"]

            if start_date in excluded_dates:
                continue

            p0 = ticker_prices.iloc[start_idx][price_col]
            p1 = ticker_prices.iloc[start_idx + horizon][price_col]

            if pd.notna(p0) and pd.notna(p1) and p0 != 0:
                returns.append((p1 - p0) / p0)

        if returns:
            results[f"ret_{horizon}d_mean"] = float(np.mean(returns))

    logger.info(
        "Calculated deterministic non-event baseline for %s",
        ticker,
    )

    return results


def calculate_car_for_events(
    events_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    horizon: int,
    price_col: str = "Close",
) -> pd.Series:
    """Calculate CAR for each event."""
    return events_df.apply(
        lambda row: cumulative_abnormal_return(
            ticker=row["ticker"],
            event_date=row["event_date"],
            horizon=horizon,
            stock_prices=prices_df,
            benchmark_prices=benchmark_df,
            price_col=price_col,
        ),
        axis=1,
    )


def forward_return(
    ticker: str,
    event_date: pd.Timestamp,
    horizon: int,
    prices_df: pd.DataFrame,
    price_col: str = "Close",
) -> float:
    """Calculate forward return from first trading day on/after event_date."""
    ticker_prices = prices_df[prices_df["ticker"] == ticker].reset_index(drop=True)

    if ticker_prices.empty:
        return np.nan

    mask = ticker_prices["Date"] >= event_date

    if not mask.any():
        return np.nan

    start_idx = mask.idxmax()
    end_idx = start_idx + horizon

    if end_idx >= len(ticker_prices):
        return np.nan

    p0 = ticker_prices.iloc[start_idx][price_col]
    p1 = ticker_prices.iloc[end_idx][price_col]

    if pd.isna(p0) or pd.isna(p1) or p0 == 0:
        return np.nan

    return float((p1 - p0) / p0)


def cumulative_abnormal_return(
    ticker: str,
    event_date: pd.Timestamp,
    horizon: int,
    stock_prices: pd.DataFrame,
    benchmark_prices: pd.DataFrame,
    price_col: str = "Close",
) -> float:
    """Calculate cumulative abnormal return versus benchmark.

    Stock and benchmark returns are aligned by actual Date.
    """
    ticker_prices = stock_prices[stock_prices["ticker"] == ticker].reset_index(drop=True)

    if ticker_prices.empty:
        return np.nan

    mask = ticker_prices["Date"] >= event_date

    if not mask.any():
        return np.nan

    start_idx = mask.idxmax()
    end_idx = start_idx + horizon

    if end_idx >= len(ticker_prices):
        return np.nan

    start_date = ticker_prices.iloc[start_idx]["Date"]
    end_date = ticker_prices.iloc[end_idx]["Date"]

    stock_window = ticker_prices[
        (ticker_prices["Date"] >= start_date)
        & (ticker_prices["Date"] <= end_date)
    ][["Date", price_col]].copy()

    benchmark_window = benchmark_prices[
        (benchmark_prices["Date"] >= start_date)
        & (benchmark_prices["Date"] <= end_date)
    ][["Date", price_col]].copy()

    stock_window["stock_return"] = stock_window[price_col].pct_change()
    benchmark_window["benchmark_return"] = benchmark_window[price_col].pct_change()

    aligned = pd.merge(
        stock_window[["Date", "stock_return"]],
        benchmark_window[["Date", "benchmark_return"]],
        on="Date",
        how="inner",
    ).dropna()

    if aligned.empty:
        return np.nan

    return float((aligned["stock_return"] - aligned["benchmark_return"]).sum())


def prepare_prices(prices_df: pd.DataFrame) -> pd.DataFrame:
    """Normalize stock price data."""
    prices = prices_df.copy()

    if isinstance(prices.index, pd.DatetimeIndex):
        prices = prices.reset_index().rename(columns={"index": "Date"})

    if "Date" not in prices.columns:
        raise ValueError("prices_df must contain a 'Date' column or DatetimeIndex")

    if "ticker" not in prices.columns:
        raise ValueError("prices_df must contain a 'ticker' column")

    prices["Date"] = normalize_dates(prices["Date"])

    return prices.sort_values(["ticker", "Date"]).reset_index(drop=True)


def prepare_benchmark(benchmark_df: pd.DataFrame) -> pd.DataFrame:
    """Normalize benchmark price data."""
    benchmark = benchmark_df.copy()

    if isinstance(benchmark.index, pd.DatetimeIndex):
        benchmark = benchmark.reset_index().rename(columns={"index": "Date"})

    if "Date" not in benchmark.columns:
        raise ValueError("benchmark_df must contain a 'Date' column or DatetimeIndex")

    benchmark["Date"] = normalize_dates(benchmark["Date"])

    return benchmark.sort_values("Date").reset_index(drop=True)


def normalize_dates(values: pd.Series) -> pd.Series:
    """Convert values to timezone-naive pandas timestamps."""
    return pd.to_datetime(values, errors="coerce").dt.tz_localize(None)


def date_set(values: Optional[Iterable[pd.Timestamp]]) -> Set[pd.Timestamp]:
    """Convert optional dates into a normalized set."""
    if values is None:
        return set()

    dates = pd.Series(values)
    dates = normalize_dates(dates)

    return set(dates.dropna())
