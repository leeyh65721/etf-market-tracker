"""Experimental close-only ETF research; no orders or private data."""
import csv, json, math, statistics as st
from pathlib import Path
from datetime import datetime, timezone
import exchange_calendars as xc

ROOT=Path(__file__).resolve().parent
def num(x):
    v=float(x)
    if not math.isfinite(v): raise ValueError("nonfinite")
    return v

def load(root):
    days={}; issues=[]
    for p in sorted((root/"data/history").glob("*.csv")):
        try:
            rows={}
            with p.open() as f:
                for r in csv.DictReader(f):
                    if r["asof"]!=p.stem or r["ticker"] in rows or num(r["close_usd"])<=0: raise ValueError("date/duplicate/price")
                    rows[r["ticker"]]=r
            if "SPY" not in rows: raise ValueError("SPY missing")
            days[p.stem]=rows
        except (ValueError,TypeError,KeyError,OSError) as e: issues.append([p.name,str(e)])
    if not days: return [],{},issues
    dates=[str(x.date()) for x in xc.get_calendar("XNYS").sessions_in_range(min(days),max(days))]
    issues += [[d,"missing session"] for d in dates if d not in days]
    return dates,days,issues

def signal(r, threshold=0):
    if r["screen"]!="candidate": return None
    ret=num(r["return_5d_pct"]); vol=num(r["volume_ratio_20d"])
    if ret>2+threshold and vol>=1.2: return "momentum_proxy"
    if -5<=ret< -1-threshold and vol<1: return "pullback_proxy"
    return None

def price(days,d,t):
    return num(days[d][t]["close_usd"])

def trade(dates,days,i,t,h=5,cost=.002,stop=.04,target=.08):
    # close signal, next close entry; next close after exit condition;
    # no claimed intraday fills. Reject discontinuities rather than infer splits.
    if i+1>=len(dates): return {"status":"pending"}
    try:
        entry=price(days,dates[i+1],t); benchmark=price(days,dates[i+1],"SPY")
        prior=price(days,dates[i],t)
        for j in range(i+1,min(i+h+3,len(dates))):
            p=price(days,dates[j],t)
            if not .65<=p/prior<=1.45: return {"status":"suspect_corporate_action"}
            prior=p
            if j==i+1: continue
            due=j>=i+1+h or p/entry-1<=-stop or p/entry-1>=target
            if due:
                if j+1>=len(dates): return {"status":"pending"}
                exitp=price(days,dates[j+1],t)
                if not .65<=exitp/p<=1.45: return {"status":"suspect_corporate_action"}
                net=exitp/entry*(1-cost/2)/(1+cost/2)-1
                return {"status":"closed","entry":dates[i+1],"exit":dates[j+1],"net":net,"spy":price(days,dates[j+1],"SPY")/benchmark-1,"sessions":j-i}
        return {"status":"pending"}
    except (KeyError,ValueError,TypeError): return {"status":"missing_data"}

def metrics(rows):
    a=[r for r in rows if r["status"]=="closed"]
    if not a:return {"n":0}
    wins=[r["net"] for r in a if r["net"]>0]
    losses=[r["net"] for r in a if r["net"]<=0]
    return {"n":len(a),"win_rate":len(wins)/len(a),"expectancy":st.mean(r["net"] for r in a),"mean_excess":st.mean(r["net"]-r["spy"] for r in a),"average_win":st.mean(wins) if wins else None,"average_loss":st.mean(losses) if losses else None,"mean_sessions":st.mean(r["sessions"] for r in a)}

def run(root=ROOT):
    dates,days,issues=load(root); results=[]
    for threshold in (-.5,0,.5):
        for i,d in enumerate(dates):
            if i==0 or d not in days or dates[i-1] not in days:continue
            for t,r in days[d].items():
                try:
                    s=signal(r,threshold)
                    prev=days[dates[i-1]].get(t)
                    if not s or prev is None or signal(prev,threshold)==s:continue
                    regime="above_ma50" if days[d]["SPY"]["above_ma50"]=="True" else "below_ma50"
                    for h in (5,10,20):
                        results.append(dict(trade(dates,days,i,t,h),ticker=t,signal_date=d,strategy=s,threshold=threshold,horizon=h,regime=regime))
                except (KeyError,ValueError,TypeError) as e:issues.append([d,t,str(e)])
    cut=dates[int(len(dates)*.7)] if dates else ""
    # Purge trades spanning split. No optimization on test set.
    groups={}
    for r in results:
        if r["status"]!="closed":split="unresolved"
        elif r["signal_date"]>=cut:split="holdout"
        elif r["exit"]<cut:split="development"
        else:split="purged"
        key="|".join(map(str,(r["strategy"],r["threshold"],r["horizon"],r["regime"],split)))
        groups.setdefault(key,[]).append(r)
    report={"schema":"experimental_close_proxy_v1","generated_at_utc":datetime.now(timezone.utc).isoformat(),"asof":dates[-1] if dates else None,"status":"WARN" if dates else "ERROR","sessions":len(dates),"issues":issues,"holdout_start":cut,"metrics":{k:metrics(v) for k,v in groups.items()},"observations":results,"limitations":["snapshot prices not independently corporate-action normalized","proxy strategies not true intraday breakout or ATR","overlapping independent hypothetical trades, not portfolio equity or real fills","no automatic strategy adoption; short archive and survivorship risk","cost assumption 20 bps round trip, no tax/FX","holdout is exploratory, not locked prospective test"]}
    out=root/"data/research";out.mkdir(parents=True,exist_ok=True)
    (out/"latest.json").write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
    return report
if __name__=="__main__":run()
