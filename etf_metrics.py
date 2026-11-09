"""ETF costs and indicative benchmark tracking error for the Market Terminal.

TER priority: Vanguard and iShares official UK product pages, checked against
an explicitly mapped security and its share-class identifier. justETF is a
third-party fallback only. Preserve catalogue figures when all feeds fail.
Source URLs and time of a *successful* fetch accompany every refreshed fee.

Tracking error: annualised weekly standard deviation of total-return proxy ETF
quotation differences versus the fund's *matching* benchmark total-return index.
This is indicative market-price tracking dispersion, NOT audited NAV tracking
error. Daily cross-market closes are often asynchronous, hence weekly use.
No tracking error against price-only indices or broad ETF proxy benchmarks.
"""
import concurrent.futures
import datetime as dt
import html
from html.parser import HTMLParser
import math
import re
import urllib.parse
import urllib.request
import urllib.error

USER_AGENT = {'User-Agent':'Mozilla/5.0 (compatible; UKETFResearch/1.0)',
              'Accept-Language':'en-GB,en;q=0.9','Accept':'text/html,*/*'}
# Only explicitly verified total-return-index Yahoo symbols. The index currency
# matters; the fund's actual benchmark variant (gross/net) must be checked.
TR_BENCHMARKS = {
    'S&P 500': ('^SP500TR','S&P 500 Total Return','USD'),
    'Russell 2000': ('^RUTTR','Russell 2000 Total Return','USD'),
    'DAX': ('^GDAXI','DAX Performance Index','EUR'),
}

class _VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','noscript','svg'):self.skip+=1
    def handle_endtag(self,tag):
        if tag in ('script','style','noscript','svg') and self.skip:self.skip-=1
    def handle_data(self,data):
        if not self.skip and data.strip():self.parts.append(data.strip())


def parse_ter_page(document, isin):
    """Return TER in percent only after matching the page's actual ISIN."""
    parser=_VisibleText();parser.feed(document)
    visible='\n'.join(parser.parts)
    start=visible[:max(3500,min(len(visible),18000))]
    if not re.search(r'\bISIN\s*'+re.escape(isin)+r'\b',start,re.I):
        return None
    # Prefer the page's primary TER summary, not the comparables fee table.
    patterns=(r'\bTER\s*\n\s*([0-9]+(?:\.[0-9]+)?)\s*%\s*p\.a\.',
              r"ETF.s TER\s*\(total expense ratio\)\s*amounts to\s*([0-9]+(?:\.[0-9]+)?)\s*%",
              r'\bTotal expense ratio\s*\n\s*([0-9]+(?:\.[0-9]+)?)\s*%')
    for pattern in patterns:
        match=re.search(pattern,visible[:12000],re.I)
        if match:
            value=float(match.group(1))
            return value if 0<=value<=5 else None
    return None


# Official, human-verified product identifiers; no search guesses or loosely
# matching a name against an unrelated product. Vanguard IDs point to the
# named ETF share class; BlackRock IDs have independently checked ISINs.
# Stable issuer product paths verified against the actual named share class.
VANGUARD_IDS = {
    'VWRP.L': ('equity','9679','ftse-all-world-ucits-etf-usd-accumulating'),
    'VWRL.L': ('equity','9505','vanguard-ftse-all-world-ucits-etf-usd-distributing'),
    'VUAG.L': ('equity','9694','sp-500-ucits-etf-usd-accumulating'),
    'VUKE.L': ('equity','9509','ftse-100-ucits'),
    'VMIG.L': ('equity','9581','ftse-250-ucits-etf-accumulating'),
    'VMID.L': ('equity','9525','ftse-250-ucits'),
    'VERX.L': ('equity','9524','ftse-developed-europe-ex-uk-ucits-etf-eur-distributing'),
    'VAPX.L': ('equity','9522','ftse-developed-asia-pacific-ex-japan-ucits-etf-usd-distributing'),
    'VGOV.L': ('bond','9501','uk-gilt-ucits-etf-distributing'),
    'VAGP.L': ('bond','9442','global-aggregate-bond-ucits-etf-hedged-distributing'),
}
ISHARES_IDS = {
    'SWDA.L': ('251882','IE00B4L5Y983'),
    'CSPX.L': ('253743','IE00B5BMR087'),
    'ISF.L': ('251795','IE0005042456'),
    'MIDD.L': ('251796','IE00B00FV128'),
    'CNDX.L': ('253741','IE00B53SZB19'),
    'SJPA.L': ('251867','IE00B4L5YX21'),
    'EIMI.L': ('264659','IE00BKM4GZ66'),
    'LTAM.L': ('251856','IE00B27YCK28'),
    'CMX1.L': ('253734','IE00B5WHFQ43'),
    'SPOL.L': ('251875','IE00B4M7GH52'),
    'IGLT.L': ('251806','IE00B1FZSB30'),
    'INXG.L': ('251717','IE00B1FZSD53'),
    'IGLS.L': ('251804','IE00B4WXJK79'),
    'IBTS.L': ('251715','IE00B14X4S71'),
    'SLXX.L': ('251839','IE00B00FV011'),
    'ITKY.L': ('251879','IE00B1FZS574'),
    'IMEU.L': ('251860','IE00B1YZSC51'),
    'EUE.L': ('251781','IE0008471009'),
    'IHYG.L': ('251843','IE00B66F4759'),
    'INRG.L': ('251911','IE00B1XNHC34'),
    'RBOT.L': ('284219','IE00BYZK4552'),
    'FLOT.L': ('288500','IE00BZ048462'),
    'IGLO.L': ('251753','IE00B3F81K65'),
    'LQDE.L': ('251832','IE0032895942'),
    'IUSA.L': ('251900','IE0031442068'),
    'IB01.L': ('307243','IE00BGSF1X88'),
    'IBTM.L': ('251716','IE00B1FZS798'),
    'IDTL.L': ('272124','IE00BSKRJZ44'),
    'TIP5.L': ('287202','IE00BDQYWQ65'),
    'SHYU.L': ('251833','IE00B4PY7Y77'),
    'IEAC.L': ('251726','IE00B3F81R35'),
    'IEMB.L': ('251824','IE00B2NPKV68'),
    'AGBP.L': ('291771','IE00BF540Y54'),
    'ITPS.L': ('251714','IE00B1FZSC47'),
}


# Dated issuer-reported charges cross-checked against the official pages on
# 8 November 2026. These are NOT treated as a live refresh: they provide a
# sourced baseline when websites block robots or a workflow runs offline.
# Values remain subject to later issuer changes.
ISSUER_FEE_SNAPSHOT = {
    'VWRP.L':.14,'VWRL.L':.14,'VUAG.L':.07,'VUKE.L':.09,
    'VMIG.L':.10,'VMID.L':.10,'VERX.L':.10,'VAPX.L':.15,
    'VGOV.L':.05,'VAGP.L':.08,
    'SWDA.L':.20,'CSPX.L':.07,'ISF.L':.07,'MIDD.L':.40,
    'CNDX.L':.30,'SJPA.L':.12,'EIMI.L':.18,'LTAM.L':.20,
    'CMX1.L':.65,'SPOL.L':.74,'IGLT.L':.07,'INXG.L':.10,
    'IGLS.L':.07,'IBTS.L':.07,'SLXX.L':.20,'ITKY.L':.74,
    'IMEU.L':.12,'EUE.L':.10,'IHYG.L':.50,'INRG.L':.65,
    'RBOT.L':.40,'FLOT.L':.10,'IGLO.L':.20,'LQDE.L':.20,
    'IUSA.L':.07,'IB01.L':.07,'IBTM.L':.07,'IDTL.L':.07,
    'TIP5.L':.10,'SHYU.L':.50,'IEAC.L':.09,'IEMB.L':.45,
    'AGBP.L':.10,'ITPS.L':.10,
}
ISSUER_FEE_SNAPSHOT_DATE='2026-11-08'


def official_product(fund):
    symbol=(fund.get('symbol') or '').upper()
    if symbol in VANGUARD_IDS and fund.get('name','').lower().startswith('vanguard'):
        asset,pid,slug=VANGUARD_IDS[symbol]
        return ('Vanguard','https://www.vanguard.co.uk/professional/product/etf/'
                +asset+'/'+pid+'/'+slug,None)
    if symbol in ISHARES_IDS and fund.get('name','').lower().startswith('ishares'):
        pid,expected=ISHARES_IDS[symbol]
        catalog_isin=fund.get('isin') or ''
        if catalog_isin and catalog_isin.upper()!=expected:
            return None  # ISIN conflict: do not accept a fee for a different security.
        return ('iShares','https://www.ishares.com/uk/individual/en/products/'
                +pid+'/',expected)
    return None


def visible_text(html_page):
    parser=_VisibleText()
    parser.feed(html_page)
    return '\n'.join(parser.parts)


def parse_official_ter(document,provider,symbol,expected_isin=None):
    """Reject wrong share classes, fees from unrelated tables and ambiguous pages.

    An iShares page must carry the exact ISIN; a Vanguard page must identify
    the ticker as part of its visible share-class heading (Ticker). The cost
    label is then matched only close to its adjacent value.
    """
    text=visible_text(document)
    ticker=symbol.upper().split('.')[0]
    if provider=='Vanguard':
        # On Vanguard product pages title includes '(VWRP)' etc.
        if not re.search(r'\('+re.escape(ticker)+r'\)',text[:10000],re.I):return None
        match=re.search(r'\bOCF\s*/\s*TER\b\s*([0-9]+(?:\.[0-9]+)?)\s*%',text[:16000],re.I)
    elif provider=='iShares':
        if not expected_isin or not re.search(r'\bISIN\s*'+re.escape(expected_isin)+r'\b',text,re.I):
            return None
        if not re.search(r'\b'+re.escape(ticker)+r'\s*(?:\('+re.escape(ticker)+r'\)|LN\b)',text[:18000],re.I):
            return None
        match=re.search(r'\bTotal\s+Expense\s+Ratio\b\s*([0-9]+(?:\.[0-9]+)?)\s*%',text,re.I)
    else:return None
    if not match:return None
    value=float(match.group(1))
    return value if 0 <= value <= 5 else None


def _get_html(url,timeout=5):
    request=urllib.request.Request(url,headers=USER_AGENT)
    with urllib.request.urlopen(request,timeout=timeout) as response:
        if 'text/html' not in response.headers.get('Content-Type','').lower():
            raise ValueError('Unexpected content type')
        # Don't read arbitrary large responses from an untrusted redirect.
        data=response.read(2500000)
        final=urllib.parse.urlsplit(response.geturl())
        requested=urllib.parse.urlsplit(url)
        if final.scheme!='https' or final.hostname!=requested.hostname:
            raise ValueError('Redirected away from issuer')
    return data.decode('utf-8','replace')


def parse_vanguard_tracking_error(document,symbol):
    """Official Vanguard annualised NAV tracking-error observations, if shown."""
    visible=visible_text(document)
    ticker=symbol.upper().split('.')[0]
    if not re.search(r'\('+re.escape(ticker)+r'\)',visible[:10000],re.I):return {}
    found=re.search(r'Annualized\s+Tracking\s+Error\s+(.*?)\s+Please\s+note',
                    visible,re.I|re.S)
    if not found:return {}
    tail=found.group(1)[:300]
    out={}
    for year in (1,3,5):
        m=re.search(r'\b'+str(year)+r'\s+years?\s*([0-9]+(?:\.[0-9]+)?)\s*%',tail,re.I)
        if m and float(m.group(1))<=5:out['officialTrackingError'+str(year)+'Y']=float(m.group(1))
    if out:
        prior=visible[max(0,found.start()-350):found.start()]
        m=re.search(r'As\s+at\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})',prior,re.I)
        out['officialTrackingErrorAsOf']=m.group(1) if m else 'Date not extracted'
        out['officialTrackingErrorSource']='Vanguard UK official product page'
    return out




def parse_ishares_fund_assets(document, expected_isin):
    """Only fund-level assets, not share class assets or trading volume.

    Requires the correct ISIN on the issuer's product page. The issuer date is
    retained. Do not treat a dated AUM figure as intraday/current liquidity.
    """
    visible = visible_text(document)
    if not expected_isin or not re.search(r'\bISIN\s*' + re.escape(expected_isin) + r'\b', visible, re.I):
        return {}
    match = re.search(
        r'\bNet\s+Assets\s+of\s+Fund\s+as\s+of\s+' 
        r'(\d{1,2}/[A-Za-z]{3,5}/\d{4})\s+(USD|GBP|EUR)\s+([\d,]+)\b',
        visible, re.I)
    if not match:
        return {}
    try:
        value = int(match.group(3).replace(',', ''))
    except ValueError:
        return {}
    if not 100000 <= value <= 10**15:
        return {}
    return {'fundSize': value, 'fundSizeCurrency':match.group(2).upper(),
            'fundSizeAsOf':match.group(1), 'fundSizeSource':'iShares official — Net Assets of Fund'}

def fetch_issuer_ter(fund,timeout=5):
    selected=official_product(fund)
    if not selected:return None,'Unmapped issuer security',None
    provider,url,isin=selected
    try:
        page=_get_html(url,timeout=timeout)
        fee=parse_official_ter(page,provider,fund['symbol'],isin)
        if fee is not None: fund['_issuerText']=visible_text(page)  # issuer identity checked; removed before JSON
        if fee is not None and provider=='Vanguard':
            fund.update(parse_vanguard_tracking_error(page,fund['symbol']))
        if fee is not None and provider=='iShares' and isin:
            fund.update(parse_ishares_fund_assets(page,isin))
        return (fee,(provider+' UK official product page' if fee is not None else
                     'Issuer page did not pass identity / TER checks'),url)
    except Exception as exc:
        return None,provider+' issuer page unavailable: '+type(exc).__name__,url


def fetch_ter(fund,timeout=5):
    """Third-party fallback; never mislabel as issuer-confirmed."""
    isin=(fund.get('isin') or '').upper()
    if not re.fullmatch(r'[A-Z]{2}[A-Z0-9]{10}',isin):
        matched=official_product(fund)
        isin=matched[2] if matched else ''
    if not isin:return None,'ISIN unavailable',None
    url='https://www.justetf.com/uk/etf-profile.html?isin='+urllib.parse.quote(isin)
    try:
        page=_get_html(url,timeout)
        fee=parse_ter_page(page,isin)
        return (fee,'justETF ISIN profile (third party)' if fee is not None else
                'TER not found or ISIN mismatch',url)
    except Exception as exc:
        return None,'justETF unavailable: '+type(exc).__name__,url


def update_fees(funds,offline=False,max_fetch=80):
    today=dt.datetime.now(dt.timezone.utc).date().isoformat()
    for fund in funds:
        # These editorial catalogue trading symbols do not match the issuer's
        # stated exchange lines; leave research entry but flag for correction.
        if fund.get('symbol')=='ICGA.L':
            fund['note']=(fund.get('note') or '')+' · VERIFY: iShares identifies ICGA as MSCI China (not China A), and as a Xetra trading line, not LSE.'
        if fund.get('symbol')=='EXS1.DE':
            fund['note']=(fund.get('note') or '')+' · VERIFY: iShares lists DAXEX on Xetra; EXS1 is not its Xetra trading ticker.'
        fund['terSource']='Editorial CSV (not live verified)' if fund.get('terPct') is not None else 'Not available'
        fund['terCheckedAt']=None
        fund['terUrl']=''
        fund['terStatus']='Catalogue value' if fund.get('terPct') is not None else 'Missing'
        provider=official_product(fund)
        if provider:
            fund['officialFactsUrl']=provider[1]
            fund['issuerFactsUrl']=provider[1]
            fund['terProvider']=provider[0]
            if fund['symbol'] in ISSUER_FEE_SNAPSHOT:
                fund['terPct']=ISSUER_FEE_SNAPSHOT[fund['symbol']]
                fund['terSource']=provider[0]+' official page — dated snapshot '+ISSUER_FEE_SNAPSHOT_DATE
                fund['terAsOf']=ISSUER_FEE_SNAPSHOT_DATE
                fund['terStatus']='Issuer snapshot (not refreshed)'
                fund['terUrl']=provider[1]
        else:
            fund['terProvider']=''
    if offline:
        return {'checked':0,'updated':0,'issuerUpdated':0,'thirdPartyUpdated':0,
                'failed':0,'skipped':len(funds),'officialMapped':sum(bool(official_product(f)) for f in funds)},[]
    candidates=funds[:max(0,min(100,int(max_fetch)))]
    results={}
    def collect_one(fund):
        # Always try official source first for Vanguard / iShares.
        issuer=official_product(fund)
        failure=''
        if issuer:
            fee,note,url=fetch_issuer_ter(fund)
            if fee is not None:return fee,note,url,'Issuer'
            failure=note
        fee,note,url=fetch_ter(fund)
        if fee is not None:return fee,note,url,'Third party'
        return None,(failure+'; ' if failure else '')+note,url,'Unavailable'
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        jobs={pool.submit(collect_one,f):f['symbol'] for f in candidates}
        for future in concurrent.futures.as_completed(jobs):
            try:results[jobs[future]]=future.result()
            except Exception as err:results[jobs[future]]=(None,type(err).__name__,'','Unavailable')
    refreshed=0;issuer_count=0;third_party=0;failed=0
    for f in candidates:
        fee,status,url,source=results.get(f['symbol'],(None,'Unavailable','', 'Unavailable'))
        if fee is None:
            failed+=1
            if f.get('terStatus')!='Issuer snapshot (not refreshed)':
                f['terStatus']='Catalogue fallback' if f.get('terPct') is not None else 'Missing'
            f['terCheckError']=status
            # Last successful source is deliberately not implied to be current.
        else:
            f['terPct']=round(fee,3)
            f['terSource']=status
            f['terCheckedAt']=today
            f['terUrl']=url or ''
            f['terStatus']='Issuer confirmed' if source=='Issuer' else 'Third-party refreshed'
            refreshed+=1
            issuer_count+=int(source=='Issuer');third_party+=int(source=='Third party')
            if source=='Issuer':
                known=official_product(f)
                if known and known[2] and not f.get('isin'):
                    f['isin']=known[2]
    return {'checked':len(candidates),'updated':refreshed,'issuerUpdated':issuer_count,
            'thirdPartyUpdated':third_party,'failed':failed,
            'skipped':len(funds)-len(candidates),
            'officialMapped':sum(bool(official_product(f)) for f in funds)},[]

def _convert_to_usd(price,currency,date,gbpusd):
    if price is None or price<=0:return None
    if currency in ('GBp','GBX'):
        rate=gbpusd.get(date)
        return price*rate/100 if rate and rate>0 else None
    if currency=='GBP':
        rate=gbpusd.get(date)
        return price*rate if rate and rate>0 else None
    if currency=='USD':return price
    return None  # No inference from unknown or EUR currencies.


def _convert_to_benchmark(price,currency,date,gbpusd,gbpeur,index_ccy):
    if index_ccy=='USD':return _convert_to_usd(price,currency,date,gbpusd)
    if index_ccy!='EUR' or price is None or price<=0:return None
    if currency=='EUR':return price
    eur=gbpeur.get(date)
    if currency=='GBP':return price*eur if eur and eur>0 else None
    if currency in ('GBp','GBX'):return price*eur/100 if eur and eur>0 else None
    if currency=='USD':
        usd=gbpusd.get(date)
        return price*eur/usd if eur and usd and eur>0 and usd>0 else None
    return None


def _weekly_common(fund_points,index_points,currency,fx,years,index_ccy='USD',fx_eur=None):
    """Use the latest SAME-DATE traded observation in each ISO week."""
    fund_map={p[0]:_convert_to_benchmark(p[2],currency,p[0],fx,fx_eur or {},index_ccy)
              for p in fund_points if len(p)>2 and p[2] is not None}
    index_map={r['date']:r['close'] for r in index_points
               if r.get('date') and isinstance(r.get('close'),(int,float)) and r['close']>0}
    common=sorted(d for d in fund_map if d in index_map and fund_map[d] and fund_map[d]>0)
    if not common:return []
    end=dt.date.fromisoformat(common[-1])
    start=end-dt.timedelta(days=round(years*365.25)+10)
    weekly={}
    for date in common:
        d=dt.date.fromisoformat(date)
        if d<start:continue
        weekly[d.isocalendar()[:2]]=(date,fund_map[date],index_map[date])
    return sorted(weekly.values())


def _tracking_error(weekly,years):
    if not weekly:return None,0
    end=dt.date.fromisoformat(weekly[-1][0]);start=end-dt.timedelta(days=round(years*365.25))
    rows=[r for r in weekly if dt.date.fromisoformat(r[0])>=start]
    if len(rows)< max(30,int(52*years*.65)):return None,max(0,len(rows)-1)
    span=(dt.date.fromisoformat(rows[-1][0])-dt.date.fromisoformat(rows[0][0])).days/365.25
    if span < years*.80:return None,max(0,len(rows)-1)
    active=[]
    for prev,cur in zip(rows,rows[1:]):
        gap=(dt.date.fromisoformat(cur[0])-dt.date.fromisoformat(prev[0])).days
        if gap<4 or gap>12:continue
        active.append(cur[1]/prev[1]-cur[2]/prev[2])
    if len(active)<max(26,int(years*52*.60)):return None,len(active)
    mean=sum(active)/len(active)
    sd=math.sqrt(sum((x-mean)**2 for x in active)/(len(active)-1))
    return round(100*sd*math.sqrt(52),2),len(active)




def _tracking_difference(weekly, years):
    """Annualised ETF CAGR minus matching benchmark total-return CAGR, in pp.

    Uses EXACT matched dated observations, not yearly averages of unrelated
    close prices. Underlying adjusted-close values are unofficial proxies,
    hence the published metric is always labelled *indicative*.
    """
    if not weekly:
        return None
    end=dt.date.fromisoformat(weekly[-1][0])
    cutoff=end-dt.timedelta(days=round(years*365.25))
    rows=[r for r in weekly if dt.date.fromisoformat(r[0])>=cutoff]
    if len(rows)<max(36,int(52*years*.70)):
        return None
    span=(dt.date.fromisoformat(rows[-1][0])-dt.date.fromisoformat(rows[0][0])).days/365.25
    if span<years*.90 or span>years*1.04:
        return None
    a,b=rows[0],rows[-1]
    if min(a[1],a[2],b[1],b[2])<=0:
        return None
    fund_cagr=(b[1]/a[1])**(1/span)-1
    index_cagr=(b[2]/a[2])**(1/span)-1
    return round(100*(fund_cagr-index_cagr),2)

def update_tracking_error(data,core,opts,main_history):
    funds=data.get('funds',[])
    series={r['symbol']:r.get('points',[]) for r in data.get('history',[])}
    fx={r['date']:r['close'] for r in main_history
        if r.get('symbol')=='GBPUSD=X' and isinstance(r.get('close'),(int,float)) and r['close']>0}
    fx_eur={r['date']:r['close'] for r in main_history
        if r.get('symbol')=='GBPEUR=X' and isinstance(r.get('close'),(int,float)) and r['close']>0}
    results={}
    used={f.get('benchmark') for f in funds}
    for index,(ticker,name,ccy) in TR_BENCHMARKS.items():
        if index not in used:continue
        try:
            # Cache and retry handled by existing market-terminal Yahoo chart reader.
            opt=__import__('copy').copy(opts)
            opt.years=min(6,opts.years)
            quote,history,_,error=core.fetch_quote(('ETF benchmark',ticker,name,'index'),opt)
            if error or not history:continue
            results[index]=(ticker,name,ccy,history)
        except Exception:continue
    calculated=0
    diff_calculated=0
    for f in funds:
        for years in (1,3,5):
            f['trackingError'+str(years)+'Y']=None
            f['trackingDifference'+str(years)+'Y']=None
        f['trackingErrorBasis']='Unavailable: exact fund total-return benchmark not sourced'
        f['trackingErrorBenchmark']=''
        f['trackingErrorObs']=None
        ref=results.get(f.get('benchmark'))
        # An FX-hedged share class needs the corresponding HEDGED index,
        # never the unhedged index with the same short catalogue label.
        if f.get('hedged'):
            f['trackingErrorBasis']='Unavailable: share class hedged; matching hedged total-return benchmark required'
            continue
        if ref is None:continue
        ticker,name,currency,ref_history=ref
        q=f.get('quote') or {}
        points=series.get(f['symbol'],[])
        if not points or not q.get('currency'):
            f['trackingErrorBasis']='Unavailable: ETF adjusted-close prices or currency missing'
            continue
        if q.get('currency','').upper() not in ('USD','GBP','GBX','EUR'):
            f['trackingErrorBasis']='Unavailable: cannot convert ETF to benchmark currency'
            continue
        periods=[]
        for years in (1,3,5):
            rows=_weekly_common(points,ref_history,q['currency'],fx,years,currency,fx_eur)
            val,obs=_tracking_error(rows,years)
            f['trackingError'+str(years)+'Y']=val
            f['trackingDifference'+str(years)+'Y']=_tracking_difference(rows,years)
            periods.append((years,obs,val))
            if val is not None:calculated+=1
            if f['trackingDifference'+str(years)+'Y'] is not None:diff_calculated+=1
        f['trackingErrorBenchmark']=name+' ['+ticker+']'
        f['trackingErrorObs']=periods[0][1]
        f['trackingErrorBasis']='Indicative annualised WEEKLY closing-price dispersion; adjusted ETF quotes vs '+name+'. Not audited fund NAV tracking error; London and US close times differ.'
    return {'eligible':sum(f.get('benchmark') in TR_BENCHMARKS for f in funds),
            'benchmarksAvailable':len(results),
            'calculatedPeriods':calculated,'trackingDifferencePeriods':diff_calculated},[]



def update_peer_dispersion(data,main_history):
    """Research-only peer dispersion; NEVER substitute for index tracking error.

    Same named benchmark and same quote currency; adjusted close of both funds.
    Even two funds tracking one index can differ in securities lending, price
    timing, distributions and NAV. Treat as a relative peer comparison only.
    """
    groups={}
    for f in data.get('funds',[]):
        if f.get('benchmark'):groups.setdefault(f['benchmark'],[]).append(f)
    histories={r['symbol']:r['points'] for r in data.get('history',[])}
    measured=0
    for f in data.get('funds',[]):
        f['peerDispersion1Y']=None
        f['peerDispersion3Y']=None
        f['peerSymbol']=''
        own=histories.get(f['symbol'],[])
        cur=(f.get('quote') or {}).get('currency')
        if not cur or not own:continue
        peers=[p for p in groups.get(f.get('benchmark'),[]) if p['symbol']!=f['symbol']
               and (p.get('quote') or {}).get('currency')==cur and histories.get(p['symbol'])]
        if not peers:continue
        peers.sort(key=lambda p:(p.get('terPct') is None,p.get('terPct') or 999,p['symbol']))
        peer=peers[0]
        pmap={r[0]:r[2] for r in histories[peer['symbol']] if len(r)>2 and r[2] and r[2]>0}
        ownmap={r[0]:r[2] for r in own if len(r)>2 and r[2] and r[2]>0}
        common=sorted(set(ownmap)&set(pmap))
        if not common:continue
        weekly={}
        for date in common:
            iso=dt.date.fromisoformat(date).isocalendar()
            weekly[(iso.year,iso.week)]=(date,ownmap[date],pmap[date])
        samples=sorted(weekly.values())
        f['peerSymbol']=peer['symbol']
        for years in (1,3):
            value,n=_tracking_error(samples,years)
            f['peerDispersion'+str(years)+'Y']=value
            if value is not None:measured+=1
    return measured

def enrich(data,core,opts,main_history):
    """Add fee + TE research to existing ETF snapshot, with failures non-fatal."""
    funds=data.get('funds',[])
    if not funds:return data,[],0
    import os
    max_fetch=int(os.environ.get('ETF_METADATA_MAX_FETCH','80'))
    fees,warnings=update_fees(funds,offline=opts.offline,max_fetch=max_fetch)
    tracking,warns=update_tracking_error(data,core,opts,main_history)
    peers=update_peer_dispersion(data,main_history)
    data['metricsCoverage']={'ter':fees,'trackingError':tracking,'peerDispersionPeriods':peers,
                             'fundSize':sum(f.get('fundSize') is not None for f in funds),
                             'trackingDifference1Y':sum(f.get('trackingDifference1Y') is not None for f in funds)}
    data.setdefault('sources',[]).extend([
        'TER: verified Vanguard/iShares UK official fund page first; justETF ISIN profile fallback only; otherwise static editorial catalog. Every successful refresh carries source URL and retrieval date.',
        'Indicative tracking error: weekly ETF adjusted-close proxy vs matching total-return index, sample standard deviation × sqrt(52). Not official NAV tracking error.',
        'Peer dispersion: weekly adjusted close relative to same named benchmark ETF in same trading currency; NOT index tracking error.',
        'Tracking difference: ETF adjusted-price proxy annualised total return minus exactly matched benchmark total-return annualised return, percentage points per year; indicative only.',
        'Fund size: dated issuer net assets of fund where verified; not intraday volume, daily spread or share-class assets.'
    ])
    return data,warnings+warns,0
