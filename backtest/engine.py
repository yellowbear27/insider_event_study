# backtest/engine.py
import pandas as pd
import numpy as np
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


def calculate_returns(
    events_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    benchmark_df: Optional[pd.DataFrame] = None,
    horizons: List[int] = [5, 20, 60],
    benchmark_col: str = 'Close'
) -> pd.DataFrame:
    if events_df.empty or prices_df.empty:
        logger.warning("Cannot calculate returns: empty input")
        return events_df.copy()

    df = events_df.copy()
    df['event_date'] = pd.to_datetime(df['event_date']).dt.tz_localize(None)

    if isinstance(prices_df.index, pd.DatetimeIndex):
        prices_df = prices_df.copy().reset_index().rename(columns={'index': 'Date'})
    prices_df['Date'] = pd.to_datetime(prices_df['Date']).dt.tz_localize(None)
    prices_df = prices_df.sort_values(['ticker', 'Date']).reset_index(drop=True)

    if benchmark_df is not None and isinstance(benchmark_df.index, pd.DatetimeIndex):
        benchmark_df = benchmark_df.copy().reset_index().rename(columns={'index': 'Date'})
        benchmark_df['Date'] = pd.to_datetime(benchmark_df['Date']).dt.tz_localize(None)
        benchmark_df = benchmark_df.sort_values('Date').reset_index(drop=True)

    for horizon in horizons:
        df[f'ret_{horizon}d'] = df.apply(
            lambda row: _forward_return(row['ticker'], row['event_date'], horizon, prices_df, benchmark_col),
            axis=1
        )
        if benchmark_df is not None:
            df[f'car_{horizon}d'] = df.apply(
                lambda row: _car(row['ticker'], row['event_date'], horizon, prices_df, benchmark_df, benchmark_col),
                axis=1
            )
        valid = df[f'ret_{horizon}d'].notna().sum()
        logger.info(f"📊 Horizon {horizon}d: {valid}/{len(df)} returns calculated")

    logger.info(f"✅ Calculated returns for horizons: {horizons}")
    return df


def _forward_return(
    ticker: str, event_date: pd.Timestamp, horizon: int,
    prices_df: pd.DataFrame, price_col: str
) -> Optional[float]:
    try:
        tp = prices_df[prices_df['ticker'] == ticker].reset_index(drop=True)
        if tp.empty:
            return np.nan
        mask = tp['Date'] >= event_date
        if not mask.any():
            return np.nan
        start = mask.idxmax()
        end = start + horizon
        if end >= len(tp):
            return np.nan
        p0, p1 = tp.iloc[start][price_col], tp.iloc[end][price_col]
        if pd.isna(p0) or pd.isna(p1) or p0 == 0:
            return np.nan
        return (p1 - p0) / p0
    except Exception as e:
        logger.debug(f"Return calc failed for {ticker} @ {event_date}: {e}")
        return np.nan


def _car(
    ticker: str, event_date: pd.Timestamp, horizon: int,
    stock_prices: pd.DataFrame, benchmark_prices: pd.DataFrame, price_col: str
) -> Optional[float]:
    try:
        sp = stock_prices[stock_prices['ticker'] == ticker].reset_index(drop=True)
        if sp.empty:
            return np.nan
        mask = sp['Date'] >= event_date
        if not mask.any():
            return np.nan
        start = mask.idxmax()
        end = start + horizon
        if end >= len(sp):
            return np.nan
        d0, d1 = sp.iloc[start]['Date'], sp.iloc[end]['Date']
        stock_ret = sp[(sp['Date'] >= d0) & (sp['Date'] <= d1)][price_col].pct_change().dropna()
        bench_ret = benchmark_prices[(benchmark_prices['Date'] >= d0) & (benchmark_prices['Date'] <= d1)][price_col].pct_change().dropna()
        if len(stock_ret) < 2 or len(bench_ret) < 2:
            return np.nan
        aligned = pd.DataFrame({'stock': stock_ret, 'bench': bench_ret}).dropna()
        return (aligned['stock'] - aligned['bench']).sum() if not aligned.empty else np.nan
    except Exception as e:
        logger.debug(f"CAR calc failed: {e}")
        return np.nan


def calculate_baseline(
    prices_df: pd.DataFrame,
    ticker: str,
    horizons: List[int] = [5, 20, 60],
    sample_size: int = 100,
    price_col: str = 'Close'
) -> Dict[str, float]:
    tp = prices_df[prices_df['ticker'] == ticker].reset_index(drop=True)
    max_start = len(tp) - max(horizons) - 1
    if max_start <= 0:
        return {}

    positions = np.random.choice(range(max_start), size=min(sample_size, max_start), replace=False)
    results = {}
    for horizon in horizons:
        returns = [
            (tp.iloc[p + horizon][price_col] - tp.iloc[p][price_col]) / tp.iloc[p][price_col]
            for p in positions
            if pd.notna(tp.iloc[p][price_col]) and pd.notna(tp.iloc[p + horizon][price_col])
            and tp.iloc[p][price_col] != 0
        ]
        if returns:
            results[f'ret_{horizon}d_mean'] = np.mean(returns)

    logger.info(f"✅ Calculated baseline for {ticker} from {len(positions)} random days")
    return results
