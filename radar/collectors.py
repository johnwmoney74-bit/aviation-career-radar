"""Permitted public sources with explicit per-stage diagnostics and bounded paging."""
import hashlib
import ipaddress
import json
import re
import socket
import time
import urllib.error
import urllib.request
import urllib.robotparser
from urllib.parse import urlsplit,urljoin
from .extract import parse_page,extract_jobs,FLYING,canonical,excerpts

AGENT='AviationCareerRadar';MAX_BYTES=4_000_000

def validate_url(url):
    p=urlsplit(url)
    if p.scheme not in ('http','https') or not p.hostname or p.username or p.password:raise ValueError('Use a public HTTP(S) URL without embedded credentials.')
    if p.port not in (None,80,443):raise ValueError('Only standard web ports are supported.')
    if p.hostname.lower() in ('localhost','localhost.localdomain') or p.hostname.lower().endswith(('.local','.internal','.localhost')):raise ValueError('Private/local hosts cannot be monitored.')
    try:literal=ipaddress.ip_address(p.hostname)
    except ValueError:literal=None
    if literal and not literal.is_global:raise ValueError('Private/local addresses cannot be monitored.')
    try:entries=socket.getaddrinfo(p.hostname,p.port or (443 if p.scheme=='https' else 80),type=socket.SOCK_STREAM)
    except socket.gaierror:
        if not urllib.request.getproxies().get(p.scheme):raise
        entries=[]
    for e in entries:
        if not ipaddress.ip_address(e[4][0]).is_global:raise ValueError('Private/local network addresses cannot be monitored.')
    return url

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        validate_url(newurl);return super().redirect_request(req,fp,code,msg,headers,newurl)

def fetch(url):
    validate_url(url)
    req=urllib.request.Request(url,headers={'User-Agent':AGENT+'/0.2 (personal career research)','Accept':'text/html,application/json,application/rss+xml,application/xml'})
    with urllib.request.build_opener(SafeRedirect).open(req,timeout=18) as r:
        b=r.read(MAX_BYTES+1)
        if len(b)>MAX_BYTES:raise ValueError('Source exceeds the 4 MB page limit.')
        return b.decode(r.headers.get_content_charset() or 'utf-8',errors='replace'),r.geturl()

def allowed(url):
    p=urlsplit(url)
    try:body,_=fetch(f'{p.scheme}://{p.netloc}/robots.txt')
    except urllib.error.HTTPError as e:
        if e.code in (404,410):return True,'No robots.txt published; site terms still apply.'
        return False,f'Robots access check returned HTTP {e.code}; access not established.'
    except Exception as e:return False,f'Robots access check failed: {type(e).__name__}: {str(e)[:180]}'
    rp=urllib.robotparser.RobotFileParser();rp.parse(body.splitlines());ok=rp.can_fetch(AGENT,url)
    return ok,'Robots allows this path; site terms still apply.' if ok else 'Robots disallows this path; automatic retrieval skipped.'

def validate_config(config):
    if not isinstance(config,dict):raise ValueError('Source configuration must be an object.')
    c={k:str(config.get(k,''))[:1000] for k in ('link_contains','title_keywords','exclude_contains','next_link_text','sample_url')}
    c['max_pages']=int(config.get('max_pages',1));c['detail_limit']=int(config.get('detail_limit',0))
    if not 1<=c['max_pages']<=5 or not 0<=c['detail_limit']<=5:raise ValueError('Use 1–5 pages and 0–5 detail fetches per source.')
    pages=config.get('extra_urls',[])
    if isinstance(pages,str):pages=[x.strip() for x in pages.splitlines() if x.strip()]
    if not isinstance(pages,list) or len(pages)>8:raise ValueError('Use up to eight extra search-page URLs.')
    c['extra_urls']=[str(u) for u in pages]
    return c

def configured_links(page,base,source,c):
    jobs=extract_jobs(page,base,source['employer'])
    if not c['link_contains'] and not c['title_keywords']:return [j for j in jobs if not c['exclude_contains'] or c['exclude_contains'] not in j['url']]
    # User rules can broaden extraction to custom link structures without regex/code edits.
    jobs=[];keys=[x.strip().lower() for x in c['title_keywords'].split(',') if x.strip()]
    for href,title in page.links:
        url=canonical(urljoin(base,href))
        if urlsplit(url).scheme not in ('http','https') or not title:continue
        if c['link_contains'] and c['link_contains'] not in url:continue
        if c['exclude_contains'] and c['exclude_contains'] in url:continue
        if keys and not any(k in title.lower() for k in keys):continue
        if not keys and not FLYING.search(title):continue
        jobs.append(dict(title=title[:200],employer=source['employer'],url=url,location='',description='',kind='program' if re.search('cadet|pathway',title,re.I) else 'job',evidence='Source-specific link rule; availability and detail requirements need verification',pay='',published='',expires=''))
    return jobs

def collect(source):
    stages=[];started=time.monotonic();jobs=[];warnings=[];texts=[];pages_checked=[]
    def stage(name,status,message):stages.append(dict(stage=name,status=status,message=message))
    def result(status,message,coverage='unavailable'):
        return dict(status=status,message=message,jobs=jobs,digest=hashlib.sha256('\n'.join(texts).encode()).hexdigest(),coverage=coverage,
                    diagnostics=dict(stages=stages,pages=pages_checked,elapsed_seconds=round(time.monotonic()-started,2),warnings=warnings,extracted_count=len(jobs),sample_found=None),preview=jobs[:12],watch_excerpt='\n'.join(texts)[:1800] if source.get('category')!='jobs' else '')
    if source['method']=='manual':
        stage('Access','manual','Manual bookmark; not part of automatic refresh.');return result('manual','Manual source; no automatic extraction configured.','manual')
    try:
        c=validate_config(source.get('config',{}));queue=[source['url']]+c['extra_urls'];seen=set();has_next=False
        max_total=c['max_pages']+len(c['extra_urls'])
        while queue and len(pages_checked)<max_total:
            url=queue.pop(0)
            if url in seen:continue
            seen.add(url);validate_url(url);stage('Connection','passed','Public URL validated: '+url)
            ok,note=allowed(url);stage('Access rules','passed' if ok else 'failed',note)
            if not ok:
                if not pages_checked:return result('blocked',note)
                warnings.append('Skipped inaccessible page: '+url);continue
            body,final=fetch(url);stage('Retrieval','passed',f'Retrieved {len(body)} characters.');pages_checked.append(final)
            if source['method'] in ('lever','greenhouse'):
                data=json.loads(body);entries=data if source['method']=='lever' else data.get('jobs',[])
                if not isinstance(entries,list):raise ValueError('Expected a public job feed list.')
                for entry in entries:
                    title=entry.get('text' if source['method']=='lever' else 'title','')
                    if not FLYING.search(title):continue
                    jobs.append(dict(title=title,employer=source['employer'],url=canonical(entry.get('hostedUrl') or entry.get('absolute_url')),
                        location=entry.get('categories',{}).get('location','') if source['method']=='lever' else entry.get('location',{}).get('name',''),
                        description=(entry.get('descriptionPlain','') if source['method']=='lever' else parse_page(entry.get('content','')).text)[:12000],kind='program' if re.search('cadet|pathway',title,re.I) else 'job',evidence='Public employer feed; verify current terms and availability',pay='',published='',expires=''))
                texts.append(json.dumps(data,sort_keys=True));stage('Extraction','passed',f'Feed contains {len(entries)} records; {len(jobs)} matching flying/program records.')
            else:
                page=parse_page(body)
                if len(page.text)<150 or re.search(r'^(access denied|just a moment|attention required)',page.title.strip(),re.I):raise ValueError('Page appears blocked or incomplete; a dedicated connection may be needed.')
                texts.append(page.text)
                if source['category']=='jobs':jobs.extend(configured_links(page,final,source,c))
                if source.get('standing_lead') and not jobs:
                    lead=dict(source['standing_lead']);lead['evidence']='Standing employer intake checked; not proof of immediate vacancy';lead['description']=excerpts(page.text);jobs.append(lead)
                stage('Extraction','passed' if jobs or source['category']!='jobs' else 'needs attention',f'{len(jobs)} candidate records so far; {len(page.links)} page links inspected.')
                if c['next_link_text']:
                    nxt=next((urljoin(final,h) for h,t in page.links if t.strip().casefold()==c['next_link_text'].casefold()),None)
                    if nxt and urlsplit(nxt).netloc==urlsplit(source['url']).netloc and nxt not in seen:
                        has_next=True
                        if len(pages_checked)<c['max_pages']:queue.append(nxt)
                        else:warnings.append('Next page exists beyond the configured page limit.')
        jobs=list({canonical(j['url']):j for j in jobs}.values())
        stage('Pagination','partial' if queue or warnings else 'passed',f'{len(pages_checked)} pages checked. '+('Configured limit or access failure leaves coverage partial.' if queue or warnings else 'Only configured pages are covered; whole-site completeness is not established.'))
        detailed=0
        for j in jobs[:c['detail_limit']]:
            try:
                ok,note=allowed(j['url'])
                if not ok:raise ValueError(note)
                body,final=fetch(j['url']);page=parse_page(body);extracted=extract_jobs(page,final,j['employer'])
                match=next((x for x in extracted if canonical(x['url'])==canonical(final)),None)
                if match:
                    for k,v in match.items():
                        if v:j[k]=v
                else:j['description']=excerpts(page.text)[:10000]
                detailed+=1
            except Exception as e:warnings.append('Detail unavailable: '+j['title']+' — '+str(e)[:120])
        stage('Detail extraction','passed' if detailed else 'not run',f'{detailed} detailed pages retrieved; configured limit {c["detail_limit"]}.')
        r=result('checked',f'{len(jobs)} candidate records from {len(pages_checked)} page(s).','listings found' if jobs else 'page watch' if source['category']!='jobs' else 'page only — extraction unverified')
        sample=c['sample_url']
        if sample:
            sample_found=canonical(sample) in {canonical(j['url']) for j in jobs};r['diagnostics']['sample_found']=sample_found
            stage('Sample verification','passed' if sample_found else 'needs attention','Saved sample listing '+('found.' if sample_found else 'not found; it may have closed or extraction may have changed.'))
        if not jobs and source['category']=='jobs':r['diagnostics']['warnings'].append('Page loaded but no matching jobs extracted. This is not verified job coverage.')
        return r
    except urllib.error.HTTPError as e:
        stage('Request','failed',f'HTTP {e.code}: {e.reason}');return result('blocked' if e.code in (401,403,429) else 'error',f'HTTP {e.code}; earlier records preserved.')
    except Exception as e:
        stage('Request / extraction','failed',f'{type(e).__name__}: {e}');return result('error',f'{type(e).__name__}: {str(e)[:220]}')
