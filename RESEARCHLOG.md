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
