"""Delayed regular-session observations, never executable quotes or orders."""
import json, re, math
from datetime import datetime, timezone, timedelta
import exchange_calendars as xc
import yfinance as yf
from research_engine import ROOT

def observe(now, plans, download):
    result={"checked_at_utc":now.isoformat(),"status":"WARN","observations":[],"errors":[],"limitations":["unofficial delayed bars; not fills","price conditions only; volume/relative strength not confirmed"]}
    cal=xc.get_calendar("XNYS")
    day=now.date().isoformat()
    if not cal.is_session(day):
        result["reason"]="market_closed";return result
    start=cal.session_open(day).to_pydatetime()
    end=cal.session_close(day).to_pydatetime()
    if not start<=now<=end:
        result["reason"]="market_closed";return result
    for p in plans[:15]:
        try:
            t=p["ticker"]
            if not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}",t):raise ValueError("ticker")
            created=datetime.fromisoformat(p["created_at_utc"].replace("Z","+00:00"))
            expires=datetime.fromisoformat(p["expiry"].replace("Z","+00:00"))
            level=float(p["price_level"]);direction=p["direction"]
            if not math.isfinite(level) or level<=0 or direction not in ("above","below"):raise ValueError("threshold")
            if not created<=now<=expires:continue
            bars=download(t)
            bars=bars[(bars.index>=max(start,created)) & (bars.index<=now-timedelta(minutes=5)) & (bars.index<end)].sort_index()
            if bars.empty:raise ValueError("no completed post-plan bar")
            row=bars.iloc[-1];stamp=bars.index[-1].to_pydatetime()
            age=(now-stamp).total_seconds();close=float(row.Close);volume=float(row.Volume)
            if not math.isfinite(close) or close<=0 or not math.isfinite(volume) or volume<0:raise ValueError("invalid bar")
            fresh=300<=age<=1200
            crossed=close>=level if direction=="above" else close<=level
            result["observations"].append({"ticker":t,"plan_created":created.isoformat(),"bar_time":stamp.isoformat(),"close":close,"volume":volume,"age_seconds":age,"price_condition":("observed" if crossed else "not_observed") if fresh else "stale_or_incomplete","execution_verified":False})
        except Exception as e:
            result["errors"].append({"ticker":str(p.get("ticker","unknown")) if isinstance(p,dict) else "unknown","error":type(e).__name__})
    if not plans:result["reason"]="no_plan"
    return result

def main():
    now=datetime.now(timezone.utc)
    path=ROOT/"analysis/triggers/latest.json"
    plans=json.loads(path.read_text()).get("plans",[]) if path.exists() else []
    result=observe(now,plans,lambda t:yf.Ticker(t).history(period="1d",interval="5m",auto_adjust=False,prepost=False,timeout=15))
    out=ROOT/"data/research";out.mkdir(parents=True,exist_ok=True)
    (out/"intraday_latest.json").write_text(json.dumps(result,indent=2,allow_nan=False))
if __name__=="__main__":main()
