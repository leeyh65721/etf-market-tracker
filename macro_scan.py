"""Public macro-economic time series with conditional evidence notes.
Direct official public Treasury, BLS, EIA, Cboe, ECB and NY Fed series.
No personal portfolio, paid APIs, financial trades or generative model calls.
"""
import json
import time
from datetime import datetime, timezone, timedelta
from io import StringIO, BytesIO
from xml.etree import ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.error import HTTPError
from pathlib import Path
from urllib.request import Request, urlopen
import pandas as pd

ROOT = Path(__file__).parent
DATA = ROOT / "data"
MACRO = DATA / "macro"
# No FRED requests: read from original public data publishers (US agencies, Cboe, ECB).
SPECS = [
 ("T2Y", "미국 국채 2년", "daily", "%"),
 ("T10Y", "미국 국채 10년", "daily", "%"),
 ("T10Y_REAL", "미국 실질 국채 10년", "daily", "%"),
 ("T10Y2Y", "미국 10년-2년 금리차", "daily", "%p"),
 ("CPI_HEADLINE", "CPI 계절조정", "monthly", "index"),
 ("CPI_CORE", "근원 CPI 계절조정", "monthly", "index"),
 ("UNRATE", "미국 실업률 계절조정", "monthly", "%"),
 ("PAYROLLS", "미국 비농업 고용 계절조정", "monthly", "thousand"),
 ("PPI_FD", "미국 PPI 최종수요 비계절조정", "monthly", "index"),
 ("WTI", "WTI 현물유가", "daily", "USD/barrel"),
 ("BRENT", "브렌트 현물유가", "daily", "USD/barrel"),
 ("VIX", "Cboe VIX 공포지수", "daily", "index"),
 ("VVIX", "Cboe VVIX 변동성의 변동성", "daily", "index"),
 ("USD_KRW_ECB", "ECB 기준 USD/KRW 교차환율", "daily", "KRW/USD"),
 ("EUR_USD_ECB", "ECB 기준 EUR/USD", "daily", "USD/EUR"),
 ("EFFR", "뉴욕연준 실효 연방기금금리", "daily", "%"),
 ("SOFR", "뉴욕연준 담보부 익일조달금리", "daily", "%"),
 ("JOLTS_OPENINGS", "미국 전체 구인 공석 JOLTS", "monthly", "thousand"),
 ("LFPR", "미국 경제활동참가율", "monthly", "%"),
 ("AVG_HOURLY_EARNINGS", "미국 민간 시간당 평균임금", "monthly", "USD/hour"),
 ("AVG_WEEKLY_HOURS", "미국 민간 평균 주간 근로시간", "monthly", "hours"),
 ("CPI_SHELTER", "미국 주거비 CPI 계절조정", "monthly", "index"),
]
BLS_SERIES = {"CPI_HEADLINE":"CUSR0000SA0", "CPI_CORE":"CUSR0000SA0L1E",
              "UNRATE":"LNS14000000", "PAYROLLS":"CES0000000001", "PPI_FD":"WPUFD4",
              "JOLTS_OPENINGS":"JTS000000000000000JOL", "LFPR":"LNS11300000",
              "AVG_HOURLY_EARNINGS":"CES0500000003",
              "AVG_WEEKLY_HOURS":"CES0500000002",
              "CPI_SHELTER":"CUSR0000SAH1"}
SOURCE_RESULTS = {}
SOURCE_ERRORS = {}
UNAVAILABLE_OTHER = ["회사채 옵션조정 신용스프레드(HY/IG OAS: 라이선스 확인 필요)",
                     "연준 목표 기준금리 상·하한(실효금리 EFFR과 구별)",
                     "광의 달러지수(DXY: ECB 환율과 다름)", "근원 PCE", "미국 GDP",
                     "제조업·서비스업 PMI", "미국 소매판매", "주간 신규 실업수당청구",
                     "금", "구리", "천연가스", "은행 금융여건 지수"]

def request_bytes(url, timeout=12):
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 (ETFMarketTracker public research)",
                             "Accept":"text/csv,application/json,application/vnd.ms-excel,*/*"})
    last_error=None
    for attempt in range(2):
        try:
            with urlopen(req,timeout=timeout) as response:
                return response.read(5000000)
        except Exception as exc:
            last_error=exc
            if isinstance(exc,HTTPError) and exc.code in (400,401,403,404):
                break
            if attempt==0:
                time.sleep(0.5)
    raise RuntimeError(f"{type(last_error).__name__}: {str(last_error)[:120]}")

def treasury(real, year):
    kind="daily_treasury_real_yield_curve" if real else "daily_treasury_yield_curve"
    url=(f"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
         f"daily-treasury-rates.csv/{year}/all?type={kind}"
         f"&field_tdr_date_value={year}&page&_format=csv")
    df=pd.read_csv(StringIO(request_bytes(url).decode("utf-8-sig")))
    df.columns=df.columns.map(str).str.strip()
    if not {"Date","10 Yr"}.issubset(df.columns):
        raise ValueError("Treasury CSV has no Date/10 Yr columns")
    return df,url

def bls(sid):
    url=f"https://api.bls.gov/publicAPI/v2/timeseries/data/{sid}"
    doc=json.loads(request_bytes(url).decode("utf-8-sig"))
    if doc.get("status")!="REQUEST_SUCCEEDED":
        raise ValueError(f"BLS API status {doc.get('status')}: {str(doc.get('message'))[:90]}")
    records=doc.get("Results",{}).get("series",[])
    if not records or records[0].get("seriesID")!=sid:
        raise ValueError("Wrong or missing BLS series")
    data=[]
    for obj in records[0].get("data",[]):
        p=obj.get("period","")
        if len(p)!=3 or not p.startswith("M") or p=="M13":
            continue
        try:
            stamp=pd.Timestamp(year=int(obj["year"]),month=int(p[1:]),day=1)
            value=float(str(obj["value"]).replace(",",""))
            data.append((stamp,value))
        except (KeyError,ValueError,TypeError):
            continue
    if len(data)<2:
        raise ValueError("Insufficient BLS observations")
    return pd.DataFrame(data,columns=["date","value"]),url

def eia(code):
    url=f"https://www.eia.gov/dnav/pet/hist_xls/{code}.xls"
    table=pd.read_excel(BytesIO(request_bytes(url,timeout=16)),
                        sheet_name="Data 1",skiprows=2,engine="xlrd")
    if table.shape[1]<2: raise ValueError("Invalid EIA Data 1 XLS format")
    df=pd.DataFrame({"date":pd.to_datetime(table.iloc[:,0],errors="coerce"),
                     "value":pd.to_numeric(table.iloc[:,1],errors="coerce")})
    return df,url

def cboe(symbol):
    # CSV is published directly by the exchange; header usually DATE,OPEN,HIGH,LOW,CLOSE.
    url=f"https://cdn.cboe.com/api/global/us_indices/daily_prices/{symbol}_History.csv"
    df=pd.read_csv(StringIO(request_bytes(url,timeout=16).decode("utf-8-sig")))
    df.columns=df.columns.map(str).str.strip().str.upper()
    if not {"DATE","CLOSE"}.issubset(df.columns):
        raise ValueError(f"Cboe {symbol} daily CSV missing DATE/CLOSE")
    out=pd.DataFrame({"date":pd.to_datetime(df["DATE"],errors="coerce"),
                      "value":pd.to_numeric(df["CLOSE"],errors="coerce")})
    return out,url

def ecb_fx():
    # ECB publishes reference rates per EUR. USD/KRW is a cross rate, not a direct quote.
    url="https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
    root=ET.fromstring(request_bytes(url,timeout=16))
    observations=[]
    for node in root.iter():
        when=node.attrib.get("time")
        if not when:continue
        rates={child.attrib.get("currency"):child.attrib.get("rate") for child in node
               if "currency" in child.attrib}
        try:
            usd=float(rates["USD"]);krw=float(rates["KRW"])
            stamp=pd.Timestamp(when)
            observations.append((stamp,krw/usd,usd))
        except (ValueError,KeyError,TypeError):
            continue
    if len(observations)<2:
        raise ValueError("Insufficient valid ECB USD/KRW reference rates")
    frame=pd.DataFrame(observations,columns=["date","usdkrw","eurusd"])
    return frame,url

def nyfed(rate):
    # Public rate history directly from the administrator. Last 120 observations;
    # do not request a rate for dates later than market_date.
    group="unsecured" if rate=="effr" else "secured"
    url=f"https://markets.newyorkfed.org/api/rates/{group}/{rate}/last/120.json"
    j=json.loads(request_bytes(url,timeout=16).decode("utf-8-sig"))
    data=[]
    for x in j.get("refRates",[]):
        if str(x.get("type","")).lower()!=rate: continue
        try:
            data.append((pd.Timestamp(x["effectiveDate"]),float(x["percentRate"])))
        except (TypeError,KeyError,ValueError):
            continue
    if len(data)<2:raise ValueError(f"No valid NY Fed {rate} history")
    return pd.DataFrame(data,columns=["date","value"]),url

def etf_credit_proxies(market_date):
    """Credit risk-on proxies, NOT option-adjusted credit spreads."""
    path=DATA/"latest.csv"
    if not path.exists():return {"status":"unavailable","reason":"ETF latest.csv missing"}
    f=pd.read_csv(path).set_index("ticker")
    targets=("HYG","LQD","IEF")
    if any(t not in f.index or str(f.loc[t,"asof"])!=str(market_date) for t in targets):
        return {"status":"unavailable","reason":"HYG/LQD/IEF missing or ETF price dates inconsistent"}
    out={}
    for name,credit in (("HY_vs_treasury","HYG"),("IG_vs_treasury","LQD")):
        series={}
        for window in ("5d","21d"):
            key=f"return_{window}_pct"
            x=float(f.loc[credit,key]);b=float(f.loc["IEF",key])
            series[window+"_price_return_gap_pp"]=round(x-b,3)
        out[name]={"credit_etf":credit,"treasury_etf":"IEF",**series}
    return {"status":"ok","asof":str(market_date),
            "metric_type":"difference in ETF price returns, not yield spread/OAS",
            "caveats":["ETF price returns exclude FX and may differ in duration, fees and distributions.",
                       "Credit, Treasury interest-rate and duration sensitivity can confound the difference.",
                       "Do not compare the figures numerically with high-yield/IG option-adjusted spreads."],
            "series":out}

def load_sources(market_date):
    jobs={"treasury_nominal":lambda:treasury(False,market_date.year),
          "treasury_real":lambda:treasury(True,market_date.year),
          "eia_wti":lambda:eia("RWTCd"),
          "eia_brent":lambda:eia("RBRTEd"),
          "cboe_vix":lambda:cboe("VIX"),
          "cboe_vvix":lambda:cboe("VVIX"),
          "ecb_fx":ecb_fx,
          "nyfed_effr":lambda:nyfed("effr"),
          "nyfed_sofr":lambda:nyfed("sofr")}
    jobs.update({f"bls_{key}":(lambda sid=sid:bls(sid)) for key,sid in BLS_SERIES.items()})
    with ThreadPoolExecutor(max_workers=4) as pool:
        future_map={pool.submit(fn):label for label,fn in jobs.items()}
        for future in as_completed(future_map):
            label=future_map[future]
            try:
                SOURCE_RESULTS[label]=future.result()
                print("MACRO_SOURCE_OK",label,flush=True)
            except Exception as exc:
                SOURCE_ERRORS[label]=f"{type(exc).__name__}: {str(exc)[:120]}"
                print("MACRO_SOURCE_ERROR",label,SOURCE_ERRORS[label],flush=True)

def collect(sid, start, date):
    if sid in ("T2Y","T10Y","T10Y2Y"):
        group="treasury_nominal"
    elif sid=="T10Y_REAL":
        group="treasury_real"
    elif sid in ("WTI","BRENT"):
        group="eia_wti" if sid=="WTI" else "eia_brent"
    elif sid in ("VIX","VVIX"):
        group="cboe_"+sid.lower()
    elif sid in ("USD_KRW_ECB","EUR_USD_ECB"):
        group="ecb_fx"
    elif sid in ("EFFR","SOFR"):
        group="nyfed_"+sid.lower()
    else:
        group=f"bls_{sid}"
    if group not in SOURCE_RESULTS:
        raise RuntimeError(SOURCE_ERRORS.get(group,"source unavailable"))
    df,url=SOURCE_RESULTS[group]
    if group=="ecb_fx":
        result=pd.DataFrame({"date":df["date"],"value":df["usdkrw" if sid=="USD_KRW_ECB" else "eurusd"]})
    elif group.startswith("treasury"):
        d=pd.to_datetime(df["Date"],errors="coerce")
        if sid=="T10Y2Y":
            value=pd.to_numeric(df["10 Yr"],errors="coerce") - pd.to_numeric(df["2 Yr"],errors="coerce")
        else:
            col="2 Yr" if sid=="T2Y" else "10 Yr"
            value=pd.to_numeric(df[col],errors="coerce")
        result=pd.DataFrame({"date":d,"value":value})
    else:
        result=df.copy()
    result=result.dropna(subset=["date","value"]).sort_values("date").drop_duplicates("date",keep="last")
    result=result[result.date.dt.date<=date]
    if len(result)<2:raise ValueError("Insufficient observations by market date")
    return result,url

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
    def add(sid,field,limit,title,possible,verify,multiplier=1):
        r=d.get(sid)
        if not r or r.get(field) is None:return
        n=r[field]*multiplier
        if abs(n)<limit:return
        signals.append({"indicator":sid,"title":title,"evidence":f"{n:+.2f}",
           "period":r.get("five_observation_reference_date",r["previous_date"])+" to "+r["observation_date"],
           "conditional_interpretation":possible,"independently_verify":verify})
    add("T10Y","five_observation_change",15,"미국 장기금리 변화",
        "상승은 기업 차입비용과 주식 할인율에 부담이 될 수 있으나 성장 기대로 움직였을 수도 있음",
        "연준과 국채 실질금리·기대물가·입찰 및 증시를 재확인",100)
    add("VIX","five_observation_change",4,"VIX 단기 변동성 확대",
        "증시 옵션시장의 위험회피가 커질 수 있으나 단기 이벤트의 영향일 수도 있음",
        "신용시장과 시장 폭·증시 추세를 함께 확인")
    add("USD_KRW_ECB","five_observation_pct",1.5,"원·달러 ECB 교차환율 변화",
        "달러 강세는 원화 기준 미국 ETF 평가액에는 긍정적일 수 있지만 환율 반전 위험도 증가",
        "서울 외환시장 USD/KRW 종가와 뉴욕 거래시각·교차환율 차이를 확인")
    add("WTI","five_observation_pct",5,"원유 현물가격 변화",
        "상승은 에너지 업종에 유리할 수 있으나 물가·운송비에 부담이 될 수 있음",
        "공급 차질인지 수요 증가인지, 브렌트와 선물 가격·뉴스를 독립 확인")
    r=d.get("UNRATE")
    if r and r["change_previous"]>=0.2:
        signals.append({"indicator":"UNRATE","title":"실업률 상승",
            "evidence":f"{r['change_previous']:+.2f} %p",
            "period":r["previous_date"]+" to "+r["observation_date"],
            "conditional_interpretation":"경기 둔화 가능성",
            "independently_verify":"고용자수, 참가율 및 발표 시차 확인"})
    return signals

def main():
    scan=json.loads((DATA/"latest.json").read_text(encoding="utf-8"))
    market_date=datetime.strptime(scan["us_market_date"],"%Y-%m-%d").date()
    start=str(market_date-timedelta(days=850))
    load_sources(market_date)
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
    try:
        credit_proxies=etf_credit_proxies(market_date)
    except Exception as exc:
        credit_proxies={"status":"unavailable","reason":f"{type(exc).__name__}: {str(exc)[:120]}"}
    state="ok" if len(rows)==len(SPECS) and all(r["status"]=="ok" for r in rows) else ("partial" if rows else "unavailable")
    report={
      "market_date":str(market_date),
      "generated_at_utc":datetime.now(timezone.utc).isoformat(),
      "status":state,"requested_series_count":len(SPECS),
      "retrieved_series_count":len(rows),
      "current_series_count":sum(r["status"]=="ok" for r in rows),
      "source":"US Treasury, BLS, EIA, Cboe, ECB, and New York Fed official public sources",
      "credit_etf_proxies":credit_proxies,
      "uncovered_indicators":UNAVAILABLE_OTHER,
      "series":rows,"conditional_signals":signals,"errors":errors,
      "limitations":[
        "Observation dates differ from release dates; official data may be revised.",
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
    if rows:
        (MACRO/"latest_nonempty.json").write_text(encoded,encoding="utf-8")
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
    lines.extend(["","## 신용 위험의 ETF 가격 보조지표(옵션조정 스프레드가 아님)","",
        f"- 자료 상태: {credit_proxies['status']} / {credit_proxies.get('asof',credit_proxies.get('reason',''))}"])
    if credit_proxies["status"]=="ok":
        for label,p in credit_proxies["series"].items():
            lines.append(f"- {label} ({p['credit_etf']}-IEF): 후행 5일 {p['5d_price_return_gap_pp']:+.2f}%p, 21일 {p['21d_price_return_gap_pp']:+.2f}%p")
        lines.append("- **주의: 회사채 신용스프레드/OAS를 계산한 것이 아니라 ETF 가격수익률 차이. 듀레이션·금리 영향으로 왜곡될 수 있음.**")
    lines.extend(["","## 자동 수집하지 못하는 지표","",
        ", ".join(UNAVAILABLE_OTHER), "", "## 주간 판단 주의점","",
        "- 관측일, 공표일, 실시간 시세를 혼동하지 않고 지표 시차와 수정 가능성을 검토.",
        "- WTI 변동의 공급/수요 원인과 기업실적, 국제정책, ETF 수급은 외부 뉴스로 재검증.",
        "- 이 문서는 ChatGPT 일일 자유 해석을 저장한 파일이 아님.",
        "- 개인 계좌·보유액·현금·비중은 공개 저장소에 기록하지 않음.",""])
    (notes/f"{market_date}.md").write_text("\n".join(lines),encoding="utf-8")
    print("MACRO_DONE",market_date,state,len(rows),"signals",len(signals),flush=True)

if __name__=="__main__":
    main()
