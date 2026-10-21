"""Offline tests for the macro data reliability monitor."""
import copy
import unittest
from datetime import datetime, timezone

from macro_health import inspect, COVERAGE_CATEGORIES


class MacroHealthTests(unittest.TestCase):
    def fixtures(self):
        ids = [k for values in COVERAGE_CATEGORIES.values() for k in values]
        technical = {
            "us_market_date": "2026-10-20",
            "generated_at_utc": "2026-10-20T23:45:00+00:00",
        }
        macro = {
            "market_date": "2026-10-20",
            "status": "ok",
            "requested_series_count": 22,
            "retrieved_series_count": 22,
            "current_series_count": 22,
            "generated_at_utc": "2026-10-20T23:50:00+00:00",
            "errors": {},
            "series": [
                {
                    "series_id": sid,
                    "status": "ok",
                    "value": 3.14,
                    "source_url": "https://example.org/original-data.csv",
                    "observation_date": "2026-10-19",
                }
                for sid in ids
            ],
        }
        return technical, macro

    def test_full_coverage_is_ok(self):
        technical, macro = self.fixtures()
        status = inspect(technical, macro)
        self.assertEqual(status["status"], "OK")
        self.assertEqual(status["retrieved"], 22)
        self.assertEqual(status["current"], 22)

    def test_partial_is_warning(self):
        t, m = self.fixtures()
        m["status"] = "partial"
        m["series"] = [s for s in m["series"] if s["series_id"] != "VIX"]
        m["retrieved_series_count"] = 21
        m["current_series_count"] = 21
        m["errors"] = {"VIX": "Timeout"}
        x = inspect(t, m)
        self.assertEqual(x["status"], "WARN")
        self.assertIn("VIX", x["critical_missing"])
        self.assertTrue(any("Source failures" in v for v in x["messages"]))

    def test_stale_generation_warning(self):
        t, m = self.fixtures()
        m["generated_at_utc"] = "2026-10-20T23:40:00+00:00"
        x = inspect(t, m)
        self.assertEqual(x["status"], "WARN")
        self.assertTrue(any("BEFORE" in v for v in x["messages"]))

    def test_market_date_mismatch_warning(self):
        t, m = self.fixtures()
        m["market_date"] = "2026-10-19"
        x = inspect(t, m)
        self.assertEqual(x["status"], "WARN")
        self.assertTrue(any("does not match" in v for v in x["messages"]))

    def test_empty_data_error(self):
        t, m = self.fixtures()
        m["series"] = []
        m["status"] = "unavailable"
        m["retrieved_series_count"] = 0
        m["current_series_count"] = 0
        self.assertEqual(inspect(t, m)["status"], "ERROR")

    def test_stale_record_warning_even_when_complete(self):
        t, m = self.fixtures()
        for r in m["series"]:
            if r["series_id"] == "JOLTS_OPENINGS":
                r["status"] = "stale"
        m["current_series_count"] = 21
        result = inspect(t, m)
        self.assertEqual(result["status"], "WARN")
        self.assertIn("JOLTS_OPENINGS", result["categories"]["labor"]["missing_or_stale"])


if __name__ == "__main__":
    unittest.main()
