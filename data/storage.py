# data/storage.py
"""Data persistence utilities: save/load DataFrames to CSV or Parquet."""
import pandas as pd
import logging
from pathlib import Path
from typing import Optional, Union

from config.settings import RAW_DIR, OUTPUT_DIR, EVENTS_DIR, CACHE_DIR

logger = logging.getLogger(__name__)

def _check_parquet_support() -> bool:
    """Check if pyarrow or fastparquet is available."""
    try:
        import pyarrow  # noqa: F401
        return True
    except ImportError:
        try:
            import fastparquet  # noqa: F401
            return True
        except ImportError:
            return False

def save_dataframe(
    df: pd.DataFrame,
    filename: str,
    directory: Union[Path, str] = OUTPUT_DIR,
    fmt: str = "csv"
) -> Path:
    """Save DataFrame to disk. Supports csv and parquet (if dependency available)."""
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / filename
    
    try:
        if fmt.lower() == "parquet":
            if not _check_parquet_support():
                logger.warning("Parquet not available (install pyarrow). Falling back to CSV.")
                file_path = file_path.with_suffix('.csv')
                df.to_csv(file_path, index=False)
            else:
                df.to_parquet(file_path, index=False)
        else:
            df.to_csv(file_path, index=False)
        logger.info(f"💾 Saved {len(df)} rows to {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Failed to save {file_path}: {e}")
        raise

def load_dataframe(
    filename: str,
    directory: Union[Path, str] = OUTPUT_DIR,
    fmt: str = "csv"
) -> Optional[pd.DataFrame]:
    """Load DataFrame from disk. Returns None if file not found."""
    file_path = Path(directory) / filename
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return None
    
    try:
        if fmt.lower() == "parquet" and _check_parquet_support():
            df = pd.read_parquet(file_path)
        else:
            # Auto-detect: if parquet requested but not available, try CSV
            df = pd.read_csv(file_path)
        logger.info(f"📂 Loaded {len(df)} rows from {file_path}")
        return df
    except Exception as e:
        logger.error(f"Failed to load {file_path}: {e}")
        return None
