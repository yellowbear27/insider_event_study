# report/report_generator.py
"""Generate structured, reproducible reports per Phase 6 spec."""
import pandas as pd
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from config.settings import OUTPUT_DIR

logger = logging.getLogger(__name__)

def generate_report(hypothesis_name: str, results_df: pd.DataFrame, baseline: Optional[Dict[str, float]] = None, config: Optional[Dict[str, Any]] = None) -> str:
    lines = [f"Hypothesis: {hypothesis_name}", f"Generated: {datetime.now().isoformat()}", ""]
    tickers = results_df['ticker'].unique().tolist() if 'ticker' in results_df.columns else []
    lines += [f"Ticker/Universe: {tickers if tickers else 'N/A'}", f"Sample size: {len(results_df)}", ""]
    
    for horizon in [5, 20, 60]:
        ret_col, car_col = f'ret_{horizon}d', f'car_{horizon}d'
        if ret_col in results_df.columns:
            mean_ret = results_df[ret_col].mean()
            median_ret = results_df[ret_col].median()
            hit_rate = (results_df[ret_col] > 0).mean()
            lines += [f"{horizon}d:"]
            lines += [f"  mean return: {mean_ret:.2%}" if pd.notna(mean_ret) else "  mean return: N/A"]
            lines += [f"  median return: {median_ret:.2%}" if pd.notna(median_ret) else "  median return: N/A"]
            lines += [f"  hit rate: {hit_rate:.2%}" if pd.notna(hit_rate) else "  hit rate: N/A"]
            if car_col in results_df.columns:
                mean_car = results_df[car_col].mean()
                lines += [f"  mean CAR: {mean_car:.2%}" if pd.notna(mean_car) else "  mean CAR: N/A"]
            lines += [""]
    
    # FIX: Baseline keys may have ticker prefix (e.g., "NVDA_ret_20d_mean")
    if baseline:
        lines += ["Baseline (random non-event days):"]
        for horizon in [5, 20, 60]:
            # Try both key formats
            key1 = f'ret_{horizon}d_mean'
            key2 = f'*_{key1}'  # wildcard for ticker prefix
            baseline_val = baseline.get(key1)
            if baseline_val is None:
                # Find first matching key with ticker prefix
                for k, v in baseline.items():
                    if k.endswith(f'_{key1}'):
                        baseline_val = v
                        break
            if baseline_val is not None:
                lines += [f"  {horizon}d mean: {baseline_val:.2%}"]
        lines += [""]
    
    decision = _make_decision(results_df, baseline, config)
    lines += [f"Decision: {decision['label']}", f"Reason: {decision['reason']}", ""]
    lines += ["Notes:", f"- Min sample threshold: {config.get('min_sample_size', 'N/A') if config else 'N/A'}", f"- Confidence: {'low' if len(results_df) < 30 else 'medium' if len(results_df) < 100 else 'high'}"]
    
    report_text = "\n".join(lines)
    output_path = OUTPUT_DIR / f"report_{hypothesis_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(report_text)
    logger.info(f"📄 Report saved to: {output_path}")
    return report_text

def _make_decision(results_df: pd.DataFrame, baseline: Optional[Dict], config: Optional[Dict]) -> Dict[str, str]:
    min_n = config.get('min_sample_size', 10) if config else 10
    if len(results_df) < min_n:
        return {'label': 'inconclusive', 'reason': f'Sample size {len(results_df)} < minimum {min_n}'}
    
    horizon = 20
    ret_col = f'ret_{horizon}d'
    if ret_col not in results_df.columns:
        return {'label': 'inconclusive', 'reason': f'Missing return column: {ret_col}'}
    
    mean_ret = results_df[ret_col].mean()
    hit_rate = (results_df[ret_col] > 0).mean()
    
    # Get baseline with ticker-prefix handling
    baseline_mean = 0.0
    if baseline:
        key1 = f'ret_{horizon}d_mean'
        baseline_mean = baseline.get(key1, 0.0)
        if baseline_mean == 0.0:
            for k, v in baseline.items():
                if k.endswith(f'_{key1}'):
                    baseline_mean = v
                    break
    
    expected_dir = config.get('expected_direction', 'bullish') if config else 'bullish'
    
    if expected_dir == 'bullish':
        if hit_rate > 0.60 and mean_ret > baseline_mean:
            return {'label': 'keep', 'reason': f'Bullish hypothesis supported: hit rate {hit_rate:.1%} > 60% AND mean return {mean_ret:.2%} > baseline {baseline_mean:.2%}'}
        elif hit_rate < 0.40 or mean_ret < -abs(baseline_mean):
            return {'label': 'reject', 'reason': f'Bullish hypothesis contradicted: hit rate {hit_rate:.1%} < 40% OR mean return {mean_ret:.2%} < -baseline'}
    else:
        if hit_rate < 0.40 and mean_ret < baseline_mean:
            return {'label': 'keep', 'reason': f'Bearish hypothesis supported: hit rate {hit_rate:.1%} < 40% AND mean return {mean_ret:.2%} < baseline {baseline_mean:.2%}'}
        elif hit_rate > 0.60 or mean_ret > abs(baseline_mean):
            return {'label': 'reject', 'reason': f'Bearish hypothesis contradicted: hit rate {hit_rate:.1%} > 60% OR mean return {mean_ret:.2%} > +baseline'}
    
    return {'label': 'inconclusive', 'reason': f'Mixed signals: hit rate {hit_rate:.1%}, mean return {mean_ret:.2%} vs baseline {baseline_mean:.2%}'}

def print_report(report_text: str):
    print("\n" + "="*60 + "\n" + report_text + "\n" + "="*60 + "\n")
