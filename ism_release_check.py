"""Public ISM release-check metadata only. Never scrape, store or redistribute PMI report content."""
import json
from datetime import datetime,date,timezone,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
OUT=Path("data/macro/ism_release_check.json")
SOURCE="https://www.ismworld.org/supply-management-news-and-reports/reports/ism-pmi-reports/"
TERMS="https://www.ismworld.org/footer/terms-of-use/"
def nth_business_day(year,month,n):
    d=date(year,month,1)
    count=0
    while d.month==month:
        if d.weekday()<5:
            count+=1
            if count==n:return d
        d+=timedelta(days=1)
    raise ValueError("invalid business day")
def build(now):
    et=now.astimezone(ZoneInfo("America/New_York"))
    current=date(et.year,et.month,1)
    checks=[]
    for name,n in [("ISM_MANUFACTURING",1),("ISM_SERVICES",3)]:
        release=nth_business_day(et.year,et.month,n)
        # Calendar is an approximate weekday schedule; holidays may shift it.
        checks.append({"series_id":name,"scheduled_release_date_et":release.isoformat(),"release_time_et":"10:00","release_calendar_is_approximate":True,"numeric_value":None,"numeric_status":"not_collected_due_to_licensing","human_review_required":True,"official_calendar_url":SOURCE})
    return {"schema_version":1,"checked_at_utc":now.astimezone(timezone.utc).isoformat(),"month_et":current.isoformat(),"status":"metadata_only","releases":checks,"source_url":SOURCE,"terms_url":TERMS,"limitations":["This file confirms expected calendar only, not that a report was published or manually checked","ISM report text and PMI numerical data are not scraped, copied or republished","Actual release date must be verified against official ISM calendar; weekday approximation ignores holidays"]}
def main():
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(build(datetime.now(timezone.utc)),indent=2)+"\n")
    print("ISM release-check metadata saved (no PMI values)")
if __name__=="__main__":main()
