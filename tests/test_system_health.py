"""No-network end-to-end health-gate regression tests."""
import csv
import json
import tempfile
import unittest
from datetime import datetime,timezone
from pathlib import Path

import system_health as h


class HealthTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.day="2026-10-20"
        self.now=datetime(2026,10,21,7,5,tzinfo=timezone.utc)
        self.rows=[
            {"ticker":"SPY","asof":self.day,"screen":"watch_non_sector","close_usd":"100"},
            {"ticker":"XLV","asof":self.day,"screen":"candidate","close_usd":"50"},
        ]
        self.file("data/latest.json",{
            "us_market_date":self.day,"generated_at_utc":"2026-10-21T06:02:00+00:00",
            "valid_screened_count":2,"candidate_universe_count":2,
            "technical_candidate_count":1,
        })
        self.write_csv()
        core=[{"series_id":f"SERIES_{i:02}","status":"ok"} for i in range(22)]
        self.file("data/macro/latest.json",{
            "market_date":self.day,"generated_at_utc":"2026-10-21T06:03:00+00:00",
            "status":"ok","requested_series_count":22,
            "retrieved_series_count":22,"current_series_count":22,"series":core,
        })
        self.file("data/macro/health_latest.json",{"status":"OK","market_date":self.day})
        extra=[{"series_id":k,"status":"manual" if k in h.EXPECTED_MANUAL else
                "stale" if k in h.KNOWN_STALE else "ok"}
                for k in sorted(h.EXPECTED_EXTRA)]
        self.file("data/macro/extra_latest.json",{
            "market_date":self.day,"generated_at_utc":"2026-10-21T06:04:00+00:00",
            "requested_indicators":10,"ok_indicators":7,"series":extra,
        })
        self.file("data/quality/latest.json",{"asof":self.day,"status":"OK"})
        self.file("data/links/latest.json",{
            "us_market_date":self.day,"market":{"status":"ok","coverage_count":17},
            "data_quality_issues":[],
        })
        self.file("data/industry/quality_latest.json",{
            "status":"OK","event_count":1,"invalid_record_count":0,
        })
        self.file("data/decisions/latest.json",{
            "status":"OK","valid_count":4,"invalid_count":0,
        })
        self.steps={k:"success" for k in ("ETF_SCAN","BASE_MACRO","EXTRA_MACRO",
                                         "SCREEN_AUDIT","MARKET_LINKS",
                                         "INDUSTRY_EVIDENCE","JUDGMENT_ARCHIVE")}
    def file(self,name,obj):
        path=self.root/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(obj),encoding="utf-8")
    def get(self,name):
        return json.loads((self.root/name).read_text(encoding="utf-8"))
    def write_csv(self):
        path=self.root/"data/latest.csv"
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open("w",newline="",encoding="utf-8") as fp:
            writer=csv.DictWriter(fp,fieldnames=["ticker","asof","screen","close_usd"])
            writer.writeheader()
            writer.writerows(self.rows)
    def analyze(self):
        return h.analyze(self.root,self.now,self.steps)
    def codes(self,out):
        return {f["code"] for f in out["findings"]}

    def test_healthy_with_known_stale_nfci_and_manual_pmi(self):
        result=self.analyze()
        self.assertEqual(result["status"],"OK")
        self.assertEqual(result["counts"]["supplemental_ok"],7)
        self.assertIn("NFCI_NOT_LIVE",self.codes(result))
        self.assertFalse(result["new_alert_codes"])

    def test_one_new_supplemental_failure_must_be_visible(self):
        extra=self.get("data/macro/extra_latest.json")
        next(z for z in extra["series"] if z["series_id"]=="RETAIL_SALES")["status"]="unavailable"
        extra["ok_indicators"]=6
        self.file("data/macro/extra_latest.json",extra)
        result=self.analyze()
        self.assertEqual(result["status"],"WARN")
        self.assertIn("EXTRA_UNAVAILABLE_RETAIL_SALES",result["new_alert_codes"])

    def test_several_automatic_failures_raise_critical_error(self):
        extra=self.get("data/macro/extra_latest.json")
        for z in extra["series"]:
            if z["series_id"] in ("RETAIL_SALES","CORE_PCE","REAL_GDP"):
                z["status"]="unavailable"
        extra["ok_indicators"]=4
        self.file("data/macro/extra_latest.json",extra)
        result=self.analyze()
        self.assertEqual(result["status"],"ERROR")
        self.assertIn("EXTRA_MULTIPLE_LOSSES",self.codes(result))

    def test_missing_core_indicators_is_not_green(self):
        data=self.get("data/macro/latest.json")
        data["series"][0]["status"]="unavailable"
        data["current_series_count"]=21
        data["status"]="partial"
        self.file("data/macro/latest.json",data)
        result=self.analyze()
        self.assertEqual(result["status"],"ERROR")
        self.assertIn("BASE_MACRO_INCOMPLETE",self.codes(result))

    def test_prior_date_dataset_fails_even_if_its_old_status_ok(self):
        doc=self.get("data/links/latest.json")
        doc["us_market_date"]="2026-10-19"
        self.file("data/links/latest.json",doc)
        result=self.analyze()
        self.assertEqual(result["status"],"ERROR")
        self.assertIn("STALE_MACRO_ETF_LINKS",self.codes(result))

    def test_missing_new_judgment_ledger_detected(self):
        (self.root/"data/decisions/latest.json").unlink()
        result=self.analyze()
        self.assertEqual(result["status"],"ERROR")
        self.assertIn("MISSING_JUDGMENT_ARCHIVE",self.codes(result))

    def test_action_stage_failures_not_hidden_by_continue_on_error(self):
        self.steps["BASE_MACRO"]="failure"
        result=self.analyze()
        self.assertEqual(result["status"],"ERROR")
        self.assertIn("STEP_BASE_MACRO",self.codes(result))

    def test_known_warning_is_not_repeated_as_new(self):
        e=self.get("data/macro/extra_latest.json")
        next(z for z in e["series"] if z["series_id"]=="CORE_PCE")["status"]="unavailable"
        e["ok_indicators"]=6
        self.file("data/macro/extra_latest.json",e)
        first=self.analyze()
        h.write_report(first,self.root)
        next_run=self.analyze()
        self.assertEqual(next_run["status"],"WARN")
        self.assertEqual(next_run["new_alert_codes"],[])

    def test_stale_etf_market_date_detected(self):
        d=self.get("data/latest.json")
        d["us_market_date"]="2026-10-19"
        self.file("data/latest.json",d)
        result=self.analyze()
        self.assertEqual(result["status"],"ERROR")
        self.assertIn("STALE_ETF_SESSION",self.codes(result))


if __name__=="__main__":
    unittest.main()
