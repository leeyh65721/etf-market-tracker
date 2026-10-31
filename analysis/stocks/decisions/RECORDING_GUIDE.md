# Public US common-stock judgment ledger — schema v1 (2026-10-31)

Separate from ETF `data/decisions/` and `analysis/decisions/entries/`. No personal holdings, account weights, cash, P&L or actual orders may be saved here.

1. Save a dated original public-only report in `analysis/stocks/weekly/YYYY-MM-DD.md` or `analysis/stocks/daily/YYYY-MM-DD.md`, then fetch it back.
2. Each genuinely new named stock observation becomes `analysis/stocks/decisions/entries/YYYY-MM-DD-TICKER-stance.json` after the original report exists. Fetch and verify each JSON. Never backdate or invent a buy signal.
3. Schema `public_stock_judgment_v1`: record_id, ticker, security_type=common_stock, stance (watch_only/watch_weaker/positive_watch/conditional_buy), us_market_date, original_report_date_kst, archived_on_utc_date, provenance (contemporaneous_report or retrospective_archived_report), source_report, verbatim_source_excerpt (exact substring), original_close_usd, original_spy_close_usd, source_price_url, thesis, counterevidence, invalidation, entry_trigger, trigger_status, trigger_validity, reference_price_timestamp, execution_verified=false, trade_instruction=false, target_and_stop_basis, review_horizons_nyse_sessions=[1,3,5,10,20], comparison_baseline=SPY, evaluation_status=pending.
4. No observed intraday trigger data -> `trigger_status:unverified_not_triggered` and `watch_only`; no pretend fill or hit rate. Distinguish idea, triggered signal, executable signal, actual user trade. MAE/MFE, ATR, costs and 1/3/5/10/20 SPY excess returns remain pending/unverifiable until same-window verified OHLCV and realistic execution data exist.
5. Earnings must cite issuer IR or SEC with release date/time; missing valuation, dilution, liquidity/spread or full sector overlap is explicitly flagged. Distinguish original forward assessment from later recovery.
6. ETF and stock scorecards and denominators never combine. Existing ETF journal and schemas remain unchanged.
