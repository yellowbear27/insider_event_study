# data/price_loader.py
"""
Price data ingestion via yfinance with local caching.
Config-driven benchmark, Parquet/CSV cache support.
"""
import pandas as pd
import yfinance as yf
import logging
from pathlib import Path
from typing import Optional, List, Union
from datetime import datetime, timedelta

from config.settings import CACHE_DIR, BENCHMARK_TICKER, DEFAULT_START_DATE, DEFAULT_END_DATE

logger = logging.getLogger(__name__)


def fetch_prices(
    ticker: str,
    start_date: str = DEFAULT_START_DATE,
    end_date: str = DEFAULT_END_DATE,
    use_cache: bool = True,
    cache_format: str = "parquet"  # or "csv"
) -> Optional[pd.DataFrame]:
    """
    Fetch OHLCV data with local caching.
    
    Args:
        ticker: Stock symbol (e.g., "NVDA")
        start_date/end_date: ISO format date strings
        use_cache: Return cached data if available
        cache_format: "parquet" (faster) or "csv"
    
    Returns:
        DataFrame with OHLCV data, or None if fetch fails
    """
    cache_path = _get_cache_path(ticker, start_date, end_date, cache_format)
    
    # Try cache first
    if use_cache and cache_path.exists():
        try:
            df = _read_cache(cache_path, cache_format)
            logger.info(f"📂 Loaded {ticker} from cache: {cache_path}")
            return df
        except Exception as e:
            logger.warning(f"Cache read failed for {ticker}: {e}. Fetching fresh...")
    
    # Fetch from yfinance
    logger.info(f"🔄 Fetching {ticker} from yfinance: {start_date} to {end_date}")
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(start=start_date, end=end_date, auto_adjust=True)
        
        if df.empty:
            logger.warning(f"No price data for {ticker} in date range")
            return None
        
        # Add ticker column for merging
        df = df.copy()
        df['ticker'] = ticker
        
        # Save to cache
        if use_cache:
            _save_cache(df, cache_path, cache_format)
            logger.info(f"💾 Cached {ticker} to: {cache_path}")
        
        return df
        
    except Exception as e:
        logger.error(f"Failed to fetch {ticker}: {e}")
        return None


def fetch_benchmark(
    start_date: str = DEFAULT_START_DATE,
    end_date: str = DEFAULT_END_DATE,
    benchmark: str = None,
    **kwargs
) -> Optional[pd.DataFrame]:
    """Fetch benchmark (e.g., SPY) for abnormal return calculations."""
    benchmark = benchmark or BENCHMARK_TICKER
    return fetch_prices(benchmark, start_date, end_date, **kwargs)


def fetch_multiple(
    tickers: List[str],
    start_date: str = DEFAULT_START_DATE,
    end_date: str = DEFAULT_END_DATE,
    **kwargs
) -> pd.DataFrame:
    """Fetch multiple tickers and concatenate."""
    dfs = []
    for ticker in tickers:
        df = fetch_prices(ticker, start_date, end_date, **kwargs)
        if df is not None:
            dfs.append(df)
    
    if not dfs:
        logger.warning("No price data fetched for any tickers")
        return pd.DataFrame()
    
    return pd.concat(dfs, ignore_index=False)


def _get_cache_path(
    ticker: str, 
    start_date: str, 
    end_date: str, 
    fmt: str
) -> Path:
    """Generate cache file path."""
    safe_start = start_date.replace("-", "")
    safe_end = end_date.replace("-", "")
    filename = f"{ticker}_{safe_start}_{safe_end}.{fmt}"
    return CACHE_DIR / "prices" / filename


def _save_cache(df: pd.DataFrame, path: Path, fmt: str):
    """Save DataFrame to cache."""
    path.parent.mkdir(parents=True, exist_ok=True)
    
    if fmt == "parquet":
        df.to_parquet(path, index=True)
    else:
        df.to_csv(path, index=True)


def _read_cache(path: Path, fmt: str) -> pd.DataFrame:
    """Read DataFrame from cache."""
    if fmt == "parquet":
        return pd.read_parquet(path)
    else:
        return pd.read_csv(path, index_col=0, parse_dates=True)


def align_prices(
    events_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    benchmark_df: Optional[pd.DataFrame] = None,
    window_days: int = 30
) -> pd.DataFrame:
    """
    Align event dates with price data for backtesting.
    
    Args:
        events_df: DataFrame with 'ticker' and 'event_date' columns
        prices_df: OHLCV DataFrame with 'ticker' column
        benchmark_df: Optional benchmark prices for CAR calculation
        window_days: Forward window for return calculation
    
    Returns:
        DataFrame with event + price data aligned
    """
    if events_df.empty or prices_df.empty:
        logger.warning("Cannot align: empty events or prices")
        return pd.DataFrame()
    
    # Merge events with prices on ticker + date
    aligned = events_df.merge(
        prices_df.reset_index(),
        on=['ticker', 'event_date'],
        how='left',
        suffixes=('_event', '_price')
    )
    
    # Add benchmark if provided
    if benchmark_df is not None and 'Close' in benchmark_df.columns:
        benchmark_renamed = benchmark_df.reset_index().rename(
            columns={'Close': 'benchmark_close', 'Date': 'event_date'}
        )
        aligned = aligned.merge(
            benchmark_renamed[['event_date', 'benchmark_close']],
            on='event_date',
            how='left'
        )
    
    logger.info(f"✅ Aligned {len(aligned)} events with price data")
    return aligned
