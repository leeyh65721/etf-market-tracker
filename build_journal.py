"""Archive a dated, public-data-only technical evidence summary after each ETF scan.

This does NOT generate macro commentary, verified ETF flows, personal allocations or trading advice.
"""
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parent
DATA = ROOT / "data"
HISTORY = DATA / "history"
OUTPUT = ROOT / "analysis" / "technical"

def fmt(value, suffix=""):
    if pd.isna(value):
        return "n/a"
    return f"{float(value):+.2f}{suffix}"

def main():
    report = json.loads((DATA / "latest.json").read_text(encoding="utf-8"))
    day = str(report["us_market_date"])
    if len(day) != 10 or day[4] != "-" or day[7] != "-" or not day.replace("-", "").isdigit():
        raise ValueError("Invalid US market date")

    current = pd.read_csv(DATA / "latest.csv")
    required = {"ticker", "asof", "screen", "return_5d_pct", "return_21d_pct",
                "return_63d_pct", "spy_excess_21d_pp", "volume_ratio_20d",
                "rank_score", "liquid_enough"}
    if not required.issubset(current.columns):
        raise ValueError("Missing essential screen columns")
    if len(current) != int(report["valid_screened_count"]) or not current["asof"].eq(day).all():
        raise ValueError("JSON/CSV mismatch or mixed market dates")
    if current["ticker"].duplicated().any():
        raise ValueError("Duplicate ticker found")
    actual_counts = current["screen"].value_counts().to_dict()

    older = sorted(p for p in HISTORY.glob("????-??-??.csv") if p.stem < day)
    previous = pd.read_csv(older[-1]) if older else None
    previous_day = older[-1].stem if older else None

    ci = current.set_index("ticker")
    pi = previous.set_index("ticker") if previous is not None else None
    cand = current[current.screen.eq("candidate")].sort_values("rank_score", ascending=False)
    current_symbols = set(cand.ticker)
    old_symbols = set(previous.loc[previous.screen.eq("candidate"), "ticker"]) if previous is not None else set()
    newly = sorted(current_symbols - old_symbols) if previous is not None else []
    dropped = sorted(old_symbols - current_symbols) if previous is not None else []
    new_rows = current[current.ticker.isin(newly)].sort_values("rank_score", ascending=False)
    lost_rows = previous[previous.ticker.isin(dropped)].sort_values("rank_score", ascending=False) if previous is not None else None

    lines = [
        f"# ETF technical evidence — US session {day}",
        "",
        "> Automated, price/volume-only research data. **Not an investment recommendation.**",
        f"- Generated at (UTC): {report.get('generated_at_utc', 'unavailable')}",
        f"- Source: {report.get('data_source','unavailable')}",
        f"- Universe: {report['candidate_universe_count']}; analyzed: {len(current)}; "
        f"invalid/unverified: {report['invalid_or_unverified_count']}",
        f"- Screens: " + "; ".join(f"{k}={actual_counts.get(k,0)}" for k in
              ["candidate","watch","watch_non_sector","excluded_illiquid","excluded_complex"]),
        f"- Previous archive session: {previous_day or 'unavailable'}",
        "",
        "## Strongest technical candidates (not buy signals)",
        "|Ticker|5d %|21d %|63d %|21d excess vs SPY (pp)|Volume / 20d avg|",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for _, x in cand.head(12).iterrows():
        lines.append(f"|{x.ticker}|{fmt(x.return_5d_pct)}|{fmt(x.return_21d_pct)}|"
                     f"{fmt(x.return_63d_pct)}|{fmt(x.spy_excess_21d_pp)}|"
                     f"{fmt(x.volume_ratio_20d)}x|")
    lines.extend(["", "## Changes since the previous archived US session"])
    if previous is None:
        lines.append("- No earlier dated archive; change signals are unavailable.")
    else:
        lines.append(f"- Became technical candidates: {len(newly)}; "
                     f"lost technical candidate status: {len(dropped)}.")
        lines.append("- Newly flagged: " + (", ".join(new_rows.ticker.head(20)) or "none"))
        lines.append("- No longer flagged: " +
                     (", ".join(lost_rows.ticker.head(20)) if not lost_rows.empty else "none"))
        lines.append("- This is a **screen transition**, not confirmation of new fundamentals.")
        lines.extend(["", "### Candidate transitions (reference only)",
                      "|Ticker|Previous screen|Current screen|21d %|SPY excess pp|",
                      "|---|---|---|---:|---:|"])
        union = list(new_rows.ticker.head(12)) + list(lost_rows.ticker.head(12))
        for symbol in union:
            before = str(pi.loc[symbol,"screen"]) if symbol in pi.index else "no data"
            after = str(ci.loc[symbol,"screen"]) if symbol in ci.index else "no data"
            x = ci.loc[symbol] if symbol in ci.index else pi.loc[symbol]
            lines.append(f"|{symbol}|{before}|{after}|{fmt(x.return_21d_pct)}|"
                         f"{fmt(x.spy_excess_21d_pp)}|")
    lines.extend([
        "", "## Important limitations / handoff to weekly analysis",
        "- All returns are USD-only. USD/KRW changes and account-level outcomes are not included.",
        "- Technical screens are based on delayed, best-effort third-party prices; no guaranteed live monitoring.",
        "- **Not provided here:** Fed/real yields, CPI/PCE, labor data, oil/gold/copper, USD, credit spreads, "
          "earnings guidance, verified ETF capital flows, valuation, bid/ask spreads, AUM and security structure.",
        "- Weekly ChatGPT research MUST independently verify material macro and cross-asset evidence, news, "
          "ETF investability and counterarguments before proposing any allocation change.",
        "- Excluded_illiquid / excluded_complex are never new-investment recommendations.",
        "- No personal portfolio sizes, positions, amounts, or P&L are stored in this repository.",
        "",
    ])
    OUTPUT.mkdir(parents=True, exist_ok=True)
    target = OUTPUT / f"{day}.md"
    target.write_text("\n".join(lines), encoding="utf-8")
    print("JOURNAL", target, "previous", previous_day or "none",
          "candidates", len(cand), "new", len(newly), "dropped", len(dropped))

if __name__ == "__main__":
    main()
