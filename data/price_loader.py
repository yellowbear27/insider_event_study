# data/price_loader.py
"""Price data via yfinance with local Parquet/CSV caching."""
import pandas as pd
import yfinance as yf
import logging
from pathlib import Path
from typing import Optional

from config.settings import CACHE_DIR, BENCHMARK_TICKER, DEFAULT_START_DATE, DEFAULT_END_DATE

logger = logging.getLogger(__name__)


def fetch_prices(
    ticker: str,
    start_date: str = DEFAULT_START_DATE,
    end_date: str = DEFAULT_END_DATE,
    use_cache: bool = True,
    cache_format: str = "parquet"
) -> Optional[pd.DataFrame]:
    cache_path = _cache_path(ticker, start_date, end_date, cache_format)

    if use_cache and cache_path.exists():
        try:
            df = _read_cache(cache_path, cache_format)
            logger.info(f"📂 Loaded {ticker} from cache: {cache_path}")
            return df
        except Exception as e:
            logger.warning(f"Cache read failed for {ticker}: {e}. Fetching fresh...")

    logger.info(f"🔄 Fetching {ticker} from yfinance: {start_date} to {end_date}")
    try:
        df = yf.Ticker(ticker).history(start=start_date, end=end_date, auto_adjust=True)
        if df.empty:
            logger.warning(f"No price data for {ticker}")
            return None
        df = df.copy()
        df['ticker'] = ticker
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
    return fetch_prices(benchmark or BENCHMARK_TICKER, start_date, end_date, **kwargs)


def _cache_path(ticker: str, start_date: str, end_date: str, fmt: str) -> Path:
    start = start_date.replace("-", "")
    end = end_date.replace("-", "")
    return CACHE_DIR / "prices" / f"{ticker}_{start}_{end}.{fmt}"


def _save_cache(df: pd.DataFrame, path: Path, fmt: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=True) if fmt == "parquet" else df.to_csv(path, index=True)


def _read_cache(path: Path, fmt: str) -> pd.DataFrame:
    return pd.read_parquet(path) if fmt == "parquet" else pd.read_csv(path, index_col=0, parse_dates=True)
