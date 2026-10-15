# ETF Market Tracker

Free **best-effort** technical screen of US-listed ETFs. Public market data only; **no brokerage access** or personal portfolio records.

## What is screened?
- [universe.txt](universe.txt) has a starting list of 353 US-listed ticker symbols.
- [scan.py](scan.py) retrieves up to 9 months of split/dividend-adjusted daily prices and share volumes via unofficial `yfinance` / Yahoo Finance data.
- Computes 5-, 21-, 63-trading-day returns, relative 21-day performance vs SPY, 20/50-day price trends and volume information.
- Requires at least 65 valid trading observations and the same latest market date as SPY. Invalid/unavailable data is **not** counted as analyzed.

## Additional trading-safety screens

To become a **technical candidate**, a fund needs all of:
- 20-day average daily **dollar trading volume ≥ $5 million**;
- 20-day median daily dollar trading volume ≥ $2 million (resists one-day volume spikes);
- 20-day average **daily shares traded ≥ 50,000**;
- positive 21-day excess return versus SPY, 20-day average price trend rising and last close above 50-day average;
- not among explicitly excluded structurally complex products or non-sector comparison funds.

Explicitly listed crypto/commodity-futures products are excluded from recommendation candidates. Country, broad-market, bond and bullion ETFs are tracked separately as non-sector comparisons. This is not a comprehensive security classification: **before recommending any ETF, independently check its legal structure (especially leverage, inverse, ETNs, derivative-based products), issuer, assets under management, expense ratio, age, spread/market depth and delisting risk.** The scanner does not verify these attributes.

Thinly traded and complex instruments remain in `data/latest.csv` for auditability, marked by `screen`: `excluded_illiquid`, `excluded_complex`, `watch_non_sector`, `watch` or `candidate`. **Never recommend excluded funds simply because their return is high.**

## Automatically produced files
- [data/latest.csv](data/latest.csv): full price-validated screen, trading-liquidity statistics and exclusion label for each processed ticker.
- [data/latest.json](data/latest.json): collection date, universe size, valid screen count, pass/exclusion counts, screening threshold definitions, and a limited candidate list.

The [daily workflow](.github/workflows/daily.yml) is scheduled weekdays 23:30 UTC (08:30 Korea time the next day), but GitHub scheduled execution can be delayed.

## Run and inspect
Open **Actions → Daily ETF market scan → Run workflow**. Once it succeeds, inspect `data/latest.json` and `data/latest.csv`. Verify `generated_at_utc`, the market date and the actual number of symbols processed.

**Limitations:** unofficial Yahoo data can be missing, stale or rate-limited; no real-time execution or guaranteed 300+ symbols. These statistics do not establish fund inflows, valuations, forward earnings, spread, fund size, or expected return; validate news, holdings and financials independently. USD returns ignore USD/KRW currency movements. ChatGPT reports depend on separate task configuration and must verify they can read these files.

**Costs:** workflow uses standard GitHub hosted runner, open-source Python and unofficial free price downloads. Monitor any usage limits; do not enable paid services or upload personal holdings, passwords, keys, or brokerage records.
