"""Release 2: bounded, dated public-source research, independent of financial maths.

Persist derived evidence in the published research cache. SEC issuer filings are
immutable source documents; retrieval failures never refresh old evidence dates.
Qualitative claims are issuer statements, never verified competitive advantages.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import urllib.request
from urllib.parse import urljoin, urlparse

import company_filings
import company_research
from research_documents import FilingHTML, SCHEMA, parse_document, compare_guidance, clean

CACHE_NAME='research_evidence_cache.json'
PRINCIPAL=('SHEL.L','MSFT','HSBA.L')
REFRESH_HOURS=24
RETRY_HOURS=6
# Source identifiers and document naming conventions, not company conclusions.
QUARTERLY_PATTERNS={
 'SHEL.L':r'(?:shellq[1-4]\d{4}6-k|shel-\d{8}_d\d)\.htm$',
 'HSBA.L':r'(?:livedocq[1-4]\d{4}earningsrelea|hsbc-\d{8})\.htm$',
}


def now_iso():return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')


def valid_source(url):
    p=urlparse(url)
    return p.scheme=='https' and p.hostname in ('www.sec.gov','data.sec.gov','shell.gcs-web.com','www.microsoft.com','www.hsbc.com','www.shell.com')


class PublicSources:
    def __init__(self,directory,offline=False):
        self.root=Path(directory);self.root.mkdir(parents=True,exist_ok=True);self.offline=offline
    def get(self,url):
        if not valid_source(url):raise ValueError('Source host is not an approved public issuer/regulator')
        key=hashlib.sha256(url.encode()).hexdigest();path=self.root/(key+'.json')
        cached=None
        try:cached=json.loads(path.read_text())
        except (OSError,ValueError):pass
        stamp=now_iso()
        immutable='/Archives/' in url
        if cached:
            age=(dt.datetime.fromisoformat(stamp)-dt.datetime.fromisoformat(cached['retrievedAt'])).total_seconds()
            if self.offline or immutable or age<REFRESH_HOURS*3600:return cached['body'],cached['retrievedAt']
        if self.offline:raise OSError('Document not in offline cache')
        import source_transport
        try:raw=source_transport.get(url,fields=['earnings','guidance','catalysts','competition','risks'])
        except Exception:
            if cached:
                self.warnings=getattr(self,'warnings',[])+['Refresh failed; retained source from '+cached['retrievedAt']+' · '+url]
                return cached['body'],cached['retrievedAt']
            raise
        body=raw.decode('utf-8')
        path.write_text(json.dumps({'body':body,'retrievedAt':stamp},separators=(',',':')))
        return body,stamp


def issuer_id(symbol,source):
    if symbol in company_filings.ISSUERS:return company_filings.ISSUERS[symbol][0]
    if symbol.endswith('.L'):return None
    data=json.loads(source.get('https://www.sec.gov/files/company_tickers.json')[0])
    match=next((r for r in data.values() if str(r.get('ticker','')).replace('.','-')==symbol),None)
    return str(match['cik_str']).zfill(10) if match else None


def discover_documents(symbol,cik,source,asof):
    body,_=source.get('https://data.sec.gov/submissions/CIK'+cik+'.json')
    filings=json.loads(body)['filings']['recent'];annual=[];results=[];interim=[]
    for i,form in enumerate(filings['form']):
        published=filings['filingDate'][i]
        if published>asof:continue
        name=filings['primaryDocument'][i]
        kind=None
        if form in ('10-K','20-F') and not annual:kind='annual'
        elif form=='8-K' and '2.02' in filings.get('items',['']*len(filings['form']))[i] and len(results)<2:kind='results'
        elif form=='6-K' and re.search(QUARTERLY_PATTERNS.get(symbol,r'(?!)'),name,re.I) and len(results)<2:kind='results'
        elif form=='10-Q' and not interim:kind='interim'
        if not kind:continue
        base=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{filings["accessionNumber"][i].replace("-","")}/'
        entry={'url':base+name,'published':published,'period':filings.get('reportDate',['']*len(filings['form']))[i] if form in ('10-K','10-Q','20-F') else None,'filingReportDate':filings.get('reportDate',['']*len(filings['form']))[i],
            'title':symbol+' '+form+' '+published,'kind':kind,'form':form}
        if kind=='results':
            cover,_=source.get(entry['url']);links=FilingHTML(cover).links
            exhibits=[(href,text) for href,text in links if re.search(r'(?:ex99[_-]?[12]|ex(?:hibit)?99[12]|exh_99[12]|quarterlyexhibit992)',href,re.I) or text.strip()=='99.2']
            if exhibits:
                # Prefer the interim financial report over a short regulatory cover.
                href,text=max(exhibits,key=lambda x:('quarterly' in x[0].lower() or (form=='6-K' and x[1].strip()=='99.2'),bool(re.search('press release|results|earnings',x[1],re.I))))
                entry.update(url=urljoin(base,href),title=(text[:140] or entry['title']))
            results.append(entry)
        elif kind=='annual':annual.append(entry)
        else:interim.append(entry)
        if annual and len(results)>=2 and (interim or form=='20-F'):break
    return annual+results+interim


def source_ref(doc):
    return {k:doc.get(k) for k in ('id','url','title','kind','form','period','published','retrievedAt','hash')}



def issuer_alternatives(c,source,docs,asof,warnings):
    """Use readable official IR pages; never turn an app shell into research."""
    symbol=c['symbol'];url=None
    if symbol=='MSFT':
        periods=[d.get('period') for d in docs if d.get('kind')=='results' and d.get('period')]
        if periods:
            period=max(periods);year=int(period[:4]);month=int(period[5:7]);fy=year+(month>6);q=((month-7)%12)//3+1
            url=f'https://www.microsoft.com/en-us/Investor/earnings/FY-{fy}-Q{q}/press-release-webcast'
    elif symbol=='HSBA.L':url='https://www.hsbc.com/investors/results-and-announcements'
    elif symbol=='SHEL.L':url='https://www.shell.com/investors/results-and-reporting/quarterly-results.html'
    if not url:return []
    try:
        body,retrieved=source.get(url)
        if symbol=='HSBA.L':
            links=FilingHTML(body).links
            paths=[href for href,text in links if re.search(r'\dQ 20\d\d quick read',text,re.I)]
            if not paths:raise ValueError('No dated readable issuer results link')
            url=urljoin(url,paths[0]);body,retrieved=source.get(url)
        # A real publication date in visible results prose or publisher metadata is required.
        matches=re.findall(r'(?:article:published_time|datePublished)["\']?\s*(?:content=|:)\s*["\'](20\d\d-\d\d-\d\d)',body,re.I)
        if not matches:
            text=' '.join(FilingHTML(body).blocks[:30]);m=re.search(r'([A-Z][a-z]+ \d{1,2}, 20\d\d)',text)
            if m:
                try:matches=[dt.datetime.strptime(m[1],'%B %d, %Y').date().isoformat()]
                except ValueError:pass
        if not matches:raise ValueError('No verifiable publication date/readable results text')
        published=matches[0]
        if published>asof:raise ValueError('Future issuer document')
        d=parse_document(body,{'url':url,'published':published,'period':None,'title':symbol+' official issuer results','kind':'results','form':'issuer IR','retrievedAt':retrieved},c.get('financialCurrency') or 'USD')
        if not d['guidance'] and not d['reportedResults'] and not d['topics']['catalysts']:raise ValueError('Readable page contains no substantive extracted research')
        return [d]
    except Exception as exc:
        warnings.append('Issuer alternative '+url+': '+str(exc)[:100]);return []


def parse_sources(c,source,previous=None,asof=None):
    """Extract current/prior results + annual sources, retaining successful cached docs."""
    asof=asof or dt.date.today().isoformat();previous=previous or {};warnings=[];docs=[];unparsed=[]
    cik=issuer_id(c['symbol'],source)
    if not cik:return {'documents':[],'warnings':['No verified primary-source issuer adapter for this listing. Provider description, news and financial calculations remain available.'],'checkedAt':now_iso(),'schema':SCHEMA}
    try:discovered=discover_documents(c['symbol'],cik,source,asof)
    except Exception as exc:
        discovered=[];warnings.append('SEC discovery failed: '+str(exc)[:140])
    saved={d['url']:d for d in previous.get('documents',[]) if d.get('schema')==SCHEMA}
    for meta in discovered[:4]:
        if not valid_source(meta['url']):continue
        if meta['url'] in saved:docs.append(saved[meta['url']]);continue
        try:
            html,retrieved=source.get(meta['url'])
            d=parse_document(html,{**meta,'retrievedAt':retrieved},c.get('financialCurrency') or 'USD')
            docs.append(d)
        except Exception as exc:
            warnings.append(meta['title']+': '+str(exc)[:140]);unparsed.append({**meta,'reason':str(exc)[:140]})
    docs.extend(issuer_alternatives(c,source,docs,asof,warnings))
    warnings.extend(getattr(source,'warnings',[])[-4:])
    if not docs and previous.get('documents'):docs=previous['documents'];warnings.append('Refresh failed; previous documents retained with original dates')
    current_urls={d['url'] for d in docs}
    docs += [d for d in previous.get('documents',[]) if d.get('url') not in current_urls and d.get('schema')==SCHEMA]
    docs=sorted(docs,key=lambda d:d['published'],reverse=True)[:8]
    return {'documents':docs,'unparsedSources':unparsed,'warnings':warnings,'checkedAt':now_iso(),'schema':SCHEMA}


def capital_allocation(c):
    # Read only. No change to Release 1 figures or definitions.
    rows=[]
    for r in (c.get('research') or {}).get('annual',[]):
        amount=lambda k:abs(r[k]) if company_research.number(r.get(k)) else None
        fcf=r.get('fcf');div=amount('dividendsPaid');buy=amount('buybacks')
        returns=div+buy if div is not None and buy is not None else None
        rows.append({'period':r['fiscalEnd'],'capex':amount('capex'),'acquisitions':r.get('netBusinessAcquisitions'),
            'acquisitionBasis':(r.get('provenance',{}).get('netBusinessAcquisitions',{}).get('basis') or 'Net business acquisitions/disposals, signed cash-flow contribution; not gross purchase consideration'),'dividends':div,'buybacks':buy,'fcf':fcf,'roic':r.get('roic'),
            'coverage':fcf/returns if company_research.number(fcf) and returns is not None and returns>0 else None,
            'sources':r.get('provenance',{})})
    return rows


def financial_warnings(c):
    data=c.get('research') or {};rows=data.get('annual') or [];r=rows[0] if rows else {};p=rows[1] if len(rows)>1 else {};fin=company_research.financial_sector(c)
    out=[]
    def add(key,title,value,status,rule,monitor):
        out.append({'key':key,'title':title,'value':value,'status':status,'rule':rule,'monitor':monitor,'period':r.get('fiscalEnd'),'kind':'calculated','sources':r.get('provenance',{})})
    cash=r.get('cashConversion');cash=None if fin else cash
    negative_ocf=not fin and company_research.number(r.get('operatingCashFlow')) and r['operatingCashFlow']<0
    add('cash','Cash conversion',cash,'flag' if negative_ocf else 'not_assessed' if not company_research.number(cash) else 'flag' if cash<.8 else 'watch' if cash<1 else 'within_rule','Flag negative OCF even if cash conversion is undefined. Otherwise OCF / positive shareholder profit: flag <0.8×; watch <1×. Corporate test excluded for financials.','Check working capital, cash taxes and earnings adjustments.')
    debt=r.get('totalDebt');cashbal=r.get('cash');profit=r.get('operatingProfit')
    lev=(debt-cashbal)/profit if not fin and all(company_research.number(x) for x in (debt,cashbal,profit)) and profit>0 else None
    debt_strain=not fin and all(company_research.number(x) for x in (debt,cashbal,profit)) and debt>cashbal and profit<=0
    add('debt','Net debt / operating profit',lev,'flag' if debt_strain else 'not_assessed' if lev is None else 'flag' if lev>4 else 'watch' if lev>2.5 else 'within_rule','Flag positive net debt with non-positive operating profit, or >4× leverage; watch >2.5×. Undefined ratios are not zero. Not a bank capital or liquidity test.','Inspect maturities, leases, financing costs and regulatory capital for banks.')
    dilution=r.get('growth',{}).get('sharesOutstanding')
    add('dilution','Annual share-count change',dilution,'not_assessed' if dilution is None else 'flag' if dilution>3 else 'watch' if dilution>1 else 'within_rule','Flag >3%; watch >1% growth. Acquisitions and share plans require context.','Reconcile issuances, buybacks, employee trusts and share classes.')
    margin=r.get('operatingMargin');old=p.get('operatingMargin')
    delta=margin-old if all(company_research.number(x) for x in (margin,old)) else None
    add('margin','Operating margin change',delta,'not_assessed' if delta is None else 'flag' if delta< -4 else 'watch' if delta< -2 else 'within_rule','Flag a fall >4pp; watch >2pp. Bank operating margins are not a sector quality measure.','Track pricing, mix, costs and bank-specific returns.');
    allocation=capital_allocation(c);coverage=allocation[0]['coverage'] if allocation and not fin else None
    no_returns=not fin and allocation and allocation[0]['dividends']==0 and allocation[0]['buybacks']==0
    add('distributions','FCF / dividends and buybacks',coverage,'not_applicable' if no_returns else 'not_assessed' if coverage is None else 'flag' if coverage<.9 else 'watch' if coverage<1.1 else 'within_rule','Both distributions must be sourced. Zero reported payouts make coverage not applicable. Flag <0.9×; watch <1.1×; generic FCF excluded for financials.','Verify capital returns against cash generation and regulatory limits.')
    if fin:
        # Do not grade a corporate bank margin as financial-sector safety.
        out[3]['value']=None;out[3]['status']='not_assessed'
    order={'flag':0,'watch':1,'not_assessed':2,'not_applicable':3,'within_rule':4}
    return sorted(out,key=lambda item:order[item['status']])[:5]


def peer_candidates(c,companies,limit=4):
    peers=[x for x in companies if x['symbol']!=c['symbol'] and c.get('industry') and x.get('industry')==c['industry']]
    basis='Same provider industry; comparability requires review'
    if not peers:
        peers=[x for x in companies if x['symbol']!=c['symbol'] and c.get('sector') and x.get('sector')==c['sector']]
        basis='Same provider sector only; not verified principal competitors'
    peers=sorted(peers,key=lambda x:x.get('name',x['symbol']))[:limit]
    return [{'symbol':x['symbol'],'name':x.get('name',x['symbol']),'basis':basis,'trailingPE':x.get('trailingPE'),'enterpriseToEbitda':x.get('enterpriseToEbitda'),'roePct':x.get('roePct'),'asOf':x.get('financialAsOf')} for x in peers]


def reported_competitors(c,documents,companies):
    competitors=[]
    passages=[{**item,'sourceId':doc['id']} for doc in documents for item in doc.get('topics',{}).get('competition',[])]
    for other in companies:
        if other['symbol']==c['symbol']:continue
        name=re.sub(r'\b(?:incorporated|corporation|holdings|limited|plc|inc|corp|ltd)\b\.?','',other.get('name',''),flags=re.I).strip(' .,')
        match=next((p for p in passages if len(name)>=4 and re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)',p.get('evidenceText',p['excerpt']),re.I)),None)
        if match:competitors.append({'name':other.get('name'),'symbol':other['symbol'],'classification':'reported_statement','sourceId':match['sourceId']})
    return competitors[:8]


def compose(c,record,companies,news=None,asof=None):
    asof=asof or dt.date.today().isoformat();docs=[d for d in (record.get('documents') or []) if isinstance(d,dict) and d.get('published') and d['published']<=asof and valid_source(d.get('url',''))]
    sources=[source_ref(d) for d in docs];ordered=sorted(docs,key=lambda d:d['published'],reverse=True)
    topics={key:[] for key in ('pricingPower','switchingCosts','marketPosition','costStructure','competition','catalysts','risks')}
    for doc in ordered:
        for key in topics:
            topics[key].extend([{**item,'sourceId':doc['id'],'published':doc['published'],'period':doc.get('period')} for item in doc.get('topics',{}).get(key,[])])
    year=int(asof[:4])
    long_term=[];near_term=[]
    for item in topics['catalysts']:
        years=[int(y) for y in item.get('timeReferences',[])]
        future=[y for y in years if y>=year]
        if future and min(future)>year+3:
            long_term.append({**item,'horizon':'Source time reference beyond 1–3 years: '+', '.join(map(str,future))});continue
        if years and max(years)<year-1:
            long_term.append({**item,'horizon':'Historical event; no forward catalyst timing established'});continue
        near_term.append({**item,'horizon':('Source time references '+', '.join(map(str,future))+'; verify execution context') if future else 'Timing not established; potential 1–3 year relevance is a scenario, not a confirmed outcome'})
    topics['catalysts']=near_term
    competitors=record.get('reportedCompetitors')
    if competitors is None:competitors=reported_competitors(c,docs,companies)
    breakdowns={}
    for kind in ('segments','geography'):
        candidates=[(d,d.get('revenueBreakdown',{}).get(kind)) for d in ordered if d.get('revenueBreakdown',{}).get(kind)]
        if candidates:
            d,b=max(candidates,key=lambda pair:pair[1]['period']);breakdowns[kind]={**b,'sourceId':d['id']}
        else:breakdowns[kind]=None
    sensitivities=[{**s,'sourceId':d['id'],'published':d['published']} for d in ordered for s in d.get('commoditySensitivities',[])]
    result_doc=next((doc for doc in ordered if doc.get('kind') in ('results','interim') and doc.get('reportedResults')),None)
    reported=[{**r,'currency':c.get('financialCurrency'),'sourceId':result_doc['id']} for r in result_doc['reportedResults']] if result_doc else []
    guidance=[g for g in compare_guidance(ordered) if not g.get('horizon') or max(map(int,g['horizon'].split('/')))>=int(asof[:4])]
    warnings=financial_warnings(c);gaps=list(record.get('warnings',[]))
    if not docs:gaps.append('No primary research document was successfully collected; this is not evidence of low risk.')
    for kind in ('segments','geography'):
        if not breakdowns[kind]:gaps.append('No compatible reported revenue '+kind+' table extracted. See issuer disclosures.')
    if not competitors:gaps.append('Principal competitors not verified from the collected competition passages. Peer suggestions are not competitor claims.')
    if not guidance:gaps.append('No unambiguous numeric management guidance extracted. No analyst consensus is inferred.')
    if not any(g.get('previous') for g in guidance):gaps.append('No like-for-like previous guidance comparison available.')
    gaps.append('Independent verification of pricing power, switching costs and market-share claims is not automated.')
    gaps.append('No earnings-call transcript text collected. Source-discovered issuer transcript links only; no paid or invented transcript.')
    if any(x['status']=='not_assessed' for x in warnings):gaps.append('Some material financial screens are unassessed because required data or sector-specific measures are missing.')
    # Cache evidence carries source retrieval dates even when current financials refresh.
    dates=[d.get('retrievedAt','') for d in docs if d.get('retrievedAt')]
    stale=bool(dates and any((dt.date.fromisoformat(asof)-dt.date.fromisoformat(t[:10])).days>120 for t in dates))
    # Old annual source dates are normal; publication age is displayed, not re-dated.
    return {'schema':SCHEMA,'sources':sources,'unparsedSources':record.get('unparsedSources',[]),'topics':{k:v[:8] for k,v in topics.items()},'guidance':guidance,
        'revenueBreakdown':breakdowns,'reportedResults':reported,'reportedCompetitors':competitors[:8],'peerCandidates':peer_candidates(c,companies),
        'capitalAllocation':capital_allocation(c),'longTermDevelopments':long_term[:4],'financialWarnings':warnings,'commoditySensitivities':sensitivities[:3],
        'news':(news or {}).get('articles',[])[:5],'newsRetrievedAt':(news or {}).get('retrievedAt'),
        'transcriptLinks':[x for d in docs for x in d.get('links',[]) if valid_source(x['url'])][:4],
        'gaps':gaps,'checkedAt':record.get('checkedAt'),'staleRetrieval':stale,'offline':record.get('offline',False)}


def compact_record(record):
    """Keep short excerpts and structured facts, not full reports, in public cache."""
    result=json.loads(json.dumps(record))
    # Preserve long competition passages privately until compose; only short excerpts publish.
    for doc in result.get('documents',[]):
        for items in doc.get('topics',{}).values():
            for item in items:item.pop('evidenceText',None)
        for row in doc.get('guidance',[]):row.pop('evidenceText',None)
    return result


def collect(companies,profiles,directory,news=None,offline=False,batch=6,fetcher=None,asof=None):
    from company_profiles import _restore_published
    root=Path(directory);root.mkdir(parents=True,exist_ok=True);path=root/CACHE_NAME
    stamp=asof or now_iso();records={}
    try:records=json.loads(path.read_text()).get('records',{})
    except (OSError,ValueError,AttributeError):pass
    if not records and not offline:records=(_restore_published(CACHE_NAME).get('records') or {})
    records={s:r for s,r in records.items() if isinstance(r,dict)} if isinstance(records,dict) else {}
    source=fetcher or PublicSources(root/'documents',offline=offline);all_companies=list(companies)+list(profiles)
    # Deduplicate; detail profiles take precedence without mutating existing finances.
    all_companies=list({c['symbol']:c for c in reversed(all_companies)}.values())
    def age(value):
        try:return (dt.datetime.fromisoformat(stamp.replace('Z','+00:00'))-dt.datetime.fromisoformat(value.replace('Z','+00:00'))).total_seconds()/3600
        except (ValueError,AttributeError):return 1e9
    pending=[c for c in all_companies if (records.get(c['symbol'],{}).get('schema')!=SCHEMA or age(records.get(c['symbol'],{}).get('checkedAt'))>=REFRESH_HOURS) and age(records.get(c['symbol'],{}).get('attemptedAt'))>=RETRY_HOURS]
    pending.sort(key=lambda c:(c['symbol'] not in PRINCIPAL,records.get(c['symbol'],{}).get('checkedAt','')))
    updated=0;warnings=[]
    if not offline:
        for c in pending[:max(0,batch)]:
            previous=records.get(c['symbol'],{})
            try:
                fresh=parse_sources(c,source,previous,asof=stamp[:10]);fresh['attemptedAt']=stamp;fresh['checkedAt']=stamp
                fresh['reportedCompetitors']=reported_competitors(c,fresh.get('documents',[]),all_companies)
                records[c['symbol']]=fresh;updated+=1
            except Exception as exc:
                records[c['symbol']]={**previous,'attemptedAt':stamp,'warnings':(previous.get('warnings',[])+['Refresh failed: '+str(exc)[:140]])[-8:]}
                warnings.append('Research '+c['symbol']+': '+str(exc)[:100])
    news_map={r['symbol']:r for r in news or []}
    for c in list(companies)+list(profiles):
        record=records.get(c['symbol'],{})
        if offline:record={**record,'offline':True}
        c['intelligence']=compose(c,record,all_companies,news_map.get(c['symbol']),asof=stamp[:10])
    path.write_text(json.dumps({'schema':SCHEMA,'records':{s:compact_record(r) for s,r in records.items()}},separators=(',',':'),allow_nan=False))
    return {'companies':len(all_companies),'primaryCovered':sum(bool(c['intelligence']['sources']) for c in list(companies)+list(profiles)),'refreshed':updated},warnings


def publish(directory,public):
    src=Path(directory)/CACHE_NAME
    if src.exists():Path(public).mkdir(parents=True,exist_ok=True);shutil.copyfile(src,Path(public)/CACHE_NAME)
