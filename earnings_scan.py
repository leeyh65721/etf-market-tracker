"""Track observed analyst EPS consensus changes across dated snapshots; no backfilled revisions."""
import json,math,time
from pathlib import Path
from datetime import datetime,timezone
import yfinance as yf
from opportunity_scan import STOCKS
OUT=Path("data/earnings")
PERIODS=["0q","+1q","0y","+1y"]
def finite(v):
    try:
        x=float(v)
        return round(x,5) if math.isfinite(x) else None
    except (TypeError,ValueError):return None
def parse_estimates(table):
    if table is None or getattr(table,"empty",True):return {}
    result={}
    for period in PERIODS:
        try:
            row=table.loc[period]
            avg=finite(row.get("avg"))
            analysts=finite(row.get("numberOfAnalysts"))
            if avg is not None:result[period]={"eps_mean_usd":avg,"analyst_count":analysts}
        except (KeyError,TypeError,AttributeError):continue
    return result
def changes(current,previous):
    out={}
    for ticker,periods in current.items():
        old=previous.get(ticker,{})
        for p,v in periods.items():
            before=old.get(p,{}).get("eps_mean_usd")
            after=v["eps_mean_usd"]
            if before is None or after is None:continue
            delta=round(after-before,5)
            out.setdefault(ticker,{})[p]={"previous_eps_mean_usd":before,"current_eps_mean_usd":after,"change_usd":delta,"change_pct":round(delta/abs(before)*100,3) if before else None}
    return out
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    path=OUT/"latest.json"
    try:previous=json.loads(path.read_text()) if path.exists() else {}
    except (OSError,ValueError):previous={}
    estimates={}
    errors={}
    for t in STOCKS:
        try:
            rows=parse_estimates(yf.Ticker(t).get_earnings_estimate())
            if rows:estimates[t]=rows
            else:errors[t]="no usable EPS estimate"
        except Exception as e:errors[t]=type(e).__name__
        time.sleep(.12)
    if len(estimates)<20:raise RuntimeError("Too few available EPS consensus estimates; do not publish empty revisions")
    prev_est=previous.get("estimates",{}) if previous.get("status") in ("ok","partial") else {}
    payload={"schema_version":1,"generated_at_utc":datetime.now(timezone.utc).isoformat(),"status":"ok" if len(estimates)>=int(len(STOCKS)*.8) else "partial","coverage":{"requested":len(STOCKS),"available":len(estimates)},"estimates":estimates,"observed_revisions":changes(estimates,prev_est),"comparison_previous_snapshot_at_utc":previous.get("generated_at_utc"),"errors":errors,"limitations":["Unofficial Yahoo Finance consensus estimates; not official issuer guidance","Only compares actually observed daily snapshots; first run has no revision history","Consensus periods may roll across reporting dates; verify fiscal period before acting","Estimate changes are not verified analyst-by-analyst upgrades/downgrades","No paid API and no private portfolio data"]}
    if previous.get("generated_at_utc"):
        history=OUT/"history";history.mkdir(exist_ok=True)
        (history/(previous["generated_at_utc"][:10]+".json")).write_text(json.dumps({"generated_at_utc":previous["generated_at_utc"],"estimates":previous.get("estimates",{})},indent=2)+"\n")
    path.write_text(json.dumps(payload,indent=2)+"\n")
    print("EPS consensus coverage",payload["coverage"])
if __name__=="__main__":main()
