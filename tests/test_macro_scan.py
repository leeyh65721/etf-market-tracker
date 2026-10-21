"""Offline smoke tests for official public macro source parsers.
No network or brokerage connection is used by this test suite.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import macro_scan as m


class MacroParserSmokeTests(unittest.TestCase):
    def test_required_coverage_is_unique(self):
        ids=[r[0] for r in m.SPECS]
        self.assertEqual(len(ids),22)
        self.assertEqual(len(ids),len(set(ids)))
        for key in ("VIX","VVIX","USD_KRW_ECB","EFFR","SOFR","JOLTS_OPENINGS"):
            self.assertIn(key,ids)

    def test_ecb_usdkrw_is_cross_rate(self):
        sample=b'''<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
          xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
        <Cube><Cube time="2026-10-19"><Cube currency="USD" rate="1.10"/>
        <Cube currency="KRW" rate="1430"/></Cube>
        <Cube time="2026-10-20"><Cube currency="USD" rate="1.12"/>
        <Cube currency="KRW" rate="1456"/></Cube></Cube></gesmes:Envelope>'''
        with patch.object(m,"request_bytes",return_value=sample):
            df,url=m.ecb_fx()
        self.assertEqual(len(df),2)
        self.assertAlmostEqual(float(df.iloc[1]["usdkrw"]),1300)
        self.assertEqual(url.endswith("eurofxref-hist-90d.xml"),True)

    def test_cboe_parses_daily_close(self):
        csv=b"DATE,OPEN,HIGH,LOW,CLOSE\n10/19/2026,21,23,20,22\n10/20/2026,24,25,22,23\n"
        with patch.object(m,"request_bytes",return_value=csv):
            df,url=m.cboe("VIX")
        self.assertEqual(len(df),2)
        self.assertAlmostEqual(float(df.iloc[-1]["value"]),23)

    def test_nyfed_parses_effective_dates(self):
        payload={"refRates":[
            {"type":"EFFR","effectiveDate":"2026-10-19","percentRate":4.9},
            {"type":"EFFR","effectiveDate":"2026-10-20","percentRate":5.0}]}
        with patch.object(m,"request_bytes",return_value=json.dumps(payload).encode()):
            df,url=m.nyfed("effr")
        self.assertEqual(len(df),2)
        self.assertAlmostEqual(float(df.iloc[-1]["value"]),5.0)

    def test_credit_etf_proxies_are_not_oas(self):
        with tempfile.TemporaryDirectory() as folder:
            df=pd.DataFrame([
                {"ticker":"HYG","asof":"2026-10-20","return_5d_pct":-1.0,"return_21d_pct":-3.0},
                {"ticker":"LQD","asof":"2026-10-20","return_5d_pct":-0.5,"return_21d_pct":-1.0},
                {"ticker":"IEF","asof":"2026-10-20","return_5d_pct":0.5,"return_21d_pct":0.0},
            ])
            df.to_csv(Path(folder)/"latest.csv",index=False)
            with patch.object(m,"DATA",Path(folder)):
                from datetime import date
                actual=m.etf_credit_proxies(date(2026,10,20))
            self.assertEqual(actual["status"],"ok")
            self.assertIn("not yield spread",actual["metric_type"])
            self.assertEqual(actual["series"]["HY_vs_treasury"]["5d_price_return_gap_pp"],-1.5)

    def test_source_group_routing_fx(self):
        from datetime import date
        data=pd.DataFrame([
            {"date":pd.Timestamp("2026-10-19"),"usdkrw":1300.0,"eurusd":1.10},
            {"date":pd.Timestamp("2026-10-20"),"usdkrw":1301.0,"eurusd":1.11}
        ])
        with patch.dict(m.SOURCE_RESULTS,{"ecb_fx":(data,"ecb://example")},clear=True):
            df,url=m.collect("USD_KRW_ECB","2026-10-01",date(2026,10,20))
            self.assertEqual(float(df.iloc[-1]["value"]),1301.0)
            self.assertEqual(url,"ecb://example")


if __name__=="__main__":
    unittest.main()
