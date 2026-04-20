# Insider & Congressional Trade Event Study

A quantitative event study framework analysing the price impact of insider and congressional trading disclosures on US equities.

---

## Overview

This repository implements a data pipeline that scrapes, parses, and analyses congressional and corporate insider trading disclosures against historical price data. The objective is to measure abnormal returns following disclosure events and evaluate whether disclosed trades carry statistically meaningful predictive signal.

The initial focus is on the semiconductor and AI infrastructure sector — specifically Cadence Design Systems, Synopsys, and Nvidia — where congressional trading activity is most likely to reflect genuine informational asymmetry rather than passive market exposure.

---

## Methodology

The system follows a standard event study design:

The disclosure date is treated as the event date (T=0). Price data is pulled for a defined window around each event. Abnormal returns are calculated against a benchmark (S&P 500 / SPY). Results are aggregated across events to identify cumulative abnormal return patterns.

The analysis addresses a straightforward empirical question: did buying when insiders or congresspersons bought outperform a passive index position over equivalent holding periods?

---

## Repository Structure

```
insider_event_study/
├── scraper.py        # Fetches disclosure filings from source
├── parser.py         # Extracts structured trade data from raw filings
├── storage.py        # Persists cleaned data to local store
├── config.py         # Tickers, date ranges, and parameter settings
├── main.py           # Pipeline entry point
├── data/
│   └── raw/          # Raw filing data (unprocessed)
├── requirements.txt
└── README.md
```

---

## Data Sources

Congressional disclosures: STOCK Act filings via House and Senate financial disclosure portals.

Corporate insider disclosures: SEC Form 4 filings via EDGAR.

Price history: Yahoo Finance via `yfinance`.

---

## Dependencies

```
pip install -r requirements.txt
```

Core dependencies: `requests`, `beautifulsoup4`, `pandas`, `yfinance`.

---

## Status

MVP — active development. Pipeline architecture is in place. Scraping and parsing modules are under active construction.

---

## Roadmap

Phase 1 — Data acquisition and cleaning (current)
Phase 2 — Price history integration and event window construction
Phase 3 — Abnormal return calculation and benchmarking
Phase 4 — Signal analysis and backtest framework
Phase 5 — Multi-ticker expansion and statistical aggregation

---

## License

MIT
