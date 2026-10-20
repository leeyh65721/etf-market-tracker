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

## Automated macro evidence archive

GitHub Actions now runs macro_scan.py after the ETF technical scan. It retrieves a best-effort set of U.S. macro/cross-asset series from the free public FRED graph CSV download endpoints (the FRED API itself may require a key), and saves:
- data/macro/latest.json and data/macro/history/YYYY-MM-DD.json: source URLs, each indicator's observation date and latest/previous changes, coverage and missing data.
- analysis/macro/YYYY-MM-DD.md: plain-language **conditional interpretation prompts** for material changes in rates, oil, credit, VIX, USD and employment.

These files are mechanically generated. They are NOT ChatGPT's independent macro news analysis or verified explanations of causality. Missing/stale indicators stay flagged. The files contain NO account/portfolio/holding details. No new paid model or API is involved. Confirm each Actions run creates these files before claiming success.

Weekly ChatGPT research must read analysis/macro/ and data/macro/history/ in addition to data/history/, analysis/technical/, and any successfully saved analysis/daily/ and analysis/events/. Independently verify FRED data and the week's news, actual ETF flows, corporate earnings and forecasts, especially where news could contradict simple macro rules.
