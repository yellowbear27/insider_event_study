# report/report_generator.py
import pandas as pd
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from config.settings import OUTPUT_DIR

logger = logging.getLogger(__name__)


def generate_report(
    hypothesis_name: str,
    results_df: pd.DataFrame,
    baseline: Optional[Dict[str, float]] = None,
    config: Optional[Dict[str, Any]] = None
) -> str:
    tickers = results_df['ticker'].unique().tolist() if 'ticker' in results_df.columns else []
    n = len(results_df)
    min_n = config.get('min_sample_size', 10) if config else 10
    confidence = 'low' if n < 30 else 'medium' if n < 100 else 'high'
    decision = _make_decision(results_df, baseline, config)

    lines = [
        f"Hypothesis: {hypothesis_name}",
        f"Generated: {datetime.now().isoformat()}",
        f"Ticker/Universe: {tickers or 'N/A'}",
        f"Sample size: {n}",
        "",
    ]

    for h in [5, 20, 60]:
        ret_col = f'ret_{h}d'
        car_col = f'car_{h}d'
        if ret_col not in results_df.columns:
            continue
        col = results_df[ret_col].dropna()
        lines += [
            f"{h}d:",
            f"  mean return:   {col.mean():.2%}",
            f"  median return: {col.median():.2%}",
            f"  hit rate:      {(col > 0).mean():.2%}",
        ]
        if car_col in results_df.columns:
            lines.append(f"  mean CAR:      {results_df[car_col].mean():.2%}")
        lines.append("")

    if baseline:
        lines.append("Baseline (random non-event days):")
        for h in [5, 20, 60]:
            vals = [v for k, v in baseline.items() if k.endswith(f'ret_{h}d_mean')]
            if vals:
                lines.append(f"  {h}d mean: {sum(vals)/len(vals):.2%}")
        lines.append("")

    lines += [
        f"Decision: {decision['label']}",
        f"Reason:   {decision['reason']}",
        "",
        f"Min sample: {min_n} | Confidence: {confidence}",
    ]

    report_text = "\n".join(lines)

    output_path = OUTPUT_DIR / f"report_{hypothesis_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_text)
    logger.info(f"📄 Report saved to: {output_path}")

    return report_text


def _make_decision(
    results_df: pd.DataFrame,
    baseline: Optional[Dict],
    config: Optional[Dict]
) -> Dict[str, str]:
    min_n = config.get('min_sample_size', 10) if config else 10
    if len(results_df) < min_n:
        return {'label': 'inconclusive', 'reason': f'Sample too small ({len(results_df)} < {min_n})'}

    if 'ret_20d' not in results_df.columns:
        return {'label': 'inconclusive', 'reason': 'Missing ret_20d'}

    col = results_df['ret_20d'].dropna()
    mean_ret = col.mean()
    hit_rate = (col > 0).mean()

    bl_vals = [v for k, v in baseline.items() if k.endswith('ret_20d_mean')] if baseline else []
    baseline_mean = sum(bl_vals) / len(bl_vals) if bl_vals else 0.0

    direction = config.get('expected_direction', 'bullish') if config else 'bullish'

    if direction == 'bullish':
        if hit_rate > 0.55 and mean_ret > baseline_mean:
            return {'label': 'keep', 'reason': f'Hit rate {hit_rate:.1%} > 55%, return {mean_ret:.2%} > baseline {baseline_mean:.2%}'}
        if hit_rate < 0.45 or mean_ret < -abs(baseline_mean):
            return {'label': 'reject', 'reason': f'Hit rate {hit_rate:.1%} or return {mean_ret:.2%} contradicts bullish thesis'}
    else:
        if hit_rate < 0.45 and mean_ret < baseline_mean:
            return {'label': 'keep', 'reason': f'Hit rate {hit_rate:.1%} < 45%, return {mean_ret:.2%} < baseline {baseline_mean:.2%}'}
        if hit_rate > 0.55 or mean_ret > abs(baseline_mean):
            return {'label': 'reject', 'reason': f'Hit rate {hit_rate:.1%} or return {mean_ret:.2%} contradicts bearish thesis'}

    return {'label': 'inconclusive', 'reason': f'Mixed: hit rate {hit_rate:.1%}, return {mean_ret:.2%} vs baseline {baseline_mean:.2%}'}


def print_report(report_text: str):
    print("\n" + "="*60 + "\n" + report_text + "\n" + "="*60 + "\n")
