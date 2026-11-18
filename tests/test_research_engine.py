import unittest
from research_engine import trade,metrics,signal
class ResearchTests(unittest.TestCase):
    def test_next_close(self):
        dates=list("abcdefghi")
        days={d:{"T":{"close_usd":str(100+i)},"SPY":{"close_usd":"100"}} for i,d in enumerate(dates)}
        r=trade(dates,days,0,"T",h=2)
        self.assertEqual((r["entry"],r["exit"]),("b","e"))
        self.assertLess(r["net"],104/101-1)
    def test_gap(self):
        dates=list("abcd")
        days={d:{"T":{"close_usd":str(p)},"SPY":{"close_usd":"100"}} for d,p in zip(dates,[100,33,34,35])}
        self.assertEqual(trade(dates,days,0,"T")["status"],"suspect_corporate_action")
    def test_signal(self):
        self.assertIsNone(signal({"screen":"excluded_complex"}))
    def test_no_sample(self):
        self.assertEqual(metrics([{"status":"pending"}]),{"n":0})
if __name__=="__main__":unittest.main()
