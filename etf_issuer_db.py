"""Issuer data enrichment for ETF terminal.

Never attach issuer information to a fund on an inferred name match. Where a
validated ISIN or exact share-class identifier is unavailable, display missing.
Published fund AUM is not the same as exchange liquidity or share class assets.
"""
import concurrent.futures
import datetime as dt
from html.parser import HTMLParser
import re
import urllib.request
import urllib.parse

DATE = dt.datetime.now(dt.timezone.utc).date().isoformat()
UA = {'User-Agent': 'Mozilla/5.0 (compatible; PersonalMarketResearch/1.0)',
      'Accept': 'text/html,*/*', 'Accept-Language':'en-GB,en;q=0.9'}
# Exact issuer URL and security ID from individual issuer fund pages.
# These are not generated from the ETF ticker or inferred from names.
SPDR = {
    'SWRD.L': ('IE00BFY0GT14', 'https://www.ssga.com/uk/en_gb/institutional/etfs/state-street-spdr-msci-world-ucits-etf-acc-sppw-gy'),
    'R2US.L': ('IE00BJ38QD84', 'https://www.ssga.com/uk/en_gb/institutional/etfs/state-street-spdr-russell-2000-us-small-cap-ucits-etf-acc-zprr-gy'),
}
XTRACKERS = {
    'XDAX.L': ('LU0274211480', 'https://etf.dws.com/en-gb/LU0274211480-dax-ucits-etf-1c/'),
    'XDEX.L': ('IE00BM67HJ62', 'https://etf.dws.com/en-gb/IE00BM67HJ62-msci-emerging-markets-ex-china-ucits-etf-1c/'),
    'XMEX.L': ('LU0476289466', 'https://etf.dws.com/en-gb/LU0476289466-msci-mexico-ucits-etf-1c/'),
    'XMBR.L': ('LU0292109344', 'https://etf.dws.com/en-gb/LU0292109344-msci-brazil-ucits-etf-1c/'),
    'XTMT.L': ('LU2928641757', 'https://etf.dws.com/en-gb/LU2928641757-msci-taiwan-ucits-etf-1d/'),
}
AMUNDI = {
    'LEMA.L': ('LU2573967036', 'https://www.amundietf.co.uk/en/professional/products/equity/amundi-core-msci-emerging-markets-swap-ucits-etf-acc/lu2573967036'),
    'AEME.L': ('LU1437017350', 'https://www.amundietf.co.uk/en/professional/products/equity/amundi-core-msci-emerging-markets-ucits-etf-acc/lu1437017350'),
    'EMXC.L': ('LU2009202107', 'https://www.amundietf.co.uk/en/professional/etf-products/search'),
    'CECL.L': ('LU1900066462', 'https://www.amundietf.co.uk/en/professional/etf-products/search'),
}
# The official Amundi product search lists fund ISIN, OGC and AUM together.
AMUNDI_INDEX = 'https://www.amundietf.co.uk/en/professional/etf-products/search'

class Visible(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.data=[]; self.skip=[]
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','svg','noscript'): self.skip.append(tag)
    def handle_endtag(self,tag):
        if self.skip and self.skip[-1]==tag:self.skip.pop()
    def handle_data(self,data):
        if not self.skip and data.strip():self.data.append(data.strip())

def visible(html):
    parser=Visible();parser.feed(html)
    return re.sub(r'[ \t]+',' ', '\n'.join(parser.data))

def get(url,timeout=6):
    url_parts=urllib.parse.urlsplit(url)
    if url_parts.scheme!='https' or url_parts.hostname not in {
        'www.vanguard.co.uk','www.ishares.com','www.ssga.com','etf.dws.com','etf.deutsche-am.com','www.amundietf.co.uk'}:
        raise ValueError('URL host not an approved ETF issuer')
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=timeout) as response:
        final=urllib.parse.urlsplit(response.geturl())
        if final.scheme!='https' or (final.hostname!=url_parts.hostname and
            not (url_parts.hostname=='etf.dws.com' and final.hostname=='etf.deutsche-am.com')):
            raise ValueError('Issuer page redirected outside approved issuer')
        ct=response.headers.get('Content-Type','').lower()
        if 'text/html' not in ct:raise ValueError('Issuer did not return HTML')
        contents=response.read(3500000)
    return contents.decode('utf-8','replace')

def _number(number):
    # Published issuer pages in UK English may use 1,234.56 or 1234.56.
    val=float(number.replace(',',''))
    return val if 0<=val<10**15 else None

def _asset_amount(amount,unit,ccy):
    try: number=_number(amount)
    except (ValueError,TypeError):return None
    factor={'M':1e6,'MILLION':1e6,'BN':1e9,'B':1e9,'BILLION':1e9,'T':1e12}
    if unit.upper() not in factor:return None
    val=round(number*factor[unit.upper()])
    return (val,ccy.upper()) if 5e4<=val<=1e15 else None

def _extract_aum(txt,provider):
    # Return fund-level assets only. Never use share class assets as a substitute.
    patterns=[]
    if provider=='Vanguard':
        patterns=[r'\bTotal\s+Assets\s*(US\$|£|€|USD|GBP|EUR)\s*([\d,.]+)\s*(B|M|T)\b']
    elif provider=='iShares':
        patterns=[r'\bNet\s+Assets\s+of\s+Fund\s+as\s+of\s+\S+\s+(USD|GBP|EUR)\s*([\d,]+)\b']
    elif provider=='SPDR':
        patterns=[r'\bTotal\s+Fund\s+Assets\s+(USD|GBP|EUR)\s*\$?\s*([\d,.]+)\s*(M|B)\b',
                  r'\bTotal\s+Fund\s+Assets\s*\(millions\)\s*(US\$|£|€)\s*([\d,.]+)\b']
    elif provider=='Xtrackers':
        patterns=[r'\bTotal\s+AUM\s+of\s+fund\b.{0,110}?([\d,.]+)\s*(B|M)\s*(GBP|EUR|USD)\b',
                  r'\bTotal\s+Fund\s+Assets\s*(USD|GBP|EUR)\s*([\d,.]+)\s*(Billion|Million)\b']
    elif provider=='Amundi':
        patterns=[r'\bAssets\s+Under\s+Management\s*([\d,.]+)\s*(M|B)\s*(EUR|USD|GBP)\b',
                  r'\bAUM\s*(USD|EUR|GBP)\s*([\d,.]+)\s*(M|B)\b']
    for pat in patterns:
        m=re.search(pat,txt,re.I|re.S)
        if not m:continue
        groups=m.groups()
        if provider=='iShares':
            ccy,amount=groups
            v=_number(amount)
            if v and 5e4<=v<=1e15:return int(v),ccy.upper()
            continue
        if provider=='Vanguard':
            ccy,amount,unit=groups
        elif provider=='Xtrackers' and groups[-1].upper() in ('EUR','USD','GBP'):
            amount,unit,ccy=groups
        elif provider=='SPDR' and len(groups)==2:
            ccy,amount=groups;unit='M'
        else:
            ccy,amount,unit=groups if provider in ('SPDR','Xtrackers') else (groups[2],groups[0],groups[1])
        ccy={'US$':'USD','£':'GBP','€':'EUR'}.get(ccy.upper(),ccy.upper())
        parsed=_asset_amount(amount,unit,ccy)
        if parsed:return parsed
    return None

def _fee(txt,provider):
    patterns={
     'Vanguard':r'\bOCF\s*/\s*TER\s*([0-9]+(?:\.[0-9]+)?)\s*%',
     'iShares':r'\bTotal\s+Expense\s+Ratio\s*([0-9]+(?:\.[0-9]+)?)\s*%',
     'SPDR':r'\bTER\s*([0-9]+(?:\.[0-9]+)?)\s*%',
     'Xtrackers':r'\b(?:All-in-fee\s*\(TER\)|All-in-fee\s*\(TER\)|Fund\s+all-in\s+fee\s*\(TER\)|All-in-fee)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)\s*%',
     'Amundi':r'\bOngoing\s+Charges\s*\*?\s*([0-9]+(?:\.[0-9]+)?)\s*%',
    }
    m=re.search(patterns[provider],txt,re.I)
    if not m:return None
    fee=float(m.group(1));return fee if 0<=fee<=5 else None

def _replication(txt,provider):
    pat={'Vanguard':r'\bInvestment\s+method\s*(Physical|Synthetic)\b',
         'iShares':r'\b(?:Product\s+Structure|Methodology)\s*(Physical\s+Replication|Physical|Synthetic|Swap)\b',
         'SPDR':r'\bReplication\s+Method\s*(Optimised|Optimized|Full|Physical|Synthetic|Swap)\b',
         'Xtrackers':r'\bInvestment\s+methodology\s*(Direct\s+Replication\s*\(physically\)|Indirect\s+Replication\s*\(Swap\)|Direct\s+Replication|Indirect\s+Replication)',
         'Amundi':r'\bReplication\s+Method\s*(Direct\s*\(physical\)|Indirect\s*\([^)]*swap[^)]*\)|Direct|Indirect)'}
    m=re.search(pat[provider],txt,re.I)
    if not m:return None
    raw=m.group(1)
    if re.search('indirect|swap|synthetic',raw,re.I):return ('Synthetic swap',raw)
    if re.search('optimis|sampl',raw,re.I):return ('Physical sampling',raw)
    if re.search('direct|full|physical',raw,re.I):
        # Unless declared full replication, don't invent full vs sampled.
        if provider=='Xtrackers':
            structure=re.search(r'\bPortfolio\s+structure\s*(Optimised\s+Sampling|Full\s+Replication)',txt,re.I)
            if structure and structure.group(1).lower().startswith('optimised'):return ('Physical sampling',raw+'; '+structure.group(1))
        if provider=='SPDR' and raw.lower().startswith('optimis'):return ('Physical sampling',raw)
        return ('Physical',raw)
    return None

def _date(txt,provider):
    pats={
      'Vanguard':r'\b(?:Total\s+Assets|Fund\s+facts)\b.{0,190}?\b(?:At\s+closure|As\s+of)\s+(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})',
      'iShares':r'\bNet\s+Assets\s+of\s+Fund\s+as\s+of\s+(\d{1,2}/[A-Za-z]{3,5}/\d{4})',
      'SPDR':r'\bTotal\s+Fund\s+Assets\s+(?:USD|GBP|EUR)\b.{0,40}?\bas\s+of\s+(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})',
      'Xtrackers':r'\bTotal\s+AUM\s+of\s+fund,?\s+As\s+of\s+(\d{2}/\d{2}/\d{4})',
      'Amundi':r'\bData\s+as\s+of\s+(\d{2}/\d{2}/\d{4})',
    }
    m=re.search(pats[provider],txt,re.I|re.S)
    return m.group(1) if m else ''

def _identity(txt,provider,isin,ticker):
    # ISIN is a primary key; one wrong share class could produce a wrong fee.
    if provider=='Vanguard':
        return bool(re.search(r'\('+re.escape(ticker)+r'\)',txt[:12000],re.I))
    if not isin:return False
    # Prefer near the fund's Key Facts section; reject if page is a generic search
    # or has multiple non-primary share classes before the requested ISIN.
    if provider=='Amundi':
        pos=txt.find('Main Fund Characteristics')
        block=txt[pos:pos+3500] if pos>=0 else txt[:3200]
        return bool(re.search(r'ISIN\s+code\s*'+re.escape(isin)+r'\b',block,re.I))
    if provider=='SPDR':
        return bool(re.search(r'\bISIN\s*'+re.escape(isin)+r'\b',txt[:18000],re.I))
    if provider=='Xtrackers':
        return bool(re.search(r'\bISIN\s*:?\s*'+re.escape(isin)+r'\b',txt[:12000],re.I))
    if provider=='iShares':
        return bool(re.search(r'\bISIN\s*'+re.escape(isin)+r'\b',txt,re.I))
    return False

def provider_for(f):
    name=f.get('name','').lower(); symbol=f['symbol']
    if name.startswith('spdr') and symbol in SPDR:
        return 'SPDR',*SPDR[symbol]
    if name.startswith('xtrackers') and symbol in XTRACKERS:
        return 'Xtrackers',*XTRACKERS[symbol]
    if name.startswith('amundi') and symbol in AMUNDI and 'search' not in AMUNDI[symbol][1]:
        return 'Amundi',*AMUNDI[symbol]
    if name.startswith(('vanguard','ishares')) and not f.get('fundSize'):
        # The existing issuer-mapping module checks the share class / security
        # against a curated product identifier; never search by similar name.
        try:
            import etf_metrics
            ref=etf_metrics.official_product(f)
        except Exception:
            ref=None
        if ref:
            provider,url,isin=ref
            isin=isin or (f.get('isin') or '').upper()
            return provider,isin,url
    return None

def _parse_page(f,provider,isin,txt,url):
    ticker=f['symbol'].split('.')[0]
    if not _identity(txt,provider,isin,ticker):return {},'ISIN or primary share class absent'
    result={'issuerProvider':provider,'issuerVerifiedUrl':url, 'issuerCheckedAt':DATE}
    fee=_fee(txt,provider)
    if fee is not None:
        result.update(terPct=fee,terStatus='Issuer confirmed',terSource=provider+' official fund page',
                      terUrl=url,terProvider=provider,terCheckedAt=DATE)
    size=_extract_aum(txt,provider)
    if size:
        result.update(fundSize=size[0],fundSizeCurrency=size[1],
                      fundSizeSource=provider+' official fund-level AUM',
                      fundSizeAsOf=_date(txt,provider),fundSizeCheckedAt=DATE,
                      fundSizeStatus='Issuer verified; issuer as-of date shown' if _date(txt,provider) else 'Issuer amount; as-of date not extracted')
    replication=_replication(txt,provider)
    if replication:
        result.update(replication=replication[0],replicationType='Synthetic' if replication[0].startswith('Synthetic') else 'Physical',
                      replicationStatus='Fund-specific issuer verified',
                      issuerReplicationDetail=replication[1],replicationPolicySource=url,
                      replicationCheckedAt=DATE)
    return result,''

def _amundi_search_records(txt):
    # The Amundi search tool is a convenience, not permission to assume a value
    # for an unrelated share class. The exact ISIN must precede OGC and AUM.
    result={}
    for m in re.finditer(r'ISIN\s+code\s+([A-Z]{2}[A-Z0-9]{10})\b',txt,re.I):
        isin=m.group(1).upper()
        seg=txt[m.end():m.end()+420]
        fee=re.search(r'\bOGC\s*(?:[¹1]\s*)?([0-9]+(?:\.[0-9]+)?)\s*%',seg,re.I)
        size=re.search(r'\bAUM\s*(?:[²2]\s*)?(USD|EUR|GBP)\s*([\d,.]+)\s*(M|B)\b',seg,re.I)
        if fee or size:
            row={}
            if fee and 0<=float(fee.group(1))<=5:row['fee']=float(fee.group(1))
            if size:row['size']=_asset_amount(size.group(2),size.group(3),size.group(1))
            result[isin]=row
    return result

def enrich(data,offline=False):
    funds=data.get('funds',[])
    for f in funds:
        f.setdefault('issuerProvider','')
        f.setdefault('fundSizeCheckedAt','')
        f.setdefault('fundSizeStatus','Unverified / not available')
        f.setdefault('replicationCheckedAt','')
    if offline:
        data['issuerDatabaseCoverage']={'catalogued':len(funds),'checked':0,'issuerAum':sum(bool(f.get('fundSize')) for f in funds),
                                        'issuerReplication':sum(f.get('replicationStatus')=='Fund-specific issuer verified' for f in funds),
                                        'issuerFees':sum(f.get('terStatus')=='Issuer confirmed' for f in funds),'offline':True}
        return data,[],0
    candidates=[]
    for fund in funds:
        selected=provider_for(fund)
        if selected:candidates.append((fund,selected))
    def one(target):
        fund,(provider,expected,url)=target
        catalog=fund.get('isin','').upper()
        if catalog and catalog!=expected:return {},'ISIN conflict: '+catalog+' != '+expected
        try:
            text=visible(get(url))
            return _parse_page(fund,provider,expected,text,url)
        except Exception as error:return {},type(error).__name__
    outcomes={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        jobs={pool.submit(one,entry):entry[0]['symbol'] for entry in candidates}
        for future in concurrent.futures.as_completed(jobs):
            sym=jobs[future]
            try:outcomes[sym]=future.result()
            except Exception as exc:outcomes[sym]=({},type(exc).__name__)
    warnings=[]
    for fund,_ in candidates:
        record,error=outcomes.get(fund['symbol'],({},'not fetched'))
        if record:
            fund.update(record)
        if error:fund['issuerRetrievalIssue']=error
    # First-party Amundi search index: exact ISIN match. It does not publish
    # fund-specific replication beside the ISIN, so never infer that field.
    amundi=[f for f in funds if f.get('name','').lower().startswith('amundi') and
            re.fullmatch(r'[A-Z]{2}[A-Z0-9]{10}',f.get('isin',''),re.I)]
    amundi_count=0
    if amundi:
        try:
            index=_amundi_search_records(visible(get(AMUNDI_INDEX,timeout=9)))
            for f in amundi:
                row=index.get(f['isin'].upper())
                if not row:continue
                if row.get('fee') is not None and f.get('terStatus')!='Issuer confirmed':
                    f.update(terPct=row['fee'],terStatus='Issuer confirmed',
                             terSource='Amundi official ETF product finder',terUrl=AMUNDI_INDEX,
                             terProvider='Amundi',terCheckedAt=DATE,issuerProvider='Amundi')
                if row.get('size') and not f.get('fundSize'):
                    value,ccy=row['size'];f.update(fundSize=value,fundSizeCurrency=ccy,
                       fundSizeSource='Amundi official product finder',fundSizeCheckedAt=DATE,
                       fundSizeStatus='Issuer figure; as-of date not established',issuerProvider='Amundi')
                amundi_count+=1
        except Exception as exc:
            warnings.append('Amundi index request failed: '+type(exc).__name__)
    # When a provided security symbol cannot be identified as an exact issuer
    # listing, flag rather than invent ticker-exchange / FX metadata.
    for fund in funds:
        if fund.get('symbol')=='XDEX.L':
            fund['identifierWarning']='Xtrackers ex-China fund has official LSE listing XDEG (GBP); verify XDEX listing and trading currency.'
        if fund.get('symbol')=='XMEX.L':
            fund['identifierWarning']='Xtrackers official LSE listing shows XMES. Confirm XMEX before using prices.'
        if fund.get('symbol')=='XMBR.L':
            fund['identifierWarning']='Xtrackers official LSE page shows XMBD. Confirm XMBR trading line and currency.'
        if fund.get('symbol')=='ICGA.L':
            fund['identifierWarning']='Fund benchmark/ticker labelling needs correcting against iShares official listing.'
        if fund.get('symbol')=='EXS1.DE':
            fund['identifierWarning']='Official iShares DAX listing ticker differs; verify Xetra ticker.'
    coverage={
       'catalogued':len(funds),'checked':len(candidates)+int(bool(amundi)),
       'issuerAum':sum(bool(f.get('fundSize') and f.get('fundSizeSource')) for f in funds),
       'issuerReplication':sum(f.get('replicationStatus')=='Fund-specific issuer verified' for f in funds),
       'issuerFees':sum(f.get('terStatus')=='Issuer confirmed' for f in funds),
       'missingAum':sum(not f.get('fundSize') for f in funds),
       'missingReplicationVerification':sum(f.get('replicationStatus')!='Fund-specific issuer verified' for f in funds),
       'identifierIssues':sum(bool(f.get('identifierWarning')) for f in funds),
       'amundiIndexMatches':amundi_count,
       'offline':False,
    }
    data['issuerDatabaseCoverage']=coverage
    data.setdefault('sources',[]).append(
        'ETF issuer metadata: Vanguard, iShares, SPDR, Xtrackers and Amundi; each amount/TER is attached to a verified security identifier; dates, source and fund-vs-share-class basis retained. Missing values stay missing. AUM is not exchange liquidity.')
    return data,warnings,0
