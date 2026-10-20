import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from radar.storage import Store
from radar.engine import Engine

class DashboardTests(unittest.TestCase):
 @unittest.skipUnless(shutil.which('node'),'Node is only needed for the JavaScript rendering check')
 def test_all_views_and_filters_render_with_revision2_data(self):
  with tempfile.TemporaryDirectory() as folder:
   engine=Engine(Store(folder))
   for title,loc,future in [('Fixture Ohio','Kent, OH',False),('Fixture California','Los Angeles, CA',True),('Fixture unknown','Multiple bases',False)]:
    j=engine.add_item(dict(title=title,location=loc,employer='Fixture company',section='early',future=future));engine.update_item(dict(id=j['id'],pinned=True,read=True))
   engine.preview_profile(engine.profile_template());engine.create_briefing()
   p=Path(folder)/'fixture.json';p.write_text(json.dumps(engine.state()),encoding='utf-8')
   r=subprocess.run(['node',str(Path(__file__).resolve().parents[1]/'build_tools/check_dashboard.js'),str(p)],capture_output=True,text=True,timeout=20)
   self.assertEqual(r.returncode,0,r.stdout+r.stderr)
