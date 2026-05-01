# ROADMAP.md

## 1. Objective

Build a **free-data, Python-based hypothesis testing engine** for event-driven signals.

The system answers:

> Does a specific event change future return distribution?

---

## 2. Design Principles

* Use **raw events**, not news
* Separate:

  * data ingestion
  * event construction
  * hypothesis interpretation
* No narrative logic in code
* All signals are **testable hypotheses**
* Weekly iteration is mandatory

---

## 3. Current State (Reality Check)

✔ Congressional trade ingestion works
✔ Event parsing works
✔ Basic backtest exists

✘ Naming was inconsistent (fixed)
✘ Parser incorrectly assigned direction (fixed)
✘ Event date integrity weak (filing_date mostly missing)
✘ Repo entry point (`main.py`) still fragile

---

## 4. System Architecture

### Data Sources (Free Only)

* Congressional trades (current)
* Price data (`yfinance`)
* Corporate insider (SEC Form 4) — later

---

### Pipeline

```text
raw data → parser → event table → backtest → report
```

---

### Standard Event Schema

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

### Event Types (current)

```text
purchase
partial_sale
full_exit_sale
```

Derived:

```text
cluster_flag (True/False)
cluster_size (int)
```

---

## 5. Phase 1 — Stabilise Core (NOW)

### Goal

Make current pipeline reliable and consistent.

### Tasks

1. Fix naming (done)
2. Remove direction from parser (done)
3. Ensure all modules compile (done)
4. Clean imports (done)

### Remaining

* Standardise entry script (`scripts/run_hypothesis.py`)
* Ensure one command runs full pipeline
* Verify no silent failures

---

## 6. Phase 2 — Backtest Integrity (CRITICAL)

### Problem

Event timing is incorrect.

### Rule

```text
event_date = when information becomes public
```

Not:

```text
transaction_date
```

### Tasks

* Audit availability of `filing_date`
* If missing:

  * mark events as low confidence
  * or exclude
* Document assumption clearly

---

## 7. Phase 3 — Hypothesis Framework

### Goal

All logic driven by config, not code.

### Example

```yaml
hypothesis: purchase_bullish
event_type: purchase
expected_direction: bullish
horizons: [5, 20, 60]
min_sample_size: 10
```

### Rules

* Parser produces facts
* Hypothesis assigns meaning

---

## 8. Phase 4 — Backtesting Engine

### Inputs

* Event table
* Price series

### Output

```text
mean return
median return
hit rate
sample size
baseline comparison
```

### Constraint

* No randomness unless seeded
* No data leakage

---

## 9. Phase 5 — Reporting

Each run produces:

```text
Hypothesis:
Sample size:
5d / 20d / 60d:
Baseline:
Decision:
```

Saved in:

```text
reports/
```

---

## 10. Phase 6 — Weekly Workflow

Every week:

```text
1 hypothesis
1 test
1 report
1 decision
```

Decisions:

```text
keep
reject
inconclusive
```

---

## 11. Phase 7 — Signal Expansion

After core is stable:

### Add:

* Corporate insider (SEC Form 4)
* More congressional filters

  * committee relevance
  * size thresholds

### Then:

* Conflict signals
* Volatility hypotheses

---

## 12. Phase 8 — Reverse Analysis

### Goal

Understand large moves without overfitting

### Steps

1. Define large move
2. Look backward at signals
3. Compare with random periods
4. Extract candidate rules
5. Validate forward

---

## 13. Phase 9 — External Proxies (Later)

Add upstream signals:

* compute demand
* semiconductor flow
* capex trends

Mapped to:

```text
pressure
flow
constraint
```

---

## 14. Non-Goals

* No trading bot
* No portfolio optimisation
* No news sentiment
* No AI swarm system
* No paid data (yet)

---

## 15. Immediate Next Task

> Run one clean hypothesis end-to-end using congressional data

Example:

```text
purchase → forward returns
```

Output a reproducible report.

---

## 16. End State

A system that:

* ingests raw events
* builds structured signals
* tests hypotheses continuously
* identifies:

  * directional bias
  * volatility regimes
* evolves weekly
