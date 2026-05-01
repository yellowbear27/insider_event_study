# report/report_generator.py
"""Generate plain-text reports for hypothesis backtests."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from config.settings import OUTPUT_DIR

logger = logging.getLogger(__name__)

DEFAULT_HORIZONS = [5, 20, 60]


def generate_report(
    hypothesis_name: str,
    results_df: pd.DataFrame,
    baseline: Optional[Dict[str, float]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate and save a text report for a hypothesis result."""
    config = config or {}
    baseline = baseline or {}

    tickers = _get_tickers(results_df)
    sample_size = len(results_df)
    min_sample_size = config.get("min_sample_size", 10)
    confidence = _confidence_label(sample_size)

    decision = make_decision(
        results_df=results_df,
        baseline=baseline,
        config=config,
    )

    lines = [
        f"Hypothesis: {hypothesis_name}",
        f"Generated: {datetime.now().isoformat()}",
        f"Ticker/Universe: {tickers or 'N/A'}",
        f"Sample size: {sample_size}",
        "",
    ]

    lines.extend(_horizon_summary_lines(results_df, DEFAULT_HORIZONS))

    if baseline:
        lines.extend(_baseline_lines(baseline, DEFAULT_HORIZONS))

    lines.extend(
        [
            f"Decision: {decision['label']}",
            f"Reason:   {decision['reason']}",
            "",
            f"Min sample: {min_sample_size} | Confidence: {confidence}",
        ]
    )

    report_text = "\n".join(lines)
    _save_report(report_text, hypothesis_name)

    return report_text


def make_decision(
    results_df: pd.DataFrame,
    baseline: Dict[str, float],
    config: Dict[str, Any],
) -> Dict[str, str]:
    """Return keep/reject/inconclusive decision for the hypothesis."""
    min_sample_size = config.get("min_sample_size", 10)

    if len(results_df) < min_sample_size:
        return {
            "label": "inconclusive",
            "reason": f"Sample too small ({len(results_df)} < {min_sample_size})",
        }

    if "ret_20d" not in results_df.columns:
        return {
            "label": "inconclusive",
            "reason": "Missing ret_20d",
        }

    returns = results_df["ret_20d"].dropna()

    if returns.empty:
        return {
            "label": "inconclusive",
            "reason": "No valid 20d returns",
        }

    mean_return = returns.mean()
    hit_rate = (returns > 0).mean()
    baseline_mean = _baseline_mean(baseline, horizon=20)

    expected_direction = config.get("expected_direction", "bullish")

    if expected_direction == "bullish":
        return _bullish_decision(hit_rate, mean_return, baseline_mean)

    if expected_direction == "bearish":
        return _bearish_decision(hit_rate, mean_return, baseline_mean)

    return {
        "label": "inconclusive",
        "reason": f"Unknown expected_direction: {expected_direction}",
    }


def print_report(report_text: str) -> None:
    """Print report with separators."""
    print("\n" + "=" * 60)
    print(report_text)
    print("=" * 60 + "\n")


def _horizon_summary_lines(results_df: pd.DataFrame, horizons: List[int]) -> List[str]:
    """Build return summary lines for each horizon."""
    lines = []

    for horizon in horizons:
        ret_col = f"ret_{horizon}d"
        car_col = f"car_{horizon}d"

        if ret_col not in results_df.columns:
            continue

        returns = results_df[ret_col].dropna()

        if returns.empty:
            lines.extend(
                [
                    f"{horizon}d:",
                    "  no valid returns",
                    "",
                ]
            )
            continue

        lines.extend(
            [
                f"{horizon}d:",
                f"  mean return:   {returns.mean():.2%}",
                f"  median return: {returns.median():.2%}",
                f"  hit rate:      {(returns > 0).mean():.2%}",
            ]
        )

        if car_col in results_df.columns:
            car_values = results_df[car_col].dropna()
            if not car_values.empty:
                lines.append(f"  mean CAR:      {car_values.mean():.2%}")

        lines.append("")

    return lines


def _baseline_lines(baseline: Dict[str, float], horizons: List[int]) -> List[str]:
    """Build deterministic baseline summary lines."""
    lines = ["Baseline (deterministic non-event days):"]

    for horizon in horizons:
        mean_value = _baseline_mean(baseline, horizon)

        if mean_value is not None:
            lines.append(f"  {horizon}d mean: {mean_value:.2%}")

    lines.append("")

    return lines


def _baseline_mean(baseline: Dict[str, float], horizon: int) -> Optional[float]:
    """Average baseline values across tickers for a horizon."""
    suffix = f"ret_{horizon}d_mean"
    values = [value for key, value in baseline.items() if key.endswith(suffix)]

    if not values:
        return None

    return sum(values) / len(values)


def _bullish_decision(
    hit_rate: float,
    mean_return: float,
    baseline_mean: Optional[float],
) -> Dict[str, str]:
    """Decision rule for bullish hypotheses."""
    baseline_value = baseline_mean if baseline_mean is not None else 0.0

    if hit_rate > 0.55 and mean_return > baseline_value:
        return {
            "label": "keep",
            "reason": (
                f"Hit rate {hit_rate:.1%} > 55%, "
                f"return {mean_return:.2%} > baseline {baseline_value:.2%}"
            ),
        }

    if hit_rate < 0.45 or mean_return < -abs(baseline_value):
        return {
            "label": "reject",
            "reason": (
                f"Hit rate {hit_rate:.1%} or return {mean_return:.2%} "
                "contradicts bullish thesis"
            ),
        }

    return {
        "label": "inconclusive",
        "reason": (
            f"Mixed: hit rate {hit_rate:.1%}, "
            f"return {mean_return:.2%} vs baseline {baseline_value:.2%}"
        ),
    }


def _bearish_decision(
    hit_rate: float,
    mean_return: float,
    baseline_mean: Optional[float],
) -> Dict[str, str]:
    """Decision rule for bearish hypotheses."""
    baseline_value = baseline_mean if baseline_mean is not None else 0.0

    if hit_rate < 0.45 and mean_return < baseline_value:
        return {
            "label": "keep",
            "reason": (
                f"Hit rate {hit_rate:.1%} < 45%, "
                f"return {mean_return:.2%} < baseline {baseline_value:.2%}"
            ),
        }

    if hit_rate > 0.55 or mean_return > abs(baseline_value):
        return {
            "label": "reject",
            "reason": (
                f"Hit rate {hit_rate:.1%} or return {mean_return:.2%} "
                "contradicts bearish thesis"
            ),
        }

    return {
        "label": "inconclusive",
        "reason": (
            f"Mixed: hit rate {hit_rate:.1%}, "
            f"return {mean_return:.2%} vs baseline {baseline_value:.2%}"
        ),
    }


def _get_tickers(results_df: pd.DataFrame) -> List[str]:
    """Return unique tickers in stable sorted order."""
    if "ticker" not in results_df.columns:
        return []

    return sorted(results_df["ticker"].dropna().unique().tolist())


def _confidence_label(sample_size: int) -> str:
    """Simple confidence label based on sample size."""
    if sample_size < 30:
        return "low"

    if sample_size < 100:
        return "medium"

    return "high"


def _save_report(report_text: str, hypothesis_name: str) -> None:
    """Save report text to reports/output directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"report_{hypothesis_name}_{timestamp}.txt"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_text)

    logger.info("Report saved to: %s", output_path)
