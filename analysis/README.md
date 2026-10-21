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

### Verification and data use

First verify that GitHub Actions produced new files with `requested_series_count=22`, compare `retrieved_series_count`, `current_series_count`, `errors`, `market_date`, and each observation date. A status of `partial` or `unavailable` requires explicit caution. The adjusted / unadjusted BLS series labels are included; some indices are levels, not inflation percentages. A CPI release-date check must be done separately; time-series observation month is **not** the publication date. No API subscription or generative model fee was added. No account holdings, cash, allocation or returns are saved in this public repository.

**Upstream pages:** [US Treasury](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml) · [BLS Public API](https://www.bls.gov/developers/api_signature_v2.htm) · [EIA Spot Oil](https://www.eia.gov/dnav/pet/pet_pri_spt_s1_d.htm) · [Cboe VIX history](https://www.cboe.com/tradable-products/vix/vix-historical-data) · [ECB euro reference exchange rates](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html) · [New York Fed markets API](https://markets.newyorkfed.org/static/docs/markets-api.html) · [ICE index distribution restrictions](https://fred.stlouisfed.org/series/BAMLH0A0HYM2).
