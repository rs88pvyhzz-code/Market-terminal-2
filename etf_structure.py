"""ETF replication, securities lending and counterparty disclosures.

Financial data quality: issuer sources only; a lender's average loaned holdings
are *not* its unsecured counterparty loss exposure. No inferred zero values.
Official pages fetched during TER refresh are reused; no additional requests.
"""
import datetime as dt
import re
import etf_metrics

VANGUARD_POLICY_URL = ('https://www.vanguard.co.uk/professional/vanguard-365/'
                       'investment-knowledge/etf-knowledge/etf-basics')
ISHARES_POLICY_URL = 'https://www.ishares.com/uk/professionals/en/products/'
VANGUARD_REPLICATION_URL = ('https://www.vanguard.co.uk/professional/vanguard-365/'
                            'investment-knowledge/etf-knowledge/replication-methodology')


def _issuer_identity(page, fund, provider, expected_isin):
    visible=etf_metrics.visible_text(page)
    ticker=(fund.get('symbol') or '').split('.')[0].upper()
    if not ticker:
        return False, visible
    if provider=='Vanguard':
        return bool(re.search(r'\('+re.escape(ticker)+r'\)',visible[:10000],re.I)),visible
    if provider=='iShares':
        if not expected_isin or not re.search(r'\bISIN\s*'+re.escape(expected_isin)+r'\b',visible,re.I):
            return False,visible
        # Same share-class identity requirement as the official TER parser.
        match=re.search(r'\b'+re.escape(ticker)+r'\s*(?:\('+re.escape(ticker)+r'\)|LN\b)',visible[:18000],re.I)
        return bool(match),visible
    return False,visible


def _field(visible,label,pattern):
    m=re.search(r'\b'+label+r'\s*\n\s*('+pattern+r')\b',visible,re.I)
    return m.group(1).strip() if m else ''


def _row_numbers(region,label,following,max_cells=12):
    """Extract a published historical table row, never take figures from nearby text."""
    start=re.search(re.escape(label),region,re.I)
    if not start:return []
    tail=region[start.end():]
    after=re.search(re.escape(following),tail,re.I)
    if not after:return []
    chunk=tail[:after.start()].strip()
    if not chunk or len(chunk)>800:return []
    # Numeric table cells only; refuse additional prose or unparseable formatting.
    chunk=re.sub(r'[\s|]+',' ',chunk).strip()
    if not re.fullmatch(r'\d+(?:\.\d+)?(?:\s+\d+(?:\.\d+)?){1,'+str(max_cells-1)+r'}',chunk):
        return []
    values=[float(v) for v in chunk.split()]
    return values if 2<=len(values)<=max_cells else []


def _ishares_lending(visible):
    """Read historical iShares lending *percentages*, not current net exposure.

    Data are published as historical one-year windows. We use the last column
    only if all principal rows have the same number of observations and a
    matching reporting window is present. Otherwise omit the values.
    """
    anchor=visible.find('Lending Summary')
    if anchor<0:return {}
    region=visible[anchor:anchor+10500]
    ends=re.findall(r'\bTo\s+(\d{1,2}[-/]\w{3,9}[-/]\d{4})',region[:4500],re.I)
    # Restrict to published lending rows, not the collateral snapshot matrix.
    labels=[
        ('Securities Lending Return (%)','Average on-loan (% of AUM)'),
        ('Average on-loan (% of AUM)','Maximum on-loan (% of AUM)'),
        ('Maximum on-loan (% of AUM)','Collateralisation (% of Loan)'),
        ('Collateralisation (% of Loan)','The above table'),
    ]
    rows=[_row_numbers(region,a,b) for a,b in labels]
    if not all(rows):return {}
    counts={len(row) for row in rows}
    if len(counts)!=1:return {}
    n=len(rows[0])
    # Funds with fewer than 12 months history may omit the lending table.
    if len(ends)<n:return {}
    values=[row[-1] for row in rows]
    lending_return,avg_loan,max_loan,collateral=values
    if not (0<=lending_return<=30 and 0<=avg_loan<=100 and
            avg_loan<=max_loan<=100 and 100<=collateral<=300):
        return {}
    return {
        'lendingReturnPct':lending_return,
        'averageOnLoanPct':avg_loan,
        'maximumOnLoanPct':max_loan,
        'collateralisationPct':collateral,
        'lendingPeriodEnd':ends[n-1],
        'lendingDataBasis':'Last published historical reporting year — not current exposure',
    }


def parse_issuer_structure(page,fund,provider,expected_isin):
    valid,visible=_issuer_identity(page,fund,provider,expected_isin)
    if not valid:return {}
    out={'structureProvider':provider,
         'structureSource':fund.get('officialFactsUrl') or fund.get('issuerFactsUrl') or '',
         'structureCheckedAt':dt.datetime.now(dt.timezone.utc).date().isoformat()}
    if provider=='Vanguard':
        method=_field(visible,'Investment method','Physical|Synthetic')
        if method:
            out['replicationType']=method.capitalize()
            # Sampling is only verified where the selected fund describes it.
            summary=re.search(r'Fund objectives(.*?)Fund facts',visible,re.I|re.S)
            sampling=bool(summary and re.search(r'representative sample|sampling',summary.group(1),re.I))
            out['issuerReplicationDetail']='Physical sampling' if sampling and method.lower()=='physical' else method.capitalize()+' (submethod not separately verified)'
            out['replicationStatus']='Fund-specific issuer verified'
    elif provider=='iShares':
        structure=_field(visible,'Product Structure','Physical|Synthetic')
        methodology=_field(visible,'Methodology','Physical Replication|Optimised Sampling|Sampling|Synthetic Replication|Swap Based|Swap-based')
        if structure:
            out['replicationType']=structure.capitalize()
            out['replicationStatus']='Fund-specific issuer verified'
            out['issuerReplicationDetail']=methodology or structure.capitalize()+' (submethod not shown)'
        else:
            return {}
        out.update(_ishares_lending(visible))
        if out.get('lendingPeriodEnd'):
            out['lendingStatus']='Fund has published lending history'
            out['lendingDisclosureStatus']='Fund-specific issuer history'
    return out


def enrich(data,offline=False):
    funds=data.get('funds',[])
    warnings=[]
    for f in funds:
        f['catalogueReplication']=f.get('replication') or ''
        f['replicationType']='Unknown'
        f['replicationStatus']='Editorial catalogue only — unverified'
        f['issuerReplicationDetail']=''
        f['lendingStatus']='Fund participation not verified'
        f['lendingDisclosureStatus']='Not obtained'
        f['lendingRevenueSharePct']=None
        f['lendingRevenueShareBasis']=''
        f['averageOnLoanPct']=None
        f['maximumOnLoanPct']=None
        f['collateralisationPct']=None
        f['lendingReturnPct']=None
        f['lendingPeriodEnd']=''
        f['swapCounterpartyNames']=None
        f['swapCounterpartyExposurePct']=None
        f['unsecuredBorrowerExposurePct']=None
        f['counterpartyExposureStatus']='Not reported — do not infer from loan balances'
        f['structureSource']=''
        f['structureCheckedAt']=None
        f['structureProvider']=''
        selected=etf_metrics.official_product(f)
        if selected:
            provider,url,isin=selected
            f['structureSource']=url
            f['structureProvider']=provider
            if provider=='iShares' and f.get('symbol')=='CSPX.L' and isin=='IE00B5BMR087':
                # Issuer's 30 Sep 2025–30 Sep 2026 annual lending summary;
                # dated snapshot, explicitly NOT a live counterparty balance.
                f.update(averageOnLoanPct=3.12, maximumOnLoanPct=4.93,
                         collateralisationPct=109.10, lendingReturnPct=0.00,
                         lendingPeriodEnd='30-Sept-2026',
                         lendingDataBasis='Dated issuer lending summary; not refreshed',
                         lendingStatus='Published historical lending (dated snapshot)',
                         lendingDisclosureStatus='Dated issuer fund-specific history',
                         lendingDataSource='https://www.ishares.com/uk/professionals/en/products/253743/CSPX')
            if provider=='Vanguard':
                # Issuer-wide public policy is not evidence of a specific fund's
                # securities lending participation or current loan balance.
                f['lendingPolicySource']=VANGUARD_POLICY_URL
                f['lendingPolicy']='Issuer offers securities lending; fund participation unconfirmed'
                f['lendingRevenueSharePct']=100.0
                f['lendingRevenueShareBasis']='Net lending revenue after programme costs; issuer-wide policy'
                f['lendingDisclosureStatus']='Issuer-wide policy only'
                f['replicationType']='Physical'
                f['replicationStatus']='Issuer-wide statement — not fund-page verified'
                f['issuerReplicationDetail']='Vanguard states all its ETFs use physical replication'
                f['replicationPolicySource']=VANGUARD_REPLICATION_URL
            elif provider=='iShares':
                f['lendingPolicySource']=url
                f['lendingPolicy']='iShares programme permits lending; fund participation unconfirmed'
                f['lendingRevenueSharePct']=62.5
                f['lendingRevenueShareBasis']='Share of lending income retained by participating funds; issuer programme'
                f['lendingDisclosureStatus']='Issuer-wide programme only'
            # Reuse the issuer's validated visible text from fee retrieval,
            # without a second network request or embedding text in snapshot.
            page=f.pop('_issuerText',None)
            if page:
                parsed=parse_issuer_structure(page,f,provider,isin)
                if parsed:
                    f.update(parsed)
                    if parsed.get('replicationType')=='Physical':
                        if parsed.get('issuerReplicationDetail')=='Physical sampling':
                            f['replication']='Physical sampling'
                        elif not f['replication']:
                            f['replication']='Physical'
                    elif parsed.get('replicationType')=='Synthetic':
                        f['replication']='Synthetic swap'
                    if parsed.get('lendingPeriodEnd'):
                        f['lendingDataSource']=f['structureSource']
                        f['lendingStatus']='Historical fund lending documented'
                        f['lendingPolicy']='Fund has published securities lending figures'
            # Do not assign any zero counterparty exposures by inference.
            if f['replicationType']=='Physical':
                f['counterpartyExposureStatus']='No index-replication swap inferred; securities-lending borrower exposure not quantified'
            elif f['replicationType']=='Synthetic':
                f['counterpartyExposureStatus']='Swap counterparty and collateral exposure need fund-specific disclosure'
        else:
            f.pop('_issuerText',None)
            if f.get('replication','').startswith('Physical'):
                f['replicationType']='Physical (catalogue only)'
            elif f.get('replication','').startswith('Synthetic'):
                f['replicationType']='Synthetic (catalogue only)'
            f['lendingPolicySource']=''
            f['lendingPolicy']='Unknown — request issuer factsheet/prospectus'
    audited=sum(f.get('replicationStatus')=='Fund-specific issuer verified' for f in funds)
    lending=sum(bool(f.get('lendingPeriodEnd')) for f in funds)
    policy=sum(bool(f.get('lendingPolicySource')) for f in funds)
    swap_measured=sum(f.get('swapCounterpartyExposurePct') is not None for f in funds)
    data['structureCoverage']={'catalogued':len(funds),
            'fundSpecificReplication':audited,'issuerPolicyMapped':policy,
            'fundSpecificLendingHistory':lending,
            'actualSwapExposureMeasured':swap_measured}
    data.setdefault('sources',[]).extend([
        'Replication: exact-share-class issuer product facts where verified; otherwise issuer-wide policy or editorial catalogue, always labelled.',
        'Lending: iShares fund-specific historical on-loan and collateralisation figures only when the full table validates; these are NOT current counterparty losses.',
        'Issuer policies: iShares participating funds retain 62.5% of lending income; Vanguard funds receive all net lending revenue after programme costs. Not proof of fund participation.',
        'Counterparty: borrower default exposure and synthetic swap counterparty exposure are not estimated from on-loan amounts; left unavailable without fund-specific evidence.'
    ])
    return data,warnings,0
