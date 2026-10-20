"""Run the actual frozen executable; fail the build if it cannot serve resources."""
import argparse
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

p=argparse.ArgumentParser();p.add_argument('executable');args=p.parse_args()
exe=Path(args.executable).resolve()
if not exe.is_file():raise SystemExit('Executable not found: '+str(exe))
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))

def get(url):
    with opener.open(url,timeout=2) as r:return r.read()

with tempfile.TemporaryDirectory() as folder:
    env=dict(os.environ,AVIATION_RADAR_DATA=str(Path(folder)/'profile'))
    report=Path(folder)/'selftest.json'
    r=subprocess.run([str(exe),'--self-test-report',str(report)],env=env,timeout=60)
    if r.returncode or not report.exists():raise SystemExit('Frozen self-test failed')
    results=json.loads(report.read_text())
    if not results.get('ok'):raise SystemExit('Frozen self-test did not pass')
    s=socket.socket();s.bind(('127.0.0.1',0));port=s.getsockname()[1];s.close()
    url=f'http://127.0.0.1:{port}'
    proc=subprocess.Popen([str(exe),'--no-browser','--port',str(port)],env=env)
    try:
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            if proc.poll() is not None:raise RuntimeError('Frozen app exited before serving HTTP')
            try:
                html=get(url+'/').decode();break
            except (OSError,urllib.error.URLError):time.sleep(.3)
        else:raise RuntimeError('Frozen HTTP server did not start')
        state=json.loads(get(url+'/api/state'))
        if not state['sources']:raise RuntimeError('Frozen app has no seed sources')
        for endpoint in ['/app.js','/style.css','/api/research']:
            if len(get(url+endpoint))<50:raise RuntimeError('Missing packaged endpoint: '+endpoint)
        token=re.search(r'name="radar-token" content="([^"]+)"',html).group(1)
        def post(endpoint,payload):
            req=urllib.request.Request(url+'/api/'+endpoint,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','X-Radar-Token':token})
            with opener.open(req,timeout=5) as response:return json.load(response)
        profile=json.loads(get(url+'/api/profile-template'));profile['certificates']['cfi']=True;profile['flight_hours']['total']=500
        pending=post('preview-profile',{'profile':profile});post('approve-profile',{'id':pending['id']})
        lead=post('add-item',dict(title='Packaged CFI test',employer='Test employer',section='cfi',description='CFI required',kind='tip'))
        post('item',dict(id=lead['id'],pinned=True,read=True,notes='Packaged personal history test',requirements=[dict(text='CFI required',field='certificates.cfi',preferred=False,minimum=None)],requirements_reviewed=True))
        updated=json.loads(get(url+'/api/state'));lead=next(j for j in updated['items'] if j['id']==lead['id'])
        if not lead['pinned'] or lead['qualification']['color']!='green':raise RuntimeError('Frozen profile comparison/tracking failed')
        briefing=post('create-briefing',{'days':7})
        if 'Packaged personal history test' not in briefing['prompt']:raise RuntimeError('Frozen briefing missed pinned notes')
        post('import-briefing',dict(id=briefing['id'],text='Packaged imported commentary'))
        results['revision2_profile_tracking_briefings']=True
        req=urllib.request.Request(url+'/api/shutdown',data=b'{}',headers={'Content-Type':'application/json','X-Radar-Token':token})
        with opener.open(req,timeout=3) as response:
            if response.status!=200:raise RuntimeError('Shutdown failed')
        proc.wait(timeout=15)
        if proc.returncode:raise RuntimeError('App shutdown returned a failure')
        results['http_resources']=True;results['authenticated_shutdown']=True
    finally:
        if proc.poll() is None:proc.kill();proc.wait(timeout=10)
    Path('frozen-smoke-test.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(results,indent=2))
