"""Public-only stock/sector opportunity scanner. Watch flags are not trade recommendations."""
import json
from pathlib import Path
from datetime import datetime,timezone
import pandas as pd
import yfinance as yf

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"data/opportunities"
STOCKS="""AAPL MSFT NVDA AMZN META GOOGL AVGO TSLA JPM V MA COST WMT HD LLY JNJ PG KO PEP XOM CVX CAT GE RTX BA HON ORCL CRM NOW ADBE AMD MU AMAT LRCX KLAC ASML TSM QCOM TXN INTC ARM PANW CRWD PLTR SNOW DDOG NET SHOP UBER NFLX DIS COIN HOOD SOFI GS MS BAC WFC SCHW BLK NEE DUK LIN DE ETN UPS FDX GM MCD NKE SBUX TGT LOW CVS ISRG GILD MRK PFE TMO DHR VRTX""".split()
SECTORS="XLK XLF XLP XLY XLE XLV XLI XLU XLB XLRE XLC SOXX XBI IGV IWM RSP".split()
BENCH=["SPY","QQQ"]
ALL=list(dict.fromkeys(STOCKS+SECTORS+BENCH+["HYG","LQD","IEF"]))
SECTOR_OF={"NVDA":"SOXX","AMD":"SOXX","MU":"SOXX","AVGO":"SOXX","AMAT":"SOXX","LRCX":"SOXX","KLAC":"SOXX","TSM":"SOXX","ASML":"SOXX","JPM":"XLF","BAC":"XLF","GS":"XLF","MS":"XLF","WFC":"XLF","COST":"XLP","WMT":"XLP","PG":"XLP","KO":"XLP","PEP":"XLP","XOM":"XLE","CVX":"XLE","CAT":"XLI","GE":"XLI","BA":"XLI","AMZN":"XLY","TSLA":"XLY","HD":"XLY","META":"XLC","GOOGL":"XLC","NFLX":"XLC","LLY":"XLV","JNJ":"XLV","MRK":"XLV","PFE":"XLV"}
HORIZONS=[1,3,5,10,20]
def ret(s,n):return round((float(s.iloc[-1])/float(s.iloc[-n-1])-1)*100,3)
def drawdown(s):return round(float((s/s.cummax()-1).min()*100),3)
def observe(c,v,spy,qqq,sector=None):
    if min(len(c),len(spy),len(qqq))<65:return None
    liquidity=float((c.iloc[-20:]*v.iloc[-20:]).mean())
    if not pd.notna(liquidity) or liquidity<5000000:return None
    r5,r20,r60=ret(c,5),ret(c,20),ret(c,60)
    sp,qp=ret(spy,20),ret(qqq,20)
    sec=ret(sector,20) if sector is not None and len(sector)>20 else None
    return {"close_usd":round(float(c.iloc[-1]),3),"return_5d_pct":r5,"return_20d_pct":r20,"return_60d_pct":r60,"spy_excess_20d_pp":round(r20-sp,3),"qqq_excess_20d_pp":round(r20-qp,3),"sector_excess_20d_pp":round(r20-sec,3) if sec is not None else None,"avg_dollar_volume_20d_usd":round(liquidity),"volume_ratio_20d":round(float(v.iloc[-1]/v.iloc[-21:-1].mean()),3) if v.iloc[-21:-1].mean()>0 else None,"above_ma50":bool(c.iloc[-1]>c.iloc[-50:].mean()),"technical_watch":bool(c.iloc[-1]>c.iloc[-20:].mean() and c.iloc[-1]>c.iloc[-50:].mean() and r20>sp and r20>qp),"not_a_buy_recommendation":True}
def audit(frames,records):
    result=[]
    for rec in records:
        t=rec.get("ticker"); date=rec.get("asof"); price=rec.get("close_usd")
        if t not in frames or not isinstance(price,(float,int)) or price<=0:continue
        c=frames[t]["Close"]; dates=c.index.strftime("%Y-%m-%d").tolist()
        if date not in dates:continue
        idx=dates.index(date); horizons={}
        for n in HORIZONS:
            if idx+n>=len(c):continue
            performance=(float(c.iloc[idx+n])/price-1)*100
            d={"return_pct":round(performance,3),"max_drawdown_pct":drawdown(c.iloc[idx:idx+n+1])}
            for b in ["SPY","QQQ",rec.get("sector_benchmark")]:
                if b not in frames:continue
                s=frames[b]["Close"].reindex(c.index)
                if pd.isna(s.iloc[idx]) or pd.isna(s.iloc[idx+n]):continue
                d[b.lower()+"_excess_pp"]=round(performance-(float(s.iloc[idx+n])/float(s.iloc[idx])-1)*100,3)
            horizons[str(n)]=d
        result.append({"ticker":t,"asof":date,"horizons":horizons})
    return result
def fetch():
    frames={}
    for start in range(0,len(ALL),20):
        names=ALL[start:start+20]
        try:
            batch=yf.download(names,period="1y",interval="1d",group_by="ticker",auto_adjust=True,threads=False,progress=False,timeout=30)
            for t in names:
                try:
                    d=(batch[t] if isinstance(batch.columns,pd.MultiIndex) else batch)[["Close","Volume"]].dropna()
                    d.index=pd.to_datetime(d.index).tz_localize(None).normalize()
                    if len(d)>=65:frames[t]=d.sort_index()
                except (KeyError,TypeError,ValueError):pass
        except Exception as e:print("batch failed",names[0],str(e))
    return frames
def build(frames,previous=None,history=None):
    if "SPY" not in frames or "QQQ" not in frames:raise RuntimeError("Missing benchmark")
    asof=frames["SPY"].index[-1]
    valid={t:d for t,d in frames.items() if len(d)>=65 and d.index[-1]==asof}
    if "QQQ" not in valid:raise RuntimeError("Stale QQQ")
    spy,qqq=valid["SPY"]["Close"],valid["QQQ"]["Close"]
    stocks=[]
    for t in STOCKS:
        if t not in valid:continue
        sec=SECTOR_OF.get(t)
        o=observe(valid[t]["Close"],valid[t]["Volume"],spy,qqq,valid[sec]["Close"] if sec in valid else None)
        if o:stocks.append({"ticker":t,"asof":asof.strftime("%Y-%m-%d"),"sector_benchmark":sec,**o})
    stocks.sort(key=lambda x:(x["technical_watch"],x["spy_excess_20d_pp"]),reverse=True)
    sectors=[{"ticker":t,"return_5d_pct":ret(valid[t]["Close"],5),"return_20d_pct":ret(valid[t]["Close"],20),"return_60d_pct":ret(valid[t]["Close"],60),"spy_excess_20d_pp":round(ret(valid[t]["Close"],20)-ret(spy,20),3)} for t in SECTORS if t in valid]
    sectors.sort(key=lambda x:x["spy_excess_20d_pp"],reverse=True)
    sample=[valid[t]["Close"] for t in STOCKS if t in valid]
    long=[s for s in sample if len(s)>=200]
    breadth={"scope":"curated_stock_sample_not_sp500","sample_size":len(sample),"above_ma50_pct":round(100*sum(s.iloc[-1]>s.iloc[-50:].mean() for s in sample)/len(sample),2) if sample else None,"above_ma200_pct":round(100*sum(s.iloc[-1]>s.iloc[-200:].mean() for s in long)/len(long),2) if long else None,"advancers_1d":sum(s.iloc[-1]>s.iloc[-2] for s in sample),"decliners_1d":sum(s.iloc[-1]<s.iloc[-2] for s in sample)}
    credit={t:{"return_5d_pct":ret(valid[t]["Close"],5)} for t in ["HYG","LQD","IEF"] if t in valid}
    return {"schema_version":1,"generated_at_utc":datetime.now(timezone.utc).isoformat(),"us_market_date":asof.strftime("%Y-%m-%d"),"status":"ok" if len(stocks)>=30 else "partial","coverage":{"stock_universe":len(STOCKS),"valid_liquid_stocks":len(stocks)},"market_breadth":breadth,"credit_etf_proxies_not_credit_spreads":credit,"sector_rotation":sectors,"stocks":stocks,"forward_audit":audit(valid,history if history is not None else (previous or {}).get("stocks",[])),"limitations":["Curated stock sample, not all US stocks or true S&P 500 breadth","Free Yahoo data may be stale or revised","Earnings revisions and issuer event catalysts require separate verified sources","Watch flag is not an entry signal; no invented target or stop","Close-to-close audit ignores fills, fees and slippage"]}
def main():
    OUT.mkdir(parents=True,exist_ok=True); p=OUT/"latest.json"
    try:previous=json.loads(p.read_text()) if p.exists() else {}
    except (OSError,ValueError):previous={}
    archive=OUT/"history"
    past=[previous]
    if archive.exists():
        for f in sorted(archive.glob("*.json"))[-25:]:
            try:past.append(json.loads(f.read_text()))
            except (OSError,ValueError):pass
    records=[r for snap in past for r in snap.get("stocks",[]) if r.get("technical_watch")]
    report=build(fetch(),previous,records)
    if previous.get("us_market_date") and previous["us_market_date"]!=report["us_market_date"]:
        archive.mkdir(exist_ok=True)
        (archive/(previous["us_market_date"]+".json")).write_text(json.dumps(previous,indent=2)+"\n")
    p.write_text(json.dumps(report,indent=2)+"\n")
    print("opportunity scan",report["us_market_date"],report["coverage"],report["status"])
if __name__=="__main__":main()
