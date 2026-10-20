"""Versioned SQLite persistence. Migration backs up old data before editing it."""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime,timezone
from pathlib import Path
from .domain import normalize_item,source_section

def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def data_path():
    override=os.environ.get('AVIATION_RADAR_DATA')
    return Path(override) if override else Path(os.environ.get('LOCALAPPDATA',Path.home()/'.local/share'))/'AviationCareerRadar'

TABLES=('sources','items','resumes','briefings','profile_imports')
class Store:
    def __init__(self,path=None):
        self.path=Path(path) if path else data_path();self.path.mkdir(parents=True,exist_ok=True);(self.path/'resumes').mkdir(exist_ok=True)
        dbfile=self.path/'radar.sqlite3'
        oldversion=0
        if dbfile.exists():
            with sqlite3.connect(dbfile) as c:oldversion=c.execute('PRAGMA user_version').fetchone()[0]
            if oldversion>2:raise ValueError('Database is from a newer Radar version. Open it with that version; do not downgrade.')
            if oldversion<2:
                backups=self.path/'backups';backups.mkdir(exist_ok=True)
                backup=backups/('before-v2-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')+'.sqlite3')
                with sqlite3.connect(dbfile) as c,sqlite3.connect(backup) as dest:c.backup(dest)
        with self.db() as c:
            c.executescript('''CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY,body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS items(id TEXT PRIMARY KEY,url TEXT UNIQUE NOT NULL,body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,at TEXT,source_id TEXT,message TEXT);
            CREATE TABLE IF NOT EXISTS resumes(id TEXT PRIMARY KEY,body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS briefings(id TEXT PRIMARY KEY,body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS profile_imports(id TEXT PRIMARY KEY,body TEXT NOT NULL);''')
            if oldversion<2:
                row=c.execute("SELECT value FROM meta WHERE key='employers'").fetchone();employers=json.loads(row[0]) if row else []
                for r in c.execute('SELECT id,body FROM items').fetchall():
                    item=normalize_item(json.loads(r['body']),employers);c.execute('UPDATE items SET body=? WHERE id=?',(json.dumps(item),r['id']))
                for r in c.execute('SELECT id,body FROM sources').fetchall():
                    s=json.loads(r['body']);s.setdefault('section',source_section(s,employers));s.setdefault('config',{});c.execute('UPDATE sources SET body=? WHERE id=?',(json.dumps(s),r['id']))
                c.execute('PRAGMA user_version=2')
        self.seed()
    @contextmanager
    def db(self):
        c=sqlite3.connect(self.path/'radar.sqlite3',timeout=20);c.row_factory=sqlite3.Row;c.execute('PRAGMA journal_mode=WAL')
        try:
            with c:yield c
        finally:c.close()
    def get(self,key,default=None):
        with self.db() as c:r=c.execute('SELECT value FROM meta WHERE key=?',(key,)).fetchone()
        return json.loads(r[0]) if r else default
    def put(self,key,value):
        with self.db() as c:c.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',(key,json.dumps(value)))
    def rows(self,table):
        if table not in TABLES:raise ValueError('Unknown table')
        with self.db() as c:return [json.loads(r['body']) for r in c.execute('SELECT body FROM '+table)]
    def save(self,table,obj):
        if table not in TABLES:raise ValueError('Unknown table')
        with self.db() as c:
            if table=='items':c.execute('INSERT OR REPLACE INTO items VALUES (?,?,?)',(obj['id'],obj['url'],json.dumps(obj)))
            else:c.execute('INSERT OR REPLACE INTO '+table+' VALUES (?,?)',(obj['id'],json.dumps(obj)))
    def event(self,sid,msg):
        with self.db() as c:c.execute('INSERT INTO events(at,source_id,message) VALUES (?,?,?)',(now(),sid,msg))
    def events(self):
        with self.db() as c:return [dict(r) for r in c.execute('SELECT * FROM events ORDER BY id DESC LIMIT 200')]
    def seed(self):
        if self.get('initialized'):return
        seed=json.loads((Path(__file__).parent/'seed.json').read_text(encoding='utf-8'))
        self.put('profile',seed['profile']);self.put('employers',seed['employers']);self.put('pathways',seed['pathways'])
        for s in seed['sources']:
            s.setdefault('section',source_section(s,seed['employers']));s.setdefault('config',{});self.save('sources',s)
        from .engine import Engine
        engine=Engine(self)
        for item in seed.get('starter_leads',[]):
            item=dict(item);sid=item.pop('source_id');engine.upsert(item,sid)
        self.put('initialized',True)
    def backup(self):
        import io,zipfile,tempfile
        out=io.BytesIO()
        with tempfile.TemporaryDirectory() as t:
            db=Path(t)/'radar.sqlite3'
            with self.db() as c:
                dest=sqlite3.connect(db);c.backup(dest);dest.close()
            with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
                z.write(db,'radar.sqlite3')
                for p in (self.path/'resumes').iterdir():
                    if p.is_file():z.write(p,'resumes/'+p.name)
        return out.getvalue()
