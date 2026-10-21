"""Industry/SEC evidence validation: distinguish first tradable session and facts vs guesses."""
import json
import tempfile
import unittest
from pathlib import Path

import industry_evidence as e


def event():
    return {
        "event_id":"2026-10-20-smci-fy2027-q1-preliminary",
        "issuer":"Super Micro Computer, Inc.",
        "ticker":"SMCI","industry":"AI server integrator",
        "published_at_utc":"2026-10-20T20:44:26Z",
        "period_label":"FY2027 Q1 ended September 2026",
        "primary_source_url":"https://www.sec.gov/Archives/edgar/data/1375365/000137536526000025/smcifirstquarterfy2027busi.htm",
        "source_type":"SEC_EDGAR",
        "source_checked_date":"2026-10-21",
        "reporting_status":"preliminary_unaudited",
        "metrics":[{
            "name":"Revenue guidance",
            "category":"revenue",
            "unit":"USD billion",
            "current_low":18.5,"current_high":19.5,
            "comparison_low":14.5,"comparison_high":15.5,
            "comparison_basis":"previous SAME-quarter company revenue outlook",
            "source_label":"SEC 8-K exhibit 99.1",
        },{
            "name":"Gross margin guidance",
            "category":"gross_margin",
            "unit":"%",
            "current_low":12,"current_high":12.5,
            "comparison_low":10.4,"comparison_high":10.8,
            "comparison_basis":"previous SAME-quarter company gross-margin outlook",
            "source_label":"SEC 8-K exhibit 99.1",
        }],
        "not_disclosed":["chip supplier new orders","inventory","bookings"],
        "related_etfs":["SOXX"],
        "transmission_hypothesis":"Indirectly relevant to suppliers if independently corroborated",
        "counterevidence":["unreviewed preliminary estimates may change",
                           "revenue is not chip bookings"],
        "recheck_trigger":"2026-11-03 final quarterly results",
    }


class IndustryEvidenceTests(unittest.TestCase):
    def test_after_hours_filing_cannot_explain_same_day_etf_close(self):
        self.assertEqual(e.earliest_session("2026-10-20T20:44:26Z"),
                         "2026-10-21")

    def test_intraday_and_weekend_eligibility(self):
        self.assertEqual(e.earliest_session("2026-10-20T15:00:00Z"),
                         "2026-10-20")
        self.assertEqual(e.earliest_session("2026-10-17T15:00:00Z"),
                         "2026-10-19")

    def test_revenue_guidance_change_not_realized_sales(self):
        out=e.validate_event(event())
        by={q["name"]:q for q in out["metrics"]}
        self.assertEqual(by["Revenue guidance"]["current_midpoint"],19)
        self.assertEqual(by["Revenue guidance"]["comparison_midpoint"],15)
        self.assertEqual(by["Revenue guidance"]["midpoint_change"],4)
        self.assertAlmostEqual(by["Revenue guidance"]["relative_midpoint_change_pct"],26.6667,places=4)
        self.assertEqual(by["Gross margin guidance"]["midpoint_change"],1.65)
        self.assertEqual(by["Gross margin guidance"]["midpoint_change_unit"],"percentage points")
        self.assertEqual(out["reporting_status"],"preliminary_unaudited")
        self.assertEqual(out["causality"],"HYPOTHESIS_ONLY")
        self.assertFalse(out["latest_price_reaction_verified"])

    def test_missing_primary_filing_is_invalid(self):
        item=event()
        item["primary_source_url"]="https://example.org/alleged-announcement"
        with self.assertRaisesRegex(ValueError,"SEC"):
            e.validate_event(item)

    def test_missing_counterevidence_is_rejected(self):
        item=event()
        item["counterevidence"]=[]
        with self.assertRaisesRegex(ValueError,"counterevidence"):
            e.validate_event(item)

    def test_invalid_ranges_and_units(self):
        for change in ({"current_low":19.6,"current_high":19.5},
                       {"unit":"handwavy demand"}):
            item=event()
            item["metrics"][0].update(change)
            with self.assertRaises(ValueError):
                e.validate_event(item)

    def test_future_source_check_is_invalid(self):
        item=event()
        item["source_checked_date"]="2026-10-19"
        with self.assertRaisesRegex(ValueError,"before issuer publication"):
            e.validate_event(item)

    def test_record_collection_invalid_json_marked_as_error(self):
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)
            path=p/"2026-10-20-smci-fy2027-q1-preliminary.json"
            path.write_text(json.dumps(event()),encoding="utf-8")
            (p/"bad.json").write_text('{"bad":',encoding="utf-8")
            data,errors=e.collect_events(p)
            self.assertEqual(len(data),1)
            self.assertEqual(data[0]["earliest_reaction_us_session"],"2026-10-21")
            self.assertEqual(len(errors),1)

    def test_markdown_marks_unreported_fundamentals(self):
        out=e.markdown([e.validate_event(event())],[])
        self.assertIn("주문",out)
        self.assertIn("preliminary_unaudited",out)
        self.assertIn("2026-10-21",out)


if __name__=="__main__":
    unittest.main()
