"""Transparent, conservative classification and qualification comparisons. No AI calls."""
import copy
import math
import re
from urllib.parse import urlsplit

SECTIONS={'cfi':'CFI opportunities','early':'Other early-career flying','regional':'Regional airlines','longterm':'Longer-term jet careers','pathways':'Pathways & recruiting'}
PROGRESS=['Not started','Looking into','Planning to apply','Applied','Interviewing','Offer','Not selected','Withdrawn']
INTEREST=['Undecided','Interested','Not interested']
AVAILABILITY=['Unverified','Open','Closed']
CERTS=['private','instrument','commercial_single','commercial_multi','cfi','cfii','mei','atp','r_atp']
HOURS=['total','pic','multi','turbine','instruction_given']
STATES={'alabama':'AL','alaska':'AK','arizona':'AZ','arkansas':'AR','california':'CA','colorado':'CO','connecticut':'CT','delaware':'DE','florida':'FL','georgia':'GA','hawaii':'HI','idaho':'ID','illinois':'IL','indiana':'IN','iowa':'IA','kansas':'KS','kentucky':'KY','louisiana':'LA','maine':'ME','maryland':'MD','massachusetts':'MA','michigan':'MI','minnesota':'MN','mississippi':'MS','missouri':'MO','montana':'MT','nebraska':'NE','nevada':'NV','new hampshire':'NH','new jersey':'NJ','new mexico':'NM','new york':'NY','north carolina':'NC','north dakota':'ND','ohio':'OH','oklahoma':'OK','oregon':'OR','pennsylvania':'PA','rhode island':'RI','south carolina':'SC','south dakota':'SD','tennessee':'TN','texas':'TX','utah':'UT','vermont':'VT','virginia':'VA','washington':'WA','west virginia':'WV','wisconsin':'WI','wyoming':'WY','district of columbia':'DC'}
SURROUNDING={'OH','MI','IN','KY','WV','PA'}

def location_states(text):
    found=set();remaining=text
    for name in sorted(STATES,key=len,reverse=True):
        pattern=r'\b'+re.escape(name)+r'\b'
        if re.search(pattern,remaining,re.I):found.add(STATES[name]);remaining=re.sub(pattern,' ',remaining,flags=re.I)
    found.update(re.findall(r'(?:,\s*|\b)([A-Z]{2})(?=\b)',text))
    return sorted(found & set(STATES.values()))

def classify(item,employers=()):
    title=item.get('title','').lower();company=item.get('employer','').lower()
    if item.get('kind') in ('program','event') or re.search(r'cadet|pathway|mentorship|career fair',title):return 'pathways'
    if re.search(r'\b(cfi|cfii|mei)\b|flight instructor|flight instruct|professional pilot.*faculty',title):return 'cfi'
    e=next((x for x in employers if x['name'].lower()==company),{})
    if str(e.get('category','')).startswith('CFI'):return 'cfi'
    if e.get('category')=='Regional' or any(x in company for x in ['republic','skywest','envoy','piedmont','envoy','endeavor','psa airlines','commuteair','gojet']):return 'regional'
    if e.get('category') in ('Airline','Fractional') or any(x in company for x in ['netjets','flexjet','fedex','ups airlines','abx air','air transport international','delta air','united airlines','southwest','jetblue','allegiant','abx air','fedex']):return 'longterm'
    if re.search(r'citation|gulfstream|challenger|falcon|learjet|airbus|boeing|jet captain|jet first officer',title):return 'longterm'
    return 'early'

def normalize_item(item,employers=()):
    j=copy.deepcopy(item);legacy=j.get('status','New')
    j.setdefault('section',classify(j,employers));j.setdefault('section_origin','Suggested from title/employer; editable')
    j.setdefault('read',legacy!='New');j.setdefault('interest','Not interested' if legacy=='Dismissed' else 'Interested' if legacy in ('Saved','Investigating','Applied') else 'Undecided')
    j.setdefault('progress','Applied' if legacy=='Applied' else 'Looking into' if legacy=='Investigating' else 'Not started')
    j.setdefault('availability','Closed' if legacy=='Closed' else 'Unverified')
    j.setdefault('pinned',legacy in ('Saved','Investigating','Applied','Future target'))
    j.setdefault('future',legacy=='Future target' or j['section']=='longterm')
    j.setdefault('interactions',[]);j.setdefault('notes','');j.setdefault('next_step','');j.setdefault('follow_up','')
    j.setdefault('updated_since_read',False);j.setdefault('requirements',[]);j.setdefault('user_fields',[])
    employer=next((e for e in employers if e['name'].casefold()==j.get('employer','').casefold()),{})
    operation={'Cargo':'Cargo','Regional':'Passenger airline','Airline':'Passenger airline','Fractional':'Fractional','CFI':'Flight school'}.get(employer.get('category'),'Flight school' if j['section']=='cfi' else 'Unspecified')
    j.setdefault('operation_type',operation);j.setdefault('description','');j.setdefault('location','')
    return j

def empty_qualifications():
    return dict(certificates={x:None for x in CERTS},flight_hours={x:None for x in HOURS},medical_class=None,passport=None,us_work_authorized=None,degree_completed=None)

def validate_profile(obj):
    if not isinstance(obj,dict) or obj.get('schema_version')!=1 or obj.get('kind')!='aviation_profile':raise ValueError('Use an aviation_profile JSON file with schema_version 1. Download the prompt/template first.')
    result={'schema_version':1,'kind':'aviation_profile'}
    for k in ('name','school','graduation','cfi_target','degree','notes'):
        if k in obj:
            if not isinstance(obj[k],str):raise ValueError(k+' must be text.')
            result[k]=obj[k][:10000]
    q=empty_qualifications()
    for group,keys in [('certificates',CERTS),('flight_hours',HOURS)]:
        values=obj.get(group,{})
        if not isinstance(values,dict):raise ValueError(group+' must be an object.')
        if set(values)-set(keys):raise ValueError('Unknown '+group+' fields: '+', '.join(sorted(set(values)-set(keys))))
        for k in keys:
            v=values.get(k)
            if group=='certificates':
                if v is not None and type(v) is not bool:raise ValueError(k+' must be true, false or null.')
            elif v is not None and (type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=200000):raise ValueError(k+' must be a non-negative number or null.')
            q[group][k]=v
    for k in ('passport','us_work_authorized','degree_completed'):
        v=obj.get(k)
        if v is not None and type(v) is not bool:raise ValueError(k+' must be true, false or null.')
        q[k]=v
    v=obj.get('medical_class')
    if v is not None and (type(v) is not int or v not in (1,2,3)):raise ValueError('medical_class must be 1, 2, 3 or null; only use current privileges confirmed by you.')
    q['medical_class']=v;result.update(q)
    planned=obj.get('planned_certificates',[])
    if not isinstance(planned,list) or any(not isinstance(x,str) for x in planned):raise ValueError('planned_certificates must be a text list.')
    result['planned_certificates']=[x[:200] for x in planned[:30]]
    evidence=obj.get('evidence',{})
    if not isinstance(evidence,dict) or any(not isinstance(v,str) for v in evidence.values()):raise ValueError('evidence must map field names to text excerpts.')
    result['evidence']={str(k)[:100]:v[:1000] for k,v in list(evidence.items())[:60]}
    # A known planned certificate cannot also be imported as earned without correction.
    for k in CERTS:
        if k in [x.lower() for x in planned] and result['certificates'][k] is True:raise ValueError(k+' is both planned and earned. Correct the JSON before import.')
    return result

def extract_requirements(text):
    """Recognize simple requirements; complex/alternative wording remains unknown."""
    out=[];seen=set()
    for line in re.split(r'[\n•;]|(?<=[.!?])\s+',text):
        line=' '.join(line.split())
        if not line or len(line)>650:continue
        if not re.search(r'requir|minimum|must|prefer|\bhours?\b|\bCFI\b|\bCFII\b|\bATP\b|certificate|passport|authoriz|degree',line,re.I):continue
        # Do not turn narrative mentions or company biographies into hard requirements.
        preferred=bool(re.search(r'prefer|desired|ideally|a plus',line,re.I))
        req=dict(text=line[:650],preferred=preferred,field='unknown',minimum=None,origin='Automatically extracted — review original wording')
        alternative=bool(re.search(r'\bor\b|\beither\b|\bunless\b|not required|waiv|equivalent',line,re.I))
        if not alternative:
            hour_patterns=[('total',r'(?:total(?:\s+(?:flight|flying))?\s*(?:time)?|total time)'),('pic',r'(?:PIC|pilot.in.command)'),('multi',r'(?:multi.engine|multiengine)'),('turbine',r'turbine'),('instruction_given',r'(?:dual given|instruction given|flight instruction given)')]
            for key,word in hour_patterns:
                m=re.search(r'(\d[\d,]*(?:\.\d+)?)\s*(?:hours?\s*(?:of\s*)?)?'+word+r'(?:\s*(?:time|hours?))?',line,re.I)
                if not m:m=re.search(word+r'\s*(?:time)?\s*(?:of|:|[-–]|minimum|at least)?\s*(\d[\d,]*(?:\.\d+)?)\s*(?:hours?|hrs?)',line,re.I)
                if m:req.update(field='flight_hours.'+key,minimum=float(m.group(1).replace(',','')));break
            # A single supported fact per sentence; mixed requirements stay gray.
            cert_hits=[]
            for key,pat in [('cfii',r'\bCFII\b|instrument instructor'),('mei',r'\bMEI\b'),('cfi',r'\bCFI\b|certified flight instructor'),('commercial_multi',r'commercial multi.engine'),('commercial_single',r'commercial single.engine'),('instrument',r'instrument rating'),('atp',r'\bATP\b|airline transport pilot')]:
                if re.search(pat,line,re.I):cert_hits.append(key)
            if req['field']=='unknown' and len(cert_hits)==1 and re.search(r'requir|must|minimum|prefer|hold|possess|valid|current',line,re.I):req['field']='certificates.'+cert_hits[0]
            if req['field']=='unknown':
                if re.search(r'passport',line,re.I) and re.search(r'must|requir|valid|hold',line,re.I):req['field']='passport'
                elif re.search(r'authoriz|eligible',line,re.I) and re.search(r'work.*(?:U\.?S\.?|United States)',line,re.I):req['field']='us_work_authorized'
                elif re.search(r"bachelor|four.year degree",line,re.I) and re.search(r'requir|must|minimum',line,re.I):req['field']='degree_completed'
            if len(cert_hits)>1 or (cert_hits and req['field'].startswith('flight_hours.')) or len(re.findall(r'\d[\d,]*\s*(?:hours?|hrs?)',line,re.I))>1 or re.search(r'\band\b',line,re.I):req['field']='unknown';req['minimum']=None
        if line.lower() not in seen:out.append(req);seen.add(line.lower())
        if len(out)>=40:break
    return out

def evaluate_requirements(item,profile):
    q=profile.get('qualification_profile') if profile.get('qualifications_approved') else None
    rows=[]
    for r in item.get('requirements') or extract_requirements(item.get('description','')):
        r=copy.deepcopy(r);field=r.get('field','unknown');actual=None
        if q:
            if '.' in field:
                a,b=field.split('.',1);actual=q.get(a,{}).get(b)
            else:actual=q.get(field)
        if not q:color='gray';reason='Import and approve a profile before comparison.'
        elif field=='unknown':color='gray';reason='Wording needs human interpretation; no eligibility guess.'
        elif actual is None:color='gray';reason='Your approved profile does not confirm this fact.'
        elif field.startswith('flight_hours.'):
            if r.get('minimum') is None:color='gray';reason='No unambiguous numeric minimum.'
            else:
                met=float(actual)>=float(r['minimum']);color='green' if met else 'red';reason=f"Your profile: {actual:g} hours; stated minimum: {r['minimum']:g}."
        elif field=='medical_class':
            needed=r.get('minimum')
            if needed not in (1,2,3):color='gray';reason='Medical class requirement is unclear.'
            else:color='green' if actual<=needed else 'red';reason=f'Your confirmed current class: {actual}; required class: {needed}.'
        else:color='green' if actual is True else 'red';reason='Confirmed in your approved profile.' if actual is True else 'Not held/met in your approved profile; planned qualifications do not count as earned.'
        r.update(color=color,reason=reason,actual=actual);rows.append(r)
    required=[r for r in rows if not r.get('preferred')]
    overall='red' if any(x['color']=='red' for x in required) else 'green' if required and all(x['color']=='green' for x in required) and item.get('requirements_reviewed') else 'gray'
    label={'red':'A requirement appears unmet','green':'Reviewed requirements appear met','gray':'Qualification fit needs confirmation'}[overall]
    return dict(color=overall,label=label,rows=rows,reviewed=bool(item.get('requirements_reviewed')))

def source_section(source,employers=()):
    if source.get('section') in SECTIONS:return source['section']
    if source.get('category') in ('pathways','events'):return 'pathways'
    return classify(dict(title=source.get('name',''),employer=source.get('employer','')),employers)
