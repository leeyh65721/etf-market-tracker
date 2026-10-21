"""Validate manually source-checked industry fundamentals; never synthesize earnings.

Only structured issuer filings and official-release records placed in data/industry/events
are summarized. It does not scrape company data or invent orders/inventory when absent.
"""
from __future__ import annotations
import json
import math
import re
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
import exchange_calendars as ec
import pandas as pd

ROOT=Path(__file__).parent
RECORDS=ROOT/"data"/"industry"/"events"
OUT=ROOT/"data"/"industry"
DOC=ROOT/"analysis"/"industry"
CAL=ec.get_calendar("XNYS")
VALID_STATUS={"final_reported","preliminary_unaudited","management_guidance","revision"}
NUMERIC_UNITS={"USD billion","USD million","USD thousand","%","units","million units",
               "billion units","million USD","billion USD","days","basis points"}
VALID_CLASS={"revenue","gross_margin","operating_margin","new_orders","inventory",
             "backlog","shipments","capex","cash_flow","guidance","other"}


def parse_time(value):
    t=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if t.tzinfo is None:
        raise ValueError("Issuer publication timestamp has no timezone")
    return t.astimezone(timezone.utc)


def earliest_session(source_time):
    """Earliest US session able to react, not proof that any ETF actually reacted."""
    published=parse_time(source_time)
    local=published.astimezone(ZoneInfo("America/New_York"))
    day=pd.Timestamp(str(local.date()))
    if CAL.is_session(day):
        if published<=CAL.session_close(day).to_pydatetime():
            return local.date().isoformat()
        return CAL.session_offset(day,1).date().isoformat()
    later=CAL.date_to_session(day,direction="next")
    return later.date().isoformat()


def number(value,what):
    if isinstance(value,bool):
        raise ValueError(f"{what} is Boolean, not a financial quantity")
    try:x=float(value)
    except (ValueError,TypeError):
        raise ValueError(f"{what} is not numeric") from None
    if not math.isfinite(x):
        raise ValueError(f"{what} is not finite")
    return x


def range_values(obj,prefix):
    lo=number(obj[prefix+"_low"],prefix+" low")
    hi=number(obj[prefix+"_high"],prefix+" high")
    if lo>hi:
        raise ValueError(f"{prefix} low > high")
    return (lo,hi)


def validate_event(obj):
    if not isinstance(obj,dict):
        raise ValueError("Issuer event must be JSON object")
    required=["event_id","issuer","ticker","industry","published_at_utc",
              "period_label","primary_source_url","source_type","source_checked_date",
              "reporting_status","metrics","not_disclosed","related_etfs",
              "transmission_hypothesis","counterevidence","recheck_trigger"]
    absent=[x for x in required if x not in obj]
    if absent:
        raise ValueError("Missing issuer record fields: "+",".join(absent))
    id_=str(obj["event_id"])
    if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}-[a-z0-9][a-z0-9-]{3,100}",id_):
        raise ValueError("Issuer event id must start with YYYY-MM-DD-")
    if not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}",str(obj["ticker"])):
        raise ValueError("Ticker symbol invalid")
    publication=parse_time(obj["published_at_utc"])
    stamp=date.fromisoformat(obj["source_checked_date"])
    if stamp<publication.date():
        raise ValueError("Evidence claimed checked before issuer publication")
    if obj["reporting_status"] not in VALID_STATUS:
        raise ValueError("Unrecognized preliminary/final evidence classification")
    url=str(obj["primary_source_url"])
    parsed=urlparse(url)
    host=(parsed.hostname or "").lower()
    if parsed.scheme!="https" or host not in ("sec.gov","www.sec.gov") and not host.endswith(".sec.gov"):
        raise ValueError("Currently accepted primary industry evidence must be SEC EDGAR https source")
    if obj["source_type"]!="SEC_EDGAR":
        raise ValueError("Only SEC_EDGAR issuer filings accepted in this first controlled implementation")
    if not parsed.path.startswith("/Archives/edgar/"):
        raise ValueError("SEC archive exhibit URL missing")
    if not isinstance(obj["metrics"],list) or not obj["metrics"]:
        raise ValueError("Must provide at least one reported, numeric compared metric")
    metrics=[]
    for metric in obj["metrics"]:
        if metric.get("category") not in VALID_CLASS:
            raise ValueError("Metric category not an observed industry fundamental")
        name=str(metric.get("name",""))
        if not name or len(name)>100:
            raise ValueError("Metric name invalid")
        if metric.get("unit") not in NUMERIC_UNITS:
            raise ValueError("Undeclared financial metric unit")
        a=range_values(metric,"current")
        b=range_values(metric,"comparison")
        basis=str(metric.get("comparison_basis",""))
        if not basis or not isinstance(metric.get("source_label"),str):
            raise ValueError("Metric comparison must identify actual basis and source label")
        c_mid=(a[0]+a[1])/2
        p_mid=(b[0]+b[1])/2
        unit=metric["unit"]
        result={
            "name":name,"category":metric["category"],"unit":unit,
            "current_range":[a[0],a[1]],"comparison_range":[b[0],b[1]],
            "current_midpoint":round(c_mid,6),"comparison_midpoint":round(p_mid,6),
            "midpoint_change":round(c_mid-p_mid,6),
            "comparison_basis":basis,"source_label":metric["source_label"],
            "provisional":obj["reporting_status"]!="final_reported",
        }
        if unit=="%" or unit=="basis points":
            result["midpoint_change_unit"]="percentage points" if unit=="%" else "basis points"
        else:
            result["midpoint_change_unit"]=unit
            if p_mid!=0:
                result["relative_midpoint_change_pct"]=round((c_mid/p_mid-1)*100,4)
        metrics.append(result)
    missing=obj["not_disclosed"]
    if not isinstance(missing,list) or not all(isinstance(x,str) and x for x in missing):
        raise ValueError("Missing/incomplete explicit not_disclosed list")
    etfs=obj["related_etfs"]
    if not isinstance(etfs,list) or not all(re.fullmatch("[A-Z0-9.-]{1,10}",x) for x in etfs):
        raise ValueError("related_etfs must be ticker strings")
    if (not isinstance(obj["counterevidence"],list) or not obj["counterevidence"]
            or not all(isinstance(x,str) and x.strip() for x in obj["counterevidence"])):
        raise ValueError("Missing actual counterevidence/uncertainties")
    for field in ["issuer","industry","period_label","transmission_hypothesis",
                  "recheck_trigger"]:
        if not isinstance(obj[field],str) or not obj[field].strip():
            raise ValueError(f"{field} is blank")
    eligible=earliest_session(obj["published_at_utc"])
    return {
        "event_id":id_,"ticker":obj["ticker"],"issuer":obj["issuer"],
        "industry":obj["industry"],"period_label":obj["period_label"],
        "source_url":url,"source_type":obj["source_type"],"source_checked_date":str(stamp),
        "published_at_utc":publication.isoformat(),
        "earliest_reaction_us_session":eligible,
        "reporting_status":obj["reporting_status"],
        "metrics":metrics,"not_disclosed":missing,
        "related_etfs":etfs,"transmission_hypothesis":obj["transmission_hypothesis"],
        "counterevidence":obj["counterevidence"],
        "recheck_trigger":obj["recheck_trigger"],
        "causality":"HYPOTHESIS_ONLY",
        "latest_price_reaction_verified":False
    }


def collect_events(records=RECORDS):
    results=[]
    errors=[]
    for path in sorted(Path(records).glob("*.json")):
        try:
            obj=json.loads(path.read_text(encoding="utf-8"))
            validated=validate_event(obj)
            if path.stem!=validated["event_id"]:
                raise ValueError("Event filename must match event ID")
            results.append(validated)
        except (ValueError,TypeError,KeyError,OSError) as exc:
            errors.append({"file":path.name,"error":f"{type(exc).__name__}: {str(exc)[:180]}"})
    if len(set(x["event_id"] for x in results))!=len(results):
        raise ValueError("Duplicate industry event ID")
    return results,errors


def markdown(events,errors):
    lines=["# 산업별 실적·주문·재고 증거 검증 목록","",
           "> 출처가 분명한 기업 공시만 요약. 수집되지 않은 주문/재고는 사실로 만들어 내지 않음.",
           f"- SEC 공시 기반 유효 이벤트: {len(events)}",
           f"- 형식 검증 실패: {len(errors)}",
           "- 회사 공시를 ETF 전체 주문이나 주가 반응의 원인으로 일반화하지 않음.",""]
    for event in events:
        lines.extend([f"## {event['issuer']} ({event['ticker']}) — {event['period_label']}","",
                      f"- 확인 자료: [SEC EDGAR]({event['source_url']})",
                      f"- 원문 공개시각(UTC): {event['published_at_utc']}",
                      f"- 반응 관측이 가능한 미국장 최초일: {event['earliest_reaction_us_session']}",
                      f"- 확정 여부: **{event['reporting_status']}**",
                      f"- 관련 ETF는 직접 보유 여부 미검증인 가설: {', '.join(event['related_etfs']) or '없음'}",
                      "",
                      "|정량 지표|이번 발표 범위|비교 수치 범위|중간값 차이|비교 기준|",
                      "|---|---:|---:|---:|---|"])
        for x in event["metrics"]:
            start=f"{x['current_range'][0]:g}~{x['current_range'][1]:g} {x['unit']}"
            old=f"{x['comparison_range'][0]:g}~{x['comparison_range'][1]:g} {x['unit']}"
            delta=f"{x['midpoint_change']:+g} {x['midpoint_change_unit']}"
            if "relative_midpoint_change_pct" in x:
                delta+=f" ({x['relative_midpoint_change_pct']:+.2f}%)"
            lines.append(f"|{x['name']}|{start}|{old}|{delta}|{x['comparison_basis']}|")
        lines.extend(["",f"- **직접 발표하지 않은 항목:** {', '.join(event['not_disclosed']) or '명시 없음'}",
                      f"- **ETF 연계 가능성(검증 전 가설):** {event['transmission_hypothesis']}",
                      f"- **다음 확인:** {event['recheck_trigger']}",
                      "- **반대 근거/한계:**"])
        lines.extend(f"  - {z}" for z in event["counterevidence"])
        lines.append("")
    lines.extend(["## 자료 오류", ""])
    lines.extend([f"- {x['file']}: {x['error']}" for x in errors] or ["- 형식 오류 없음"])
    lines.extend(["","자료 형식 적합성 검사는 데이터가 참이라는 보증이 아니다. SEC 원문 변경/수정 공시, 동종기업 공시, 실제 주문 출하·재고 변화, ETF 구성종목·주가 반응은 별도로 검증할 것.",""])
    return "\n".join(lines)


def main():
    events,errors=collect_events()
    OUT.mkdir(parents=True,exist_ok=True)
    DOC.mkdir(parents=True,exist_ok=True)
    data={"generated_at_utc":datetime.now(timezone.utc).isoformat(),
          "status":"WARN" if errors else "OK",
          "event_count":len(events),"invalid_record_count":len(errors),
          "events":events,"errors":errors,
          "notes":[
              "Manually source-checked filings only; validator checks schema, not issuer truth.",
              "No claims about unreported order bookings, stock reaction, causality or ETF recommendation.",
              "First eligible market date does not establish actual price impact or fill.",
              "Filing preliminary guidance is not final audited revenue." ]}
    (OUT/"quality_latest.json").write_text(
        json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+"\n",
        encoding="utf-8")
    (DOC/"latest.md").write_text(markdown(events,errors),encoding="utf-8")
    for x in errors:
        print("::warning::Invalid industry source record",x["file"],x["error"],flush=True)
    print("INDUSTRY_EVIDENCE",len(events),"validated events",len(errors),"errors",flush=True)


if __name__=="__main__":
    main()
