# Event-Driven Signal Hypothesis Engine

A Python framework for testing whether **discrete market events** (e.g. congressional trades) change the distribution of future returns.

---

## Objective

Answer a single question:

> Does a specific event provide a measurable edge in future price movement?

This project does **not** build a trading system.
It builds a **hypothesis testing engine**.

---

## Current Status

* Congressional trade ingestion: working
* Event parsing and enrichment: working
* Backtesting engine: working
* Hypothesis framework: partially implemented

### Known Issues

* `filing_date` mostly missing → event timing not reliable
* Current tests use transaction date (not ideal)
* Sample size small
* No statistical significance testing yet

---

## System Overview

### Data Sources (Free Only)

* Congressional trades (Senate disclosures)
* Price data via `yfinance`

---

### Pipeline

```text
raw data → parser → event table → backtest → report
```

---

### Event Schema

```text
ticker
event_date
filing_date
transaction_type
shares_before
shares_after
event_type
direction (always None at this stage)
source
```

---

### Event Types

```text
purchase
partial_sale
full_exit_sale
```

Derived:

```text
cluster_flag
cluster_size
```

---

## Key Design Principles

* Parser produces **facts only**
* Hypothesis layer assigns **interpretation**
* No narrative logic in code
* All signals must be testable
* Weekly iteration discipline

---

## Example Hypothesis

```yaml
hypothesis: purchase_bullish
event_type: purchase
expected_direction: bullish
horizons: [5, 20, 60]
min_sample_size: 10
```

---

## Output

Each test produces:

```text
mean return
median return
hit rate
sample size
baseline comparison
decision
```

Saved to:

```text
reports/
```

---

## How to Run (current)

Install dependencies:

```bash
pip install -r requirements.txt
```

Run pipeline (temporary entry point):

```bash
python main.py
```

(Note: entry script will be replaced with `scripts/run_hypothesis.py`)

---

## Limitations

* Event timing not yet correct (disclosure vs transaction)
* Congressional data is delayed and incomplete
* Small dataset → results exploratory only
* No cross-validation yet

---

## Roadmap

See:

```text
ROADMAP.md
```

---

## Non-Goals

* No trading bot
* No portfolio optimisation
* No news sentiment analysis
* No paid data (until edge is proven)

---

## License

MIT
