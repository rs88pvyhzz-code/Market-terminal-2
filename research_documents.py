"""Structured evidence from publicly filed HTML, without generating investment claims.

Parses inline XBRL dimensions (not companyfacts consolidated totals), small
reported tables and short source-linked statements. No transcript/consensus is
synthesised. Keep this independent of the Release 1 financial calculators.
"""
from __future__ import annotations
from html.parser import HTMLParser
import datetime as dt
import hashlib
import math
import re

SCHEMA=1


def clean(s):return ' '.join(str(s).replace('\xa0',' ').split())


def label(s):
    s=s.split(':')[-1]
    s=re.sub(r'(Member|Axis|Domain)$','',s)
    return clean(re.sub(r'(?<=[a-z])(?=[A-Z])',' ',s))


class FilingHTML(HTMLParser):
    def __init__(self,html):
        super().__init__(convert_charrefs=True)
        self.blocks=[];self.tables=[];self.links=[];self.contexts={};self.units={};self.facts=[]
        self.context=None;self.unit=None;self.special=None;self.special_text=[];self.fact=None
        self.table_stack=[];self.row=None;self.cell=None;self.block=None;self.block_tag=None;self.link=None;self.skip=0
        self.feed(html)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ('script','style'):self.skip+=1
        if tag.endswith(':context'):self.context={'id':a.get('id'),'members':[]}
        elif self.context is not None and tag.split(':')[-1] in ('startdate','enddate','instant','explicitmember'):
            self.special=tag.split(':')[-1];self.special_text=[];self.axis=a.get('dimension','')
        elif tag.endswith(':unit'):self.unit=a.get('id')
        elif self.unit and tag.endswith(':measure'):self.special='measure';self.special_text=[]
        if tag=='ix:nonfraction':self.fact={'name':a.get('name',''),'context':a.get('contextref'),'unit':a.get('unitref'),'scale':a.get('scale','0'),'sign':a.get('sign',''),'text':[]}
        if tag=='table':self.table_stack.append([])
        elif tag=='tr':self.row=[]
        elif tag in ('td','th'):self.cell=[]
        if tag in ('div','p','li','h1','h2','h3','h4'):
            self.block=[];self.block_tag=tag
        if tag=='a':self.link=[a.get('href',''),[]]
    def handle_data(self,data):
        if self.special is not None:self.special_text.append(data)
        if self.fact is not None:self.fact['text'].append(data)
        if self.skip:return
        if self.cell is not None:self.cell.append(data)
        if self.block is not None:self.block.append(data)
        if self.link is not None:self.link[1].append(data)
    def handle_endtag(self,tag):
        short=tag.split(':')[-1]
        if self.special==short:
            text=clean(' '.join(self.special_text))
            if short=='measure':self.units[self.unit]=text.split(':')[-1]
            elif self.context is not None:
                if short=='explicitmember':self.context['members'].append((self.axis,text))
                else:self.context[short]=text
            self.special=None
        if tag.endswith(':context') and self.context is not None:
            self.contexts[self.context['id']]=self.context;self.context=None
        if tag.endswith(':unit'):self.unit=None
        if tag=='ix:nonfraction' and self.fact is not None:
            f=self.fact;self.fact=None
            try:
                text=clean(''.join(f.pop('text'))).replace(',','').replace('(','-').replace(')','')
                value=float(text)*(10**int(f['scale']))*(-1 if f['sign']=='-' and not text.startswith('-') else 1)
                if math.isfinite(value):f['value']=value;self.facts.append(f)
            except (ValueError,OverflowError):pass
        if tag in ('td','th') and self.cell is not None:
            if self.row is not None:self.row.append(clean(' '.join(self.cell)))
            self.cell=None
        elif tag=='tr' and self.row is not None:
            if self.table_stack:self.table_stack[-1].append(self.row)
            self.row=None
        elif tag=='table' and self.table_stack:
            t=self.table_stack.pop()
            if t:self.tables.append(t)
        if tag==self.block_tag and self.block is not None:
            text=clean(' '.join(self.block))
            if 30<=len(text)<=4000:self.blocks.append(text)
            self.block=None;self.block_tag=None
        if tag=='a' and self.link is not None:
            self.links.append((self.link[0],clean(' '.join(self.link[1]))));self.link=None
        if tag in ('script','style'):self.skip=max(0,self.skip-1)


REVENUE_TAGS=('RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','Revenue','RevenueAndOperatingIncome','RevenueFromContractsWithCustomers')


def dimensional_revenue(doc,currency):
    """Single explicit dimension only; never sum mixed definitions or axes."""
    groups={}
    for f in doc.facts:
        c=doc.contexts.get(f['context'],{});members=c.get('members',[])
        if len(members)!=1 or not c.get('startdate') or not c.get('enddate'):continue
        try:days=(dt.date.fromisoformat(c['enddate'])-dt.date.fromisoformat(c['startdate'])).days
        except ValueError:continue
        if not 330<=days<=380 or doc.units.get(f['unit'])!=currency:continue
        tag=f['name'].split(':')[-1]
        if tag not in REVENUE_TAGS:continue
        axis,member=members[0]
        kind='geography' if re.search(r'geograph|countr|region',axis,re.I) else 'segments' if re.search(r'business|segment',axis,re.I) else None
        if not kind or re.search(r'consolidat|eliminat|total',member,re.I) or f['value']<0:continue
        key=(kind,c['enddate'],axis,tag,c['startdate'])
        groups.setdefault(key,{})[member]={'label':label(member),'value':f['value'],'member':member}
    result={}
    for kind in ('segments','geography'):
        possible=[(key,values) for key,values in groups.items() if key[0]==kind and len(values)>=2]
        if not possible:result[kind]=None;continue
        key,values=max(possible,key=lambda pair:(pair[0][1],len(pair[1]),-REVENUE_TAGS.index(pair[0][3])))
        result[kind]={'period':key[1],'start':key[4],'axis':key[2],'tag':key[3],'currency':currency,'basis':'Reported revenue by one XBRL axis; entries may overlap (e.g. a country within a region). Do not sum geographic rows or infer market shares.','rows':list(values.values())[:16]}
    return result


TOPICS={
 'pricingPower':r'pricing power|pricing pressure|price increases|pricing strategy',
 'switchingCosts':r'switching costs?|customer retention|integrat(?:ion|ed) platform|ecosystem',
 'marketPosition':r'market share|market position|market leader|leading provider|competitive position',
 'costStructure':r'cost structure|unit costs?|cost reduction|economies of scale|operating leverage|cost competitiveness',
 'competition':r'competitors?|competition|compete with',
 'catalysts':r'(?:launch|acquisit|expan[ds]|capacity|investment|commercial operation|new product|regulatory approval)',
 'risks':r'(?:risk|uncertain|regulat|litigat|cyber|credit loss|impairment|commodity price)',
}
METRICS={
 'capital expenditure':r'cash capital expenditure|capital expenditure|capital spending|capex',
 'RPO recognition':r'remaining performance obligation',
 'revenue':r'\brevenue\b', 'operating margin':r'operating margin',
 'cash flow':r'(?:free|operating) cash flow|cash flow from operating activities',
 'shareholder distributions':r'share buyback|buy-back|share repurchase|dividend|shareholder distribution',
 'banking NII':r'banking NII|net interest income', 'RoTE':r'\bRoTE\b|return on average tangible equity',
}


def statements(doc):
    # Blocks, not a word search over an entire filing; boilerplate is not guidance.
    out=[];seen=set()
    for block in doc.blocks:
        for sentence in re.split(r'(?<=[.!?])\s+(?=[A-Z–—•])',block):
            sentence=clean(sentence).lstrip('–—• ')
            if len(sentence)<45 or len(sentence)>1500 or sentence.lower() in seen:continue
            if re.search(r'forward-looking statements|safe harbor|not a guarantee|except as required by|undue reliance',sentence,re.I):continue
            seen.add(sentence.lower());out.append(sentence)
    return out


def evidence_excerpt(text,words=24):
    tokens=text.split();return ' '.join(tokens[:words])+(' …' if len(tokens)>words or not re.search(r'[.!?]$',text.strip()) else '')


def guidance_rows(sentences,published):
    rows=[]
    for text in sentences:
        if not re.search(r'\b(?:we|our|the group|the company).{0,100}\b(?:expect|target|plan|aim|anticipat)|(?:expenditure|revenue|margin|cash flow).{0,70}(?:expected|guidance|outlook)',text,re.I):continue
        if not re.search(r'\d',text) or re.search(r'not reconcile|not (?:a |our )?(?:forecast|guidance)|not represent.*guidance',text,re.I):continue
        years=re.findall(r'\b20\d{2}\b',text)
        # Forecast year must be explicit, not guessed from the filing date.
        horizon='/'.join(sorted(set(years))) if years else None
        for metric,pattern in METRICS.items():
            if metric=='revenue' and re.search('remaining performance obligation',text,re.I):continue
            hit=re.search(pattern,text,re.I)
            if not hit:continue
            # Keep qualifications alongside amounts; never equate "at least" with "around".
            measure=re.search(r'(\$\s*\d+(?:\.\d+)?\s*(?:(?:-|–|—|to)\s*\$?\s*\d+(?:\.\d+)?)?\s*(?:bn|billion|million)|\d+(?:\.\d+)?\s*%)',text,re.I)
            if not measure:continue
            if metric=='RPO recognition' and (not re.search(r'we expect.{0,50}recognize',text,re.I) or '%' not in measure[0]):continue
            qualifier='at least' if re.search(r'at least',text,re.I) else 'around' if re.search(r'around|approximately|about',text,re.I) else 'range' if re.search(r'\d\s*[-–—]\s*\d',measure[0]) else 'stated'
            # Multiple metric clauses/figures need human review, not spurious numeric attribution.
            metrics=sum(bool(re.search(p,text,re.I)) for k,p in METRICS.items() if not(k=='revenue' and re.search('remaining performance obligation',text,re.I)))
            if metrics>1:continue
            value=clean(measure[0]);unit='USD' if '$' in value else '%'
            metric_name=metric
            if metric=='cash flow' and unit=='%' and re.search(r'growth|grow',text,re.I):metric_name='cash flow growth'
            elif metric=='revenue' and re.search(r'synerg',text,re.I):metric_name='acquisition revenue/cost synergies'
            elif metric=='revenue' and unit=='%' and re.search(r'growth|grow|increas|ris',text,re.I):metric_name='revenue growth'
            elif metric=='revenue' and unit=='USD' and re.search(r'impact|reduction|loss|decrease',text,re.I):metric_name='revenue-related impact (see source for direction)'
            elif metric=='shareholder distributions' and unit=='%' and re.search(r'payout',text,re.I):metric_name='dividend payout ratio'
            elif metric=='shareholder distributions' and unit=='USD' and re.search(r'buyback|buy-back|repurchase',text,re.I):metric_name='share repurchase programme'
            basis='; '.join(k for k,pat in [('constant currency',r'constant currency'),('excluding notable items',r'excluding notable'),('adjusted',r'adjusted'),('cash capex',r'cash capital expenditure')] if re.search(pat,text,re.I))
            rows.append({'metric':metric_name,'horizon':horizon,'amountText':value,'unit':unit,'qualifier':qualifier,'basis':basis,'relativeHorizon':'next 12 months' if re.search(r'next 12 months',text,re.I) else None,
                         'classification':'management_expectation','published':published,'excerpt':evidence_excerpt(text),'evidenceText':text[:1000]})
    # A single dated document may state a current and previous figure; do not choose between them silently.
    unique={}
    for r in rows:unique[(r['metric'],r['horizon'],r['amountText'],r['qualifier'])]=r
    return list(unique.values())[:24]


def compare_guidance(documents):
    out=[]
    ordered=sorted(documents,key=lambda d:d['published'],reverse=True)
    for i,current in enumerate(ordered):
        for row in current.get('guidance',[]):
            if not row['horizon']:
                if not any(r['metric']==row['metric'] and not r.get('horizon') for r in out):out.append({**row,'sourceId':current['id'],'previous':None,'comparison':'forecast period not explicit; no automatic comparison'})
                continue
            key=(row['metric'],row['horizon'],row['unit'],row.get('basis',''))
            if any((r['metric'],r['horizon'],r['unit'],r.get('basis',''))==key for r in out):continue
            cur=[r for r in current['guidance'] if (r['metric'],r['horizon'],r['unit'],r.get('basis',''))==key]
            if len(cur)!=1:continue
            previous=None
            for doc in ordered[i+1:]:
                candidates=[r for r in doc.get('guidance',[]) if (r['metric'],r['horizon'],r['unit'],r.get('basis',''))==key]
                if len(candidates)==1:previous=(doc,candidates[0]);break
            prior=previous[1] if previous else None
            out.append({**row,'sourceId':current['id'],'previous':({**prior,'sourceId':previous[0]['id']} if prior else None),
                'comparison':('different stated terms; review conditions' if (row['amountText'],row['qualifier'])!=(prior['amountText'],prior['qualifier']) else 'same extracted terms; verify conditions') if prior else 'no comparable previous guidance sourced'})
    return out[:12]


def commodity_sensitivities(sentences):
    out=[]
    pattern=r'change of\s*[−-](\d+(?:\.\d+)?)%\s*or\s*\+?(\d+(?:\.\d+)?)%.*?\$([\d.]+)[−–-]([\d.]+)\s*billion impairment or\s*\$([\d.]+)[−–-]([\d.]+)\s*billion impairment reversal'
    for text in sentences:
        m=re.search(pattern,text,re.I)
        if m and 'price outlook' in text.lower():
            out.append({'classification':'possible_scenario','basis':'Issuer asset recoverability sensitivity; not an FCFF coefficient',
                'downShockPct':-float(m[1]),'upShockPct':float(m[2]),'impairmentLow':float(m[3])*1e9,'impairmentHigh':float(m[4])*1e9,
                'reversalLow':float(m[5])*1e9,'reversalHigh':float(m[6])*1e9,'currency':'USD','excerpt':evidence_excerpt(text)})
    return out[:3]


def result_period(doc,metadata):
    if metadata.get('period'):return metadata['period']
    text=' '.join(doc.blocks[:30])
    m=re.search(r'(?:quarter|three and (?:six|nine) month periods?|three[- ]month periods?)\s+ended\s+([A-Za-z]+ \d{1,2},? \d{4})',text,re.I)
    if not m:return None
    try:return dt.datetime.strptime(m[1].replace(',',''),'%B %d %Y').date().isoformat()
    except ValueError:return None


def reported_results(doc,period):
    if not period:return []
    out={}
    pattern=r'^(?:Revenue|Total revenue|Net income|Operating income|Income attributable to .+ shareholders|Cash flow from operating activities|Profit before tax|Adjusted EBITDA)$'
    for table in doc.tables:
        context=' '.join(c for row in table[:5] for c in row)
        if not re.search(r'million',context,re.I) or not re.search(r'quarter|three months',context,re.I):continue
        for row in table:
            labels=[(i,c) for i,c in enumerate(row) if re.fullmatch(pattern,c,re.I)]
            if len(labels)!=1:continue
            i,name=labels[0]
            numbers=[c for j,c in enumerate(row) if j!=i and re.fullmatch(r'\$?\(?[\d,]+(?:\.\d+)?\)?',c)]
            if not numbers:continue
            text=numbers[0].replace('$','').replace(',','').replace('(','-').replace(')','')
            out.setdefault(name,{'metric':name,'value':float(text)*1e6,'period':period,'basis':'First reported quarter column, reported/GAAP where labelled; not an analyst estimate'})
    return list(out.values())[:8]


def narrative_segments(sentences,period,currency):
    rows=[]
    for text in sentences:
        m=re.search(r'Revenue in (.{3,80}?) was \$([\d.]+) (billion|million)',text,re.I)
        if m:rows.append({'label':m[1],'value':float(m[2])*(1e9 if m[3].lower()=='billion' else 1e6),'member':'issuer revenue statement'})
    return {'period':period,'start':None,'axis':'issuer reported business areas','tag':'issuer narrative revenue statement','currency':currency,
        'basis':'Reported quarter business-area revenue, not market share. Segment definitions may change; verify issuer definitions.','rows':rows} if len(rows)>=2 and period else None


def parse_document(html,metadata,currency):
    doc=FilingHTML(html);sentences=statements(doc);topics={}
    period=result_period(doc,metadata);metadata={**metadata,'period':period}
    breakdowns=dimensional_revenue(doc,currency)
    if metadata['kind']=='results':
        fallback=narrative_segments(sentences,period,currency)
        if fallback:breakdowns['segments']=fallback
    for key,pattern in TOPICS.items():
        matches=[s for s in sentences if re.search(pattern,s,re.I) and not re.search(r'audit committee|risk of material misstatement|independent registered public|not reconcile|non-GAAP financial measure',s,re.I)]
        if key=='catalysts':
            matches=[s for s in matches if re.search(r'launch|acquisit|expan[ds]|capacity|commercial operation|new product|regulatory approval|project|commission|start.up',s,re.I) and not re.search(r'cash flow from investing|cash used in investing|cash provided by investing',s,re.I)]
        if key=='risks':matches.sort(key=lambda s:not bool(re.search(r'adversely affect|credit loss|cyberattack|commodity price|regulatory risk|competition',s,re.I)))
        items=[]
        for s in matches[:4]:
            kind='management_expectation' if re.search(r'\bexpect|\bplan|\btarget|\bwill|\baim|\bintend|\bpropos',s,re.I) else 'possible_scenario' if re.search(r'\bmay\b|\bcould\b|\bmight\b|\bwould\b|\bif\b',s,re.I) else 'reported_statement'
            items.append({'excerpt':evidence_excerpt(s),'evidenceText':s[:1200],'classification':kind,'timeReferences':sorted(set(re.findall(r'\b20\d{2}\b',s)))})
        topics[key]=items
    return {**metadata,'schema':SCHEMA,'id':hashlib.sha256(metadata['url'].encode()).hexdigest()[:16],
        'hash':hashlib.sha256(html.encode()).hexdigest(),'revenueBreakdown':breakdowns,'reportedResults':reported_results(doc,period),
        'topics':topics,'commoditySensitivities':commodity_sensitivities(sentences) if currency=='USD' else [],'guidance':guidance_rows(sentences,metadata['published']),
        'links':[{'url':u,'title':t} for u,t in doc.links if re.search(r'transcript',t,re.I) and u.startswith('https://')][:4]}
