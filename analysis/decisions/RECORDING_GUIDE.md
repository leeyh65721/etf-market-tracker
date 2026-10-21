# Persist actual ETF research decisions (public-market-only)

**Scope:** structured record of actual dated ChatGPT research statements, NOT trades or the technical scanner's candidate list. Never publish individual account holdings, allocations, balances, cash, private investment P&L or trade orders to this public GitHub repo.

**Archive procedure for a daily/weekly run:**

1. Finish the Korean research answer; distinguish a market observation, watchlist idea, confirmed change in investment thesis, no-new-candidate outcome, or a conditional **public** market stance. Do not invent a buy/sell recommendation just to create a record.
2. Save the **exact public-only analysis** in `analysis/daily/YYYY-MM-DD.md` or `analysis/weekly/YYYY-MM-DD.md`, quoting facts and sources, US as-of session, Korea report date, counterevidence, original idea and falsifier. Verify that this exact file exists after writing through GitHub. A task-generated answer that fails saving is **not** an archived record.
3. For each meaningfully new *named ETF* interpretation, create ONE `analysis/decisions/entries/YYYY-MM-DD-TICKER-type.json`. Include its US market session, contemporaneously recorded adjusted close AND same-date SPY close from original `data/history/YYYY-MM-DD.csv`; the Korean report date, original report path, a **verbatim exact substring** from the report as its receipt, original thesis, counterevidence, invalidation and 5/10/20 NYSE-session revisit. Set `trade_instruction:false`; this is research, not an order. Copy actual report content; never fill unknown values from hindsight.
4. If there were genuinely **no newly validated ETF ideas**, a single `MARKET` record with `stance:"no_new_candidate"`, no price baselines and a verbatim text excerpt from that day's archived public report can preserve the negative decision **without inventing a ticker**.
5. `provenance:"contemporaneous_report"` is allowed ONLY if the report was archived when first reported (not recreated after knowing subsequent prices); use its true `archived_on_utc_date`. If the public copy was backed up later, use `provenance:"retrospective_archived_report"` and do not count it toward prospective hit rate. GitHub commit timestamps remain verifiable.
6. Immediately fetch and verify the newly created record and source; report archive failure explicitly, **do not claim it was saved**, and continue the investment explanation without fabricated performance.
7. GitHub Actions executes `decision_journal.py` every US trading session and writes `data/decisions/latest.json` and `analysis/decisions/ledger_latest.md`. Unindexed daily reports are warned; source mismatch, missing/rewritten thesis receipts or incorrect historical price baselines are flagged as errors by `system_health.py`. The research report itself is the source of judgment; automatic rank labels do not create these records.

**Example record structure** (placeholders only; do NOT publish as a real archive):

```json
{
  "schema": "public_etf_judgment_v1",
  "record_id": "2026-10-20-XLV-watch",
  "ticker": "XLV",
  "stance": "positive_watch",
  "us_market_date": "2026-10-20",
  "original_report_date_kst": "2026-10-21",
  "archived_on_utc_date": "2026-10-21",
  "provenance": "retrospective_archived_report",
  "source_report": "analysis/daily/2026-10-21.md",
  "verbatim_source_excerpt": "**XLV — 헬스케어 전반**",
  "original_close_usd": 179.82,
  "original_spy_close_usd": 769.05,
  "thesis": "Concrete original public research thesis, never guessed afterward",
  "counterevidence": "Concrete contrary public research with date and sources",
  "invalidation": "Observable event or price/evidence condition that falsifies this view",
  "revisit_trigger": "A dated plan to revisit after 5, 10 and 20 US sessions",
  "review_horizons_nyse_sessions": [5, 10, 20],
  "comparison_baseline": "SPY",
  "trade_instruction": false
}
```

This example references an **existing retrospectively archived** observation, not a freshly issued recommendation. Historical reports can help retrospective narrative assessment but cannot become previously demonstrated predictions.

**Missing-archive detection:** `decision_journal.py` checks every stored public daily report. If no structured entry references that report, the quality report flags it. This does **not** prove that unsaved ChatGPT messages have been recovered, nor can GitHub Actions archive absent conversations. The ChatGPT scheduled task is responsible for filing its actual public opinion immediately and reporting write failures.

