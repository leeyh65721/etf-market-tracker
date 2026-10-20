"""Public macro-economic time series with conditional evidence notes.
Free FRED graph CSV downloads; NOT the API requiring a key.
No personal portfolio, paid APIs, financial trades or generative model calls.
"""
import json
import time
from datetime import datetime, timezone, timedelta
from io import StringIO
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
import pandas as pd

ROOT = Path(__file__).parent
DATA = ROOT / "data"
MACRO = DATA / "macro"
SPECS = [
 ("DGS2","미국 2년 국채금리","daily","%"),
 ("DGS10","미국 10년 국채금리","daily","%"),
 ("DFII10","미국 10년 실질금리","daily","%"),
 ("T10Y2Y","10년-2년 국채금리차","daily","%p"),
 ("DFF","실효 연방기금금리","daily","%"),
 ("BAMLH0A0HYM2","하이일드 신용스프레드","daily","%p"),
 ("VIXCLS","VIX","daily","index"),
 ("DCOILWTICO","WTI 원유 현물","daily","USD/barrel"),
 ("DCOILBRENTEU","브렌트 원유 현물","daily","USD/barrel"),
 ("DTWEXBGS","광의 달러지수","daily","index"),
 ("DEXKOUS","원/달러 환율","daily","KRW/USD"),
 ("CPIAUCSL","미국 CPI","monthly","index"),
 ("PCEPILFE","미국 근원 PCE 물가지수","monthly","index"),
 ("UNRATE","미국 실업률","monthly","%"),
 ("PAYEMS","미국 비농업고용","monthly","thousand"),
 ("INDPRO","미국 산업생산","monthly","index"),
 ("RSXFS","미국 소매판매(자동차 제외)","monthly","USD million"),
 ("GDPC1","미국 실질GDP","quarterly","USD billion chained"),
]
def collect(sid, start, date):
    url="https://fred.stlouisfed.org/graph/fredgraph.csv?"+urlencode({"id":sid,"cosd":start})
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 (PublicMarketResearch; ETFTracker)",
                              "Accept":"text/csv,*/*"})
    last_error=None
    for attempt in range(2):
        try:
            with urlopen(req,timeout=12) as response:
                raw=response.read(3000000).decode("utf-8-sig")
            table=pd.read_csv(StringIO(raw))
            date_col=next((c for c in ("DATE","observation_date") if c in table.columns),None)
            if date_col is None or sid not in table.columns:
                raise ValueError("Unexpected FRED CSV format")
            clean=pd.DataFrame({"date":pd.to_datetime(table[date_col],errors="coerce"),
                                "value":pd.to_numeric(table[sid],errors="coerce")})
            clean=clean.dropna().sort_values("date")
            clean=clean[clean.date.dt.date <= date]
            if len(clean)<2: raise ValueError("Insufficient valid historical observations")
            return clean,url
        except Exception as exc:
            last_error=f"{type(exc).__name__}: {str(exc)[:100]}"
            if not attempt: time.sleep(1)
    raise RuntimeError(last_error)

def measure(spec,start,date):
    sid,name,freq,unit=spec
    t,url=collect(sid,start,date)
    current=t.iloc[-1]
    previous=t.iloc[-2]
    ago=t.iloc[-6] if len(t)>=6 else None
    stale=(date-current.date.date()).days > {"daily":10,"monthly":78,"quarterly":190}[freq]
    row={
      "series_id":sid,"name":name,"frequency":freq,"unit":unit,"source_url":url,
      "observation_date":str(current.date.date()),
      "value":round(float(current.value),5),
      "previous_date":str(previous.date.date()),
      "previous_value":round(float(previous.value),5),
      "change_previous":round(float(current.value-previous.value),5),
      "status":"stale" if stale else "ok",
    }
    if freq=="daily" and ago is not None:
        row["five_observation_reference_date"]=str(ago.date.date())
        row["five_observation_change"]=round(float(current.value-ago.value),5)
        row["five_observation_pct"]=round(float((current.value/ago.value-1)*100),4) if ago.value else None
    if freq=="monthly":
        prev12=t[t.date<=current.date-pd.DateOffset(months=12)]
        if not prev12.empty and float(prev12.iloc[-1].value):
            row["year_over_year_change_pct"]=round(float(
                (current.value/prev12.iloc[-1].value-1)*100),4)
            row["year_over_year_reference_date"]=str(prev12.iloc[-1].date.date())
    return row

def conditional_signals(records):
    d={r["series_id"]:r for r in records if r["status"]=="ok"}
    signals=[]
    def add(sid,field,limit,title,conditional,verify,multiplier=1):
        r=d.get(sid)
        if not r or r.get(field) is None: return
        n=r[field]*multiplier
        if abs(n)<limit:return
        signals.append({
          "indicator":sid,"title":title,"evidence":f"{n:+.2f}",
          "period":r.get("five_observation_reference_date",r["previous_date"])+" to "+r["observation_date"],
          "conditional_interpretation":conditional,
          "independently_verify":verify})
    add("DGS10","five_observation_change",15,"미국 장기금리 급변",
        "금리 상승은 할인율·차입 비용 부담일 수 있지만 성장 기대 확대를 반영할 수도 있음",
        "실질금리, 연준 발언, 기대물가 및 발행·수급 원인을 확인",100)
    add("BAMLH0A0HYM2","five_observation_change",20,"고위험 회사채 신용 위험 변화",
        "스프레드 확대는 자금조달 환경 악화 가능성, 축소는 반대 방향 가능성",
        "신용 유동성과 실물 부도율, 가격 소스 재확인",100)
    add("DCOILWTICO","five_observation_pct",5,"원유 가격 큰 변화",
        "상승은 에너지 업체에 유리할 수 있지만 운송비·물가에 부담; 하락은 반대 방향 가능성",
        "중동·러시아 공급과 실물 수요, 브렌트 및 선물곡선을 함께 확인")
    add("VIXCLS","five_observation_change",4,"예상 변동성 변화",
        "VIX 상승은 위험회피 심화의 신호일 수 있으나 단기 이벤트일 수도 있음",
        "S&P500 움직임, 시장 폭, 옵션 관련 요인 확인")
    add("DTWEXBGS","five_observation_pct",1.5,"달러 강약 변화",
        "달러 강세는 환율 환산수익과 기업 해외매출 등에 영향을 줄 수 있음",
        "원/달러, 정책 금리차, 지정학적 위험 분리")
    r=d.get("UNRATE")
    if r and r["change_previous"]>=0.2:
        signals.append({"indicator":"UNRATE","title":"실업률 상승",
            "evidence":f"{r['change_previous']:+.2f} %p",
            "period":r["previous_date"]+" to "+r["observation_date"],
            "conditional_interpretation":"경기 둔화 가능성이 커질 수 있음",
            "independently_verify":"고용 증가, 노동참가율, 발표 개정 여부 확인"})
    return signals

def main():
    scan=json.loads((DATA/"latest.json").read_text(encoding="utf-8"))
    market_date=datetime.strptime(scan["us_market_date"],"%Y-%m-%d").date()
    start=str(market_date-timedelta(days=850))
    rows=[]
    errors={}
    for spec in SPECS:
        sid=spec[0]
        try:
            rows.append(measure(spec,start,market_date))
            print("MACRO_OK",sid,flush=True)
        except Exception as exc:
            errors[sid]=f"{type(exc).__name__}: {str(exc)[:130]}"
            print("MACRO_ERROR",sid,errors[sid],flush=True)
    signals=conditional_signals(rows)
    state="ok" if len(rows)>=12 else ("partial" if rows else "unavailable")
    report={
      "market_date":str(market_date),
      "generated_at_utc":datetime.now(timezone.utc).isoformat(),
      "status":state,"requested_series_count":len(SPECS),
      "retrieved_series_count":len(rows),
      "current_series_count":sum(r["status"]=="ok" for r in rows),
      "source":"FRED public graph CSV downloads (best effort, not FRED API)",
      "series":rows,"conditional_signals":signals,"errors":errors,
      "limitations":[
        "Series have different observation dates and release frequency. FRED historical values may be revised.",
        "No as-released/vintage data: do not treat historical figures as available in real time.",
        "Conditions are hypotheses, not AI interpretations or investment advice.",
        "No verified news, issuer fundamentals, futures term structure or ETF flows.",
        "No user personal portfolio or account information."
      ]
    }
    encoded=json.dumps(report,ensure_ascii=False,allow_nan=False,indent=2)+"\n"
    (MACRO/"history").mkdir(parents=True,exist_ok=True)
    (MACRO/"latest.json").write_text(encoded,encoding="utf-8")
    (MACRO/"history"/f"{market_date}.json").write_text(encoded,encoding="utf-8")
    notes=ROOT/"analysis"/"macro"
    notes.mkdir(parents=True,exist_ok=True)
    lines=[
        f"# 미국 거시경제 관찰 기록 — 거래일 {market_date}",
        "",
        "> 자동 수집 수치와 조건부 해석. AI가 뉴스와 원인을 종합한 분석이 아니며 매매 신호가 아닙니다.",
        f"- 수집 시각 UTC: {report['generated_at_utc']}",
        f"- 데이터 품질: {state}; 수집 {len(rows)}/{len(SPECS)}, 유효 시차 {report['current_series_count']}",
        "- 각 지표의 정확한 출처/관측일은 해당 날짜의 macro JSON 파일에 있음.",
        "",
        "## 경제지표", "",
        "|지표|관측일|값|직전 대비|5개 관측치 대비|상태|",
        "|---|---|---:|---:|---:|---|",
    ]
    for r in rows:
        back=r.get("five_observation_change")
        back_str=f"{back:+.3f}" if back is not None else "해당 없음"
        lines.append(f"|{r['name']} ({r['series_id']})|{r['observation_date']}|"
                     f"{r['value']:.3f} {r['unit']}|{r['change_previous']:+.3f}|{back_str}|{r['status']}|")
    lines.extend(["","## 유의할 시장 변화 신호"])
    if not signals:
        lines.append("- 규칙상 큰 변화 신호 없음(시장 안전의 증거가 아님).")
    for s in signals:
        lines.extend(["",f"### {s['title']} ({s['indicator']})",
                      f"- 변화량: {s['evidence']} / {s['period']}",
                      f"- 조건부 해석: {s['conditional_interpretation']}",
                      f"- 추가 검증: {s['independently_verify']}"])
    if errors:
        lines.extend(["","## 수집 누락"])
        lines.extend(f"- {sid}: {error}" for sid,error in errors.items())
    lines.extend(["","## 주간 판단 주의점","",
        "- 관측일, 공표일, 실시간 시세를 혼동하지 않고 지표 시차와 수정 가능성을 검토.",
        "- WTI 변동의 공급/수요 원인과 기업실적, 국제정책, ETF 수급은 외부 뉴스로 재검증.",
        "- 이 문서는 ChatGPT 일일 자유 해석을 저장한 파일이 아님.",
        "- 개인 계좌·보유액·현금·비중은 공개 저장소에 기록하지 않음.",""])
    (notes/f"{market_date}.md").write_text("\n".join(lines),encoding="utf-8")
    print("MACRO_DONE",market_date,state,len(rows),"signals",len(signals),flush=True)

if __name__=="__main__":
    main()
