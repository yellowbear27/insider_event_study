# ROADMAP.md

## Project Objective

Build a **free-data, Python-based hypothesis testing engine** for event-driven market signals.

**Core principle:**

* Use **raw events (filings, trades, announcements)**
* Avoid **news, narratives, and lagging aggregates**
* Focus on **state detection (alignment vs conflict)**, not prediction

---

## System Architecture (Conceptual)

### Inputs

* Insider filings (Form 4)
* Politician trades (later phase)
* Price data (yfinance)

### Processing Layers

1. Event Construction (raw → structured)
2. State Mapping (signals → pressure/flow/constraint)
3. Hypothesis Testing (event → outcome)
4. Reporting (simple, consistent output)

---

## Phase 1 — Audit Existing Repo (IMMEDIATE)

### Objective

Stabilise and understand current insider trading pipeline.

### Tasks

* Review all files:

  * classify: `keep / refactor / delete / move`
* Identify:

  * data ingestion logic
  * event parsing logic
  * backtest logic
  * report logic
* Remove:

  * unused scripts
  * duplicate logic
  * experimental clutter

### Output

* Clean directory structure
* Clear understanding of current pipeline

---

## Phase 2 — Insider Data Pipeline (CORE)

### Objective

Create a robust insider event dataset

### Standard Event Table

Each row must contain:

```
ticker
event_date
filing_date
transaction_type
shares_before
shares_after
event_type
direction
source
```

### Event Types

```
insider_buy
partial_insider_sale
full_exit_sale
cluster_buy
```

### Rules

* Partial sale = reduced but not zero
* Full exit = position goes to zero
* Cluster = ≥ N insiders within T days

---

## Phase 3 — Code Separation

### Objective

Decouple system components

### Modules

```
data/
    insider_loader.py
    price_loader.py

events/
    insider_parser.py
    event_builder.py

backtest/
    engine.py

config/
    hypotheses.yaml

report/
    report_generator.py
```

### Rule

NO mixing of:

* data ingestion
* event logic
* backtesting
* reporting

---

## Phase 4 — Hypothesis Framework

### Objective

Make system configurable

### Example

```
hypothesis: partial_insider_sale_bullish
event_type: partial_insider_sale
expected_direction: bullish
horizons: [5, 20, 60]
```

### Constraint

* No hardcoded hypotheses
* All tests driven by config

---

## Phase 5 — Backtesting Engine

### Objective

Standardised evaluation

### For each event:

```
event_date → forward returns:
    5d
    20d
    60d
```

### Baseline

* Same ticker
* Non-event days

### Metrics

```
mean return
median return
hit rate
sample size
baseline comparison
```

---

## Phase 6 — Reporting

### Output Format

```
Hypothesis:
Ticker/Universe:
Sample size:

5d:
20d:
60d:

Baseline:
Hit rate:

Decision:
Notes:
```

### Rule

* No charts required initially
* No narrative interpretation

---

## Phase 7 — Validation & Sanity Checks

### Required Checks

* No future data leakage
* Correct event date alignment
* Missing price handling
* Sufficient sample size
* Outlier detection

---

## Phase 8 — Weekly Workflow (DISCIPLINE)

Every week:

```
1 hypothesis
1 backtest
1 report
1 decision
```

Decisions:

```
keep
reject
inconclusive
```

---

## Phase 9 — Reverse Analysis (CONTROLLED)

### Objective

Study large moves without overfitting

### Steps

1. Define big moves:

   * top 5% returns
2. Analyse signals BEFORE move
3. Compare with random periods
4. Extract candidate rules
5. Validate forward

---

## Phase 10 — Politician Data (AFTER STABILISATION)

### Sources

* Senate disclosure portal
* House Clerk disclosures

### Event Table

```
politician
chamber
filing_date
transaction_date
ticker
transaction_type
amount_band
committee_relevance
source
```

### First Hypotheses

```
politician_buying_bullish
domain_relevant_trade_stronger
```

---

## Phase 11 — External Proxies (TECH FOCUS)

### Objective

Add upstream signals (like Tianjin port analogy)

### Categories

* Compute demand (data centers, GPU demand)
* Supply chain (semiconductor flow)
* Constraints (capacity bottlenecks)
* Capital flow (capex announcements)

### Rule

Each proxy must map to:

```
pressure
flow
constraint
```

---

## Phase 12 — State System (WEATHER MODEL)

### Variables

```
Conflict (0/1)
Calm (0/1)
Catalyst (0/1)
```

### Interpretation

```
3/3 → volatility regime
alignment → trend regime
else → ignore
```

---

## Core Philosophy

* Binary signals
* Thresholded strength
* No narrative
* No overfitting
* Continuous testing

---

## Non-Goals (STRICT)

* No trading bot
* No portfolio optimisation
* No news sentiment analysis
* No deep AI reasoning layer
* No paid data (until proven edge)

---

## First Milestone

> Run a clean backtest of:
> **partial insider selling → forward returns**
> and produce a reproducible report

---

## End State (Long-Term)

A system that:

* Continuously ingests raw events
* Maps them into system state
* Identifies alignment vs conflict
* Outputs directional or volatility bias
* Evolves through weekly hypothesis testing
