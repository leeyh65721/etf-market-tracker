"""Experimental public synthetic portfolio. Never reads user holdings."""
import json, math
from pathlib import Path
from datetime import datetime, timezone
from research_engine import ROOT, load, signal, price, num
def simulate(dates,days,start_cash=10000,cost=.001):
    cash=start_cash; positions={}; orders={}; curve=[]; trades=[]; issues=[]; peak=start_cash; loss_streak=0
    for i,d in enumerate(dates):
        if d not in days:
            issues.append([d,"missing session"]);break
        # Do not carry stale/split-discontinuous marks or fabricate fills.
        for t in positions:
            if t not in days[d] or not .65<=price(days,d,t)/positions[t]["mark"]<=1.45:
                issues.append([d,t,"missing or discontinuous mark"]);break
        if issues:break
        for t in sorted(list(positions)):
            pos=positions[t];p=price(days,d,t)
            if orders.get(t)=="sell":
                proceeds=pos["shares"]*p*(1-cost);cash+=proceeds
                pnl=proceeds-pos["basis"];loss_streak=loss_streak+1 if pnl<0 else 0
                trades.append({"ticker":t,"entry":pos["date"],"exit":d,"pnl":pnl,"return":pnl/pos["basis"]})
                del positions[t]
            else:pos["mark"]=p
        equity=cash+sum(p["shares"]*p["mark"] for p in positions.values())
        peak=max(peak,equity)
        for t in sorted(orders):
            if orders[t]!="buy" or t in positions or t not in days[d] or i==0:continue
            p=price(days,d,t)
            if t not in days[dates[i-1]] or not .65<=p/price(days,dates[i-1],t)<=1.45:continue
            # Synthetic caps only; no implication for user account.
            budget=min(cash,equity*(.05 if loss_streak>=3 else .1),max(0,equity*.5-sum(x["shares"]*x["mark"] for x in positions.values())))
            if budget<1 or equity/peak<.9:continue
            positions[t]={"shares":budget/(p*(1+cost)),"basis":budget,"entry":p,"mark":p,"date":d,"i":i};cash-=budget
        equity=cash+sum(p["shares"]*p["mark"] for p in positions.values());peak=max(peak,equity)
        curve.append({"date":d,"equity":equity,"cash":cash,"drawdown":equity/peak-1,"spy_equity":start_cash*price(days,d,"SPY")/price(days,dates[0],"SPY")})
        orders={}
        for t,p in positions.items():
            r=p["mark"]/p["entry"]-1
            if r<=-.04 or r>=.08 or i-p["i"]>=5:orders[t]="sell"
        for t,r in days[d].items():
            if t in positions or t=="SPY":continue
            try:
                if i and t in days[dates[i-1]] and signal(r) and not signal(days[dates[i-1]][t]):orders[t]="buy"
            except (ValueError,KeyError,TypeError):continue
    last=curve[-1] if curve else None
    return {"status":"WARN" if curve else "ERROR","synthetic_only":True,"curve":curve,"closed_trades":trades,"open_positions":positions,"pending_orders":orders,"issues":issues,"summary":{"return":last["equity"]/start_cash-1,"spy_return":last["spy_equity"]/start_cash-1,"max_drawdown":min(r["drawdown"] for r in curve),"stress_20pct_equity_shock":-.2*(last["equity"]-last["cash"])/last["equity"]} if last else None,"limitations":["historical simulated next-close fills only","not a live forward ledger","no sector overlap or FX model","discontinuity guard not split adjustment","fixed experimental risk parameters"]}
def main():
    dates,days,issues=load(ROOT)
    r=simulate(dates,days);r["source_issues"]=issues
    r["generated_at_utc"]=datetime.now(timezone.utc).isoformat()
    r["asof"]=r["curve"][-1]["date"] if r["curve"] else None
    r["source_asof"]=dates[-1] if dates else None
    out=ROOT/"data/research";out.mkdir(parents=True,exist_ok=True)
    (out/"paper_latest.json").write_text(json.dumps(r,indent=2,allow_nan=False))
if __name__=="__main__":main()
