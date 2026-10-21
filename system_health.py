"""End-to-end daily public ETF data health gate.

All collectors may use continue-on-error, but this final gate documents every stage,
publishes a dated report, and fails the GitHub workflow AFTER diagnostics are saved
when core evidence is absent. Known/manual source gaps are not treated as successes.
"""
from __future__ import annotations

import csv
import json
import math
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import exchange_calendars as xcals
import pandas as pd

ROOT=Path(__file__).parent
OUT=ROOT/"data"/"health"
DOC=ROOT/"analysis"/"health"
EXPECTED_EXTRA={
    "CORE_PCE","INITIAL_CLAIMS","RETAIL_SALES","NFCI","MFG_NEW_ORDERS",
    "DURABLE_NEW_ORDERS","ISM_MANUFACTURING","ISM_SERVICES",
    "REAL_GDP","SP500_BREADTH",
}
EXPECTED_MANUAL={"ISM_MANUFACTURING","ISM_SERVICES"}
KNOWN_STALE={"NFCI"}
CRITICAL_AUTO=EXPECTED_EXTRA-EXPECTED_MANUAL-KNOWN_STALE
REQUIRED_BASE=22
CAL=xcals.get_calendar("XNYS")

def read(path):
    try:
        with Path(path).open(encoding="utf-8") as f:
            return json.load(f),None
    except (OSError,ValueError,TypeError) as exc:
        return None,f"{type(exc).__name__}: {str(exc)[:180]}"

def utc(text):
    d=datetime.fromisoformat(str(text).replace("Z","+00:00"))
    if d.tzinfo is None:
        raise ValueError("missing timezone")
    return d.astimezone(timezone.utc)

def expected_us_session(now):
    now=now.astimezone(timezone.utc)
    dates=CAL.sessions_in_range(pd.Timestamp(now.date())-pd.Timedelta(days=18),
                                pd.Timestamp(now.date())+pd.Timedelta(days=1))
    closed=[d for d in dates if CAL.session_close(d).to_pydatetime()<=now]
    return closed[-1].date().isoformat() if closed else None

def analyze(root=ROOT,now=None,steps=None):
    root=Path(root)
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Health audit must receive timezone-aware now")
    findings=[]
    def add(level,code,message):
        if not any(f["code"]==code for f in findings):
            findings.append({"level":level,"code":code,"detail":message})

    latest=root/"data"/"latest.json"
    technical,e=read(latest)
    if e:
        add("ERROR","TECHNICAL_FILE_MISSING","ETF technical scan unreadable: "+e)
        technical={}
    market=technical.get("us_market_date")
    expected=expected_us_session(now)
    if not market:
        add("ERROR","MARKET_DATE_MISSING","ETF market date unavailable")
    else:
        try:
            m=pd.Timestamp(market)
            if not CAL.is_session(m):
                raise ValueError("not a NYSE trading session")
        except (ValueError,TypeError):
            add("ERROR","MARKET_DATE_INVALID","ETF market date is not an NYSE session")
        if expected and market!=expected:
            add("ERROR","STALE_ETF_SESSION",
                f"Latest closed NYSE session {expected}, scanner shows {market}")
    def timestamp(doc,field,code,required_session=True):
        try:
            stamp=utc(doc[field])
            if stamp>now+pd.Timedelta(minutes=15):
                raise ValueError("generated timestamp in the future")
            return stamp
        except (KeyError,ValueError,TypeError) as exc:
            add("ERROR",code,f"{field}: {exc}")
            return None

    tstamp=timestamp(technical,"generated_at_utc","TECHNICAL_TIMESTAMP_BAD")
    valid=int(technical.get("valid_screened_count",0) or 0)
    universe=int(technical.get("candidate_universe_count",0) or 0)
    candidates=int(technical.get("technical_candidate_count",0) or 0)
    fraction=valid/universe if universe else 0
    if universe<=0 or valid<=0 or valid>universe or fraction<0.85:
        add("ERROR","ETF_COVERAGE_LOW",
            f"Verified {valid}/{universe} ({fraction:.1%}), required >=85%")
    elif fraction<0.95:
        add("WARN","ETF_COVERAGE_WATCH",
            f"Verified ETF universe {valid}/{universe} ({fraction:.1%})")
    csv_path=root/"data"/"latest.csv"
    if not csv_path.is_file():
        add("ERROR","ETF_CSV_MISSING","Missing current ETF CSV")
    else:
        try:
            with csv_path.open(newline="",encoding="utf-8") as fp:
                rows=list(csv.DictReader(fp))
            if len(rows)!=valid or len({r.get("ticker") for r in rows})!=len(rows):
                add("ERROR","ETF_CSV_COUNT","ETF CSV row count or unique tickers disagree with scanner JSON")
            if not all(r.get("asof")==market for r in rows):
                add("ERROR","ETF_CSV_DATE","ETF CSV dates disagree with JSON")
            if not any(r.get("ticker")=="SPY" for r in rows):
                add("ERROR","ETF_BENCHMARK_MISSING","ETF CSV lacks SPY reference")
            if sum(r.get("screen")=="candidate" for r in rows)!=candidates:
                add("ERROR","ETF_CANDIDATE_COUNT","CSV candidates differ from scanner JSON")
        except (OSError,ValueError,KeyError) as exc:
            add("ERROR","ETF_CSV_INVALID",str(exc)[:170])

    base,err=read(root/"data"/"macro"/"latest.json")
    if err:
        add("ERROR","BASE_MACRO_FILE","Missing 22-series official macro data: "+err)
        base={}
    if base.get("market_date")!=market:
        add("ERROR","BASE_MACRO_DATE","Base macro snapshot date mismatches ETF scan")
    bstatus=base.get("status")
    bseries=base.get("series",[])
    if not isinstance(bseries,list):
        bseries=[]
    bcounts=Counter(s.get("status") for s in bseries if isinstance(s,dict))
    bid=[s.get("series_id") for s in bseries if isinstance(s,dict)]
    if (bstatus!="ok" or base.get("requested_series_count")!=REQUIRED_BASE
        or base.get("retrieved_series_count")!=REQUIRED_BASE
        or base.get("current_series_count")!=REQUIRED_BASE
        or len(bseries)!=REQUIRED_BASE or len(set(bid))!=REQUIRED_BASE
        or bcounts.get("ok",0)!=REQUIRED_BASE):
        add("ERROR","BASE_MACRO_INCOMPLETE",
            f"Baseline {bcounts.get('ok',0)}/{REQUIRED_BASE} ok, source state {bstatus}")
    bstamp=timestamp(base,"generated_at_utc","BASE_MACRO_TIMESTAMP")
    if bstamp and tstamp and bstamp<tstamp:
        add("ERROR","BASE_MACRO_STALE_RUN","Base macro snapshot predates today's ETF scan")
    base_health,err=read(root/"data"/"macro"/"health_latest.json")
    if err:
        add("ERROR","BASE_MACRO_HEALTH_MISSING",err)
        base_health={}
    if base_health.get("status")!="OK" or base_health.get("market_date")!=market:
        add("ERROR","BASE_MACRO_HEALTH_UNSAFE",
            f"Baseline macro health={base_health.get('status')} date={base_health.get('market_date')}")
    extra,err=read(root/"data"/"macro"/"extra_latest.json")
    if err:
        add("ERROR","EXTRA_MACRO_FILE",err)
        extra={}
    if extra.get("market_date")!=market:
        add("ERROR","EXTRA_MACRO_DATE","Supplemental macro dataset is not from this US session")
    estamp=timestamp(extra,"generated_at_utc","EXTRA_MACRO_TIMESTAMP")
    if estamp and tstamp and estamp<tstamp:
        add("ERROR","EXTRA_MACRO_STALE_RUN","Supplemental macro snapshot predates today's ETF scan")
    items=extra.get("series",[])
    if not isinstance(items,list):
        items=[]
    ex_id=[s.get("series_id") for s in items if isinstance(s,dict)]
    by_id={s["series_id"]:s for s in items if isinstance(s,dict) and isinstance(s.get("series_id"),str)}
    if (set(by_id)!=EXPECTED_EXTRA or len(ex_id)!=10 or len(set(ex_id))!=10
        or extra.get("requested_indicators")!=10
        or extra.get("ok_indicators")!=sum(s.get("status")=="ok" for s in items)):
        add("ERROR","EXTRA_MACRO_SCHEMA","Required 10 supplemental indicators missing, duplicated or count inconsistent")
    actual_statuses={k:v.get("status","missing") for k,v in by_id.items()}
    for key in sorted(EXPECTED_MANUAL):
        if actual_statuses.get(key)!="manual":
            add("WARN","MANUAL_STATUS_CHANGED_"+key,
                f"{key} expected manual review, actual {actual_statuses.get(key)}")
    for key in sorted(KNOWN_STALE):
        if actual_statuses.get(key)!="ok":
            add("KNOWN","NFCI_NOT_LIVE",
                f"{key} latest official CSV status={actual_statuses.get(key)}, requires permitted manual verification")
    missing_auto=sorted(k for k in CRITICAL_AUTO if actual_statuses.get(k)!="ok")
    for key in missing_auto:
        add("WARN","EXTRA_UNAVAILABLE_"+key,
            f"Supplemental automatic metric {key} is {actual_statuses.get(key)}; don't use as current")
    if len(missing_auto)>=3:
        add("ERROR","EXTRA_MULTIPLE_LOSSES",
            f"At least 3/7 normally automated supplemental metrics failed: {', '.join(missing_auto)}")

    additional={
        "screen_audit":("data/quality/latest.json","asof","status"),
        "macro_etf_links":("data/links/latest.json","us_market_date",None),
        "industry_evidence":("data/industry/quality_latest.json",None,"status"),
        "judgment_archive":("data/decisions/latest.json",None,"status"),
    }
    module_status={}
    for name,(path,date_field,status_field) in additional.items():
        d,err=read(root/path)
        if err:
            add("ERROR","MISSING_"+name.upper(),f"{path}: {err}")
            module_status[name]="missing"
            continue
        module_status[name]=d.get(status_field) if status_field else "available"
        if date_field and d.get(date_field)!=market:
            add("ERROR","STALE_"+name.upper(),f"{path} shows {d.get(date_field)} not {market}")
        if status_field and d.get(status_field) in ("ERROR","WARN"):
            level="ERROR" if name=="judgment_archive" and d.get("invalid_count",0) else "WARN"
            add(level,"MODULE_"+name.upper()+"_"+d.get(status_field),
                f"{path} reports status {d.get(status_field)}")
        if name=="industry_evidence" and d.get("invalid_record_count",0):
            add("ERROR","INDUSTRY_INVALID_RECORD","Industry SEC evidence contains invalid records")
        if name=="judgment_archive" and d.get("invalid_count",0):
            add("ERROR","DECISIONS_INVALID_RECORD","ETF research decision evidence contains invalid records")
        if name=="macro_etf_links":
            market_section=d.get("market",{})
            if market_section.get("status")!="ok" or market_section.get("coverage_count",0)<10:
                add("WARN","LINKED_ETF_COVERAGE","Insufficient representative ETF same-session price pairs")
            issues=d.get("data_quality_issues",[])
            if issues:
                add("WARN","LINKED_MACRO_ISSUES",f"{len(issues)} macro-ETF link data issues")

    steps=steps or {}
    for name,outcome in steps.items():
        if outcome in ("","skipped",None):
            # A skipped essential producer means the expected report cannot be assumed fresh.
            if name in ("ETF_SCAN","BASE_MACRO","MARKET_LINKS","JUDGMENT_ARCHIVE"):
                add("ERROR","STEP_"+name,"Workflow essential collection stage skipped")
        elif outcome!="success":
            level="ERROR" if name in ("ETF_SCAN","BASE_MACRO","MARKET_LINKS","JUDGMENT_ARCHIVE",
                                       "SCREEN_AUDIT") else "WARN"
            add(level,"STEP_"+name,f"GitHub Actions stage outcome={outcome}")
    severity="ERROR" if any(x["level"]=="ERROR" for x in findings) else (
        "WARN" if any(x["level"]=="WARN" for x in findings) else "OK")
    original,_=read(root/"data"/"health"/"latest.json")
    prior_codes={z.get("code") for z in (original or {}).get("findings",[])
                 if z.get("level") in ("WARN","ERROR")}
    fresh=[z["code"] for z in findings if z["level"] in ("ERROR","WARN")
           and z["code"] not in prior_codes]
    return {
        "us_market_date":market,
        "expected_latest_closed_nyse_session":expected,
        "generated_at_utc":now.astimezone(timezone.utc).isoformat(),
        "status":severity,
        "counts":{"etf_verified":valid,"etf_universe":universe,"etf_fraction":round(fraction,5),
                  "base_macro_ok":bcounts.get("ok",0),"base_macro_expected":REQUIRED_BASE,
                  "supplemental_ok":sum(v=="ok" for v in actual_statuses.values()),
                  "supplemental_expected":10,"manual_expected":len(EXPECTED_MANUAL),
                  "supplemental_missing_automatic":len(missing_auto)},
        "supplemental_statuses":actual_statuses,
        "module_status":module_status,
        "stage_outcomes":steps,
        "findings":findings,
        "new_alert_codes":fresh,
        "alert_summary":"new non-expected warning/error codes only; KNOWN values excluded",
        "not_a_market_signal":True,
        "guidance":"ERROR fails GitHub Actions after archival; WARN annotates success; KNOWN must still be reported separately.",
    }

def markdown(r):
    c=r["counts"]
    lines=["# ETF 자동 수집 종합 품질 상태","",
           f"- 상태: **{r['status']}**",
           f"- 미국 시장 기준일: {r['us_market_date']} (최신 마감일 {r['expected_latest_closed_nyse_session']})",
           f"- 검증된 ETF: **{c['etf_verified']}/{c['etf_universe']} ({c['etf_fraction']:.1%})**",
           f"- 공식 22개 지표: **{c['base_macro_ok']}/22**",
           f"- 추가 10개 세부 지표: **{c['supplemental_ok']}/10 자동 정상**",
           "- ISM 2개 수동 확인, NFCI가 오래되면 최신값으로 사용하지 않음.",
           f"- 신규 주의/오류 코드: {', '.join(r['new_alert_codes']) or '없음'}","",
           "## 발견 문제","",
           "| 수준 | 코드 | 내용 |","|---|---|---|"]
    for f in r["findings"]:
        lines.append(f"|{f['level']}|{f['code']}|{f['detail'].replace('|','/')}|")
    if not r["findings"]:
        lines.append("|OK|-|자료 수집 형식·필수 일자 검사 통과. 투자 안전을 의미하지 않음.|")
    lines.extend(["","## 모듈별 최신 상태","",
                  "|모듈|상태|","|---|---|"])
    for k,v in r["module_status"].items():
        lines.append(f"|{k}|{v}|")
    lines.extend(["","**기준:** 자동 수집 완료 자체가 발표자료·매매판단 정확도를 보장하지 않음. "
                  "변화가 확인되지 않은 지표를 '변화 없음'으로 처리하지 말 것.",
                  "개인 계좌/비중/손익 등은 공개 GitHub에 기록하지 않음.",""])
    return "\n".join(lines)

def write_report(r,root=ROOT):
    root=Path(root)
    out=root/"data"/"health"
    docs=root/"analysis"/"health"
    out.mkdir(parents=True,exist_ok=True)
    docs.mkdir(parents=True,exist_ok=True)
    blob=json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False)+"\n"
    (out/"latest.json").write_text(blob,encoding="utf-8")
    if r["us_market_date"]:
        (out/f"{r['us_market_date']}.json").write_text(blob,encoding="utf-8")
    md=markdown(r)
    (docs/"latest.md").write_text(md,encoding="utf-8")
    if r["us_market_date"]:
        (docs/f"{r['us_market_date']}.md").write_text(md,encoding="utf-8")
    summary=os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary,"a",encoding="utf-8") as fp:
            fp.write(md+"\n")
    for f in r["findings"]:
        if f["level"]=="ERROR":
            print(f"::error::{f['code']}: {f['detail']}",flush=True)
        elif f["level"]=="WARN":
            print(f"::warning::{f['code']}: {f['detail']}",flush=True)
    print("SYSTEM_HEALTH",r["status"],r["us_market_date"],
          "new_alert_codes",r["new_alert_codes"],flush=True)

def main():
    keys={
      "ETF_SCAN":"ETF_SCAN_OUTCOME",
      "BASE_MACRO":"MACRO_COLLECTION_OUTCOME",
      "EXTRA_MACRO":"EXTRA_COLLECTION_OUTCOME",
      "SCREEN_AUDIT":"SCREEN_AUDIT_OUTCOME",
      "MARKET_LINKS":"MARKET_LINKS_OUTCOME",
      "INDUSTRY_EVIDENCE":"INDUSTRY_EVIDENCE_OUTCOME",
      "JUDGMENT_ARCHIVE":"JUDGMENT_ARCHIVE_OUTCOME",
    }
    steps={name:os.getenv(env) for name,env in keys.items()}
    r=analyze(steps=steps)
    write_report(r)

if __name__=="__main__":
    main()
