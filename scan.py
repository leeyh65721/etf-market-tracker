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

# Screening defaults, not guarantees of fills or tight bid-ask spreads.
MIN_AVG_DOLLAR_VOLUME_20D = 5_000_000
MIN_MEDIAN_DOLLAR_VOLUME_20D = 2_000_000
MIN_AVG_SHARES_20D = 50_000

# Explicit exclusions: derivatives-based commodity/crypto products.
# These ticker lists are not a complete security-type database; fund
# structure, assets under management and spreads require independent checks.
COMPLEX_PRODUCTS = set("""
USO BNO DBC PDBC COMT GSG DBA WEAT CORN SOYB UNG CPER KRBN
IBIT FBTC BITB ARKB ETHA FETH BITO
""".split())

# Tradable but outside the US-industry sector-rotation recommendation pool.
REGIONAL_FUNDS = set("""
FXI MCHI ASHR EWJ DXJ EWZ EWY EWT EWH EWG EWU EWI EWP EWA EWC
EWW EZA INDA EPI SMIN PIN VNM EIDO TUR GREK KWEB EMQQ
VEA VWO EFA EEM ACWI VT
""".split())
NON_SECTOR_FUNDS = set("""
SPY QQQ IWM DIA VTI VOO IVV RSP QQQM SCHD VUG VTV IVE IVW
IWF IWD IJR IJH IWB IWO IWN IWS IWP IWR IUSG IUSV ITOT
VXF VV VONE VONG VONV VTWO VB VO VBR VBK MDY SPMD SPLG
SCHB SCHX SCHG SCHV SCHM SCHA
TLT IEF SHY SGOV BIL SHV USFR TFLO VGSH VGIT VGLT GOVT
SCHR SCHO SPTL AGG BND BNDX LQD HYG JNK VCIT VCSH MUB TIP STIP VTIP
GLD IAU GLDM SGOL BAR SLV SIVR PPLT PALL
MTUM QUAL USMV SPLV VYM HDV DGRO DGRW NOBL SDY VIG VIGI VYMI SCHY
AVUV AVDV AVEM DFAX DFEV
""".split())

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
            recent_dollar_volume = (c.iloc[-20:] * v.iloc[-20:]).dropna()
            avg_shares = float(v.iloc[-20:].mean())
            avg_dollar = float(recent_dollar_volume.mean()) if len(recent_dollar_volume)==20 else 0.0
            median_dollar = float(recent_dollar_volume.median()) if len(recent_dollar_volume)==20 else 0.0
            liquid = bool(
                pd.notna(avg_shares) and pd.notna(avg_dollar) and pd.notna(median_dollar)
                and avg_shares >= MIN_AVG_SHARES_20D
                and avg_dollar >= MIN_AVG_DOLLAR_VOLUME_20D
                and median_dollar >= MIN_MEDIAN_DOLLAR_VOLUME_20D
            )
            if t in COMPLEX_PRODUCTS:
                status = "excluded_complex"
            elif not liquid:
                status = "excluded_illiquid"
            elif t in REGIONAL_FUNDS or t in NON_SECTOR_FUNDS:
                status = "watch_non_sector"
            elif excess>0 and trend:
                status = "candidate"
            else:
                status = "watch"
            rows.append(dict(ticker=t,asof=str(asof.date()),close_usd=round(c.iloc[-1],3),
                             return_5d_pct=round(week,3),return_21d_pct=round(month,3),
                             return_63d_pct=round(quarter,3),spy_excess_21d_pp=round(excess,3),
                             above_ma50=bool(c.iloc[-1]>ma50.iloc[-1]),ma20_rising=bool(ma20.iloc[-1]>ma20.iloc[-6]),
                             volume_ratio_20d=round(float(v.iloc[-1]/volbase),3) if volbase>0 else None,
                             avg_dollar_volume_20d_usd=round(avg_dollar),
                             median_dollar_volume_20d_usd=round(median_dollar),
                             avg_shares_20d=round(avg_shares),
                             liquid_enough=liquid,
                             screen=status,
                             rank_score=round(excess*.5+week*.3+(3 if trend else 0),3)))
        except Exception as e: print("skip",t,str(e))
    if not rows: raise RuntimeError("Zero validated ETFs; report not published")
    frame=pd.DataFrame(rows).sort_values("rank_score",ascending=False)
    frame.to_csv(OUT/"latest.csv",index=False)
    report=dict(generated_at_utc=datetime.now(timezone.utc).isoformat(),us_market_date=str(asof.date()),
                candidate_universe_count=len(NAMES),downloaded_price_history_count=len(data),
                valid_screened_count=len(frame),invalid_or_unverified_count=len(NAMES)-len(frame),
                eligible_sector_screened_count=int(frame.screen.isin(["candidate","watch"]).sum()),
                technical_candidate_count=int((frame.screen=="candidate").sum()),
                excluded_illiquid_count=int((frame.screen=="excluded_illiquid").sum()),
                excluded_complex_count=int((frame.screen=="excluded_complex").sum()),
                watch_non_sector_count=int((frame.screen=="watch_non_sector").sum()),
                liquidity_filter=dict(min_avg_20d_dollar_usd=MIN_AVG_DOLLAR_VOLUME_20D,
                                      min_median_20d_dollar_usd=MIN_MEDIAN_DOLLAR_VOLUME_20D,
                                      min_avg_20d_shares=MIN_AVG_SHARES_20D),
                data_source="Unofficial Yahoo Finance via yfinance (best effort, delayed or incomplete)",
                caveats=["Not a trading signal or price prediction",
                         "Candidate screen excludes thin trading and explicitly identified complex products",
                         "Other complex funds may remain; independently verify structure before recommending",
                         "AUM, fund age, fee, tracking, bid-ask spread and delisting risk require separate verification",
                         "No company fundamentals, ETF flows or verified news",
                         "USD historical returns; no KRW FX impact"],
                technical_candidates=frame[frame.screen=="candidate"].head(15).to_dict("records"))
    report_json = json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n"
    (OUT/"latest.json").write_text(report_json,encoding="utf-8")

    # Preserve dated snapshots so weekly reports can compare real historical screens.
    # Re-runs for the same US trading date replace that date's snapshot (idempotent).
    history_dir = OUT / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    market_date = str(asof.date())
    frame.to_csv(history_dir / f"{market_date}.csv", index=False)
    (history_dir / f"{market_date}.json").write_text(report_json,encoding="utf-8")

    print("COMPLETE",len(frame),"valid",asof.date(),flush=True)
if __name__=="__main__":main()
