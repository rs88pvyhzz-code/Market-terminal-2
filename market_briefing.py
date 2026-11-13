"""Dated headline intelligence. Ranking is editorial triage, never a recommendation."""
import datetime as dt
import hashlib
import json
import math
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

CATEGORIES = {'market_moving':'Market Moving','rates':'Central Banks & Rates','economic':'Economic Releases','corporate':'Corporate','watchlist':'My Watchlist','policy':'Regulation & Policy'}
RULES = [('rates',r'\b(federal reserve|fed|bank of england|ecb|interest rates?|monetary policy|bond yields?)\b',45),('economic',r'\b(inflation|cpi|payrolls|employment|gdp|unemployment)\b',40),('corporate',r'\b(earnings|results|profit warning|acquisition|buyback|dividend|merger|(?:profit|earnings|revenue|sales|cash|margin|financial)\s+guidance)\b',35),('policy',r'\b(regulat\w*|tariffs?|legislation|sanctions|budget|tax reform)\b',30)]
THRESHOLDS=json.loads(Path(__file__).with_name('market_alert_thresholds.json').read_text())

def timestamp(value):
    try:parsed=dt.datetime.fromisoformat(str(value).replace(' UTC','+00:00').replace('Z','+00:00'));return (parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)).astimezone(dt.timezone.utc)
    except (ValueError,TypeError):return None

def headline_text(item):
    """Remove RSS publisher/edition metadata before geography or event matching."""
    title=item.get('title','').lower()
    if not item.get('official') and ' - ' in title:
        headline,suffix=title.rsplit(' - ',1)
        if suffix==str(item.get('source','')).lower() or not re.search(r'\d|\b(cuts?|hikes?|rates?|inflation|earnings|guidance|gdp|cpi)\b',suffix):title=headline
    return re.sub(r'\s*--?\s*\d+(?:st|nd|rd|th)\s+update\b.*$','',title)

def significance_evidence(item, text):
    """Conservative headline evidence, independent of topic/relevance weights.

    A headline is a publisher claim, not independently verified event causation.
    Unknown materiality is deliberately insufficient for Market Moving.
    """
    preview = re.search(r"\b(preview|commentary|analysis|opinion|interview|calendar|recap|odds|what to expect|could|might|may|expected to|forecast to|set to|poised to|to discuss|last week|last month|last year|await\w*)\b", text)
    if preview or '?' in text:
        return []
    evidence = []
    # Quantified *reported* moves only: expressive words such as 'rally' are insufficient.
    asset = r"(?:shares?|stocks?|equities|index|indices|ftse|s&p|nasdaq|dow|nikkei|oil|brent|gold|sterling|pound|dollar|euro|yen|vix)"
    movement = r"(?:rises?|rose|rising|falls?|fell|falling|jumps?|jumped|surges?|surged|plunges?|plunged|gains?|gained|drops?|dropped|rallies|rallied|slides?|slid|tumbles?|tumbled|soars?|soared|up|down)"
    move = re.search(r'\b'+asset+r'\b.{0,45}?\b'+movement+r'\b\s+(?:by\s+|more than\s+|over\s+|nearly\s+)?([0-9]+(?:\.[0-9]+)?)\s*(?:%|percent\b|per cent\b)', text)
    if move and float(move[1]) >= THRESHOLDS['priceMovePct'] and not re.search(r'\b(nearly|almost|up to)\b', move[0]):
        evidence.append(f"Publisher reports a {move[1]}% asset move; significance threshold {THRESHOLDS['priceMovePct']:g}% (no causal attribution)")
    yield_move = re.search(r'\byields?\b.{0,35}?\b'+movement+r'\b\s+(?:by\s+)?([0-9]+(?:\.[0-9]+)?)\s*(?:basis points?|bps?)\b', text)
    if yield_move and float(yield_move[1]) >= THRESHOLDS['yieldMoveBp']:
        evidence.append(f"Publisher reports a {yield_move[1]} bp yield move; significance threshold {THRESHOLDS['yieldMoveBp']:g} bp")
    # 'Ahead of a decision' is not the decision; an actual quantified move above
    # can still be material even when it precedes a scheduled announcement.
    anticipation = re.search(r'\b(ahead of|before|will|next week|next meeting|due to announce|expected|forecast)\b', text)
    if not anticipation:
        bank = r'(?:federal reserve|fed|bank of england|ecb|bank rate)'
        decision = r'(?:cuts?|raises?|hikes?|holds?|increased|reduced|leaves?\b.{0,20}\bunchanged|keeps?\b.{0,20}\bunchanged)'
        if re.search(r'\b'+bank+r'\b\s+(?:(?:has|unexpectedly|unanimously|again|is|was)\s+|(?:interest|policy)\s+rates?\s+)?'+decision+r'\b',text) and re.search(r'\b(rate|rates|monetary policy)\b',text):
            evidence.append('Reported central-bank rate decision, not a preview or rate commentary')
        elif item.get('official') and item.get('source') in ('Federal Reserve','Bank of England','ECB') and re.search(r'\b(fomc statement|monetary policy (?:decision|statement|summary))\b',text):
            evidence.append('Identified official central-bank monetary-policy decision document')
        if re.search(r'\b(issues?|issued|delivers?|warns?|warned)\b.{0,30}\bprofit warning\b|\bprofit warning\b.{0,30}\b(issued|announced)\b',text):
            evidence.append('Explicit reported profit-warning announcement')
        if not re.search(r'\b(analysts?|brokers?|price target|consensus)\b',text) and re.search(r'\b(cuts?|lowers?|lowered|slashes?|raises?|raised|upgrades?|downgrades?|withdraws?|withdrawn)\b.{0,35}\b(?:(?:profit|earnings|revenue|sales|cash|margin|annual|full-year)\s+){0,3}guidance\b',text):
            evidence.append('Explicit reported issuer guidance revision; no consensus surprise inferred')
        # Leadership change: a reported departure of a chief executive or chair. Rumour,
        # speculation and 'could/may' wording are already excluded above.
        if re.search(r'\b(ceo|chief executive|chairman|chairwoman|chair)\b.{0,60}\b(steps? down|stepping down|resigns?|resigned|resignation|ousted|fired|quits?|departs?|departure|exits?|to leave|leaves)\b',text) or re.search(r'\b(steps? down|resigns?|resigned|ousted|quits?)\b.{0,30}\b(as )?(ceo|chief executive|chairman|chair)\b',text):
            if not re.search(r'\b(talks|rumou?r|considers?|considering|mulls?|reportedly weighing)\b',text):
                evidence.append('Reported chief-executive or chair departure (leadership change); no price causation inferred')
        # No claim that every acquisition/buyback is material: require a confirmed
        # transaction and a stated >=1 billion headline value; currency is not converted.
        transaction = re.search(r'\b(agrees?|agreed|announces?|announced|completes?|completed|signs?|signed)\b.{0,70}\b(acquisition|merger|takeover|buyout|buyback|acquire|buy)\b',text)
        amount = re.search(r'(?:[$£€]|usd\s*|gbp\s*|eur\s*)([0-9]+(?:\.[0-9]+)?)\s*(billion|bn|b)\b',text)
        if transaction and amount and float(amount[1]) >= 1 and not re.search(r'\b(talks|rumou?r|considers?|considering|mulls?)\b',text):
            evidence.append('Reported confirmed transaction with stated value >=1 billion in stated headline currency units ($/£/€/USD/GBP/EUR); nominal threshold, no FX estimate')
    return evidence


def development_status(item, text):
    """Evidence tier, not an investment significance/reliability rating."""
    preview=bool(re.search(r"\b(preview|commentary|opinion|interview|calendar|recap|odds|ahead of|what to expect|could|might|may|expected to|forecast to|set to|poised to|to discuss|await\w*|investors (?:are )?watching|stocks to (?:buy|watch)|heads into)\b",text) or '?' in text)
    event=bool(re.search(r'\b(reports?|reported|releases?|released|announces?|announced|issues?|issued|publishes?|published)\b.{0,65}\b(earnings|results|inflation|cpi|gdp|employment|payrolls|profit warning|guidance)\b',text) or significance_evidence(item,text))
    if preview:return 'commentary_preview'
    if event:return 'confirmed_event' if item.get('official') else 'reported_development'
    return 'general_news'


def publisher_tier(item):
    if item.get('official'):return 0
    known={'reuters','associated press','ap news','bbc','bbc news','bbc business','cnbc','financial times','ft','bloomberg','wall street journal','the wall street journal','wsj','yahoo finance','yahoo finance uk','the guardian','the economist'}
    return 1 if str(item.get('source','')).strip().lower() in known else 2


def news_order(item):
    tier={'confirmed_event':0,'reported_development':1,'general_news':2,'commentary_preview':3}.get(item.get('developmentStatus'),2)
    return (item['archived'],tier,'market_moving' not in item['categories'],publisher_tier(item),-(timestamp(item.get('published')).timestamp() if timestamp(item.get('published')) else 0),-item['rank'])


def classify(item, now, watch_names=()):
    item=dict(item); text=headline_text(item); cats=[]; reasons=[];score=0
    for key,pattern,weight in RULES:
        if re.search(pattern,text):cats.append(key);score+=weight;reasons.append(f'{CATEGORIES[key]} (+{weight})')
    if any(n and re.search(r'\b'+re.escape(n.lower())+r'\b',text) for n in watch_names):cats.append('watchlist');score+=25;reasons.append('Watchlist match (+25)')
    if re.search(r'\b(oil|gold|currency|stocks|markets?|vix|sterling|dollar)\b',text):score+=20;reasons.append('Market/commodity relevance (+20)')
    if item.get('official'):score+=5;reasons.append('Primary source (+5)')
    if re.search(r'\b(oil|gold|currency|stocks|markets?|vix|sterling|dollar|yields?)\b',text) and re.search(r'\b(surge|slump|rally|rout|plunge|jump|rebound|record|tumble|spike|soar)\w*\b',text):score+=20;reasons.append('Movement wording (+20); not significance evidence')
    evidence=significance_evidence(item,text)
    if evidence:cats.insert(0,'market_moving')
    reasons=['Topic/relevance: '+reason for reason in reasons]+['Significance: '+reason for reason in evidence]
    if not cats:cats=['corporate']
    # An identified official central-bank feed establishes jurisdiction; a
    # commercial publisher's country suffix does not establish story geography.
    official_region={'Federal Reserve':'US','Bank of England':'UK','ECB':'Europe'}.get(item.get('source')) if item.get('official') else None
    if official_region and 'rates' not in cats:cats.append('rates')
    regions=[official_region] if official_region else []
    for label,pattern in [('UK',r'\b(uk|u\.k|britain|british|england|scotland|sterling|bank of england|ftse)\b'),('US',r'\b(us|u\.s|united states|fed|federal reserve|wall street|nasdaq|s&p)\b'),('Europe',r'\b(europe|european|euro|eurozone|ecb|german|germany|france|french|italy|spain|eu|e\.u)\b')]:
        if re.search(pattern,text) and label not in regions:regions.append(label)
    published=timestamp(item.get('published'));age=(now-published).total_seconds()/3600 if published else None
    archived=bool(item.get('restored') or item.get('archived') or age is None or age>THRESHOLDS['maxNewsAgeHours'] or age<-.1 or not item.get('retrievedAt'))
    if age is not None and 0<=age<24:reasons.append('Published within 24 hours (+10)')
    item.update(categories=list(dict.fromkeys(cats)),regions=regions or ['Global'],rank=score+(10 if age is not None and 0<=age<24 else 0),rankReasons=reasons,developmentStatus=development_status(item,text),significanceEvidence=evidence,archived=archived)
    return item

def deduplicate(items):
    """Conservative headline event grouping; keep differing numbers/directions separate."""
    result=[]
    for item in sorted(items,key=news_order):
        title=headline_text(item)
        normal=title.replace('federal reserve','fed').replace('bank of england','boe').replace('consumer price index','cpi').replace('lowers rates','cuts rates').replace('raises rates','hikes rates')
        tokens=set(re.findall(r'[a-z0-9]+',normal)) - {'the','a','an','in','of','to','and','for','on','as','with','after','says'}
        numbers=set(re.findall(r'\d+(?:\.\d+)?',title));directions=set()
        for direction,pattern in [('up',r'\b(rises?|rising|raises?|hikes?|increases?)\b'),('down',r'\b(falls?|falling|cuts?|lowers?|decreases?)\b'),('flat',r'\b(holds?|unchanged)\b')]:
            if re.search(pattern,normal):directions.add(direction)
        match=None
        for other in result:
            same_url=item['url']==other['url']
            overlap=len(tokens & other['_tokens'])/max(1,len(tokens | other['_tokens']))
            same_day=item.get('published','')[:10]==other.get('published','')[:10]
            if same_url or (same_day and numbers==other['_numbers'] and directions==other['_directions'] and overlap>=.72):match=other;break
        if match:
            match['categories']=list(dict.fromkeys(match['categories']+[c for c in item['categories'] if c!='market_moving' or match.get('significanceEvidence')]))
            if item['url']!=match['url'] and not any(x['url']==item['url'] for x in match['coverage']):
                match['coverage'].append({k:item.get(k) for k in ['title','url','source','published','retrievedAt','archived']})
        else:
            item.update(id=hashlib.sha256((title+item.get('published','')[:10]).encode()).hexdigest()[:16],coverage=[],_tokens=tokens,_numbers=numbers,_directions=directions);result.append(item)
    for item in result:item.pop('_tokens');item.pop('_numbers');item.pop('_directions')
    return sorted(result,key=news_order)

def enrich(payload):
    now=timestamp(payload.get('generatedAt')) or dt.datetime.now(dt.timezone.utc)
    names=[re.sub(r'\b(plc|inc|corporation|corp|limited|ltd|holdings|ag|se)\b.*','',r.get('name',''),flags=re.I).strip() for r in payload.get('personalWatchlist',[]) if isinstance(r,dict)]
    items=list(payload.get('news',[]))
    for group in payload.get('watchlist_news',[]) or []:
        if isinstance(group,dict):
            for item in group.get('articles',[]):items.append(dict(item))
    payload['news']=deduplicate([classify(x,now,names) for x in items if x.get('title') and str(x.get('url','')).startswith('https://')])
    alerts=[]; moves=[]
    metrics={x['symbol']:x for x in payload.get('marketHistoryMetrics',[]) if x.get('symbol')}
    missing={q['symbol'] for q in payload.get('quotes',[]) if q.get('symbol') not in metrics}
    records={symbol:{'points':[],'asOf':payload.get('generatedAt')} for symbol in missing}
    for row in payload.get('history',[]):
        if row.get('symbol') in records:records[row['symbol']]['points'].append([row['date'],row['close']])
    from market_price_history import metrics_for_records
    metrics.update({m['symbol']:m for m in metrics_for_records(records)})
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
                alerts.append({'title':f"VIX: {change:+.2f}%",'detail':f"Observed rise {q['price']-previous:.2f} points; thresholds {THRESHOLDS['vixRisePct']}% and {THRESHOLDS['vixRisePoints']} points.",'date':date,'kind':'Calculated','source':'Yahoo Finance','assetClass':'Volatility','severity':min(change/THRESHOLDS['vixRisePct'],(q['price']-previous)/THRESHOLDS['vixRisePoints'])})
        elif abs(change)>=THRESHOLDS['priceMovePct'] and sigma is not None and sigma>=THRESHOLDS['volatilitySigma']:
            alerts.append({'title':f"{q.get('name') or q.get('symbol')}: {change:+.2f}%",'detail':f"{sigma:.1f} × daily volatility (existing 1Y annualised volatility / √252); thresholds {THRESHOLDS['volatilitySigma']}× and {THRESHOLDS['priceMovePct']}%. Intraday moves are provisional.",'date':date,'kind':'Calculated','source':'Yahoo Finance; existing market-history metrics','assetClass':'FX' if q.get('kind')=='fx' else 'Commodities' if q.get('kind')=='future' else 'Equities','severity':min(abs(change)/THRESHOLDS['priceMovePct'],sigma/THRESHOLDS['volatilitySigma'])})
    for credit in payload.get('credit_spreads',[]):
        rows=sorted([x for x in credit.get('history',[]) if isinstance(x.get('bp'),(int,float)) and timestamp(x.get('date'))],key=lambda x:x['date'])
        if len(rows)>=2:
            a,b=rows[-2:]; age=(now-timestamp(b['date'])).days; gap=(timestamp(b['date'])-timestamp(a['date'])).days;delta=b['bp']-a['bp']
            if 0<=age<=THRESHOLDS['criticalMaxAgeDays'] and 0<gap<=7 and abs(delta)>=THRESHOLDS['creditMoveBp']:
                alerts.append({'title':f"{credit['name']}: {delta:+.0f} bp",'detail':f"Option-adjusted spread, {a['date']} → {b['date']}; threshold {THRESHOLDS['creditMoveBp']} bp.",'date':b['date'],'kind':'Calculated','url':credit.get('sourceUrl'),'source':'FRED / ICE BofA','assetClass':'Credit','severity':abs(delta)/THRESHOLDS['creditMoveBp']})
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
                if abs(delta)>=THRESHOLDS['yieldMoveBp']:alerts.append({'title':f'{label}: {delta:+.0f} bp','detail':f"{a['date']} → {b['date']}; threshold {THRESHOLDS['yieldMoveBp']:g} bp",'date':b['date'],'kind':'Calculated','source':{'uk_rates':'Bank of England','us_rates':'FRED / US Treasury','eu_rates':'ECB'}[series],'assetClass':'Bonds','severity':abs(delta)/THRESHOLDS['yieldMoveBp']})
    today=now.date().isoformat()
    for event in payload.get('calendar',[]):
        if event.get('date')==today and any(word in event.get('title','').lower() for word in ['inflation','gdp','gross domestic','employment','monetary','interest','cpi','consumer price','producer price','payroll']):
            alerts.append({'title':event['title'],'url':event.get('url'),'date':event['date'],'detail':'Scheduled economic release; no outcome or surprise inferred. See Economics for official calendar.','kind':'Scheduled'})
    fresh=[x for x in payload['news'] if not x['archived']]
    for item in fresh:
        text=item['title'].lower()
        preview=bool(re.search(r'\b(ahead of|expected to|forecast to|outlook|preview|odds|calendar|recap)\b',text))
        announcement=bool(re.search(r'\b(earnings|profit warning|acquisition|acquires|buybacks?|merger)\b',text) or re.search(r'\b(profit|revenue|sales|cash|margin|management|capital)\b.{0,60}\bguidance\b|\bguidance\b.{0,60}\b(cut|raised|lowered|upgraded|downgraded)\b',text))
        official_decision=bool(item.get('official') and re.search(r'\b(decision|statement|announces?|announced)\b',text))
        reported_release=bool(re.search(r'\b(inflation|cpi|payrolls|gdp|employment)\b.{0,70}\b(rises?|falls?|released|reported|accelerates?|slows?)\b',text))
        if not preview and (announcement or official_decision or reported_release):
            alerts.append({'title':item['title'],'url':item['url'],'date':item['published'],'detail':'Sourced announcement headline: research prompt, not a verified earnings surprise.','kind':'Reported'})
        if len(alerts)>=THRESHOLDS['maxAlerts']:break
    if payload.get('giltFreshness',{}).get('stale'):alerts.insert(0,{'title':'DMO quotations require a freshness review','detail':'See Bonds & Rates for verified quotation date and recovery diagnostics.','date':payload['giltFreshness'].get('quotationDate'),'kind':'Coverage'})
    payload['marketBriefing']={'thresholds':THRESHOLDS,'alerts':alerts[:THRESHOLDS['maxAlerts']],'movements':sorted(moves,key=lambda q:abs(q['changePct']),reverse=True)[:8],'currentCount':len(fresh),'archivedCount':len(payload['news'])-len(fresh),'generatedAt':payload.get('generatedAt'),'watchMovements':[q for q in moves if q['watchlist'] and abs(q['changePct'])>=THRESHOLDS['priceMovePct']],'limitations':['Headline relevance uses transparent keyword rules, not investment ratings.','Volatility alerts use existing 1Y historical metrics; missing or discontinuous histories are excluded. Credit alerts require dated FRED / ICE BofA observations.','RSS does not reliably provide earnings consensus or changes in guidance. Issuer evidence remains in Company Research.']}
    assemble_daily_briefing(payload,alerts,now)
    return payload


def assemble_daily_briefing(payload, alerts, now):
    """Reuse the engine's calculated observations, never infer news causation."""
    unique={}
    for alert in alerts:
        key=hashlib.sha256((alert['kind']+str(alert.get('date'))+alert['title']).encode()).hexdigest()[:16]
        alert['id']=key
        unique.setdefault(key,alert)
    observations=sorted([a for a in unique.values() if a['kind']=='Calculated'],key=lambda a:-a.get('severity',0))
    # Broad coverage when multiple asset classes actually cross existing thresholds.
    first=[];rest=[];classes=set()
    for alert in observations:
        group=alert.get('assetClass','Other')
        (rest if group in classes else first).append(alert);classes.add(group)
    candidates=[]
    for alert in first+rest:
        candidates.append({'id':alert['id'],'alertId':alert['id'],'title':alert['title'],'published':alert['date'],'source':alert.get('source'),'url':alert.get('url'),'classification':'observed_market_movement','marketMoving':True,'selectionReasons':[alert['detail'],'Existing alert threshold crossed; no event-to-price cause inferred'],'assetClass':alert.get('assetClass')})
    for story in payload['news']:
        if story['archived']:continue
        status=story['developmentStatus']
        candidates.append({'id':story['id'],'newsId':story['id'],'title':story['title'],'url':story['url'],'published':story['published'],'retrievedAt':story.get('retrievedAt'),'source':story['source'],'classification':'confirmed_event' if status=='confirmed_event' else 'general_news','marketMoving':bool(status=='confirmed_event' and story.get('significanceEvidence')),'selectionReasons':[{'confirmed_event':'Primary-source release/decision with explicit event evidence','reported_development':'Reported development; primary confirmation not available','general_news':'General news; no verified significant event established','commentary_preview':'Preview/opinion/speculation; below confirmed developments'}[status], 'Primary source' if publisher_tier(story)==0 else 'Identified established publisher (preference only, not significance evidence)' if publisher_tier(story)==1 else 'Other attributed publisher',*story.get('significanceEvidence',[])],'tier':{'confirmed_event':0,'reported_development':1,'general_news':2,'commentary_preview':3}[status]})
    # Fresh dated issuer results already in the research cache are primary evidence.
    for company in payload.get('companies',[]):
        for source in company.get('intelligence',{}).get('sources',[]):
            date=timestamp(source.get('published'));retrieved=timestamp(source.get('retrievedAt'))
            if source.get('kind')!='results' or not date or not retrieved or not 0<=(now-date).total_seconds()<=THRESHOLDS['maxNewsAgeHours']*3600 or not str(source.get('url','')).startswith('https://'):continue
            if any(x.get('url')==source['url'] for x in candidates):continue
            candidates.append({'id':source['id'],'title':company['name']+' — results document: '+(source.get('title') or source.get('form') or 'Results'),'url':source['url'],'published':source['published'],'retrievedAt':source['retrievedAt'],'source':company['name']+' issuer filing','classification':'confirmed_event','marketMoving':False,'selectionReasons':['Dated issuer results document in existing verified research cache; not an earnings surprise or investment significance claim'],'tier':0})
    # Observed threshold breaches and confirmed primary events lead; commentary is last.
    candidates.sort(key=lambda x:-1 if x['classification']=='observed_market_movement' else x.get('tier',0))
    leading=candidates[:5]
    for item in leading:
        if item.get('alertId'):continue
        reported=next((a for a in unique.values() if a['kind']=='Reported' and a.get('url') and a.get('url')==item.get('url')),None)
        if reported:item['alertId']=reported['id']
    payload['marketBriefing']['leadingItems']=leading
    payload['marketBriefing']['verifiedSignificantCount']=sum(x['marketMoving'] for x in candidates)
    selected=[unique[x['alertId']] for x in leading if x.get('alertId')]
    selected_ids={a['id'] for a in selected}
    selected.extend(a for a in unique.values() if a['id'] not in selected_ids)
    payload['marketBriefing']['alerts']=selected[:THRESHOLDS['maxAlerts']]
    payload['marketBriefing']['briefingMethod']='Existing observed alert breaches first (asset-class coverage, then threshold exceedance), confirmed primary events, reported developments, general news, previews/opinion last. Source preference never grants significance.'
