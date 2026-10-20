"""Small, dependency-free public HTML extractors; no browser/session scraping."""
import html
import json
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit

FLYING = re.compile(r'\b(pilot|flight instructor|certified flight instructor|CFI|CFII|first officer|cadet|aerial survey)\b', re.I)

class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.anchor = None
        self.links = []
        self.texts = []
        self.jsons = []
        self.script = None
        self.title = ''
        self.in_title = False
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('script', 'style', 'noscript', 'svg'):
            self.skip += 1
            if tag == 'script' and a.get('type') == 'application/ld+json': self.script = ''
        if tag == 'title': self.in_title = True
        if tag == 'a': self.anchor = [a.get('href', ''), []]
    def handle_data(self, data):
        if self.script is not None: self.script += data
        if self.in_title: self.title += data
        if not self.skip:
            value = ' '.join(data.split())
            if value: self.texts.append(value)
            if self.anchor: self.anchor[1].append(data)
    def handle_endtag(self, tag):
        if tag == 'script' and self.script is not None:
            try: self.jsons.append(json.loads(self.script))
            except (ValueError, TypeError): pass
            self.script = None
        if tag in ('script', 'style', 'noscript', 'svg'): self.skip = max(0, self.skip-1)
        if tag == 'a' and self.anchor:
            self.links.append((self.anchor[0], ' '.join(' '.join(self.anchor[1]).split())))
            self.anchor = None
        if tag == 'title': self.in_title = False
    @property
    def text(self): return '\n'.join(self.texts)

def parse_page(body):
    page = Page(); page.feed(body); return page

def plain(value):
    return parse_page(str(value or '')).text

def canonical(url):
    p = urlsplit(url)
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip('/') or '/', p.query, ''))

def walk_json(obj):
    if isinstance(obj, list):
        for item in obj: yield from walk_json(item)
    elif isinstance(obj, dict):
        yield obj
        for value in obj.values():
            if isinstance(value, (dict, list)): yield from walk_json(value)

def location(value):
    if isinstance(value, list): return '; '.join(filter(None, (location(x) for x in value)))
    if isinstance(value, dict):
        a = value.get('address', value)
        if isinstance(a, str): return a
        return ', '.join(str(a[k]) for k in ('addressLocality', 'addressRegion', 'addressCountry') if a.get(k))
    return str(value or '')

def extract_jobs(page, base, employer):
    found = {}
    for block in page.jsons:
        for item in walk_json(block):
            typ = item.get('@type', '')
            if 'JobPosting' not in (typ if isinstance(typ, list) else [typ]): continue
            title = item.get('title', '')
            if not FLYING.search(title): continue
            url = canonical(urljoin(base, item.get('url') or base))
            org = item.get('hiringOrganization', {})
            desc = plain(item.get('description', ''))
            found[url] = dict(title=title, employer=org.get('name', employer) if isinstance(org, dict) else employer,
                url=url, location=location(item.get('jobLocation')), description=desc[:10000],
                kind='program' if re.search(r'cadet|pathway', title, re.I) else 'job',
                evidence='Structured employer posting; verify availability before applying',
                published=item.get('datePosted', ''), expires=item.get('validThrough', ''),
                pay=json.dumps(item['baseSalary'], ensure_ascii=False) if item.get('baseSalary') else '')
    # Links are leads, not proof of a vacancy. Do not follow pagination or crawl whole sites.
    for href, title in page.links:
        if not FLYING.search(title) or not 8 <= len(title) <= 180: continue
        url = canonical(urljoin(base, href))
        if urlsplit(url).scheme not in ('http', 'https'): continue
        if not re.search(r'/(postings/\d+|jobs/[^/?]+/[^/?]+|job/[^/?]+)', urlsplit(url).path): continue
        if url not in found:
            found[url] = dict(title=title, employer=employer, url=url, location='', description='',
                kind='program' if re.search(r'cadet|pathway', title, re.I) else 'job',
                evidence='Listing link discovered; requirements and availability not yet verified',
                published='', expires='', pay='')
    return list(found.values())

def excerpts(text):
    """Keep context, not inferred salary or eligibility."""
    lines = text.splitlines()
    selected = []
    for i, line in enumerate(lines):
        if re.search(r'qualification|requirement|salary|compensation|\$|minimum|hours|schedule|domicile|base',line,re.I):
            selected.extend(lines[max(0,i-1):min(len(lines),i+4)])
    return '\n'.join(dict.fromkeys(selected))[:5000]
