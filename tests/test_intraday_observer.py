import unittest
from datetime import datetime, timezone
import pandas as pd
from intraday_observer import observe

class ObserverTest(unittest.TestCase):
    def test_closed(self):
        r=observe(datetime(2026,11,15,16,tzinfo=timezone.utc),[],lambda t:None)
        self.assertEqual(r["reason"],"market_closed")
    def test_post_plan_completed(self):
        now=datetime(2026,11,17,16,tzinfo=timezone.utc)
        p={"ticker":"SPY","created_at_utc":"2026-11-17T15:50:00+00:00","expiry":"2026-11-17T20:00:00+00:00","price_level":100,"direction":"above"}
        bars=pd.DataFrame({"Close":[99,101,120],"Volume":[10,20,30]},index=pd.to_datetime(["2026-11-17T15:45Z","2026-11-17T15:55Z","2026-11-17T16:00Z"]))
        r=observe(now,[{},p],lambda t:bars)
        self.assertEqual(len(r["errors"]),1)
        self.assertEqual(r["observations"][0]["close"],101)
        self.assertEqual(r["observations"][0]["price_condition"],"observed")
        self.assertFalse(r["observations"][0]["execution_verified"])
