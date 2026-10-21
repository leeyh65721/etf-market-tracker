# Four-pillar ETF decision quality framework — 2026-10-21

> **Purpose:** improve the reproducibility, honesty and future assessment of existing ETF market research, not promise superior returns or automatically execute trades. Public repository contains no portfolio holdings, account balances, personally identified user risks or recommended account-specific allocation.

## 1. Economic release → ETF response: separate coexistence from causation

Machine source: `data/macro/latest.json` (22 official series) and `data/macro/extra_latest.json` (8 areas, 10 metrics), alongside `data/latest.csv` and dated price snapshots. Output: `data/links/latest.json`, `data/links/YYYY-MM-DD.json`, `analysis/links/latest.md` and `analysis/links/YYYY-MM-DD.md`.

- Only use the **exact prior NYSE trading session** for an adjacent ETF price comparison; missing data → unavailable, not extrapolated. USD provider-adjusted close is a research approximation, not a fill or perfect total return.
- For each macro observation record its actual **observation period**, source, previous observation and units; 10-year yield declines by 0.03 **percentage points**, not 3 percent. PCE/CPI YoY changes and GDP annualized changes must not be treated as the same basis. Stale/failed/manual-only series never become current numbers.
- The release **publication timestamp is not encoded** in most macro scanner rows. Two series with the same date did not necessarily become public at the same time. Thus the table says *co-observed*, not "Treasury yields caused tech to rise". Monthly and quarterly observation periods are especially remote from public announcement dates.
- Before ChatGPT asserts a catalyst, independently confirm the original release/publication time and market price window with a primary source and corroboration. Consider Fed policy, earnings and geopolitics as alternative explanations. Correlation does not establish causation.

## 2. Industry results and orders: primary evidence before sector-level thesis

Machine source: **manually verified and dated issuer SEC filings** in `data/industry/events/*.json`, validated by `industry_evidence.py`. Output: `data/industry/quality_latest.json`, `analysis/industry/latest.md`.

- Record issuer, ticker, business area, earnings period, filing/publication time, *preliminary vs final*, SEC exhibit URL, checked date, units, estimate range, strictly matched comparison basis, next verification and independent counterevidence.
- **Prior quarterly actual revenue**, **prior guidance for the same quarter**, **Wall Street consensus**, and **sequential growth** are FOUR DIFFERENT COMPARATORS and must never be interchanged. Price-return figures are separate again. Use percentage points for gross margins and % for comparable sales growth.
- Orders, shipments, cancellations, inventory, billings, bookings, CAPEX and backlog are different measures. The issuer must explicitly disclose a number before the analysis claims it changed. Say "not reported" rather than substituting revenue projections for orders.
- An announcement **after** the US stock-market close cannot be attributed to the just-completed regular-session price. `earliest_reaction_us_session` is a calendar-verified earliest possible response window, NOT an estimate of actual price impact.
- Company → sector → ETF is a **hypothesis requiring ETF actual constituent exposure and additional supplier/customer evidence**. Downstream AI-server guidance does not automatically confirm SOXX-wide semiconductor orders. Check competing company results, credit/FX/yield conditions, and contradictory results before a broad industry claim.
- The validator enforces syntax and provenance fields, not the factual truth of the public filing; ChatGPT must check the original SEC exhibit or an authorized official issuer release in every material decision. A later amendment should be recorded with new date and provenance, not rewrite earlier investment history.

## 3. Verify investment decisions and their failures without hindsight

Two ledgers are intentionally distinct:

- Mechanical screen: `signal_audit.py` freezes first-observed daily candidate transitions in `data/quality/snapshots/`, evaluates next-NYSE-session-close to 5/10/20 subsequent NYSE sessions, and compares with the same-window SPY proxy. This does **not** measure any recommended trade return, because rankings are not explicit investment recommendations.
- Actual research judgment: `analysis/daily/`, `analysis/events/` and any published `analysis/weekly/` should preserve first statement date (Korea and US session), issuer/ETF, **falsifiable thesis**, contemporaneous sources and corrections, downside/countercase, objective 5/10/20-NYSE-session revisit, and the decision **observe/maintain/rotate/reduce/no trade**. Do not write a new historical investment thesis after viewing its outcome.

On review: differentiate price direction vs SPY-relative performance; invalid original evidence vs unforeseen new event; false signal vs reasonable but unlucky realized outcome; preliminary vs final earnings revision; ignored counterevidence; late entry/overvaluation; sector overlap, liquidity or currency. Explicitly mark **pending**, **false/unverified**, **mixed**, **supported**, or **insufficient data** with counterfactual "what evidence would have changed the judgment?". Not all correct market narratives are profitable and not all winning short-term prices validate the stated thesis.

Do not report a prediction success percentage before enough forward outcomes mature; 30+ mechanical observations are still exploratory, may be correlated, and do not justify fine-tuning signal weights to a short recent sample. Compare against a naïve benchmark such as SPY and a hold/no-trade alternative.

## 4. ETF target allocations: private risk-aware, conditional proposals only

The publicly accessible GitHub project **must never store** actual investor holdings, specific allocation weights, amounts, net account returns, orders, currency conversions tied to the account, or real trades.

At weekly private ChatGPT report time:

1. Check latest consented personal holding weights **in private context** (or ask if needed). Validate freshness, USD→KRW sensitivity, underlying ETF shareholdings overlap, issuer cost, spread, taxes and market capacity. Do not substitute older weights as current.
2. Compare **A keep current**, **B rotate/add validated ETF**, **C reduce exposure/increase cash**, and the case for doing nothing. If evidence is inadequate, recommend no change; do not manufacture percentages.
3. Use the official macro 22 + supplemental 10 **quality statuses** and latest independent corporate/news evidence. Explain how each credible change alters growth, real rates, credit, earnings and discounted valuations. Include at least one plausible reason the preferred thesis could be wrong.
4. For any proposed change, state current→target percentages that add up to 100% **only in the private response**, proposed gradual execution trigger/horizon, reversal conditions, fees, FX and stress scenarios. Do not promise a hard maximum drawdown; ex-ante estimated risk from short historical windows is unstable.
5. Human user decides and manually executes; this project never initiates securities transactions.

**What is implemented now:** historical first-seen technical candidate preservation, source-date-safe macro/ETF movement comparisons, first verified SEC issuer industry evidence ledger, and a disciplined weekly allocation review procedure. **Not established:** a predictive alpha edge, causal ETF-return model, comprehensive auto-extraction of all company financials, reliable future industry-wide order signals, or a proven ability to keep actual portfolio drawdown below a chosen threshold.

