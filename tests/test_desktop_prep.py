import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from app import make_handler
from radar.engine import Engine
from radar.storage import Store
from radar.runtime import open_existing,VERSION

class DesktopPrepTests(unittest.TestCase):
 def test_shutdown_requires_token_and_stops_server(self):
  with tempfile.TemporaryDirectory() as folder:
   engine=Engine(Store(folder))
   server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(engine,'secret','instance-id'))
   t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
   opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));url=f'http://127.0.0.1:{server.server_port}'
   try:
    with opener.open(url+'/api/health') as r:
     health=json.load(r);self.assertEqual(health['instance'],'instance-id');self.assertEqual(health['version'],VERSION)
    req=urllib.request.Request(url+'/api/shutdown',data=b'{}')
    with self.assertRaises(urllib.error.HTTPError) as ex:opener.open(req)
    self.assertEqual(ex.exception.code,403)
    req.add_header('X-Radar-Token','secret');engine.progress['running']=True
    with self.assertRaises(urllib.error.HTTPError) as ex:opener.open(req)
    self.assertEqual(ex.exception.code,409)
    engine.progress['running']=False
    with opener.open(req) as r:self.assertEqual(r.status,200)
    t.join(3);self.assertFalse(t.is_alive())
   finally:server.shutdown();server.server_close();t.join()
 def test_stale_instance_does_not_open_unrelated_service(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder);(path/'running.json').write_text(json.dumps(dict(port=12345,instance='ours')))
   fake=io.BytesIO(b'{"instance":"someone-else"}')
   with patch('radar.runtime.urllib.request.build_opener') as mock,patch('radar.runtime.webbrowser.open') as browser:
    mock.return_value.open.return_value.__enter__.return_value=fake
    self.assertFalse(open_existing(path));browser.assert_not_called()
 def test_packaging_recipe_includes_runtime_assets_and_windowed_mode(self):
  root=Path(__file__).resolve().parent.parent
  recipe=(root/'Radar.spec').read_text()
  for required in ["'radar'/'static'","'seed.json'","'VERSION'","'RESEARCH.md'","console=False","'pypdf'","'tkinter'"]:
   self.assertIn(required,recipe)
  self.assertTrue((root/'.github/workflows/build-windows.yml').is_file())
if __name__=='__main__':unittest.main()
