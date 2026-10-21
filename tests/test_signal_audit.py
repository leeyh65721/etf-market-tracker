"""Synthetic, offline audit tests. Future prices must never affect original signals."""
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

import signal_audit as a


class SignalAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def frame(self, day="2026-10-20", candidate=True, date_override=None):
        data = [
            {"ticker": "SPY", "asof": date_override or day, "screen": "watch_non_sector",
             "close_usd": 100.0, "liquid_enough": True, "rank_score": 0.0,
             "return_5d_pct": 0., "return_21d_pct": 0., "spy_excess_21d_pp": 0.},
            {"ticker": "XLV", "asof": date_override or day,
             "screen": "candidate" if candidate else "watch",
             "close_usd": 50.0, "liquid_enough": True, "rank_score": 5.0,
             "return_5d_pct": 1., "return_21d_pct": 2., "spy_excess_21d_pp": 2.},
        ]
        return pd.DataFrame(data)

    def files(self, day="2026-10-20", candidate=True, generated="2026-10-21T02:01:00+00:00"):
        source_json = self.root / "latest.json"
        source_csv = self.root / "latest.csv"
        frame = self.frame(day, candidate)
        report = {
            "us_market_date": day,
            "generated_at_utc": generated,
            "data_source": "synthetic test only",
            "valid_screened_count": len(frame),
            "technical_candidate_count": int(frame.screen.eq("candidate").sum()),
            "candidate_universe_count": len(frame),
        }
        source_json.write_text(json.dumps(report), encoding="utf-8")
        frame.to_csv(source_csv, index=False)
        return source_json, source_csv

    def make_lock(self, day, spy, xlv, candidate, entries=None):
        return {
            "schema": a.SCHEMA, "us_market_date": day,
            "first_published_scan_generated_at_utc": "2026-10-21T02:00:00+00:00",
            "verified_count": 2, "universe_count": 2,
            "tickers": {
                "SPY": {"screen": "watch_non_sector", "liquid": True,
                        "score": 0, "close_usd": spy},
                "XLV": {"screen": "candidate" if candidate else "watch",
                        "liquid": True, "score": 3, "close_usd": xlv},
            },
            "new_technical_entries": entries or [],
        }

    def test_genuine_nyse_sessions_skip_good_friday(self):
        self.assertEqual(a.offset("2026-04-02", 1), "2026-04-06")
        self.assertEqual(a.offset("2026-10-16", 1), "2026-10-19")
        self.assertEqual(a.offset("2026-10-19", 5), "2026-10-26")

    def test_source_json_csv_match_and_market_close(self):
        js, csv = self.files()
        first = a.current_first_published(js, csv)
        self.assertEqual(first["us_market_date"], "2026-10-20")
        self.assertEqual(len(first["tickers"]), 2)
        self.assertEqual(first["tickers"]["XLV"]["screen"], "candidate")

    def test_scan_before_market_close_rejected(self):
        js, csv = self.files(generated="2026-10-20T15:00:00+00:00")
        with self.assertRaisesRegex(ValueError, "predates"):
            a.current_first_published(js, csv)

    def test_mismatched_market_date_rejected(self):
        js, csv = self.files()
        self.frame(date_override="2026-10-19").to_csv(csv, index=False)
        with self.assertRaisesRegex(ValueError, "different market date"):
            a.current_first_published(js, csv)

    def test_missing_spy_rejected(self):
        js, csv = self.files()
        frame = pd.read_csv(csv)
        frame.loc[0, "ticker"] = "QQQ"
        frame.to_csv(csv, index=False)
        with self.assertRaisesRegex(ValueError, "Missing SPY"):
            a.current_first_published(js, csv)

    def test_same_session_rerun_preserves_first_published_snapshot(self):
        old, fresh = self.files()
        first = a.current_first_published(old, fresh)
        locked, created = a.write_lock_if_missing(first, self.root / "locks")
        self.assertTrue(created)
        modified = a.current_first_published(old, fresh)
        modified["tickers"]["XLV"]["close_usd"] = 9999.
        locked2, created2 = a.write_lock_if_missing(modified, self.root / "locks")
        self.assertFalse(created2)
        self.assertEqual(locked2["tickers"]["XLV"]["close_usd"], 50.)
        self.assertEqual(locked["tickers"], locked2["tickers"])

    def test_candidate_transition_only_with_consecutive_previous_snapshot(self):
        locks = self.root / "locks"
        locks.mkdir()
        p = locks / "2026-10-15.json"
        p.write_text(json.dumps(self.make_lock("2026-10-15", 100, 50, False)),
                     encoding="utf-8")
        new = self.make_lock("2026-10-16", 100, 55, True)
        frozen, created = a.write_lock_if_missing(new, locks)
        self.assertTrue(created)
        self.assertEqual([x["ticker"] for x in frozen["new_technical_entries"]], ["XLV"])
        self.assertEqual(frozen["new_technical_entries"][0]["previous_screen"], "watch")
        self.assertEqual(frozen["new_technical_entries"][0]["entry_signal_date"], "2026-10-16")

    def test_gap_in_archive_is_not_new_candidate_transition(self):
        locks = self.root / "locks"
        locks.mkdir()
        (locks / "2026-10-15.json").write_text(
            json.dumps(self.make_lock("2026-10-15", 100, 50, False)), encoding="utf-8")
        frozen, created = a.write_lock_if_missing(
            self.make_lock("2026-10-19", 100, 55, True), locks)
        self.assertTrue(created)
        self.assertEqual(frozen["new_technical_entries"], [])

    def test_forward_return_uses_next_day_close_not_signal_close(self):
        signals = [{"ticker": "XLV", "entry_signal_date": "2026-10-16",
                    "first_published_close_usd": 5.0, "initial_score": 10.0,
                    "previous_screen": "watch"}]
        snaps = {
            "2026-10-15": self.make_lock("2026-10-15", 100, 50, False),
            "2026-10-16": self.make_lock("2026-10-16", 100, 5, True, entries=signals),
            "2026-10-19": self.make_lock("2026-10-19", 100, 100, True),
            "2026-10-26": self.make_lock("2026-10-26", 110, 120, True),
        }
        out = a.outcomes(snaps)
        matured = [r for r in out["observations"] if r["sessions_held"] == 5][0]
        self.assertEqual(matured["reference_entry_day"], "2026-10-19")
        self.assertEqual(matured["reference_exit_day"], "2026-10-26")
        self.assertEqual(matured["etf_price_return_pct"], 20.)
        self.assertEqual(matured["spy_price_return_pct"], 10.)
        self.assertEqual(matured["excess_vs_spy_pp"], 10.)
        self.assertTrue(matured["outperform_spy"])
        self.assertEqual(out["summaries"]["5"]["observed"], 1)
        self.assertEqual(out["summaries"]["5"]["assessment"], "insufficient_observations")
        self.assertEqual(out["summaries"]["10"]["pending"], 1)

    def test_missing_exact_entry_date_is_unverifiable_not_invented(self):
        entry = [{"ticker": "XLV", "entry_signal_date": "2026-10-16"}]
        snaps = {
            "2026-10-16": self.make_lock("2026-10-16", 100, 50, True, entry),
            "2026-10-26": self.make_lock("2026-10-26", 110, 120, True),
        }
        result = a.outcomes(snaps)
        self.assertEqual(result["observations"][0]["result"], "missing_exact_session_snapshot")
        self.assertEqual(result["summaries"]["5"]["unverifiable"], 1)
        self.assertIsNone(result["summaries"]["5"]["mean_excess_pp"])

    def test_first_snapshot_is_seed_not_hindsight_recommendation(self):
        result = a.outcomes({"2026-10-20": self.make_lock("2026-10-20", 100, 50, True)})
        self.assertEqual(result["signal_count"], 0)
        self.assertEqual(result["summaries"]["5"]["observed"], 0)
        self.assertIsNone(result["summaries"]["5"]["observed_outperformance_fraction"])


if __name__ == "__main__":
    unittest.main()
