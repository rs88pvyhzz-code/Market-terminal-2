"""Selected-company research for the static terminal.

Prices use the existing Yahoo chart collector; optional fundamentals come from
`yfinance` (pip install yfinance). Never invent missing P/E or income figures.
The static terminal embeds only companies listed here or requested via CLI.
"""
import datetime as dt
import math
import random
import re

DEFAULT_COMPANIES = [
    ('SHEL.L', 'Shell plc'), ('AZN.L', 'AstraZeneca plc'), ('HSBA.L', 'HSBC Holdings'),
    ('BP.L','BP plc'), ('ULVR.L','Unilever plc'), ('GSK.L','GSK plc'),
    ('RIO.L','Rio Tinto plc'), ('LLOY.L','Lloyds Banking Group'),
    ('BARC.L','Barclays plc'), ('REL.L','RELX plc'), ('DGE.L','Diageo plc'),
    ('NG.L','National Grid plc'), ('BATS.L','British American Tobacco'),
    ('MSFT','Microsoft'), ('AAPL','Apple'), ('NVDA','NVIDIA'),
    ('GOOGL','Alphabet'), ('AMZN','Amazon'), ('META','Meta Platforms'),
    ('JPM','JPMorgan Chase'), ('BRK-B','Berkshire Hathaway'), ('TSLA','Tesla'),
    ('XOM','Exxon Mobil'), ('WMT','Walmart'), ('V','Visa')
]


def valid_symbol(s):
    s=s.strip().upper()
    return s if re.fullmatch(r'[A-Z0-9^][A-Z0-9.\-^]{0,17}',s) else None


def company_universe(custom):
    records={sym:name for sym,name in DEFAULT_COMPANIES}
    for raw in custom:
        symbol=valid_symbol(raw)
        if not symbol: raise ValueError('Invalid company ticker: '+raw)
        records.setdefault(symbol,symbol)
    return list(records.items())


def _num(v):
    try:
        n=float(v)
        return n if math.isfinite(n) else None
    except (ValueError,TypeError,OverflowError): return None


def _text(v):
    return str(v).strip() if v is not None and str(v).strip() else None


# Exact fiscal dates are joined across statements; calendar-year joins can mix periods.
_INCOME = {
    'revenue': ['Total Revenue', 'Operating Revenue'],
    'ebitda': ['EBITDA'],
    'operatingProfit': ['Operating Income'], 'netProfit': ['Net Income', 'Net Income Common Stockholders'],
    'pretaxProfit': ['Pretax Income'], 'taxExpense': ['Tax Provision'],
    'dilutedEps': ['Diluted EPS'], 'grossProfit': ['Gross Profit'],
    'interestExpense': ['Interest Expense', 'Interest Expense Non Operating'],
}
_BALANCE = {
    'receivables': ['Accounts Receivable', 'Receivables'], 'inventory': ['Inventory'],
    'totalAssets': ['Total Assets'], 'equity': ['Stockholders Equity', 'Common Stock Equity'],
    'totalLiabilities': ['Total Liabilities Net Minority Interest'],
    'currentAssets': ['Current Assets'], 'currentLiabilities': ['Current Liabilities'],
    'totalDebt': ['Total Debt'], 'cash': ['Cash And Cash Equivalents'],
    'goodwill': ['Goodwill'], 'sharesOutstanding': ['Ordinary Shares Number'],
}
_CASHFLOW = {
    'operatingCashFlow': ['Operating Cash Flow'], 'capex': ['Capital Expenditure'],
    'investingCashFlow': ['Investing Cash Flow'], 'financingCashFlow': ['Financing Cash Flow'],
    'netBusinessAcquisitions': ['Acquisitions Net', 'Net Business Purchase And Sale'],
    'workingCapitalCashChange': ['Change In Working Capital'],
    'depreciation': ['Depreciation And Amortization', 'Depreciation Amortization Depletion'],
    'shareBasedComp': ['Stock Based Compensation'],
    'buybacks': ['Repurchase Of Capital Stock'], 'dividendsPaid': ['Cash Dividends Paid'],
}


def annual_income_rows(ticker, currency=None, retrieved=None):
    """Up to five real annual periods; missing provider history is never backfilled."""
    periods = {}
    retrieved = retrieved or dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    for attr, fields in (('income_stmt', _INCOME), ('balance_sheet', _BALANCE), ('cashflow', _CASHFLOW)):
        try:
            frame = getattr(ticker, attr)
            if frame is None or frame.empty:
                continue
            for col in frame.columns:
                date = col.date().isoformat() if hasattr(col, 'date') else str(col)[:10]
                row = periods.setdefault(date, {'fiscalYear': date[:4], 'fiscalEnd': date})
                for key, names in fields.items():
                    for name in names:
                        if name in frame.index:
                            value = _num(frame.loc[name, col])
                            if value is not None:
                                row[key] = value
                                row.setdefault('provenance', {})[key] = {'source':'Yahoo Finance', 'period':date, 'retrievedAt':retrieved, 'currency':'shares' if key=='sharesOutstanding' else currency, 'kind':'reported'}
                                break
        except Exception:
            continue  # A missing statement must not discard the other statements.
    return [periods[d] for d in sorted(periods, reverse=True)
            if any(isinstance(v, (int, float)) for v in periods[d].values())][:5]


def latest_balance(ticker, symbol, currency, stamp):
    """Latest dated reported balance, never undated info values labelled current."""
    candidates = []
    for attr in ('quarterly_balance_sheet', 'balance_sheet'):
        try:
            frame = getattr(ticker, attr)
            if frame is None or frame.empty: continue
            for col in frame.columns:
                date = col.date().isoformat() if hasattr(col, 'date') else str(col)[:10]
                if date > stamp[:10]: continue
                row = {'period':date, 'retrievedAt':stamp, 'source':'Yahoo Finance reported balance sheet', 'currency':currency}
                for key in ('totalDebt','cash','sharesOutstanding'):
                    for label in _BALANCE[key]:
                        if label in frame.index:
                            v = _num(frame.loc[label,col])
                            if v is not None:
                                row[key] = v
                                break
                # Ordinary share counts are only auto-used for verified quote units.
                row['shareBasis'] = 'ordinary quoted shares; 1:1' if symbol in ('SHEL.L','HSBA.L','MSFT') else None
                if row['shareBasis'] is None: row.pop('sharesOutstanding',None)
                candidates.append(row)
        except Exception: continue
    return max(candidates,key=lambda r:r['period']) if candidates else None


def research_metadata(info):
    """Provider facts only; never generate a moat, forecast or investment rating."""
    return {
        'businessSummary': _text(info.get('longBusinessSummary')),
        'website': _text(info.get('website')),
        'employees': _num(info.get('fullTimeEmployees')),
        'heldPercentInsiders': _num(info.get('heldPercentInsiders')),
        'heldPercentInstitutions': _num(info.get('heldPercentInstitutions')),
        'shortPercentOfFloat': _num(info.get('shortPercentOfFloat')),
        'sharesOutstanding': _num(info.get('sharesOutstanding')),
        'researchBalance': info.get('_researchBalance'),
        'filingWarning': info.get('_filingWarning'),
    }


def _calendar_events(calendar):
    """Extract date-only Yahoo calendar fields. Any range is indicative."""
    if not isinstance(calendar,dict): return []
    def day(v):
        if isinstance(v,dt.datetime):return v.date().isoformat()
        if isinstance(v,dt.date):return v.isoformat()
        if hasattr(v,'date'):
            try:return v.date().isoformat()
            except Exception:pass
        try:return dt.date.fromisoformat(str(v)[:10]).isoformat()
        except (ValueError,TypeError):return None
    out=[]
    estimates=calendar.get('Earnings Date') or []
    if not isinstance(estimates,(list,tuple)):estimates=[estimates]
    dates=sorted(set(filter(None,(day(x) for x in estimates))))
    if dates:
        out.append({'type':'earnings','title':'Earnings date (provider estimate)' if len(dates)==1 else 'Earnings window (provider estimate)',
                    'date':dates[0],'endDate':dates[-1] if len(dates)>1 else None})
    for label,typ,title in [('Ex-Dividend Date','ex-dividend','Ex-dividend date'),
                             ('Dividend Date','dividend-payment','Dividend payment date')]:
        d=day(calendar.get(label))
        if d:out.append({'type':typ,'title':title,'date':d})
    return out


def financials_for(symbol, offline=False):
    if offline:
        return {},[], 'No fundamentals fetched (offline mode)',[]
    import company_filings
    stamp=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    try: primary, primary_warning=company_filings.collect(symbol)
    except Exception as exc: primary, primary_warning=[], 'SEC parsing unavailable: '+str(exc)[:100]
    info, rows, calendar, client_warning = {}, [], [], None
    try:
        import yfinance as yf
        t=yf.Ticker(symbol)
        try: info=t.get_info() or {}
        except Exception: info={}
        if not isinstance(info,dict): info={}
        currency=info.get('financialCurrency') or (company_filings.ISSUERS.get(symbol) or ('','',''))[2]
        info['financialCurrency']=currency
        rows=annual_income_rows(t,currency,stamp)
        info['_researchBalance']=latest_balance(t,symbol,currency,stamp)
        try: calendar=_calendar_events(t.calendar)
        except Exception: pass
    except Exception as exc:
        client_warning='Yahoo unavailable: '+str(exc)[:100]
    currency=info.get('financialCurrency') or (company_filings.ISSUERS.get(symbol) or ('','',''))[2]
    info['financialCurrency']=currency
    rows=company_filings.retain_financial_history(symbol,company_filings.merge_rows(rows,primary,currency),currency=currency)
    if symbol=='SHEL.L':
        try:
            import shell_issuer_inputs
            balance,capital,issuer_warnings=shell_issuer_inputs.collect()
            info['_researchBalance']=shell_issuer_inputs.apply(info.get('_researchBalance'),balance,capital)
            if issuer_warnings: primary_warning='; '.join(filter(None,[primary_warning,*issuer_warnings]))
        except Exception as exc: primary_warning='Shell supplemental sources unavailable: '+str(exc)[:100]
    info['_filingWarning']=primary_warning
    status='Issuer filings (SEC XBRL) preferred; Yahoo Finance fallback by field' if primary else 'Yahoo Finance via yfinance (unofficial; figures unverified)'
    for warning in (primary_warning,client_warning):
        if warning: status+=' · '+warning
    if not rows and not info.get('_researchBalance') and not any(info.get(k) is not None for k in ('longName','shortName','marketCap','totalRevenue')):
        info={}
    return info,rows,status,calendar


def fetch_company(symbol,name,builder,opts):
    """Return a summary and annual income rows, plus separate daily price history."""
    q,history,_,error=builder.fetch_quote(('Companies',symbol,name,'equity'),opts)
    info,annual,status,events=financials_for(symbol, opts.offline)
    # Yahoo share price may be in GBp, while reported financials are USD/GBP.
    # Do not infer market capitalization currency from the reporting currency.
    quote_currency=(q or {}).get('currency') or info.get('currency') or ''
    marketcap_currency=('GBP' if quote_currency in ('GBp','GBX') else quote_currency)
    financial_currency=info.get('financialCurrency') or ''
    trailing=_num(info.get('trailingPE'))
    forward=_num(info.get('forwardPE'))
    div_yield=_num(info.get('dividendYield'))
    # yfinance dividendYield is a percentage in supported releases, not a fraction.
    # Reject implausible figures instead of displaying a 306% Shell yield.
    if div_yield is not None and not 0 <= div_yield <= 30:div_yield=None
    latest=annual[0] if annual else {}
    # If a statement is missing, do not silently swap in TTM without relabelling.
    company={
        **research_metadata(info),
        'financialAsOf':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
        'symbol':symbol,'name':_text(info.get('longName')) or _text(info.get('shortName')) or name,
        'sector':_text(info.get('sector')),'industry':_text(info.get('industry')),
        'exchange':_text(info.get('exchange')),
        'price':q['price'] if q else None,
        'changePct':q['changePct'] if q else None,
        'priceCurrency':quote_currency,'priceAsOf':q['asOf'] if q else None,
        'marketCap':_num(info.get('marketCap')),'marketCapCurrency':marketcap_currency,
        'trailingPE':trailing if trailing and trailing>0 else None,
        'forwardPE':forward if forward and forward>0 else None,
        'epsTTM':_num(info.get('trailingEps')),
        'dividendYieldPct':div_yield,'priceToBook':_num(info.get('priceToBook')),
        'revenueTTM':_num(info.get('totalRevenue')),
        'netIncomeTTM':_num(info.get('netIncomeToCommon')),
        'profitMarginPct':_num(info.get('profitMargins'))*100 if _num(info.get('profitMargins')) is not None else None,
        'ebitda':_num(info.get('ebitda')),'enterpriseToEbitda':_num(info.get('enterpriseToEbitda')),
        'freeCashflow':_num(info.get('freeCashflow')),'totalDebt':_num(info.get('totalDebt')),
        'roePct':_num(info.get('returnOnEquity'))*100 if _num(info.get('returnOnEquity')) is not None else None,
        'earningsGrowthPct':_num(info.get('earningsGrowth'))*100 if _num(info.get('earningsGrowth')) is not None else None,
        'revenueGrowthPct':_num(info.get('revenueGrowth'))*100 if _num(info.get('revenueGrowth')) is not None else None,
        'revenue':latest.get('revenue'),'operatingProfit':latest.get('operatingProfit'),
        'netProfit':latest.get('netProfit'),'fiscalEnd':latest.get('fiscalEnd'),
        'financialCurrency':financial_currency,'annual':annual,'events':events,
        'fundamentalSource':status,'priceSource':q['source'] if q else None,
        'warning':error or None,
    }
    return company,history,error


def demo_companies():
    """All demonstration financial figures intentionally synthetic and marked."""
    rng=random.Random(4472)
    companies=[];prices=[]
    for i,(sym,name) in enumerate(DEFAULT_COMPANIES):
        reporting='USD' if sym in ('SHEL.L','BP.L','RIO.L') or '.L' not in sym else 'GBP'
        quote='GBp' if sym.endswith('.L') else 'USD'
        annual=[]
        for year in (2025,2024,2023,2022):
            base=(28+i*5)*1e9 * (1-(2025-year)*.035)
            revenue=round(base*(1+rng.uniform(-.06,.06)))
            net=round(revenue*rng.uniform(.06,.18))
            annual.append({'fiscalYear':str(year),'fiscalEnd':f'{year}-12-31',
                'revenue':revenue,'operatingProfit':round(net*1.34),'netProfit':net,
                'pretaxProfit':round(net*1.18),'dilutedEps':None})
        val=1600+i*135 if quote=='GBp' else 90+i*12
        end=dt.date(2026,11,5)
        # Eleven years of WEEKLY synthetic observations so the demo can genuinely
        # illustrate its 1/5/10-year selectors without implying daily quote accuracy.
        for age in range(365*11 + (-365*11) % 7, -1, -7):
            day=end-dt.timedelta(days=age)
            if day.weekday()>4:continue
            progress=(365*11-age)/(365*11)
            v=val*(.56+.44*progress)*(1+.04*math.sin((365*11-age)/130+i))
            prices.append({'symbol':sym,'date':day.isoformat(),'close':round(v,4)})
        current=next(p['close'] for p in reversed(prices) if p['symbol']==sym)
        companies.append({'symbol':sym,'name':name,'sector':'SYNTHETIC / TEST','industry':'Test only',
            'exchange':'Synthetic demonstration','price':current,'changePct':rng.uniform(-2.5,2.5),
            'priceCurrency':quote,'priceAsOf':'2026-11-05 16:30 UTC',
            'marketCap':round(80e9+i*14e9),'marketCapCurrency':'GBP' if quote=='GBp' else 'USD',
            'trailingPE':round(rng.uniform(9,35),2),'forwardPE':round(rng.uniform(8,30),2),
            'epsTTM':round(rng.uniform(1,19),2),'dividendYieldPct':round(rng.uniform(.2,4.8),2),
            'priceToBook':round(rng.uniform(1,8),2),'revenueTTM':annual[0]['revenue'],
            'netIncomeTTM':annual[0]['netProfit'],'profitMarginPct':round(100*annual[0]['netProfit']/annual[0]['revenue'],2),
            'revenue':annual[0]['revenue'],'operatingProfit':annual[0]['operatingProfit'],
            'netProfit':annual[0]['netProfit'],'fiscalEnd':'2025-12-31',
            'financialCurrency':reporting,'annual':annual,'fundamentalSource':'SYNTHETIC DEMO — NOT REAL FINANCIALS',
            'priceSource':'SYNTHETIC DEMO','warning':None})
    return companies,prices
