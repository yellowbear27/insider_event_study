# backtest/engine.py - FINAL FIX FOR YOUR DATA STRUCTURE
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
    """Calculate forward returns with robust date alignment."""
    if events_df.empty or prices_df.empty:
        logger.warning("Cannot calculate returns: empty input")
        return events_df.copy()
    
    df = events_df.copy()
    
    # FIX 1: Convert event_date from string to naive datetime
    df['event_date'] = pd.to_datetime(df['event_date']).dt.tz_localize(None)
    
    # FIX 2: Prices have DatetimeIndex. Reset to get 'Date' column with integer index.
    if isinstance(prices_df.index, pd.DatetimeIndex):
        prices_df = prices_df.copy().reset_index().rename(columns={'index': 'Date'})
    prices_df['Date'] = pd.to_datetime(prices_df['Date']).dt.tz_localize(None)
    prices_df = prices_df.sort_values(['ticker', 'Date']).reset_index(drop=True)
    
    # Same for benchmark
    if benchmark_df is not None and isinstance(benchmark_df.index, pd.DatetimeIndex):
        benchmark_df = benchmark_df.copy().reset_index().rename(columns={'index': 'Date'})
        benchmark_df['Date'] = pd.to_datetime(benchmark_df['Date']).dt.tz_localize(None)
        benchmark_df = benchmark_df.sort_values('Date').reset_index(drop=True)
    
    # Calculate returns for each horizon
    for horizon in horizons:
        df[f'ret_{horizon}d'] = df.apply(
            lambda row: _calc_forward_return(
                row['ticker'], row['event_date'], horizon, 
                prices_df, benchmark_col
            ),
            axis=1
        )
        
        if benchmark_df is not None:
            df[f'car_{horizon}d'] = df.apply(
                lambda row: _calc_car(
                    row['ticker'], row['event_date'], horizon,
                    prices_df, benchmark_df, benchmark_col
                ),
                axis=1
            )
    
    # Log success rate
    for horizon in horizons:
        valid = df[f'ret_{horizon}d'].notna().sum()
        logger.info(f"📊 Horizon {horizon}d: {valid}/{len(df)} returns calculated")
    
    logger.info(f"✅ Calculated returns for horizons: {horizons}")
    return df


def _calc_forward_return(
    ticker: str,
    event_date: pd.Timestamp,
    horizon: int,
    prices_df: pd.DataFrame,
    price_col: str
) -> Optional[float]:
    """Calculate forward return using integer index positions (.iloc)."""
    try:
        # Filter to ticker and reset index for integer access
        ticker_prices = prices_df[prices_df['ticker'] == ticker].copy().reset_index(drop=True)
        if ticker_prices.empty:
            return np.nan
        
        # Find first trading day >= event_date
        mask = ticker_prices['Date'] >= event_date
        if not mask.any():
            return np.nan
        
        # Get integer position (0-based) of first match
        start_pos = mask.idxmax()  # This returns the label, but we reset index so label=int
        
        # End position: horizon trading days later
        end_pos = start_pos + horizon
        if end_pos >= len(ticker_prices):
            return np.nan
        
        # Use .iloc for integer position access (NOT .loc)
        start_price = ticker_prices.iloc[start_pos][price_col]
        end_price = ticker_prices.iloc[end_pos][price_col]
        
        if pd.isna(start_price) or pd.isna(end_price) or start_price == 0:
            return np.nan
        
        return (end_price - start_price) / start_price
        
    except Exception as e:
        logger.debug(f"Return calc failed for {ticker} @ {event_date}: {e}")
        return np.nan


def _calc_car(
    ticker: str,
    event_date: pd.Timestamp,
    horizon: int,
    stock_prices: pd.DataFrame,
    benchmark_prices: pd.DataFrame,
    price_col: str
) -> Optional[float]:
    """Calculate CAR using integer index positions."""
    try:
        stock_subset = stock_prices[stock_prices['ticker'] == ticker].copy().reset_index(drop=True)
        if stock_subset.empty:
            return np.nan
        
        mask = stock_subset['Date'] >= event_date
        if not mask.any():
            return np.nan
        
        start_pos = mask.idxmax()
        end_pos = start_pos + horizon
        if end_pos >= len(stock_subset):
            return np.nan
        
        start_date = stock_subset.iloc[start_pos]['Date']
        end_date = stock_subset.iloc[end_pos]['Date']
        
        # Calculate returns
        stock_slice = stock_subset[
            (stock_subset['Date'] >= start_date) & 
            (stock_subset['Date'] <= end_date)
        ][price_col].pct_change().dropna()
        
        bench_slice = benchmark_prices[
            (benchmark_prices['Date'] >= start_date) & 
            (benchmark_prices['Date'] <= end_date)
        ][price_col].pct_change().dropna()
        
        if len(stock_slice) < 2 or len(bench_slice) < 2:
            return np.nan
        
        aligned = pd.DataFrame({'stock': stock_slice, 'bench': bench_slice}).dropna()
        if aligned.empty:
            return np.nan
        
        return (aligned['stock'] - aligned['bench']).sum()
        
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
    """Calculate baseline returns from random non-event days.
    
    FIX: Use .iloc[] for integer position access, NOT .loc[]
    """
    # Filter and reset index for integer access
    ticker_prices = prices_df[prices_df['ticker'] == ticker].copy().reset_index(drop=True)
    
    if len(ticker_prices) < max(horizons) + 10:
        return {}
    
    # Sample random start POSITIONS (not labels)
    max_start = len(ticker_prices) - max(horizons) - 1
    if max_start <= 0:
        return {}
    
    sample_positions = np.random.choice(
        range(max_start), 
        size=min(sample_size, max_start), 
        replace=False
    )
    
    results = {}
    for horizon in horizons:
        returns = []
        for pos in sample_positions:
            # FIX: Use .iloc[] for integer position, NOT .loc[]
            start_p = ticker_prices.iloc[pos][price_col]
            end_p = ticker_prices.iloc[pos + horizon][price_col]
            if pd.notna(start_p) and pd.notna(end_p) and start_p != 0:
                returns.append((end_p - start_p) / start_p)
        
        if returns:
            results[f'ret_{horizon}d_mean'] = np.mean(returns)
            results[f'ret_{horizon}d_median'] = np.median(returns)
            results[f'ret_{horizon}d_std'] = np.std(returns)
    
    logger.info(f"✅ Calculated baseline for {ticker} from {len(sample_positions)} random days")
    return results
