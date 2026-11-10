"""Source freshness only; does not change settlement or valuation calculations."""
import datetime as dt
import json
from pathlib import Path
import urllib.request
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
URL='https://www.gov.uk/bank-holidays.json'

def load_calendar(offline=False):
    path=ROOT/'.terminal_sources/uk_bank_holidays.json'
    seed=ROOT/'uk_bank_holidays.json'
    cached=None
    for f in [path,seed]:
        try:
            data=json.loads(f.read_text())
            if not cached or data['retrievedAt']>cached['retrievedAt']:cached=data
        except (OSError,ValueError,KeyError):pass
    now=dt.datetime.now(dt.timezone.utc)
    if not offline and (not cached or (now-dt.datetime.fromisoformat(cached['retrievedAt'])).total_seconds()>86400):
        try:
            with urllib.request.urlopen(urllib.request.Request(URL,headers={'User-Agent':'MarketTerminal/2.2'}),timeout=12) as r:data=json.loads(r.read(300000))
            dates=[e['date'] for e in data['england-and-wales']['events']]
            if len(dates)<10:raise ValueError('Incomplete official calendar')
            cached={'holidays':dates,'retrievedAt':now.isoformat(timespec='seconds'),'source':URL}
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(cached))
        except Exception:pass
    if not cached:raise ValueError('Official UK holiday calendar unavailable')
    return cached

def assess(quotation,now=None,calendar=None):
    calendar=calendar or load_calendar(offline=True)
    now=now or dt.datetime.now(dt.timezone.utc)
    local=now.astimezone(ZoneInfo('Europe/London'));day=local.date()
    # DMO says approximately 14:00. Allow a transparent 30-minute publication grace.
    if local.time()<dt.time(14,30):day-=dt.timedelta(days=1)
    while day.weekday()>=5 or day.isoformat() in calendar['holidays']:day-=dt.timedelta(days=1)
    years={int(d[:4]) for d in calendar['holidays']}
    covered=day.year in years
    return {'quotationDate':quotation,'checkedAt':now.isoformat(timespec='seconds'),'expectedQuotationDate':day.isoformat(),
            'stale':not covered or not quotation or quotation<day.isoformat(),'calendarCovered':covered,'calendarSource':calendar['source'],
            'publicationRule':'UK business days, approximately 14:00 London time; warning cutoff 14:30'}
