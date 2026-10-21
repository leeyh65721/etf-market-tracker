# Official macro source smoke-test diagnostic

- Checked at UTC: 2026-10-21T02:20:31.738598+00:00
- Offline parser test outcome: success
- Macro collection process outcome: success
- Coverage health process outcome: success
- Requested series: 22
- Retrieved series: 22
- Current series: 22
- Overall report status: ok
- Market date: 2026-10-20

## Per-series results
- T2Y : ok (2026-10-20)
- T10Y : ok (2026-10-20)
- T10Y_REAL : ok (2026-10-20)
- T10Y2Y : ok (2026-10-20)
- CPI_HEADLINE : ok (2026-09-01)
- CPI_CORE : ok (2026-09-01)
- UNRATE : ok (2026-09-01)
- PAYROLLS : ok (2026-09-01)
- PPI_FD : ok (2026-09-01)
- WTI : ok (2026-10-14)
- BRENT : ok (2026-10-14)
- VIX : ok (2026-10-20)
- VVIX : ok (2026-10-20)
- USD_KRW_ECB : ok (2026-10-20)
- EUR_USD_ECB : ok (2026-10-20)
- EFFR : ok (2026-10-19)
- SOFR : ok (2026-10-19)
- JOLTS_OPENINGS : ok (2026-08-01)
- LFPR : ok (2026-09-01)
- AVG_HOURLY_EARNINGS : ok (2026-09-01)
- AVG_WEEKLY_HOURS : ok (2026-09-01)
- CPI_SHELTER : ok (2026-09-01)

## Source errors

## Offline unit test log

```text
test_empty_data_error (test_macro_health.MacroHealthTests.test_empty_data_error) ... ok
test_full_coverage_is_ok (test_macro_health.MacroHealthTests.test_full_coverage_is_ok) ... ok
test_market_date_mismatch_warning (test_macro_health.MacroHealthTests.test_market_date_mismatch_warning) ... ok
test_partial_is_warning (test_macro_health.MacroHealthTests.test_partial_is_warning) ... ok
test_stale_generation_warning (test_macro_health.MacroHealthTests.test_stale_generation_warning) ... ok
test_stale_record_warning_even_when_complete (test_macro_health.MacroHealthTests.test_stale_record_warning_even_when_complete) ... ok
test_cboe_parses_daily_close (test_macro_scan.MacroParserSmokeTests.test_cboe_parses_daily_close) ... ok
test_cboe_single_value_column (test_macro_scan.MacroParserSmokeTests.test_cboe_single_value_column) ... ok
test_credit_etf_proxies_are_not_oas (test_macro_scan.MacroParserSmokeTests.test_credit_etf_proxies_are_not_oas) ... ok
test_ecb_usdkrw_is_cross_rate (test_macro_scan.MacroParserSmokeTests.test_ecb_usdkrw_is_cross_rate) ... ok
test_jolts_recent_month_is_not_stale (test_macro_scan.MacroParserSmokeTests.test_jolts_recent_month_is_not_stale) ... ok
test_nyfed_parses_effective_dates (test_macro_scan.MacroParserSmokeTests.test_nyfed_parses_effective_dates) ... ok
test_required_coverage_is_unique (test_macro_scan.MacroParserSmokeTests.test_required_coverage_is_unique) ... ok
test_source_group_routing_fx (test_macro_scan.MacroParserSmokeTests.test_source_group_routing_fx) ... ok
test_treasury_real_header_uppercase (test_macro_scan.MacroParserSmokeTests.test_treasury_real_header_uppercase) ... ok

----------------------------------------------------------------------
Ran 15 tests in 0.086s

OK
```

## Live collector log tail

```text
MACRO_SOURCE_OK treasury_nominal
MACRO_SOURCE_OK treasury_real
MACRO_SOURCE_OK cboe_vix
MACRO_SOURCE_OK cboe_vvix
MACRO_SOURCE_OK ecb_fx
MACRO_SOURCE_OK nyfed_effr
MACRO_SOURCE_OK nyfed_sofr
MACRO_SOURCE_OK bls_CPI_HEADLINE
MACRO_SOURCE_OK bls_CPI_CORE
MACRO_SOURCE_OK bls_UNRATE
MACRO_SOURCE_OK bls_PAYROLLS
MACRO_SOURCE_OK bls_PPI_FD
MACRO_SOURCE_OK bls_JOLTS_OPENINGS
MACRO_SOURCE_OK bls_LFPR
MACRO_SOURCE_OK bls_AVG_HOURLY_EARNINGS
MACRO_SOURCE_OK bls_AVG_WEEKLY_HOURS
MACRO_SOURCE_OK bls_CPI_SHELTER
MACRO_SOURCE_OK eia_brent
MACRO_SOURCE_OK eia_wti
MACRO_OK T2Y
MACRO_OK T10Y
MACRO_OK T10Y_REAL
MACRO_OK T10Y2Y
MACRO_OK CPI_HEADLINE
MACRO_OK CPI_CORE
MACRO_OK UNRATE
MACRO_OK PAYROLLS
MACRO_OK PPI_FD
MACRO_OK WTI
MACRO_OK BRENT
MACRO_OK VIX
MACRO_OK VVIX
MACRO_OK USD_KRW_ECB
MACRO_OK EUR_USD_ECB
MACRO_OK EFFR
MACRO_OK SOFR
MACRO_OK JOLTS_OPENINGS
MACRO_OK LFPR
MACRO_OK AVG_HOURLY_EARNINGS
MACRO_OK AVG_WEEKLY_HOURS
MACRO_OK CPI_SHELTER
MACRO_DONE 2026-10-20 ok 22 signals 1
```
