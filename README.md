# Insider & Congressional Trade Event Study

A quantitative event study framework measuring abnormal returns following congressional trading disclosures in US equities.

---

## Status

**MVP complete — 2026-04-22**

Full pipeline operational: fetch, parse, store, price pull, CAR calculation, results to CSV.

Data: 49 Senate disclosure events, 2016-2020. Tickers: NVDA, CDNS, SNPS.

Known limitations: historical data only (2016-2020), transaction date used as T(0), duplicate events not yet deduplicated. See RESEARCH_LOG.md for full detail.

---

## Key Finding

30-day Cumulative Abnormal Return vs SPY benchmark:

| Trade Type | Avg CAR |
|---|---|
| Purchase | +7.30% |
| Sale (Full) | +7.96% |
| Sale (Partial) | +14.95% |

Sample size insufficient for statistical conclusions. Directional only.

Hypothesis refinement: Sale Partial signals continued conviction — senator retains exposure while meeting liquidity needs. Purchase and Sale Partial should be grouped as bullish signals in next version. See RESEARCH_LOG.md.

---

## Overview

Congressional members are required to disclose stock transactions under the STOCK Act within 45 days of execution. This project treats each disclosure as an event, measures the stock's return against SPY over the subsequent 30 trading days, and calculates the Cumulative Abnormal Return (CAR) per event.

The hypothesis: congressional trades in strategic sectors reflect informational asymmetry not available to the public, producing measurable abnormal returns post-disclosure.

Initial universe: Nvidia (NVDA), Cadence Design Systems (CDNS), Synopsys (SNPS). Three layers of AI infrastructure — compute, EDA design, and EDA simulation. Sectors where congressional awareness of policy, export controls, and spending decisions is most likely to precede public information.

---

## Methodology

Event date: transaction disclosure date as T(0).
Window: T(0) to T(+30) trading days.
Benchmark: SPY (S&P 500 ETF).
Abnormal return: daily stock return minus daily SPY return.
CAR: cumulative sum of abnormal returns over the event window.

See RESEARCH_LOG.md for full hypothesis, data source decisions, and findings.

---

## Pipeline

fetcher.py        — pulls Senate disclosure JSON from GitHub archive
parser.py         — filters to target tickers, structures into DataFrame
storage.py        — saves cleaned trades to data/output/senate_trades.csv
price_fetcher.py  — pulls historical OHLCV prices via yfinance
event_study.py    — calculates CAR per event, saves to data/output/event_study_results.csv
config.py         — central configuration: tickers, URLs, file paths
main.py           — pipeline entry point for data acquisition

---

## Data Sources

Senate disclosures: timothycarambat/senate-stock-watcher-data (GitHub archive, 2016-2020).
Price history: Yahoo Finance via yfinance. Auto-adjusted for splits and dividends.
Benchmark: SPY fetched via yfinance.

Next version: Capitol Trades API for current data (2021-present).

---

## Roadmap

Phase 1 — Data acquisition and cleaning. **Complete.**
Phase 2 — Price history integration and event window construction. **Complete.**
Phase 3 — CAR calculation and benchmarking. **Complete.**
Phase 4 — Disclosure date fix, deduplication, statistical significance testing.
Phase 5 — Capitol Trades integration for current data.
Phase 6 — Signal reclassification: bullish group (Purchase + Sale Partial) vs neutral group (Sale Full).
Phase 7 — Multi-ticker expansion and cross-sector analysis.

---

## Dependencies

```bash
pip install -r requirements.txt
```

Core: pandas, numpy, requests, yfinance, beautifulsoup4, lxml.

---

## License

MIT
