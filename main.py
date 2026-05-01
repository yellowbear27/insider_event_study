#!/usr/bin/env python3
# main.py
"""Pipeline orchestrator for event-driven signal hypothesis testing."""

import argparse
import logging
import sys
from typing import Any, Dict, List, Optional

import pandas as pd
import yaml

from backtest.engine import calculate_baseline, calculate_returns
from config.settings import OUTPUT_DIR, ROOT_DIR
from data.congress_loader import fetch_senate_trades, load_raw_trades, save_raw_trades
from data.price_loader import fetch_benchmark, fetch_prices
from data.storage import load_dataframe, save_dataframe
from events.congress_parser import parse_raw_trades, save_events
from events.event_builder import enrich_events, filter_by_hypothesis
from report.report_generator import generate_report, make_decision, print_report


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
    print_full_report: bool = True,
) -> Optional[Dict[str, Any]]:
    """Run the event-study pipeline for one hypothesis."""
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
            return None

    # PARSE
    if stage in [None, "parse"]:
        logger.info("Stage: parse events")

        raw = raw_data or load_raw_trades()

        if not raw:
            logger.error("No raw data available for parsing. Exiting.")
            return None

        events_df = parse_raw_trades(raw, target_tickers=target_tickers)
        save_events(events_df)
    else:
        events_df = load_dataframe("events.csv", directory=ROOT_DIR / "data" / "events")

    if events_df is None or events_df.empty:
        logger.error("No events available. Exiting.")
        return None

    # ENRICH
    if stage in [None, "enrich"]:
        logger.info("Stage: enrich events")

        events_df = enrich_events(events_df)
        save_events(events_df, filename="events_enriched.csv")

    # BACKTEST
    results_df = None
    baseline: Dict[str, float] = {}

    if stage in [None, "backtest"]:
        logger.info("Stage: backtest")

        if hypothesis:
            events_df = filter_by_hypothesis(events_df, hypothesis)
            logger.info("Filtered for hypothesis: %s", hypothesis_name)

        if events_df.empty:
            logger.warning("No events match hypothesis. Skipping backtest.")
            return {
                "hypothesis": hypothesis_name or "default_test",
                "sample_size": 0,
                "ret_20d_mean": None,
                "hit_20d": None,
                "baseline_20d": None,
                "decision": "inconclusive",
                "reason": "No matching events",
            }

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
            return None

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

        output_name = f"backtest_results_{hypothesis_name or 'default'}.csv"
        save_dataframe(results_df, output_name, directory=OUTPUT_DIR)

        logger.info("Backtest complete: %s events evaluated", len(results_df))

    # REPORT
    if stage in [None, "report"]:
        logger.info("Stage: report")

        report_df = results_df

        if report_df is None or report_df.empty:
            report_df = load_dataframe("backtest_results.csv", directory=OUTPUT_DIR)

        if report_df is None or report_df.empty:
            logger.warning("No backtest results available for report")
            return None

        report_text = generate_report(
            hypothesis_name or "default_test",
            report_df,
            baseline=baseline or None,
            config=hypothesis or {"min_sample_size": 10},
        )

        if print_full_report:
            print_report(report_text)

        summary = build_summary_row(
            hypothesis_name=hypothesis_name or "default_test",
            results_df=report_df,
            baseline=baseline,
            config=hypothesis or {"min_sample_size": 10},
        )

        logger.info("Pipeline complete")
        return summary

    logger.info("Pipeline complete")
    return None


def run_all_hypotheses(
    tickers: Optional[List[str]] = None,
    use_cache: bool = True,
) -> None:
    """Run all configured hypotheses and print compact summary."""
    hypotheses_cfg = load_config("hypotheses")
    hypotheses = hypotheses_cfg.get("hypotheses", {})

    if not hypotheses:
        print("No hypotheses found in config/hypotheses.yaml")
        return

    rows = []

    for hypothesis_name in hypotheses:
        row = run_pipeline(
            stage=None,
            tickers=tickers,
            hypothesis_name=hypothesis_name,
            use_cache=use_cache,
            print_full_report=False,
        )

        if row:
            rows.append(row)

    print_summary_table(rows)


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


def build_summary_row(
    hypothesis_name: str,
    results_df: pd.DataFrame,
    baseline: Dict[str, float],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """Build one compact summary row for terminal display."""
    returns_20d = results_df["ret_20d"].dropna() if "ret_20d" in results_df else pd.Series()

    decision = make_decision(
        results_df=results_df,
        baseline=baseline,
        config=config,
    )

    return {
        "hypothesis": hypothesis_name,
        "sample_size": len(results_df),
        "ret_20d_mean": returns_20d.mean() if not returns_20d.empty else None,
        "hit_20d": (returns_20d > 0).mean() if not returns_20d.empty else None,
        "baseline_20d": baseline_mean(baseline, 20),
        "decision": decision["label"],
        "reason": decision["reason"],
    }


def baseline_mean(baseline: Dict[str, float], horizon: int) -> Optional[float]:
    """Average baseline values across tickers for one horizon."""
    suffix = f"ret_{horizon}d_mean"
    values = [value for key, value in baseline.items() if key.endswith(suffix)]

    if not values:
        return None

    return sum(values) / len(values)


def print_summary_table(rows: List[Dict[str, Any]]) -> None:
    """Print compact all-hypotheses summary."""
    if not rows:
        print("No hypothesis results.")
        return

    print()
    print("Hypothesis Summary")
    print("=" * 86)
    print(
        f"{'Hypothesis':<24} "
        f"{'N':>5} "
        f"{'20d Mean':>10} "
        f"{'20d Hit':>10} "
        f"{'Baseline':>10} "
        f"{'Decision':>14}"
    )
    print("-" * 86)

    for row in rows:
        print(
            f"{row['hypothesis']:<24} "
            f"{row['sample_size']:>5} "
            f"{format_pct(row['ret_20d_mean']):>10} "
            f"{format_pct(row['hit_20d']):>10} "
            f"{format_pct(row['baseline_20d']):>10} "
            f"{row['decision']:>14}"
        )

    print("=" * 86)
    print()


def format_pct(value: Optional[float]) -> str:
    """Format float as percentage or N/A."""
    if value is None or pd.isna(value):
        return "N/A"

    return f"{value:.2%}"


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
    parser.add_argument("--all-hypotheses", action="store_true")
    parser.add_argument("--no-cache", action="store_true")

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )

    args = parser.parse_args()
    setup_logging(args.log_level)

    try:
        if args.all_hypotheses:
            run_all_hypotheses(
                tickers=args.tickers,
                use_cache=not args.no_cache,
            )
            return

        run_pipeline(
            stage=args.stage,
            tickers=args.tickers,
            hypothesis_name=args.hypothesis,
            use_cache=not args.no_cache,
            print_full_report=True,
        )

    except KeyboardInterrupt:
        logging.warning("Interrupted")
        sys.exit(130)

    except Exception as error:
        logging.error("Pipeline failed: %s", error, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
