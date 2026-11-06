import unittest
import pandas as pd
from breadth_scan import members,calculate
from earnings_scan import parse_estimates,changes
class TestBreadthEarnings(unittest.TestCase):
 def test_membership_parsing(self):
  html="<table><tr><th>Symbol</th></tr>"+''.join("<tr><td>T%03d</td></tr>"%i for i in range(500))+"</table>"
  self.assertEqual(len(members(html)),500)
 def test_breadth_denominator(self):
  dates=pd.bdate_range("2025-01-01",periods=260)
  up=pd.DataFrame({"Close":[100+i for i in range(260)]},index=dates)
  down=pd.DataFrame({"Close":[400-i for i in range(260)]},index=dates)
  x=calculate({"A":up,"B":down},["A","B","C"],dates[-1])
  self.assertEqual(x["valid_count"],2)
  self.assertEqual(x["coverage_pct"],66.67)
  self.assertEqual(x["advancers"],1)
 def test_estimates(self):
  table=pd.DataFrame({"avg":[1.5,2.0],"numberOfAnalysts":[10,12]},index=["0q","+1q"])
  self.assertEqual(parse_estimates(table)["0q"]["eps_mean_usd"],1.5)
 def test_revisions_only_with_prior(self):
  cur={"A":{"0q":{"eps_mean_usd":2.0}}}
  self.assertEqual(changes(cur,{}),{})
  self.assertEqual(changes(cur,{"A":{"0q":{"eps_mean_usd":1.5}}})["A"]["0q"]["change_usd"],.5)
if __name__=="__main__":unittest.main()
