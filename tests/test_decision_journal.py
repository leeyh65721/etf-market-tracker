"""No-network checks for public-only, report-anchored ETF judgment provenance."""
import csv
import json
import tempfile
import unittest
from pathlib import Path

import decision_journal as a

EXCERPT="- XLY newly highlighted for observation with unproven continuation"

def record():
    return {
        "schema":a.SCHEMA,"record_id":"2026-10-19-XLY-watch",
        "ticker":"XLY","stance":"watch",
        "us_market_date":"2026-10-19",
        "original_report_date_kst":"2026-10-20",
        "archived_on_utc_date":"2026-10-21",
        "provenance":"retrospective_archived_report",
        "source_report":"analysis/daily/2026-10-20.md",
        "verbatim_source_excerpt":EXCERPT,
        "original_close_usd":114.46,
        "original_spy_close_usd":766.48,
        "thesis":"XLY relative strength improved but continuation unproven",
        "counterevidence":"Growth risk and sustained discount rates could cause reversal",
        "invalidation":"Fall in SPY relative price strength over multiple sessions",
        "revisit_trigger":"Reassess on next 5/10/20 US sessions against SPY",
        "review_horizons_nyse_sessions":[5,10,20],
        "comparison_baseline":"SPY","trade_instruction":False,
    }

class DecisionsTest(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        reports=self.root/"analysis/daily"
        reports.mkdir(parents=True)
        (reports/"2026-10-20.md").write_text(
            "# Oct 20 ETF opportunity report\n"+EXCERPT+"\n",
            encoding="utf-8")
        prices=self.root/"data/history"
        prices.mkdir(parents=True)
        with (prices/"2026-10-19.csv").open("w",newline="",encoding="utf-8") as fp:
            w=csv.DictWriter(fp,fieldnames=["ticker","asof","close_usd"])
            w.writeheader()
            w.writerows([
                {"ticker":"XLY","asof":"2026-10-19","close_usd":114.46},
                {"ticker":"SPY","asof":"2026-10-19","close_usd":766.48},
            ])
    def test_report_and_close_match_real_original_snapshot(self):
        row=a.check_entry(record(),self.root)
        self.assertEqual(row["stance"],"watch")
        self.assertEqual(row["first_theoretical_reference_session"],"2026-10-20")
        self.assertFalse(row["eligible_for_prospective_judgment_scoring"])
        self.assertEqual(row["assessment"],"historical_backfill_not_prospectively_scored")

    def test_changed_quote_or_missing_original_report_rejected(self):
        item=record()
        item["verbatim_source_excerpt"]="- made-up BUY call XLY"
        with self.assertRaisesRegex(ValueError,"not found"):
            a.check_entry(item,self.root)
        item=record()
        item["source_report"]="analysis/daily/2026-10-18.md"
        with self.assertRaisesRegex(ValueError,"missing"):
            a.check_entry(item,self.root)

    def test_unverified_backfilled_price_rejected(self):
        item=record()
        item["original_close_usd"]=140.
        with self.assertRaisesRegex(ValueError,"does not match"):
            a.check_entry(item,self.root)
        item=record()
        item["original_spy_close_usd"]=777.
        with self.assertRaisesRegex(ValueError,"does not match"):
            a.check_entry(item,self.root)

    def test_backdated_prospective_claim_rejected(self):
        item=record()
        item["provenance"]="contemporaneous_report"
        item["archived_on_utc_date"]="2026-10-25"
        with self.assertRaisesRegex(ValueError,"prospective"):
            a.check_entry(item,self.root)

    def test_private_allocation_or_implicit_trade_forbidden(self):
        item=record()
        item["target_allocation"]=40
        with self.assertRaisesRegex(ValueError,"Private account"):
            a.check_entry(item,self.root)
        item=record()
        item["trade_instruction"]=True
        with self.assertRaisesRegex(ValueError,"trade instruction"):
            a.check_entry(item,self.root)

    def test_cannot_misstate_no_candidate_as_spy_trade(self):
        item=record()
        item["stance"]="no_new_candidate"
        with self.assertRaisesRegex(ValueError,"MARKET"):
            a.check_entry(item,self.root)

    def test_collect_flags_reports_without_structured_entry(self):
        rows,errors,missing=a.collect(self.root)
        self.assertEqual(rows,[])
        self.assertEqual(errors,[])
        self.assertEqual(missing,["analysis/daily/2026-10-20.md"])

    def test_collect_and_link_success(self):
        entries=self.root/"analysis/decisions/entries"
        entries.mkdir(parents=True)
        item=record()
        (entries/(item["record_id"]+".json")).write_text(
            json.dumps(item),encoding="utf-8")
        rows,errors,missing=a.collect(self.root)
        self.assertEqual(len(rows),1)
        self.assertEqual(errors,[])
        self.assertEqual(missing,[])

    def test_genuine_no_new_candidate_without_fictitious_trade(self):
        neutral="- No verified new ETF candidate exists; no change to public watchlist."
        report=self.root/"analysis/daily/2026-10-20.md"
        report.write_text(report.read_text(encoding="utf-8")+neutral+"\n",encoding="utf-8")
        item=record()
        item.update(record_id="2026-10-19-MARKET-no-new-candidate",
                    ticker="MARKET",stance="no_new_candidate",
                    verbatim_source_excerpt=neutral,
                    thesis="No new validated ETF ideas meet our public-market criteria")
        del item["original_close_usd"]
        del item["original_spy_close_usd"]
        check=a.check_entry(item,self.root)
        self.assertEqual(check["ticker"],"MARKET")
        self.assertIsNone(check["original_close_usd"])
        self.assertFalse(check["eligible_for_prospective_judgment_scoring"])

    def test_missing_countercase_is_invalid(self):
        item=record()
        item["counterevidence"]="none"
        with self.assertRaisesRegex(ValueError,"counterevidence"):
            a.check_entry(item,self.root)


if __name__=="__main__":
    unittest.main()
