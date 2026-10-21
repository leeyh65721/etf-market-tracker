"""Same-session market co-movements and macro observation changes: NOT causality.

Uses only published GitHub ETF daily snapshots and official-source macro scanner
observations. No economic release time is guessed. No brokerage or allocation data.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import exchange_calendars as calendars
import pandas as pd

ROOT=Path(__file__).parent
OUT=ROOT/"data"/"links"
DOCS=ROOT/"analysis"/"links"
CAL=calendars.get_calendar("XNYS")
# Representative price exposures, not comprehensive ETF coverage or recommended trades.
BENCHMARKS={
 "SPY":"미국 대형주 기준",
 "SOXX":"반도체",
 "XLK":"기술",
 "XLE":"에너지",
 "XLF":"금융",
 "XLP":"필수소비재",
 "XLV":"헬스케어",
 "XLI":"산업재",
 "XLU":"유틸리티",
 "XLY":"경기소비재",
 "XLB":"소재",
 "XLC":"커뮤니케이션서비스",
 "IWM":"중소형주",
 "TLT":"장기 국채",
 "IEF":"중기 국채",
 "HYG":"하이일드 채권 ETF",
 "LQD":"우량 회사채 ETF",
}
# Limited source release dates: observation periods are NOT release timestamps.
MACRO_FOCUS=[
 "T2Y","T10Y","T10Y_REAL","T10Y2Y",
 "VIX","VVIX","WTI","BRENT","EFFR","SOFR",
 "CPI_HEADLINE","CPI_CORE","PPI_FD","UNRATE","PAYROLLS",
 "JOLTS_OPENINGS","AVG_HOURLY_EARNINGS",
 "CORE_PCE","INITIAL_CLAIMS","RETAIL_SALES","NFCI",
 "MFG_NEW_ORDERS","DURABLE_NEW_ORDERS","REAL_GDP","SP500_BREADTH"
]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def require_float(x,description):
    try:
        f=float(x)
    except (ValueError,TypeError):
        raise ValueError(f"{description}: invalid value") from None
    if not math.isfinite(f):
        raise ValueError(f"{description}: not finite")
    return f


def predecessor(market_date):
    day=pd.Timestamp(str(market_date))
    if not CAL.is_session(day):
        raise ValueError("Market date is not an NYSE session")
    return CAL.session_offset(day,-1).date().isoformat()


def verified_snapshots(market_date,current_csv,history_dir):
    prev=predecessor(market_date)
    old_path=Path(history_dir)/f"{prev}.csv"
    if not old_path.exists():
        return {"status":"previous_exact_session_missing",
                "market_date":market_date,"previous_market_date":prev,
                "instruments":[],"coverage_count":0}
    current=pd.read_csv(current_csv)
    prior=pd.read_csv(old_path)
    required={"ticker","asof","close_usd"}
    for frame,day in ((current,market_date),(prior,prev)):
        if not required.issubset(frame.columns):
            raise ValueError("ETF snapshots are missing columns")
        if frame.empty or frame.ticker.isna().any() or frame.ticker.duplicated().any():
            raise ValueError("Missing/duplicate ticker")
        if not frame["asof"].astype(str).eq(day).all():
            raise ValueError("ETF snapshot date mismatch")
    i=current.set_index("ticker")
    j=prior.set_index("ticker")
    instruments=[]
    for ticker,exposure in BENCHMARKS.items():
        row={"ticker":ticker,"exposure":exposure,"status":"unavailable"}
        if ticker not in i.index or ticker not in j.index:
            row["reason"]="missing price pair"
        else:
            try:
                now=require_float(i.loc[ticker,"close_usd"],f"{ticker} current")
                before=require_float(j.loc[ticker,"close_usd"],f"{ticker} prior")
                if now<=0 or before<=0:
                    raise ValueError("nonpositive close")
                r=(now/before-1)*100
                if abs(r)>35:
                    row.update(status="unverified",reason="price move >35%; verify split/corporate action")
                else:
                    row.update(status="observed",price_return_pct=round(r,4),
                               previous_close_usd=round(before,4),
                               current_close_usd=round(now,4))
            except (ValueError,KeyError) as exc:
                row["reason"]=str(exc)[:130]
        instruments.append(row)
    by_id={x["ticker"]:x for x in instruments}
    spy=by_id["SPY"]
    for row in instruments:
        if row["status"]=="observed" and spy["status"]=="observed":
            row["excess_vs_spy_pp"]=round(row["price_return_pct"]-spy["price_return_pct"],4)
    return {"status":"ok" if spy["status"]=="observed" else "benchmark_unverified",
            "market_date":market_date,"previous_market_date":prev,
            "instruments":instruments,
            "coverage_count":sum(r["status"]=="observed" for r in instruments)}


def macro_changes(market_date,macro_file,extra_file):
    combined=[]
    issues=[]
    for path,kind in ((macro_file,"core"),(extra_file,"supplemental")):
        try:
            doc=load_json(path)
        except (OSError,ValueError,TypeError) as exc:
            issues.append({"type":kind,"issue":f"{type(exc).__name__}: {exc}"})
            continue
        if doc.get("market_date")!=market_date:
            issues.append({"type":kind,"issue":"macro market date does not match ETF session"})
            continue
        for row in doc.get("series",[]):
            if not isinstance(row,dict):
                continue
            sid=row.get("series_id")
            if not sid or row.get("status")!="ok":
                continue
            try:
                observation=pd.Timestamp(row["observation_date"]).date()
                if observation>pd.Timestamp(market_date).date():
                    raise ValueError("observation in future")
                value=require_float(row["value"],f"{sid} current")
                item={"series_id":sid,"source_group":kind,"name":row.get("name",sid),
                      "value":round(value,5),"unit":row.get("unit",""),
                      "observation_date":str(observation),"source_url":row.get("source_url",""),
                      "frequency":row.get("frequency","unknown"),
                      "publication_date_verified":False,
                      "same_market_date_observation":str(observation)==market_date}
                if "previous_value" in row and row.get("previous_date"):
                    prior=pd.Timestamp(row["previous_date"]).date()
                    if prior>=observation:
                        raise ValueError("previous observation date not older")
                    previous=require_float(row["previous_value"],f"{sid} previous")
                    item.update(previous_value=round(previous,5),
                                previous_observation_date=str(prior),
                                delta_observation_units=round(value-previous,5),
                                value_changed=abs(value-previous)>1e-9)
                else:
                    item["value_changed"]=None
                combined.append(item)
            except (ValueError,KeyError,TypeError,OverflowError) as exc:
                issues.append({"type":"invalid_macro_row","id":sid,"issue":str(exc)[:150]})
    order={name:i for i,name in enumerate(MACRO_FOCUS)}
    combined.sort(key=lambda x:(order.get(x["series_id"],len(order)),x["series_id"]))
    return combined,issues


def report_for_session(market_date,current_csv,history_dir,macro_file,extra_file):
    market=verified_snapshots(market_date,current_csv,history_dir)
    observations,issues=macro_changes(market_date,macro_file,extra_file)
    if market["status"]!="ok":
        issues.append({"type":"etf","issue":market["status"]})
    return {
        "us_market_date":market_date,
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "market":market,
        "macro_observations":observations,
        "data_quality_issues":issues,
        "comparison_scope":"Adjacent U.S. market-date ETF price changes and independently latest-reported macro observations",
        "cause_attribution":"NOT_ESTABLISHED",
        "publication_timing":"UNVERIFIED",
        "limitations":[
            "No macro release timestamps were verified; the source observation period can predate the public release.",
            "Any same-date co-movement is not proof of cause, prediction, or information known before that market close.",
            "Monthly/weekly/quarterly releases and same-date ETF price moves are NOT event-study windows.",
            "ETF quote source is unofficial Yahoo adjusted close; historical snapshots may be revised at different fetch times.",
            "All ETF results are USD prices; not actual fills, after-cost returns, or Korean-won outcomes.",
            "Industrial announcements and ETF net capital flows require separately documented official sources.",
        ]
    }


def markdown(payload):
    d=payload["us_market_date"]
    m=payload["market"]
    lines=[f"# 경제지표 관측과 ETF 시장 움직임 — {d} 미국장","",
           "> **단순 동시 관측 표. 인과관계·예측력·매수신호가 아님.**",
           f"- 작성(UTC): {payload['generated_at_utc']}",
           f"- ETF 가격 관측일: {m['previous_market_date']} → {d}",
           f"- 검증된 대표 ETF 종가 쌍: {m['coverage_count']}/{len(BENCHMARKS)}",
           "- 거시지표 관측 기간과 실제 발표 시각은 다를 수 있음. 경제지표가 ETF를 움직였다고 단정하지 않음.","",
           "## 대표 ETF 하루 가격변화 및 SPY 대비","",
           "|ETF|시장 노출|가격 변화(%)|SPY 대비(pp)|데이터 상태|",
           "|---|---|---:|---:|---|"]
    for row in m["instruments"]:
        absolute=(f"{row['price_return_pct']:+.3f}%" if "price_return_pct" in row else "미확인")
        relative=(f"{row['excess_vs_spy_pp']:+.3f}pp" if "excess_vs_spy_pp" in row else "-")
        lines.append(f"|{row['ticker']}|{row['exposure']}|{absolute}|{relative}|{row['status']}|")
    lines.extend(["","## 공식 수집 거시지표 — 각 지표의 자체 관측 시차","",
                  "|지표|최근 관측일|측정값|전 관측 변화|같은 시장일 관측?|출처|",
                  "|---|---|---:|---:|---|---|"])
    for row in payload["macro_observations"]:
        value=f"{row['value']:g} {row['unit']}"
        delta=f"{row['delta_observation_units']:+g} {row['unit']}" if "delta_observation_units" in row else "비교 원자료 없음"
        match="예(발표시각 미확인)" if row["same_market_date_observation"] else "아니오"
        url=row["source_url"]
        link=f"[기관]({url})" if url.startswith("https://") else "원자료 URL 미확인"
        lines.append(f"|{row['series_id']}|{row['observation_date']}|{value}|{delta}|{match}|{link}|")
    lines.extend(["","## 자료 품질 및 해석 범위",""])
    for entry in payload["data_quality_issues"]:
        lines.append(f"- {entry.get('type')}: {entry.get('issue')}")
    if not payload["data_quality_issues"]:
        lines.append("- 자동 검사에서 분명한 누락은 확인되지 않았지만, 공표일·인과관계는 여전히 미검증.")
    lines.extend(["",
                  "**읽는 방법:** 금리/유가/변동성의 관측값과 ETF 종가를 나란히 비교하고, 실제 발표시각과 업종별 독립 근거를 별도로 확인한 뒤에만 가설을 세울 것. 이 표에서 인과관계를 추론하지 말 것.",
                  ""])
    return "\n".join(lines)


def main():
    scan=load_json(ROOT/"data"/"latest.json")
    day=str(scan["us_market_date"])
    result=report_for_session(day,ROOT/"data"/"latest.csv",
                              ROOT/"data"/"history",
                              ROOT/"data"/"macro"/"latest.json",
                              ROOT/"data"/"macro"/"extra_latest.json")
    OUT.mkdir(parents=True,exist_ok=True)
    DOCS.mkdir(parents=True,exist_ok=True)
    blob=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n"
    (OUT/"latest.json").write_text(blob,encoding="utf-8")
    (OUT/f"{day}.json").write_text(blob,encoding="utf-8")
    md=markdown(result)
    (DOCS/"latest.md").write_text(md,encoding="utf-8")
    (DOCS/f"{day}.md").write_text(md,encoding="utf-8")
    print("MARKET_LINKS",day,"ETFs",result["market"]["coverage_count"],
          "macros",len(result["macro_observations"]),
          "issues",len(result["data_quality_issues"]),flush=True)


if __name__=="__main__":
    main()
