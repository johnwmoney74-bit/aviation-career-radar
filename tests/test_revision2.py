"""Regression tests for data upgrades, truthful qualification colors and source coverage."""
import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from radar.domain import classify,extract_requirements,evaluate_requirements,location_states,validate_profile
from radar.engine import Engine
from radar.storage import Store
from radar.collectors import collect,validate_config

class RevisionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.store=Store(self.tmp.name);self.engine=Engine(self.store)
 def tearDown(self):self.tmp.cleanup()
 def add(self,**kw):
  return self.engine.add_item(dict(title='Flight instructor',employer='Test School',section='cfi',**kw))
 def approved(self,**kw):
  p=self.engine.profile_template();p['name']='Test Pilot';p['flight_hours']['total']=500;p['certificates']['cfi']=True;p['certificates']['cfii']=False;p.update(kw)
  r=self.engine.preview_profile(p);self.engine.approve_profile(r['id']);return self.store.get('profile')
 def test_import_is_previewed_and_planned_not_earned(self):
  old=self.store.get('profile');p=self.engine.profile_template();p['planned_certificates']=['cfi'];p['certificates']['cfi']=False;p['flight_hours']['total']=275.5
  r=self.engine.preview_profile(p);self.assertEqual(old,self.store.get('profile'));self.assertTrue(any(x['field']=='flight_hours.total' for x in r['changes']))
  result=self.engine.approve_profile(r['id']);self.assertFalse(result['qualification_profile']['certificates']['cfi']);self.assertEqual(result['planned_certificates'],['cfi'])
  self.engine.restore_profile(r['id']);self.assertEqual(self.store.get('profile'),old)
 def test_profile_rejects_guessed_types_and_stale_approval(self):
  for value in ['yes',1,{},float('nan')]:
   p=self.engine.profile_template();p['certificates']['cfi']=value
   with self.assertRaises(ValueError):validate_profile(p)
  p=self.engine.profile_template();p['flight_hours']['total']=float('nan')
  with self.assertRaises(ValueError):validate_profile(p)
  p=self.engine.profile_template();p['planned_certificates']=['cfi'];p['certificates']['cfi']=True
  with self.assertRaises(ValueError):validate_profile(p)
  r=self.engine.preview_profile(self.engine.profile_template());old=self.store.get('profile');old['name']='Changed';self.store.put('profile',old)
  with self.assertRaisesRegex(ValueError,'changed since preview'):self.engine.approve_profile(r['id'])
 def test_qualification_green_red_unknown_and_preferred(self):
  profile=self.approved();j={'requirements':[{'text':'CFI required','field':'certificates.cfi'},{'text':'400 total hours','field':'flight_hours.total','minimum':400},{'text':'CFII preferred','field':'certificates.cfii','preferred':True}],'requirements_reviewed':True}
  q=evaluate_requirements(j,profile);self.assertEqual(q['color'],'green');self.assertEqual([x['color'] for x in q['rows']],['green','green','red'])
  j['requirements'][1]['minimum']=1000;self.assertEqual(evaluate_requirements(j,profile)['color'],'red')
  j['requirements'][1]['field']='flight_hours.turbine';self.assertEqual(evaluate_requirements(j,profile)['color'],'gray')
  self.assertEqual(evaluate_requirements(j,{'certificates':'CFI'})['color'],'gray')
  j['requirements']=j['requirements'][:1];j['requirements_reviewed']=False;self.assertEqual(evaluate_requirements(j,profile)['color'],'gray')
 def test_extractor_keeps_alternatives_and_mixed_rows_unknown(self):
  rows=extract_requirements('Minimum 1,000 total flight hours.\nCurrent CFI required.\nCFI or CFII required.\n500 total hours and 50 multi-engine hours required.')
  self.assertEqual(rows[0]['field'],'flight_hours.total');self.assertEqual(rows[0]['minimum'],1000)
  self.assertEqual(rows[1]['field'],'certificates.cfi');self.assertEqual(rows[2]['field'],'unknown');self.assertEqual(rows[3]['field'],'unknown')
 def test_medical_class_and_no_atp_inference(self):
  profile=self.approved(medical_class=2);j={'requirements':[{'text':'First class current privileges','field':'medical_class','minimum':1}]}
  self.assertEqual(evaluate_requirements(j,profile)['color'],'red')
  j['requirements'][0]['minimum']=3;self.assertEqual(evaluate_requirements(j,profile)['rows'][0]['color'],'green')
  j['requirements']=[{'text':'ATP required','field':'certificates.atp'}];self.assertEqual(evaluate_requirements(j,profile)['rows'][0]['color'],'gray')
 def test_personal_state_survives_refresh_and_closed_never_deleted(self):
  j=self.add(url='https://example.com/job/cfi');j=self.engine.update_item({'id':j['id'],'read':True,'pinned':True,'interest':'Not interested','progress':'Applied','availability':'Closed','notes':'Call on Friday','follow_up':'2027-01-08','requirements':[{'text':'CFI required','field':'certificates.cfi'}],'requirements_reviewed':True})
  fresh=dict(j,description='Changed minimum 1,000 total hours required',notes='overwrite',pinned=False,progress='Not started');self.engine.upsert(fresh,'other-source')
  saved=next(x for x in self.store.rows('items') if x['id']==j['id'])
  for k in ['read','pinned','interest','progress','availability','notes','follow_up']:self.assertEqual(saved[k],j[k])
  self.assertTrue(saved['updated_since_read']);self.assertFalse(saved['requirements_reviewed']);self.assertEqual(saved['requirements'][0]['field'],'certificates.cfi')
  self.engine.update_item({'id':j['id'],'pinned':False});self.assertTrue(any(x['id']==j['id'] for x in self.store.rows('items')))
 def test_word_of_mouth_no_url_and_merge_retains_tracking(self):
  tip=self.add(description='Airport contact said call chief pilot',contact='Chief pilot',heard_at='2026-10-20',origin='Airport conversation')
  self.assertTrue(tip['url'].startswith('note://'));tip=self.engine.update_item({'id':tip['id'],'pinned':True,'notes':'Ask about summer start','progress':'Looking into','follow_up':'2027-02-01'})
  official=self.add(url='https://example.com/job/123',description='Official details');merged=self.engine.link_item(tip['id'],official['url'])
  self.assertEqual(merged['id'],official['id']);self.assertTrue(merged['pinned']);self.assertIn('Ask about summer start',merged['notes']);self.assertEqual(merged['progress'],'Looking into');self.assertEqual(merged['follow_up'],'2027-02-01')
  self.assertIn('Airport contact said call chief pilot',json.dumps(merged['interactions']));self.assertNotIn(tip['id'],[x['id'] for x in self.store.rows('items')])
 def test_categories_and_work_states(self):
  for title,company,expected in [('CFI','United Airlines','cfi'),('Cadet program','Republic Airways','pathways'),('First Officer','Republic Airways','regional'),('Citation Captain','Local operator','longterm'),('First Officer','FedEx','longterm'),('Survey pilot','Local operator','early')]:
   self.assertEqual(classify(dict(title=title,employer=company)),expected)
  sources={x['id']:x for x in self.store.rows('sources')};self.assertEqual(sources['ksu-jobs']['section'],'cfi');self.assertEqual(sources['tandg']['section'],'cfi');self.assertEqual(sources['fedex']['section'],'longterm')
  self.assertEqual(location_states('Charleston, West Virginia'),['WV']);self.assertEqual(location_states('Kent, Ohio; Columbus, OH'),['OH']);self.assertEqual(location_states('Cleveland, TN'),['TN']);self.assertEqual(location_states('Multiple bases'),[])
 def test_legacy_database_backed_up_before_migration(self):
  j=self.add(url='https://example.com/job/legacy');legacy=dict(j,status='Applied',notes='Keep this note')
  for k in ['section','read','interest','progress','availability','pinned','future','interactions']:legacy.pop(k,None)
  self.store.save('items',legacy)
  with self.store.db() as c:c.execute('PRAGMA user_version=1')
  again=Store(self.tmp.name);saved=next(x for x in again.rows('items') if x['id']==j['id']);self.assertEqual(saved['progress'],'Applied');self.assertTrue(saved['pinned']);self.assertEqual(saved['notes'],'Keep this note')
  backups=list((Path(self.tmp.name)/'backups').glob('*.sqlite3'));self.assertEqual(len(backups),1)
  with sqlite3.connect(backups[0]) as c:
   self.assertEqual(c.execute('PRAGMA user_version').fetchone()[0],1);self.assertNotIn('pinned',json.loads(c.execute('SELECT body FROM items WHERE id=?',(j['id'],)).fetchone()[0]))
  Store(self.tmp.name);self.assertEqual(len(list((Path(self.tmp.name)/'backups').glob('*.sqlite3'))),1)
 def test_newer_database_refuses_downgrade(self):
  with self.store.db() as c:c.execute('PRAGMA user_version=9')
  with self.assertRaisesRegex(ValueError,'newer'):Store(self.tmp.name)
 def test_briefing_snapshot_and_response_never_change_jobs(self):
  j=self.add();self.engine.update_item({'id':j['id'],'pinned':True,'notes':'My context'})
  before=self.store.rows('items');r=self.engine.create_briefing(7);self.assertIn('My context',r['prompt']);self.assertIn('Source coverage',r['prompt']);self.assertIn('Do not infer industry-wide',r['prompt'])
  self.engine.import_briefing(r['id'],'Employer X doubled pay. This is commentary.');self.assertEqual(before,self.store.rows('items'))
  saved=self.store.rows('briefings')[0];self.assertEqual(saved['prompt'],r['prompt']);self.assertEqual(len(saved['responses']),1)
  self.engine.update_item({'id':j['id'],'notes':'Changed'});self.assertEqual(self.store.rows('briefings')[0]['snapshot']['items'][-1]['notes'],'My context')
 def source(self):return dict(id='fixture',name='Test operator',url='https://example.com/jobs',employer='Test',category='jobs',section='early',method='page',enabled=True,config={})
 def page(self,links):return '<title>Careers</title><p>'+('Company introduction and careers information. '*6)+'</p>'+links
 def test_source_plain_page_is_not_verified_extraction(self):
  with patch('radar.collectors.validate_url'),patch('radar.collectors.allowed',return_value=(True,'Allowed')),patch('radar.collectors.fetch',return_value=(self.page('No current links'),'https://example.com/jobs')):r=collect(self.source())
  self.assertEqual(r['status'],'checked');self.assertEqual(r['jobs'],[]);self.assertIn('unverified',r['coverage']);self.assertTrue(r['diagnostics']['warnings'])
  source=self.source();source.update(status=r['status'],checked_count=0,diagnostics=r['diagnostics']);self.store.save('sources',source)
  with self.assertRaises(ValueError):self.engine.verify_source('fixture')
 def test_custom_rules_pagination_details_and_sample(self):
  s=self.source();s['config']=dict(link_contains='/opportunity/',title_keywords='captain, instructor',exclude_contains='closed',next_link_text='Next',max_pages=2,detail_limit=1,sample_url='https://example.com/opportunity/2')
  pages={'https://example.com/jobs':self.page('<a href="/opportunity/1">Instructor</a><a href="/jobs?page=2">Next</a><a href="/opportunity/closed">Captain closed</a>'),'https://example.com/jobs?page=2':self.page('<a href="/opportunity/2">Captain</a>'),'https://example.com/opportunity/1':self.page('<p>Minimum 500 total hours required.</p>')}
  with patch('radar.collectors.validate_url'),patch('radar.collectors.allowed',return_value=(True,'Allowed')),patch('radar.collectors.fetch',side_effect=lambda u:(pages[u],u)):r=collect(s)
  self.assertEqual(len(r['jobs']),2);self.assertTrue(r['diagnostics']['sample_found']);self.assertEqual(len(r['diagnostics']['pages']),2);self.assertIn('500 total hours',r['jobs'][0]['description']);self.assertTrue(any(x['stage']=='Pagination' for x in r['diagnostics']['stages']))
 def test_source_restriction_is_explicit_and_old_records_preserved(self):
  with patch('radar.collectors.validate_url'),patch('radar.collectors.allowed',return_value=(False,'Robots disallows this path')),patch('radar.collectors.fetch') as fetch:r=collect(self.source())
  self.assertEqual(r['status'],'blocked');fetch.assert_not_called();self.assertEqual(r['diagnostics']['stages'][-1]['status'],'failed')
 def test_sample_mismatch_blocks_verification_and_report_private_exclusion(self):
  source=self.source();source.update(status='checked',checked_count=2,diagnostics={'sample_found':False},notes='private source note',preview=[]);self.store.save('sources',source)
  with self.assertRaisesRegex(ValueError,'sample'):self.engine.verify_source(source['id'])
  self.add(description='private application fact');self.engine.upload('resume.txt',b'private resume fact');report=json.dumps(self.engine.source_report(source['id']))
  for secret in ['private source note','private application fact','private resume fact','John Maloney']:self.assertNotIn(secret,report)
 def test_preview_test_does_not_import_until_requested(self):
  s=self.source();self.store.save('sources',s);j=dict(title='Pilot',employer='Test',url='https://example.com/job/new',location='',description='',kind='job',evidence='Fixture')
  self.engine.lock.acquire()
  with patch('radar.engine.collect',return_value=dict(status='checked',message='1 record',jobs=[j],preview=[j],coverage='listings found',digest='a')):self.engine.refresh([s],False,False)
  self.assertNotIn(j['url'],[x['url'] for x in self.store.rows('items')]);source=next(x for x in self.store.rows('sources') if x['id']==s['id']);self.assertEqual(len(source['preview']),1);self.assertEqual(source['diagnostics']['stages'][-1]['status'],'preview only')
 def test_source_settings_change_invalidates_verification(self):
  s=self.source();s['verified_at']='2026-01-01';self.store.save('sources',s)
  with patch('radar.engine.validate_url'):
   changed=self.engine.save_source(dict(s,config=dict(link_contains='/new/')))
  self.assertIsNone(changed['verified_at']);self.assertIn('retest',changed['coverage'])
 def test_config_rejects_unbounded_requests(self):
  for c in [{'max_pages':100},{'detail_limit':-1},{'extra_urls':['https://example.com']*9}]:
   with self.assertRaises(ValueError):validate_config(c)

if __name__=='__main__':unittest.main()
