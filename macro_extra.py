"""Additional eight macro research categories, isolated from the 22 proven base sources.

Source-first, conservative parsing: each category reports observed/stale/unavailable/
manual; never invents a price, economic value or release date. No FRED queries.
ISM data requires license approval: no bot scraping, redistribution or caching.
"""
from __future__ import annotations
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from io import BytesIO, StringIO
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

ROOT=Path(__file__).parent
OUT=ROOT/"data"/"macro"
NOTES=ROOT/"analysis"/"macro"
MONTHS={name.lower():num for num,name in enumerate(
    ("January","February","March","April","May","June","July","August",
     "September","October","November","December"),1)}
SOURCES={
 "CORE_PCE":("근원 PCE 물가(전년대비)", "monthly",
             "https://www.bea.gov/data/personal-consumption-expenditures-price-index-excluding-food-and-energy"),
 "INITIAL_CLAIMS":("미국 주간 신규 실업수당 청구(계절조정)", "weekly",
             "https://www.dol.gov/ui/data.pdf"),
 "RETAIL_SALES":("미국 소매·음식서비스 매출(월간 전월비)", "monthly",
             "https://www.census.gov/retail/sales.html"),
 "NFCI":("시카고 연준 금융여건지수", "weekly",
             "https://www.chicagofed.org/research/data/nfci/current-data"),
 "MFG_NEW_ORDERS":("미국 제조업 신규주문(전월비)", "monthly",
             "https://www.census.gov/manufacturing/m3/current/index.html"),
 "DURABLE_NEW_ORDERS":("미국 내구재 신규주문(전월비)", "monthly",
             "https://www.census.gov/manufacturing/m3/adv/current/index.html"),
 "ISM_MANUFACTURING":("ISM 제조업 PMI", "monthly",
             "https://www.ismworld.org/supply-management-news-and-reports/reports/ism-pmi-reports/"),
 "ISM_SERVICES":("ISM 서비스업 PMI", "monthly",
             "https://www.ismworld.org/supply-management-news-and-reports/reports/ism-pmi-reports/"),
 "REAL_GDP":("미국 실질 GDP 성장률(전기비 연율)", "quarterly",
             "https://www.bea.gov/data/gdp/gross-domestic-product"),
 "SP500_BREADTH":("S&P 500 구성종목 상승 비율(자체 산출)", "daily",
             "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"),
}
CATEGORIES=[
 ("pce",("CORE_PCE",)),
 ("weekly_claims",("INITIAL_CLAIMS",)),
 ("retail_sales",("RETAIL_SALES",)),
 ("financial_conditions",("NFCI",)),
 ("manufacturing_orders",("MFG_NEW_ORDERS","DURABLE_NEW_ORDERS")),
 ("ism_pmi",("ISM_MANUFACTURING","ISM_SERVICES")),
 ("real_gdp",("REAL_GDP",)),
 ("market_breadth",("SP500_BREADTH",)),
]
MAX_AGE={"monthly":80,"weekly":19,"quarterly":200,"daily":4}
HEADERS={"User-Agent":"ETFMarketTracker/1.0 (+public research; contact via Github)",
         "Accept":"text/html,text/csv,application/pdf,*/*"}


def fetch(url, timeout=15):
    last=None
    for n in range(2):
        try:
            r=requests.get(url,headers=HEADERS,timeout=timeout)
            r.raise_for_status()
            if len(r.content)>15000000:raise ValueError("Unusually large source file")
            return r.content
        except requests.RequestException as exc:
            last=exc
            if getattr(exc.response,"status_code",None) in (400,401,403,404):
                break
    raise RuntimeError(f"{type(last).__name__}: {str(last)[:160]}")


def html_text(url):
    raw=fetch(url)
    soup=BeautifulSoup(raw,"html.parser")
    for tag in soup.select("script,style,nav,footer,header"):
        tag.decompose()
    return soup.get_text(" ",strip=True),soup


def monthdate(month, year):
    value=MONTHS[month.lower()]
    return date(int(year),value,1)


def record(sid, value, observed, unit, method, note="", url=None,
           previous=None, previous_observed=None, sample_size=None):
    if not isinstance(observed,date):raise ValueError("Missing observation date")
    if not isinstance(value,(float,int)) or not -1e12<float(value)<1e12:
        raise ValueError("Invalid numeric value")
    r={"series_id":sid,"name":SOURCES[sid][0],"frequency":SOURCES[sid][1],
       "value":round(float(value),5),"unit":unit,"observation_date":observed.isoformat(),
       "source_url":url or SOURCES[sid][2],"collection_method":method,
       "notes":note}
    if previous is not None:r["previous_value"]=round(float(previous),5)
    if previous_observed:r["previous_date"]=previous_observed.isoformat()
    if sample_size is not None:r["sample_size"]=int(sample_size)
    return r


def parse_core_pce(raw):
    txt=BeautifulSoup(raw,"html.parser").get_text(" ",strip=True)
    rx=r"\b("+"|".join(MONTHS)+r")\s+(20\d{2})\s*(?:\||:)?\s*([+-]?\d{1,2}(?:\.\d+)?)\s*%"
    values=[]
    for m in re.finditer(rx,txt,re.I):
        stamp=monthdate(m.group(1),m.group(2))
        values.append((stamp,float(m.group(3))))
    if len(set(d for d,_ in values))<2:raise ValueError("BEA PCE chart rows not found")
    series=dict(values)
    current,prior=sorted(series)[-2:]
    return record("CORE_PCE",series[current],current,"% YoY","BEA headline chart",
                  "Released core PCE year-over-year rate; release date requires independent checking",
                  previous=series[prior],previous_observed=prior)


def parse_real_gdp(raw):
    txt=BeautifulSoup(raw,"html.parser").get_text(" ",strip=True)
    # BEA front-page chart: '2nd Quarter 2026 +2.2%' or 'Q2 2026 +2.2%'.
    rx=r"\b(?:Q([1-4])\s*(20\d{2})|([1-4])(?:st|nd|rd|th)?\s+Quarter\s+(20\d{2}))\s*(?:\||:)?\s*([+-]?\d{1,2}(?:\.\d+)?)\s*%"
    values={}
    for m in re.finditer(rx,txt,re.I):
        q=int(m.group(1) or m.group(3));y=int(m.group(2) or m.group(4))
        values[date(y,(q-1)*3+1,1)]=float(m.group(5))
    if values:
        d=max(values)
        return record("REAL_GDP",values[d],d,"% q/q annualized","BEA headline GDP chart",
                      "Quarterly real GDP, annualized; check latest revision",
                      previous=values[sorted(values)[-2]] if len(values)>1 else None)
    # Alternative official introductory release paragraph.
    rx2=r"real gross domestic product\s*\(GDP\)\s*(?:increased|decreased)\s+at an annual rate of\s+(\d+(?:\.\d+)?)\s+percent\s+in the\s+(first|second|third|fourth)\s+quarter\s+of\s+(20\d{2})"
    m=re.search(rx2,txt,re.I)
    if not m:raise ValueError("BEA real GDP annualized rate not visible")
    quarters={"first":1,"second":2,"third":3,"fourth":4}
    q=quarters[m.group(2).lower()]
    sign=-1 if re.search(r"real gross domestic product\s*\(GDP\)\s*decreased",m.group(0),re.I) else 1
    return record("REAL_GDP",sign*float(m.group(1)),date(int(m.group(3)),3*q-2,1),
                  "% q/q annualized","BEA release statement")


def parse_claims_pdf(raw):
    reader=PdfReader(BytesIO(raw))
    if len(reader.pages)<1:raise ValueError("Empty DOL report")
    txt=" ".join((page.extract_text() or "") for page in reader.pages[:3])
    txt=re.sub(r"\s+"," ",txt)
    # DOL release prose usually omits the year after "week ending".
    # Pair the reporting week with the PDF's own publication year instead.
    heading=re.search(r"(?:Thursday|Friday|Wednesday),?\s+[A-Z][a-z]+\s+\d{1,2},?\s+(20\d{2})",txt,re.I)
    d=re.search(r"In the week ending\s+([A-Z][a-z]+)\s+(\d{1,2})(?:,?\s+(20\d{2}))?",txt,re.I)
    value=re.search(r"advance figure for seasonally adjusted initial claims was\s+([\d,]{5,9})",txt,re.I)
    if not d or not value or (not d.group(3) and not heading):
        raise ValueError("No validated DOL week, issue year or seasonally adjusted claims")
    year=int(d.group(3) or heading.group(1))
    month=MONTHS[d.group(1).lower()]
    if heading and not d.group(3):
        # December weekly claims published in January refer to previous year.
        release_year=int(heading.group(1))
        if month==12 and year==release_year:
            year-=1
    day=date(year,month,int(d.group(2)))
    return record("INITIAL_CLAIMS",int(value.group(1).replace(",","")),day,"persons",
                  "DOL Weekly Claims PDF", "Seasonally adjusted initial claims; week ending date")


def parse_retail(raw):
    txt=BeautifulSoup(raw,"html.parser").get_text(" ",strip=True)
    rx=r"Advance estimates of U\.S\. retail and food services sales for\s+([A-Z][a-z]+)\s+(20\d{2}).{0,260}?\b(up|down|unchanged)\s+(\d+(?:\.\d+)?)\s+percent"
    m=re.search(rx,txt,re.I)
    if not m:raise ValueError("No current Census advance retail-sales estimate/period")
    num=float(m.group(4))*(-1 if m.group(3).lower()=="down" else 1)
    return record("RETAIL_SALES",num,monthdate(m.group(1),m.group(2)),"% m/m",
                  "Census advance retail release summary",
                  "Seasonally adjusted but nominal; retail plus food services, subject to revisions")


def parse_manufacturing(raw, sid):
    txt=BeautifulSoup(raw,"html.parser").get_text(" ",strip=True)
    descriptor="manufactured durable goods" if sid=="DURABLE_NEW_ORDERS" else "manufactured goods"
    rx=(r"New orders for\s+"+descriptor+r"\s+in\s+([A-Z][a-z]+)(?:\s+(20\d{2}))?"
       r".{0,230}?\b(increased|decreased)\s+(?:[\$\d.,]+\s+billion\s+or\s+)?"
       r"(?:(virtually unchanged)|([\d.]+)\s+percent)")
    m=re.search(rx,txt,re.I)
    if not m:raise ValueError("Census release summary new orders/period not parsed")
    year=m.group(2)
    if not year:
        stamp_rx=r"\b("+"|".join(MONTHS)+r")\s+\d{1,2},?\s+(20\d{2})\b"
        issued=re.search(stamp_rx,txt,re.I)
        if issued:
            yy=int(issued.group(2))
            if MONTHS[m.group(1).lower()]>MONTHS[issued.group(1).lower()]:yy-=1
            year=str(yy)
    if not year:raise ValueError("Census report has no verifiable reference year")
    val=0.0 if m.group(4) else float(m.group(5))*(-1 if m.group(3).lower()=="decreased" else 1)
    return record(sid,val,monthdate(m.group(1),year),"% m/m",
                  "Census M3 release summary",
                  "Nominal seasonally adjusted order change; zero may be rounded 'virtually unchanged'")


def nfci(market_date):
    source=SOURCES["NFCI"][2]
    text,soup=html_text(source)
    urls=[]
    for a in soup.find_all("a",href=True):
        href=a.get("href","")
        label=a.get_text(" ",strip=True).lower()
        if "csv" in label or ".csv" in href.lower():
            from urllib.parse import urljoin
            url=urljoin(source,href)
            if url.startswith("https://") and ".csv" in url.lower():
                urls.append(url)
    for url in urls:
        try:
            f=pd.read_csv(StringIO(fetch(url,20).decode("utf-8-sig")))
            f.columns=f.columns.map(str).str.strip().str.lower()
            datecol=next((c for c in f.columns if c in ("date","observation_date","week","week ending")),None)
            valcol=next((c for c in f.columns if c in ("nfci","nfci_index","nfci index")),None)
            if datecol and valcol:
                df=pd.DataFrame({"date":pd.to_datetime(f[datecol],errors="coerce"),
                                 "value":pd.to_numeric(f[valcol],errors="coerce")}).dropna()
                df=df[df.date.dt.date<=market_date].sort_values("date")
                if len(df)>=2:
                    return record("NFCI",float(df.value.iloc[-1]),df.date.iloc[-1].date(),
                        "index","Chicago Fed official CSV",url=url,
                        previous=df.value.iloc[-2],previous_observed=df.date.iloc[-2].date())
        except Exception:
            continue
    # Official news summary fallback: mark older dated values stale instead
    # of silently using stale HTML as the current index.
    rx=(r"\bNFCI\s+(?:decreased|increased|was unchanged).*?\bto\s+([+\-−]?\d+\.\d+)"
        r".{0,100}?\bweek ending\s+("+"|".join(MONTHS)+r")\s+(\d{1,2})")
    m=re.search(rx,text,re.I)
    if not m:raise ValueError("No verifiable Chicago Fed NFCI CSV or dated official summary")
    value=float(m.group(1).replace("−","-"))
    month=MONTHS[m.group(2).lower()]
    day=int(m.group(3))
    year=market_date.year
    stamped=date(year,month,day)
    if stamped>market_date:stamped=date(year-1,month,day)
    return record("NFCI",value,stamped,"index",
                  "Chicago Fed official dated public summary",
                  "No verified official CSV was discoverable; dated summary may be stale")


def breadth(market_date):
    # This is S&P500 company participation, not all US-listed stocks.
    import yfinance as yf
    url=SOURCES["SP500_BREADTH"][2]
    html=fetch(url,timeout=18)
    f=pd.read_html(BytesIO(html),match="Symbol")[0]
    symbolcol=next((c for c in f.columns if str(c).strip().lower()=="symbol"),None)
    if symbolcol is None:raise ValueError("S&P 500 constituent table missing Symbol")
    syms=list(dict.fromkeys(str(s).strip().replace(".","-") for s in f[symbolcol].dropna()))
    if not 450<=len(syms)<=530:raise ValueError(f"Constituent list unverified: {len(syms)}")
    adv=dec=flat=0
    asof=None
    for idx in range(0,len(syms),50):
        block=syms[idx:idx+50]
        try:
            df=yf.download(block,period="7d",interval="1d",auto_adjust=True,
                           group_by="ticker",threads=False,progress=False,timeout=18)
        except Exception as e:
            print("BREADTH_BATCH_FAILED",idx,str(e)[:100],flush=True)
            continue
        for symbol in block:
            try:
                d=df[symbol] if isinstance(df.columns,pd.MultiIndex) else df
                close=d["Close"].dropna()
                close.index=pd.to_datetime(close.index).tz_localize(None).normalize()
                close=close[close.index.date<=market_date].sort_index()
                if len(close)<2 or close.index[-1].date()!=market_date:continue
                r=float(close.iloc[-1]/close.iloc[-2]-1)
                if r>0:adv+=1
                elif r<0:dec+=1
                else:flat+=1
            except Exception:continue
    n=adv+dec+flat
    if n<400 or n/len(syms)<.8:raise ValueError(f"S&P breadth too sparse: {n}/{len(syms)}")
    out=record("SP500_BREADTH",100*adv/n,market_date,"% constituents up",
               "S&P 500 listed constituents via Wikipedia, adjusted daily close via yfinance",
               "Advancing / all valid constituents; not NYSE-wide A/D ratio; prices unofficial",
               sample_size=n)
    out["advanced"]=adv
    out["declined"]=dec
    out["unchanged"]=flat
    out["universe_size"]=len(syms)
    return out


def evaluate(sid, datum, market_date):
    observed=date.fromisoformat(datum["observation_date"])
    if observed>market_date:raise ValueError("Source observation after benchmark market date")
    delta=(market_date-observed).days
    max_age={"CORE_PCE":90,"REAL_GDP":210,"NFCI":24,
             "INITIAL_CLAIMS":24,"MFG_NEW_ORDERS":85,
             "DURABLE_NEW_ORDERS":85,"RETAIL_SALES":85,
             "SP500_BREADTH":0}.get(sid,MAX_AGE[SOURCES[sid][1]])
    datum["status"]="ok" if delta<=max_age else "stale"
    datum["age_days"]=delta
    return datum


def collect_one(sid,market_date):
    if sid.startswith("ISM_"):
        # Explicitly not scraping/storing ISM's licensed PMI time series.
        return {"series_id":sid,"name":SOURCES[sid][0],"status":"manual",
                "source_url":SOURCES[sid][2],"notes":
                "ISM forbids automated harvesting and republishing; user must consult licensed report."}
    try:
        if sid=="NFCI":r=nfci(market_date)
        elif sid=="SP500_BREADTH":r=breadth(market_date)
        else:
            raw=fetch(SOURCES[sid][2])
            r={
              "CORE_PCE":lambda:parse_core_pce(raw),
              "INITIAL_CLAIMS":lambda:parse_claims_pdf(raw),
              "RETAIL_SALES":lambda:parse_retail(raw),
              "MFG_NEW_ORDERS":lambda:parse_manufacturing(raw,sid),
              "DURABLE_NEW_ORDERS":lambda:parse_manufacturing(raw,sid),
              "REAL_GDP":lambda:parse_real_gdp(raw),
            }[sid]()
        return evaluate(sid,r,market_date)
    except Exception as exc:
        return {"series_id":sid,"name":SOURCES[sid][0],"status":"unavailable",
                "source_url":SOURCES[sid][2],"error":f"{type(exc).__name__}: {str(exc)[:180]}"}


def main():
    scan=json.loads((ROOT/"data"/"latest.json").read_text(encoding="utf-8"))
    market_date=date.fromisoformat(scan["us_market_date"])
    keys=list(SOURCES)
    results={}
    # Market breadth has many quote calls; do not block other primary-source reports.
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures={pool.submit(collect_one,key,market_date):key for key in keys}
        for f in as_completed(futures):
            k=futures[f]
            try:results[k]=f.result()
            except Exception as exc:
                results[k]={"series_id":k,"name":SOURCES[k][0],"status":"unavailable",
                            "source_url":SOURCES[k][2],"error":f"{type(exc).__name__}: {str(exc)[:120]}"}
            print("EXTRA_MACRO",k,results[k]["status"],flush=True)
    categories={}
    for group,ids in CATEGORIES:
        categories[group]={"indicators":list(ids),"observed":sum(results[x]["status"]=="ok" for x in ids),
                           "total":len(ids)}
    ok=sum(r["status"]=="ok" for r in results.values())
    report={"generated_at_utc":datetime.now(timezone.utc).isoformat(),
            "market_date":str(market_date),"coverage":"8 named categories, 10 separately labelled indicators",
            "requested_indicators":len(keys),"ok_indicators":ok,
            "status":"ok" if ok==len(keys) else "partial" if ok else "unavailable",
            "categories":categories,"series":[results[k] for k in keys],
            "limitations":["ISM PMI is manual-only due to published data usage restrictions.",
                           "Source access or parsing failures are explicitly unavailable, never zero.",
                           "BEA GDP/PCE and Census estimates can be revised; observation month differs from release day.",
                           "Market breadth, if observed, is S&P 500 constituent price breadth, not all US listed equities.",
                           "No personal portfolio data, investment orders or fabricated source values."]}
    OUT.mkdir(parents=True,exist_ok=True)
    NOTES.mkdir(parents=True,exist_ok=True)
    encoded=json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n"
    (OUT/"extra_latest.json").write_text(encoded,encoding="utf-8")
    (OUT/"history").mkdir(exist_ok=True)
    (OUT/"history"/f"extra-{market_date}.json").write_text(encoded,encoding="utf-8")
    lines=[f"# 추가 거시경제 8분야 기록 — 미국 {market_date}","",
           "> 기존 공식 22개 시계열과 별도. 수집 실패는 0이 아니라 미확인. ISM은 이용제한으로 자동 보관 금지.",
           f"- 완료시각 UTC: {report['generated_at_utc']}",
           f"- 유효 관측: {ok}/{len(keys)} 세부 지표 (8개 분야)","",
           "| 분야 | 지표 | 상태 | 관측일 | 값 | 출처 |","|---|---|---|---|---:|---|"]
    for group,ids in CATEGORIES:
        for k in ids:
            r=results[k]
            lines.append(f"|{group}|{r['name']}|{r['status']}|{r.get('observation_date','-')}|"
                         f"{r.get('value','-')} {r.get('unit','')}|[원자료]({r['source_url']})|")
            if r.get("error"):lines.append(f"  - {k} 미수집: {r['error']}")
    lines.extend(["","## 해석 주의","",
                  "- 이 기록은 기계적 관측용이며 경기 전환 또는 ETF 매수·매도의 자동 신호가 아님.",
                  "- 반드시 공표일, 시차, 지표 조정 여부와 최신 공식 자료를 주간 분석에서 재확인.",""])
    (NOTES/f"extra-{market_date}.md").write_text("\n".join(lines),encoding="utf-8")
    print("EXTRA_MACRO_DONE",market_date,ok,len(keys),flush=True)


if __name__=="__main__":
    main()
