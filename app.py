"""Local-only Windows-friendly entry point. Python 3.10+; standard library core."""
import argparse
import base64
import hashlib
import json
import logging
import os
import sys
import secrets
import threading
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from radar.collectors import validate_url
from radar.engine import Engine
from radar.storage import Store, now, data_path
from radar.runtime import VERSION, configure_logging, open_existing, controller

ROOT=Path(__file__).parent
STATUSES={'New','Saved','Investigating','Applied','Future target','Dismissed','Closed'}

def make_handler(engine,token,instance="test"):
    logger=logging.getLogger("radar")
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,fmt,*args):pass
        def send(self,status,body,content_type='application/json; charset=utf-8',filename=None):
            if isinstance(body,(dict,list)):body=json.dumps(body).encode()
            elif isinstance(body,str):body=body.encode()
            self.send_response(status);self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            if filename:self.send_header('Content-Disposition','attachment; filename="'+filename+'"')
            self.end_headers();self.wfile.write(body)
        def local(self):
            expected=f'127.0.0.1:{self.server.server_port}'
            if self.headers.get('Host')!=expected:return False
            origin=self.headers.get('Origin')
            return not origin or origin==f'http://{expected}'
        def do_GET(self):
            if not self.local():return self.send(403,{'error':'Local dashboard access only.'})
            path=urlsplit(self.path).path
            if path=='/api/health':return self.send(200,dict(app='AviationCareerRadar',version=VERSION,instance=instance))
            if path=='/api/state':return self.send(200,engine.state())
            query=parse_qs(urlsplit(self.path).query)
            if path=='/api/briefing':
                rid=query.get('id',[None])[0]
                row=next((x for x in engine.store.rows('briefings') if x['id']==rid),None) if rid else None
                return self.send(200,row['prompt'] if row else engine.briefing(),'text/markdown; charset=utf-8','Aviation-Briefing.md')
            if path=='/api/source-report':
                try:return self.send(200,json.dumps(engine.source_report(query.get('id',[''])[0]),indent=2),'application/json; charset=utf-8','Source-Diagnostics.json')
                except StopIteration:return self.send(404,{'error':'Source not found'})
            if path=='/api/profile-prompt':return self.send(200,engine.profile_prompt(),'text/plain; charset=utf-8','Resume-Profile-Prompt.txt')
            if path=='/api/profile-template':return self.send(200,json.dumps(engine.profile_template(),indent=2),'application/json; charset=utf-8','aviation-profile-template.json')
            if path=='/api/backup':return self.send(200,engine.store.backup(),'application/zip','Aviation-Radar-Backup.zip')
            if path=='/api/research':return self.send(200,(ROOT/'RESEARCH.md').read_text(encoding='utf-8'),'text/markdown; charset=utf-8','Source-and-Pathway-Research.md')
            files={'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/style.css':('style.css','text/css; charset=utf-8')}
            if path not in files:return self.send(404,{'error':'Not found'})
            name,typ=files[path];body=(ROOT/'radar/static'/name).read_text(encoding='utf-8')
            return self.send(200,body.replace('__TOKEN__',token),typ)
        def do_POST(self):
            if not self.local() or not secrets.compare_digest(self.headers.get('X-Radar-Token',''),token):return self.send(403,{'error':'Reload the dashboard and try again.'})
            try:
                n=int(self.headers.get('Content-Length',0))
                if not 0<n<=12_000_000:raise ValueError('Request must be under 12 MB.')
                data=json.loads(self.rfile.read(n));path=urlsplit(self.path).path
                if path=='/api/shutdown':
                    if engine.progress['running']:return self.send(409,{'error':'Wait for the active refresh to finish, then exit.'})
                    self.send(200,{'ok':True})
                    threading.Thread(target=self.server.shutdown,daemon=True).start();return
                if path=='/api/refresh':return self.send(202,{'started':engine.start_refresh()})
                if path=='/api/profile':
                    old=engine.store.get('profile')
                    for k in ('name','school','degree','graduation','cfi_target','preferences','work','notes','total_hours','pic_hours','multi_hours'):
                        if k in data and isinstance(data[k],str):old[k]=data[k][:10000]
                    old['updated']=now();engine.store.put('profile',old)
                elif path=='/api/item':return self.send(200,engine.update_item(data))
                elif path=='/api/add-item':return self.send(200,engine.add_item(data))
                elif path=='/api/link-item':return self.send(200,engine.link_item(data['id'],data['url']))
                elif path=='/api/enrich':return self.send(200,engine.enrich(data['id']))
                elif path=='/api/source':
                    old=next(x for x in engine.store.rows('sources') if x['id']==data['id']);old['enabled']=bool(data['enabled']);engine.store.save('sources',old)
                elif path in ('/api/add-source','/api/edit-source'):return self.send(200,engine.save_source(data))
                elif path=='/api/test-source':return self.send(202,dict(started=engine.start_refresh(data['id'],False)))
                elif path=='/api/verify-source':return self.send(200,engine.verify_source(data['id']))
                elif path=='/api/import-source-preview':
                    source=next(x for x in engine.store.rows('sources') if x['id']==data['id'])
                    if source['status']!='checked':raise ValueError('Run a successful test before importing preview records.')
                    count=0
                    for item in source.get('preview',[]):count+=int(engine.upsert(item,source['id']))
                    return self.send(200,dict(imported_new=count))
                elif path=='/api/pathway':
                    ps=engine.store.get('pathways');row=next(x for x in ps if x['id']==data['id'])
                    row['personal_status']=str(data.get('personal_status',row['personal_status']))[:200];row['notes']=str(data.get('notes',row['notes']))[:10000];engine.store.put('pathways',ps)
                elif path=='/api/add-pathway':
                    url=str(data.get('url',''));validate_url(url);name=str(data.get('name','')).strip()
                    if not name:raise ValueError('Name the program.')
                    ps=engine.store.get('pathways',[]);ps.append(dict(id=uuid.uuid4().hex,name=name[:200],url=url,school_url='',checked='',status=str(data.get('status','Unverified'))[:200],eligibility=str(data.get('eligibility','Not verified'))[:5000],benefits='Not verified',commitments='Not verified',next_step='Review original program and confirm current intake.',personal_status='Research',notes=str(data.get('notes',''))[:5000],connection=data.get('connection','Other program')));engine.store.put('pathways',ps)
                elif path in ('/api/employer','/api/add-employer'):
                    es=engine.store.get('employers');row=next((x for x in es if x['id']==data.get('id')),None)
                    if row is None:
                        name=str(data.get('name','')).strip();url=str(data.get('url',''))
                        if url:validate_url(url)
                        if not name:raise ValueError('Name the employer.')
                        row=dict(id=uuid.uuid4().hex,name=name[:200],url=url,facts_url=url,category=data.get('category','Other'),hq='',operations='',bases='',location_policy='',pay='',schedule='',transfer='',notes='');es.append(row)
                    for k in ('hq','operations','bases','location_policy','pay','schedule','transfer','notes'):
                        if k in data:row[k]=str(data[k])[:10000]
                    row['checked']=now();engine.store.put('employers',es)
                elif path=='/api/upload':return self.send(200,engine.upload(data['name'],base64.b64decode(data['data'],validate=True)))
                elif path=='/api/preview-profile':return self.send(200,engine.preview_profile(data['profile']))
                elif path=='/api/approve-profile':return self.send(200,engine.approve_profile(data['id']))
                elif path=='/api/restore-profile':return self.send(200,engine.restore_profile(data['id']))
                elif path=='/api/create-briefing':return self.send(200,engine.create_briefing(data.get('days',7)))
                elif path=='/api/import-briefing':return self.send(200,engine.import_briefing(data['id'],data['text'],data.get('title','ChatGPT response')))
                else:return self.send(404,{'error':'Unknown operation'})
                return self.send(200,{'ok':True})
            except (ValueError,KeyError,StopIteration) as e:return self.send(400,{'error':str(e) or 'Record not found'})
            except Exception as e:
                logger.exception('API operation failed: %s',path)
                return self.send(500,{'error':'Operation failed: '+str(e)[:200]})
    return Handler

def self_test(report_path):
    """Offline checks that run inside the packaged executable on Windows CI."""
    import tempfile
    required=['VERSION','RESEARCH.md','radar/seed.json','radar/static/index.html','radar/static/app.js','radar/static/style.css']
    missing=[x for x in required if not (ROOT/x).is_file()]
    if missing:raise RuntimeError('Missing packaged resources: '+', '.join(missing))
    import tkinter
    import pypdf
    with tempfile.TemporaryDirectory() as folder:
        store=Store(folder);state=Engine(store).state()
        if len(state['sources'])<1:raise RuntimeError('No seed sources loaded')
        if not state['sections'] or 'qualification' not in state['items'][0]:raise RuntimeError('Revision 2 state missing')
        Engine(store).upload('smoke-test.txt',b'Local resume archive test')
        result=dict(ok=True,version=VERSION,resources=len(required),sources=len(state['sources']),resume_archive=True,pdf_module=pypdf.__version__,tkinter=True,platform=sys.platform)
    Path(report_path).write_text(json.dumps(result,indent=2),encoding='utf-8')

def main(desktop=False):
    p=argparse.ArgumentParser();p.add_argument('--no-browser',action='store_true');p.add_argument('--port',type=int,default=8765);p.add_argument('--refresh-only',action='store_true');p.add_argument('--self-test-report');args=p.parse_args()
    logger=configure_logging()
    if args.self_test_report:
        self_test(args.self_test_report);return
    if desktop and not args.no_browser and open_existing(data_path()):return
    store=Store();engine=Engine(store)
    if args.refresh_only:
        engine.start_refresh()
        while engine.progress['running']:time.sleep(.2)
        if sys.stdout is not None:print(json.dumps(dict(progress=engine.progress,summary=store.get('last_refresh')),indent=2))
        return
    instance=secrets.token_urlsafe(24)
    try:server=ThreadingHTTPServer(('127.0.0.1',args.port),make_handler(engine,secrets.token_urlsafe(32),instance))
    except OSError as exc:
        raise RuntimeError(f'Port {args.port} is in use. Close the old Radar instance and try again.') from exc
    url=f'http://127.0.0.1:{server.server_port}'
    runtime_file=store.path/'running.json'
    runtime_file.write_text(json.dumps(dict(port=server.server_port,instance=instance)))
    logger.info('Radar %s started on loopback port %s',VERSION,server.server_port)
    if sys.stdout is not None:print(f'Aviation Career Radar {VERSION}\nOpen {url}\nData: {store.path}')
    stopped=threading.Event()
    def serve():
        try:server.serve_forever()
        finally:stopped.set()
    thread=threading.Thread(target=serve,daemon=True);thread.start()
    if not args.no_browser:threading.Timer(.7,lambda:webbrowser.open(url)).start()
    try:
        if desktop and not args.no_browser:controller(server,engine,url,stopped)
        else:
            while not stopped.wait(.5):pass
    except KeyboardInterrupt:pass
    finally:
        server.shutdown();thread.join(timeout=5);server.server_close()
        try:
            if json.loads(runtime_file.read_text()).get('instance')==instance:runtime_file.unlink()
        except (OSError,ValueError):pass
        logger.info('Radar stopped')
if __name__=='__main__':main()
