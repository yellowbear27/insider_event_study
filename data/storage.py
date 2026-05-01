# data/storage.py
"""Save and load DataFrames to CSV or Parquet."""
import pandas as pd
import logging
from pathlib import Path
from typing import Optional, Union

from config.settings import OUTPUT_DIR

logger = logging.getLogger(__name__)

try:
    import pyarrow  # noqa: F401
    _PARQUET_AVAILABLE = True
except ImportError:
    _PARQUET_AVAILABLE = False


def save_dataframe(
    df: pd.DataFrame,
    filename: str,
    directory: Union[Path, str] = OUTPUT_DIR,
    fmt: str = "csv"
) -> Path:
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / filename

    if fmt == "parquet" and not _PARQUET_AVAILABLE:
        logger.warning("pyarrow not available, falling back to CSV")
        fmt = "csv"
        file_path = file_path.with_suffix(".csv")

    if fmt == "parquet":
        df.to_parquet(file_path, index=False)
    else:
        df.to_csv(file_path, index=False)

    logger.info(f"💾 Saved {len(df)} rows to {file_path}")
    return file_path


def load_dataframe(
    filename: str,
    directory: Union[Path, str] = OUTPUT_DIR,
    fmt: str = "csv"
) -> Optional[pd.DataFrame]:
    file_path = Path(directory) / filename

    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return None

    try:
        df = pd.read_parquet(file_path) if fmt == "parquet" and _PARQUET_AVAILABLE else pd.read_csv(file_path)
        logger.info(f"📂 Loaded {len(df)} rows from {file_path}")
        return df
    except Exception as e:
        logger.error(f"Failed to load {file_path}: {e}")
        return None
