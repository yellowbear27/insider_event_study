# data/insider_loader.py
"""
Insider trade data ingestion from Senate disclosures.
Config-driven URL, retry logic, structured logging.
"""
import json
import requests
import logging
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from config.settings import SENATE_API_URL, RAW_DIR

logger = logging.getLogger(__name__)


def fetch_senate_trades(
    url: Optional[str] = None,
    max_retries: int = 3,
    backoff_factor: float = 1.0
) -> Optional[List[Dict[str, Any]]]:
    """
    Fetch Senate insider trade JSON with exponential backoff retry.

    Args:
        url: Override default SENATE_API_URL (for testing)
        max_retries: Number of retry attempts on failure
        backoff_factor: Multiplier for exponential backoff (seconds)

    Returns:
        List of trade records, or None if all retries fail
    """
    fetch_url = url or SENATE_API_URL

    if fetch_url is None:
        logger.info("SENATE_API_URL not configured — skipping fetch, using cache")
        return None

    logger.info(f"Fetching insider trades from: {fetch_url}")

    for attempt in range(max_retries):
        try:
            response = requests.get(fetch_url, timeout=30)
            response.raise_for_status()
            data = response.json()
            logger.info(f"✅ Successfully fetched {len(data)} records")
            return data

        except requests.exceptions.RequestException as e:
            wait_time = backoff_factor * (2 ** attempt)
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                f"Retrying in {wait_time}s..."
            )
            time.sleep(wait_time)
        except ValueError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return None

    logger.error(f"❌ Failed to fetch data after {max_retries} attempts")
    return None


def save_raw_trades(data: List[Dict[str, Any]], filename: str = "senate_trades.json") -> Path:
    """
    Save raw JSON to data/raw/ directory.

    Args:
        data: List of trade records
        filename: Output filename

    Returns:
        Path to saved file
    """
    output_path = RAW_DIR / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    logger.info(f"💾 Saved raw trades to: {output_path}")
    return output_path


def load_raw_trades(filename: str = "senate_trades.json") -> Optional[List[Dict[str, Any]]]:
    """
    Load previously saved raw trades from disk.

    Args:
        filename: Filename in data/raw/

    Returns:
        List of trade records, or None if file not found/invalid
    """
    file_path = RAW_DIR / filename

    if not file_path.exists():
        logger.warning(f"Raw file not found: {file_path}")
        return None

    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        logger.info(f"📂 Loaded {len(data)} records from: {file_path}")
        return data
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to load raw trades: {e}")
        return None
