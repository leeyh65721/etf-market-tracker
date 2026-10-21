"""Offline, synthetic checks for no causal overclaim and exact U.S. ETF price dates."""
import json
import tempfile
import unittest
from pathlib import Path
import pandas as pd
import market_links as m


class MarketLinkTests(unittest.TestCase):
    def setUp(self):
        x=tempfile.TemporaryDirectory()
        self.addCleanup(x.cleanup)
        self.root=Path(x.name)
        self.history=self.root/"history"
        self.history.mkdir()
        self.latest=self.root/"latest.csv"

    def price(self,day,spy=100,soxx=120):
        frame=pd.DataFrame([{"ticker":"SPY","asof":day,"close_usd":spy},
                            {"ticker":"SOXX","asof":day,"close_usd":soxx}])
        return frame

    def test_exact_previous_nyse_session_including_weekend(self):
        self.assertEqual(m.predecessor("2026-10-19"),"2026-10-16")
        self.assertEqual(m.predecessor("2026-04-06"),"2026-04-02")

    def test_adjacent_prices_usd_and_relative_spy(self):
        self.price("2026-10-16",100,120).to_csv(self.history/"2026-10-16.csv",index=False)
        self.price("2026-10-19",102,126).to_csv(self.latest,index=False)
        out=m.verified_snapshots("2026-10-19",self.latest,self.history)
        self.assertEqual(out["previous_market_date"],"2026-10-16")
        by={r["ticker"]:r for r in out["instruments"]}
        self.assertEqual(out["coverage_count"],2)
        self.assertEqual(by["SOXX"]["price_return_pct"],5)
        self.assertEqual(by["SPY"]["price_return_pct"],2)
        self.assertEqual(by["SOXX"]["excess_vs_spy_pp"],3)
        self.assertEqual(by["XLE"]["status"],"unavailable")

    def test_missing_precise_prior_day_no_interpolation(self):
        self.price("2026-10-15",100,120).to_csv(self.history/"2026-10-15.csv",index=False)
        self.price("2026-10-19",102,126).to_csv(self.latest,index=False)
        result=m.verified_snapshots("2026-10-19",self.latest,self.history)
        self.assertEqual(result["status"],"previous_exact_session_missing")
        self.assertEqual(result["coverage_count"],0)

    def test_incompatible_snapshot_date_fails_closed(self):
        self.price("2026-10-16").to_csv(self.history/"2026-10-16.csv",index=False)
        self.price("2026-10-15").to_csv(self.latest,index=False)
        with self.assertRaisesRegex(ValueError,"snapshot date mismatch"):
            m.verified_snapshots("2026-10-19",self.latest,self.history)

    def test_outlier_price_does_not_look_like_valid_return(self):
        self.price("2026-10-16",100,100).to_csv(self.history/"2026-10-16.csv",index=False)
        self.price("2026-10-19",101,200).to_csv(self.latest,index=False)
        out=m.verified_snapshots("2026-10-19",self.latest,self.history)
        soxx=next(z for z in out["instruments"] if z["ticker"]=="SOXX")
        self.assertEqual(soxx["status"],"unverified")
        self.assertNotIn("price_return_pct",soxx)

    def test_macro_observation_not_release_timestamp(self):
        primary={"market_date":"2026-10-19","series":[{
            "series_id":"T2Y","name":"Treasury 2Y","frequency":"daily",
            "observation_date":"2026-10-19","previous_date":"2026-10-16",
            "value":4.7,"previous_value":4.65,"status":"ok","unit":"%",
            "source_url":"https://home.treasury.gov/example"}]}
        extra={"market_date":"2026-10-19","series":[{
            "series_id":"CORE_PCE","name":"Core PCE","frequency":"monthly",
            "observation_date":"2026-08-01","previous_date":"2026-07-01",
            "value":3.0,"previous_value":2.9,"status":"ok","unit":"% YoY",
            "source_url":"https://www.bea.gov/example"}]}
        files=[]
        for i,data in enumerate((primary,extra)):
            p=self.root/f"{i}.json"
            p.write_text(json.dumps(data),encoding="utf-8")
            files.append(p)
        arr,issues=m.macro_changes("2026-10-19",*files)
        self.assertFalse(issues)
        by={x["series_id"]:x for x in arr}
        self.assertEqual(by["T2Y"]["delta_observation_units"],.05)
        self.assertTrue(by["T2Y"]["same_market_date_observation"])
        self.assertFalse(by["T2Y"]["publication_date_verified"])
        self.assertFalse(by["CORE_PCE"]["same_market_date_observation"])

    def test_stale_and_manual_are_not_misrepresented(self):
        primary={"market_date":"2026-10-19","series":[]}
        extra={"market_date":"2026-10-19","series":[
            {"series_id":"NFCI","status":"stale","value":-0.5,
             "observation_date":"2026-04-01"},
            {"series_id":"ISM_MANUFACTURING","status":"manual"},
        ]}
        p=self.root/"p.json"
        q=self.root/"q.json"
        p.write_text(json.dumps(primary),encoding="utf-8")
        q.write_text(json.dumps(extra),encoding="utf-8")
        arr,issues=m.macro_changes("2026-10-19",p,q)
        self.assertEqual(arr,[])
        self.assertEqual(issues,[])

    def test_wrong_macroeconomic_market_date_excluded(self):
        p=self.root/"p.json"
        q=self.root/"q.json"
        p.write_text(json.dumps({"market_date":"2026-10-16","series":[]}))
        q.write_text(json.dumps({"market_date":"2026-10-19","series":[]}))
        data,issues=m.macro_changes("2026-10-19",p,q)
        self.assertEqual(data,[])
        self.assertEqual(len(issues),1)

    def test_output_expressly_refuses_causal_claim(self):
        self.price("2026-10-16").to_csv(self.history/"2026-10-16.csv",index=False)
        self.price("2026-10-19").to_csv(self.latest,index=False)
        p=self.root/"m.json"; q=self.root/"e.json"
        p.write_text(json.dumps({"market_date":"2026-10-19","series":[]}))
        q.write_text(json.dumps({"market_date":"2026-10-19","series":[]}))
        row=m.report_for_session("2026-10-19",self.latest,self.history,p,q)
        self.assertEqual(row["cause_attribution"],"NOT_ESTABLISHED")
        self.assertEqual(row["publication_timing"],"UNVERIFIED")
        markdown=m.markdown(row)
        self.assertIn("인과관계",markdown)


if __name__=="__main__":
    unittest.main()
