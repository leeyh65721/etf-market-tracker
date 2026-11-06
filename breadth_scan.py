"""S&P 500 constituent breadth: current membership, explicit coverage and freshness."""
import io,json,time
from pathlib import Path
from datetime import datetime,timezone
import pandas as pd
import requests
import yfinance as yf
OUT=Path("data/breadth")
URL="https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
def members(html):
    tables=pd.read_html(io.StringIO(html),match="Symbol")
    table=next(t for t in tables if "Symbol" in t.columns and len(t)>=450)
    return list(dict.fromkeys(str(s).strip().replace(".","-") for s in table["Symbol"] if isinstance(s,str) and s.strip()))
def calculate(frames,tickers,asof):
    valid={}
    for t in tickers:
        d=frames.get(t)
        if d is None or len(d)<200 or d.index[-1]!=asof:continue
        c=d["Close"].astype(float)
        if c.iloc[-1]<=0 or c.iloc[-200:].isna().any():continue
        valid[t]=d
    n=len(valid)
    if not n:raise RuntimeError("No same-date constituents with 200 sessions")
    cs=[d["Close"].astype(float) for d in valid.values()]
    adv=sum(c.iloc[-1]>c.iloc[-2] for c in cs)
    dec=sum(c.iloc[-1]<c.iloc[-2] for c in cs)
    high=sum(c.iloc[-1]>=c.iloc[-252:].max() for c in cs if len(c)>=252)
    low=sum(c.iloc[-1]<=c.iloc[-252:].min() for c in cs if len(c)>=252)
    eligible52=sum(len(c)>=252 for c in cs)
    return {"universe_count":len(tickers),"valid_count":n,"coverage_pct":round(n/len(tickers)*100,2),"above_ma50_pct":round(100*sum(c.iloc[-1]>c.iloc[-50:].mean() for c in cs)/n,2),"above_ma200_pct":round(100*sum(c.iloc[-1]>c.iloc[-200:].mean() for c in cs)/n,2),"advancers":adv,"decliners":dec,"unchanged":n-adv-dec,"new_52w_highs":high,"new_52w_lows":low,"eligible_52w_count":eligible52,"equal_weighted_not_index_cap_weighted":True}
def fetch(tickers):
    result={}
    for i in range(0,len(tickers),20):
        batch=tickers[i:i+20]
        for attempt in range(2):
            try:
                data=yf.download(batch,period="15mo",interval="1d",group_by="ticker",auto_adjust=True,threads=False,progress=False,timeout=30)
                for t in batch:
                    try:
                        d=(data[t] if isinstance(data.columns,pd.MultiIndex) else data)[["Close","Volume"]].dropna(subset=["Close"])
                        d.index=pd.to_datetime(d.index).tz_localize(None).normalize()
                        if len(d)>=200:result[t]=d.sort_index()
                    except (KeyError,ValueError,TypeError):pass
                break
            except Exception as e:
                print("breadth batch retry",i,attempt,str(e))
                time.sleep(2)
    return result
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    response=requests.get(URL,headers={"User-Agent":"MarketResearchBot/1.0 (public market research)"},timeout=30)
    response.raise_for_status()
    tickers=members(response.text)
    if not 495<=len(tickers)<=520:raise RuntimeError("Unexpected S&P 500 constituent count")
    frames=fetch(tickers)
    if not frames:raise RuntimeError("No prices retrieved")
    from collections import Counter
    asof=Counter(d.index[-1] for d in frames.values()).most_common(1)[0][0]
    report=calculate(frames,tickers,asof)
    if report["coverage_pct"]<90:raise RuntimeError("Insufficient breadth coverage: "+str(report["coverage_pct"]))
    payload={"schema_version":1,"generated_at_utc":datetime.now(timezone.utc).isoformat(),"market_date":asof.strftime("%Y-%m-%d"),"status":"ok" if report["coverage_pct"]>=98 else "partial","source_url":URL,"membership_type":"current_constituents_only","historical_backtest_warning":"Current membership cannot be used for unbiased historical constituent backtests","metrics":report}
    (OUT/"latest.json").write_text(json.dumps(payload,indent=2)+"\n")
    print("S&P 500 breadth",payload["market_date"],report["coverage_pct"])
if __name__=="__main__":main()
