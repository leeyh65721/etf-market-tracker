"""Verify daily ETF macro coverage and save an auditable public-data health report.

Runs after macro_scan.py; no network and no account/portfolio information.
A missing, partial or older run must never be called 'healthy'.
"""
import json
import math
import os
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
MACRO = ROOT / "data" / "macro"
DIAG = ROOT / "analysis" / "diagnostics"
REQUIRED_COUNT = 22
CRITICAL = ("T2Y", "T10Y", "T10Y_REAL", "T10Y2Y", "VIX", "USD_KRW_ECB", "EFFR")
COVERAGE_CATEGORIES = {
    "treasury": ("T2Y", "T10Y", "T10Y_REAL", "T10Y2Y"),
    "inflation": ("CPI_HEADLINE", "CPI_CORE", "CPI_SHELTER", "PPI_FD"),
    "labor": ("UNRATE", "PAYROLLS", "JOLTS_OPENINGS", "LFPR",
              "AVG_HOURLY_EARNINGS", "AVG_WEEKLY_HOURS"),
    "energy": ("WTI", "BRENT"),
    "volatility": ("VIX", "VVIX"),
    "foreign_exchange": ("USD_KRW_ECB", "EUR_USD_ECB"),
    "money_markets": ("EFFR", "SOFR"),
}


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8")), None
    except (OSError, ValueError) as exc:
        return {}, f"{type(exc).__name__}: {str(exc)[:160]}"


def inspect(technical, macro):
    messages = []
    market_date = technical.get("us_market_date")
    if not market_date:
        messages.append("ETF technical scan date missing")
    if macro.get("market_date") != market_date:
        messages.append(f"Macro market date {macro.get('market_date')} does not match ETF date {market_date}")
    if macro.get("status") != "ok":
        messages.append(f"Macro status is {macro.get('status', 'missing')}, not ok")

    requested = macro.get("requested_series_count")
    reported = macro.get("retrieved_series_count")
    current = macro.get("current_series_count")
    if requested != REQUIRED_COUNT:
        messages.append(f"Requested count {requested}, expected {REQUIRED_COUNT}")

    rows = macro.get("series", [])
    if not isinstance(rows, list):
        rows = []
        messages.append("Malformed macro series collection")

    by_id = {r["series_id"]: r for r in rows if isinstance(r, dict) and isinstance(r.get("series_id"), str)}
    if len(by_id) != len(rows):
        messages.append("Duplicate or malformed macro series identifiers")
    if reported != len(rows):
        messages.append(f"Declared retrieved count {reported} does not match {len(rows)} rows")
    actual_current = sum(r.get("status") == "ok" for r in rows if isinstance(r, dict))
    if current != actual_current:
        messages.append(f"Declared current count {current} does not match {actual_current} rows")

    expected = {s for values in COVERAGE_CATEGORIES.values() for s in values}
    missing = sorted(expected - set(by_id))
    unexpected = sorted(set(by_id) - expected)
    if missing:
        messages.append("Missing required series: " + ", ".join(missing))
    if unexpected:
        messages.append("Unexpected series: " + ", ".join(unexpected))

    category_stats = {}
    for group, ids in COVERAGE_CATEGORIES.items():
        category_stats[group] = {
            "ok": sum(by_id.get(s, {}).get("status") == "ok" for s in ids),
            "required": len(ids),
            "missing_or_stale": [s for s in ids if by_id.get(s, {}).get("status") != "ok"],
        }

    for sid, row in by_id.items():
        try:
            value = float(row["value"])
            if not math.isfinite(value):
                raise ValueError("non-finite")
            observation = date.fromisoformat(row["observation_date"])
            if market_date and observation > date.fromisoformat(market_date):
                messages.append(f"{sid} observation date after market date")
            if not str(row.get("source_url", "")).startswith("https://"):
                messages.append(f"{sid} missing direct HTTPS source URL")
        except (TypeError, ValueError, KeyError) as exc:
            messages.append(f"{sid} invalid numeric value/date: {type(exc).__name__}")

    technical_generated = technical.get("generated_at_utc", "")
    macro_generated = macro.get("generated_at_utc", "")
    try:
        t = datetime.fromisoformat(technical_generated.replace("Z", "+00:00"))
        m = datetime.fromisoformat(macro_generated.replace("Z", "+00:00"))
        if m < t:
            messages.append("Macro data generated BEFORE current ETF technical scan: likely stale")
    except (TypeError, ValueError):
        messages.append("Missing or invalid source generation timestamps")

    errors = macro.get("errors", {})
    if not isinstance(errors, dict):
        errors = {}
        messages.append("Malformed error dictionary")
    if errors:
        messages.append(f"Source failures: {len(errors)}")

    non_ok = [s for s, r in by_id.items() if r.get("status") != "ok"]
    if non_ok:
        messages.append("Stale/unusable observations: " + ", ".join(sorted(non_ok)))
    missing_critical = [s for s in CRITICAL if by_id.get(s, {}).get("status") != "ok"]
    if missing_critical:
        messages.append("Critical market series not current: " + ", ".join(missing_critical))

    if not market_date or not macro.get("generated_at_utc") or not rows:
        state = "ERROR"
    elif messages:
        state = "WARN"
    else:
        state = "OK"
    return {
        "status": state,
        "market_date": market_date,
        "source_macro_status": macro.get("status", "missing"),
        "requested": requested,
        "retrieved": len(rows),
        "current": actual_current,
        "critical_missing": missing_critical,
        "categories": category_stats,
        "messages": messages,
        "source_errors": errors,
        "macro_generated_at_utc": macro_generated,
        "technical_generated_at_utc": technical_generated,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "important_note": "Data collection health only; not a statement about market risk. Publication and revision lag still require verification.",
    }


def write_report(result):
    DIAG.mkdir(parents=True, exist_ok=True)
    MACRO.mkdir(parents=True, exist_ok=True)
    (MACRO / "health_latest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# ETF 거시경제 자동 수집 품질 점검", "",
        f"- 품질 상태: **{result['status']}**",
        f"- 미국 시장 기준일: {result['market_date']}",
        f"- 점검 시각 UTC: {result['checked_at_utc']}",
        f"- 거시 수집 생성 시각 UTC: {result['macro_generated_at_utc']}",
        f"- 기술 데이터 생성 시각 UTC: {result['technical_generated_at_utc']}",
        f"- 요청/수집/시차 기준 정상: **{result['requested']} / {result['retrieved']} / {result['current']}**", "",
        "## 분야별 수집 상태", "",
        "| 분야 | 정상 | 요청 | 누락 또는 오래됨 |",
        "|---|---:|---:|---|",
    ]
    for group, item in result["categories"].items():
        lines.append(f"| {group} | {item['ok']} | {item['required']} | {', '.join(item['missing_or_stale']) or '-'} |")
    lines += ["", "## 발견한 문제", ""]
    if not result["messages"]:
        lines.append("- 자동 품질 검사상 이상 없음. 시장이 안전하다는 의미는 아님.")
    else:
        lines += [f"- {s}" for s in result["messages"]]
    lines += ["", "## 원출처 오류", ""]
    if result["source_errors"]:
        lines += [f"- {k}: {str(v)[:160]}" for k, v in result["source_errors"].items()]
    else:
        lines.append("- 없음")
    lines += ["", "## 사용 시 주의", "",
              "- 수집 수치는 지표별 관측일과 발표일이 다를 수 있고 수정될 수 있음.",
              "- 하이일드 회사채 ETF 가격수익률 차이는 실제 신용스프레드/OAS가 아님.",
              "- 보유계좌·현금·개인 수익률은 공개 저장소에 기록하지 않음.", ""]
    rendered = "\n".join(lines)
    (DIAG / "macro-health-latest.md").write_text(rendered, encoding="utf-8")
    if result["market_date"]:
        history = DIAG / "history"
        history.mkdir(parents=True, exist_ok=True)
        (history / f"{result['market_date']}.md").write_text(rendered, encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(rendered + "\n")
    print(f"MACRO_HEALTH {result['status']} {result['current']}/{REQUIRED_COUNT}", flush=True)
    for msg in result["messages"]:
        print(f"::warning::{msg.replace(chr(10), ' ')}", flush=True)


def main():
    technical, technical_error = read_json(ROOT / "data" / "latest.json")
    macro, macro_error = read_json(MACRO / "latest.json")
    result = inspect(technical, macro)
    for step_name in ("ETF_SCAN_OUTCOME", "MACRO_COLLECTION_OUTCOME"):
        outcome = os.environ.get(step_name)
        if outcome and outcome != "success":
            result["messages"].append(f"GitHub Actions step {step_name} = {outcome}")
            result["status"] = "ERROR"
    for issue in (technical_error, macro_error):
        if issue:
            result["messages"].append(issue)
            result["status"] = "ERROR"
    write_report(result)


if __name__ == "__main__":
    main()
