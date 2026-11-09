"""Release 1 primary-source adapter: SEC XBRL facts for verified issuer mappings.

Companyfacts contains issuer-filed facts, including later restatements. Values
remain in absolute currency/share units; every selected field keeps its filing.
Unsupported issuers/tags fall back to the existing Yahoo collector.
"""
from __future__ import annotations
import datetime as dt
import json
import math
import os
from pathlib import Path
import urllib.request

ISSUERS = {'SHEL.L': ('0001306965', 'ifrs-full', 'USD'),
           'MSFT': ('0000789019', 'us-gaap', 'USD'),
           'HSBA.L': ('0001089113', 'ifrs-full', 'USD')}
GAAP = {
 'revenue': ['RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet', 'Revenues'],
 'operatingProfit': ['OperatingIncomeLoss'], 'netProfit': ['NetIncomeLoss'],
 'pretaxProfit': ['IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest'],
 'taxExpense': ['IncomeTaxExpenseBenefit'], 'grossProfit': ['GrossProfit'],
 'depreciation': ['DepreciationDepletionAndAmortization', 'DepreciationDepletionAndAmortizationPropertyPlantAndEquipment'],
 'operatingCashFlow': ['NetCashProvidedByUsedInOperatingActivities'],
 'capex': ['PaymentsToAcquirePropertyPlantAndEquipment'],
 'investingCashFlow': ['NetCashProvidedByUsedInInvestingActivities'],
 'financingCashFlow': ['NetCashProvidedByUsedInFinancingActivities'],
 'netBusinessAcquisitions': ['PaymentsToAcquireBusinessesNetOfCashAcquired'],
 'shareBasedComp': ['ShareBasedCompensation'], 'dividendsPaid': ['PaymentsOfDividends'],
 'buybacks': ['PaymentsForRepurchaseOfCommonStock'],
 'totalAssets': ['Assets'], 'equity': ['StockholdersEquity'], 'totalLiabilities': ['Liabilities'],
 'currentAssets': ['AssetsCurrent'], 'currentLiabilities': ['LiabilitiesCurrent'],
 'cash': ['CashAndCashEquivalentsAtCarryingValue'], 'sharesOutstanding': ['CommonStockSharesOutstanding'],
 'receivables': ['AccountsReceivableNetCurrent'], 'inventory': ['InventoryNet'], 'goodwill': ['Goodwill'],
}
IFRS = {
 'revenue': ['Revenue', 'RevenueAndOperatingIncome'],
 'operatingProfit': ['ProfitLossFromOperatingActivities'],
 'netProfit': ['ProfitLossAttributableToOwnersOfParent'], 'pretaxProfit': ['ProfitLossBeforeTax'],
 'taxExpense': ['IncomeTaxExpenseContinuingOperations'], 'grossProfit': ['GrossProfit'],
 'depreciation': ['AdjustmentsForDepreciationAndAmortisationExpense'],
 'operatingCashFlow': ['CashFlowsFromUsedInOperatingActivities'],
 'capex': ['PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities'],
 'investingCashFlow': ['CashFlowsFromUsedInInvestingActivities'],
 'financingCashFlow': ['CashFlowsFromUsedInFinancingActivities'],
 'dividendsPaid': ['DividendsPaidOrdinaryShares'], 'buybacks': ['PaymentsToAcquireOrRedeemEntitysShares'],
 'totalAssets': ['Assets'], 'equity': ['EquityAttributableToOwnersOfParent'],
 'totalLiabilities': ['Liabilities'], 'totalDebt': ['Borrowings'],
 'currentAssets': ['CurrentAssets'], 'currentLiabilities': ['CurrentLiabilities'],
 'cash': ['CashAndCashEquivalents'], 'inventory': ['Inventories'], 'goodwill': ['Goodwill'],
}
INSTANT = {'totalAssets', 'equity', 'totalLiabilities', 'totalDebt', 'currentAssets',
           'currentLiabilities', 'cash', 'sharesOutstanding', 'receivables', 'inventory', 'goodwill'}
OUTFLOWS = {'capex', 'dividendsPaid', 'buybacks', 'netBusinessAcquisitions'}


def parse_facts(data, symbol, retrieved, asof=None):
    """Select annual consolidated facts, with no quarterly flows or future filings."""
    cik, namespace, currency = ISSUERS[symbol]
    today = asof or dt.date.today().isoformat()
    facts = data.get('facts', {}).get(namespace, {})
    mappings = GAAP if namespace == 'us-gaap' else IFRS
    periods = {}
    for key, tags in mappings.items():
        selected = {}
        for tag in tags:
            unit = 'shares' if key == 'sharesOutstanding' else currency
            for fact in facts.get(tag, {}).get('units', {}).get(unit, []):
                end = fact.get('end', '')
                try: dt.date.fromisoformat(end)
                except ValueError: continue
                if fact.get('form') not in ('10-K', '10-K/A', '20-F', '20-F/A') or fact.get('filed', '') > today or end > today:
                    continue
                if key not in INSTANT:
                    try: days = (dt.date.fromisoformat(end)-dt.date.fromisoformat(fact['start'])).days
                    except (ValueError, KeyError): continue
                    if not 330 <= days <= 380: continue
                elif 'start' in fact:
                    continue
                value = fact.get('val')
                if not isinstance(value, (int, float)) or not math.isfinite(value): continue
                # Priority tags have a precise definition; latest filing wins within each tag.
                prev = selected.get(end)
                rank = (tags.index(tag), -(int(fact.get('filed', '1900-01-01').replace('-', ''))))
                if prev is None or rank < prev[0]: selected[end] = (rank, fact, tag)
        for end, (_, fact, tag) in selected.items():
            row = periods.setdefault(end, {'fiscalYear': end[:4], 'fiscalEnd': end, 'provenance': {}})
            row[key] = -abs(fact['val']) if key in OUTFLOWS else fact['val']
            row['provenance'][key] = {'source': 'SEC issuer filing', 'tag': namespace+':'+tag,
                'period': end, 'start': fact.get('start'), 'filed': fact.get('filed'),
                'retrievedAt': retrieved, 'currency': 'shares' if key == 'sharesOutstanding' else currency,
                'url': f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{fact["accn"].replace("-", "")}/',
                'accession': fact['accn'], 'kind': 'reported'}
            if key=='netBusinessAcquisitions':row['provenance'][key]['basis']='Cash paid to acquire businesses, net of cash acquired; excludes disposal proceeds'
    # Balance-only instants do not count as annual financial periods.
    rows = [r for r in periods.values() if any(k in r for k in ('revenue', 'netProfit', 'operatingCashFlow'))]
    return sorted(rows, key=lambda r: r['fiscalEnd'], reverse=True)[:5]


def collect(symbol, offline=False, directory=None):
    if symbol not in ISSUERS: return [], None
    root = Path(directory or Path(__file__).parent/'.terminal_filings')
    path = root/(symbol+'.json')
    data = None
    retrieved = None
    try:
        cached = json.loads(path.read_text())
        data, retrieved = cached['data'], cached['retrievedAt']
    except (OSError, ValueError, KeyError): pass
    age = 1e9
    if retrieved:
        try: age = (dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(retrieved)).total_seconds()
        except ValueError: pass
    warning = None
    if not offline and age > 86400:
        try:
            cik = ISSUERS[symbol][0]
            req = urllib.request.Request(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json',
                headers={'User-Agent': os.environ.get('SEC_USER_AGENT', 'MarketTerminal/1.0 (github.com/rs88pvyhzz-code/Market-terminal-2)'), 'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=18) as response: fresh = json.load(response)
            retrieved = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
            data = fresh
            root.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({'data': data, 'retrievedAt': retrieved}, separators=(',', ':')))
        except Exception as exc: warning = 'SEC filings unavailable: '+str(exc)[:120]
    return (parse_facts(data, symbol, retrieved) if data else []), warning


def merge_rows(yahoo, primary, currency):
    """Prefer issuer fields only when currency and exact fiscal period agree."""
    merged = {r['fiscalEnd']: {**r, 'provenance': dict(r.get('provenance', {}))} for r in yahoo}
    for p in primary:
        if not any(source['currency'] in (currency,'shares') for source in p['provenance'].values()): continue
        row = merged.setdefault(p['fiscalEnd'], {'fiscalEnd': p['fiscalEnd'], 'fiscalYear': p['fiscalYear'], 'provenance': {}})
        for key, source in p['provenance'].items():
            if source['currency'] not in (currency, 'shares'): continue
            row[key] = p[key]
            row['provenance'][key] = source
    return [merged[d] for d in sorted(merged, reverse=True)[:5]]
