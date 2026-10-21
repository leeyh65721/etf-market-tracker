"""Evidence-anchored, public-only ETF research judgment archive.

A human/ChatGPT analysis must first be saved to its dated public research report.
The nightly job validates authored decisions; it NEVER fabricates a recommendation
from technical candidate screens. Old reports archived later are flagged as such.
User-specific account exposure, allocation percentages and orders are prohibited.
"""
from __future__ import annotations

import csv
import json
import math
import re
from datetime import date, datetime, timezone
from pathlib import Path

import exchange_calendars as calendars
import pandas as pd

ROOT=Path(__file__).parent
ENTRIES=ROOT/"analysis"/"decisions"/"entries"
INDEX=ROOT/"data"/"decisions"
REPORTS=ROOT/"analysis"/"decisions"
XNYS=calendars.get_calendar("XNYS")
SCHEMA="public_etf_judgment_v1"
STANCES={"watch","watch_weaker","avoid","positive_watch","no_new_candidate"}
PROVENANCE={"retrospective_archived_report","contemporaneous_report"}
REPORT_PATTERN=re.compile(r"analysis/(daily|events|weekly)/[0-9A-Za-z_.-]+\.md")
SYMBOL_PATTERN=re.compile(r"[A-Z][A-Z0-9.-]{0,9}")

def read(path):
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)

def number(v,caption):
    if isinstance(v,bool):
        raise ValueError(f"{caption} should not be a boolean")
    try:f=float(v)
    except (ValueError,TypeError):raise ValueError(f"{caption} must be numeric") from None
    if not math.isfinite(f) or f<=0:
        raise ValueError(f"{caption} not a positive finite number")
    return f

def session(d):
    x=pd.Timestamp(d)
    if not XNYS.is_session(x):
        raise ValueError(f"Not a valid NYSE market date: {d}")
    return x

def session_plus(d,n):
    return XNYS.session_offset(session(d),n).date().isoformat()

def asof_close(root,day,ticker):
    path=Path(root)/"data"/"history"/f"{day}.csv"
    if not path.is_file():
        raise ValueError(f"Missing original dated ETF price file: {path.name}")
    with path.open(newline="",encoding="utf-8") as fp:
        rows=[x for x in csv.DictReader(fp) if x.get("ticker")==ticker and x.get("asof")==day]
    if len(rows)!=1:
        raise ValueError(f"Missing/duplicate {ticker} close for {day}")
    return number(rows[0].get("close_usd"),f"{ticker} saved close")

def check_entry(item,root=ROOT):
    root=Path(root)
    if item.get("schema")!=SCHEMA:
        raise ValueError("Unsupported decision-archive schema")
    rid=str(item.get("record_id",""))
    if not re.fullmatch(r"20\d\d-\d\d-\d\d-[A-Z0-9.-]+-[a-z0-9-]+",rid):
        raise ValueError("Invalid record ID")
    symbol=str(item.get("ticker",""))
    if not SYMBOL_PATTERN.fullmatch(symbol):
        raise ValueError("Invalid ETF symbol")
    stance=item.get("stance")
    if stance not in STANCES:
        raise ValueError("Stance not in controlled public vocabulary")
    if stance=="no_new_candidate" and symbol!="MARKET":
        raise ValueError("No-new-candidate record must use MARKET")
    if symbol=="MARKET" and stance!="no_new_candidate":
        raise ValueError("MARKET is only valid for no-new-candidate statements")
    market=str(item.get("us_market_date",""))
    session(market)
    kst=str(item.get("original_report_date_kst",""))
    if date.fromisoformat(kst)<date.fromisoformat(market):
        raise ValueError("Published Korea date before underlying US market date")
    archived=str(item.get("archived_on_utc_date",""))
    if date.fromisoformat(archived)<date.fromisoformat(kst):
        # KST publication could occur just before UTC date turnover, but UTC date
        # cannot be several days before it; accept at most one day offset.
        if (date.fromisoformat(kst)-date.fromisoformat(archived)).days>1:
            raise ValueError("Archive date cannot predate the report date by >1 day")
    if item.get("provenance") not in PROVENANCE:
        raise ValueError("Must distinguish later archival from contemporaneous record")
    if item["provenance"]=="contemporaneous_report":
        delta=(date.fromisoformat(archived)-date.fromisoformat(kst)).days
        if delta>1 or delta< -1:
            raise ValueError("Old saved report cannot be called prospective")
    source=item.get("source_report","")
    if not REPORT_PATTERN.fullmatch(str(source)):
        raise ValueError("Must reference dated public research report, not private content")
    src=root/source
    if not src.is_file():
        raise ValueError("Original report missing from public archive")
    text=src.read_text(encoding="utf-8")
    excerpt=str(item.get("verbatim_source_excerpt",""))
    if len(excerpt)<14 or excerpt not in text:
        raise ValueError("Specific original text excerpt not found in stored report")
    if symbol not in excerpt and symbol not in str(item.get("thesis","")):
        raise ValueError("ETF not anchored to original report excerpt")
    if str(kst) not in src.name:
        # Events may have US date in title; verify explicit report day for dated daily/weekly files.
        if source.startswith("analysis/daily/"):
            raise ValueError("Daily report filename does not match report date")
    for name in ("thesis","counterevidence","invalidation","revisit_trigger"):
        if not isinstance(item.get(name),str) or len(item[name].strip())<12:
            raise ValueError(f"{name}: original decision must be falsifiable")
    for name in ("thesis","counterevidence","invalidation","revisit_trigger"):
        value=item[name]
        if any(ch in value for ch in ("\r","\x00")):
            raise ValueError("Invalid control characters")
    forbidden_fields={"user_holdings","personal_allocations","account_value","cash_balance",
                      "profit_loss","order","user_portfolio","target_allocation"}
    if forbidden_fields & set(item):
        raise ValueError("Private account values must never enter the public ledger")
    if item.get("trade_instruction",None) is not False:
        raise ValueError("The public market observation cannot be a trade instruction")
    if item.get("comparison_baseline")!="SPY":
        raise ValueError("SPY benchmark must be explicit")
    if symbol!="MARKET":
        initial=number(item.get("original_close_usd"),"original ETF baseline")
        benchmark=number(item.get("original_spy_close_usd"),"original SPY baseline")
        exact=asof_close(root,market,symbol)
        spy=asof_close(root,market,"SPY")
        if abs(initial-exact)>.015:
            raise ValueError("ETF baseline does not match contemporaneous saved scanner close")
        if abs(benchmark-spy)>.015:
            raise ValueError("SPY baseline does not match same-date saved scanner close")
    elif any(k in item for k in ("original_close_usd","original_spy_close_usd")):
        raise ValueError("MARKET no-new-idea record must not fabricate ETF prices")
    if item.get("review_horizons_nyse_sessions")!=[5,10,20]:
        raise ValueError("Must preserve objective 5/10/20 NYSE sessions")
    # Retrospectively archived calls may be useful context but CANNOT claim
    # prospectively captured decision accuracy.
    eligible=item["provenance"]=="contemporaneous_report"
    return {
        "record_id":rid,"ticker":symbol,"stance":stance,
        "us_market_date":market,"original_report_date_kst":kst,
        "archived_on_utc_date":archived,"provenance":item["provenance"],
        "source_report":source,"original_close_usd":item.get("original_close_usd"),
        "original_spy_close_usd":item.get("original_spy_close_usd"),
        "thesis":item["thesis"],"counterevidence":item["counterevidence"],
        "invalidation":item["invalidation"],"revisit_trigger":item["revisit_trigger"],
        "review_horizons_nyse_sessions":[5,10,20],
        "first_theoretical_reference_session":session_plus(market,1),
        "eligible_for_prospective_judgment_scoring":eligible,
        "assessment":"awaiting_forward_observation" if eligible else
                     "historical_backfill_not_prospectively_scored",
        "not_a_buy_recommendation":True,
    }

def collect(root=ROOT):
    root=Path(root)
    entries=[]
    errors=[]
    directory=root/"analysis"/"decisions"/"entries"
    for path in sorted(directory.glob("*.json")):
        try:
            obj=read(path)
            row=check_entry(obj,root)
            if path.stem!=row["record_id"]:
                raise ValueError("Record ID must match immutable filename")
            entries.append(row)
        except (OSError,ValueError,TypeError,KeyError) as exc:
            errors.append({"file":path.name,"error":f"{type(exc).__name__}: {str(exc)[:230]}"})
    keys=[r["record_id"] for r in entries]
    if len(keys)!=len(set(keys)):
        errors.append({"file":"<all>","error":"Duplicate research judgment identifier"})
    tracked={x["source_report"] for x in entries}
    unindexed=[]
    for p in sorted((root/"analysis"/"daily").glob("????-??-??.md")):
        source=p.relative_to(root).as_posix()
        if source not in tracked:
            unindexed.append(source)
    return entries,errors,unindexed

def render(d):
    lines=["# ETF 분석 판단 보존 원장","",
           "> 실제 분석에 적힌 표현과 기준가격을 대조한 공개 시장연구 원장. "
           "자동 스크리너 후보·사용자 거래와 구분.",
           f"- 유효하게 연결된 의견: **{d['valid_count']}건**",
           f"- 원문을 사후 보관해 적중률 산정이 불가능한 의견: **{d['retrospective_count']}건**",
           f"- 형식·출처 확인 실패: **{d['invalid_count']}건**",
           f"- 구조화되지 않은 일일 분석 파일: **{d['reports_missing_structured_records_count']}개**",
           f"- 상태: **{d['status']}**","",
           "|기록|ETF|당시 결론|기준 미국장|원문 날짜|보존 시점|향후 검증 자격|",
           "|---|---|---|---|---|---|---|"]
    for r in d["entries"]:
        lines.append(f"|{r['record_id']}|{r['ticker']}|{r['stance']}|{r['us_market_date']}|"
                     f"{r['original_report_date_kst']}|{r['archived_on_utc_date']}|"
                     f"{'prospective' if r['eligible_for_prospective_judgment_scoring'] else 'backfill/no hit rate'}|")
    lines.extend(["","## 아직 독립 기록이 없는 보고서",""])
    lines.extend("- "+s for s in d["reports_missing_structured_records"])
    if not d["reports_missing_structured_records"]:
        lines.append("- 없음")
    lines.extend(["","## 검증 오류",""])
    lines.extend([f"- {e['file']}: {e['error']}" for e in d["errors"]] or ["- 없음"])
    lines.extend(["","**운영 원칙:** GitHub와 연결된 일일·주간 ChatGPT 분석은 실제 새 공개 판단마다"
                  " 별도 구조화 기록을 저장하고 반드시 재조회해 검증해야 함. "
                  "보고서 저장 실패는 판단 기록 성공으로 취급하지 않음.",
                  "이전 날짜 보고를 나중에 구조화한 항목은 사후 기록으로 분류하며, "
                  "자신의 과거 예측 적중 사례로 계산하지 않음. 개인 계좌 정보는 저장 금지.",""])
    return "\n".join(lines)

def main():
    entries,errors,missing=collect()
    status="ERROR" if errors else "WARN" if missing else "OK"
    result={
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "status":status,"valid_count":len(entries),
        "retrospective_count":sum(r["provenance"]=="retrospective_archived_report" for r in entries),
        "prospective_count":sum(r["eligible_for_prospective_judgment_scoring"] for r in entries),
        "invalid_count":len(errors),
        "reports_missing_structured_records_count":len(missing),
        "reports_missing_structured_records":missing,
        "entries":entries,
        "errors":errors,
        "limitations":[
           "This is a ledger of manually saved dated public analyst research, not an automatically generated view.",
           "Past analysis uploaded afterward is NOT a validated forward-only call.",
           "Prospective results must be scored only after genuine future US sessions mature.",
           "Technical scanner candidates are separate from explicitly expressed judgments.",
           "No actual brokerage positions, targets, trades, fees or P&L are stored here.",
        ],
    }
    INDEX.mkdir(parents=True,exist_ok=True)
    REPORTS.mkdir(parents=True,exist_ok=True)
    (INDEX/"latest.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    (REPORTS/"ledger_latest.md").write_text(render(result),encoding="utf-8")
    for issue in errors:
        print("::error::Invalid ETF judgment entry:",issue["file"],issue["error"],flush=True)
    for issue in missing:
        print("::warning::Daily report lacks structured judgment archive:",issue,flush=True)
    print("DECISION_ARCHIVE",result["status"],len(entries),"valid",
          len(missing),"unindexed reports",flush=True)

if __name__=="__main__":
    main()
