"""Best-effort free delayed intraday observations, not executable quotes."""
import json, re
from datetime import datetime, timezone
import yfinance as yf
from research_engine import ROOT
def main():
    now=datetime.now(timezone.utc)
    path=ROOT/"analysis/triggers/latest.json"
    result={"checked_at_utc":now.isoformat(),"status":"WARN","observations":[],"limitations":["unofficial delayed bars; not fills or alerts","no trigger without verified plan"]}
    try:
        plan=json.loads(path.read_text())
        for p in plan.get("plans",[])[:15]:
            t=p["ticker"]
            if not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}",t):continue
            expires=datetime.fromisoformat(p["expiry"].replace("Z","+00:00"))
            created=datetime.fromisoformat(p["created_at_utc"].replace("Z","+00:00"))
            if not created<=now<=expires:continue
            bars=yf.Ticker(t).history(period="1d",interval="5m",auto_adjust=False)
            if bars.empty:continue
            bars=bars[bars.index < now]
            if bars.empty:continue
            row=bars.iloc[-1];stamp=bars.index[-1].to_pydatetime()
            age=(now-stamp).total_seconds()
            fresh=300<=age<=900
            close=float(row.Close)
            # Only a verified explicit numeric price threshold; volume/RS/quotes still unverified.
            level=float(p["price_level"]);direction=p["direction"]
            crossed=(direction=="above" and close>=level) or (direction=="below" and close<=level)
            result["observations"].append({"ticker":t,"bar_time":stamp.isoformat(),"close":close,"volume":float(row.Volume),"age_seconds":age,"price_condition":("observed" if crossed else "not_observed") if fresh else "stale_or_incomplete","execution_verified":False})
    except Exception as e:result["error"]=type(e).__name__+": "+str(e)[:200]
    out=ROOT/"data/research";out.mkdir(parents=True,exist_ok=True)
    (out/"intraday_latest.json").write_text(json.dumps(result,indent=2,allow_nan=False))
if __name__=="__main__":main()
