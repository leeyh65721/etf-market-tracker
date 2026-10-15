"""Public-market technical ETF scanner; no brokerage or personal information."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).parent
OUT = ROOT / "data"
OUT.mkdir(exist_ok=True)
NAMES = list(dict.fromkeys((ROOT / "universe.txt").read_text().split()))
NAMES = [t for t in NAMES if not t.startswith("#")]
def fetch():
    items = {}
    for n in range(0,len(NAMES),20):
        chunk = NAMES[n:n+20]
        for retry in range(3):
            try:
                data=yf.download(chunk,period="9mo",interval="1d",group_by="ticker",auto_adjust=True,threads=False,progress=False,timeout=25)
                if data.empty: raise ValueError("empty response")
                for t in chunk:
                    try:
                        d=data[t] if isinstance(data.columns,pd.MultiIndex) else data
                        d=d[["Close","Volume"]].dropna(subset=["Close"]).copy()
                        d.index=pd.to_datetime(d.index).tz_localize(None).normalize()
                        d=d.sort_index()
                        if len(d)>=65 and d["Close"].iloc[-1]>0: items[t]=d
                    except (KeyError,ValueError,TypeError): pass
                break
            except Exception as e:
                print("batch retry",retry,chunk[:2],str(e))
                time.sleep(2+retry*3)
        print("retrieved",len(items),"of",len(NAMES),flush=True)
    return items
def ret(s,n): return float((s.iloc[-1]/s.iloc[-n-1]-1)*100)
def main():
    data=fetch()
    if "SPY" not in data: raise RuntimeError("Missing SPY benchmark - no report published")
    spy=data["SPY"]
    asof=spy.index[-1]
    rows=[]
    for t,d in data.items():
        if len(d)<65 or d.index[-1]!=asof: continue
        c=d["Close"].astype(float); v=d["Volume"].astype(float)
        ma20=c.rolling(20).mean(); ma50=c.rolling(50).mean()
        try:
            week,month,quarter=ret(c,5),ret(c,21),ret(c,63)
            excess=month-ret(spy["Close"],21)
            volbase=v.iloc[-21:-1].mean()
            trend=bool(c.iloc[-1]>ma50.iloc[-1] and ma20.iloc[-1]>ma20.iloc[-6])
            rows.append(dict(ticker=t,asof=str(asof.date()),close_usd=round(c.iloc[-1],3),
                             return_5d_pct=round(week,3),return_21d_pct=round(month,3),
                             return_63d_pct=round(quarter,3),spy_excess_21d_pp=round(excess,3),
                             above_ma50=bool(c.iloc[-1]>ma50.iloc[-1]),ma20_rising=bool(ma20.iloc[-1]>ma20.iloc[-6]),
                             volume_ratio_20d=round(float(v.iloc[-1]/volbase),3) if volbase>0 else None,
                             screen="candidate" if excess>0 and trend else "watch",
                             rank_score=round(excess*.5+week*.3+(3 if trend else 0),3)))
        except Exception as e: print("skip",t,str(e))
    if not rows: raise RuntimeError("Zero validated ETFs; report not published")
    frame=pd.DataFrame(rows).sort_values("rank_score",ascending=False)
    frame.to_csv(OUT/"latest.csv",index=False)
    report=dict(generated_at_utc=datetime.now(timezone.utc).isoformat(),us_market_date=str(asof.date()),
                candidate_universe_count=len(NAMES),downloaded_price_history_count=len(data),
                valid_screened_count=len(frame),invalid_or_unverified_count=len(NAMES)-len(frame),
                data_source="Unofficial Yahoo Finance via yfinance (best effort, delayed or incomplete)",
                caveats=["Not a trading signal or price prediction","No company fundamentals, ETF flows or verified news","USD historical returns; no KRW FX impact"],
                technical_candidates=frame[frame.screen=="candidate"].head(15).to_dict("records"))
    (OUT/"latest.json").write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n")
    print("COMPLETE",len(frame),"valid",asof.date(),flush=True)
if __name__=="__main__":main()
