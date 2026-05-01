#!/usr/bin/env python3
# main.py
"""Pipeline orchestrator."""
import argparse
import logging
import sys
import yaml
import pandas as pd
from typing import Optional, List

from config.settings import ROOT_DIR, OUTPUT_DIR
from data.insider_loader import fetch_senate_trades, load_raw_trades, save_raw_trades
from data.price_loader import fetch_prices, fetch_benchmark
from events.insider_parser import parse_raw_trades, save_events
from events.event_builder import enrich_events, filter_by_hypothesis
from backtest.engine import calculate_returns, calculate_baseline
from report.report_generator import generate_report, print_report
from data.storage import save_dataframe, load_dataframe


def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def load_config(config_name: str) -> dict:
    config_path = ROOT_DIR / "config" / f"{config_name}.yaml"
    if not config_path.exists():
        logging.warning(f"Config not found: {config_path}, using defaults")
        return {}
    with open(config_path) as f:
        return yaml.safe_load(f)


def run_pipeline(
    stage: Optional[str] = None,
    tickers: Optional[List[str]] = None,
    hypothesis_name: Optional[str] = None,
    use_cache: bool = True
):
    logger = logging.getLogger(__name__)
    logger.info(f"🚀 Starting pipeline | stage={stage}, tickers={tickers}, hypothesis={hypothesis_name}")

    universe_cfg = load_config("universe")
    hypotheses_cfg = load_config("hypotheses")
    target_tickers = tickers or universe_cfg.get("tickers", ["NVDA", "CDNS", "SNPS"])
    hypothesis = hypotheses_cfg.get("hypotheses", {}).get(hypothesis_name, {}) if hypothesis_name else {}

    # ── FETCH ──────────────────────────────────────────────────────────────
    raw_data = None
    if stage in [None, "fetch"]:
        logger.info("📥 Stage: Fetch raw trades")
        raw_data = fetch_senate_trades()
        if raw_data:
            save_raw_trades(raw_data)
        else:
            logger.info("⚠️ Fetch failed, loading from cache...")
            raw_data = load_raw_trades()
        if not raw_data:
            logger.error("❌ No raw data available. Exiting.")
            return

    # ── PARSE ──────────────────────────────────────────────────────────────
    events_df = None
    if stage in [None, "parse"]:
        logger.info("🔍 Stage: Parse events")
        raw = raw_data or load_raw_trades()
        if not raw:
            logger.error("❌ No raw data for parsing. Exiting.")
            return
        events_df = parse_raw_trades(raw, target_tickers=target_tickers)
        save_events(events_df)
    else:
        events_df = load_dataframe("events.csv", directory=ROOT_DIR / "data" / "events")

    if events_df is None or events_df.empty:
        logger.error("❌ No events to process. Exiting.")
        return

    # ── ENRICH ─────────────────────────────────────────────────────────────
    if stage in [None, "enrich"]:
        logger.info("✨ Stage: Enrich events")
        events_df = enrich_events(events_df)
        save_events(events_df, filename="events_enriched.csv")

    # ── BACKTEST ───────────────────────────────────────────────────────────
    results_df = None
    baseline = {}
    if stage in [None, "backtest"]:
        logger.info("📊 Stage: Backtest")

        if hypothesis:
            events_df = filter_by_hypothesis(events_df, hypothesis)
            logger.info(f"🎯 Filtered for hypothesis: {hypothesis_name}")

        if events_df.empty:
            logger.warning("⚠️ No events match hypothesis. Skipping backtest.")
        else:
            horizons  = hypothesis.get("horizons", [5, 20, 60])
            benchmark = hypothesis.get("benchmark", "SPY")
            start_date = pd.to_datetime(events_df['event_date']).min().strftime("%Y-%m-%d")
            end_date   = pd.to_datetime(events_df['event_date']).max().strftime("%Y-%m-%d")

            prices_dfs = [
                df for ticker in events_df['ticker'].unique()
                if (df := fetch_prices(ticker, start_date, end_date, use_cache=use_cache)) is not None
            ]
            if not prices_dfs:
                logger.error("❌ No price data fetched. Exiting.")
                return

            prices_df    = pd.concat(prices_dfs, ignore_index=False)
            benchmark_df = fetch_benchmark(start_date, end_date, benchmark=benchmark, use_cache=use_cache)
            results_df   = calculate_returns(events_df, prices_df, benchmark_df, horizons=horizons)

            for ticker in results_df['ticker'].unique():
                bl = calculate_baseline(prices_df, ticker, horizons=horizons)
                baseline.update({f"{ticker}_{k}": v for k, v in bl.items()})

            save_dataframe(results_df, "backtest_results.csv", directory=OUTPUT_DIR)
            logger.info(f"✅ Backtest complete: {len(results_df)} events evaluated")

    # ── REPORT ─────────────────────────────────────────────────────────────
    if stage in [None, "report"]:
        logger.info("📄 Stage: Generate report")
        report_df = results_df if (results_df is not None and not results_df.empty) \
                    else load_dataframe("backtest_results.csv", directory=OUTPUT_DIR)

        if report_df is not None and not report_df.empty:
            report_text = generate_report(
                hypothesis_name or "default_test",
                report_df,
                baseline=baseline or None,
                config=hypothesis or {"min_sample_size": 10}
            )
            print_report(report_text)
        else:
            logger.warning("⚠️ No backtest results to report")

    logger.info("🏁 Pipeline complete")


def main():
    parser = argparse.ArgumentParser(description="Insider Event Study Pipeline")
    parser.add_argument("--stage", choices=["fetch", "parse", "enrich", "backtest", "report"])
    parser.add_argument("--tickers", nargs="+")
    parser.add_argument("--hypothesis")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    args = parser.parse_args()
    setup_logging(args.log_level)

    try:
        run_pipeline(
            stage=args.stage,
            tickers=args.tickers,
            hypothesis_name=args.hypothesis,
            use_cache=not args.no_cache
        )
    except KeyboardInterrupt:
        logging.warning("⚠️ Interrupted")
        sys.exit(130)
    except Exception as e:
        logging.error(f"❌ Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
