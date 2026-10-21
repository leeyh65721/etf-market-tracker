# ETF market decision journal (public market research only)

This folder is for **public market research**, not brokerage accounts, trades, personal holdings, portfolio amounts or account-level P&L. Do not record sensitive user information here.

## Data flow

- `data/latest.json`, `data/latest.csv`: latest daily screen (overwritten each run).
- `data/history/YYYY-MM-DD.json`, `data/history/YYYY-MM-DD.csv`: market-date snapshots saved by the scanner. Compare at least two distinct market dates; never treat a same-day rerun as a new trading session.
- `analysis/daily/YYYY-MM-DD.md`: material, sourced **daily opportunity research** (macro + cross-asset + industry + eligible ETFs). One file per *Korea reporting date*.
- `analysis/events/YYYY-MM-DD-HHMM-<short-id>.md`: **material new intraday events** ONLY; no entry required if there is no meaningful change.
- `analysis/weekly/YYYY-MM-DD.md`: public market regime assessment and evaluation of dated evidence. Weekly ChatGPT output may include private portfolio-weight recommendations, but **do not write those private weights to this public repo**.

## Daily research format

# Daily market research — YYYY-MM-DD KST
- Time checked (KST) and latest US trading session:
- Source freshness: GitHub files/market prices/news (separate what is verified from what is delayed or unknown)
- Macro: Fed, nominal/real yields and curve, CPI/PCE/PPI, employment, growth, PMIs, consumption, credit, liquidity
- Cross-asset: WTI/Brent oil, gas, gold, copper, USD and USD/KRW, bond spreads, volatility, global markets
- Corporate/industry: verified earnings, guidance, revisions, policy, supply chains, ETF flows (only if sourced)
- New or strengthened ETF candidates: ticker, reasons, dates, performance vs SPY, liquidity/structure check, counterarguments, invalidate conditions
- Weakened/discarded candidates:
- Newly changed information since previous report:
- Sources (specific URLs, timestamps):
- Limitations and unverified items:

Do **not** manufacture every data point in every report; cover material verified inputs, state gaps, and avoid implying a source was checked when it was not. Scanned candidates are not recommendations; exclude complex/illiquid products.

## Event entry format

- Event and original occurrence time (KST / market local)
- New evidence versus previous event/news
- Reliable source URLs and verification time
- Macro/cross-asset implications and sector/ETF transmission mechanism
- Counterargument and invalidation/monitoring conditions
- Urgency: does this genuinely justify reassessing before the weekly review?
- No personal holdings or precise portfolio percentages

Do not log hourly heartbeat, duplicate news, unchanged calls, or speculative shocks.

## Weekly workflow

1. Read the latest summary and dated market snapshots in `data/history/` for all sessions since last review, plus the current `latest.*`.
2. Read all available `analysis/daily/` and `analysis/events/` files from the week; **do not assume missing days were monitored**.
3. Independently verify current macro, cross-asset, industry fundamentals, ETF structure/AUM/fees/spreads, news and flow data via reliable sources.
4. Distinguish genuine regime changes from noise, recognize conflicting evidence, test alternatives, check concentration/correlation and drawdown risk.
5. In the private ChatGPT report only, compare the user's latest disclosed portfolio with alternatives. Recommend new 100% target weights **only if the evidence merits change**; otherwise explicitly recommend maintaining positions. User decides and executes trades.

## Storage and access limitations

Scheduled ChatGPT tasks can only persist research here **if their GitHub connection permits writing during the run**. If access fails, clearly report that the analysis wasn't saved. Never claim an event or daily report was durably recorded without successful read-after-write verification. The GitHub Actions price scanner cannot see ChatGPT's hourly/daily conclusions automatically; its date snapshots are a separate automated input.

Market data is approximate, delayed and third-party sourced. This project does not place orders and does not guarantee the user's maximum acceptable portfolio loss.

## Deterministic automatic archive (GitHub Actions fallback)

The GitHub Actions workflow runs `scan.py` and then `build_journal.py` to create `analysis/technical/YYYY-MM-DD.md` from the verified daily screen, including screen transitions versus the previous saved market date. This text is mechanically generated from historical CSV/JSON only; it is **not** the ChatGPT daily market narrative and **contains no independently verified macro/news**. `analysis/technical/` is written by GitHub Actions together with `data/`, bypassing the need for ChatGPT scheduled tasks to push commits. Scheduled Actions may be delayed or fail; verify the relevant file really exists.

Weekly analysis should read `analysis/technical/` first as the reliable record of ETF-screen changes, then any existing `analysis/daily/` and `analysis/events/` research, and perform a fresh independent macro, rates, oil, FX, credit, earnings and cross-asset review. Missing ChatGPT research must not be represented as saved; all private portfolio allocation judgment stays in ChatGPT, not in public GitHub.

## Automated macro evidence archive — 2026-10-21 expanded coverage

`macro_scan.py` runs in GitHub Actions after `scan.py` and `build_journal.py`.
The 2026-10-20 FRED graph downloader failed on all 18 requests and was retired. **Do not obtain archived ICE BofA credit OAS data from FRED:** the ICE indices have third-party reproduction restrictions. This repo never pretends ETF returns are actual OAS.

### Automatically attempted (22 series, 6 primary publishers)

| Publisher | Requested indicators |
|---|---|
| US Treasury | 2y, 10y nominal Treasury yields, 10y real Treasury yield, 10y−2y curve spread |
| BLS (public API) | headline CPI, core CPI, shelter CPI, unemployment rate, payrolls, labor participation, JOLTS job openings, private average hourly earnings, private weekly hours, producer price index |
| EIA | WTI and Brent **spot** oil |
| Cboe | VIX and VVIX **indices** |
| ECB | EUR/USD published reference quote and USD/KRW **derived by KRW-per-EUR divided by USD-per-EUR**; neither is a New York end-of-day FX quote |
| New York Fed | effective federal funds rate (EFFR) and secured overnight financing rate (SOFR); **neither equals an FOMC target range** |

These are *requested* inputs, not a claim that 22 were retrieved. Data from the official publishers may be delayed, revised, have differing publication days, or fail entirely. Sources are individually retried with bounded timeouts using at most four workers. The workflow's macro step is non-blocking so a provider failure will not stop the ETF scanner from saving its report.

### Credit-market proxy (not OAS)

If market-date-matching HYG, LQD and IEF rows exist in `data/latest.csv`, the scanner computes **5d and 21d percentage-point differences in ETF price returns**, HYG minus IEF and LQD minus IEF. These differ structurally from **HY and IG corporate yield spread indices or option-adjusted credit spreads**; duration, default risk, distributions, yield levels and portfolio exposures create bias. Do not use proxy returns as OAS percentages or assert spreads widened unless actual licensed yield-spread evidence is available.

### Persisted and still not automated

`data/macro/latest.json` and `data/macro/history/YYYY-MM-DD.json` contain values with their source URL, observation date, coverage, individual errors, status and proxy notes.
`data/macro/latest_nonempty.json` is the *last* report with nonzero data, potentially stale; check its date before use.
`analysis/macro/YYYY-MM-DD.md` contains mechanical conditional indicators only; it does **not** archive the assistant's independent investment analysis.

**Not in the automatic numeric archive:** direct HY/IG OAS spreads, FOMC target range, broad dollar index/DXY, core PCE, GDP, ISM manufacturing/services PMI, U.S. retail sales, weekly initial jobless claims, gold/copper/gas, comprehensive financial-conditions indices, corporate earnings, ETF flows, geopolitics. The daily and weekly ChatGPT research must investigate material changes independently via legitimate, timely primary sources or mark them unverified. Never infer "no change" merely from a missing record or empty series.

### Automatic quality monitoring after each scheduled scan

The scheduled `daily.yml` runs `macro_health.py` after macro collection and archives:
- `data/macro/health_latest.json`: machine-readable **OK / WARN / ERROR** assessment, category coverage, missing critical series, source errors, and generation timestamps.
- `analysis/diagnostics/macro-health-latest.md`: readable summary of coverage and detected problems.
- `analysis/diagnostics/history/YYYY-MM-DD.md`: same health report indexed by US market date, updated on same-date reruns.

The monitor validates the **22 expected indicator IDs**, internal reported counts and uniqueness, individual staleness labels, numeric/date/HTTPS source sanity, that the market date matches the ETF scanner, and that macro generation is not older than the relevant ETF scan. It flags missing critical indicators (Treasury rates, VIX, FX and EFFR) and emits GitHub Actions warnings plus the job summary. The health status is about **data availability**, not safety of the stock market or investment advice.

When macro collection fails, the ETF scan/archive remains available; missing data is marked WARN/ERROR rather than silently replaced by an earlier `latest_nonempty` snapshot. A GitHub Actions warning is **not automatically a ChatGPT push notification**. The assistant's daily/weekly reports should read the health JSON and describe the implications and missing evidence.

### Verification and data use

First verify that GitHub Actions produced new files with `requested_series_count=22`, compare `retrieved_series_count`, `current_series_count`, `errors`, `market_date`, and each observation date. A status of `partial` or `unavailable` requires explicit caution. The adjusted / unadjusted BLS series labels are included; some indices are levels, not inflation percentages. A CPI release-date check must be done separately; time-series observation month is **not** the publication date. No API subscription or generative model fee was added. No account holdings, cash, allocation or returns are saved in this public repository.

**Upstream pages:** [US Treasury](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml) · [BLS Public API](https://www.bls.gov/developers/api_signature_v2.htm) · [EIA Spot Oil](https://www.eia.gov/dnav/pet/pet_pri_spt_s1_d.htm) · [Cboe VIX history](https://www.cboe.com/tradable-products/vix/vix-historical-data) · [ECB euro reference exchange rates](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html) · [New York Fed markets API](https://markets.newyorkfed.org/static/docs/markets-api.html) · [ICE index distribution restrictions](https://fred.stlouisfed.org/series/BAMLH0A0HYM2).


## BEA PCE / GDP and Chicago Fed NFCI source repair (2026-10-21)

- **Core PCE:** the BEA chart lists most recent first. The parser previously reversed its two most recent months. It now selects the maximum reference month as current and the immediately preceding month as previous. Live verified **August 2026** at **+3.0% year-over-year** (released September 30); period date is not release date.
- **Real GDP:** BEA displays `Q2 2026 (3rd) | +2.2%`, which the former parser skipped because of the estimate qualifier. Parser now accepts advance/second/third estimates. Live verified **2026 Q2** **+2.2% annualized quarter-over-quarter** (third estimate; released September 30). Quarter reference stored as 2026-04-01.
- **NFCI:** confirmed Chicago Fed direct official CSV `https://www.chicagofed.org/~/media/publications/nfci/nfci-data-series-csv.csv` with validated columns `Friday_of_Week,NFCI,ANFCI`. However its **last available row was 2026-04-24 during the Oct 21 live test**, which is too old for weekly risk analysis. The institution's newer website drives its downloads through an API which **returned HTTP 403 for the GitHub-hosted runner's IP**. The repository must **keep NFCI marked stale**, never pretend this historical CSV is current. Evaluate a newly permitted publisher feed or ask the research report to consult the current official Chicago Fed release manually. Do not use IP/copyright circumvention or third-party mirrors without access approval.
- A standalone on-demand GitHub Actions workflow `macro-repair-check.yml` tests parser regressions and separately queries the three official source feeds. It can succeed with NFCI marked `stale` but must report that status explicitly.
- The existing **22-series** base macro health report remains separate and does not assert that the extra eight categories are fully available.

## 8 additional macro research categories (2026-10-21)

The daily workflow calls `macro_extra.py` **after** the already-validated 22 series. This is an independent, best-effort layer; errors do **not** change the trusted 22-series `data/macro/latest.json` or its health status.

| Category | Tracked series | Data source and limits |
|---|---|---|
| Core PCE inflation | CORE_PCE | U.S. BEA published YoY core-PCE rate, release chart; not a reconstructed PCE index |
| Initial unemployment claims | INITIAL_CLAIMS | Department of Labor Weekly Claims public PDF; seasonally-adjusted initial claims, week-end date |
| Retail sales | RETAIL_SALES | Census monthly **nominal** advance retail-and-food-service month-over-month change |
| Financial conditions | NFCI | Federal Reserve Bank of Chicago official CSV *if discoverable* from public data page |
| Manufacturing orders | MFG_NEW_ORDERS, DURABLE_NEW_ORDERS | Census monthly full M3 orders and advance durable goods monthly changes are distinct releases |
| Manufacturing/services PMI | ISM_MANUFACTURING, ISM_SERVICES | **manual/licensed only**: no automated ISM access, redistribution or archive of PMI values |
| Real GDP | REAL_GDP | BEA published quarterly real GDP annualized growth, revision-prone |
| Market participation | SP500_BREADTH | **S&P 500 constituent** daily advancers divided by stocks with validated price pairs. This is not NYSE breadth or all US-listed equities; unofficial Yahoo quotes and Wikipedia current symbols |

This adds **8 requested areas and 10 separately identified metrics** (manufacturing orders and PMI each have two). A metric status can be `ok`, `stale`, `unavailable`, or `manual`. Partial coverage is explicitly recorded; there is no assumption of 8/8 successful automatic collection. Not all public web sources are consistently machine-readable; changes to official web-page markup may temporarily make a metric unavailable rather than produce speculative values.

- `data/macro/extra_latest.json` = latest attempt and per-indicator source/status/value/observation date where supported.
- `data/macro/history/extra-YYYY-MM-DD.json` = dated attempt.
- `analysis/macro/extra-YYYY-MM-DD.md` = human-readable results, unavailable reasons and cautions.
- `tests/test_macro_extra.py` contains offline parser, date sanity and manual-only ISM checks.

Weekly research should integrate verified observations and explicitly mark anything unavailable; examine official ISM PMI reports through permitted human reading or an authorized license rather than scraping. Publication dates can differ from referenced month or week and official macro data may be revised. Independently verify ETF prices, company information, news and the source date before financial decisions.

Official source pages: [BEA core PCE](https://www.bea.gov/data/personal-consumption-expenditures-price-index-excluding-food-and-energy), [DOL unemployment claims](https://www.dol.gov/ui/data.pdf), [Census retail](https://www.census.gov/retail/sales.html), [Chicago Fed NFCI](https://www.chicagofed.org/research/data/nfci/current-data-aws), [Census manufacturing orders](https://www.census.gov/manufacturing/m3/current/index.html), [Census durable orders](https://www.census.gov/manufacturing/m3/adv/current/index.html), [ISM reports and restrictions](https://www.ismworld.org/footer/terms-of-use/), [BEA real GDP](https://www.bea.gov/data/gdp/gross-domestic-product).
