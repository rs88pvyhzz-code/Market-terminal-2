"""Dated headline intelligence. Ranking is editorial triage, never a recommendation."""
import datetime as dt
import hashlib
import json
import math
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

CATEGORIES = {'market_moving':'Market Moving','rates':'Central Banks & Rates','economic':'Economic Releases','corporate':'Corporate','watchlist':'My Watchlist','policy':'Regulation & Policy'}
RULES = [('rates',r'\b(federal reserve|fed|bank of england|ecb|interest rates?|monetary policy|bond yields?)\b',45),('economic',r'\b(inflation|cpi|payrolls|employment|gdp|unemployment)\b',40),('corporate',r'\b(earnings|results|guidance|profit warning|acquisition|buyback|dividend|merger)\b',35),('policy',r'\b(regulat\w*|tariffs?|legislation|sanctions|budget|tax reform)\b',30)]
THRESHOLDS=json.loads(Path(__file__).with_name('market_alert_thresholds.json').read_text())

def timestamp(value):
    try:parsed=dt.datetime.fromisoformat(str(value).replace(' UTC','+00:00').replace('Z','+00:00'));return (parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)).astimezone(dt.timezone.utc)
    except (ValueError,TypeError):return None

def classify(item, now, watch_names=()):
    item=dict(item); text=item.get('title','').lower(); cats=list(item.get('categories',[])); reasons=[];score=0
    for key,pattern,weight in RULES:
        if re.search(pattern,text):cats.append(key);score+=weight;reasons.append(CATEGORIES[key])
    if any(n and re.search(r'\b'+re.escape(n.lower())+r'\b',text) for n in watch_names):cats.append('watchlist');score+=25;reasons.append('Watchlist match')
    if re.search(r'\b(oil|gold|currency|stocks|markets?|vix|sterling|dollar)\b',text):score+=20
    if item.get('official'):score+=5;reasons.append('Primary source')
    if re.search(r'\b(oil|gold|currency|stocks|markets?|vix|sterling|dollar|yields?)\b',text) and re.search(r'\b(surge|slump|rally|rout|plunge|jump|rebound|record|tumble|spike|soar)\w*\b',text):score+=20;reasons.append('Reported sharp market movement')
    if score>=35:cats.insert(0,'market_moving')
    if not cats:cats=['corporate']
    regions=[]
    for label,pattern in [('UK',r'\b(uk|britain|british|sterling|bank of england|ftse)\b'),('US',r'\b(us|u\.s\.|fed|federal reserve|wall street|nasdaq|s&p)\b'),('Europe',r'\b(europe|european|euro|ecb|german|france)\b')]:
        if re.search(pattern,text):regions.append(label)
    published=timestamp(item.get('published'));age=(now-published).total_seconds()/3600 if published else None
    archived=bool(item.get('restored') or item.get('archived') or age is None or age>THRESHOLDS['maxNewsAgeHours'] or age<-.1 or not item.get('retrievedAt'))
    item.update(categories=list(dict.fromkeys(cats)),regions=regions or ['Global'],rank=score+(10 if age is not None and 0<=age<24 else 0),rankReasons=reasons,archived=archived)
    return item

def deduplicate(items):
    """Conservative headline event grouping; keep differing numbers/directions separate."""
    result=[]
    for item in sorted(items,key=lambda x:(x['archived'],-x['rank'],x.get('published','')),reverse=False):
        title=item['title'].lower()
        # RSS search appends publisher names (which may themselves contain hyphens).
        # Edition numbers are metadata, not conflicting economic numerical claims.
        if not item.get('official') and ' - ' in title:
            headline,suffix=title.rsplit(' - ',1)
            if suffix==str(item.get('source','')).lower() or not re.search(r'\d|\b(cuts?|hikes?|rates?|inflation|earnings|guidance|gdp|cpi)\b',suffix):title=headline
        title=re.sub(r'\s*--?\s*\d+(?:st|nd|rd|th)\s+update\b.*$','',title)
        normal=title.replace('federal reserve','fed').replace('bank of england','boe').replace('consumer price index','cpi').replace('lowers rates','cuts rates').replace('raises rates','hikes rates')
        tokens=set(re.findall(r'[a-z0-9]+',normal)) - {'the','a','an','in','of','to','and','for','on','as','with','after','says'}
        numbers=set(re.findall(r'\d+(?:\.\d+)?',title));match=None
        for other in result:
            same_url=item['url']==other['url']
            overlap=len(tokens & other['_tokens'])/max(1,len(tokens | other['_tokens']))
            same_day=item.get('published','')[:10]==other.get('published','')[:10]
            if same_url or (same_day and numbers==other['_numbers'] and overlap>=.72):match=other;break
        if match:
            match['categories']=list(dict.fromkeys(match['categories']+item['categories']))
            match['coverage'].append({k:item.get(k) for k in ['title','url','source','published','retrievedAt','archived']})
        else:
            item.update(id=hashlib.sha256((title+item.get('published','')[:10]).encode()).hexdigest()[:16],coverage=[],_tokens=tokens,_numbers=numbers);result.append(item)
    for item in result:item.pop('_tokens');item.pop('_numbers')
    return sorted(result,key=lambda x:(x['archived'],-x['rank'], -(timestamp(x.get('published')).timestamp() if timestamp(x.get('published')) else 0)))

def enrich(payload):
    now=timestamp(payload.get('generatedAt')) or dt.datetime.now(dt.timezone.utc)
    names=[re.sub(r'\b(plc|inc|corporation|corp|limited|ltd|holdings|ag|se)\b.*','',r.get('name',''),flags=re.I).strip() for r in payload.get('personalWatchlist',[]) if isinstance(r,dict)]
    items=list(payload.get('news',[]))
    for group in payload.get('watchlist_news',[]) or []:
        if isinstance(group,dict):
            for item in group.get('articles',[]):items.append({**item,'categories':['watchlist']})
    payload['news']=deduplicate([classify(x,now,names) for x in items if x.get('title') and str(x.get('url','')).startswith('https://')])
    alerts=[]; moves=[]
    metrics={x['symbol']:x for x in payload.get('marketHistoryMetrics',[]) if x.get('symbol')}
    watch_symbols={x.get('symbol') for x in payload.get('personalWatchlist',[]) if isinstance(x,dict)}
    quotes={x['symbol']:x for x in payload.get('quotes',[])+payload.get('watchlist_quotes',[]) if x.get('symbol')}
    for market in payload.get('movers',[]):
        for q in market.get('gainers',[])+market.get('losers',[]):quotes.setdefault(q['symbol'],q)
    for q in quotes.values():
        change=q.get('changePct');date=q.get('asOf') or q.get('date'); parsed=timestamp(date)
        if not isinstance(change,(int,float)) or not parsed or abs((now-parsed).total_seconds())>4*86400:continue
        moves.append({**{k:q.get(k) for k in ['symbol','name','changePct','asOf','price','currency']},'watchlist':q.get('symbol') in watch_symbols})
        metric=metrics.get(q.get('symbol'),{});vol=metric.get('volatility1YPct')
        valid_vol=(isinstance(vol,(int,float)) and vol>0 and not metric.get('priceDiscontinuityFlag') and metric.get('dailyCloses',0)>=200 and timestamp(metric.get('last')) and abs((parsed-timestamp(metric['last'])).days)<=5)
        sigma=abs(change)/(vol/math.sqrt(252)) if valid_vol else None
        if q.get('symbol')=='^VIX':
            previous=q['price']/(1+change/100) if q.get('price') and change>-100 else None
            if change>=THRESHOLDS['vixRisePct'] and previous and q['price']-previous>=THRESHOLDS['vixRisePoints']:
                alerts.append({'title':f"VIX: {change:+.2f}%",'detail':f"Observed rise {q['price']-previous:.2f} points; thresholds {THRESHOLDS['vixRisePct']}% and {THRESHOLDS['vixRisePoints']} points.",'date':date,'kind':'Calculated','source':'Yahoo Finance'})
        elif abs(change)>=THRESHOLDS['priceMovePct'] and sigma is not None and sigma>=THRESHOLDS['volatilitySigma']:
            alerts.append({'title':f"{q.get('name') or q.get('symbol')}: {change:+.2f}%",'detail':f"{sigma:.1f} × daily volatility (existing 1Y annualised volatility / √252); thresholds {THRESHOLDS['volatilitySigma']}× and {THRESHOLDS['priceMovePct']}%. Intraday moves are provisional.",'date':date,'kind':'Calculated','source':'Yahoo Finance; existing market-history metrics'})
    for credit in payload.get('credit_spreads',[]):
        rows=sorted([x for x in credit.get('history',[]) if isinstance(x.get('bp'),(int,float)) and timestamp(x.get('date'))],key=lambda x:x['date'])
        if len(rows)>=2:
            a,b=rows[-2:]; age=(now-timestamp(b['date'])).days; gap=(timestamp(b['date'])-timestamp(a['date'])).days;delta=b['bp']-a['bp']
            if 0<=age<=THRESHOLDS['criticalMaxAgeDays'] and 0<gap<=7 and abs(delta)>=THRESHOLDS['creditMoveBp']:
                alerts.append({'title':f"{credit['name']}: {delta:+.1f} bp",'detail':f"Option-adjusted spread, {a['date']} → {b['date']}; threshold {THRESHOLDS['creditMoveBp']} bp.",'date':b['date'],'kind':'Calculated','url':credit.get('sourceUrl'),'source':'FRED / ICE BofA'})
    critical=['^GSPC','^FTSE','^VIX','GBPUSD=X','BZ=F']
    unavailable=[]
    for symbol in critical:
        q=quotes.get(symbol,{});date=timestamp(q.get('asOf'))
        if q.get('price') is None or date is None or (now-date).days>THRESHOLDS['criticalMaxAgeDays']:unavailable.append(symbol)
    for series,key,label in [('uk_rates','gilt10y','UK10Y'),('us_rates','DGS10','US10Y')]:
        dates=[timestamp(x.get('date')) for x in payload.get(series,[]) if isinstance(x.get(key),(int,float)) and timestamp(x.get('date'))]
        if not dates or (now-max(dates)).days>THRESHOLDS['criticalMaxAgeDays']:unavailable.append(label)
    if unavailable:alerts.insert(0,{'title':'Critical quote coverage: '+', '.join(unavailable),'detail':'Missing or older than the configured calendar-day tolerance. See Data Quality.','date':payload.get('generatedAt'),'kind':'Coverage'})
    for series,key,label in [('uk_rates','gilt10y','UK 10Y'),('us_rates','DGS10','US 10Y'),('eu_rates','eur10y','Euro-area 10Y')]:
        rows=[x for x in payload.get(series,[]) if isinstance(x.get(key),(int,float)) and x.get('date')]; rows.sort(key=lambda x:x['date'])
        if len(rows)>1:
            a,b=rows[-2:]; date=timestamp(b['date']); prior=timestamp(a['date'])
            if date and prior and 0<=(now-date).days<=4 and 0<(date-prior).days<=7:
                delta=(b[key]-a[key])*100
                if abs(delta)>=THRESHOLDS['yieldMoveBp']:alerts.append({'title':f'{label}: {delta:+.1f} bp','detail':f"{a['date']} → {b['date']}; threshold {THRESHOLDS['yieldMoveBp']:g} bp",'date':b['date'],'kind':'Calculated'})
    today=now.date().isoformat()
    for event in payload.get('calendar',[]):
        if event.get('date')==today and any(word in event.get('title','').lower() for word in ['inflation','gdp','employment','monetary','interest','cpi','payroll']):
            alerts.append({'title':event['title'],'url':event.get('url'),'date':event['date'],'detail':'Scheduled economic release; no outcome or surprise inferred. See Economics for official calendar.','kind':'Scheduled'})
    fresh=[x for x in payload['news'] if not x['archived']]
    for item in fresh:
        if any(c in item['categories'] for c in ['rates','economic','corporate']):alerts.append({'title':item['title'],'url':item['url'],'date':item['published'],'detail':'Sourced headline: research prompt, not a verified earnings surprise.','kind':'Reported'})
        if len(alerts)>=THRESHOLDS['maxAlerts']:break
    if payload.get('giltFreshness',{}).get('stale'):alerts.insert(0,{'title':'DMO quotations require a freshness review','detail':'See Bonds & Rates for verified quotation date and recovery diagnostics.','date':payload['giltFreshness'].get('quotationDate'),'kind':'Coverage'})
    payload['marketBriefing']={'thresholds':THRESHOLDS,'alerts':alerts[:THRESHOLDS['maxAlerts']],'movements':sorted(moves,key=lambda q:abs(q['changePct']),reverse=True)[:8],'currentCount':len(fresh),'archivedCount':len(payload['news'])-len(fresh),'generatedAt':payload.get('generatedAt'),'watchMovements':[q for q in moves if q['watchlist'] and abs(q['changePct'])>=THRESHOLDS['priceMovePct']],'limitations':['Headline relevance uses transparent keyword rules, not investment ratings.','Volatility alerts use existing 1Y historical metrics; missing or discontinuous histories are excluded. Credit alerts require dated FRED / ICE BofA observations.','RSS does not reliably provide earnings consensus or changes in guidance. Issuer evidence remains in Company Research.']}
    return payload
