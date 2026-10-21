"""Prospective ETF technical-screen audit, without hindsight or brokerage data.

Frozen daily first-seen screens make mechanical signals inspectable in later weeks.
A screen is NOT the assistant's investment recommendation or a feasible order fill.
Hypothetical next-session CLOSE to a later CLOSE is only a research price proxy.
"""
from __future__ import annotations

import json
import math
from datetime import date, datetime, timezone
from pathlib import Path

import exchange_calendars as calendars
import pandas as pd

ROOT = Path(__file__).parent
DATA = ROOT / "data"
LOCKS = DATA / "quality" / "snapshots"
RESULTS = DATA / "quality"
REPORTS = ROOT / "analysis" / "quality"
XNYS = calendars.get_calendar("XNYS")
HORIZONS = (5, 10, 20)
VALID_SCREENS = {"candidate", "watch", "watch_non_sector",
                 "excluded_illiquid", "excluded_complex"}
COVERAGE_WARN = .85
SCHEMA = "etf_screen_freeze_v1"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def session(day):
    d = pd.Timestamp(str(day))
    if not XNYS.is_session(d):
        raise ValueError(f"Not an NYSE trading session: {day}")
    return d


def offset(day, sessions):
    return XNYS.session_offset(session(day), sessions).date().isoformat()


def utc(value):
    t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError("Naive generated_at timestamp")
    return t.astimezone(timezone.utc)


def require_number(val, description, positive=False):
    try:
        v = float(val)
    except (ValueError, TypeError):
        raise ValueError(f"{description} is not numeric") from None
    if not math.isfinite(v) or (positive and v <= 0):
        raise ValueError(f"{description} is invalid/nonpositive")
    return v


def current_first_published(source_json, source_csv):
    """Validate the daily publication BEFORE writing any permanent audit baseline."""
    src = read(source_json)
    day = str(src.get("us_market_date", ""))
    close_utc = XNYS.session_close(session(day)).to_pydatetime()
    generated = utc(src.get("generated_at_utc"))
    if generated < close_utc:
        raise ValueError(f"ETF scan timestamp predates the NYSE close for {day}")

    frame = pd.read_csv(source_csv, keep_default_na=True)
    required = {"ticker", "asof", "screen", "close_usd", "liquid_enough",
                "rank_score", "return_5d_pct", "return_21d_pct", "spy_excess_21d_pp"}
    if not required.issubset(frame.columns):
        raise ValueError("ETF scanner CSV missing required fields")
    if frame.empty or frame.ticker.isna().any() or frame.ticker.duplicated().any():
        raise ValueError("ETF scanner CSV empty or has missing/duplicate tickers")
    if not frame.asof.astype(str).eq(day).all():
        raise ValueError("ETF scanner CSV has a different market date")
    if not frame.screen.isin(VALID_SCREENS).all():
        raise ValueError("ETF scanner CSV contains unrecognized statuses")
    if len(frame) != src.get("valid_screened_count"):
        raise ValueError("ETF CSV row count disagrees with JSON")
    if int(frame.screen.eq("candidate").sum()) != src.get("technical_candidate_count"):
        raise ValueError("ETF CSV candidate count disagrees with JSON")
    if src.get("candidate_universe_count", 0) < len(frame):
        raise ValueError("Screened universe exceeds declared universe")
    if "SPY" not in set(frame.ticker):
        raise ValueError("Missing SPY benchmark in ETF scanner CSV")

    tickers = {}
    for x in frame.itertuples(index=False):
        close = require_number(x.close_usd, f"{x.ticker} close", positive=True)
        score = require_number(x.rank_score, f"{x.ticker} score")
        if isinstance(x.liquid_enough, str):
            if x.liquid_enough.lower() not in {"true", "false"}:
                raise ValueError(f"{x.ticker} has unrecognized liquidity flag")
            liquid = x.liquid_enough.lower() == "true"
        else:
            liquid = bool(x.liquid_enough)
        if x.screen == "candidate" and not liquid:
            raise ValueError(f"Illiquid candidate {x.ticker}")
        tickers[str(x.ticker)] = {
            "close_usd": round(close, 3),
            "screen": str(x.screen),
            "liquid": liquid,
            "score": round(score, 3),
        }
    return {
        "schema": SCHEMA,
        "us_market_date": day,
        "first_published_scan_generated_at_utc": generated.isoformat(),
        "source": src.get("data_source", "unverified source"),
        "universe_count": int(src["candidate_universe_count"]),
        "verified_count": len(tickers),
        "tickers": tickers,
        "new_technical_entries": [],
        "exclusion_note": "Technical candidate status is not analyst advice or a trade order.",
    }


def write_lock_if_missing(current, locks_dir=LOCKS):
    """A same-day rerun must NOT quietly rewrite past price/signal baselines."""
    locks_dir = Path(locks_dir)
    locks_dir.mkdir(parents=True, exist_ok=True)
    day = current["us_market_date"]
    p = locks_dir / (day + ".json")
    if p.exists():
        prior = read(p)
        if prior.get("schema") != SCHEMA or prior.get("us_market_date") != day:
            raise ValueError("Existing first-published lock is invalid")
        return prior, False

    prior_path = locks_dir / (offset(day, -1) + ".json")
    if prior_path.exists():
        prior = read(prior_path)
        if prior.get("schema") != SCHEMA:
            raise ValueError("Previous market session lock has incompatible schema")
        for symbol, row in current["tickers"].items():
            before = prior.get("tickers", {}).get(symbol)
            if (before is not None and before["screen"] != "candidate"
                and row["screen"] == "candidate" and row["liquid"]):
                current["new_technical_entries"].append({
                    "ticker": symbol,
                    "entry_signal_date": day,
                    "first_published_close_usd": row["close_usd"],
                    "initial_score": row["score"],
                    "previous_screen": before["screen"],
                })
        current["new_technical_entries"].sort(key=lambda x: x["ticker"])

    # Only atomically create absent file; avoid overwriting during same-day reruns.
    try:
        with p.open("x", encoding="utf-8") as out:
            json.dump(current, out, ensure_ascii=False, indent=2, allow_nan=False)
            out.write("\n")
    except FileExistsError:
        return read(p), False
    return current, True


def all_locks(locks_dir=LOCKS):
    locked = {}
    for p in sorted(Path(locks_dir).glob("????-??-??.json")):
        obj = read(p)
        day = obj.get("us_market_date")
        if obj.get("schema") != SCHEMA or day != p.stem:
            raise ValueError(f"Invalid frozen audit record {p.name}")
        session(day)
        if day in locked:
            raise ValueError("Duplicate market-session locks")
        if not isinstance(obj.get("tickers"), dict):
            raise ValueError("Frozen price data not a dictionary")
        locked[day] = obj
    return locked


def pair_return(start, end, symbol):
    first = start.get("tickers", {}).get(symbol)
    last = end.get("tickers", {}).get(symbol)
    if first is None or last is None:
        raise KeyError(f"{symbol} absent in one of the frozen snapshots")
    p0 = require_number(first["close_usd"], f"{symbol} baseline", positive=True)
    p1 = require_number(last["close_usd"], f"{symbol} horizon", positive=True)
    return round((p1 / p0 - 1) * 100, 5)


def outcomes(locked, horizons=HORIZONS):
    """Evaluate only original transitions at exact NYSE sessions.

    Entry proxy: next NYSE session CLOSE, unavailable on the signal day.
    Exit proxy: N NYSE sessions after that entry proxy.
    This deliberately avoids assuming a trade at the signal day's close.
    """
    days = sorted(locked)
    if not days:
        return {"asof": None, "locked_sessions": 0, "signal_count": 0,
                "summaries": {}, "observations": []}
    newest = days[-1]
    result = []
    for day in days:
        for signal in locked[day].get("new_technical_entries", []):
            ticker = signal["ticker"]
            if ticker not in locked[day]["tickers"] or locked[day]["tickers"][ticker]["screen"] != "candidate":
                raise ValueError("Frozen technical entry has inconsistent candidate status")
            entry_day = offset(day, 1)
            for n in horizons:
                exit_day = offset(entry_day, n)
                row = {"signal_day": day, "ticker": ticker, "sessions_held": n,
                       "reference_entry_day": entry_day, "reference_exit_day": exit_day,
                       "result": "pending"}
                if exit_day <= newest:
                    if entry_day not in locked or exit_day not in locked:
                        row["result"] = "missing_exact_session_snapshot"
                    else:
                        try:
                            a = pair_return(locked[entry_day], locked[exit_day], ticker)
                            b = pair_return(locked[entry_day], locked[exit_day], "SPY")
                            row.update(result="observed",
                                       etf_price_return_pct=a, spy_price_return_pct=b,
                                       excess_vs_spy_pp=round(a - b, 5),
                                       outperform_spy=a > b)
                        except (KeyError, ValueError) as exc:
                            row["result"] = "unverified_price"
                            row["reason"] = str(exc)[:140]
                result.append(row)
    summaries = {}
    for n in horizons:
        parts = [x for x in result if x["sessions_held"] == n]
        good = [x for x in parts if x["result"] == "observed"]
        missing = sum(x["result"] in ("missing_exact_session_snapshot", "unverified_price")
                      for x in parts)
        excesses = [x["excess_vs_spy_pp"] for x in good]
        summaries[str(n)] = {
            "signals": len(parts),
            "observed": len(good),
            "pending": sum(x["result"] == "pending" for x in parts),
            "unverifiable": missing,
            "outperformed_spy_count": sum(x["outperform_spy"] for x in good),
            "observed_outperformance_fraction": (
                round(sum(x["outperform_spy"] for x in good) / len(good), 5) if good else None
            ),
            "mean_excess_pp": round(sum(excesses) / len(good), 5) if good else None,
            "median_excess_pp": round(float(pd.Series(excesses).median()), 5) if good else None,
            "assessment": "exploratory_only" if len(good) >= 30 else "insufficient_observations",
        }
    return {"asof": newest, "locked_sessions": len(days),
            "signal_count": sum(len(locked[d].get("new_technical_entries", [])) for d in days),
            "summaries": summaries, "observations": result}


def latest_closed_session(now=None):
    now = now or datetime.now(timezone.utc)
    today = now.date()
    low = pd.Timestamp(today) - pd.Timedelta(days=15)
    high = pd.Timestamp(today) + pd.Timedelta(days=1)
    dates = XNYS.sessions_in_range(low, high)
    matches = [d for d in dates if XNYS.session_close(d).to_pydatetime() <= now]
    return matches[-1].date().isoformat() if matches else None


def main():
    current = current_first_published(DATA / "latest.json", DATA / "latest.csv")
    locked, created = write_lock_if_missing(current)
    state = outcomes(all_locks())
    expected = latest_closed_session()
    warnings = []
    if expected and state["asof"] < expected:
        elapsed = XNYS.sessions_in_range(pd.Timestamp(state["asof"]), pd.Timestamp(expected))
        missed = len(elapsed) - 1
        if missed > 1:
            warnings.append(f"Market audit snapshots lag latest closed NYSE session by {missed} sessions")
    coverage = locked["verified_count"] / max(locked["universe_count"], 1)
    if coverage < COVERAGE_WARN:
        warnings.append(f"Only {coverage:.1%} of universe had validated price/screen data")
    state.update({
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "new_daily_lock_created": created,
        "locked_current_us_date": locked["us_market_date"],
        "current_technical_candidate_entries": len(locked["new_technical_entries"]),
        "latest_verified_universe_fraction": round(coverage, 5),
        "last_expected_closed_us_session": expected,
        "warnings": warnings,
        "status": "WARN" if warnings else "OK",
        "interpretation": (
            "Audit of technical-screen transitions ONLY, not ChatGPT ETF buy/hold recommendations. "
            "Next-session-close to subsequent-close is an observation proxy, NOT a tradable fill. "
            "The Yahoo auto-adjusted closes in separate frozen downloads may be revised around "
            "distributions, splits and provider corrections. Do not claim total-return accuracy, "
            "causality, live execution, or strategy superiority. No fees, FX or slippage included. "
            "A prospective sample of 30+ observations is exploratory, not proof."
        ),
    })
    RESULTS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / "latest.json"
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2,
                               allow_nan=False) + "\n", encoding="utf-8")
    lines = [
        "# ETF technical screen prospective accuracy audit", "",
        "> **Not investment recommendations or a trading backtest.**",
        f"- Latest locked US session: **{state['asof']}**",
        f"- Verified universe coverage: **{coverage:.1%}**",
        f"- Preserved NYSE sessions: **{state['locked_sessions']}**",
        f"- Recorded new candidate transitions: **{state['signal_count']}**",
        f"- New locked baseline created on this execution: **{created}**",
        f"- Audit status (data quality only): **{state['status']}**", "",
        "## Observation-to-observation results", "",
        "| Holding window | Signals | Observed | Awaiting maturity | Unverifiable | Beat SPY | Mean excess | Interpretation |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for n, row in state["summaries"].items():
        excess = f"{row['mean_excess_pp']:+.3f}pp" if row["mean_excess_pp"] is not None else "n/a"
        lines.append(
            f"|{n} NYSE sessions|{row['signals']}|{row['observed']}|{row['pending']}|"
            f"{row['unverifiable']}|{row['outperformed_spy_count']}/{row['observed']}|"
            f"{excess}|{row['assessment']}|"
        )
    lines += [
        "", "## Freshness and quality concerns", "",
        *(["- " + w for w in warnings] if warnings else ["- None identified in the mechanical check."]),
        "", "## Evaluation rules", "",
        "- NYSE trading calendar is used, not calendar or weekday approximations.",
        "- Capture is frozen at first successful GitHub publishing day; same-day reruns do not overwrite the locked baseline.",
        "- Only NEW technical-candidate transitions after a known consecutive prior NYSE session are evaluated. First archived session only seeds the baseline.",
        "- Signal becomes known AFTER its market-session close; entry reference = the NEXT NYSE session CLOSE; exit reference = exact 5/10/20 NYSE sessions after this.",
        "- If the reference day is missing, result is explicitly unverifiable, never interpolated.",
        "- Relative return uses frozen Yahoo auto-adjusted close snapshots; corporate actions and later provider revisions can distort comparability.",
        "- Technical labels are not ChatGPT investment recommendations; no actual portfolio, orders, FX, costs or P&L.",
        "- Until enough future observations mature, there is **no supported predictive accuracy estimate**.",
        "",
    ]
    (REPORTS / "latest.md").write_text("\n".join(lines), encoding="utf-8")
    print("SIGNAL_AUDIT", state["status"], state["asof"],
          "baseline_created", created, "new_transitions",
          state["current_technical_candidate_entries"],
          "matured", {n: s["observed"] for n, s in state["summaries"].items()}, flush=True)


if __name__ == "__main__":
    main()
