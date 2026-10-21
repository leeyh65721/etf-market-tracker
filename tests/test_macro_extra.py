"""Offline validation of official macro-release parsers and explicit ISM opt-out."""
import unittest
from datetime import date
from unittest.mock import patch
import macro_extra as e


class ExtraMacroTests(unittest.TestCase):
    def test_eight_categories_and_ten_subindicators(self):
        self.assertEqual(len(e.CATEGORIES),8)
        self.assertEqual(len(e.SOURCES),10)
        names={x for _,keys in e.CATEGORIES for x in keys}
        self.assertEqual(names,set(e.SOURCES))

    def test_bea_core_pce_year_over_year(self):
        html=b"<html><h1>Core PCE</h1><p>Change From Month One Year Ago</p><p>August 2026 | +3.0%</p><p>July 2026 | +2.9%</p></html>"
        row=e.parse_core_pce(html)
        self.assertEqual(row["series_id"],"CORE_PCE")
        self.assertEqual(row["observation_date"],"2026-08-01")
        self.assertEqual(row["value"],3.0)
        self.assertEqual(row["previous_value"],2.9)
        self.assertEqual(row["unit"],"% YoY")

    def test_retail_sales_monthly(self):
        html=b'<html><body>Advance estimates of U.S. retail and food services sales for September 2026, adjusted for seasonality, were $800.1 billion, down 0.8 percent from the previous month.</body></html>'
        r=e.parse_retail(html)
        self.assertEqual(r["value"],-0.8)
        self.assertEqual(r["observation_date"],"2026-09-01")

    def test_manufacturing_orders(self):
        src=b'<p>October 02, 2026</p><p>New orders for manufactured goods in August, up two consecutive months, increased $0.7 billion or 0.1 percent to $663.5 billion.</p>'
        r=e.parse_manufacturing(src,"MFG_NEW_ORDERS")
        self.assertEqual(r["value"],0.1)
        self.assertEqual(r["observation_date"],"2026-08-01")

    def test_durable_orders_virtually_unchanged(self):
        src=b'<p>September 25, 2026</p><p>New orders for manufactured durable goods in August, decreased $0.1 billion or virtually unchanged to $338.6 billion.</p>'
        r=e.parse_manufacturing(src,"DURABLE_NEW_ORDERS")
        self.assertEqual(r["value"],0.0)
        self.assertEqual(r["observation_date"],"2026-08-01")

    def test_gdp_annualized_chart(self):
        src=b'<html><body>Real GDP Quarterly Q2 2026 | +2.2% Q1 2026 | +2.5%</body></html>'
        r=e.parse_real_gdp(src)
        self.assertEqual(r["value"],2.2)
        self.assertEqual(r["observation_date"],"2026-04-01")

    def test_dol_pdf_week_year_from_release_header(self):
        from unittest.mock import MagicMock
        import macro_extra as e
        text=("TRANSMISSION EMBARGOED UNTIL 8:30 A.M. (Eastern) Thursday, August 6, 2026 "
              "UNEMPLOYMENT INSURANCE WEEKLY CLAIMS SEASONALLY ADJUSTED DATA "
              "In the week ending August 1, the advance figure for seasonally adjusted "
              "initial claims was 199,000, an increase of 1,000.")
        with patch.object(e,"PdfReader") as reader:
            reader.return_value.pages=[MagicMock(extract_text=lambda:text)]
            row=e.parse_claims_pdf(b"%PDF mock")
        self.assertEqual(row["value"],199000)
        self.assertEqual(row["observation_date"],"2026-08-01")

    def test_stale_and_future_are_rejected(self):
        x=e.record("CORE_PCE",3.0,date(2026,7,1),"% YoY","fixture")
        self.assertEqual(e.evaluate("CORE_PCE",x,date(2026,10,20))["status"],"stale")
        future=e.record("CORE_PCE",3.0,date(2026,11,1),"% YoY","fixture")
        with self.assertRaises(ValueError):
            e.evaluate("CORE_PCE",future,date(2026,10,20))

    def test_ism_only_manual(self):
        with patch.object(e,"fetch",side_effect=AssertionError("ISM should not be downloaded")):
            r=e.collect_one("ISM_MANUFACTURING",date(2026,10,20))
        self.assertEqual(r["status"],"manual")
        self.assertNotIn("value",r)

    def test_source_failure_is_unavailable_not_zero(self):
        with patch.object(e,"fetch",side_effect=RuntimeError("provider offline")):
            r=e.collect_one("CORE_PCE",date(2026,10,20))
        self.assertEqual(r["status"],"unavailable")
        self.assertNotIn("value",r)


if __name__=="__main__":
    unittest.main()
