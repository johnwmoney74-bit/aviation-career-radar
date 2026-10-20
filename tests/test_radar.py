import base64
import io
import json
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import zipfile
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from radar.storage import Store
from radar.engine import Engine, distances
from radar.extract import extract_jobs,parse_page
from radar.collectors import collect,validate_url
from app import make_handler

class RadarTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.store=Store(self.tmp.name);self.engine=Engine(self.store)
 def tearDown(self):self.tmp.cleanup()
 def job(self):return dict(title='CFI',employer='Example',url='https://example.com/jobs/123/cfi',location='Kent, OH',kind='job',description='',evidence='Test fixture',pay='',published='',expires='')
 def test_dedup_preserves_user_data_and_merges_sources(self):
  self.engine.upsert(self.job(),'a');j=next(x for x in self.store.rows('items') if x['title']=='CFI');j.update(status='Saved',notes='Call chief instructor',pay='$40/hour — user note',user_fields=['pay']);self.store.save('items',j)
  new=self.job();new.update(description='Updated requirements',pay='$35/hour');self.engine.upsert(new,'b')
  j=next(x for x in self.store.rows('items') if x['title']=='CFI');self.assertEqual(j['status'],'Saved');self.assertEqual(j['notes'],'Call chief instructor');self.assertEqual(j['pay'],'$40/hour — user note');self.assertEqual(set(j['source_ids']),{'a','b'})
 def test_failure_and_empty_results_do_not_close_old_jobs(self):
  s=self.store.rows('sources')[0];self.engine.upsert(self.job(),s['id'])
  for result in [dict(status='blocked',message='HTTP 403',jobs=[]),dict(status='checked',message='No matching links',jobs=[],digest='new')]:
   self.engine.lock.acquire()
   with patch('radar.engine.collect',return_value=result):self.engine.refresh([s])
  j=next(x for x in self.store.rows('items') if x['title']=='CFI');self.assertEqual(j['status'],'New')
 def test_parser_handles_structured_jobs_and_relative_leads(self):
  text='''<script type="application/ld+json">{"@graph":[{"@type":"JobPosting","title":"Flight Instructor","url":"/jobs/1/cfi","jobLocation":{"address":{"addressLocality":"Kent","addressRegion":"OH"}},"description":"<p>CFI required</p>"}]}</script><a href="/postings/23">Certified Flight Instructor 1 (Pool Posting)</a><a href="/jobs/4/a">Mechanic</a>'''
  jobs=extract_jobs(parse_page(text),'https://example.com','Test');self.assertEqual(len(jobs),2);self.assertEqual(jobs[0]['location'],'Kent, OH');self.assertIn('not yet verified',jobs[1]['evidence'])
 def test_backup_and_reopen_preserve_profile_resume_and_status(self):
  p=self.store.get('profile');p['total_hours']='321.4';self.store.put('profile',p);r=self.engine.upload('resume.txt',b'Commercial planned, not earned')
  z=zipfile.ZipFile(io.BytesIO(self.store.backup()));self.assertIn('radar.sqlite3',z.namelist());self.assertIn('resumes/'+r['stored_name'],z.namelist())
  again=Store(self.tmp.name);self.assertEqual(again.get('profile')['total_hours'],'321.4');self.assertEqual(len(again.rows('resumes')),1)
 def test_resume_docx_and_no_silent_profile_changes(self):
  before=self.store.get('profile');b=io.BytesIO()
  with zipfile.ZipFile(b,'w') as z:z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>CFI planned summer 2027</w:t></w:r></w:p></w:body></w:document>')
  r=self.engine.upload('../../resume.docx',b.getvalue());self.assertIn('CFI planned',r['text']);self.assertEqual(r['name'],'resume.docx');self.assertEqual(before,self.store.get('profile'))
 def test_locations_do_not_guess_unknown_distance(self):
  self.assertEqual(distances('Kent, Ohio')['Kent'],0);self.assertIsNone(distances('Multiple bases'));self.assertIsNone(distances('Cleveland, TN'))
 def test_blocks_local_source_urls(self):
  for url in ['file:///etc/passwd','http://127.0.0.1','http://localhost','http://169.254.169.254','https://user:pass@example.com']:
   with self.assertRaises(ValueError):validate_url(url)
 def test_api_security_and_profile_write(self):
  server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(self.engine,'test-token'));t=threading.Thread(target=server.serve_forever,daemon=True);t.start();u=f'http://127.0.0.1:{server.server_port}'
  # Local loopback tests must bypass this environment's external HTTP proxy.
  opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
  try:
   req=urllib.request.Request(u+'/api/profile',data=b'{"total_hours":"200"}',headers={'Content-Type':'application/json'})
   with self.assertRaises(urllib.error.HTTPError) as ex:opener.open(req)
   self.assertEqual(ex.exception.code,403)
   req.add_header('X-Radar-Token','test-token');opener.open(req).read();self.assertEqual(self.store.get('profile')['total_hours'],'200')
   req=urllib.request.Request(u+'/api/state',headers={'Origin':'https://other.example'})
   with self.assertRaises(urllib.error.HTTPError):opener.open(req)
   self.assertEqual(opener.open(u+'/').status,200)
  finally:server.shutdown();server.server_close();t.join()
if __name__=='__main__':unittest.main()
