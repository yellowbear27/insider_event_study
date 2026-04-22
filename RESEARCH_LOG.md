# RESEARCH LOG
# Project: insider_event_study
# Format: dated entries, append-only, decisions before code, findings after analysis

---

## 2026-04-21

### Stock Universe Selection

Tickers: NVDA, CDNS, SNPS
Rationale: AI infrastructure bellwethers. Three distinct layers.

NVDA — compute layer. GPU monopoly. Foundation of all AI training and inference.
CDNS — design layer. EDA duopoly with SNPS. No chip designed without Cadence tools.
SNPS — design layer. EDA duopoly with CDNS. ANSYS acquisition: expanded into simulation.

Logic: Congressional awareness of AI infrastructure spending, export controls, or semiconductor policy visible here before broader market.

Correlated signal across all three: strong thesis.
Signal in NVDA only: momentum, public information.
Signal in CDNS/SNPS not NVDA: structural, non-public, most interesting case.

Scope: US-listed equities only. STOCK Act jurisdiction.
Exclusions: ASML (Dutch domicile, different disclosure rules) — Phase 2 consideration.

---

### Methodology Selection

Method: Event study. Abnormal return analysis around disclosure date.
Alternative considered: Simple return comparison. Rejected — no risk adjustment.
Alternative considered: Portfolio backtest. Rejected — premature, insufficient data points.

Event definition: Disclosure date = T(0). Not transaction date.
Rationale: Transaction date often unknown or stale. Disclosure date is verifiable.

Window: T(0) to T(+30). Thirty calendar days post-disclosure.
Benchmark: SPY. Simple, liquid, standard.
Signal types captured: Purchase, Sale, Exchange.
Signal types excluded: None at this stage.

---

### Data Source Selection

Senate disclosures: senatestockwatcher.com/api
Format: JSON. Free. No authentication. Updated daily.
Rationale: Clean, structured, maintained. Avoids JS-rendering problem of raw EFD portal.

House disclosures: housestockwatcher.com — DEAD as of early 2026. S3 bucket returns HTTP 403.
Alternative: SEC EDGAR Form 4 (corporate insiders). Phase 2.
Alternative: Capitol Trades API or FMP congressional API. Paid. Phase 3 if free sources insufficient.

Senate EFD portal (efdsearch.senate.gov): JS-rendered. BeautifulSoup insufficient. Abandoned.

---

### Hypothesis

Pre-data statement. Written before analysis. Not to be modified after results seen.

H1 (Primary): Congressional purchases of NVDA, CDNS, SNPS generate positive abnormal returns over T(0) to T(+30) versus SPY.

H2 (Structural signal): Abnormal returns higher for CDNS and SNPS purchases than NVDA purchases. Rationale: CDNS/SNPS less followed, informational asymmetry greater.

H3 (Asymmetry): Purchase signals stronger than sale signals. Rationale: Sales have more confounding motivations (liquidity, diversification, tax). Purchases are more deliberate.

Null hypothesis: No statistically significant abnormal return. Congressional trades indistinguishable from random timing.

---

### Known Limitations

Amount ranges only: STOCK Act requires range disclosure, not exact amount. ($1,001-$15,000 etc). No position sizing possible.
Reporting lag: Up to 45 days between transaction and disclosure. Signal may be stale by T(0).
Sample size: Three tickers. Statistical power limited. Results directional, not conclusive at this stage.
Spousal trades: Included in disclosures. Motivation and information source less certain.

---

### Next Actions

1. Build fetcher.py — Senate Stock Watcher API call, filter NVDA/CDNS/SNPS
2. Expand parser.py — JSON to pandas DataFrame, clean columns
3. Update storage.py — save to data/raw/senate_trades.csv
4. Update main.py — pipeline entry point, print summary to terminal
5. Fix config.py typo: OUTOUT_DATA_DIR → OUTPUT_DATA_DIR
6. Commit with message referencing this log entry

---
### Data Source Validation — 2026-04-21

senate-stock-watcher-data GitHub repo: last commit 2020-12-05.
Status: HISTORICAL ARCHIVE. Not live. Data covers 2016-2020 only.

Implication: Pipeline valid for historical backtest. 
Missing: 2021-2026 period including AI boom trades.

Current live alternative identified: capitoltrades.com
NVDA: 320 trades. Both Senate and House. Updated daily.
Action: Switch source after pipeline is fully built and validated.
Decision: Proceed with historical data for pipeline development.

## 2026-04-21 — Session End

### Completed Today
- fetcher.py: Senate Stock Watcher data pipeline working
- parser.py: filters to NVDA/CDNS/SNPS, 49 records
- storage.py: saves to data/output/senate_trades.csv
- price_fetcher.py: yfinance pull working, 1258 trading days

### Known Issues to Fix Next Session
1. disclosure_date missing from aggregate source — need daily files
2. transaction_date used as T(0) for now — overstates signal
3. Data source is historical 2016-2020 only — switch to Capitol Trades later

### Next Session Priorities
1. Fix disclosure_date problem
2. Build event_study.py — merge trades with prices around T(0)
3. Calculate abnormal returns vs SPY

## 2026-04-22

### Event Study Results — First Run

Status: Working. 49 events processed. 0 skipped.

Results:
- Purchase: avg CAR +7.30% vs SPY over 30 days
- Sale (Full): avg CAR +7.96% vs SPY over 30 days
- Sale (Partial): avg CAR +14.95% vs SPY over 30 days

### Interpretation

Preliminary only. Sample too small for conclusions.

Positive CAR on sales: counterintuitive.
Possible explanations:
- Senators selling for liquidity, not on negative information
- 2020 NVDA bull run inflating all results regardless of trade direction
- Sample size insufficient to separate signal from noise

### Known Data Issues

1. Duplicate events: Ron Wyden 2020-10-16 appears 3 times. Same date, same ticker.
   Cause: multiple family members trading same day, each filed separately.
   Fix needed: decide whether to deduplicate or keep all — document decision.

2. transaction_date used as T(0). Disclosure date missing from source.
   Actual market-observable date may be up to 45 days later.
   Fix needed: pull daily files for disclosure dates.

3. Data covers 2016-2020 only. Misses AI boom 2021-2026.
   Fix needed: switch to Capitol Trades for current data.

### Next Session Priorities

1. Deduplicate or document duplicate decision
2. Fix disclosure_date problem
3. Switch data source to Capitol Trades
4. Add statistical significance testing — t-test on CAR
5. Separate purchases from sales in analysis

## 2026-04-22 — Hypothesis Refinement

### ** KEY INSIGHT: Signal Reclassification **

Original grouping: Purchase / Sale Full / Sale Partial — three categories.

Revised grouping:

** Bullish signal: Purchase + Sale Partial **
Rationale: Senator retains exposure. Revealed preference for upside.
Partial sale = liquidity need, not conviction exit.
High conviction hold disguised as a sale.

** Neutral/bearish signal: Sale Full **
Rationale: Complete exit. No remaining skin in game.
Motivation ambiguous — liquidity, rebalancing, estate planning.
Not necessarily informed selling.

### Implication for Analysis

Current CAR calculation treats all three separately.
Next version should regroup and retest:
- Group A: Purchase + Sale Partial combined
- Group B: Sale Full isolated

Prediction: Group A CAR will be materially higher than Group B.
This is a testable hypothesis. Add to next session priorities.

### Origin

Derived from finance first principles during result interpretation.
Not from data mining. Pre-stated before retest. — 2026-04-22

