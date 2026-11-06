import unittest
import pandas as pd
import opportunity_scan as scan
class TestOpportunity(unittest.TestCase):
 def setUp(self):
  idx=pd.bdate_range("2025-01-01",periods=220)
  self.spy=pd.Series([100+i*.1 for i in range(220)],index=idx)
  self.qqq=pd.Series([100+i*.12 for i in range(220)],index=idx)
  self.stock=pd.Series([100+i*.25 for i in range(220)],index=idx)
  self.vol=pd.Series([1000000]*220,index=idx)
 def test_relative_strength(self):
  x=scan.observe(self.stock,self.vol,self.spy,self.qqq,self.spy)
  self.assertTrue(x["technical_watch"])
  self.assertGreater(x["spy_excess_20d_pp"],0)
 def test_illiquid(self):
  self.assertIsNone(scan.observe(self.stock,self.vol*0,self.spy,self.qqq))
 def test_no_future_audit(self):
  frame={"AAPL":pd.DataFrame({"Close":self.stock,"Volume":self.vol}),"SPY":pd.DataFrame({"Close":self.spy,"Volume":self.vol})}
  r=scan.audit(frame,[{"ticker":"AAPL","asof":self.stock.index[-2].strftime("%Y-%m-%d"),"close_usd":float(self.stock.iloc[-2])}])
  self.assertEqual(list(r[0]["horizons"]),["1"])
 def test_missing_benchmark(self):
  with self.assertRaises(RuntimeError):scan.build({})
if __name__=="__main__":unittest.main()
