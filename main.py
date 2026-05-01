#!/usr/bin/env python3
# main.py
"""Pipeline orchestrator for event-driven signal hypothesis testing."""

import argparse
import logging
import sys
from typing import List, Optional

import pandas as pd
import yaml

from backtest.engine import calculate_baseline, calculate_returns
from config.settings import OUTPUT_DIR, ROOT_DIR
from data.congress_loader import fetch_senate_trades, load_raw_trades, save_raw_trades
from data.price_loader import fetch_benchmark, fetch_prices
from data.storage import load_dataframe, save_dataframe
from events.congress_parser import parse_raw_trades, save_events
from events.event_builder import enrich_events, filter_by_hypothesis
from report.report_generator import generate_report, print_report


def setup_logging(level: str = "INFO") -> None:
    """Configure console logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def load_config(config_name: str) -> dict:
    """Load a YAML config file from config/."""
    config_path = ROOT_DIR / "config" / f"{config_name}.yaml"

    if not config_path.exists():
        logging.warning("Config not found: %s; using defaults", config_path)
        return {}

    with open(config_path, "r") as file:
        return yaml.safe_load(file) or {}


def run_pipeline(
    stage: Optional[str] = None,
    tickers: Optional[List[str]] = None,
    hypothesis_name: Optional[str] = None,
    use_cache: bool = True,
) -> None:
    """Run the event-study pipeline."""
    logger = logging.getLogger(__name__)

    logger.info(
        "Starting pipeline | stage=%s | tickers=%s | hypothesis=%s",
        stage,
        tickers,
        hypothesis_name,
    )

    universe_cfg = load_config("universe")
    hypotheses_cfg = load_config("hypotheses")

    target_tickers = tickers or universe_cfg.get("tickers", ["NVDA", "CDNS", "SNPS"])
    hypothesis = get_hypothesis(hypotheses_cfg, hypothesis_name)

    raw_data = None

    # FETCH
    if stage in [None, "fetch"]:
        logger.info("Stage: fetch raw congressional trades")

        raw_data = fetch_senate_trades()

        if raw_data:
            save_raw_trades(raw_data)
        else:
            logger.info("Fetch failed or unavailable; loading raw trades from cache")
            raw_data = load_raw_trades()

        if not raw_data:
            logger.error("No raw data available. Exiting.")
            return

    # PARSE
    if stage in [None, "parse"]:
        logger.info("Stage: parse events")

        raw = raw_data or load_raw_trades()

        if not raw:
            logger.error("No raw data available for parsing. Exiting.")
            return

        events_df = parse_raw_trades(raw, target_tickers=target_tickers)
        save_events(events_df)
    else:
        events_df = load_dataframe("events.csv", directory=ROOT_DIR / "data" / "events")

    if events_df is None or events_df.empty:
        logger.error("No events available. Exiting.")
        return

    # ENRICH
    if stage in [None, "enrich"]:
        logger.info("Stage: enrich events")

        events_df = enrich_events(events_df)
        save_events(events_df, filename="events_enriched.csv")

    # BACKTEST
    results_df = None
    baseline = {}

    if stage in [None, "backtest"]:
        logger.info("Stage: backtest")

        if hypothesis:
            events_df = filter_by_hypothesis(events_df, hypothesis)
            logger.info("Filtered for hypothesis: %s", hypothesis_name)

        if events_df.empty:
            logger.warning("No events match hypothesis. Skipping backtest.")
            return

        horizons = hypothesis.get("horizons", [5, 20, 60])
        benchmark_ticker = hypothesis.get("benchmark", "SPY")

        start_date = pd.to_datetime(events_df["event_date"]).min().strftime("%Y-%m-%d")
        end_date = pd.to_datetime(events_df["event_date"]).max().strftime("%Y-%m-%d")

        prices_df = fetch_all_prices(
            tickers=events_df["ticker"].dropna().unique().tolist(),
            start_date=start_date,
            end_date=end_date,
            use_cache=use_cache,
        )

        if prices_df is None or prices_df.empty:
            logger.error("No price data fetched. Exiting.")
            return

        benchmark_df = fetch_benchmark(
            start_date,
            end_date,
            benchmark=benchmark_ticker,
            use_cache=use_cache,
        )

        results_df = calculate_returns(
            events_df=events_df,
            prices_df=prices_df,
            benchmark_df=benchmark_df,
            horizons=horizons,
        )

        baseline = calculate_all_baselines(
            results_df=results_df,
            prices_df=prices_df,
            horizons=horizons,
        )

        save_dataframe(results_df, "backtest_results.csv", directory=OUTPUT_DIR)

        logger.info("Backtest complete: %s events evaluated", len(results_df))

    # REPORT
    if stage in [None, "report"]:
        logger.info("Stage: report")

        report_df = results_df

        if report_df is None or report_df.empty:
            report_df = load_dataframe("backtest_results.csv", directory=OUTPUT_DIR)

        if report_df is None or report_df.empty:
            logger.warning("No backtest results available for report")
            return

        report_text = generate_report(
            hypothesis_name or "default_test",
            report_df,
            baseline=baseline or None,
            config=hypothesis or {"min_sample_size": 10},
        )

        print_report(report_text)

    logger.info("Pipeline complete")


def get_hypothesis(hypotheses_cfg: dict, hypothesis_name: Optional[str]) -> dict:
    """Return selected hypothesis config."""
    if not hypothesis_name:
        return {}

    hypotheses = hypotheses_cfg.get("hypotheses", {})

    if hypothesis_name not in hypotheses:
        logging.warning("Hypothesis not found: %s", hypothesis_name)
        return {}

    return hypotheses[hypothesis_name]


def fetch_all_prices(
    tickers: List[str],
    start_date: str,
    end_date: str,
    use_cache: bool = True,
) -> Optional[pd.DataFrame]:
    """Fetch and combine price data for all tickers."""
    logger = logging.getLogger(__name__)

    price_frames = []

    for ticker in tickers:
        price_df = fetch_prices(
            ticker,
            start_date,
            end_date,
            use_cache=use_cache,
        )

        if price_df is not None and not price_df.empty:
            price_frames.append(price_df)

    if not price_frames:
        logger.error("No price data available for requested tickers")
        return None

    return pd.concat(price_frames, ignore_index=False)


def calculate_all_baselines(
    results_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    horizons: List[int],
) -> dict:
    """Calculate deterministic non-event baseline for each ticker."""
    baseline = {}

    for ticker in results_df["ticker"].dropna().unique():
        ticker_event_dates = results_df.loc[
            results_df["ticker"] == ticker,
            "event_date",
        ]

        ticker_baseline = calculate_baseline(
            prices_df=prices_df,
            ticker=ticker,
            event_dates=ticker_event_dates,
            horizons=horizons,
        )

        baseline.update(
            {f"{ticker}_{key}": value for key, value in ticker_baseline.items()}
        )

    return baseline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Event-driven signal hypothesis testing pipeline"
    )

    parser.add_argument(
        "--stage",
        choices=["fetch", "parse", "enrich", "backtest", "report"],
    )

    parser.add_argument("--tickers", nargs="+")
    parser.add_argument("--hypothesis")
    parser.add_argument("--no-cache", action="store_true")

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )

    args = parser.parse_args()
    setup_logging(args.log_level)

    try:
        run_pipeline(
            stage=args.stage,
            tickers=args.tickers,
            hypothesis_name=args.hypothesis,
            use_cache=not args.no_cache,
        )
    except KeyboardInterrupt:
        logging.warning("Interrupted")
        sys.exit(130)
    except Exception as error:
        logging.error("Pipeline failed: %s", error, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
